; STUFF.ASM -- put keys into the BIOS keyboard buffer, as if they had been
; typed, so that a program that reads the keyboard can be tested unattended.
; usage: STUFF keys        ^X stands for Ctrl-X:  STUFF xn   STUFF ^Cn
; At most 15 keys (the size of the buffer).  Needs an AT BIOS (INT 16h, 05h).
; Build: nasm -f bin -o STUFF.COM STUFF.ASM

        org     100h

        mov     si, 81h                 ; the command tail
skip:   lodsb
        cmp     al, ' '
        je      skip
next:   cmp     al, 13                  ; CR ends the tail
        je      done
        cmp     al, '^'
        jne     put
        lodsb                           ; ^C -> 03h
        and     al, 1Fh
put:    mov     cl, al                  ; CL = character, CH = scan code 0
        xor     ch, ch
        mov     ah, 05h                 ; store a keystroke in the buffer
        int     16h
        lodsb
        jmp     next
done:   mov     ax, 4C00h
        int     21h
