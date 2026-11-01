"""Package append-only translation deltas; no complete original game BIN needed."""
import argparse
import json
from pathlib import Path
import shutil
import struct
import zipfile
from formats import Archive,sha
from project import ROOT,REPORTS,config

def create(args):
    source=Archive(config()['source']);built=Archive(args.mod)
    if built.data[:len(source.data)]!=source.data:
        raise ValueError('Only append-only mods are supported')
    edits=[]
    for i in range(len(source.entries)):
        if source.entries[i]!=built.entries[i]:
            edits.append([i,*struct.unpack_from('<QQQQ',built.index,32*i)])
    manifest={'format':'pokopia-append-patch-v1','label':'655360-experimental','source':{},'target':{},'index_edits':edits}
    for name in ('LD_C0_R.BIN','LI_C0_R.IDX'):
        manifest['source'][name]={'bytes':(source.root/name).stat().st_size,'sha256':sha(source.root/name)}
        manifest['target'][name]={'bytes':(built.root/name).stat().st_size,'sha256':sha(built.root/name)}
    with zipfile.ZipFile(args.output,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        z.writestr('manifest.json',json.dumps(manifest,indent=2))
        z.writestr('translated-tail.bin',built.data[len(source.data):])
    print(f'Patch created: {len(edits)} bank entries; {Path(args.output).stat().st_size} bytes')

def apply(args):
    source=Path(args.source).resolve();target=Path(args.output).resolve()
    if target==source or source in target.parents or target in source.parents:
        raise ValueError('Output must be isolated from source')
    allowed=(ROOT/'build').resolve()
    if allowed not in target.parents:
        raise ValueError('Output must be inside project/build, never the game source')
    with zipfile.ZipFile(args.patch) as z:
        manifest=json.loads(z.read('manifest.json'));tail=z.read('translated-tail.bin')
    if manifest['format']!='pokopia-append-patch-v1':raise ValueError('Unknown patch format')
    for name,info in manifest['source'].items():
        if name not in ('LD_C0_R.BIN','LI_C0_R.IDX'):raise ValueError('Unknown source filename')
        if (source/name).stat().st_size!=info['bytes'] or sha(source/name)!=info['sha256']:
            raise ValueError('Original source hash mismatch; no files written')
    idx=bytearray((source/'LI_C0_R.IDX').read_bytes());seen=set()
    for i,offset,size,stored,flag in manifest['index_edits']:
        if i in seen or not 0<=i<len(idx)//32:raise ValueError('Invalid patch index')
        seen.add(i)
        if offset<manifest['source']['LD_C0_R.BIN']['bytes'] or offset+stored>manifest['source']['LD_C0_R.BIN']['bytes']+len(tail):
            raise ValueError('Patch offset outside appended data')
        struct.pack_into('<QQQQ',idx,32*i,offset,size,stored,flag)
    target.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(source/'LD_C0_R.BIN',target/'LD_C0_R.BIN')
    with (target/'LD_C0_R.BIN').open('ab') as f:f.write(tail)
    (target/'LI_C0_R.IDX').write_bytes(idx)
    for name,info in manifest['target'].items():
        if name not in ('LD_C0_R.BIN','LI_C0_R.IDX'):raise ValueError('Unknown target filename')
        if (target/name).stat().st_size!=info['bytes'] or sha(target/name)!=info['sha256']:
            raise ValueError('Patched output hash mismatch; do not install')
    archive=Archive(target)
    for bank in seen:archive.read(bank)
    print(f'Patch reapplied; {len(seen)} banks validated; both output hashes match build exactly.')

def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True)
    cr=sub.add_parser('create');cr.add_argument('--mod',default=str(ROOT/'build/Pokopia-PTBR-655360/romfs'));cr.add_argument('--output',required=True);cr.set_defaults(func=create)
    ap=sub.add_parser('apply');ap.add_argument('--source',required=True);ap.add_argument('--patch',required=True);ap.add_argument('--output',default=str(ROOT/'build/from-patch/romfs'));ap.set_defaults(func=apply)
    a=p.parse_args();a.func(a)

if __name__=='__main__':main()
