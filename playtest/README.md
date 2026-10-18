# snestest — automated play-testing for SNES translation patches

Plays a build headlessly (snes9x libretro core), many times over, with every hero, in many places,
and writes a bug log with a screenshot per finding.  Built for the Popful Mail translation; the
core is game-independent and a new game needs only a profile.

## Layout

    snestest/emu.py      emulator wrapper: run/tap, RAM read/write, savestates, desktop-snes9x
                         state import (.000-.009, gzip), SRAM, write watchpoints, discover_flag()
    snestest/detect.py   detectors: crash (CPU outside game code), black screen, frozen picture,
                         text box checks (overflow, mixed colours, off-centre, stray indent, too many lines)
    snestest/runner.py   runs a job matrix on all CPU cores; a crashing job is logged, never fatal
    snestest/report.py   bugs.json + report.html (severity-sorted, one picture per finding)
    snestest/textscan.py finds original-language text anywhere in the ROM that the script does not cover
    profiles/popful_mail.py   everything specific to Popful Mail
    playtest.py          command line

## Commands (Popful Mail)

    python3 playtest.py ROM static                    no emulation: unpatched copies of text code in any
                                                      compressed stream, line widths, message selection, jumps
    python3 playtest.py ROM messages [IDS]            every message the game starts, as Mail, Tatto and Gaw,
                                                      paged box by box; text reached by jumps and hero
                                                      branches is checked as it is shown (coverage in not_reached.json)
    python3 playtest.py ROM explore --save X.srm      warp to every area x sub-area x hero x input policy;
                                                      the same run on the original Japanese ROM decides
                                                      whether a crash is ours or a test artefact
    python3 playtest.py ROM states FILE.00x ...       user's snes9x save states x hero x policy
                                                      (code blocks in RAM are refreshed from the build first)

Results: `out/<rom crc>/<command>/report.html`.

## What each finding means

| kind | meaning |
|---|---|
| crash | CPU left the game's code (profile `valid_pc`) for 8–20 frames |
| black_screen / frozen | picture black, or unchanged despite input, for 15–30 s |
| stuck | message text stopped advancing while A was pressed |
| overflow | text pixels outside the box's text area |
| colour_mix | one line drawn in two text colours where the text has no colour code |
| off_centre | a centred (narration) line more than ~1.5 letters off centre |
| leading_space | a left-aligned line that does not start at the margin, with no indent code |
| hero_not_offered | (info) a branch has fewer ways than heroes: that hero cannot be there in a real game |
| unpatched_code | (static) a copy of the text-start routine that still reads the Japanese text location |
| untranslated_text | (run time) some code read the ORIGINAL text bytes, or drew original-language glyphs: a display the patch never redirected (scroll, sign, menu, credits) |
| direct_text_read | (static) code that walks the original text itself (`LDA text,X` + `INX`) instead of going through the message pointers |
| text_not_in_script | (static) bytes anywhere in the ROM (every packed block, and the raw ROM) that read like original text but are in no script line |

## Adapting to another game

A profile module provides:

1. **RAM map**: text pointer, active character, party, HP, a "message open" flag. Find flags with
   `emu.discover_flag()` (bytes equal before and after an event, different during it) — then confirm
   by tracing the value through the event: the first candidate can be a coincidence (here `$0365`
   was the walk animation, `$0652` the real window flag).
2. **valid_pc(pc)**: which banks/addresses hold code (ROM size and mapping, RAM-resident code).
3. **Text box geometry and colours**: the text area, the text palette, alignment per colour, icons
   to ignore (blinking prompt arrows).
4. **A way to show any message**: here, open a real NPC conversation and replace the text pointer
   while the box waits; read the pointer just before each button press to know which message the
   next box comes from (this engine builds a whole box at once).
5. **Start points**: a warp hack (location override), user save states, SRAM.
6. **Static checks**: whatever code patterns the translation had to patch, searched in every
   compressed block *after* the patch is applied — the Hagel Island crash was one copy in a block
   that was not a scene.

## Emulator core additions

The stock snes9x libretro core plus a few debug entry points. `snes9x_debug.patch` applies to
snes9x commit fae2fea08f74 (github.com/libretro/snes9x); build `libretro/` with `make` and point
`SNES_CORE` at the resulting `snes9x_libretro.so`. Watch logs are written to /tmp/snestest/.

- `dbg_pc`, `dbg_reg` — CPU registers.
- `dbg_trace_enable`, `dbg_trace_read`, `dbg_trace_valid_banks`, `dbg_trace_state` — a ring of the last
  65 536 executed addresses that **freezes at the first instruction outside the game's code banks**.
  Every crash in a report carries the code path into it, and a crash is detected on the exact
  instruction, not by sampling the PC once per frame (an interrupt handler running inside a crashed
  game looks healthy to a per-frame sample).
- `dbg_set_watch` — write watchpoint on a work-RAM range (logs address, PC, value; only catches some
  write paths — use the trace for anything important).

## Every text display, not only dialogue

The Castle Alcazar story scroll (Popful Mail 17#7) stayed Japanese through v0.15: its text was in the
script and translated, but the scene's own routine read the Japanese bytes directly, 16 px per glyph, and
never touched the message pointers the patch redirects.  Dialogue sweeps cannot see that.  Three checks
now look for it, and none of them knows what the display looks like:

1. **Run time, original-text reads** (`detect.TextReadMonitor`): a read watchpoint on the work-RAM range
   where the current block's original text sits.  After translation, nothing should read those bytes;
   a run of >= 8 consecutive text-like bytes read means some routine is drawing them.  Ignore the
   decompressor (its back-references read the block it unpacks) and code living inside the range.
   Calibrated: original ROM, ordinary conversation -> flagged; English build, same inputs -> clean.
2. **Run time, foreign glyphs** (`detect.GlyphMonitor`): a read watchpoint on the part of the font only
   original-language glyphs use.  Good inside message boxes; outside them the same RAM may be reused
   (here the field reuses it for map data), so use it where the font is known to be resident.
3. **Static** (`textscan`, `direct_text_reads`): text anywhere that no script line covers (a character-
   bigram model of the script tells sentences from data; thresholds come from the script's own lines),
   and code that walks the original text.  Calibrated by hiding the scroll from the script: flagged.

Reaching a one-off cutscene: find the scene's event table (zone -> handler), widen the zone to the whole
map, and turn the "wait until the NPC has walked there" calls into NOPs (done for the 17#7 scroll while developing the patch) - the cutscene then runs straight through to the display under test.

Lessons that carry over:
- Compare against the original ROM before calling something a bug; warping causes its own glitches.
- Sweep per character: hero-specific branches hid an overflow ("Mr. Beastie") that no other run saw.
- Old emulator save states carry old code in RAM; refresh it or the state reproduces fixed bugs.
- Text that only runs inside its own menu (shops) must be tested in that menu, not injected elsewhere.
- Calibrate every detector on builds with known bugs before trusting a clean report.
- A warp hack reaches location numbers the game never uses; check that what got loaded is real
  (here: scene code starts with a JMP) and skip the rest instead of reporting their crashes.
- Run the original ROM through the very same inputs and judge with the same exact crash test;
  a looser test on one side produced a page of false "English-only" crashes.
- A base state saved by an older build keeps that build's blocks in RAM.  Warping inside the scene that is
  already loaded does not reload it, so the old message-table address stays and a later message 'crashes'
  (Port Miine after the dwarf contest).  Refresh RAM code whenever a run enters a scene, not only at load.
- A warp can pick a location the scene does not have; find the scene's location dispatch table and
  check the entry before trusting anything that happens there.
- Check that a message window is actually on screen before measuring text: the window flag is also set
  while a window opens or closes, and the status bar then reads as overflowing text.
- Translate every display, not just dialogue: scrolls, signs, menus, credits, intros, name cards.
  Run the static scan on the original ROM at the start of a project, before any script is made.
- Text engines that build a whole box at once move the text pointer past the box immediately: read
  the pointer while the box waits for a button to know which message the next box comes from.
