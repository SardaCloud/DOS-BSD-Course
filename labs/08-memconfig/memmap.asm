; MEMMAP.COM - Lab 8.1: look at the first megabyte of a PC from a DOS program.
;   nasm -f bin -o MEMMAP.COM memmap.asm
; Reads the BIOS data area, asks the BIOS for memory sizes, tests the A20 line,
; scans C000-EFFF for option ROMs (55AA signature) and classifies every 16 KB
; page between A000 and FFFF as RAM, ROM or nothing.
        cpu     8086
        org     100h

start:  mov     dx, s_int12             ; conventional memory, two ways
        call    puts
        int     12h                     ; AX = KB below the video memory
        call    pdec
        mov     dx, s_bda413
        call    puts
        push    ds
        mov     ax, 40h
        mov     ds, ax
        mov     ax, [13h]               ; BDA 0040:0013, the variable INT 12h returns
        pop     ds
        call    pdec
        call    crlf

        mov     dx, s_top               ; PSP offset 2: first segment beyond our block
        call    puts
        mov     ax, [2]
        call    phex4
        call    crlf

        mov     dx, s_ext               ; extended memory size from the AT BIOS
        call    puts
        mov     ah, 88h
        clc
        int     15h
        jnc     .ext
        xor     ax, ax
.ext:   call    pdec
        mov     dx, s_kb
        call    puts

        mov     dx, s_a20               ; A20: does FFFF:0510 alias 0000:0500?
        call    puts
        cli
        xor     ax, ax
        mov     es, ax
        mov     ax, 0FFFFh
        mov     ds, ax                  ; DS = FFFF, ES = 0000
        mov     bx, [es:500h]           ; save the word we will change
        mov     word [es:500h], 0AA55h
        mov     cx, [510h]              ; FFFF:0510 = linear 100500h, or 000500h if A20 is off
        mov     word [es:500h], 055AAh
        mov     dx, [510h]
        mov     [es:500h], bx           ; restore
        push    cs
        pop     ds
        push    cs
        pop     es
        sti
        cmp     cx, 0AA55h
        jne     .on
        cmp     dx, 055AAh
        jne     .on
        mov     dx, s_off
        jmp     .a20
.on:    mov     dx, s_on
.a20:   call    puts

        mov     dx, s_video             ; video state from the BDA
        call    puts
        push    ds
        mov     ax, 40h
        mov     ds, ax
        mov     al, [49h]               ; current video mode
        mov     bx, [4Ah]               ; columns
        mov     cx, [63h]               ; CRTC port: 3D4h colour, 3B4h mono
        pop     ds
        push    cx
        push    bx
        xor     ah, ah
        call    phex2
        mov     dx, s_cols
        call    puts
        pop     ax
        call    pdec
        mov     dx, s_crtc
        call    puts
        pop     ax
        push    ax
        call    phex4
        pop     ax
        mov     dx, s_b800
        cmp     ax, 3D4h
        je      .vid
        mov     dx, s_b000
.vid:   call    puts

        mov     dx, s_equip             ; equipment word, INT 11h = BDA 0040:0010
        call    puts
        int     11h
        call    phex4
        call    crlf

        mov     dx, s_bios              ; BIOS date and model byte at the top of the ROM
        call    puts
        push    ds
        mov     ax, 0F000h
        mov     ds, ax
        mov     si, 0FFF5h
        mov     cx, 8
.date:  lodsb
        mov     dl, al
        call    putc
        loop    .date
        mov     al, [0FFFEh]
        pop     ds
        push    ax
        mov     dx, s_model
        call    puts
        pop     ax
        call    phex2
        call    crlf

        mov     dx, s_roms              ; option ROMs: 55 AA, size/512, checksum 0
        call    puts
        mov     bx, 0C000h
.scan:  mov     es, bx
        cmp     word [es:0], 0AA55h
        jne     .next
        mov     dx, s_ind
        call    puts
        mov     ax, bx
        call    phex4
        mov     dx, s_size
        call    puts
        mov     al, [es:2]              ; size in 512-byte blocks
        xor     ah, ah
        mov     cl, 9
        shl     ax, cl
        push    ax
        call    pdec
        pop     cx                      ; CX = size in bytes (0 means 64 KB: not handled)
        xor     si, si
        xor     ah, ah
.sum:   add     ah, [es:si]
        inc     si
        loop    .sum
        mov     dx, s_ckok
        or      ah, ah
        jz      .ck
        mov     dx, s_ckbad
.ck:    call    puts
.next:  add     bx, 80h                 ; 2 KB steps
        cmp     bx, 0F000h
        jb      .scan
        push    cs
        pop     es

        mov     dx, s_pages             ; 16 KB pages from A000 to FC00
        call    puts
        mov     bx, 0A000h
        xor     di, di                  ; pages printed on this line
.page:  mov     ax, bx
        call    phex4
        mov     dl, ' '
        call    putc
        mov     es, bx
        cli
        mov     al, [es:0]              ; RAM if a changed byte reads back changed
        mov     ah, al
        not     al
        mov     [es:0], al
        mov     cl, [es:0]
        mov     [es:0], ah              ; restore
        sti
        mov     dl, 'R'
        cmp     cl, al
        je      .cls
        mov     dl, '-'                 ; not RAM: ROM if any sampled byte is not FFh
        mov     si, 0
.samp:  cmp     byte [es:si], 0FFh
        jne     .rom
        add     si, 800h
        cmp     si, 4000h
        jb      .samp
        jmp     .cls
.rom:   mov     dl, 'O'
.cls:   call    putc
        mov     dx, s_sep
        call    puts
        inc     di
        cmp     di, 8
        jb      .pn
        call    crlf
        mov     dx, s_ind
        call    puts
        xor     di, di
.pn:    add     bx, 400h
        jnz     .page                   ; until the segment wraps past FC00
        push    cs
        pop     es
        mov     dx, s_legend
        call    puts
        mov     ax, 4C00h
        int     21h

puts:   mov     ah, 09h
        int     21h
        ret
putc:   mov     ah, 02h
        int     21h
        ret
crlf:   mov     dx, s_crlf
        jmp     puts
phex4:  push    ax                      ; AX as 4 hex digits
        mov     al, ah
        call    phex2
        pop     ax
phex2:  push    ax                      ; AL as 2 hex digits
        mov     cl, 4
        shr     al, cl
        call    .dig
        pop     ax
        and     al, 0Fh
.dig:   add     al, '0'
        cmp     al, '9'
        jbe     .out
        add     al, 7
.out:   mov     dl, al
        jmp     putc
pdec:   push    bx                      ; AX as unsigned decimal
        push    cx
        mov     bx, 10
        xor     cx, cx
.div:   xor     dx, dx
        div     bx
        push    dx
        inc     cx
        or      ax, ax
        jnz     .div
.prt:   pop     dx
        add     dl, '0'
        call    putc
        loop    .prt
        pop     cx
        pop     bx
        ret

s_int12  db     'Conventional memory, INT 12h:  $'
s_bda413 db     ' KB; BDA word 0040:0013 = $'
s_top    db     'Memory top in our PSP:         $'
s_ext    db     'Extended memory, INT 15h 88h:  $'
s_kb     db     ' KB', 13, 10, '$'
s_a20    db     'A20 line:                      $'
s_on     db     'enabled (FFFF:0510 is not 0000:0500)', 13, 10, '$'
s_off    db     'disabled (FFFF:0510 wraps to 0000:0500)', 13, 10, '$'
s_video  db     'Video mode (BDA 0040:0049):    $'
s_cols   db     'h, columns $'
s_crtc   db     ', CRTC port $'
s_b800   db     'h: colour text at B800:0000', 13, 10, '$'
s_b000   db     'h: monochrome text at B000:0000', 13, 10, '$'
s_equip  db     'Equipment word, INT 11h:       $'
s_bios   db     'BIOS date at F000:FFF5:        $'
s_model  db     ', model byte F000:FFFE = $'
s_roms   db     'Option ROMs (55AA every 2 KB from C000 to EFFF):', 13, 10, '$'
s_size   db     ' size $'
s_ckok   db     ' bytes, checksum ok', 13, 10, '$'
s_ckbad  db     ' bytes, checksum not zero', 13, 10, '$'
s_pages  db     '16 KB pages from A000 to FFFF:', 13, 10
s_ind    db     '  $'
s_sep    db     '   $'
s_legend db     'R = RAM (a write reads back), O = ROM or device, - = nothing (reads FFh)', 13, 10, '$'
s_crlf   db     13, 10, '$'
