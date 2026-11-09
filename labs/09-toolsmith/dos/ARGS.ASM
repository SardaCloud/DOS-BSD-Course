; ARGS.ASM -- print the command tail, then every word of it, numbered;
; word 0 is the program's own path, found after the environment strings.
; MS-DOS .COM program.  Build: nasm -f bin -o ARGS.COM ARGS.ASM

        org     100h

start:  mov     dx, s_tail              ; "tail: "
        call    puts
        xor     ah, ah
        mov     al, [80h]               ; length byte of the command tail
        call    putdec
        mov     dx, s_bytes             ; " bytes ["
        call    puts
        mov     cl, [80h]
        xor     ch, ch
        mov     dx, 81h                 ; the tail itself, without its CR
        call    write
        mov     dx, s_close             ; "]" CR LF
        call    puts

; Word 0: the path DOS stored after the environment (DOS 3.0 and later).
; TODO 1: print "0: [" with  call number  (argno is still 0).
;         Load DS from the environment segment at PSP offset 2Ch (push DS
;         first), skip every NAME=value string up to the empty string that
;         ends the environment, skip the 0 and the word count that follows,
;         print the path with  call puts , restore DS and print s_close.

; Words 1..n: runs of characters separated by blanks or tabs, up to the CR.
; TODO 2: walk the tail from offset 81h with LODSB.  Skip blanks and tabs;
;         stop at the CR (13).  For each word: remember its first byte in DX,
;         find the delimiter, increment [argno], call number, put the
;         length in CX, call write, print s_close, and continue.

done:   mov     ax, 4C00h               ; exit code 0
        int     21h

; number: print argno in decimal, then ": [".  Preserves all registers.
number: push    ax
        push    dx
        mov     ax, [argno]
        call    putdec
        mov     dx, s_open
        call    puts
        pop     dx
        pop     ax
        ret

; putdec: print AX as an unsigned decimal number.  Preserves all registers.
putdec: push    ax
        push    bx
        push    dx
        push    di
        mov     di, numend              ; build the digits backwards
        mov     bx, 10
.digit: xor     dx, dx
        div     bx
        add     dl, '0'
        dec     di
        mov     [di], dl
        or      ax, ax
        jnz     .digit
        mov     dx, di
        call    puts
        pop     di
        pop     dx
        pop     bx
        pop     ax
        ret

; puts: write the NUL-terminated string at DS:DX to standard output.
puts:   push    cx
        push    di
        mov     di, dx
        xor     cx, cx
.len:   cmp     byte [di], 0
        je      .go
        inc     di
        inc     cx
        jmp     .len
.go:    call    write
        pop     di
        pop     cx
        ret

; write: write CX bytes at DS:DX to handle 1 (standard output).
write:  push    ax
        push    bx
        mov     ah, 40h
        mov     bx, 1
        int     21h
        pop     bx
        pop     ax
        ret

s_tail  db      'tail: ', 0
s_bytes db      ' bytes [', 0
s_open  db      ': [', 0
s_close db      ']', 13, 10, 0
argno   dw      0
numbuf  times 5 db 0
numend  db      0
