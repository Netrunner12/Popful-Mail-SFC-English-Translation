Popful Mail (SFC) - English fan translation - work-in-progress patch v0.3
=========================================================================

Apply to:  Popful Mail (Japan).sfc   (1 MB, no copier header, CRC32 88E5BCDF)
Result:    2 MB LoROM, CRC32 2DAC1A2C
Formats:   popful_mail_en_v0.3.bps (recommended, verifies the source ROM)
           popful_mail_en_v0.3.ips (same result, no source check)

IMPORTANT: emulator save states made with an earlier version will show wrong text
(the game keeps the scene's text pointers in RAM). In-game saves are fine.
Start from an in-game save or a new game.

New since v0.2
--------------
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
- Ending text is in English (built and checked by the tools; not yet seen
  in play).
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
- A few graphic labels: the shop's header ("buy", "save"...) and the yes/no
  box are pictures, still Japanese; the item-count suffix on the status
  screen ("ORANGE 1" followed by a kana counter).
- In the purple cut-scene window the "more" arrow can overlap the last
  letter of a full-width second line.
- Tested in the emulator: title intro, Port Miine town, tavern, wanted
  posters, a house interior, the shop menus, saving and the status screen. The rest
  of the game is built and checked by tools but not yet played.
