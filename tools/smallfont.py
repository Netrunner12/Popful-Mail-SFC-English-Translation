# small 8x8 menu font: digits 10-19, ':'=1A, space 20?, A-Z = 21-3A, katakana 80+ (JIS X0201 order - 0x26)
SM = {}
for d in range(10): SM[0x10 + d] = str(d)
SM[0x1A] = ':'
for i, c in enumerate('ABCDEFGHIJKLMNOPQRSTUVWXYZ'): SM[0x21 + i] = c
SM[0x00] = ' '; SM[0x20] = '_'
kana = 'ヲァィゥェォャュョッーアイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワン゛゜'
# JIS X0201 A6..DF minus the long-vowel at B0 which this font places at B9
order = 'ヲァィゥェォャュョッアイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワン゛゜ー'
for i, c in enumerate(order): SM[0x80 + i] = c
def dec(b):
    return ''.join(SM.get(x, '<%02X>' % x) for x in b)
