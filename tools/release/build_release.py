"""Build a compressed release with the same manual/installer payload layout."""
import argparse
import ast
import copy
import hashlib
import json
from pathlib import Path
import pprint
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
import zlib

from linkdata import BIN, IDX, repack, sha256_file


ROOT = Path(__file__).resolve().parents[2]
INSTALLER = ROOT / "tools/installer/pokopia_installer.py"
CONFIG_NAMES = ("APP_VERSION", "PACKAGE_NAME", "PACKAGE_URL", "ROMFS_FILES", "VERSIONS")


def installer_config(source: str) -> dict:
    return {
        node.targets[0].id: ast.literal_eval(node.value)
        for node in ast.parse(source).body
        if isinstance(node, ast.Assign) and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name) and node.targets[0].id in CONFIG_NAMES
    }


def render_installer(source: str, values: dict) -> str:
    lines = source.splitlines(keepends=True)
    edits = []
    for node in ast.parse(source).body:
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name) and node.targets[0].id in values):
            name = node.targets[0].id
            edits.append((node.lineno - 1, node.end_lineno,
                          f"{name} = {pprint.pformat(values[name], sort_dicts=False)}\n"))
    if len(edits) != len(values):
        raise ValueError("Installer configuration assignments were not found")
    for start, end, replacement in reversed(edits):
        lines[start:end] = [replacement]
    result = "".join(lines)
    compile(result, "release_installer.py", "exec")
    return result


def build(args: argparse.Namespace) -> Path:
    source_text = INSTALLER.read_text(encoding="utf-8")
    config = installer_config(source_text)
    version = args.version or config["APP_VERSION"]
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9.-]+)?", version):
        raise ValueError("Release version must look like 2.5.1 or 2.5.1-test")
    output = args.output.resolve()
    # Never allow generated builds inside tracked version payloads or tools.
    for protected in (ROOT / "tools", *(ROOT / v for v in config["VERSIONS"])):
        if output == protected or protected in output.parents:
            raise ValueError("Output must be outside source payloads and tools")
    output.mkdir(parents=True, exist_ok=True)
    suffix = "-manual" if args.manual_only else ""
    package_name = f"Pokemon-Pokopia-PT-BR-v{version}{suffix}.zip"
    destination = output / package_name
    report_path = output / f"Pokemon-Pokopia-PT-BR-v{version}{suffix}-build.json"
    if destination.exists() or report_path.exists():
        raise FileExistsError("This release already exists in the output directory")
    signatures = copy.deepcopy(config["VERSIONS"])
    report = {"version": version, "manual_only": args.manual_only,
              "python_version": sys.version.split()[0],
              "zlib_version": zlib.ZLIB_RUNTIME_VERSION,
              "game_test": "not_run", "versions": {}}

    with tempfile.TemporaryDirectory(prefix=".pokopia-release-", dir=output) as temp:
        stage = Path(temp)
        package = stage / "package"
        package.mkdir()
        for game_version, signature in signatures.items():
            source = ROOT / game_version / "romfs"
            target = package / game_version / "romfs"
            input_hashes = {}
            for relative in config["ROMFS_FILES"]:
                path = source / relative
                # A fresh checkout must have fetched its LFS objects first.
                with path.open("rb") as stream:
                    if stream.read(64).startswith(b"version https://git-lfs.github.com/spec/v1"):
                        raise ValueError(f"Git LFS pointer found: {path}. Run git lfs pull first.")
                input_hashes[relative] = sha256_file(path)
            print(f"Repacking {game_version} and comparing every decoded record...", flush=True)
            stats = repack(source, target)
            for relative in config["ROMFS_FILES"]:
                if relative in (BIN, IDX):
                    continue
                dest = target / relative
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source / relative, dest)
            hashes = {name: sha256_file(target / name) for name in config["ROMFS_FILES"]}
            previous = signature.setdefault("previous_hashes", [])
            for known in (signature["hashes"], input_hashes):
                if known != hashes and known not in previous:
                    previous.append(known)
            signature["hashes"] = hashes
            signature["idx_size"] = (target / IDX).stat().st_size
            signature["rdb_size"] = (target / "motor_asset_re/KIDS_PLATFORM_OUNCE/root.rdb").stat().st_size
            signature["fdata_size"] = (target / "motor_asset_re/KIDS_PLATFORM_OUNCE/0x4b13d561.fdata").stat().st_size
            report["versions"][game_version] = {**stats, "input_hashes": input_hashes, "hashes": hashes}
            print(f"{stats['source_bytes']:,} -> {stats['output_bytes']:,} bytes; "
                  f"{stats['records_verified']} records verified", flush=True)

        # Compile the exact payload fingerprints into the EXE; do not trust an
        # editable external manifest or keep stale hashes from a previous build.
        generated = stage / "pokopia_installer.py"
        generated.write_text(render_installer(source_text, {
            "APP_VERSION": version,
            "PACKAGE_NAME": package_name,
            "PACKAGE_URL": f"https://github.com/{args.repository}/releases/download/v{version}/{package_name}",
            "VERSIONS": signatures,
        }), encoding="utf-8")
        if not args.manual_only:
            subprocess.run([
                "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                str(ROOT / "tools/installer/build.ps1"),
                "-OutputDirectory", str(package), "-SourcePath", str(generated),
                "-InstallerName", f"Pokemon-Pokopia-PT-BR-Installer-v{version}",
            ], check=True)

        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        readme = readme.replace(config["APP_VERSION"], version)
        if args.manual_only:
            readme = re.sub(r"^Pokemon-Pokopia-PT-BR-Installer-.*\.exe\n", "", readme, flags=re.MULTILINE)
            readme = re.sub(r"### Instalação automática\n.*?(?=### Instalação manual)",
                            "", readme, flags=re.DOTALL)
            readme = readme.replace("(ZIP com instalador)", "(ZIP para instalação manual)")
            readme = readme.replace(f"Pokemon-Pokopia-PT-BR-v{version}.zip", package_name)
        (package / "README.md").write_text(readme, encoding="utf-8")
        with zipfile.ZipFile(stage / package_name, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for path in sorted(package.rglob("*")):
                if path.is_file():
                    archive.write(path, path.relative_to(package).as_posix())
        # Verify the packaged bytes, including textures, before publishing output.
        with zipfile.ZipFile(stage / package_name) as archive:
            if archive.testzip() is not None:
                raise ValueError("Release ZIP failed its CRC check")
            for game_version, signature in signatures.items():
                for relative, expected in signature["hashes"].items():
                    digest = hashlib.sha256()
                    with archive.open(f"{game_version}/romfs/{relative}") as stream:
                        for block in iter(lambda: stream.read(1024 * 1024), b""):
                            digest.update(block)
                    if digest.hexdigest() != expected:
                        raise ValueError(f"Release ZIP hash mismatch: {relative}")
        report["zip_bytes"] = (stage / package_name).stat().st_size
        report["zip_sha256"] = sha256_file(stage / package_name)
        # Metadata is for the maintainer; it stays outside the player-facing ZIP.
        (stage / "build.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        # Copy into newly created files so output inherits the destination's
        # permissions, rather than the private temporary directory's ACL.
        for source, target in ((stage / package_name, destination), (stage / "build.json", report_path)):
            with source.open("rb") as incoming, target.open("xb") as outgoing:
                shutil.copyfileobj(incoming, outgoing, 1024 * 1024)
    print(destination, flush=True)
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", help="Mod release version; defaults to the current installer version")
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    parser.add_argument("--repository", default="LucianoNeo/pokemon-pokopia-pt-br")
    parser.add_argument("--manual-only", action="store_true", help="Skip Windows EXE compilation")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", args.repository):
        parser.error("--repository must be owner/repository")
    build(args)


if __name__ == "__main__":
    main()
