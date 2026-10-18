"""English title logo: screen capture of the logo (english_logo_source.png, 256x224, logo on screen rows
31-110) -> patch/logo_en.npy, a 256x80 picture in the title screen's own palette indices
(title_palette.json).  The capture is grouped into its colours (k-means), each group is given the nearest
palette colour, and compression speckle is cleaned up.  Writes previews to out/logo_preview_*.png.

    python3 logo/convert.py
"""
from PIL import Image
import numpy as np, json
from scipy.cluster.vq import kmeans2
from scipy import ndimage
import os
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))   # repo root
pal={int(k):tuple(v) for k,v in json.load(open('logo/title_palette.json')).items()}
used=[i for i in range(17,32)]+[i for i in range(97,112)]
P5={i:np.array(pal[i])//8 for i in used}
ref=np.array(Image.open('logo/english_logo_source.png').convert('RGB')).astype(float)[31:111]
r=ref*31/255; X=r.reshape(-1,3)
C,l=kmeans2(X,24,minit='++',seed=1,iter=50); l=l.reshape(80,256)
idx=np.zeros((80,256),np.uint8)
for k,c in enumerate(C):
    m=l==k
    if c[2]>c[0]+c[1]+8 and c[0]<6:            # background blue (and its compression noise)
        continue
    if c[0]<16 and c[1]<4 and c[2]>5:           # blend of dark outline and background: decide per pixel
        px=r[m]; d_bg=((px-[0,0,17.5])**2).sum(1); d_ol=((px-P5[17])**2).sum(1)
        idx[m]=np.where(d_ol<d_bg,17,0); continue
    best=min(used,key=lambda j:((P5[j]-c)**2).sum())
    idx[m]=best
# the darkest red belongs only to the hat; elsewhere it is the outline seen through compression
hat=np.zeros((80,256),bool); hat[0:32,158:192]=True
idx[(idx==20)&~hat]=17
idx[(idx==18)&~hat]=17
# pink vs purple group for identical colours: keep whichever group the letter around it uses (left/right of the sword)
twin={17:97,21:110,22:102,23:103,24:104,26:106,27:107}
xs=np.arange(256)[None,:].repeat(80,0)
for a,b in twin.items(): idx[(idx==a)&(xs<150)]=b
a=idx.copy()
for it in range(2):
    p=np.pad(a,1,mode='edge'); n4=[p[:-2,1:-1],p[2:,1:-1],p[1:-1,:-2],p[1:-1,2:]]
    iso=np.all([a!=n for n in n4],0)
    n8=np.stack([p[i:i+80,j:j+256] for i in range(3) for j in range(3) if (i,j)!=(1,1)],-1)
    for y,x in zip(*np.where(iso)):
        v,c=np.unique(n8[y,x],return_counts=True)
        if c.max()>=5: a[y,x]=v[c.argmax()]
    print('cleaned',iso.sum())
lab,nl=ndimage.label(a>0); sz=ndimage.sum(a>0,lab,range(1,nl+1))
a[np.isin(lab,[i+1 for i in range(nl) if sz[i]<20])]=0
np.save('patch/logo_en.npy',a)
t=set(bytes(a[y*8:y*8+8,x*8:x*8+8].ravel()) for y in range(10) for x in range(32)); print('tiles',len(t))
def rgb(z):
    o=np.zeros(z.shape+(3,),np.uint8); o[:]=(0,0,136)
    for v in np.unique(z):
        if v: o[z==v]=pal[int(v)]
    return o
for name,x0 in (('a',0),('b',128)):
    im=np.concatenate([ref.astype(np.uint8)[:,x0:x0+128],np.full((80,2,3),255,np.uint8),rgb(a)[:,x0:x0+128]],1)
    os.makedirs('out',exist_ok=True); Image.fromarray(im).resize((im.shape[1]*8,640),Image.NEAREST).save('out/logo_preview_%s.png'%name)
