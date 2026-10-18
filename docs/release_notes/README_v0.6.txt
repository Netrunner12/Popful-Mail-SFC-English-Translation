Popful Mail (SFC) - English fan translation - work-in-progress patch v0.6
=========================================================================

Apply to:  Popful Mail (Japan).sfc   (1 MB, no copier header, CRC32 88E5BCDF)
Result:    2 MB LoROM, CRC32 964E08DD
Formats:   popful_mail_en_v0.6.bps (recommended, verifies the source ROM)
           popful_mail_en_v0.6.ips (same result, no source check)
Both checked with Flips; the patched ROM boots and plays in snes9x.

As with earlier versions, emulator save states made with an older patch
can show wrong text. In-game saves carry over fine.

New since v0.4
--------------
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
- The item-count suffix on the status screen ("ORANGE 1" followed by a
  kana counter) is still Japanese.
- The ending and credits were checked with a debug jump, not by playing
  to the end.
- Mid- and late-game chapters have been checked by tools, and every
  message has been rendered in the text box, but they have not been
  played through.
