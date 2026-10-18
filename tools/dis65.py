"""Minimal 65816 disassembler (tracks REP/SEP for M and X widths).
usage: dis.py rom.sfc BB:AAAA count [m8 x8]   or import dis(buf, base_addr, n, m, x)"""
import sys
M = 'imm_m'; X = 'imm_x'
OPS = {}
def op(code, name, mode): OPS[code] = (name, mode)
tbl = """
00 BRK imm8|01 ORA dpxi|02 COP imm8|03 ORA sr|04 TSB dp|05 ORA dp|06 ASL dp|07 ORA dpil|08 PHP -|09 ORA imm_m|0A ASL acc|0B PHD -|0C TSB abs|0D ORA abs|0E ASL abs|0F ORA long
10 BPL rel|11 ORA dpiy|12 ORA dpi|13 ORA sriy|14 TRB dp|15 ORA dpx|16 ASL dpx|17 ORA dpily|18 CLC -|19 ORA absy|1A INC acc|1B TCS -|1C TRB abs|1D ORA absx|1E ASL absx|1F ORA longx
20 JSR abs|21 AND dpxi|22 JSL long|23 AND sr|24 BIT dp|25 AND dp|26 ROL dp|27 AND dpil|28 PLP -|29 AND imm_m|2A ROL acc|2B PLD -|2C BIT abs|2D AND abs|2E ROL abs|2F AND long
30 BMI rel|31 AND dpiy|32 AND dpi|33 AND sriy|34 BIT dpx|35 AND dpx|36 ROL dpx|37 AND dpily|38 SEC -|39 AND absy|3A DEC acc|3B TSC -|3C BIT absx|3D AND absx|3E ROL absx|3F AND longx
40 RTI -|41 EOR dpxi|42 WDM imm8|43 EOR sr|44 MVP mv|45 EOR dp|46 LSR dp|47 EOR dpil|48 PHA -|49 EOR imm_m|4A LSR acc|4B PHK -|4C JMP abs|4D EOR abs|4E LSR abs|4F EOR long
50 BVC rel|51 EOR dpiy|52 EOR dpi|53 EOR sriy|54 MVN mv|55 EOR dpx|56 LSR dpx|57 EOR dpily|58 CLI -|59 EOR absy|5A PHY -|5B TCD -|5C JML long|5D EOR absx|5E LSR absx|5F EOR longx
60 RTS -|61 ADC dpxi|62 PER rell|63 ADC sr|64 STZ dp|65 ADC dp|66 ROR dp|67 ADC dpil|68 PLA -|69 ADC imm_m|6A ROR acc|6B RTL -|6C JMP absi|6D ADC abs|6E ROR abs|6F ADC long
70 BVS rel|71 ADC dpiy|72 ADC dpi|73 ADC sriy|74 STZ dpx|75 ADC dpx|76 ROR dpx|77 ADC dpily|78 SEI -|79 ADC absy|7A PLY -|7B TDC -|7C JMP absxi|7D ADC absx|7E ROR absx|7F ADC longx
80 BRA rel|81 STA dpxi|82 BRL rell|83 STA sr|84 STY dp|85 STA dp|86 STX dp|87 STA dpil|88 DEY -|89 BIT imm_m|8A TXA -|8B PHB -|8C STY abs|8D STA abs|8E STX abs|8F STA long
90 BCC rel|91 STA dpiy|92 STA dpi|93 STA sriy|94 STY dpx|95 STA dpx|96 STX dpy|97 STA dpily|98 TYA -|99 STA absy|9A TXS -|9B TXY -|9C STZ abs|9D STA absx|9E STZ absx|9F STA longx
A0 LDY imm_x|A1 LDA dpxi|A2 LDX imm_x|A3 LDA sr|A4 LDY dp|A5 LDA dp|A6 LDX dp|A7 LDA dpil|A8 TAY -|A9 LDA imm_m|AA TAX -|AB PLB -|AC LDY abs|AD LDA abs|AE LDX abs|AF LDA long
B0 BCS rel|B1 LDA dpiy|B2 LDA dpi|B3 LDA sriy|B4 LDY dpx|B5 LDA dpx|B6 LDX dpy|B7 LDA dpily|B8 CLV -|B9 LDA absy|BA TSX -|BB TYX -|BC LDY absx|BD LDA absx|BE LDX absy|BF LDA longx
C0 CPY imm_x|C1 CMP dpxi|C2 REP imm8|C3 CMP sr|C4 CPY dp|C5 CMP dp|C6 DEC dp|C7 CMP dpil|C8 INY -|C9 CMP imm_m|CA DEX -|CB WAI -|CC CPY abs|CD CMP abs|CE DEC abs|CF CMP long
D0 BNE rel|D1 CMP dpiy|D2 CMP dpi|D3 CMP sriy|D4 PEI dp|D5 CMP dpx|D6 DEC dpx|D7 CMP dpily|D8 CLD -|D9 CMP absy|DA PHX -|DB STP -|DC JML absil|DD CMP absx|DE DEC absx|DF CMP longx
E0 CPX imm_x|E1 SBC dpxi|E2 SEP imm8|E3 SBC sr|E4 CPX dp|E5 SBC dp|E6 INC dp|E7 SBC dpil|E8 INX -|E9 SBC imm_m|EA NOP -|EB XBA -|EC CPX abs|ED SBC abs|EE INC abs|EF SBC long
F0 BEQ rel|F1 SBC dpiy|F2 SBC dpi|F3 SBC sriy|F4 PEA abs|F5 SBC dpx|F6 INC dpx|F7 SBC dpily|F8 SED -|F9 SBC absy|FA PLX -|FB XCE -|FC JSR absxi|FD SBC absx|FE INC absx|FF SBC longx
"""
for line in tbl.strip().splitlines():
    for ent in line.split('|'):
        c, n, m = ent.split(); op(int(c, 16), n, m)
SIZE = {'-': 0, 'acc': 0, 'imm8': 1, 'dp': 1, 'dpx': 1, 'dpy': 1, 'dpi': 1, 'dpxi': 1, 'dpiy': 1, 'dpil': 1, 'dpily': 1,
        'sr': 1, 'sriy': 1, 'rel': 1, 'abs': 2, 'absx': 2, 'absy': 2, 'absi': 2, 'absxi': 2, 'absil': 2, 'rell': 2,
        'mv': 2, 'long': 3, 'longx': 3}
FMT = {'-': '', 'acc': 'A', 'imm8': '#$%02X', 'dp': '$%02X', 'dpx': '$%02X,x', 'dpy': '$%02X,y', 'dpi': '($%02X)',
       'dpxi': '($%02X,x)', 'dpiy': '($%02X),y', 'dpil': '[$%02X]', 'dpily': '[$%02X],y', 'sr': '$%02X,s',
       'sriy': '($%02X,s),y', 'abs': '$%04X', 'absx': '$%04X,x', 'absy': '$%04X,y', 'absi': '($%04X)',
       'absxi': '($%04X,x)', 'absil': '[$%04X]', 'long': '$%06X', 'longx': '$%06X,x'}

def dis(buf, addr, n, m=True, x=True, out=None):
    """buf indexed from 0 == addr. m/x True = 8-bit."""
    lines = []; i = 0
    while i < len(buf) and len(lines) < n:
        c = buf[i]; name, mode = OPS[c]
        if mode == 'imm_m': sz = 1 if m else 2
        elif mode == 'imm_x': sz = 1 if x else 2
        else: sz = SIZE[mode]
        arg = int.from_bytes(buf[i+1:i+1+sz], 'little')
        a = addr + i
        if mode in ('imm_m', 'imm_x'): s = ('#$%02X' if sz == 1 else '#$%04X') % arg
        elif mode == 'rel': s = '$%04X' % ((a + 2 + (arg - 256 if arg > 127 else arg)) & 0xFFFF)
        elif mode == 'rell': s = '$%04X' % ((a + 3 + (arg - 65536 if arg > 32767 else arg)) & 0xFFFF)
        elif mode == 'mv': s = '$%02X,$%02X' % (arg & 0xFF, arg >> 8)
        else: s = FMT[mode] % arg if '%' in FMT[mode] else FMT[mode]
        if name == 'REP': m = m and not (arg & 0x20); x = x and not (arg & 0x10)
        if name == 'SEP': m = m or bool(arg & 0x20); x = x or bool(arg & 0x10)
        lines.append('%02X:%04X  %-12s %s %s' % (a >> 16, a & 0xFFFF, buf[i:i+1+sz].hex(' '), name, s))
        i += 1 + sz
    return lines

def lorom(a): return ((a >> 16) & 0x7F) * 0x8000 + (a & 0x7FFF)

if __name__ == '__main__':
    rom = open(sys.argv[1], 'rb').read()
    b, a = sys.argv[2].split(':'); addr = int(b, 16) << 16 | int(a, 16)
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 40
    m = (sys.argv[4] != 'm16') if len(sys.argv) > 4 else True
    x = (sys.argv[5] != 'x16') if len(sys.argv) > 5 else True
    o = lorom(addr)
    print('\n'.join(dis(rom[o:o + 4 * n], addr, n, m, x)))
