; sum64.asm - Lab 4.8: the same function for x86-64 (System V ABI), NASM syntax
; nasm -f elf64 sum64.asm
        section .text
        global  sum
; long sum(const long *a, long n): a in RDI, n in RSI, result in RAX
sum:    push    rbp                     ; a frame like the 8086 version
        mov     rbp, rsp                ; (a leaf function does not need it)
        xor     eax, eax                ; sum = 0 (writing EAX clears all of RAX)
        test    rsi, rsi
        jz      .done                   ; n = 0: nothing to add
.next:  add     rax, [rdi]
        add     rdi, 8                  ; next long
        dec     rsi
        jnz     .next
.done:  pop     rbp
        ret

        section .note.GNU-stack noalloc noexec nowrite progbits