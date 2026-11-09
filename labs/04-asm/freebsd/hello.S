/* hello.S - Lab 4.6: the same program in AT&T syntax, for cc (clang's assembler) */
/* cc -nostdlib -static -o hello-att hello.S */
#include <sys/syscall.h>

        .section .rodata
msg:    .ascii  "Hello from AT&T syntax\n"
        .set    len, . - msg

        .text
        .globl  _start
_start: movl    $SYS_write, %eax        /* source first, destination last */
        movl    $1, %edi
        leaq    msg(%rip), %rsi
        movl    $len, %edx
        syscall
        jc      fail
        movl    $SYS_exit, %eax
        xorl    %edi, %edi
        syscall
fail:   movl    %eax, %edi
        movl    $SYS_exit, %eax
        syscall