;
; 6502 firmware and OS
;

USER_START    = $0200   ; just above stack
UART_ADDR     = $efff   ; ersatz UART
FW_ADDR       = $f000
SYSCALL_TABLE = $ff00
FW_VECTORS    = $fffa   ; per 6502 standard
SMC_PATCH     = $ffff   ; Label indicating self-modifying code sequence/address

NEWLINE = $0d

; START HERE

    .org FW_ADDR
init:
    jsr _print_imm
    .byte "Butlerian 0.1"
    .byte NEWLINE
    .byte NEWLINE
    .byte $00

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
; EMIT : write to Ersatz UART
;
;  Argument in A
;
_emit:
    sta UART_ADDR
    rts

;
; SYSCALL TABLE : three bytes apiece
;

    .org SYSCALL_TABLE
    jmp _print_imm     ; Index 0 : PRINT_IMM

;
; VECTOR TABLE
;

    .org FW_VECTORS
    .word init  ; NMI vector
    .word init  ; Reset vector  LAUNCHES HERE
    .word init  ; IRQ vector

    .end

; EOF
