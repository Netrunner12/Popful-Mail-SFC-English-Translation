Popful Mail (SFC) - English fan translation - work-in-progress patch v0.8
=========================================================================

Apply to:  Popful Mail (Japan).sfc   (1 MB, no copier header, CRC32 88E5BCDF)
Result:    2 MB LoROM, CRC32 89B60402
Formats:   popful_mail_en_v0.8.bps (recommended, verifies the source ROM)
           popful_mail_en_v0.8.ips (same result, no source check)
Both checked with Flips; the patched ROM boots and plays in snes9x.

As with earlier versions, emulator save states made with an older patch
can show wrong text. In-game saves carry over fine.

New since v0.7
--------------
- The "Equip it?" prompt after you receive a weapon or armour is in
  English (it was Japanese text inside the game's code).
- The Monster Card line on the status screen reads MON CARD.
- The Dwarf Medicine Man's contest display labels him DWARF.
- Checked in play: every chapter's areas were loaded directly, and the
  game was played with scripted input while the tools watched for any
  text read from untranslated data. Nothing else turned up.

New in v0.7
-----------
- Status screen: the item count no longer has the Japanese counter after
  it ("ORANGE 1").
- The enemy health bar in the top-of-screen display is labelled FOE.

New in v0.6 (since v0.4)
------------------------
- Staff credits are romanized. The credit names are redrawn as English
  letters in the credits' own outline style. A few readings could not be
  confirmed from a published source and may be wrong:
    Takahiro Tsunashima, Masaru Nakajima, Yoshinobu Nakahara,
    Noriyoshi Akiba, Toshikuni Matsumae, Tadashi Hayakawa
  Corrections are welcome.
- The yes/no box (shops, saving) now reads YES / NO; the highlighted
  choice is shown in orange.
- Shop header labels (BUY, CASH, HEAL, KEYS, SAVE, SPEED) are in English.
- Numbers in dialogue use the new font, with no stray gap before them.
- Line fixes: dialogue boxes that were one line too long, and some
  awkwardly split sentences.

Still Japanese / known issues
-----------------------------
- The title-screen logo is intentionally left as the original Japanese artwork.
- The ending and credits were checked with a debug jump, not by playing
  to the end.
- The dwarf contest display was fixed in the data but not seen in play
  (it opens only after story progress).
- Later chapters were spot-checked by jumping into each area, not played
  through from start to finish.
