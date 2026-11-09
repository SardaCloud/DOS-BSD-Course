; KEYS.COM - the console device, cooked and raw (Lab 6.3)
;   KEYS     report IOCTL 4400h for handles 0-2, then one cooked read from handle 0
;   KEYS R   switch handle 0 to raw mode (IOCTL 4401h, bit 5), read keys one at a time
;            until 'q' or 16 keys, switch back, then report what was read
; Nothing is printed between the reads, so DOS has no reason to look for Ctrl-C
; while the keys are being read (see Lab 6.3).
; nasm -f bin -o KEYS.COM keys.asm
        cpu     8086
        org     100h

        call    report                  ; device information before
        mov     si, 81h                 ; command tail
skipsp: lodsb
        cmp     al, ' '
        je      skipsp
        and     al, 0DFh                ; upper case
        cmp     al, 'R'
        je      raw

; cooked: one read of up to 40 bytes from standard input --------------------
        mov     dx, s_cooked
        call    puts
        mov     ah, 3Fh
        xor     bx, bx                  ; handle 0
        mov     cx, 40
        mov     dx, buf
        int     21h
        jc      fail
        mov     [count], ax
        jmp     show

; raw: set bit 5 in the device information of handle 0 ----------------------
raw:    mov     ax, 4400h
        xor     bx, bx
        int     21h
        mov     [oldinfo], dl
        xor     dh, dh                  ; DH must be 0
        or      dl, 20h                 ; RAW
        mov     ax, 4401h
        int     21h
        jc      fail
        mov     dx, s_raw
        call    puts
        call    report                  ; device information after
        mov     di, buf
rawlp:  mov     ah, 3Fh                 ; read one byte
        xor     bx, bx
        mov     cx, 1
        mov     dx, di
        int     21h
        jc      fail
        inc     di
        inc     word [count]
        cmp     byte [di-1], 'q'
        je      rawend
        cmp     word [count], 16
        jb      rawlp
rawend: mov     ax, 4401h               ; back to cooked
        xor     bx, bx
        mov     dl, [oldinfo]
        xor     dh, dh
        int     21h

show:   mov     dx, s_got
        call    puts
        mov     ax, [count]
        call    puthex4
        mov     dx, s_bytes
        call    puts
        mov     si, buf
        mov     cx, [count]
        jcxz    eol
showlp: lodsb
        call    puthex2
        mov     al, ' '
        call    putc
        loop    showlp
eol:    call    crlf
        mov     ax, 4C00h
        int     21h

fail:   mov     dx, s_fail
        call    puts
        mov     ax, 4C01h
        int     21h

; print "handle N: DX=xxxx <flags>" for handles 0, 1, 2 ---------------------
report: xor     bx, bx
replp:  mov     dx, s_hnd
        call    puts
        mov     al, bl
        add     al, '0'
        call    putc
        mov     dx, s_dx
        call    puts
        mov     ax, 4400h
        int     21h
        mov     ax, dx
        push    dx
        call    puthex4
        pop     dx
        mov     si, names               ; one name per bit, bit 7 first
        mov     ah, 80h
bitlp:  test    dl, ah
        jz      nobit
        mov     al, ' '
        call    putc
        push    dx
        mov     dx, si
        call    puts
        pop     dx
nobit:  add     si, 7
        shr     ah, 1
        jnz     bitlp
        call    crlf
        inc     bx
        cmp     bx, 3
        jb      replp
        ret

; output helpers (INT 21h, standard output)
putc:   push    ax
        push    dx
        mov     dl, al
        mov     ah, 02h
        int     21h
        pop     dx
        pop     ax
        ret
puts:   push    ax
        mov     ah, 09h
        int     21h
        pop     ax
        ret
crlf:   mov     al, 13
        call    putc
        mov     al, 10
        jmp     putc
puthex4:
        push    ax
        mov     al, ah
        call    puthex2
        pop     ax
puthex2:
        push    cx
        push    ax
        mov     cl, 4
        shr     al, cl
        call    nibble
        pop     ax
        and     al, 0Fh
        call    nibble
        pop     cx
        ret
nibble: add     al, '0'
        cmp     al, '9'
        jbe     putc
        add     al, 7
        jmp     putc

names   db      "ISDEV$ "               ; bit 7
        db      "NOTEOF$"               ; bit 6 (0 = end of file reached)
        db      "RAW$   "               ; bit 5
        db      "SPECL$ "               ; bit 4 (INT 29h output)
        db      "ISCLK$ "               ; bit 3
        db      "ISNUL$ "               ; bit 2
        db      "ISCOT$ "               ; bit 1 (console output)
        db      "ISCIN$ "               ; bit 0 (console input)
s_hnd   db      "handle $"
s_dx    db      ": DX=$"
s_cooked db     "cooked read(0, buf, 40)", 13, 10, "$"
s_raw   db      "handle 0 switched to raw", 13, 10, "$"
s_got   db      "read returned $"
s_bytes db      "h bytes: $"
s_fail  db      "error", 13, 10, "$"
oldinfo db      0
count   dw      0
buf     times 48 db 0
