; Hello World

; TODO: macros and includes
SYSCALL_TABLE = $FF00
SYS_PRINT_IMM = SYSCALL_TABLE+0

    .ORG $200

    jsr SYS_PRINT_IMM
    .byte "Hello world!"
    .byte $0D
    .byte $00

    rts

; EOF
