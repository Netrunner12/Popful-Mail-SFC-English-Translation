import sys; sys.path.insert(0,'tools')
exec(open('tools/table.py',encoding='utf-8').read())
ARGS={0x13:1,0x18:1,0x11:1,0x1C:4,0x1D:2,0x14:4,0x15:2,0x16:2,0x0E:2,0x0D:2}
BASE=0xC000
def tokenize(o, i0=0, i1=None):
  """yield (pos, kind, value) kinds: chr, cmd(code,args bytes), name(str)"""
  i=i0; i1=len(o) if i1 is None else i1
  while i<i1:
    x=o[i]
    if x==0x20 and i+1<len(o):
      c=o[i+1]
      if c==0x12:
        j=i+2; nm=''
        while j<len(o) and o[j]!=0x20:
          if o[j]==0x21: nm+=D.get(o[j+1],'?'); j+=2
          else: nm+=S.get(o[j],'?'); j+=1
        yield i,'name',nm; i=j+1; continue
      if c==0x10 and i+3<len(o):
        d=(o[i+2]|o[i+3]<<8)-BASE-(i+2)
        if d%2==0 and 2<=d<=8 and all(0<=(o[i+2+2*k]|o[i+3+2*k]<<8)-BASE<len(o) for k in range(d//2)):
          yield i,'cmd',(0x10,bytes(o[i+2:i+2+d])); i=i+2+d; continue
      if c==0x10:
        j=i+2; ptrs=[]
        while j+1<len(o) and o[j]!=0x20 and 0xC0<=o[j+1]<=0xDF and (o[j]|o[j+1]<<8)-BASE<len(o):
          ptrs.append(o[j]|o[j+1]<<8); j+=2
        if ptrs:
          n0=(ptrs[0]-BASE-(i+2))//2          # first variant normally starts right after the list
          if 1<=n0<=len(ptrs) and (ptrs[0]-BASE-(i+2))%2==0: j=i+2+2*n0
        yield i,'cmd',(0x10,bytes(o[i+2:j])); i=j; continue
      n=ARGS.get(c,0)
      yield i,'cmd',(c,bytes(o[i+2:i+2+n])); i+=2+n; continue
    if x==0x21 and i+1<len(o):
      yield i,'chr',D.get(o[i+1],'{21%02X}'%o[i+1]); i+=2; continue
    yield i,'chr',S.get(x,'{%02X}'%x); i+=1
def substr(o,ptr):
  """text of substring at ptr, up to 20 17 / 20 FF"""
  q=ptr-BASE
  if not (0<=q<len(o)): return None
  out=''
  for p,k,v in tokenize(o,q,min(len(o),q+80)):
    if k=='cmd' and v[0] in (0x17,0xFF,0x0C): break
    if k=='name': out+='['+v+']'
    elif k=='chr': out+=v
  return out
PORTRAIT={0x08:'メイル',0x09:'タット',0x0A:'ガウ'}
def render(o,a,b,resolve=True):
  s=''
  for p,k,v in tokenize(o,a,b):
    if k=='chr': s+=v
    elif k=='name': s+='【'+v+'】'
    else:
      c,args=v
      if c==0x0B: s+='⏎'
      elif c==0x0C: s+='▼'
      elif c==0xFF: s+='■'
      elif c in PORTRAIT: s+='【'+PORTRAIT[c]+'】'
      elif c==0x04: s+='【ナレ】'
      elif c==0x0E and resolve:
        t=substr(o,args[0]|args[1]<<8) if len(args)==2 else None
        s+='{%s}'%t if t else '{0E:%s}'%args.hex()
      elif c==0x13: s+='…' if True else ''
      elif c in (0x01,0x02,0x00): s+={0x01:'«',0x02:'‹',0x00:'»'}[c]
      else: s+='<%02X%s>'%(c,(':'+args.hex()) if args else '')
  return s
