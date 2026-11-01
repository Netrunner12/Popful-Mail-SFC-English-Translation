# Pending changes

Items 1-5 below were APPLIED in v0.10 (2026-10-10). Add new items under a new heading.

# Applied in v0.10

## 1. Locked-door text (requested 2026-10-09)
Change every "The door is locked. / Nobody seems to live here." to
"The door is locked. / You can't get in."
Reason: the same message is used in places where "Nobody seems to live here" doesn't fit.
Where: patch/overrides.tsv lines for M0707 and M0113 (both narration, <18:03>/<18:05> indents).
Also check 05#7 substring 0E34 ("The door is locked / and won't open.") for consistency.

## 2. Material Horn line after the golem fight (05#1) — shown to user, awaiting decision
Current in-game (two boxes):
  [Mail] Wait, could you be... / the $2,000,000 bounty, / Material Horn?      (X0003, patch/extra_msgs.tsv line 4)
  is YOUR master?!                                                            (M0076)
JP: ２，０００，０００の マテリアル・ホルンって / あんたの お師匠さまなの？！
Problem: the two boxes don't join into one sentence.
Suggested: X0003 -> "Wait... the $2,000,000 bounty,⏎Material Horn..."  so it reads on into "is YOUR master?!"

## 3. Gaps around highlighted names (requested 2026-10-10)
Example: M0159 (05#3, jungle, Tatto): "Up ahead are the  Ancient / Caves ." — extra gap before
"Ancient" and before the period.
Cause: two letters share one 16x16 cell and a cell has one colour, so a colour switch (« »)
must start a new cell; when the text before it ends on a half-filled cell, the empty half
shows as an extra space.
Fix plan (builder, not engine): when « / » falls on a half cell, drop an adjacent space (the
empty half already looks like a space); for "»." / "»!" etc., rephrase or shift a letter so the
switch lands on a cell boundary. Re-check line wrapping after.
Affected (scan of all messages): M0159, M0581, M0634, M0827, M1973, M2003, plus wrapped
continuation lines such as M0159 "Caves»." — rescan after the fix.

## 4. Tatto-joins conversation, boxes 16-20 all Mail (05#3) — decided 2026-10-10
Boxes 17-20 have no name, and box 20 ("Fine! I'll let the money slide...") reads like a reply to Tatto.
- Add Mail's name at the top of box 19 (M0155 "With you along, he might be easier to catch...").
- Box 20 (M0156): pause at the start, and reword to match 仕方ない (Mail deciding with herself):
  "⏸Oh, what the heck! I'll forget the money... but you're helping me catch Material!" (3 lines)

## 5. Status screen: TATTO doesn't fit the name box (reported 2026-10-10)
"NAME:TATTO" runs past the right edge of the box (the box holds 9 menu-font characters:
"NAME:MAIL" just fits; the Japanese names were 3 characters).
Plan: find whether "NAME:" and the box frame are drawn from the status-screen tilemap or the
text routine, then either widen the box by one tile (preferred, if the frame art allows) or
shorten the label so the longest name (TATTO) fits. Check all three characters on screen.

# Ancient Caves batch (2026-10-11) — RELEASED as v0.11 (build/v011.sfc)
Applied in the preview: Blacky logo (◐◑ + space, new font codes $83/$84); narration centring (⇥ token,
dryrun._centre_narration) — awaiting user OK on the samples; minutes zero-padded (pause $00:8A78,
save list 17#3, title continue list 1A#0); DWARF moved to column $10; M0188 "Follow me!" line;
M0606 "Do you not...⏸ remember me?"; M0614 "I" to line 3; status label WEAPON; beastie shop
"Anything else ya need?" on one line ("That it?" left as is, centred under the item name).
Save file for the dwarf contest: release/dwarf_contest_test.srm (slot 1, Port Miine, flags
$0293=58 $0294=01, 3000 gold, Mail only).
Decided 2026-10-11:
- X0009 (05#6 beastie): APPLIED -> "...Hey! Let me finish / what I was sayin', will ya!"
- M0521 (05#8 Gaw): LEFT AS IS (user: makes sense in context).
- Centring made half-cell accurate (leading space when the letter padding is odd, rounded right)
  — build/test25 = v0.11-preview2 (CRC32 873C4BC0). Also fixed M0405/M0556 ("Got the Pickaxe!",
  "Got the Jail Key!"): their original indent plus the centring indent added up and pushed the
  text right.
- X0014 (pickaxe chest) is only reached from X0012 after its blank line + narration colour, so it
  is green and on row 2 in game; checked by rendering X0012 forced onto the pickaxe branch.
- M0405 "Got the / Pickaxe!": top line moved left one letter. Rule: odd padding rounds right only
  when the line ends in narrow punctuation (. , ! ? '), otherwise left (also moves M0556 "Got the").
- M0556 "Got the / Jail Key!" kept with its top line rounded right (user: bottom line is longer),
  via the per-line marker ⇥+ in overrides.tsv.

# General / Gades Ruins batch (2026-10-13) — RELEASED as v0.12 (build/v012.sfc, CRC32 CA05AE07)
1. Port Miine Nuts Cracker poster: name and $500,000 moved right one letter (poster labels now use
   the same half-cell centring as narration; insert.poster_centre). The half-cell space goes INSIDE the
   label (a label starts a new cell, so a space before it costs a whole cell = 2 letters).
2. M1097 "You were knocked back / by an invisible wall.": bottom line moved left one letter
   (new per-line marker ⇥- = round left; ⇥+ = round right).
3. Status screen equipment label per character: MAIL SWORD, TATTO M.ROD (period glyph sits left, so no
   space after it), GAW ATTACK (engine.asm
   StatusLabel, hooked into 17#3's name drawing); the yellow N (attribute $24 in 01#17) is gone.
4. M1015 (Marvela): "ends" moved to line 2 ("Marvela... your part / ends here.").
5. Status screen name field blanked before each name (cycling with R left TATTO's letters: MAILO,
   GAWTO). StatusLabel draws 5 blanks first. Folded into v0.12 (re-issued 2026-10-13).

# v0.13 (2026-10-14) — Hagel Island crash fix
- Event code stream 1F#27 (loaded at $7E:E000, not a scene) had its own unpatched local message
  starter, so after the Dokken boss the voice message read $7E:0000 and crashed (black screen / hang).
  special.do_1F27 replaces it with JSL MsgStartX. Scan of every stream: no other unpatched starter.
- Verified from the user's snes9x states: 006 (green box) plays through; 008 (pre-boss) fight ->
  voice scene -> next scenes, no crash. Menu black screen mid-fight: not reproduced (12 tries).

# v0.14 (2026-10-16) — Hagel Island text
- M1489 "Just you wait, Nuts / Cracker!!" (comma after wait).
- M1303 Maril: removed the stray space after the pause so line 2 is flush left.

# Castle Alcazar batch (2026-10-16) — build/test32 = v0.15-preview
1. X0031 (17#7, JP ここのカベだけ グラグラしている): "This part of the wall / looks like it could crumble." — awaiting OK.
2. M2017 Ryuke: stray space after the pause removed (line 2 flush left). Scan: no other pause+space line starts.
3. M2042 "A pile of rubble / blocks the way." (was one 32-letter line, overflowing).
4. M2367 "Got the Gold Armor / (Beastie size)!" shown to user.
5. M1631/M1632: "Him", (comma outside the quotes).
6. Material Horn poster: name and $2,000,000 one letter right (insert.POSTER_NUDGE).

# Play-test tool findings (2026-10-16) — in build/test34 = v0.15-preview2 (with the Castle Alcazar batch)
- M1697/M1699 (girl, Gaw branch): "Huh...? What's wrong? Mr. Beastie." ran off the box -> "⏎Mr. Beastie."
- M0271 (Mail breaks the door): line was ~2 letters left; new builder width hint ⟨wN⟩ for lines that continue
  through a jump; whole-cell centring because the jump starts a new cell.
- X0028: "(Rip and Rap are really / that old?!)" stray leading space removed.
- Open: red (‹) text draws mostly dim in some scenes (Marvela M1015, boss arena); check vs original later.
Tool: playtest/ (README.md). Sweeps on test34: static clean; 1746 message runs (582 starts x 3 heroes,
1965 texts seen) clean except the red-text item; 504 exploration runs: no English-only problems;
user states 006/008 x 3 heroes x 3 policies: clean.
- preview3 (build/test35): girl's line restructured per hero (JP どうしたのぉ + name): "Huh...? / What's wrong? I'm fine!" (Mail),
  "What's wrong, / Big Brother Soldi?" (Tatto), "What's wrong, Mr. Beastie?" (Gaw); $2,000,000 back one letter left
  (POSTER_NUDGE now only Material Horn); M0271 line 1 two letters in (⟨w26⟩); shared line 2 "with the pickaxe!!"
  one letter right (⟨w17⟩ in M0276, also moves Tatto's version).
- preview4 (build/test36): "with the pickaxe!!" back to exact centre (6 letters in); user may want one more left.
- preview5 (build/test37): "with the pickaxe!!" 5 letters in (⟨w20⟩): 3/4 under Tatto line 1, 3/3 under Mail.
- preview6 (build/test38): Gaw name tag added to "Who's \"Him\", gaw?" (M1632, free 【+Gaw】).

# OPEN ITEMS (remind the user at each release)
- DONE in v0.17: loose-wall text X0031 -> "This part of the wall / looks weak..." (line 2 centred on line 1, ⇥-).
  17#7 block padded to its released size (build.KEEP_SIZE) so later text and the user's states don't move.
  (old note) Loose-wall text X0031 (17#7, Castle Alcazar): kept "This part of the wall / looks like it could crumble." for now;
  user asked to revisit later. Alternatives offered: "Only this part of the wall / is wobbly." / "This part of the
  wall / feels loose." / "The wall here seems weak. / It might give way." / "This section of wall / wobbles at the
  touch." / "The wall here / is shaky."  (JP: ここのカベだけ グラグラしている)
- Red (‹) text drawn mostly dim in some scenes (Marvela, Dokken): not yet compared with the original in those scenes.

# Rolled into v0.15 (re-issued 2026-10-17, build/v015.sfc = test39)
- M2017 Ryuke split into two boxes: "Sisty... I'm sorry." / (pause) "I dragged you along on my / selfish crusade..."
  New builder token ▽ = box break added in English only (free 20 0C).

# Castle Alcazar story scroll (2026-10-17) — RELEASED as v0.16 (build/v016.sfc = test41)
- The Waterway Man's story of the light goddess (17#7, scrolling text) was still Japanese: the scene's own
  scroll routine ($CC1E-$CC57) reads the Japanese text bytes directly (LDA $D7F5,X) and never goes through
  the message pointers the patch redirects. Its translation (M2118) existed but was never used.
- Fix: engine.asm ScrollLine (copied to $7E:D800 over the unused Japanese text, entered from $CC30)
  draws English lines from $28:D000, two letters per 16x16 cell, keeping the scene's tile bookkeeping.
  Cell pool wrap is handled only after both halves of a cell are staged (first version lost letters:
  "goddess" -> " oddess").
- Text rewritten line by line to follow the original's 38 phrase lines, centred on 30 columns
  (overrides.tsv M2118). Verified in the emulator through the whole cutscene: scroll, return, no crash.
- Toolkit: run-time original-text read monitor, foreign-glyph monitor, static walker scan, and a
  whole-ROM scan for original text missing from the script (playtest/README.md). Whole-ROM scan: nothing
  else untranslated. Removed the PM_TEST_SCROLL stub.
- Play-tester fixes found while sweeping test40/41: stale scene blocks in the base state are refreshed on
  every scene entry (false crash after the Port Miine dwarf contest), nonexistent warp locations detected
  (area 3/8), window must be on screen before text is measured. All were test artefacts, not game bugs.

# Ending batch (2026-10-17) — RELEASED as v0.17 (build/v017.sfc = test50)
- M2303 "Gold Armor!" one letter left (⇥-). M2164 "Geistreis, O sealed god! / The hour of your complete /
  revival is at hand!!" (wording offered, alternatives given). M2049 "My, he's a persistent fellow."
  M2206/M2207 "Maril... She did it to save me...!" / "So I teleported her somewhere safe...".
- Hm -> Hmm everywhere: M0027 M0121 M0409 M0842 M0897 M1063 M1356 M1530 M1748 M1778 M2181 M2411.
- Status screen: LGT SABER (item-name block was full: the empty names now share another name's end byte).
- Credits: DIRECT -> DIRECTION, PRODUCE -> PRODUCTION, built from letters of the original headings
  (N, I from NIHON; O from SCENARIO; T from THANKS) - credits.py retitle().
- Shown, not changed: Siana (M0040-M0043), M2237/M2238. Credits SCENARIO spacing = same as the original.
- FIXED (test43 = v0.17-preview2): black screen before "The End?" - the ending text table (1F#0) was built
  with 14 entries; the original has 15 (0x0E = Blacky's closing laugh M2425). Index 0x0E read past the table,
  the text ran from a garbage address and its tile list overran the IRQ routine the ending copies to $1F20.
  Verified from the user's state 007: "Ha-ha-ha-ha-ha..." -> THE END? -> title.
- preview3 (build/test44): credits headings ART & GRAPHICS and PROGRAMMING. No S, M or G stands apart in any
  original heading, so those are drawn in the headings' style (credits.DRAWN); appended letters are fitted
  row by row so outlines touch like the originals.
- preview4 (build/test47): PROGRAMMING uses PROGRAM's own M twice (credits.FILL_SOURCES); only S and G drawn.
  Decided: "O Geistreis" wording stays; status screen keeps MON CARD (MONSTER CARD runs into DEF).
- preview5 (build/test48): G cut from PROGRAM and S cut from SCENARIO (credits.CUT_SOURCES, per-row cuts with the
  outline closed); no drawn letters left.
- preview6 (build/test49): GRAPHICS keeps the drawn S (user's choice); PROGRAMMING keeps M and G from PROGRAM.
- preview7 (build/test50): SCENARIO names evenly spaced (credits.MOVE: Mizushima row 29->27, Suzuki page 2 row 2->0),
  5 rows apart like every other group; the gap to ART & GRAPHICS is now 14 rows, same as PROGRAMMING -> SCENARIO.
  The post-boss state (release/state_v017p6/POPFUL_MAIL_USA.005) still works (text layout unchanged).

# Green narration check (2026-10-17) — build/test51 = v0.18-preview
- All 59 green boxes rendered and measured (narrshots.py): line 1 against the box centre, other lines against
  line 1. Letters are 8 px and lines move in whole letters, so anything within 4 px is as close as possible.
- Fixed: M0259 (beastie's voice) and M0498 (dried fish): line 2 one letter left (was 7 px right of line 1).
  05#5 block kept at its released size (KEEP_SIZE) so save states keep working.
- Left as decided earlier: M0271/M0276 (pickaxe door), M1097 (invisible wall), X0031 (loose wall).
- preview2 (build/test52): M0654, M1214, M1722, M0280 start on line 2 like the other green boxes (rule: no green
  box starts on the top line; § + leading ⏎ — the auto re-flow dropped the leading ⏎ of M1214). M1722 re-broken
  "You hear something / from up above." X0017 -> "This rock seems loose." (<18:00> keeps the token count).
  Text after these moved a few bytes: save states made with v0.17 need re-patching (C003 / 1F#0 table pointer).

# RELEASED as v1.0 (2026-10-17) — build/v100.sfc = test52
- Save states for v1.0: release/states_v1.0/POPFUL_MAIL_USA.005 (after the final boss) and .003 (credits),
  re-patched from the v0.17 ones (C003 / ending text-table address), verified to reach "Ha-ha-ha-ha-ha...".
- Declined: an alternate patch with the English (Working Designs) title logo - that logo is someone else's artwork.

## v1.0 English-logo edition
- PM_LOGO=en build: original lettering design (patch/logo_en.npy, logo/design.py), original sword emblem. do_logo keeps Mode 7 tiles 0-15, 64, 192 (shared with the title menu BG1 layer). Release: popful_mail_en_v1.0_englishlogo.bps/.ips, CRC 5565BE5B (emblem re-cut from the original with its full outline).
- Logo replaced with the user-supplied English logo (logo/user/ref.png -> logo/user/convert2.py -> patch/logo_en.npy), mapped to the title palette. 1B#5 needs compress_opt(skip_runs=True) to fit (4636/4804); 1B#7 moved to the bank tail. Standard build verified identical to v100.sfc.

## v1.0 refresh (2026-10-18)
- M0112 shop sign: "Closed for Now / ~Off to Port Miine!~" (even lengths, exact centre).
- Monster Card box (13#0 substring 064B + M0723): "Received the Monster Card!" alone on the middle line.
- KEEP_SIZE pads 05#1 and 13#0 so later text blocks keep their v1.0 addresses.
- M0654 (tavern sign narration): removed the leading line break added in the green-box pass. The game enters this message a few bytes early, at a line break + indent kept from the Japanese, so it already starts on line 2; the review renders started at the message itself and showed it on line 1. Scan of every message for a line break hidden before its start: only M0473, M0654, M1785 (narration) and M2045; rendered from the real entry point, all now start on line 2.
- Siana (Jungle village): first talk box 2 ends "counts on him, but..."; box 3 (X0002) "...he ran off from the village all by himself." (was "She ran off..."); second talk opens "Namo's sense of justice is second to none." (was "but more than that, ..."). X0002 was missed by the first extraction pass and translated on its own later, so its unstated subject was guessed wrong, and M0042 was written as if it continued M0041.

# RELEASED as v1.1
- Line breaks: Nuts Cracker's introduction ("Indeed! I am the boss / of the Marionette Gang... / Nuts Cracker!!"),
  the $2,000,000 bounty line, and Material's "Getting old is no fun at all." on one line.

# RELEASED as v1.2 (2026-10-31)
Changes
- 0C#9 shop KEYS screen: a 32x32 tile map whose letter tiles are ASCII - 0x20; the bottom row still had
  ケッテイ / キャンセル, now CONFIRM / CANCEL (special.do_keys).
- Dwarf Medicine Man, beastie shop lines ("Which one ya want, huh?!", "I'll save your progress / for ya.",
  "Hey, welcome! Whaddaya need?" on one line - the JP indent token moved to the end of the line, where it does nothing).
- Heal price boxes (17#4 S1374, M1997) centred, amount in gold; card cash (M1970, M2001) "... / N Gold" centred.
  The number printer drops leading blanks, so a run-time number line is exactly centred for one digit count only.
- New English-only tokens: ⟪ ⟫ (gold on/off, not counted against the Japanese highlight codes) and ⏹ (end of message).
- Gaw's cave (scene 05#8): two scene-code hooks (engine.asm $20:E000, patched into the scene by build.py):
  GawSplit replaces the start of the Gaw talk; M0536 ends with ⏹, the window closes, 180 frames pass
  (JSL $00:E878 = wait A frames), then the talk resumes at M0537, whose address build.py writes into HookPtr0537.
  Mail only: the talk branches on the lead hero and Tatto's branch never reaches M0536. MarilWait puts the same
  wait between "Is she Tatto's girlfriend?" and the Mysterious Voice.
  The resident message starter $7E:B037 ends in RTS; pushing $B01D makes it return to the RTL at $7E:B01E.
- Pauses: M0533, M0534, M0537, M0576 (⏸ = 16 frames, ⏸1 = 32, ⏸2 = 80; they add up when chained).
- Openers "?" / "!" before text replaced: M0904 "Hmm?", M0949 "Huh?!", M1056 "Wha—?!", M1152 "Ah!".

Findings
- The original pause handler ($00:EDCF) skips every pause when the message speed is Fast ($0211 = 0).
- Shop testing: $0925 = shop type (2 beastie, 0 polite; both use 17#4), $0490 = HP, $0206 = Monster Card value.
- Shop message 9 ("[item] will be N gold") is never shown: no code path starts it; buying shows "[item] / That it?".
- Scene 05#8 event zones are 8-byte records [location, x0, x1, y0, y1, 0, handler] read by $7E:B937 with D = $0600.
- Port Miine's map label is ミーネの砦 ("fortress") while all dialogue says ミーネの港 ("port"); left as Port Miine.

Lessons
- A colour change starts a new two-letter block. Text that follows a highlighted run-time number on the same line
  gets a gap whenever the number has an odd length; end the line with the number instead.
- A scene hook that jumps into one branch of a hero-branched talk must check the hero; test every hero.
- Judge pauses in game at Normal speed; the test host runs text at full speed.
- Test saves for a scene: edit the player's own emulator state in place (clear the scene's "seen" bit, re-apply the
  build's scene RAM patches). Desktop snes9x writes version 11 states, the libretro core version 14; the blocks match
  in size except NAM, SRA and the screenshot, but the sound block must stay from the real v11 state.
- Menu text can be a tile map with an ASCII-like tile order; search streams for the word as 16-bit tile words.
- Read map-label graphics directly; don't infer them from dialogue.

Tests before release: static checks identical to v1.0; every message as Mail, Tatto and Gaw (only new flag: the
intended gold "Jungle"); the user's save states as every hero (one crash: Gaw forced as lead in his own scene,
impossible in play, also broken in v1.1); shops (Buy, Cash, Heal, Keys, Save, Speed, both shop types), the Gaw scene
and Maril's rescue as Mail and Tatto played through by hand. The repo build reproduces both release ROMs byte for byte.

# RELEASED as v1.2.1 (2026-10-31)
- Credits: PROGRAMMING and the second SCENARIO name are 永島 純, Jun **Nagashima** (was misread as 水島, Mizushima).
  The 16-px kanji has the dot of 永 on top. All names checked against the SNES credits on MobyGames (kanji and
  readings); every other name matches, including the six readings noted as unconfirmed since v0.6.
- Release: CRC32 1870CA23 (standard), 7C21198B (English logo). The repo build reproduces the standard ROM byte for byte; the English-logo ROM differs from it only in the title logo, as in v1.2.
- New tool tools/text_tables.py: six tables of all game text (Japanese from the user's ROM, English, context,
  requested changes) in out/text_tables/; the Japanese is never stored in the repo.
