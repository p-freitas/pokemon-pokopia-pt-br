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
TRANSLATIONS = ROOT/'translations/655360'
REPORTS = ROOT/'reports/655360'
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

def scan(archive):
    tables = {}
    for i in range(len(archive.entries)):
        data = archive.read(i)
        table = parse_table(data)
        if table:
            tables[i] = table
    # Observed contiguous localization region, homogeneous runs of nine languages.
    # Require Japanese and Chinese content as independent language anchors; empty
    # groups need no catalog entries and are deliberately omitted.
    groups = []
    occupied = set()
    cjk = re.compile('[\u3040-\u30ff\u3400-\u9fff]')
    for i, t in tables.items():
        if i in occupied:
            continue
        if not all(i+j in tables and (tables[i+j].count,tables[i+j].stride)==(t.count,t.stride) for j in range(9)):
            continue
        if not any(cjk.search(s) for s in t.strings.values()):
            continue
        if not any(cjk.search(s) for s in tables[i+8].strings.values()):
            continue
        groups.append(i)
        occupied.update(range(i,i+9))
    return tables,groups

def foreign_key(tables,g,key):
    # Eight independent original-language strings anchor the row. No raw offsets
    # or ordinal equivalence between different game versions is assumed.
    values = [tables[g+j].strings[key] for j in (0,2,3,4,5,6,7,8)]
    return hashlib.sha256(json.dumps(values,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()

def extract(args):
    if CAT.exists():
        raise SystemExit('Catalog already exists; use existing checkpoint, do not overwrite review work.')
    current = Archive(args.source)
    upstream = Archive(ROOT/'romfs',tolerate_legacy_stored=True)
    tables, groups = scan(current)
    old_tables,old_groups = scan(upstream)
    candidates = collections.defaultdict(set)
    provenance = collections.defaultdict(list)
    for g in old_groups:
        for key,text in old_tables[g+1].strings.items():
            if text:
                fk = foreign_key(old_tables,g,key)
                candidates[fk].add(text)
                provenance[fk].append([g+1,*key])
    catalog = []
    for g in groups:
        for (row,field),source in tables[g+1].strings.items():
            if not source:
                continue
            key = foreign_key(tables,g,(row,field))
            values = candidates.get(key,set())
            rec = dict(id=f'b{g+1:05d}:r{row:05d}:f{field:02d}',bank=g+1,row=row,field=field,
                       source=source,translation='',status='pending_translation',origin='',foreign_key=key)
            if len(values)==1:
                target = next(iter(values))
                errors = technical_errors(source,target)
                if errors:
                    rec.update(status='needs_attention',candidate_translation=target,issues=errors,origin='upstream_rejected')
                else:
                    rec.update(translation=target,status='translated_unreviewed',origin='upstream' if source!=target else 'upstream_unchanged')
                rec['upstream_locations'] = provenance[key]
            elif len(values)>1:
                rec.update(status='needs_attention',issues=['ambiguous_upstream_translation'])
            catalog.append(rec)
    (ROOT/'local').mkdir(exist_ok=True)
    dump(ROOT/'local/config.json',{'source':str(Path(args.source).resolve()),'installed':str(Path(args.installed).resolve()),'exefs':str(Path(args.exefs).resolve())})
    manifest = {'source_files':{},'installed_files':{},'upstream_files':{},'entries':len(current.entries),'upstream_entries':len(upstream.entries),
                'v2_tables':len(tables),'localized_groups':len(groups),'upstream_localized_groups':len(old_groups),
                'version_label_supplied_by_user':'2.0.1a (655360)','version_label_independently_verified':False}
    for label,root in [('source',args.source),('installed',args.installed),('upstream',ROOT/'romfs')]:
        for name in ['LD_C0_R.BIN','LI_C0_R.IDX']:
            p=Path(root)/name
            manifest[label+'_files'][name]={'sha256':sha(p),'bytes':p.stat().st_size}
    if manifest['source_files']!=manifest['installed_files']:
        raise ValueError('Backup differs from installed pair; inspect before proceeding')
    main = (Path(args.exefs)/'main').read_bytes()
    npdm = (Path(args.exefs)/'main.npdm').read_bytes()
    pos=npdm.index(b'ACI0')
    manifest.update(main_sha256=sha(Path(args.exefs)/'main'),main_build_id=main[64:96].hex().upper(),
                    title_id=f'{struct.unpack_from("<Q",npdm,pos+16)[0]:016X}')
    dump(REPORTS/'source_manifest.json',manifest)
    dump(REPORTS/'banks.json',[{'bank':g+1,'count':tables[g+1].count,'stride':tables[g+1].stride,
        'nonempty':sum(bool(s) for s in tables[g+1].strings.values()),'sample':next((s[:100] for s in tables[g+1].strings.values() if s),'')} for g in groups])
    save_jsonl(CAT,catalog)
    report(None)

def report(args):
    rows = read_jsonl(CAT)
    counts=collections.Counter(r['status'] for r in rows)
    origins=collections.Counter(r['origin'] for r in rows)
    sources=collections.Counter(r['source'] for r in rows)
    result = dict(found_nonempty_fields=len(rows),statuses=dict(counts),origins=dict(origins),
                  changed_translations=sum(bool(r['translation']) and r['translation']!=r['source'] for r in rows),
                  preserved_unchanged=sum(r['origin']=='upstream_unchanged' for r in rows),
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
                if item['translation']:
                    errors=technical_errors(r['source'],item['translation'])
                    if errors:raise ValueError(f'{r["id"]}: {errors}')
                elif item['status'] in ('reviewed','translated_unreviewed'):
                    raise ValueError('Translated status requires text')
                changed=item['translation']!=r['translation'] or item['status']!=r['status']
                r.update(translation=item['translation'],status=item['status'])
                if changed:r['origin']='manual_csv'
        save_jsonl(CAT,rows);report(None)
    else:
        with (TRANSLATIONS/'review.csv').open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fields,extrasaction='ignore');w.writeheader();w.writerows(rows)

def build(args):
    cfg=config();source=Archive(cfg['source'])
    manifest=json.loads((REPORTS/'source_manifest.json').read_text(encoding='utf-8'))
    for name,info in manifest['source_files'].items():
        if sha(Path(cfg['source'])/name)!=info['sha256']:raise ValueError('Source hash changed')
    target=Path(args.output).resolve()
    source_root=source.root.resolve()
    if target==source_root or source_root in target.parents or target in source_root.parents:
        raise ValueError('Output must be isolated from source')
    # Never allow output in the source tree, game, upstream final binary tree or emulator.
    allowed=(ROOT/'build').resolve()
    if target!=allowed and allowed not in target.parents:
        raise ValueError('Build output must be under project/build')
    target.mkdir(parents=True,exist_ok=True)
    rows=read_jsonl(CAT);changes=collections.defaultdict(dict);table_cache={}
    for r in rows:
        if r['translation'] and r['status'] in ('translated_unreviewed','reviewed') and r['translation']!=r['source']:
            errors=technical_errors(r['source'],r['translation'])
            if errors:raise ValueError(f'{r["id"]}: {errors}')
            if r['bank'] not in table_cache:table_cache[r['bank']]=parse_table(source.read(r['bank']))
            t=table_cache[r['bank']]
            if not t or t.strings.get((r['row'],r['field']))!=r['source']:raise ValueError('Catalog source mismatch')
            changes[r['bank']][(r['row'],r['field'])]=r['translation']
    idx=bytearray(source.index)
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
    # All untouched records and original BIN prefix must be byte-identical.
    if built.data[:len(source.data)]!=source.data:raise ValueError('Original prefix altered')
    for i in range(len(source.entries)):
        if i not in changes:
            if source.index[i*32:i*32+32]!=built.index[i*32:i*32+32]:raise ValueError('Untouched IDX record changed')
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
                untouched_records=len(source.entries)-len(changes),original_bin_prefix_preserved=True,
                source_sha256={n:sha(Path(cfg['source'])/n) for n in manifest['source_files']},
                output_sha256={n:sha(target/n) for n in manifest['source_files']},emulator_test='not_run')
    dump(REPORTS/'build_validation.json',result)
    print(json.dumps(result))

def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True)
    ex=sub.add_parser('extract');ex.add_argument('--source',required=True);ex.add_argument('--installed',required=True);ex.add_argument('--exefs',required=True);ex.set_defaults(func=extract)
    cf=sub.add_parser('configure');cf.add_argument('--source',required=True);cf.set_defaults(func=configure)
    qu=sub.add_parser('queue');qu.add_argument('--bank',type=int);qu.add_argument('--limit',type=int,default=50);qu.add_argument('--output',default=str(ROOT/'local/next_batch.jsonl'));qu.set_defaults(func=queue)
    sub.add_parser('report').set_defaults(func=report)
    sub.add_parser('reuse').set_defaults(func=reuse)
    ap=sub.add_parser('apply');ap.add_argument('file');ap.set_defaults(func=apply_batch)
    rv=sub.add_parser('review');rv.add_argument('--import-file');rv.set_defaults(func=review)
    bd=sub.add_parser('build');bd.add_argument('--output',default=str(ROOT/'build/Pokopia-PTBR-655360/romfs'));bd.set_defaults(func=build)
    args=p.parse_args();args.func(args)

if __name__=='__main__':main()
