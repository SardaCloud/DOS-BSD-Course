; RC.ASM -- exit with the number typed on the command line ("RC 44").
; A helper for section 9.4 and the labs, complete as given.
; Build: nasm -f bin -o RC.COM RC.ASM
; The number is kept in 16 bits; only its low byte (AL) reaches DOS.

        org     100h

        mov     si, 81h         ; command tail: text after the length byte at 80h
        xor     bx, bx          ; BX = the number so far
skip:   lodsb
        cmp     al, ' '
        je      skip
digit:  sub     al, '0'
        cmp     al, 9
        ja      done            ; the CR at the end (or any non-digit) stops
        xor     ah, ah
        push    ax
        mov     ax, 10
        mul     bx              ; AX = BX * 10 (the high word in DX is dropped)
        pop     bx
        add     bx, ax          ; BX = BX * 10 + digit
        lodsb
        jmp     digit
done:   mov     al, bl          ; AL = exit code
        mov     ah, 4Ch         ; terminate with return code
        int     21h
