; EMSTEST.COM - Lab 8.3: use expanded memory through INT 67h (LIM EMS 4.0).
;   nasm -f bin -o EMSTEST.COM emstest.asm
;   EMSTEST       allocate 4 pages, show bank switching, free the pages
;   EMSTEST K     the same, but keep the pages (look at MEM /DEBUG afterwards)
        cpu     386                     ; for SMSW only; everything else is 8086 code
        org     100h

start:  mov     dx, s_mode              ; 1. Which mode is the CPU in?
        call    puts
        smsw    ax                      ; low word of CR0; not privileged, works in V86 mode
        mov     dx, s_real
        test    al, 1                   ; PE bit
        jz      .mode
        mov     dx, s_v86
.mode:  call    puts

        mov     ax, 3567h               ; 2. Is an expanded memory manager installed?
        int     21h                     ; ES:BX = INT 67h vector
        mov     ax, es
        mov     [drvseg], ax
        mov     di, 0Ah                 ; device name field of the driver header
        mov     si, emmname
        mov     cx, 8
        repe    cmpsb
        push    cs
        pop     es
        je      found
        mov     dx, s_noemm
        call    puts
        jmp     exit

found:  mov     dx, s_drv
        call    puts
        mov     ax, [drvseg]
        call    phex4
        call    crlf

        mov     ah, 46h                 ; 3. Version (BCD in AL)
        int     67h
        push    ax
        mov     dx, s_ver
        call    puts
        pop     ax
        push    ax
        mov     dl, al
        shr     dl, 4
        add     dl, '0'
        call    putc
        mov     dl, '.'
        call    putc
        pop     ax
        mov     dl, al
        and     dl, 0Fh
        add     dl, '0'
        call    putc
        call    crlf

        mov     ah, 41h                 ; 4. Page frame segment
        int     67h
        mov     [frame], bx
        mov     dx, s_frame
        call    puts
        mov     ax, bx
        call    phex4
        call    crlf

        call    pages                   ; 5. Free and total 16 KB pages

        mov     ax, 5801h               ; 6. EMS 4.0: how many mappable physical pages?
        int     67h
        mov     [nmap], cx
        mov     dx, s_nmap
        call    puts
        mov     ax, cx
        call    pdec
        mov     dx, s_at
        call    puts
        mov     ax, 5800h               ; ES:DI <- array of (segment, physical page number)
        mov     di, maparr
        int     67h
        mov     si, maparr
        mov     cx, [nmap]
.seg:   lodsw                           ; segment
        call    phex4
        lodsw                           ; physical page number (not printed)
        mov     dl, ' '
        call    putc
        loop    .seg
        call    crlf

        mov     ah, 43h                 ; 7. Allocate 4 logical pages (64 KB)
        mov     bx, 4
        int     67h
        or      ah, ah
        jz      .ok
        mov     dx, s_allocerr
        call    puts
        jmp     exit
.ok:    mov     [handle], dx
        mov     dx, s_alloc
        call    puts
        mov     ax, [handle]
        call    phex4
        call    crlf
        mov     ax, 5301h               ; give the handle a name (MEM /DEBUG shows it)
        mov     dx, [handle]
        mov     si, hname
        int     67h
        call    pages

        xor     bx, bx                  ; 8. Write each logical page through window 0
.wr:    mov     ax, 4400h               ; map logical page BX into physical page 0
        mov     dx, [handle]
        int     67h
        mov     al, bl
        add     al, '0'
        mov     [tag_n], al
        mov     es, [frame]
        xor     di, di
        mov     si, tag
        mov     cx, tag_len
        rep     movsb
        push    cs
        pop     es
        inc     bx
        cmp     bx, 4
        jb      .wr

        xor     bx, bx                  ; 9. Map logical page i into physical page i, read all four
.map:   mov     al, bl
        mov     ah, 44h
        mov     dx, [handle]
        int     67h
        inc     bx
        cmp     bx, 4
        jb      .map
        xor     bx, bx
.rd:    mov     dx, s_phys
        call    puts
        mov     ax, bx
        call    pdec
        mov     dx, s_seg
        call    puts
        mov     ax, bx
        mov     cl, 10
        shl     ax, cl                  ; physical page i is at frame + i*400h (16 KB)
        add     ax, [frame]
        push    ax
        call    phex4
        mov     dx, s_holds
        call    puts
        pop     ax
        push    ds
        mov     ds, ax
        xor     dx, dx                  ; the text we wrote is '$'-terminated
        mov     ah, 09h
        int     21h
        pop     ds
        inc     bx
        cmp     bx, 4
        jb      .rd

        mov     ax, 4400h               ; 10. Switch the bank under window 0 once more
        mov     bx, 3
        mov     dx, [handle]
        int     67h
        mov     dx, s_again
        call    puts
        push    ds
        mov     ds, [frame]
        xor     dx, dx
        mov     ah, 09h
        int     21h
        pop     ds

        mov     si, 81h                 ; 11. Free the pages unless the command line has a K
.arg:   lodsb
        cmp     al, 0Dh
        je      .free
        and     al, 0DFh                ; upper case
        cmp     al, 'K'
        jne     .arg
        mov     dx, s_kept
        call    puts
        jmp     .done
.free:  mov     ah, 45h
        mov     dx, [handle]
        int     67h
        mov     dx, s_freed
        call    puts
.done:  call    pages
exit:   mov     ax, 4C00h
        int     21h

pages:  mov     ah, 42h                 ; BX = unallocated pages, DX = total pages
        int     67h
        push    dx
        push    bx
        mov     dx, s_pages
        call    puts
        pop     ax
        call    pdec
        mov     dx, s_of
        call    puts
        pop     ax
        call    pdec
        mov     dx, s_pg
        call    puts
        ret

puts:   mov     ah, 09h
        int     21h
        ret
putc:   mov     ah, 02h
        int     21h
        ret
crlf:   mov     dx, s_crlf
        jmp     puts
phex4:  push    cx                      ; AX as 4 hex digits
        mov     cx, 4
.l:     rol     ax, 4
        push    ax
        and     al, 0Fh
        add     al, '0'
        cmp     al, '9'
        jbe     .d
        add     al, 7
.d:     mov     dl, al
        call    putc
        pop     ax
        loop    .l
        pop     cx
        ret
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
.out:   pop     dx
        add     dl, '0'
        call    putc
        loop    .out
        pop     cx
        pop     bx
        ret

emmname   db    'EMMXXXX0'
hname     db    'LAB8    '
s_mode    db    'CPU mode (SMSW): $'
s_real    db    'real mode, PE=0', 13, 10, '$'
s_v86     db    'protected mode, PE=1: we run in virtual-8086 mode', 13, 10, '$'
s_noemm   db    'No expanded memory manager (no EMMXXXX0 driver behind INT 67h)', 13, 10, '$'
s_drv     db    'EMMXXXX0 driver at segment $'
s_ver     db    'EMS version $'
s_frame   db    'Page frame segment $'
s_nmap    db    'Mappable physical pages: $'
s_at      db    ' at $'
s_pages   db    'Free pages: $'
s_of      db    ' of $'
s_pg      db    ' (16 KB each)', 13, 10, '$'
s_alloc   db    'Allocated 4 pages, handle $'
s_allocerr db   'Allocation failed', 13, 10, '$'
s_phys    db    'Physical page $'
s_seg     db    ' (segment $'
s_holds   db    ') holds: $'
s_again   db    'Window 0 after mapping logical page 3 into it: $'
s_kept    db    'Pages kept (K): the handle outlives this program', 13, 10, '$'
s_freed   db    'Pages freed', 13, 10, '$'
s_crlf    db    13, 10, '$'
tag       db    'logical page '
tag_n     db    '0', 13, 10, '$'
tag_len   equ   $ - tag

drvseg  dw      0
frame   dw      0
handle  dw      0
nmap    dw      0
maparr  times 64*4 db 0
