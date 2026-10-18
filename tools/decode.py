import sys; sys.path.insert(0,'tools')
exec(open('tools/table.py',encoding='utf-8').read())
def tokens(b):
  i=0
  while i<len(b):
    x=b[i]
    if x==0x20 and i+1<len(b): yield i,('cmd',b[i+1]); i+=2
    elif x==0x21 and i+1<len(b): yield i,('chr',D.get(b[i+1],'{21%02X}'%b[i+1])); i+=2
    else: yield i,('chr',S.get(x,'{%02X}'%x)); i+=1
def dec(b):
  o=''
  for i,(t,v) in tokens(b):
    if t=='cmd': o+={0x0B:'⏎',0x0C:'▼',0xFF:'■'}.get(v,'<%02X>'%v)
    else: o+=v
  return o
