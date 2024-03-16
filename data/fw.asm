;
; 6502 firmware and OS
;

USER_START    = $0200   ; just above stack
CONSOLE_ADDR  = $e000   ; frame buffer
UART_ADDR     = $efff   ; ersatz UART
FW_ADDR       = $f000
SYSCALL_TABLE = $ff00
FW_VECTORS    = $fffa   ; per 6502 standard
SMC_PATCH     = $ffff   ; Label indicating self-modifying code sequence/address

NEWLINE = $0d

; START HERE

    .org FW_ADDR
init:
    jsr init_console
    
    lda #0
    sta cursor_x
    lda #0
    sta cursor_y
    jsr recalc_console
    jsr _print_imm
    .byte "+"
    .byte $00

    lda #79
    sta cursor_x
    lda #0
    sta cursor_y
    jsr recalc_console
    jsr _print_imm
    .byte "+"
    .byte $00
    
    lda #0
    sta cursor_x
    lda #24
    sta cursor_y
    jsr recalc_console
    jsr _print_imm
    .byte "+"
    .byte $00

    lda #79
    sta cursor_x
    lda #24
    sta cursor_y
    jsr recalc_console
    jsr _print_imm
    .byte "+"
    .byte $00

    lda #30
    sta cursor_x
    lda #14
    sta cursor_y
    jsr recalc_console
    jsr _print_imm
    .byte "*** DerpyOS 0.1 ***"
    .byte $00

    lda #0
    sta cursor_x
    lda #24
    sta cursor_y
    jsr recalc_console
    jsr _print_imm
    .byte "*"
    .byte NEWLINE
    .byte $00

    jmp _barf

    jsr USER_START

    jsr _print_imm
    .byte "BACK AGAIN"
    .byte $00

_barf:
    jmp _barf

; ***
;
; SYSCALL_TABLE = $FF00
;
; Print immediate message, as follows:
;
; SYS_PRINT_IMM = SYSCALL_TABLE+0
;
;  jsr SYS_PRINT_IMM
;  .byte "IMMEDIATE MESSAGE"
;  .byte $00
;  <your-next-instruction>
;
; ***

_print_imm:
    pla            ; NOTE: stack now invalidated
    sta primmaddr
    pla
    sta primmaddr+1
pi_next:
    inc primmaddr
    bne pi_skip
    inc primmaddr+1
pi_skip:
primmaddr = *+1    ; after opcode next
    lda SMC_PATCH  ; this addr will be patched
    beq pi_done    ; zero byte terminates
    jsr _emit
    jmp pi_next

pi_done:
    lda primmaddr+1
    pha
    lda primmaddr
    pha
    rts
; end _print_imm

;
; EMIT : write to console at cursor_x, cursor_y
;        advances cursor, including newline
;
;  Argument in A
;
;  Stolen liberally from here https://github.com/MagerValp/u4remastered/blob/master/src/patchedgame/subs.s

CONS_COLUMNS = 80
CONS_ROWS = 25

_emit:
    cmp #NEWLINE
    beq emit_newline  ; chains

    sta emit_char        ; save off char to write - A now scratch
    lda cursor_x
    cmp #CONS_COLUMNS    ; >= carry bit set.  == zero bit set
    bcc drawchar
    jsr emit_newline

emit_char = *+1
drawchar:
    lda #<SMC_PATCH
    
emit_addr = *+1
    sta SMC_PATCH

    inc emit_addr
    bne dc_skip
    inc emit_addr+1
dc_skip:
    inc cursor_x
    rts

emit_newline:
    lda #0
    sta cursor_x
    inc cursor_y        ; not gonna roll over
    lda cursor_y
    cmp #CONS_ROWS
    bcc do_recalc       ; cmp cc -> register < operand
    lda #CONS_ROWS      ; more than CONS_ROWS - reset to CONS_ROWS
    sta cursor_y
    jsr scroll_console
do_recalc:
    jmp recalc_console
    

; Preserves X
recalc_console:
    txa
    pha
    lda cursor_y
    asl                 ; each table entry is two bytes
    tax
    lda c_table,x
    sta emit_addr
    lda c_table+1,x
    sta emit_addr+1
    lda cursor_x
    adc emit_addr       ; TODO must be a way to combine with above
    sta emit_addr
    bcc ns_skip
    inc emit_addr+1
ns_skip:
    pla
    tax
    rts

;
; scroll_console: move everything up by one row (CONS_COLUMNS bytes in array)
;
; Preserves A, X, Y
; Uses m_to, m_from
;
scroll_console:
    pha
    txa
    pha
    tya
    pha
    lda #<CONSOLE_ADDR
    sta m_to
    lda #>CONSOLE_ADDR
    sta m_to+1
    lda #<CONSOLE_ADDR+CONS_COLUMNS
    sta m_from
    lda #>CONSOLE_ADDR+CONS_COLUMNS
    sta m_from+1

    ; 80x25 = 2000 ; 2000 - 80 = 1920 ; 1920 / 256 = 7.5 ; 7 iterations plus 128
    ldy #7
scroll_loop:
    ldx #$ff    ; number of bytes
    jsr move_mem
    dey
    bne scroll_loop
    pla
    tax
    pla
    tay
    rts

;
;
;  Input: X is quantity, counts down
;  Caller sets m_from and m_to

move_mem:
m_from = *+1
    lda SMC_PATCH
m_to = *+1
    sta SMC_PATCH
    dex
    beq m_done
    inc m_from
    bne mfrom_skip
    inc m_from+1
mfrom_skip:
    inc m_to
    bne mto_skip
    inc m_to+1
mto_skip:
    dex
    bne m_done
    jmp move_mem
m_done:
    rts

;
; Initialization Routines
;

init_console:
    lda #<CONSOLE_ADDR
    sta emit_addr
    lda #>CONSOLE_ADDR
    sta emit_addr+1
    rts

;
; Data
;

cursor_x:
    .byte 0
cursor_y:
    .byte 0
c_table:                    ; Frame buffer, ptr for each row
    .word CONSOLE_ADDR      ; 0
    .word CONSOLE_ADDR+80
    .word CONSOLE_ADDR+160
    .word CONSOLE_ADDR+240
    .word CONSOLE_ADDR+320
    .word CONSOLE_ADDR+400  ; 5
    .word CONSOLE_ADDR+480
    .word CONSOLE_ADDR+560
    .word CONSOLE_ADDR+640
    .word CONSOLE_ADDR+720
    .word CONSOLE_ADDR+800  ; 10
    .word CONSOLE_ADDR+880
    .word CONSOLE_ADDR+960
    .word CONSOLE_ADDR+1040
    .word CONSOLE_ADDR+1120
    .word CONSOLE_ADDR+1200 ; 15
    .word CONSOLE_ADDR+1280
    .word CONSOLE_ADDR+1360
    .word CONSOLE_ADDR+1440
    .word CONSOLE_ADDR+1520
    .word CONSOLE_ADDR+1600 ; 20
    .word CONSOLE_ADDR+1680
    .word CONSOLE_ADDR+1760
    .word CONSOLE_ADDR+1840
    .word CONSOLE_ADDR+1920 ; 24

; TODO: pattern is (y div 5)*400 + (y modulo 5)*80  has to be a way to leverage that

;
; SYSCALL TABLE : three bytes apiece
;

    .org SYSCALL_TABLE
    jmp _print_imm     ; Index 0 : PRINT_IMM
    jmp _emit          ; Index 3 : EMIT

;
; VECTOR TABLE
;

    .org FW_VECTORS
    .word init  ; NMI vector
    .word init  ; Reset vector  LAUNCHES HERE
    .word init  ; IRQ vector

    .end

; EOF
