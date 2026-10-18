import sys
d=open(sys.argv[1],'rb').read()
x0201="｡｢｣､･ｦｧｨｩｪｫｬｭｮｯｰｱｲｳｴｵｶｷｸｹｺｻｼｽｾｿﾀﾁﾂﾃﾄﾅﾆﾇﾈﾉﾊﾋﾌﾍﾎﾏﾐﾑﾒﾓﾔﾕﾖﾗﾘﾙﾚﾛﾜﾝﾞﾟ"
hira="。「」、・をぁぃぅぇぉゃゅょっーあいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわん゛゜"
kata="。「」、・ヲァィゥェォャュョッーアイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワン゛゜"
T={}
for i,c in enumerate(hira): T[0xA1+i]=c
for i,c in enumerate(kata): T[0x61+i]=c   # guess katakana at 0x61..
for i in range(0x20,0x5f): T.setdefault(i,chr(i))
a=int(sys.argv[2],16); n=int(sys.argv[3],16) if len(sys.argv)>3 else 0x100
out=''
for b in d[a:a+n]:
  out+=T.get(b,'{%02X}'%b)
print(out)
