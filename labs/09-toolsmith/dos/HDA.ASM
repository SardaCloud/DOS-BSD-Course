; HDA.ASM -- hex dump of standard input in the format of FreeBSD's hd
; (hexdump -C), without the "*" for repeated lines.  MS-DOS .COM program,
; 8086 instructions only.  Build: nasm -f bin -o HDA.COM HDA.ASM

        org     100h

nextln: xor     bp, bp                  ; BP = bytes in this line so far
fill:
; TODO: read the rest of the line (16 - BP bytes) from handle 0 into
;       data + BP with function 3Fh.  On an error go to failed; when 0 bytes
;       come back go to eof; otherwise add them to BP and read again until
;       BP is 16: a pipe or the console may return fewer bytes than asked for.
eof:    or      bp, bp
        jz      finish
        call    putline
        add     [offset], bp            ; 32-bit offset += bytes in the line
        adc     word [offset+2], 0
        cmp     bp, 16
        je      nextln

finish: mov     ax, [offset]            ; the final offset, if there was input
        or      ax, [offset+2]
        jz      done
        mov     di, line
        call    putoff
        call    endline
done:   mov     ax, 4C00h               ; exit code 0
        int     21h
failed: mov     ax, 4C01h               ; exit code 1: the read failed
        int     21h

; putline: format and write one line for the BP bytes at data.
putline:
        mov     di, line
        call    putoff
        mov     al, ' '
        stosb
        xor     si, si                  ; SI = index 0..15
.hex:   cmp     si, 8
        jne     .nogap
        mov     al, ' '                 ; extra blank between the halves
        stosb
.nogap: mov     al, ' '
        stosb
        cmp     si, bp
        jae     .blank
        mov     al, [data+si]
        call    puthex
        jmp     .next
.blank: mov     al, ' '                 ; past the end of a short line
        stosb
        stosb
.next:  inc     si
        cmp     si, 16
        jb      .hex
        mov     ax, ' |'                ; with the STOSB: two blanks and '|'
        stosb
        stosw
        xor     si, si
.chr:   cmp     si, bp
        jae     .bar
        mov     al, [data+si]
        cmp     al, ' '
        jb      .dot
        cmp     al, '~'
        jbe     .put
.dot:   mov     al, '.'
.put:   stosb
        inc     si
        jmp     .chr
.bar:   mov     al, '|'
        stosb
        ; fall through to endline

; endline: append CR LF and write the line from line to DI.
endline:
        mov     ax, 0A0Dh               ; stores CR, then LF
        stosw
        mov     dx, line
        mov     cx, di
        sub     cx, dx
        mov     ah, 40h
        mov     bx, 1
        int     21h
        ret

; putoff: store the 32-bit offset as 8 hex digits at DI.
putoff: mov     al, [offset+3]
        call    puthex
        mov     al, [offset+2]
        call    puthex
        mov     al, [offset+1]
        call    puthex
        mov     al, [offset]
        ; fall through to puthex

; puthex: store AL as two hex digits at DI.
puthex: push    bx
        push    cx
        mov     bx, digits
        mov     ah, al
        mov     cl, 4
        shr     al, cl                  ; high nibble first
        xlat
        stosb
        mov     al, ah
        and     al, 0Fh
        xlat
        stosb
        pop     cx
        pop     bx
        ret

digits  db      '0123456789abcdef'
offset  dd      0
data    times 16 db 0
line:                                   ; up to 80 bytes after the program
