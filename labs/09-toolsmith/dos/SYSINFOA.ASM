; SYSINFOA.ASM -- the DOS version, the current drive and directory, the free
; disk space and the largest free memory block.  MS-DOS .COM program.
; Build: nasm -f bin -o SYSINFOA.COM SYSINFOA.ASM
;        (with -dNOSHRINK the program keeps all the memory that EXEC gave it)

STACKSIZE       equ     256

        org     100h

start:
%ifndef NOSHRINK
        mov     sp, endprog + STACKSIZE ; move the stack below the new end
        mov     ah, 4Ah                 ; set block: ES = our PSP
        mov     bx, (endprog - $$ + 100h + STACKSIZE + 15) / 16
        int     21h                     ; keep only what the program needs
%endif
        mov     dx, s_sys               ; "system:    MS-DOS "
        call    puts
        mov     ah, 30h                 ; AL = major, AH = minor version
        int     21h
        push    ax
        xor     ah, ah
        call    putdec
        mov     dl, '.'
        call    putc
        pop     ax
        mov     al, ah
        xor     ah, ah
        cmp     al, 10                  ; two digits: 4.00, not 4.0
        jae     .minor
        push    ax
        mov     dl, '0'
        call    putc                    ; (write changes AX)
        pop     ax
.minor: call    putdec
        call    newline

        mov     dx, s_dir               ; "directory: "
        call    puts
        mov     ah, 19h                 ; AL = current drive, 0 = A
        int     21h
        add     al, 'A'
        mov     dl, al
        call    putc
        mov     dx, s_root              ; ":\"
        call    puts
        mov     ah, 47h                 ; current directory of drive DL
        xor     dl, dl                  ; 0 = the current drive
        mov     si, curdir              ; DS:SI = 64-byte buffer
        int     21h
        mov     dx, curdir
        call    puts
        call    newline

        mov     dx, s_disk              ; "disk:      "
        call    puts
        mov     ah, 36h                 ; free space of drive DL (0 = current)
        xor     dl, dl
        int     21h                     ; AX sect/cluster, BX free clusters,
        mov     [tclus], dx             ; CX bytes/sector, DX total clusters
        mul     cx                      ; AX = bytes per cluster
        mov     [cbytes], ax
        mul     bx                      ; DX:AX = free bytes
        call    put32
        mov     dx, s_of                ; " bytes free of "
        call    puts
        mov     ax, [cbytes]
        mul     word [tclus]            ; DX:AX = total bytes
        call    put32
        call    newline

        mov     dx, s_mem               ; "memory:    largest free block "
        call    puts
; TODO: function 48h with BX = FFFFh fails and returns in BX the size of the
;       largest free block in paragraphs.  Put the size in bytes in DX:AX
;       for put32.  (Build once with -dNOSHRINK as well: see Module 8,
;       Exercise 8.2.)
        call    put32
        mov     dx, s_bytes             ; " bytes"
        call    puts
        call    newline
        mov     ax, 4C00h
        int     21h

; put32: print DX:AX in decimal.  putdec: print AX in decimal.
putdec: xor     dx, dx
put32:  mov     di, numend
        mov     bx, 10
.digit: mov     cx, ax                  ; divide DX:AX by 10, high word first
        mov     ax, dx
        xor     dx, dx
        div     bx
        xchg    ax, cx
        div     bx                      ; CX:AX = quotient, DX = digit
        add     dl, '0'
        dec     di
        mov     [di], dl
        mov     dx, cx
        or      cx, ax
        jnz     .digit
        mov     dx, di
        ; fall through to puts

; puts: write the NUL-terminated string at DS:DX to standard output.
puts:   mov     di, dx
        xor     cx, cx
.len:   cmp     byte [di], 0
        je      write
        inc     di
        inc     cx
        jmp     .len

newline:
        mov     dx, s_crlf
        jmp     puts

; putc: write the character in DL.
putc:   mov     [onech], dl
        mov     dx, onech
        mov     cx, 1
        ; fall through to write

; write: write CX bytes at DS:DX to handle 1.
write:  mov     ah, 40h
        mov     bx, 1
        int     21h
        ret

s_sys   db      'system:    MS-DOS ', 0
s_dir   db      'directory: ', 0
s_root  db      ':\', 0
s_disk  db      'disk:      ', 0
s_of    db      ' bytes free of ', 0
s_mem   db      'memory:    largest free block ', 0
s_bytes db      ' bytes', 0
s_crlf  db      13, 10, 0
onech   db      0
tclus   dw      0
cbytes  dw      0
curdir  times 64 db 0
numbuf  times 10 db 0
numend  db      0
endprog:
