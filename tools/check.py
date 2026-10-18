import json,re,glob,collections
rows=json.load(open('out/src.json',encoding='utf-8'))
en={}
dups=[]
for f in sorted(glob.glob('tr/en_*.tsv')):
  for line in open(f,encoding='utf-8'):
    line=line.rstrip('\n')
    if not line: continue
    k,v=line.split('\t',1)
    if k in en: dups.append(k)
    en[k]=v
ids=[r['id'] for r in rows]
missing=[i for i in ids if i not in en]; extra=[k for k in en if k not in ids]
print('rows',len(ids),'translated',len(en),'missing',missing[:20],'extra',extra[:5],'dups',dups[:5])
PORT={'【メイル】':'【Mail】','【タット】':'【Tatto】','【ガウ】':'【Gaw】','【ナレ】':'【NARR】'}
def sig(s,lang):
  s=s.lstrip('§')
  codes=re.findall(r'<[0-9A-F]{2}(?::[0-9a-f]+)?>',s)
  pages=[c for c in s if c in '▼■']
  port=re.findall(r'【[^】]*】',s)
  if lang=='jp': port=[PORT.get(p,p) for p in port]
  calls=len(re.findall(r'\{\[[^\]]*\]\}',s))
  labels=len(re.findall(r'〔[^〕]*〕',s))
  col=(s.count('«'),s.count('‹'),s.count('»'))
  return codes,pages,port,calls,labels,col
bad=[]
for r in rows:
  e=en.get(r['id'])
  if e is None or e=='=' or e.startswith('⟦KEEP⟧') or e.startswith('!MANUAL!'): continue
  a=sig(r['jp'],'jp'); b=sig(e,'en')
  names=['codes','pages','portraits','calls','labels','color']
  diff=[names[i] for i in range(6) if a[i]!=b[i]]
  if diff: bad.append((r['id'],diff,r['jp'][:60],e[:60]))
print(len(bad),'mismatches')
for x in bad[:80]: print(x)
