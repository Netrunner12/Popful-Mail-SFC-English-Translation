Popful Mail (SFC) - English fan translation - work-in-progress patch v0.4
=========================================================================

Apply to:  Popful Mail (Japan).sfc   (1 MB, no copier header, CRC32 88E5BCDF)
Result:    2 MB LoROM, CRC32 D1FE3903
Formats:   popful_mail_en_v0.4.bps (recommended, verifies the source ROM)
           popful_mail_en_v0.4.ips (same result, no source check)

IMPORTANT: emulator save states made with an earlier version will show wrong text
(the game keeps the scene's text pointers in RAM). In-game saves are fine.
Start from an in-game save or a new game.

New since v0.3
--------------
- Shop header labels are now English sprites: BUY, CASH, HEAL, KEYS,
  SAVE, SPEED (the options entry "Button" is now "Keys" to match).
- The ending was run in the emulator (started directly with a debug jump,
  not reached by playing): its text is English and displays correctly.

New in v0.3
-----------
- Fixed: the save-slot list in shops was drawn as garbage (saving itself
  worked). "Save to slot 1?" now reads naturally.
- Fixed: dialogue branches whose pointer happened to contain the byte $20
  jumped to the wrong place (a few later-game lines, e.g. Mail boasting
  about beating Nuts Cracker).
- Translated Japanese fragments that sat inside shared text pieces: the
  "Monster Card" name used inside sentences, a locked-door message, some
  laughs and shouts, two missed lines (Udo, Peena).
- Fixed the few lines that were too long for the window (a narration, the
  long legend text, two others).
- Every message was checked with a tool that walks the text the way the
  game does, and rendered once in the game's text box for review.

New in v0.2
-----------
- Title-screen character intro (Mail, Tatto, Gaw) is in English.
- Ending text is in English.
- Shops, saving, options and the bounty exchange text are in English.
- Item, equipment and skill names are in English (8x8 menu font, so they
  are capitals and some are abbreviated to fit: SHORT SWD, WOOD SHLD,
  BRONZ MIR...).
- Character names on the status screen are in English.
- Wanted posters are re-centred.
- Boxes that the cut-scene window could not hold have been re-cut to fit.
- Numbers inside dialogue are drawn with the new font.
- More messages that the first extraction pass had missed are translated.

Still Japanese / known issues
-----------------------------
- The shop's small yes/no box (はい / いいえ: top = yes, bottom = no) and
  the item-count suffix on the status screen ("ORANGE 1" followed by a
  kana counter) are still Japanese.
- The staff credits after the ending are pictures with the staff's names
  in Japanese; left untouched.
- In the purple cut-scene window the "more" arrow can overlap the last
  letter of a full-width second line.
- Tested in the emulator: title intro, Port Miine town, tavern, wanted
  posters, a house interior, the shop menus, saving, the status screen
  and the ending. The rest
  of the game is built and checked by tools but not yet played.
