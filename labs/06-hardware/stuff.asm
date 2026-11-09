; STUFF.COM - put keystrokes into the BIOS keyboard buffer (lab helper)
;   STUFF text      each character becomes one keystroke; ^X means Ctrl-X
;                   (^M = Enter, ^H = Backspace, ^C = Ctrl-C, ^Z = Ctrl-Z, ^[ = Esc);
;                   ~XX (two hex digits) is a key with scan code XX and no ASCII
;                   code, for example ~48 = Up arrow, ~3B = F1
; Uses INT 16h AH=05h (store keystroke), which AT-class BIOSes provide. The buffer
; holds 15 keystrokes. Programs run afterwards read the keys as if they were typed.
; nasm -f bin -o STUFF.COM stuff.asm
        cpu     8086
        org     100h

        mov     si, 81h                 ; command tail (length byte at 80h)
        mov     bl, [80h]
        xor     bh, bh
        mov     byte [si+bx], 0         ; terminate it (replaces the CR)
skip:   lodsb
        cmp     al, ' '
        je      skip
next:   or      al, al
        jz      done
        cmp     al, '~'
        je      scan
        cmp     al, '^'
        jne     store
        lodsb                           ; ^X -> X AND 1Fh
        or      al, al
        jz      done
        and     al, 1Fh
store:  mov     cl, al                  ; CL = ASCII code
        xor     ch, ch                  ; CH = scan code (0: DOS only looks at ASCII)
put:    mov     ah, 05h
        int     16h
        or      al, al                  ; AL = 1: buffer full
        jnz     full
        lodsb
        jmp     next
scan:   call    hexdig                  ; ~XX: CH = scan code, CL = 0
        mov     ch, al
        mov     cl, 4
        shl     ch, cl
        call    hexdig
        or      ch, al
        xor     cl, cl
        jmp     put
full:   mov     dx, msg_full
        mov     ah, 09h
        int     21h
done:   mov     ax, 4C00h
        int     21h

hexdig: lodsb                           ; one hex digit at DS:SI -> AL = 0..15
        sub     al, '0'
        cmp     al, 9
        jbe     .ok
        and     al, 0DFh                ; 'a'-'f' -> 'A'-'F' (after the subtraction)
        sub     al, 7
.ok:    and     al, 0Fh
        ret

msg_full db     "STUFF: keyboard buffer full", 13, 10, "$"
