; SCREEN.COM - copy the 80x25 text screen (video memory at B800:0000) to COM1, one line per row.
; Lets tools/dos_run.py capture messages printed before AUTOEXEC.BAT ran (for example by SYSINIT).
; nasm -f bin -o SCREEN.COM screen.asm
        cpu     8086
        org     100h

        mov     dx, com1
        mov     ax, 3D01h               ; open "COM1" for writing
        int     21h
        jc      done
        mov     [handle], ax
        xor     si, si                  ; offset into video memory
        mov     cx, 25                  ; rows
row:    push    cx
        mov     di, line
        mov     cx, 80
        mov     bx, line                ; end of the text so far (trailing blanks trimmed)
        push    ds
        mov     ax, 0B800h
        mov     ds, ax
col:    lodsw                           ; AL = character, AH = attribute
        mov     [es:di], al
        inc     di
        cmp     al, ' '
        je      blank
        mov     bx, di
blank:  loop    col
        pop     ds
        sub     bx, line                ; trailing blanks trimmed
        mov     di, line
        add     di, bx
        mov     word [di], 0A0Dh        ; CR LF
        lea     cx, [bx+2]
        mov     dx, line
        mov     bx, [handle]
        mov     ah, 40h
        int     21h
        pop     cx
        loop    row
        mov     bx, [handle]
        mov     ah, 3Eh
        int     21h
done:   mov     ax, 4C00h
        int     21h

com1    db      'COM1', 0
handle  dw      0
line    times 82 db 0
