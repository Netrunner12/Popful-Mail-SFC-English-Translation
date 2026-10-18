Popful Mail (SFC) - English fan translation - patch v1.0
=========================================================================

Apply to:  Popful Mail (Japan).sfc   (1 MB, no copier header, CRC32 88E5BCDF)
Result:    2 MB LoROM, CRC32 6616CC3A
Formats:   popful_mail_en_v1.0.bps (recommended, verifies the source ROM)
           popful_mail_en_v1.0.ips (same result, no source check)
Both checked by applying them to the original ROM; the result boots and
plays in snes9x.

As with earlier versions, emulator save states made with an older patch
can show wrong text. In-game saves carry over fine.

New since v0.17 (v1.0: complete)
--------------------------------
- Green narration boxes: every one starts on the second line of the box
  and each line is centred under the one above it (tavern sign, big
  stone, "You hear something / from up above.", "The door creaked
  open.", the beastie's voice behind the door, the Waterway Man's kid).
- "This rock seems loose."
- The whole game has been played through to "THE END?".

New since v0.16 (ending and credits)
-------------------------------------
- Fixed the black screen at the very end: after Blacky and Maril's last
  lines the game crashed instead of showing "Ha-ha-ha-ha-ha..." and
  "THE END?". The patch had left out the ending's last line of text.
- Credits headings: PROGRAMMING, ART & GRAPHICS, DIRECTION and PRODUCTION
  (were PROGRAM, ART & GRAPHIC, DIRECT, PRODUCE), drawn with letters from
  the original lettering. The SCENARIO names are evenly spaced.
- "Hm" is now "Hmm" everywhere (12 lines).
- Status screen: LGT SABER (was LT SABER).
- "Got the Gold Armor!" second line centred.
- Castle Alcazar: "My, he's a persistent fellow."; Tatto's lines about
  Maril read "Maril... She did it to save me...!" / "So I teleported her
  somewhere safe with magic, but I don't know where she ended up!!".
- Castle Alcazar: the loose wall Blacky's bomb opens now reads "This part
  of the wall / looks weak...".
  Note: emulator save states made during the ending or credits with an
  older patch can still show the old credits; in-game saves are fine.

New since v0.15 (Castle Alcazar story scroll)
---------------------------------------------
- The Waterway Man's story of the light goddess, the text that scrolls
  up the screen in front of the statue, is now in English. It was still
  Japanese: that scene draws its scroll with its own code, which read the
  Japanese text directly. The English follows the original line by line,
  each line centred.
  Note: an emulator save state made inside Castle Alcazar with an older
  patch still holds the old code and shows the Japanese scroll; use an
  in-game save, or a state from before entering the castle.
- The whole ROM was scanned for any other Japanese text the patch does
  not cover (besides the title logo): none was found.

New since v0.14 (Castle Alcazar and others)
-------------------------------------------
- Castle Alcazar: the loose-wall hint reads "This part of the wall /
  looks like it could crumble." (reworded again in v0.17); "A pile of rubble / blocks the way." no
  longer runs off the box; Ryuke's apology is split into two boxes ("Sisty... I'm sorry." / "I dragged you
  along on my selfish crusade...").
- Hagel Island: "Him", with the comma after the quotes; Gaw's version of
  that line now shows his name.
- The girl's line in Hagel Island depends on the hero: "What's wrong?
  I'm fine!" (Mail), "What's wrong, Big Brother Soldi?" (Tatto), "What's
  wrong, Mr. Beastie?" (Gaw) - Gaw's version used to run off the box.
- "Mail broke down the door / with the pickaxe!!" (and Tatto's version)
  sit better under each other.
- "(Rip and Rap are really / that old?!)" no longer starts one space in.
- Port Miine: the Material Horn poster's name is centred.
- Every message was checked automatically as each of the three heroes.

Note on save states: an emulator save state made with an older patch can
crash with a newer one (it carries old code in memory). In-game saves are
always safe across versions.

New since v0.13 (Hagel Island text)
-----------------------------------
- "Just you wait, Nuts Cracker!!" now has a comma after "wait".
- Maril's "...just Miss Mail..." line no longer starts one space in.

New since v0.12 (Hagel Island crash fix)
----------------------------------------
- Fixed a crash after the Dokken fight on Hagel Island: after "From
  somewhere, a voice rang out." the screen went black (or froze) instead
  of showing the voice's message. A piece of the game's event code still
  looked for the text where the Japanese version kept it.
  Note: an emulator save state made AFTER the fight (with the green box
  already on screen) still holds the old code and will crash; load an
  in-game save or a state from before the fight.

New since v0.11 (general / Gades Ruins fixes)
---------------------------------------------
- Status screen: each character's weapon label fits their weapon -
  SWORD for Mail, M.ROD for Tatto, ATTACK for Gaw - and is all white
  (one letter used to show in yellow).
- Status screen: cycling through the heroes no longer leaves letters of
  a longer name behind (MAILO, GAWTO).
- Port Miine's Nuts Cracker wanted poster is centred.
- "You were knocked back by an invisible wall." lines up properly.
- Marvela's line breaks so "here." is no longer on a line by itself.

New since v0.10 (Ancient Caves fixes)
-------------------------------------
- Green narration text (item pickups, locked doors, party changes and so
  on) is centred left to right on every line, as close to exact centre
  as the game's letter spacing allows.
- The Blacky logo that appears inside some lines is drawn as a proper
  symbol, with a space after it.
- Play time minutes keep their leading zero (2:01, not 2: 1) on the pause
  screen, the save list and the title screen's continue list.
- Dwarf contest display: DWARF is spelled out in full with a space, like
  MAIL.
- Line-break fixes: "Follow me!" on its own line; Maril's "Do you not...
  remember me?" with a pause; "I hardly recognized you." starts on its own line.
- Status screen: the equipment label reads WEAPON (it said SWORD for all
  three characters).
- Beastie shop: "Anything else ya need?" fits on one line.
- Beastie by the broken ladder: "...Hey! Let me finish what I was sayin',
  will ya!"

New since v0.9 (Port Miine / Jungle fixes)
------------------------------------------
- Locked doors say "The door is locked. / You can't get in."
- Mail's line about Material Horn now reads on into the next box:
  "Wait... the $2,000,000 bounty, Material Horn... is YOUR master?!"
- Highlighted names (Ancient Caves, Gades Ruins, Maril, START) no longer
  have extra gaps around them.
- Tatto joining the party: Mail's name now appears where she starts
  planning to use Tatto, and her next line has a short pause and reads
  as her making up her mind.
- Status screen: the name box is one letter wider, so TATTO fits.

New in v0.9
-----------
- World map: the destination name bubbles are in English (Port Miine,
  Jungle, Ancient Caves, Gades Ruins, Hagel Island, Castle Alcazar),
  drawn in a new pixel font in the style of the original lettering.
- The in-game save list (SELECT on the status screen) shows English area
  names.
- Locked houses now say "The door is locked. Nobody seems to live here."
- Receiving the Monster Card now reads "Received the Monster Card!"

New in v0.8
-----------
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
- Some staff-name readings in the credits could not be confirmed from a
  published source (see v0.6 notes). Corrections are welcome.
- Emulator save states made with an older version of the patch can show
  wrong text or crash; in-game saves are always safe across versions.
