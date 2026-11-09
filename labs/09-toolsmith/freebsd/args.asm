; args.asm -- print argc, every argv[i] numbered, and the executable's path
; from the auxiliary vector.  FreeBSD/amd64, no C library.
; Build: nasm -f elf64 args.asm && ld -o argsa args.o

SYS_exit        equ     1
SYS_write       equ     4
AT_NULL         equ     0
AT_EXECPATH     equ     15

        section .text
        global  _start
_start:
        mov     r12, rdi                ; the kernel's rdi points at argc
        mov     rbx, [r12]              ; rbx = argc
        lea     rsi, [rel s_argc]       ; "argc: "
        call    puts
        mov     rax, rbx
        call    putdec
        lea     rsi, [rel s_nl]
        call    puts

        ; TODO 1: for i = 0 .. argc-1 print  i: [argv[i]]  .  argv[i] is the
        ;         quadword at r12 + 8 + i*8.  Keep i in r13, r14 or r15: puts,
        ;         putdec and the syscall instruction change the others.

        ; TODO 2: envp starts at &argv[argc + 1].  Skip the environment
        ;         pointers up to their NULL; the auxiliary vector follows as
        ;         (type, value) pairs ending with AT_NULL.  If you find
        ;         AT_EXECPATH, print  path: [value]  .

.done:  mov     eax, SYS_exit
        xor     edi, edi                ; exit status 0
        syscall

; putdec: print rax as an unsigned decimal number.
putdec: lea     rsi, [rel numend]
        mov     byte [rsi], 0
        mov     rcx, 10
.digit: xor     edx, edx
        div     rcx
        add     dl, '0'
        dec     rsi
        mov     [rsi], dl
        test    rax, rax
        jnz     .digit
        ; fall through to puts

; puts: write the NUL-terminated string at rsi to standard output.
puts:   mov     rdx, rsi
.len:   cmp     byte [rdx], 0
        je      .go
        inc     rdx
        jmp     .len
.go:    sub     rdx, rsi                ; rdx = length
        mov     eax, SYS_write
        mov     edi, 1                  ; fd 1
        syscall                         ; write(1, rsi, rdx); clobbers rcx, r11
        ret

        section .rodata
s_argc  db      'argc: ', 0
s_nl    db      10, 0
s_open  db      ': [', 0
s_close db      ']', 10, 0
s_path  db      'path: [', 0

        section .bss
numbuf  resb    20
numend  resb    1
