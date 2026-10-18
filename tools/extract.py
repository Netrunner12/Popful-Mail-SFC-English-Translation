import sys,pickle; sys.path.insert(0,'tools')
from pmlz import decompress
exec(open('tools/decode.py',encoding='utf-8').read())
TEXTCHARS=set("あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをんがぎぐげござじずぜぞだぢづでどばびぶべぼぱぴぷぺぽぁぃぅぇぉゃゅょっアイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲンガギグゲゴザジズゼゾダヂヅデドバビブベボパピプペポヴァィゥェォャュョッー―～、。・「」！？（），　０１２３４５６７８９")
KANJI=set(c for c in list(S.values())+list(D.values()) if len(c)==1 and '一'<=c<='鿿' or c=='々')
TEXTCHARS|=KANJI; TEXTCHARS|={'シス','テム'}
def messages(o):
  toks=list(tokens(o))
  res=[]; i=0; n=len(toks)
  # end markers: cmd FF or 0C
  ends=[k for k,(p,(t,v)) in enumerate(toks) if t=='cmd' and v in (0xFF,0x0C)]
  prev_end=-1
  for e in ends:
    k=e-1; inner=0
    while k>prev_end:
      p,(t,v)=toks[k]
      if t=='chr' and v in TEXTCHARS: k-=1; inner+=1; continue
      if t=='cmd' and v in (0x0B,0x0C,0xFF) : k-=1; continue
      if t=='cmd': k-=1; continue
      break
    start=k+1
    # trim leading chars that are unlikely openers
    while start<e and toks[start][1][0]=='chr' and toks[start][1][1] in '、。ー―～　）':
      start+=1
    if inner>=2:
      res.append((toks[start][0], toks[e][0]+2, o[toks[start][0]:toks[e][0]+2]))
    prev_end=e
  return res
