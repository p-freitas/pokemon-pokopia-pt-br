"""Compare an integrated mod with the pinned upstream release, field by field."""
import argparse
import collections
from formats import Archive,parse_table,sha
from project import ROOT,REPORTS,read_jsonl,dump,technical_errors

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--baseline',required=True)
    p.add_argument('--mod',default=str(ROOT/'romfs'))
    a=p.parse_args();baseline=Archive(a.baseline,tolerate_legacy_stored=True);mod=Archive(a.mod)
    if len(baseline.entries)!=len(mod.entries):raise ValueError('Index length changed')
    changes=collections.defaultdict(dict)
    for r in read_jsonl(ROOT/'translations/additions.jsonl'):
        if technical_errors(r['source'],r['translation']):raise ValueError('Addition tags changed')
        key=(r['row'],r['field']) if 'row' in r else None
        # Public addition records use stable IDs, independent of local filenames.
        b,row,field=r['id'].split(':')
        changes[int(b[1:])][(int(row[1:]),int(field[1:]))]=r
    unchanged=0;preserved_fields=0
    for i in range(len(mod.entries)):
        original=baseline.read(i);result=mod.read(i)
        if i not in changes:
            if original!=result:raise ValueError(f'Unrequested upstream payload change: bank {i}')
            unchanged+=1
        else:
            t=parse_table(original);new=parse_table(result)
            if t is None or new is None or t.stride!=new.stride or t.count!=new.count:raise ValueError('Table structure changed')
            for key,text in t.strings.items():
                r=changes[i].get(key)
                if r and r['source']!=text:raise ValueError('Addition overwrites translated upstream text')
                expected=r['translation'] if r else text
                if new.strings[key]!=expected:raise ValueError('Unexpected field change')
                if r is None:preserved_fields+=1
    report=dict(passed=True,index_entries=len(mod.entries),additional_translations=sum(map(len,changes.values())),
                changed_text_banks=len(changes),unchanged_bank_payloads=unchanged,
                preserved_other_fields_in_changed_banks=preserved_fields,
                strict_decode_all_records=True,upstream_text_preserved=True,
                output_sha256={n:sha(mod.root/n) for n in ('LD_C0_R.BIN','LI_C0_R.IDX')},emulator_test='not_run')
    dump(REPORTS/'integration_validation.json',report);print(report)

if __name__=='__main__':main()
