; CCTEST.ASM -- what does Ctrl-C at the ASK prompt return?  (instructor test)
; Puts Ctrl-C in the keyboard buffer, runs "ASK YN Continue" with EXEC and
; prints the exit type and exit code that function 4Dh returns.  INT 23h
; points to a handler that tells DOS to abort the program (STC, RETF), which
; is what COMMAND.COM does at the command line or after "Y" in a batch file.
; Build: nasm -f bin -o CCTEST.COM CCTEST.ASM

        org     100h

        mov     ah, 4Ah                 ; keep 64 KB, free the rest for ASK
        mov     bx, 1000h
        int     21h
        mov     ax, 2523h               ; INT 23h -> onbreak
        mov     dx, onbreak
        int     21h
        mov     ah, 05h                 ; type Ctrl-C (03h, scan code 0)
        mov     cx, 0003h
        int     16h
        mov     [pb_tail+2], cs
        mov     [pb_fcb1+2], cs
        mov     [pb_fcb2+2], cs
        mov     [savesp], sp
        mov     ax, 4B00h               ; load and run ASK.COM
        mov     dx, path
        mov     bx, pblock
        int     21h
        mov     bx, cs                  ; EXEC may not keep SS:SP
        cli
        mov     ss, bx
        mov     sp, [cs:savesp]
        sti
        mov     ds, bx
        mov     es, bx
        jc      failed
        mov     ah, 4Dh                 ; AH = exit type, AL = exit code
        int     21h
        mov     [result], ax
        mov     dx, msg1
        call    puts
        mov     al, [result+1]
        call    putdec
        mov     dx, msg2
        call    puts
        mov     al, [result]
        call    putdec
        mov     dx, crlf
        call    puts
        mov     ax, 4C00h
        int     21h
failed: mov     dx, msgf
        call    puts
        mov     ax, 4C01h
        int     21h

onbreak:
        stc                             ; carry set and RETF: abort
        retf

puts:   mov     ah, 09h                 ; DS:DX -> '$'-terminated text
        int     21h
        ret

putdec: xor     ah, ah                  ; AL as a decimal number
        mov     bl, 10
        xor     cx, cx
.div:   div     bl
        push    ax                      ; AH = remainder
        inc     cx
        xor     ah, ah
        or      al, al
        jnz     .div
.out:   pop     dx
        mov     dl, dh
        add     dl, '0'
        mov     ah, 02h
        int     21h
        loop    .out
        ret

pblock: dw      0                       ; environment: a copy of ours
pb_tail: dw     tail, 0
pb_fcb1: dw     fcb, 0
pb_fcb2: dw     fcb, 0
tail:   db      12, ' YN Continue', 13
fcb:    times 16 db 0
path:   db      'ASK.COM', 0
msg1:   db      13, 10, 'ASK ended: exit type $'
msg2:   db      ', exit code $'
msgf:   db      'EXEC failed', 13, 10, '$'
crlf:   db      13, 10, '$'
savesp: dw      0
result: dw      0
