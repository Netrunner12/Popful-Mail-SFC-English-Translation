import sys
from PIL import Image
import numpy as np
d=open(sys.argv[1],'rb').read()
mode=sys.argv[2]; start=int(sys.argv[3],16); length=int(sys.argv[4],16); cols=int(sys.argv[5]); out=sys.argv[6]
scale=int(sys.argv[7]) if len(sys.argv)>7 else 1
tiles=[]
if mode=='1bpp':
  for a in range(start,start+length,8):
    t=np.array([[ (d[a+r]>>(7-c))&1 for c in range(8)] for r in range(8)])*3; tiles.append(t)
elif mode=='2bpp':
  for a in range(start,start+length,16):
    t=np.array([[ ((d[a+2*r]>>(7-c))&1) | (((d[a+2*r+1]>>(7-c))&1)<<1) for c in range(8)] for r in range(8)]); tiles.append(t)
elif mode=='4bpp':
  for a in range(start,start+length,32):
    t=np.array([[ ((d[a+2*r]>>(7-c))&1) | (((d[a+2*r+1]>>(7-c))&1)<<1) | (((d[a+16+2*r]>>(7-c))&1)<<2)| (((d[a+16+2*r+1]>>(7-c))&1)<<3) for c in range(8)] for r in range(8)])//5; tiles.append(t)
rows=(len(tiles)+cols-1)//cols
img=np.zeros((rows*8,cols*8),dtype=np.uint8)
for i,t in enumerate(tiles):
  r,c=divmod(i,cols); img[r*8:r*8+8,c*8:c*8+8]=t*85
im=Image.fromarray(255-img)
if scale>1: im=im.resize((im.width*scale,im.height*scale),Image.NEAREST)
im.save(out)
