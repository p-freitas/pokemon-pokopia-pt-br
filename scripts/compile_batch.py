"""Expand exact whole-source TSV translations to pending IDs only; no partial replace."""
import argparse
import csv
from pathlib import Path
from project import CAT, read_jsonl, save_jsonl, technical_errors

def main():
    p=argparse.ArgumentParser();p.add_argument('tsv');p.add_argument('output');a=p.parse_args()
    mapping={}
    with Path(a.tsv).open(encoding='utf-8-sig',newline='') as f:
        for cells in csv.reader(f,delimiter='\t'):
            pairs=[cells] if len(cells)==2 else [(cells[0],cells[2]),(cells[1],cells[3])] if len(cells)==4 else []
            if not pairs:raise ValueError('Expected two or four TSV columns')
            for source,target in pairs:
                if source in mapping:raise ValueError('Duplicate source')
                if technical_errors(source,target):raise ValueError(f'Invalid tags: {source}')
                mapping[source]=target
    rows=[{'id':r['id'],'source':r['source'],'translation':mapping[r['source']]} for r in read_jsonl(CAT)
          if r['status']=='pending_translation' and r['source'] in mapping]
    save_jsonl(a.output,rows)
    print(f'{len(mapping)} source translations; {len(rows)} pending fields selected')

if __name__=='__main__':main()
