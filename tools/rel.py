import sys
d=open(sys.argv[1],'rb').read()
plain="あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをん"
sj="ぁあぃいぅうぇえぉおかがきぎくぐけげこごさざしじすずせぜそぞただちぢっつづてでとどなにぬねのはばぱひびぴふぶぷへべぺほぼぽまみむめもゃやゅゆょよらりるれろゎわゐゑをん"
orders={'plain':plain,'sjis':sj}
words=["わたし","あなた","これは","なにも","ありません","います","ない","なんて","しまった","よろしく","ところ","ませんか","ほしい"]
kata=lambda s:''.join(chr(ord(c)+0x60) for c in s)
words+= [ "めいる"]
for on,o in orders.items():
  for w in words:
    if any(c not in o for c in w): continue
    idx=[o.index(c) for c in w]; diffs=[idx[i+1]-idx[i] for i in range(len(idx)-1)]
    for width in (1,2):
      hits=[]
      n=len(w)
      for p in range(0,len(d)-n*width):
        vals=[d[p+i*width] if width==1 else d[p+i*width]|(d[p+i*width+1]<<8) for i in range(n)]
        if all(vals[i+1]-vals[i]==diffs[i] for i in range(n-1)):
          if len(set(vals))>1 or n==1: hits.append((p,vals[0]-idx[0]))
      if 0<len(hits)<200:
        from collections import Counter
        print(on,w,width,len(hits),Counter(h[1] for h in hits).most_common(3), [hex(h[0]) for h in hits[:5]])
