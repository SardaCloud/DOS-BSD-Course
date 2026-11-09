; hello9.asm - Lab 4.4: the DEBUG program again, written for NASM
; nasm -f bin -o HELLO9.COM hello9.asm
        cpu     8086
        org     100h

        mov     ah, 9                   ; print a '$'-terminated string
        mov     dx, msg
        int     21h
        mov     ax, 4C00h               ; exit with code 0
        int     21h

msg     db      'Hello from NASM', 13, 10, '$'
