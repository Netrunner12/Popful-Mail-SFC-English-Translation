Popful Mail (SFC) - English fan translation - work-in-progress patch v0.1
=========================================================================

Apply to:  Popful Mail (Japan).sfc   (1 MB, no copier header, CRC32 88E5BCDF)
Result:    2 MB LoROM, CRC32 91146993
Formats:   popful_mail_en_v0.1.bps (recommended, verifies the source ROM)
           popful_mail_en_v0.1.ips (same result, no source check)
Tested by applying with Flips and booting in snes9x.

What is in this build
---------------------
- Original 8x16 English font (not taken from any other release). Two letters
  are packed into each of the game's 16x16 character cells, so a text line
  holds 30 letters instead of 15 kana.
- All dialogue in the 30 standard scene streams (over 2,000 messages) is
  in English: the field text box and the purple cut-scene box.
- Speaker names (portrait names Mail, Tatto, Gaw and every NPC name label)
  are in English.
- Centred narration lines are re-centred for English line lengths.
- If a text box runs out of rows, the game now ends the box and continues in
  a fresh one, so no line falls off the bottom of the window.
- Text relocated to new ROM banks $22-$25; engine code in bank $20; font in
  bank $21.

Still in Japanese / not done yet
--------------------------------
- Opening intro, ending, and the shop/menu stream (three streams with a
  different layout).
- Menus, item names, status screen and other non-dialogue graphics text.
- Numbers drawn by the number printer still use the original full-width
  digit style.
- Only the opening part of the game (Port town, tavern) has been played
  through in the emulator so far. Later scenes were built and checked by the
  tools but not yet seen in play.

Please report anything that looks wrong with a screenshot and a note of where
it happened.
