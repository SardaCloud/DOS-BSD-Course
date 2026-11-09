; RTC.COM - read the date and time four ways (Lab 6.2)
;   1. DOS:   INT 21h AH=2Ah (date) and AH=2Ch (time), binary values
;   2. BIOS:  INT 1Ah AH=00h, the tick counter (about 18.2 ticks per second since midnight)
;   3. BIOS:  INT 1Ah AH=04h (date) and AH=02h (time), read from the CMOS clock, BCD values
;   4. Ports: the CMOS clock itself, index port 70h and data port 71h, BCD values
; nasm -f bin -o RTC.COM rtc.asm
        cpu     8086
        org     100h

; 1. DOS -------------------------------------------------------------------
        mov     dx, s_dos
        call    puts
        mov     ah, 2Ah                 ; get date: CX = year, DH = month, DL = day
        int     21h
        push    dx
        mov     ax, cx
        call    putdec4
        mov     al, '-'
        call    putc
        pop     dx
        push    dx
        mov     al, dh
        call    putdec2
        mov     al, '-'
        call    putc
        pop     dx
        mov     al, dl
        call    putdec2
        mov     al, ' '
        call    putc
        mov     ah, 2Ch                 ; get time: CH = hour, CL = minute, DH = second, DL = 1/100
        int     21h
        push    dx
        mov     al, ch
        call    putdec2
        mov     al, ':'
        call    putc
        mov     al, cl
        call    putdec2
        mov     al, ':'
        call    putc
        pop     dx
        push    dx
        mov     al, dh
        call    putdec2
        mov     al, '.'
        call    putc
        pop     dx
        mov     al, dl
        call    putdec2
        call    crlf

; 2. BIOS tick counter -----------------------------------------------------
        mov     dx, s_tick
        call    puts
        mov     ah, 00h                 ; CX:DX = ticks since midnight, AL = midnight flag
        int     1Ah
        mov     [ticks], dx
        mov     [ticks+2], cx
        mov     ax, cx
        call    puthex4
        mov     ax, [ticks]
        call    puthex4
        mov     dx, s_hexeq
        call    puts
        mov     ax, [ticks]             ; DX:AX = ticks
        mov     dx, [ticks+2]
        call    putdec32
        call    crlf

; 3. BIOS CMOS clock -------------------------------------------------------
        mov     dx, s_bios
        call    puts
        mov     ah, 04h                 ; CH = century, CL = year, DH = month, DL = day (BCD)
        int     1Ah
        jc      no_rtc
        push    dx
        mov     al, ch
        call    puthex2                 ; BCD prints as decimal digits in hex
        mov     al, cl
        call    puthex2
        mov     al, '-'
        call    putc
        pop     dx
        push    dx
        mov     al, dh
        call    puthex2
        mov     al, '-'
        call    putc
        pop     dx
        mov     al, dl
        call    puthex2
        mov     al, ' '
        call    putc
        mov     ah, 02h                 ; CH = hour, CL = minute, DH = second (BCD)
        int     1Ah
        push    dx
        mov     al, ch
        call    puthex2
        mov     al, ':'
        call    putc
        mov     al, cl
        call    puthex2
        mov     al, ':'
        call    putc
        pop     dx
        mov     al, dh
        call    puthex2
        call    crlf
        jmp     ports
no_rtc: mov     dx, s_none
        call    puts

; 4. CMOS ports 70h/71h ----------------------------------------------------
ports:  mov     dx, s_port
        call    puts
wait_uip:
        mov     al, 0Ah                 ; status register A
        call    cmos
        test    al, 80h                 ; update in progress?
        jnz     wait_uip
        mov     al, 32h                 ; century (IBM AT location)
        call    cmos
        call    puthex2
        mov     al, 09h                 ; year
        call    cmos
        call    puthex2
        mov     al, '-'
        call    putc
        mov     al, 08h                 ; month
        call    cmos
        call    puthex2
        mov     al, '-'
        call    putc
        mov     al, 07h                 ; day of month
        call    cmos
        call    puthex2
        mov     al, ' '
        call    putc
        mov     al, 04h                 ; hours
        call    cmos
        call    puthex2
        mov     al, ':'
        call    putc
        mov     al, 02h                 ; minutes
        call    cmos
        call    puthex2
        mov     al, ':'
        call    putc
        mov     al, 00h                 ; seconds
        call    cmos
        call    puthex2
        mov     dx, s_regs
        call    puts
        mov     al, 0Ah
        call    cmos
        call    puthex2
        mov     dx, s_regb
        call    puts
        mov     al, 0Bh                 ; status register B: bit 2 = binary, bit 1 = 24 h
        call    cmos
        call    puthex2
        call    crlf
        mov     ax, 4C00h
        int     21h

; AL = CMOS register -> AL = value
cmos:   cli
        out     70h, al                 ; select the register (bit 7 = 0 keeps NMI enabled)
        jmp     short $+2               ; a short delay for slow I/O devices
        in      al, 71h                 ; read it
        sti
        ret

; output helpers: all write to standard output with INT 21h
putc:   push    dx
        push    ax
        mov     dl, al
        mov     ah, 02h
        int     21h
        pop     ax
        pop     dx
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
puthex4:                                ; AX
        push    ax
        mov     al, ah
        call    puthex2
        pop     ax
puthex2:                                ; AL (CX preserved)
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
putdec2:                                ; AL < 100, two digits
        aam                             ; AH = AL / 10, AL = AL mod 10
        add     ax, '00'
        push    ax
        mov     al, ah
        call    putc
        pop     ax
        jmp     putc
putdec4:                                ; AX < 10000, four digits
        xor     dx, dx
        mov     cx, 100
        div     cx
        push    dx
        call    putdec2
        pop     ax
        jmp     putdec2
putdec32:                               ; DX:AX, unsigned, no leading zeros
        mov     bx, 10
        xor     cx, cx
d32:    push    ax                      ; divide DX:AX by 10 in two steps
        mov     ax, dx
        xor     dx, dx
        div     bx                      ; AX = high quotient, DX = remainder
        mov     si, ax
        pop     ax
        div     bx                      ; AX = low quotient, DX = digit
        push    dx
        inc     cx
        mov     dx, si
        mov     di, dx
        or      di, ax
        jnz     d32
d32out: pop     ax
        add     al, '0'
        call    putc
        loop    d32out
        ret

ticks   dw      0, 0
s_dos   db      "DOS   INT 21h 2Ah/2Ch : $"
s_tick  db      "BIOS  INT 1Ah 00h     : ticks $"
s_hexeq db      "h = $"
s_bios  db      "BIOS  INT 1Ah 04h/02h : $"
s_none  db      "no CMOS clock (carry set)", 13, 10, "$"
s_port  db      "PORTS 70h/71h         : $"
s_regs  db      "  A=$"
s_regb  db      " B=$"
