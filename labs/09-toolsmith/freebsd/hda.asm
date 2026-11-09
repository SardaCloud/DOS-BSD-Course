; hda.asm -- hex dump of standard input in the format of hd (hexdump -C),
; without the "*" for repeated lines.  FreeBSD/amd64, no C library.
; Build: nasm -f elf64 hda.asm && ld -o hda hda.o

SYS_exit        equ     1
SYS_read        equ     3
SYS_write       equ     4

        section .text
        global  _start
_start: xor     r12, r12                ; r12 = offset of the current line
.line:  xor     r13, r13                ; r13 = bytes in this line so far
.fill:
        ; TODO: read(0, data + r13, 16 - r13).  On an error (carry set) go to
        ;       .error; when 0 bytes come back go to .eof; otherwise add them
        ;       to r13 and read again until r13 is 16: a pipe may return fewer
        ;       bytes than asked for.
.eof:   test    r13, r13
        jz      .finish
        call    putline
        add     r12, r13
        cmp     r13, 16
        je      .line

.finish:
        test    r12, r12                ; the final offset, if there was input
        jz      .done
        lea     rdi, [rel line]
        call    putoff
        call    endline
.done:  xor     edi, edi                ; exit status 0
        jmp     .exit
.error: mov     edi, 1                  ; exit status 1: the read failed
.exit:  mov     eax, SYS_exit
        syscall

; putline: format and write one line for the r13 bytes at data.
putline:
        lea     rdi, [rel line]
        call    putoff
        mov     al, ' '
        stosb
        lea     rsi, [rel data]
        xor     ecx, ecx                ; rcx = index 0..15
.hex:   cmp     ecx, 8
        jne     .nogap
        mov     al, ' '                 ; extra blank between the halves
        stosb
.nogap: mov     al, ' '
        stosb
        cmp     rcx, r13
        jae     .blank
        mov     al, [rsi + rcx]
        call    puthex
        jmp     .next
.blank: mov     ax, '  '                ; past the end of a short line
        stosw
.next:  inc     ecx
        cmp     ecx, 16
        jb      .hex
        mov     eax, '  |'
        stosw
        shr     eax, 16
        stosb
        xor     ecx, ecx
.chr:   cmp     rcx, r13
        jae     .bar
        mov     al, [rsi + rcx]
        cmp     al, ' '
        jb      .dot
        cmp     al, '~'
        jbe     .put
.dot:   mov     al, '.'
.put:   stosb
        inc     ecx
        jmp     .chr
.bar:   mov     al, '|'
        stosb
        ; fall through to endline

; endline: append LF and write the line from line to rdi.
endline:
        mov     al, 10
        stosb
        lea     rsi, [rel line]
        mov     rdx, rdi
        sub     rdx, rsi
        mov     eax, SYS_write
        mov     edi, 1
        syscall
        ret

; putoff: store the low 32 bits of r12 as 8 hex digits at rdi.
putoff: mov     edx, r12d
        mov     r8d, 4
.byte:  rol     edx, 8                  ; the most significant byte first
        mov     al, dl
        call    puthex
        dec     r8d
        jnz     .byte
        ret

; puthex: store al as two hex digits at rdi.
puthex: lea     r9, [rel digits]
        movzx   r10d, al
        shr     r10d, 4                 ; the high nibble first
        mov     r10b, [r9 + r10]
        mov     [rdi], r10b
        movzx   r10d, al
        and     r10d, 0Fh
        mov     r10b, [r9 + r10]
        mov     [rdi + 1], r10b
        add     rdi, 2
        ret

        section .rodata
digits  db      '0123456789abcdef'

        section .bss
data    resb    16
line    resb    80
