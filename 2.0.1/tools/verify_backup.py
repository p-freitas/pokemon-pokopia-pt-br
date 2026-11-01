"""Read-only complete RomFS comparison. Does not launch emulator or touch saves."""
import argparse
import json
from pathlib import Path
from formats import sha
from project import REPORTS

def main():
    p=argparse.ArgumentParser();p.add_argument('backup');p.add_argument('installed');a=p.parse_args()
    roots=[Path(a.backup),Path(a.installed)]
    paths=[{str(p.relative_to(root)).replace('\\','/'):p for p in root.rglob('*') if p.is_file()} for root in roots]
    report={'backup_only':sorted(paths[0].keys()-paths[1].keys()),'installed_only':sorted(paths[1].keys()-paths[0].keys()),'files':[]}
    for name in sorted(paths[0].keys()&paths[1].keys()):
        pair=[paths[j][name] for j in (0,1)]
        sizes=[p.stat().st_size for p in pair]
        hashes=[sha(p) for p in pair]
        report['files'].append(dict(path=name,bytes=sizes,sha256=hashes,equal=sizes[0]==sizes[1] and hashes[0]==hashes[1]))
    report['passed']=not report['backup_only'] and not report['installed_only'] and all(r['equal'] for r in report['files'])
    (REPORTS/'backup_comparison.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'passed':report['passed'],'files':len(report['files']),'bytes_per_copy':sum(r['bytes'][0] for r in report['files'])}))

if __name__=='__main__':main()
