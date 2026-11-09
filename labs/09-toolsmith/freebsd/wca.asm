; wca.asm -- count the lines, words and bytes of standard input, like wc with
; no file names.  FreeBSD/amd64, no C library.
; Build: nasm -f elf64 wca.asm && ld -o wca wca.o

SYS_exit        equ     1
SYS_read        equ     3
SYS_write       equ     4
BUFSIZE         equ     4096

        section .text
        global  _start
_start: xor     r12, r12                ; r12 = lines
        xor     r13, r13                ; r13 = words
        xor     r14, r14                ; r14 = bytes
        xor     r15d, r15d              ; r15 = 1 inside a word
.read:  mov     eax, SYS_read           ; read(0, buf, BUFSIZE)
        xor     edi, edi
        lea     rsi, [rel buf]
        mov     edx, BUFSIZE
        syscall
        jc      .error                  ; carry set: rax holds an errno
        test    rax, rax                ; 0 bytes read: end of file
        jz      .report
        add     r14, rax
        lea     rsi, [rel buf]
        mov     rcx, rax
.next:  movzx   eax, byte [rsi]
        inc     rsi
        ; TODO: count each LF in r12 and the first byte of each word in r13
        ;       (a word byte is anything but ' ' and 9..13).  r15 says whether
        ;       the previous byte was inside a word, also across blocks.
        dec     rcx
        jnz     .next
        jmp     .read

.report:
        mov     rax, r12
        call    put8
        mov     rax, r13
        call    put8
        mov     rax, r14
        call    put8
        lea     rsi, [rel nl]
        mov     edx, 1
        call    write
        xor     edi, edi                ; exit status 0
        jmp     .exit
.error: mov     edi, 1                  ; exit status 1: the read failed
.exit:  mov     eax, SYS_exit
        syscall

; put8: print rax in decimal, right-aligned in 8 columns.
put8:   lea     rsi, [rel numend]
        mov     ecx, 10
.digit: xor     edx, edx
        div     rcx
        add     dl, '0'
        dec     rsi
        mov     [rsi], dl
        test    rax, rax
        jnz     .digit
        lea     rax, [rel numend - 8]
.pad:   cmp     rsi, rax                ; blanks up to 8 columns
        jbe     .out
        dec     rsi
        mov     byte [rsi], ' '
        jmp     .pad
.out:   lea     rdx, [rel numend]
        sub     rdx, rsi
        ; fall through to write

; write: write rdx bytes at rsi to standard output.
write:  mov     eax, SYS_write
        mov     edi, 1
        syscall
        ret

        section .rodata
nl      db      10

        section .bss
buf     resb    BUFSIZE
numbuf  resb    20
numend  resb    1
