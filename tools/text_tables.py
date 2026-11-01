"""Write six tables of all the game's text, Japanese next to the English, from your own copy of the ROM.

    python3 tools/text_tables.py

out/text_tables/1_world_map.csv     destination labels on the world map
                2_menus.csv         title, save lists, shops, status screen, item names, other menu text
                3_dialogue.csv      every message box, in story order
                4_scrolling_misc.csv  the Castle Alcazar story scroll and the title logo
                5_epilogue.csv      the ending epilogue
                6_credits.csv       the staff credits
                text_tables.xlsx    the same six tables as sheets (if openpyxl is installed)

Columns: ID, Japanese (decoded from your ROM), English (as the build inserts it), Context, Changes
(wording, pause and colour changes made at the project owner's request; centring and line breaks are
not listed).  The Japanese text is not stored in this repository; it is read from the ROM each time.
"""
import sys, os, re, csv, json
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, 'patch')); sys.path.insert(0, os.path.join(ROOT, 'tools'))
import prepare; prepare.main()
import pickle
from pmlz import decompress
exec(open('tools/extract.py', encoding='utf-8').read())
exec(open('tools/tok2.py', encoding='utf-8').read())
exec(open('tools/build_src.py', encoding='utf-8').read().split('rom=open')[0].split("exec(open('tools/tok2.py'")[1].split('\n', 1)[1])
import build as _build
JROM = open(_build.SRC, 'rb').read()
STR = {(s[0], s[1]): s for s in pickle.load(open('out/streams.pkl', 'rb'))}
def DEC(k): return bytes(decompress(JROM, STR[k][2])[0])
_SMNS = {}; exec(open('tools/smallfont.py').read(), _SMNS); smdec = _SMNS['dec']
import importlib, io, contextlib
with contextlib.redirect_stdout(io.StringIO()):
    dr = importlib.import_module('dryrun')
import special as SP
W = dr.wrapped
SRC = {r['id']: r for r in json.load(open('out/src.json', encoding='utf-8'))}
ORDER = [r['id'] for r in json.load(open('out/src.json', encoding='utf-8'))]

# ---------------------------------------------------------------- cleaning
def clean_en(t):
    t = t.replace('⟦KEEP⟧', '').lstrip('§')
    t = re.sub(r'<19>.{3}', '[N]', t)
    t = re.sub(r'<0D:[0-9a-f]+>', '\n\n(other hero:)\n', t)
    t = re.sub(r'<[0-9A-F]{2}(?::[0-9a-f]+)?>', '', t)
    t = re.sub(r'【\+?NARR】', '', t)
    t = re.sub(r'【\+?([^】]*)】', r'\1: ', t)
    t = re.sub(r'\{\[([^\]]*)\]\}', r'\1: ', t)
    t = re.sub(r'〔([^〕]*)〕', r'\1: ', t)
    t = re.sub(r'⏸\d?|⇥[+-]?|⟨w\d+⟩|¦|⏹', '', t)
    t = t.replace('⟪', '').replace('⟫', '').replace('«', '').replace('»', '').replace('‹', '')
    t = t.replace('◐◑', '(Blacky logo)')
    t = re.sub(r'[\u3001-\u303f\u3040-\u30fa\u30fc-\u30ff\u4e00-\u9fff\uff00-\uffef]', '', t)   # stray argument bytes (keep ・)
    t = t.replace('⏎', '\n').replace('▼', '\n\n').replace('▽', '\n\n').replace('■', '')
    t = '\n'.join(l.strip() for l in t.split('\n'))
    t = re.sub(r'\n{3,}', '\n\n', t).strip()
    return t

def clean_jp(t):
    t = re.sub(r'<19>.{3}', '[N]', t)
    t = re.sub(r'<0D:[0-9a-f]+>', '\n\n（別の主人公：）\n', t)
    t = re.sub(r'<[0-9A-F]{2}(?::[0-9a-f]+)?>', '', t)
    t = re.sub(r'【ナレ】', '', t)
    t = re.sub(r'【([^】]*)】', r'\1：', t)
    t = re.sub(r'\{\[([^\]]*)\]\}', r'\1：', t)
    t = re.sub(r'\{([^}]*)\}', r'\1', t)
    t = re.sub(r'〔([^〕]*)〕', r'\1：', t)
    t = re.sub(r'⏸\d?', '', t)
    t = t.replace('«', '').replace('»', '').replace('‹', '').replace('[EXIT]', '（終了）')
    t = t.replace('⏎', '\n').replace('▼', '\n\n').replace('■', '')
    t = '\n'.join(l.strip('　 ') if i else l.rstrip('　 ') for i, l in enumerate(t.split('\n')))
    t = re.sub(r'\n{3,}', '\n\n', t).strip()
    return t

CJK = r'[\u3001-\u303f\u3040-\u30fa\u30fc-\u30ff\u4e00-\u9fff\uff00-\uffef]+'
def jp_strip(jp, en_raw):
    if en_raw.startswith('⟦KEEP⟧'):
        m = re.search(r'<1A>|【|\{\[|〔', jp)
        if m: jp = jp[m.start():]
    body = re.sub(r'<[0-9A-F]{2}(?::[0-9a-f]+)?>|【[^】]*】|\{\[[^\]]*\]\}|〔[^〕]*〕|<19>.{3}', ' ', en_raw)
    for junk in re.findall(CJK, body):
        if junk in ('・', '―'): continue
        jp = jp.replace(junk, '', 1)
    return clean_jp(jp)

# ---------------------------------------------------------------- scene context (by message id)
SCENES = [
    (1, 33, 'Jungle - opening: Mail is woken by the man sorting gear on the ledge above'),
    (34, 53, 'Jungle elf village - villagers (Namo, Siana, the Marionette Gang raids)'),
    (54, 80, 'Jungle - Tatto and the Wood Golem; Mail meets Tatto'),
    (81, 110, 'Jungle - Material speaks to Tatto, then appears and escapes'),
    (111, 114, 'Jungle - signs and locked doors'),
    (115, 136, 'Jungle - Namo\'s trap; meeting Namo'),
    (137, 164, 'Jungle - Mail frees Tatto; he joins her'),
    (165, 201, 'Ancient Caves - Samina Village (beasties), Ryuke and the Sorceress, the broken ladder'),
    (202, 297, 'Ancient Caves - beastie villagers, Blacky\'s bombs, the locked door and the pickaxe'),
    (298, 373, 'Ancient Caves - beasties under Goruades; Gaw; the Thunder Dragon'),
    (374, 517, 'Ancient Caves - the Waterway Man, Ruti and the medicine errand'),
    (518, 555, 'Ancient Caves - Gaw lies injured after the Thunder Dragon'),
    (556, 587, 'Ancient Caves - Maril freed from the jail; Material\'s voice'),
    (588, 605, 'Ancient Caves - Mail in a cage; Blacky'),
    (606, 652, 'Ancient Caves - Maril and Tatto; Material appears and leaves'),
    (653, 789, 'Port Miine - tavern (Basso), townsfolk, Maice, the elf merchant, the Dwarf Medicine Man and his contest'),
    (790, 844, 'Gades Ruins - Blacky with Maril; cultists take Maril'),
    (845, 945, 'Gades Ruins - the rockslide, Namo, Blacky\'s bomb, the dwarf guards'),
    (946, 965, 'Gades Ruins - Udo and Maril'),
    (966, 1087, 'Gades Ruins - Udo, Marvela and the demon god Sajim; Material takes the holy sword'),
    (1088, 1118, 'Gades Ruins - the cultists and Marvela with Maril'),
    (1119, 1215, 'Gades Ruins - dwarf village (Udo, the Elder, villagers)'),
    (1216, 1298, 'Hagel Island - Namo and Nuts Cracker; Rip turned against them'),
    (1299, 1454, 'Hagel Island - Maril; the avalanche; Desarodios takes Maril; Namo is Soldios'),
    (1455, 1571, 'Hagel Island - Nuts Cracker; Rap possessed; Dokken'),
    (1572, 1591, 'Hagel Island - after Dokken; Namo'),
    (1592, 1679, 'Hagel Island - penguin village; Rap tells of Geistreis'),
    (1680, 1793, 'Hagel Island - the Ice Tower, Rip, Dokken'),
    (1794, 1954, 'Hagel Island - Rip and Rap\'s home, Palm, the fight for Rip and Rap'),
    (1955, 1985, 'Shop (polite shopkeeper)'),
    (1986, 2009, 'Shop (beastie shopkeeper)'),
    (2017, 2042, 'Castle Alcazar - Ryuke and Sisty'),
    (2043, 2052, 'Castle Alcazar - after the fights; Nuts Cracker'),
    (2053, 2084, 'Castle Alcazar - Maril shields Tatto from Desarodios'),
    (2085, 2147, 'Castle Alcazar - the Waterway Man and Ruti; the legend of the gods'),
    (2148, 2241, 'Castle Alcazar - Belcrift and Gaw; Material and Nuts Cracker; the escape'),
    (2242, 2264, 'Castle Alcazar - Gaw runs off alone'),
    (2265, 2277, 'Castle Alcazar - Tatto hears Maril\'s voice'),
    (2278, 2303, 'Castle Alcazar - Blacky\'s present'),
    (2304, 2367, 'Castle Alcazar - Material, the holy sword and Geistreis (final battle)'),
    (2374, 2395, 'Character introductions (title screen demo)'),
    (2396, 2425, 'Ending - epilogue'),
]
def scene(mid):
    if mid.startswith('X'):
        return None
    n = int(mid[1:])
    for a, b, d in SCENES:
        if a <= n <= b: return d
    return ''

X_SCENE = {'05#0': 'Jungle - opening', '05#1': 'Jungle elf village / Material', '05#3': 'Jungle - Tatto joins',
           '05#5': 'Ancient Caves', '05#6': 'Ancient Caves', '05#7': 'Ancient Caves - the Waterway Man',
           '05#8': 'Ancient Caves', '13#0': 'Port Miine', '13#2': 'Gades Ruins', '13#4': 'Gades Ruins',
           '13#7': 'Gades Ruins - dwarf village', '15#1': 'Hagel Island', '15#5': 'Hagel Island - Ice Tower',
           '15#6': 'Hagel Island', '17#7': 'Castle Alcazar', '17#8': 'Castle Alcazar', '17#12': 'Castle Alcazar'}

def context(mid, en_raw, sk):
    c = scene(mid) or X_SCENE.get(sk, sk)
    notes = []
    if '<10:' in en_raw: notes.append('different lines for Mail / Tatto / Gaw')
    if en_raw.lstrip('§').startswith('【NARR】') or '【NARR】' in en_raw[:12]: notes.append('narration (green text)')
    if '‹' in en_raw: notes.append('large red text')
    return c + ('; ' + '; '.join(notes) if notes else '')

# ---------------------------------------------------------------- changes requested by the project owner (wording, pauses, colour)
CHANGES = {
    'M0707': 'Locked-door text: "The door is locked. / You can\'t get in." (was "Nobody seems to live here.")',
    'M0113': 'Locked-door text: "The door is locked. / You can\'t get in." (was "Nobody seems to live here.")',
    'X0003': 'Reworded so it reads on into the next box ("...is YOUR master?!")',
    'M0155': 'Mail\'s name added at the top of the box',
    'M0156': 'Pause at the start; reworded as Mail making up her mind ("Oh, what the heck!...")',
    'X0009': 'Reworded: "...Hey! Let me finish what I was sayin\', will ya!"',
    'M0606': 'Pause added: "Do you not... remember me?"',
    'M1489': 'Comma added: "Just you wait, Nuts Cracker!!"',
    'M1631': '"Him", with the comma outside the quotes',
    'M1632': 'Gaw\'s name added to his version of the line',
    'M1697': 'Girl\'s line written separately for each hero ("I\'m fine!" / "Big Brother Soldi" / "Mr. Beastie")',
    'M1699': 'Girl\'s line written separately for each hero ("I\'m fine!" / "Big Brother Soldi" / "Mr. Beastie")',
    'X0031': 'Loose-wall text reworded: "This part of the wall / looks weak..."',
    'M0112': 'Shop sign reworded: "Closed for Now / ~Off to Port Miine!~"',
    'X0017': 'Reworded: "This rock seems loose."',
    'X0002': 'Siana: the one who ran off is Namo ("...he ran off from the village all by himself.")',
    'M0042': 'Siana: "Namo\'s sense of justice is second to none."',
    'M0756': 'v1.2: "Yeah, what is it, little lady?!"',
    'M1992': 'v1.2: "Which one ya want, huh?!"',
    'M0689': 'v1.2: "Jungle" in gold text',
    'M0533': 'v1.2: half-second pause after "Goruades!!"',
    'M0534': 'v1.2: half-second pause after "But..."; "..." added at the end',
    'M0536': 'v1.2: the window closes for 3 seconds after this box (Mail thinking it over)',
    'M0537': 'v1.2: shown in a new window after the 3-second break; half-second pause before line 2',
    'M0573': 'v1.2: 3-second break before this box (after "Is she Tatto\'s girlfriend?")',
    'M0576': 'v1.2: half-second pauses before "Material!" and "Where are you?!"',
    'M0904': 'v1.2: "Hmm?" in place of a bare "?"',
    'M0949': 'v1.2: "Huh?!" in place of a bare "?!"',
    'M1056': 'v1.2: "Wha—?!" in place of a bare "!!"',
    'M1152': 'v1.2: "Ah!" in place of a bare "!!"',
    'S1374': 'v1.2: amount in gold text, "Gold" with a capital G',
    'M1997': 'v1.2: amount in gold text, "Gold" with a capital G; "You good with that?" added',
    'M1970': 'v1.2: reworded "Your card was exchanged for / N Gold"; amount in gold text',
    'M2001': 'v1.2: reworded "That card of yours gets ya / N Gold"; amount in gold text',
    'M1986': 'v1.2: one line, "Hey, welcome! Whaddaya need?"',
}

# ---------------------------------------------------------------- dialogue
MENU_IDS = {'M1975', 'M1977', 'M2005', 'M2007'} | {'M%04d' % i for i in range(2010, 2017)} | {'M%04d' % i for i in range(2368, 2374)}
MISC_IDS = {'M2118'}
SKIP_UNUSED = {'M1964', 'M1995'}          # shop message 9: never shown (no code path starts it)

def x_jp(sk, a, b):
    k = tuple(int(v) if i else int(v, 16) for i, v in enumerate(sk.split('#')))
    return render_src(DEC(k), a, b)

rows = {'dialogue': [], 'menus': [], 'misc': [], 'map': []}
for mid in ORDER:
    en_raw = W.get(mid, '')
    if not en_raw or en_raw.startswith('=') or mid in SKIP_UNUSED: continue
    sk = SRC[mid]['sk']; jp = jp_strip(SRC[mid]['jp'], en_raw)
    en = clean_en(en_raw)
    if not en: continue
    r = [mid, jp, en, context(mid, en_raw, sk), CHANGES.get(mid, '')]
    if mid in MENU_IDS: continue
    if mid in MISC_IDS:
        r[3] = 'Castle Alcazar - the legend of the gods, scrolling up the screen in front of the statue'
        rows['misc'].append(r); continue
    rows['dialogue'].append(r)
# English-only additions (X ids), placed after the message they belong to
for sk, lst in dr.EXTRA.items():
    for a, b, mid in lst:
        en_raw = W[mid]; jp = clean_jp(x_jp(sk, a, b))
        rows['dialogue'].append([mid, jp, clean_en(en_raw), context(mid, en_raw, sk) + ' (found in a later pass)', CHANGES.get(mid, '')])

# ---------------------------------------------------------------- shop strings (17#4 code-side messages)
o174 = DEC((0x17, 4))
def jp174(s):
    e = o174.find(b'\x20\xff', s); return clean_jp(render_src(o174, s, e + 2))
EXTRA_EN = {
    'S12B9': ('Shop: confirming a purchase (polite shopkeeper)', 'dialogue'),
    'S1374': ('Shop: healing price (polite shopkeeper)', 'dialogue'),
    'S161B': ('Shop: after a purchase (beastie shopkeeper)', 'dialogue'),
    'S1635': ('Shop: confirming a purchase (beastie shopkeeper)', 'dialogue'),
}
src_txt = open('patch/special.py', encoding='utf-8').read()
for sid, (ctx, cat) in EXTRA_EN.items():
    m = re.search(r"'%s': '([^']*)'" % sid, src_txt)
    en = clean_en(m.group(1))
    rows[cat].append([sid, jp174(int(sid[1:], 16)), en, ctx, CHANGES.get(sid, '')])

# ---------------------------------------------------------------- menus
M = rows['menus']
def add(i, jp, en, ctx, ch=''): M.append([i, jp, en, ctx, ch])
add('TITLE-1', 'START', 'START', 'Title screen (English in the original)')
add('TITLE-2', 'CONTINUE', 'CONTINUE', 'Title screen (English in the original)')
jp_areas = ['ミーネの港', 'ジャングル', '古代の洞窟', 'ガデス遺跡', 'ハーゲル島', 'アルカザール城']
for i, (j, e) in enumerate(zip(jp_areas, SP.AREAS)):
    add('AREA-%d' % (i + 1), j, e, 'Area names in the title screen\'s CONTINUE list, the save list (SELECT on the status screen) and the shop save-slot list')
add('AREA-7', '―――――――', '―――――――', 'Empty save slot')
add('SHOP-1', '買う', 'BUY', 'Shop: header label (graphic)')
add('SHOP-2', '換金', 'CASH', 'Shop: header label (graphic)')
add('SHOP-3', '治療', 'HEAL', 'Shop: header label (graphic)')
add('SHOP-4', 'コンフィグ', 'KEYS', 'Shop: header label (graphic)')
add('SHOP-5', 'セーブ', 'SAVE', 'Shop: header label (graphic)')
add('SHOP-6', '速さ', 'SPEED', 'Shop: header label (graphic)')
add('S1497', jp174(0x1497).replace('（終了）', '（終了の記号）'), 'Buy   Cash   Heal   Opts   Exit', 'Shop: main menu (both shopkeepers)')
add('S14AF', jp174(0x14AF), 'Keys   Save   Speed   Back', 'Shop: Opts menu (both shopkeepers)')
add('S14D4', jp174(0x14D4), 'Set the message speed.\n\nFast  ・  Normal', 'Shop: Opts > Speed (polite shopkeeper)')
add('S1820', jp174(0x1820), 'Set the message speed.\n\nFast  ・  Normal', 'Shop: Opts > Speed (beastie shopkeeper)')
add('YESNO-1', 'はい', 'YES', 'Shop and save: yes/no box')
add('YESNO-2', 'いいえ', 'NO', 'Shop and save: yes/no box')
add('KEYS-1', 'ケッテイ', 'CONFIRM', 'Shop: Opts > Keys (controls screen), bottom row', 'v1.2: translated (was left in Japanese)')
add('KEYS-2', 'キャンセル', 'CANCEL', 'Shop: Opts > Keys (controls screen), bottom row', 'v1.2: translated (was left in Japanese)')
add('KEYS-3', 'JUMP / DEFENCE / CHANGE / ATTACK / ITEM MODE / STAGE SEL', 'JUMP / DEFENCE / CHANGE / ATTACK / ITEM MODE / STAGE SEL', 'Shop: Opts > Keys (English in the original)')
for i, (j, e) in enumerate([('メイル', 'MAIL'), ('タット', 'TATTO'), ('ガウ', 'GAW')]):
    add('STATUS-%d' % (i + 1), j, e, 'Status screen: character name')
add('STATUS-4', 'SWORD', 'SWORD / M.ROD / ATTACK', 'Status screen: weapon label (SWORD for Mail, M.ROD for Tatto, ATTACK for Gaw)')
add('STATUS-5', 'モンスターカード', 'MON CARD', 'Status screen: Monster Card line')
add('STATUS-6', '（個数のあとの「コ」）', '(removed)', 'Status screen: counter after an item count ("ORANGE 1")')
add('HUD-1', '敵', 'FOE', 'Top-of-screen display: enemy health bar label')
add('EQUIP-1', 'そうびしますか？', 'Equip it?', 'After receiving a weapon or armour')
add('CONTEST-1', 'おやじ', 'DWARF', 'Dwarf Medicine Man\'s contest display (MAIL / DWARF)')
o157 = DEC((0x15, 7))
def dakuten(s):
    s = s.replace('_', ' ').replace('<F8>', 'ピ').replace('<E5>', 'グ').replace('<FB>', 'ボ')
    for a, b in zip('カキクケコサシスセソタチツテトハヒフヘホ', 'ガギグゲゴザジズゼゾダヂヅデドバビブベボ'):
        s = s.replace(a + '゛', b)
    for a, b in zip('ハヒフヘホ', 'パピプペポ'):
        s = s.replace(a + '゜', b)
    return s
n = (o157[0] | o157[1] << 8) // 2
for i in range(n):
    if i not in SP.ITEMS or i in range(37, 47): continue
    p = o157[2*i] | o157[2*i+1] << 8; e = o157.index(0, p)
    jp = dakuten(smdec(o157[p:e]))
    add('ITEM-%02d' % i, jp, SP.ITEMS[i], 'Item / equipment / skill name (status screen, shops)')

# ---------------------------------------------------------------- world map
for i, (j, e) in enumerate(zip(['ミーネの砦', 'ジャングル', '古代の洞窟', 'ガデス遺跡', 'ハーゲル島', 'アルカザール城'], SP.AREAS)):
    rows['map'].append(['MAP-%d' % (i + 1), j, e, 'World map: destination name bubble (graphic)'
                        + ('; the Japanese label says 砦 ("fortress") while all dialogue says ミーネの港 ("port")' if i == 0 else ''), ''])

# ---------------------------------------------------------------- scrolling / misc
X = rows['misc']
X.insert(0, ['TITLE-LOGO', 'ポップフルメイル（タイトルロゴ）', 'Original Japanese logo (standard edition) / "POPFUL MAIL" (English-logo edition)', 'Title screen logo', 'English-logo edition: new English logo'])
cred_jp = {'Jun Nagashima': '永島 純', 'Hideyuki Shiota': '塩田 英幸', 'Mayuko Suzuki': '鈴木 繭子', 'Yuichi Shiota': '塩田 雄一',
           'Norihiro Sawada': '沢田 憲宏', 'Kazuo Nakamura': '中村 和郎', 'Yuichi Takashita': '高下 雄一', 'Mieko Ishikawa': '石川 三恵子',
           'Atsushi Shirakawa': '白川 篤史', 'Hirofumi Matsuoka': '松岡 博文', 'Takahiro Tsunashima': '綱島 貴博', 'Masaru Nakajima': '中島 勝',
           'Naoki Kaneda': '金田 直樹', 'Yoshinobu Nakahara': '中原 嘉伸', 'Noriyoshi Akiba': '秋葉 紀好', 'Toshikuni Matsumae': '松前 俊邦',
           'Tadashi Hayakawa': '早川 正', 'Yoshio Kiya': '木屋 善夫', 'Shinji Yamazaki': '山崎 伸治', 'Masayuki Kato': '加藤 正幸',
           'POPFUL MAIL': 'ぽっぷるメイル'}
for h_jp, h_en in [('PROGRAM', 'PROGRAMMING'), ('SCENARIO', 'SCENARIO'), ('ART & GRAPHIC', 'ART & GRAPHICS'), ('DIRECT', 'DIRECTION'),
                   ('PRODUCE', 'PRODUCTION'), ('MUSIC', 'MUSIC'), ('MANUAL', 'MANUAL'), ('SPECIAL THANKS', 'SPECIAL THANKS')]:
    X.append(['CREDIT-H', h_jp, h_en, 'Staff credits: heading (English in the original)', ''])
import credits as CR
for (page, row), name in sorted(CR.NAMES.items()):
    X.append(['CREDIT-%d-%02d' % (page, row), cred_jp.get(name, ''), name, 'Staff credits: name (kanji graphic in the original)'
              , 'Corrected to Jun Nagashima (was Jun Mizushima)' if name == 'Jun Nagashima' else ''])
X.append(['CREDIT-END', 'COPYRIGHT (C) 1994 NIHON FALCOM INC.', 'COPYRIGHT (C) 1994 NIHON FALCOM INC.', 'Staff credits: last page (English in the original)', ''])

SORDER = {}
for mid in ORDER: SORDER.setdefault(SRC[mid]['sk'], len(SORDER))
def okey(r):
    i = r[0]
    if i.startswith('M'): return (SORDER[SRC[i]['sk']], int(SRC[i]['off'], 16))
    if i.startswith('X'):
        for sk, lst in dr.EXTRA.items():
            for a, b, mid in lst:
                if mid == i: return (SORDER.get(sk, 99), a)
    if i.startswith('S'): return (SORDER['17#4'], int(i[1:], 16))
    return (999, 0)
rows['dialogue'].sort(key=okey)

# ---------------------------------------------------------------- write
# epilogue and credits get tables of their own
rows['epilogue'] = [r for r in rows['dialogue'] if r[0].startswith('M') and 2396 <= int(r[0][1:]) <= 2425]
rows['dialogue'] = [r for r in rows['dialogue'] if r not in rows['epilogue']]
rows['credits'] = [r for r in rows['misc'] if r[0].startswith('CREDIT')]
rows['misc'] = [r for r in rows['misc'] if not r[0].startswith('CREDIT')]

HEAD = ['ID', 'Japanese', 'English', 'Context', 'Changes']
OUT = os.path.join('out', 'text_tables'); os.makedirs(OUT, exist_ok=True)
TABLES = [('1_world_map', 'World Map', 'map'), ('2_menus', 'Menus', 'menus'), ('3_dialogue', 'Dialogue', 'dialogue'),
          ('4_scrolling_misc', 'Scrolling & Misc', 'misc'), ('5_epilogue', 'Epilogue', 'epilogue'), ('6_credits', 'Credits', 'credits')]
for name, title, key in TABLES:
    with open(os.path.join(OUT, name + '.csv'), 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f); w.writerow(HEAD); w.writerows(rows[key])
    print('%-18s %5d rows' % (name, len(rows[key])))
try:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
except ImportError:
    print('(openpyxl not installed: CSV files only)')
else:
    wb = Workbook(); wb.remove(wb.active)
    for name, title, key in TABLES:
        ws = wb.create_sheet(title); ws.append(HEAD)
        for r in rows[key]: ws.append(r)
        for c, wd in zip('ABCDE', (12, 40, 40, 45, 40)): ws.column_dimensions[c].width = wd
        for row in ws.iter_rows():
            for cell in row: cell.alignment = Alignment(wrap_text=True, vertical='top')
        for cell in ws[1]: cell.font = Font(bold=True); cell.fill = PatternFill('solid', fgColor='DDDDDD')
        ws.freeze_panes = 'B2'; ws.auto_filter.ref = ws.dimensions
    wb.save(os.path.join(OUT, 'text_tables.xlsx'))
print('wrote', OUT)
