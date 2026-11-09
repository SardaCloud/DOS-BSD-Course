; WCA.ASM -- count the lines, words and bytes of standard input, like WC with
; no file names.  32-bit counters.  MS-DOS .COM program.
; Build: nasm -f bin -o WCA.COM WCA.ASM

        org     100h

start:
readblk:
        mov     ah, 3Fh                 ; read up to 512 bytes from handle 0
        xor     bx, bx
        mov     cx, 512
        mov     dx, buf
        int     21h
        jc      failed
        or      ax, ax                  ; 0 bytes read: end of file
        jz      report
        add     [chars], ax             ; 32-bit add: low word, then the carry
        adc     word [chars+2], 0
        mov     cx, ax
        mov     si, buf
nextch: lodsb
; TODO: count each LF in [lines] and the first byte of each word in [words]
;       (a word byte is anything but ' ' and 9..13).  Keep the state in [inw],
;       because a word can go on in the next block.  The counters are 32-bit:
;       use ADD on the low word and ADC on the high word.
        loop    nextch
        jmp     readblk

report: mov     si, lines
        call    put32
        mov     si, words
        call    put32
        mov     si, chars
        call    put32
        mov     dx, crlf
        mov     cx, 2
        call    write
        mov     ax, 4C00h               ; exit code 0
        int     21h

failed: mov     ax, 4C01h               ; exit code 1: the read failed
        int     21h

; put32: print the 32-bit number at DS:SI in decimal, right-aligned in 8
; columns.  DX:AX / 10 is done as two 16-bit divisions, high word first.
put32:  mov     ax, [si]
        mov     dx, [si+2]
        mov     di, numend
        mov     bx, 10
.digit: mov     cx, ax                  ; CX = low word
        mov     ax, dx
        xor     dx, dx
        div     bx                      ; AX = high quotient, DX = remainder
        xchg    ax, cx                  ; CX = high quotient, AX = low word
        div     bx                      ; AX = low quotient, DX = the digit
        add     dl, '0'
        dec     di
        mov     [di], dl
        mov     dx, cx                  ; DX:AX = the quotient
        or      cx, ax
        jnz     .digit
.pad:   cmp     di, numend - 8          ; blanks up to 8 columns
        jbe     .out
        dec     di
        mov     byte [di], ' '
        jmp     .pad
.out:   mov     dx, di
        mov     cx, numend
        sub     cx, dx
        ; fall through to write

; write: write CX bytes at DS:DX to handle 1 (standard output).
write:  mov     ah, 40h
        mov     bx, 1
        int     21h
        ret

crlf    db      13, 10
lines   dd      0
words   dd      0
chars   dd      0
inw     db      0
numbuf  times 10 db 0
numend:
buf:                                    ; 512 bytes after the end of the file
