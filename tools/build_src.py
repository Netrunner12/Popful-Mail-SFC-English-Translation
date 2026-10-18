import sys,os,pickle,json,re; sys.path.insert(0,'tools')
from pmlz import decompress
exec(open('tools/extract.py',encoding='utf-8').read())
exec(open('tools/tok2.py',encoding='utf-8').read())
def render_src(o,a,b):
  s=''
  for p,k,v in tokenize(o,a,b):
    if k=='chr': s+=v
    elif k=='name': s+='〔'+v+'〕'
    else:
      c,args=v
      if c==0x0B: s+='⏎'
      elif c==0x0C: s+='▼'
      elif c==0xFF: s+='■'
      elif c==0x08: s+='【メイル】'
      elif c==0x09: s+='【タット】'
      elif c==0x0A: s+='【ガウ】'
      elif c==0x04: s+='【ナレ】'
      elif c==0x13: s+='⏸'+('' if args==b'\x00' else str(args[0]) if args else '')
      elif c==0x01: s+='«'
      elif c==0x02: s+='‹'
      elif c==0x00: s+='»'
      elif c==0x0E:
        t=substr(o,args[0]|args[1]<<8) if len(args)==2 else None
        s+='{%s}'%t if t else '{0E:%s}'%args.hex()
      else: s+='<%02X%s>'%(c,(':'+args.hex()) if args else '')
  return s
rom=open(os.environ.get('PM_ROM') or 'rom/Popful Mail (Japan).sfc','rb').read()
streams=pickle.load(open('out/streams.pkl','rb'))
txt=[s for s in streams if s[6]>5]
rows=[]; names={}
KANA=re.compile(r'[ぁ-んァ-ヶー]')
for s in txt:
  o,_=decompress(rom,s[2])
  key='%02X#%d'%(s[0],s[1])
  for a,b,m in messages(o):
    mid='M%04d'%(len(rows)+1)
    t=render_src(o,a,b)
    defs=[]
    if '<17>' in t:
      parts=t.split('<17>')
      defs=[re.findall(r'〔([^〕]*)〕',p)[-1] if re.findall(r'〔([^〕]*)〕',p) else p for p in parts[:-1]]
      names.setdefault(key,[])
      for d_ in defs:
        if d_ not in names[key]: names[key].append(d_)
      t=parts[-1]
    # junk score: share of chars that are plausible text
    body=re.sub(r'<[^>]*>|\{[^}]*\}|〔[^〕]*〕|【[^】]*】','',t)
    good=len(KANA.findall(body)); tot=max(1,len(body))
    rows.append({'id':mid,'stream':'%06X'%s[2],'sk':key,'off':'%04X'%a,'jp':t,'junk': (good/tot<0.45 and '⏎' not in t) })
json.dump(rows,open('out/src.json','w',encoding='utf-8'),ensure_ascii=False,indent=0)
json.dump(names,open('out/namedefs.json','w',encoding='utf-8'),ensure_ascii=False,indent=1)
j=[r for r in rows if r['junk']]
print(len(rows),'rows',len(j),'junk')
for r in j: print(r['id'],r['jp'][:70])
