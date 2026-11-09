; hello4.asm - Lab 4.4: NASM, handles and an exit code (MS-DOS .COM)
; nasm -f bin -o HELLO4.COM hello4.asm
        cpu     8086
        org     100h                    ; .COM: loaded at offset 100h

        mov     ah, 40h                 ; INT 21h 40h: write to a handle
        mov     bx, 1                   ; handle 1: standard output
        mov     cx, msglen              ; byte count, so '$' is allowed
        mov     dx, msg                 ; DS:DX -> the bytes
        int     21h
        jc      fail                    ; CF=1: AX holds an error code
        mov     ah, 40h
        mov     bx, 2                   ; handle 2: standard error
        mov     cx, errlen
        mov     dx, err
        int     21h
        mov     ax, 4C03h               ; 4Ch: exit, AL = exit code 3
        int     21h
fail:   mov     ah, 4Ch                 ; exit code = DOS error code
        int     21h

msg     db      'Price: $5, on handle 1', 13, 10
msglen  equ     $ - msg
err     db      'A note on handle 2', 13, 10
errlen  equ     $ - err
