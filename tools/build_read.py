import os
import sys,pickle,json; sys.path.insert(0,'tools')
from pmlz import decompress
exec(open('tools/extract.py',encoding='utf-8').read())
exec(open('tools/tok2.py',encoding='utf-8').read())
rom=open(os.environ.get('PM_ROM') or 'rom/Popful Mail (Japan).sfc','rb').read()
streams=pickle.load(open('out/streams.pkl','rb'))
txt=[s for s in streams if s[6]>5]
rows=[];lines=[]
for s in txt:
  o,_=decompress(rom,s[2])
  lines.append('### BANK %02X #%d'%(s[0],s[1]))
  for a,b,m in messages(o):
    mid='M%04d'%(len(rows)+1)
    t=render(o,a,b)
    rows.append({'id':mid,'stream':'%06X'%s[2],'bank':s[0],'idx':s[1],'off':a,'end':b,'jp':t})
    lines.append(mid+' '+t)
json.dump(rows,open('out/messages2.json','w',encoding='utf-8'),ensure_ascii=False,indent=0)
open('out/read2.txt','w',encoding='utf-8').write('\n'.join(lines))
print(len(rows))
