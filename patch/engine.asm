; Popful Mail (SFC) English translation — text engine changes
; Two 8px-wide letters are packed into each 16x16 character slot.
lorom

!half    = $16F0      ; 0 = next letter starts a new slot, 1 = next letter fills right half
!tmp     = $16F2      ; scratch word
!cnt     = $16F4      ; loop counter
!lines   = $16F6      ; line breaks issued in the current box

; ---------------------------------------------------------------- hooks in bank $00
org $00F0C9           ; command byte path: finalize a half-filled slot first
    JSL FinalizeLoadCmd   ; replaces LDA $0000,X / CMP #$FF
    NOP

org $00F0ED           ; normal character path (A = char, M8 X16, Y = $1B00 list index)
    JSL BodyChar
    db $80,$13        ; BRA $F106 (slot-count check; INC $5F is done inside BodyChar)

org $00EEDE           ; name-label character path (A = char)
    JSL NameChar
    db $80,$0C        ; BRA $EEF0 (INX / loop)
org $00EEF3           ; name-label terminator
    JSL NameEnd       ; does STX $63 / LDA #$12
    ; JMP $EE63 follows (original bytes at $EEF7)

org $00EE8A           ; portrait speaker name (fixed 3-glyph JP names) -> 6-letter English names
    JSL PortName
    JMP $EEA9

org $00C26F           ; scene stream loader: decompress, then apply RAM patches from $20:C000
    JML SceneLoad
    NOP : NOP : NOP

org $00F0AF           ; builder entry: reset per-box line counter
    JSL BoxStart
    NOP : NOP
org $00EEAE           ; builder newline (20 0B): page to a new box when the window is full
    JSL NewLine           ; returns A = $5F and flags of CMP #$0F, like the original

org $00EFB9           ; number printer (20 19): draw digits as packed 8-px letters
    LDA $0702,x
    JSL DigitChar
    db $80,$15         ; BRA $EFD7
    ; leftover original bytes up to $EFD6 are skipped

; ---------------------------------------------------------------- new code in bank $20
org $208000
; A = char code. Original code did: LDA $075A ASL ASL ADC #$21 -> attribute byte
BodyChar:
    PHA
    LDA.w !half : BNE .second
    LDA $075A : ASL : ASL : CLC : ADC #$21 : STA $1B01,y
    JSR SlotTile : STA $1B00,y
    INY : INY
    PLA
    JSR DrawLeft
    LDA #$01 : STA.w !half
    INC $5F
    RTL
.second:
    PLA
    JSR DrawRight
    STZ.w !half
    INC $0758
    RTL

NameChar:
    PHA
    LDA.w !half : BNE .second
    LDA #$25 : STA $1B01,y
    JSR SlotTile : STA $1B00,y
    INY : INY
    PLA
    JSR DrawLeft
    LDA #$01 : STA.w !half
    RTL
.second:
    PLA
    JSR DrawRight
    STZ.w !half
    INC $0758
    RTL

NameEnd:
    JSR Finalize
    JSR NameRow
    STX $63
    LDA #$12
    RTL

FinalizeLoadCmd:
    LDA $0000,x
    CMP #$19 : BEQ +                      ; number and pause commands continue the current cell
    CMP #$13 : BEQ +
    JSR Finalize
+   LDA $0000,x
    CMP #$FF
    RTL

Finalize:             ; close a half-filled slot
    PHA
    LDA.w !half : BEQ +
    STZ.w !half
    INC $0758
+   PLA
    RTS

SlotTile:             ; = $0758*4 + $10 (same as $00:8C78)
    LDA $0758 : ASL : ASL : CLC : ADC #$10
    RTS

; ---- glyph copy: left 8px column of glyph (A) -> left or right half of current slot
DrawLeft:
    PHX : PHY
    JSR GlyphSrc            ; X = font offset
    JSR SlotDst             ; Y = slot buffer offset
    PHB : LDA #$7E : PHA : PLB
    REP #$20
    LDA #$0008 : STA.w !tmp
-   LDA $7F8000,x : STA $9100,y
    LDA $7F8100,x : STA $9120,y
    LDA #$0000 : STA $9110,y : STA $9130,y   ; clear right half
    INX : INX : INY : INY
    DEC.w !tmp : BNE -
    SEP #$20
    PLB
    PLY : PLX
    RTS

DrawRight:
    PHX : PHY
    JSR GlyphSrc
    JSR SlotDst
    PHB : LDA #$7E : PHA : PLB
    REP #$20
    LDA #$0008 : STA.w !tmp
-   LDA $7F8000,x : STA $9110,y
    LDA $7F8100,x : STA $9130,y
    INX : INX : INY : INY
    DEC.w !tmp : BNE -
    SEP #$20
    PLB
    PLY : PLX
    RTS

GlyphSrc:               ; X = ((c&$F8)<<6) + ((c&7)<<5) + $0756(word); then $0757 = 0
    REP #$20
    AND #$00FF : PHA
    AND #$00F8 : ASL : ASL : ASL : ASL : ASL : ASL : STA.w !tmp
    PLA : AND #$0007 : ASL : ASL : ASL : ASL : ASL
    CLC : ADC.w !tmp : CLC : ADC $0756
    TAX
    SEP #$20
    STZ $0757
    RTS

SlotDst:                ; Y = $0758 * 64
    REP #$20
    LDA $0758 : AND #$00FF
    ASL : ASL : ASL : ASL : ASL : ASL
    TAY
    SEP #$20
    RTS

; ---- message starter used by the resident text code (was: bank hardcoded to $7E)
; called with A = message index (8-bit), returns with SEP #$30 like the original
MsgStart:
    ASL : TAX
    PHB
    LDA $7EC005 : STA $0736 : PHA : PLB
    REP #$31
    TXA : ADC $7EC003 : TAX
    LDA $0000,x : STA $0734
    SEP #$30
    PLB
    RTL

; ---- speaker name for portrait commands 20 08/09/0A ($5A = index 0..2)
PortName:
    REP #$20
    LDA $5A : AND #$00FF : ASL : STA.w !tmp : ASL : CLC : ADC.w !tmp
    TAX
    SEP #$20
    LDA #$06 : STA.w !cnt
-   LDA.l PortNames,x : BEQ +
    JSL NameChar
+   INX
    DEC.w !cnt : BNE -
    JSR Finalize
    JSR NameRow
    RTL
PortNames:
    db "Mail",0,0
    db "Tatto",0
    db "Gaw",0,0,0

; ---- local message starters (24-byte pattern 8B A9 7E 48 AB 8D 36 07 C2 31 8A|98 6D 03 C0 AA BD 00 00 8D 34 07 E2 30 AB)
MsgStartX:              ; X = index*2 (8-bit regs on entry)
    PHB
    REP #$31
    TXA
    BRA MsgStartCommon
MsgStartY:              ; Y = index*2
    PHB
    REP #$31
    TYA
MsgStartCommon:
    AND #$00FF
    ADC $7EC003 : TAX
    SEP #$20
    LDA $7EC005 : STA $000736 : PHA : PLB
    REP #$20
    LDA $0000,x : STA $000734
    SEP #$30
    PLB
    RTL

; ---- scene loader tail: decompress stream to $7E:C000, then patch it in RAM
; patch directory at $20:C000: [bank, index, ptr16]..., $FF
; patch list (bank $20): [dest16 (in $7E), count8, bytes...]..., $FFFF
SceneLoad:
    LDA #$7E : STA $05
    JSL $0091EA
    PHP
    REP #$30 : PHA : PHX : PHY : PHB
    SEP #$20
    LDA #$20 : PHA : PLB
    LDX #$C000
.find:
    LDA $0000,x : CMP #$FF : BEQ .done
    CMP.l $000241 : BNE .next
    LDA $0001,x : CMP.l $000240 : BNE .next
    REP #$20
    LDA $0002,x : TAY
.rec:
    REP #$20
    LDA $0000,y : CMP #$FFFF : BEQ .done
    TAX
    SEP #$20
    LDA $0002,y : STA.w !cnt
    INY : INY : INY
.byte:
    LDA $0000,y : STA $7E0000,x
    INY : INX
    DEC.w !cnt : BNE .byte
    BRA .rec
.next:
    INX : INX : INX : INX
    BRA .find
.done:
    REP #$30 : PLB : PLY : PLX : PLA
    PLP
    RTL

BoxStart:
    STZ $0740 : STZ $0741
    STZ.w !lines
    STZ.w !half
    RTL

; field window: name row + 3 text rows; cutscene window ($0754 != 0): name row + 2 text rows
NewLine:
    LDA $5F : CMP #$0F : BCS .ret        ; auto-wrap call at 15 slots: nothing is emitted
    INC.w !lines
    LDA $0754 : BEQ .field
    LDA.w !lines : CMP #$03 : BCS .page
    BRA .ok
.field:
    LDA.w !lines : CMP #$04 : BCS .page
.ok:
    LDA $5F : CMP #$0F
.ret:
    RTL
.page:                                    ; abandon this newline: end the box here (like 20 0C)
    PLA : PLA : PLA                       ; our JSL return
    PLA : PLA                             ; JSR return into the builder dispatch
    LDX $63                               ; X -> the 0B byte; caller does INX / STX $0734
    JML $00F114                           ; PLB : SEC : RTL  (box end)

NameRow:                                  ; a speaker name at the top of a box occupies the first row
    PHA
    LDA.w !lines : BNE +
    LDA #$01 : STA.w !lines
+   PLA
    RTS

DigitChar:                                ; A = ASCII digit or ' ' (zero-suppressed lead) from the number buffer
    CMP #$20 : BNE +
    RTL                                   ; leading blanks are dropped; the English text supplies spacing
+   JML BodyChar

; ---- shop / save yes-no box ($00:EA1C draws it with immediate tile words): YES / NO in the menu font
org $00EA57 : dw $2C39        ; Y   (selected row uses palette 3)
org $00EA5D : dw $2C25        ; E
org $00EA63 : dw $2C33        ; S
org $00EA72 : dw $202E        ; N
org $00EA78 : dw $202F        ; O
org $00EA7E : dw $2020        ;
org $00EA86 : dw $2039        ; Y   (NO selected)
org $00EA8C : dw $2025        ; E
org $00EA92 : dw $2033        ; S
org $00EAA1 : dw $2C2E        ; N
org $00EAA7 : dw $2C2F        ; O
org $00EAAD : dw $2C20        ;

; ---- play time: minutes keep their leading zero ("2:01", not "2: 1")
; the number printer leaves a space for a leading zero; A is 16-bit here, low byte = tens digit
org $008A78                   ; pause screen: LDA $0706 / STA $079D
    JSL MinFixPause
    NOP : NOP
org $20F500
MinFixPause:
    LDA $0706
    JSR ZeroLead
    STA $079D
    RTL
MinFixSave:                   ; save list (17#3): replaces LDA $0706 / STA $7E26CD
    LDA $0706
    JSR ZeroLead
    STA $7E26CD
    RTL
MinFixTitle:                  ; title-screen continue list (1A#0): replaces LDA $0706 / STA $7E3229
    LDA $0706
    JSR ZeroLead
    STA $7E3229
    RTL
ZeroLead:
    PHA
    AND.w #$00FF
    CMP.w #$0020
    BEQ +
    PLA
    RTS
+   PLA
    AND.w #$FF00
    ORA.w #$0030
    RTS

; ---- status screen: equipment label per character (SWORD / M.ROD / ATTACK)
; 17#3's name-drawing sequence is replaced by LDA $0736 : PHA : JSL StatusLabel + NOPs.
; Blanks the 5-letter name field (names now differ in length, so cycling characters left
; letters behind), draws the name as before, then the label at row 15, column 2 of the same
; page, with the menu-font string routine (chars are ASCII - $20, so ' ' is the blank tile and
; 0 ends the string).
StatusLabel:                  ; 8-bit A/X/Y; the caller has already pushed $0736
    LDA $0732 : PHA
    LDA $0733 : PHA
    LDA #$20 : STA $0736
    LDA #$20 : STA $0731
    LDA.b #StatusLabels : STA $0732
    LDA.b #StatusLabels>>8 : STA $0733
    LDA #$06 : STA $0730      ; entry 3: blank name
    LDA #$04
    LDY #$31
    JSL $00F1A4
    PLA : STA $0733
    PLA : STA $0732
    STZ $0731
    LDA $0202 : ASL : ADC #$0A : STA $0730
    LDA #$00 : STA $0736
    LDA #$04
    LDY #$31
    JSL $00F1A4
    LDA $0730 : PHA
    LDA $0731 : PHA
    LDA $0732 : PHA
    LDA $0733 : PHA
    LDA #$20 : STA $0736
    LDA #$20 : STA $0731
    LDA.b #StatusLabels : STA $0732
    LDA.b #StatusLabels>>8 : STA $0733
    LDA $0202 : ASL : STA $0730
    LDA #$0F
    LDY #$22
    JSL $00F1A4
    PLA : STA $0733
    PLA : STA $0732
    PLA : STA $0731
    PLA : STA $0730
    LDA #$00 : STA $0736
    RTL
StatusLabels:
    dw .mail, .tatto, .gaw, .blank
.mail:  db "SWORD ", 0
.tatto: db "M.ROD ", 0     ; the period sits at the left of its tile, so no space after it
.gaw:   db "ATTACK", 0
.blank: db "     ", 0

; ---- Castle Alcazar story scroll (scene 17#7): English line builder
; The scene's own routine ($7E:CC1E) reads its Japanese text straight from RAM ($7E:D7F5,x) and draws
; one 16-px cell per character.  This replacement is copied by the scene RAM patches over that
; (no longer used) Japanese text at $7E:D800, and the scene jumps here from $CC30.  It reads the
; English text from ROM ($28:D000, filled by the builder: char codes, $FE = end of line, $FF = end)
; and packs two 8-px letters per cell, keeping the scene's own tile bookkeeping and flush ($CCFD).
; Entry: DBR=$7E, A 8-bit, X/Y 16-bit, Y=0 (line tilemap index), $63 = text index.
org $28C000
base $7ED800
ScrollLine:
    LDX $63
    STZ $5F
    STZ $0757
    STZ.w ScrHalf
.next
    LDA.l ScrollText,x
    INX
    CMP #$FE : BEQ .eol
    CMP #$FF : BEQ .end
    JSR ScrLetter
    BRA .next
.eol
    LDA.w ScrHalf : BEQ +      ; a half-filled cell is finished too
    PHX : JSR ScrDone : PLX
+   STX $63
    CLC
    JMP $CC4E                  ; SEP #$10 : PLB : RTS
.end
    LDA.w ScrHalf : BEQ +
    JSR ScrDone
+   SEC
    JMP $CC4E

ScrDone:                       ; a cell is complete: next cell; when the cell pool wraps, the routine at
    INC $5F                    ; $CCFD sends the staged cells to VRAM - only after BOTH halves are staged
    LDA $0758 : INC : CMP #$80 : BCC +
    LDA $60 : JSR $CCFD
    LDA #$01 : STA $60 : STZ $5F
+   STA $0758
    STZ.w ScrHalf
    RTS

ScrLetter:                     ; A = char code; Y = tilemap index (kept)
    PHX
    PHA
    LDA.w ScrHalf : BNE .right
    REP #$20                   ; new cell: staging offset = $5F * 64
    LDA $5F : AND #$00FF : XBA : LSR : LSR : STA.w ScrStage
    STZ.w ScrOff
    SEP #$20
    PLA : JSR ScrCopy
    REP #$20                   ; clear the right half of the cell
    LDA.w ScrStage : CLC : ADC #$0010 : PHY : TAY
    SEP #$20
    LDA #$10 : STA $5A
-   LDA #$00 : STA $9000,y : STA $9020,y
    INY : DEC $5A : BNE -
    PLY
    REP #$20                   ; tilemap entries for the cell (as the original)
    LDA $0758 : AND #$00FF : ASL : ASL : ORA #$2000
    STA $1B00,y : INC : STA $1B02,y : INC : STA $1B40,y : INC : STA $1B42,y
    SEP #$20
    INY : INY : INY : INY
    LDA #$01 : STA.w ScrHalf
    PLX
    RTS
.right
    REP #$20
    LDA #$0010 : STA.w ScrOff
    SEP #$20
    PLA : JSR ScrCopy
    JSR ScrDone
    PLX
    RTS

ScrCopy:                       ; copy the left 8 px (top + bottom tile) of glyph A into the cell half
    PHY
    REP #$20
    AND #$00FF : PHA
    AND #$00F8 : ASL : ASL : ASL : ASL : ASL : ASL : STA $5A
    PLA : AND #$0007 : ASL : ASL : ASL : ASL : ASL
    CLC : ADC $5A : CLC : ADC $0756 : TAX
    LDA.w ScrStage : CLC : ADC.w ScrOff : TAY
    SEP #$20
    LDA #$10 : STA $5A
-   LDA $7F8000,x : STA $9000,y
    LDA $7F8100,x : STA $9020,y
    INX : INY : DEC $5A : BNE -
    PLY
    RTS

ScrHalf:  db 0
ScrOff:   dw 0
ScrStage: dw 0
ScrollEnd:
base off

org $28D000
ScrollText:
    db $FF
