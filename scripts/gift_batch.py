"""Explicit translation template for gifts, with names anchored to Pokémon tables."""
import re
from project import CAT,TRANSLATIONS,read_jsonl,save_jsonl

rows=read_jsonl(CAT)
names={r['source'] for r in rows if r['bank'] in (2261,4934)}
batch=[]
for r in rows:
    if r['status']!='pending_translation':continue
    m=re.fullmatch(r'(.+)’s (gift|gifts)',r['source'])
    if m and m[1] in names:
        batch.append({'id':r['id'],'source':r['source'],'translation':('presente de ' if m[2]=='gift' else 'presentes de ')+m[1]})
save_jsonl(TRANSLATIONS/'batch003_gifts.jsonl',batch)
print(f'{len(batch)} pending gift fields selected; official names preserved')
