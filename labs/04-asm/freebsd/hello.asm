; hello.asm - Lab 4.6: hello on FreeBSD/amd64 with two system calls, NASM syntax
; nasm -f elf64 hello.asm && ld -o hello hello.o
        section .rodata
msg:    db      "Hello from x86-64 assembly", 10
len     equ     $ - msg

        section .text
        global  _start
_start: mov     eax, 4                  ; SYS_write
        mov     edi, 1                  ; fd 1: standard output
        lea     rsi, [rel msg]          ; buffer, RIP-relative
        mov     edx, len                ; byte count
        syscall                         ; RCX and R11 are overwritten
        jc      fail                    ; CF=1: RAX holds an errno value
        mov     eax, 1                  ; SYS_exit
        xor     edi, edi                ; status 0
        syscall                         ; does not return
fail:   mov     edi, eax                ; exit status = errno
        mov     eax, 1                  ; SYS_exit
        syscall