"""Incremental extraction, conservative porting, CSV review and isolated builds."""
import argparse
import collections
import csv
import hashlib
import json
from pathlib import Path
import re
import struct
from formats import Archive, align, compress, parse_table, rebuild_table, sha

ROOT = Path(__file__).resolve().parents[1]
TRANSLATIONS = ROOT/'translations'
REPORTS = ROOT/'reports'
CAT = TRANSLATIONS/'catalog.jsonl'
STATUSES = {'pending_translation','translated_unreviewed','reviewed','needs_attention'}
TAG = re.compile(r'<[^<>]*>|\{[^{}]*\}|%(?:\d+\$)?[-+0 #]*\d*(?:\.\d+)?[sdifuxX]')

def read_jsonl(path):
    with Path(path).open(encoding='utf-8-sig') as f:
        return [json.loads(line) for line in f if line.strip()]

def save_jsonl(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp = path.with_suffix(path.suffix+'.tmp')
    with tmp.open('w',encoding='utf-8',newline='\n') as f:
        for row in rows:
            f.write(json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n')
    tmp.replace(path)

def dump(path, value):
    Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def technical_errors(source, target):
    errors = []
    if collections.Counter(TAG.findall(source)) != collections.Counter(TAG.findall(target)):
        errors.append('placeholder_or_tag_mismatch')
    if any(ord(c)<32 and c not in '\n\r\t' for c in target):
        errors.append('control_character')
    if any(0xd800<=ord(c)<=0xdfff for c in target):
        errors.append('invalid_unicode')
    if source.count('\n') != target.count('\n'):
        errors.append('newline_mismatch')
    return errors

def config():
    return json.loads((ROOT/'local/config.json').read_text(encoding='utf-8'))

def configure(args):
    manifest=json.loads((REPORTS/'source_manifest.json').read_text(encoding='utf-8'))
    root=Path(args.source).resolve()
    for name,info in manifest['source_files'].items():
        if sha(root/name)!=info['sha256']:
            raise ValueError(f'Unsupported source hash: {name}; do not use another version or an already patched source')
    (ROOT/'local').mkdir(exist_ok=True)
    dump(ROOT/'local/config.json',{'source':str(root)})
    print('Local source configured; exact supported BIN/IDX hashes verified.')

def queue(args):
    rows=(r for r in read_jsonl(CAT) if r['status']=='pending_translation' and (args.bank is None or r['bank']==args.bank))
    selected=[]
    for r in rows:
        selected.append({k:r[k] for k in ('id','source','translation','status')})
        if len(selected)>=args.limit:break
    save_jsonl(args.output,selected)
    print(f'{len(selected)} pending entries exported')

def extract(args):
    source=Path(args.source).resolve()
    target=Path(args.output).resolve()
    if target.exists():raise ValueError('Extraction output already exists; no review work overwritten')
    manifest=json.loads((REPORTS/'source_manifest.json').read_text(encoding='utf-8'))
    for name,info in manifest['source_files'].items():
        if sha(source/name)!=info['sha256']:raise ValueError('Unsupported original source hash')
    archive=Archive(source)
    banks=json.loads((REPORTS/'banks.json').read_text(encoding='utf-8'))
    rows=[]
    for bank in banks:
        table=parse_table(archive.read(bank['bank']))
        if table is None or table.count!=bank['count'] or table.stride!=bank['stride']:
            raise ValueError('Original table structure differs from supported layout')
        for (row,field),text in table.strings.items():
            if text:rows.append(dict(id=f"b{bank['bank']:05d}:r{row:05d}:f{field:02d}",
                bank=bank['bank'],row=row,field=field,source=text,translation='',status='pending_translation',origin=''))
    save_jsonl(target,rows)
    print(f'{len(rows)} original text fields extracted; canonical catalog untouched')

def report(args):
    rows = read_jsonl(CAT)
    counts=collections.Counter(r['status'] for r in rows)
    origins=collections.Counter(r['origin'] for r in rows)
    sources=collections.Counter(r['source'] for r in rows)
    result = dict(found_nonempty_fields=len(rows),statuses=dict(counts),origins=dict(origins),
                  changed_translations=sum(bool(r['translation']) and r['translation']!=r['source'] for r in rows),
                  preserved_unchanged=sum(bool(r['translation']) and r['translation']==r['source'] for r in rows),
                  distinct_sources=len(sources),repeated_fields=sum(v-1 for v in sources.values()))
    dump(REPORTS/'progress.json',result)
    save_jsonl(TRANSLATIONS/'memory.jsonl',({'source':r['source'],'translation':r['translation'],'status':r['status'],'id':r['id'],'origin':r['origin']} for r in rows if r['translation']))
    print(json.dumps(result,ensure_ascii=False))

def apply_batch(args):
    rows=read_jsonl(CAT)
    byid={r['id']:r for r in rows}
    incoming=read_jsonl(args.file)
    seen=set()
    for item in incoming:
        if item['id'] in seen:
            raise ValueError('Duplicate batch id')
        seen.add(item['id'])
        r=byid[item['id']]
        if r['status']!='pending_translation':
            # Idempotent resumption; never replace an existing translation.
            if r['translation']==item['translation']:
                continue
            raise ValueError(f'Not pending: {r["id"]}')
        if item.get('source',r['source'])!=r['source']:
            raise ValueError('Source mismatch')
        errors=technical_errors(r['source'],item['translation'])
        if errors or not item['translation']:
            raise ValueError(f'{r["id"]}: {errors or "empty_translation"}')
        r.update(translation=item['translation'],status='translated_unreviewed',origin='ai_batch')
    save_jsonl(CAT,rows)
    report(None)

def reuse(args):
    rows=read_jsonl(CAT)
    memory=collections.defaultdict(set)
    for r in rows:
        if r['translation'] and r['status'] in ('translated_unreviewed','reviewed'):
            memory[r['source']].add(r['translation'])
    reused=0;names=0
    for r in rows:
        if r['status']!='pending_translation':continue
        if r['bank'] in (2261,4934):
            r.update(translation=r['source'],status='translated_unreviewed',origin='preserved_pokemon_name');names+=1
        elif len(memory[r['source']])==1:
            text=next(iter(memory[r['source']]))
            if not technical_errors(r['source'],text):
                r.update(translation=text,status='translated_unreviewed',origin='exact_memory');reused+=1
    save_jsonl(CAT,rows)
    print(json.dumps(dict(reused_exact_sources=reused,preserved_pokemon_names=names)))
    report(None)

def review(args):
    rows=read_jsonl(CAT)
    fields=['id','source','translation','status','origin']
    if args.import_file:
        byid={r['id']:r for r in rows}
        seen=set()
        with Path(args.import_file).open(encoding='utf-8-sig',newline='') as f:
            for item in csv.DictReader(f):
                if item['id'] in seen:raise ValueError('Duplicate review id')
                seen.add(item['id']);r=byid[item['id']]
                if item['source']!=r['source']:raise ValueError('Source changed')
                if item['status'] not in STATUSES:raise ValueError('Invalid status')
                if item['translation'] and item['translation']!=r['translation']:
                    errors=technical_errors(r['source'],item['translation'])
                    if errors:raise ValueError(f'{r["id"]}: {errors}')
                elif not item['translation'] and item['status'] in ('reviewed','translated_unreviewed'):
                    raise ValueError('Translated status requires text')
                changed=item['translation']!=r['translation'] or item['status']!=r['status']
                r.update(translation=item['translation'],status=item['status'])
                if changed:r['origin']='manual_csv'
        save_jsonl(CAT,rows);report(None)
    else:
        with (TRANSLATIONS/'review.csv').open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fields,extrasaction='ignore');w.writeheader();w.writerows(rows)

def build(args):
    cfg=config();original=Archive(cfg['source'])
    manifest=json.loads((REPORTS/'source_manifest.json').read_text(encoding='utf-8'))
    for name,info in manifest['source_files'].items():
        if sha(Path(cfg['source'])/name)!=info['sha256']:raise ValueError('Source hash changed')
    baseline=Path(args.baseline).resolve()
    hashes={n:sha(baseline/n) for n in ('LD_C0_R.BIN','LI_C0_R.IDX')}
    if hashes not in manifest['supported_baselines']:
        raise ValueError('Unrecognized baseline; use the versioned RomFS from this branch')
    source=Archive(baseline,tolerate_legacy_stored=True)
    if len(source.entries)!=len(original.entries):raise ValueError('Baseline index count differs')
    target=Path(args.output).resolve()
    source_root=source.root.resolve()
    if target==source_root or source_root in target.parents or target in source_root.parents:
        raise ValueError('Output must be isolated from source')
    original_root=original.root.resolve()
    if target==original_root or original_root in target.parents or target in original_root.parents:
        raise ValueError('Output must be isolated from original source')
    # Never allow output in the source tree, game, upstream final binary tree or emulator.
    allowed=(ROOT/'build').resolve()
    if target!=allowed and allowed not in target.parents:
        raise ValueError('Build output must be under project/build')
    target.mkdir(parents=True,exist_ok=True)
    rows=read_jsonl(CAT);changes=collections.defaultdict(dict);table_cache={};original_cache={}
    for r in rows:
        if r['translation'] and r['status'] in ('translated_unreviewed','reviewed'):
            if r['bank'] not in table_cache:table_cache[r['bank']]=parse_table(source.read(r['bank']))
            t=table_cache[r['bank']]
            key=(r['row'],r['field'])
            if r['bank'] not in original_cache:original_cache[r['bank']]=parse_table(original.read(r['bank']))
            ot=original_cache[r['bank']]
            if not ot or ot.strings.get(key)!=r['source']:raise ValueError('Catalog source mismatch')
            if not t or key not in t.strings:raise ValueError('Baseline field missing')
            if t.strings[key]==r['translation']:continue
            errors=technical_errors(r['source'],r['translation'])
            if errors:raise ValueError(f'{r["id"]}: {errors}')
            changes[r['bank']][(r['row'],r['field'])]=r['translation']
    idx=bytearray(source.index)
    repaired=[]
    for i,e in enumerate(source.entries):
        actual=source.physical_size(i)
        if actual>e.stored:
            struct.pack_into('<Q',idx,32*i+16,actual)
            repaired.append(i)
    binpath=target/'LD_C0_R.BIN'
    with binpath.open('wb') as f:
        f.write(source.data)
        for bank,strings in sorted(changes.items()):
            data=source.read(bank);table=parse_table(data)
            rebuilt=rebuild_table(data,table,strings)
            encoded=compress(rebuilt)
            f.write(bytes(align(f.tell(),256)-f.tell()))
            offset=f.tell();f.write(encoded)
            struct.pack_into('<QQQQ',idx,32*bank,offset,len(rebuilt),len(encoded),1)
    (target/'LI_C0_R.IDX').write_bytes(idx)
    built=Archive(target)
    # Preserve every upstream payload, including banks outside our catalog.
    if built.data[:len(source.data)]!=source.data:raise ValueError('Original prefix altered')
    for i in range(len(source.entries)):
        built.read(i)  # Strict decoding: no stale stored-size tolerance in output.
        if i not in changes:
            if idx[i*32:i*32+32]!=built.index[i*32:i*32+32]:raise ValueError('Untouched IDX record changed')
        else:
            data=built.read(i);t=parse_table(data);orig=parse_table(source.read(i))
            if t is None:raise ValueError('Generated table parse failure')
            for key,text in orig.strings.items():
                if t.strings[key]!=changes[i].get(key,text):raise ValueError('Generated string mismatch')
            # Compare header, row metadata, old pool and padding; only pointers differ.
            old=source.read(i);normalized=bytearray(data[:len(old)])
            for row,field in changes[i]:
                p=64+row*orig.stride+field;normalized[p:p+4]=old[p:p+4]
            if normalized!=old:raise ValueError('Opaque table bytes changed')
    result=dict(passed=True,modified_banks=len(changes),modified_fields=sum(map(len,changes.values())),
                repaired_stored_size_records=repaired,
                untouched_records=len(source.entries)-len(set(changes)|set(repaired)),baseline_bin_prefix_preserved=True,
                baseline_sha256=hashes,
                source_sha256={n:sha(Path(cfg['source'])/n) for n in manifest['source_files']},
                output_sha256={n:sha(target/n) for n in manifest['source_files']},emulator_test='not_run')
    dump(REPORTS/'build_validation.json',result)
    print(json.dumps({**result,'repaired_stored_size_records':len(repaired)}))

def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True)
    ex=sub.add_parser('extract');ex.add_argument('--source',required=True);ex.add_argument('--output',required=True);ex.set_defaults(func=extract)
    cf=sub.add_parser('configure');cf.add_argument('--source',required=True);cf.set_defaults(func=configure)
    qu=sub.add_parser('queue');qu.add_argument('--bank',type=int);qu.add_argument('--limit',type=int,default=50);qu.add_argument('--output',default=str(ROOT/'local/next_batch.jsonl'));qu.set_defaults(func=queue)
    sub.add_parser('report').set_defaults(func=report)
    sub.add_parser('reuse').set_defaults(func=reuse)
    ap=sub.add_parser('apply');ap.add_argument('file');ap.set_defaults(func=apply_batch)
    rv=sub.add_parser('review');rv.add_argument('--import-file');rv.set_defaults(func=review)
    bd=sub.add_parser('build');bd.add_argument('--output',default=str(ROOT/'build/Pokopia-PTBR-655360/romfs'));bd.add_argument('--baseline',default=str(ROOT/'romfs'));bd.set_defaults(func=build)
    args=p.parse_args();args.func(args)

if __name__=='__main__':main()
