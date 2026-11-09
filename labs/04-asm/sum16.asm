; sum16.asm - Lab 4.8: the sum of an array of words, 8086 (MS-DOS .COM)
; nasm -f bin -o SUM16.COM sum16.asm
        cpu     8086
        org     100h

main:   mov     ax, count
        push    ax                      ; second argument: n
        mov     ax, table
        push    ax                      ; first argument: the address
        call    sum                     ; AX = sum
        add     sp, 4                   ; the caller removes the arguments
        call    printdec                ; print AX in decimal
        mov     ax, 4C00h               ; exit with code 0
        int     21h

; int sum(int *a, int n): arguments on the stack, result in AX
sum:    push    bp                      ; save the caller's BP
        mov     bp, sp                  ; [bp+2] = return address
        push    si                      ; SI belongs to the caller
        mov     si, [bp+4]              ; a
        mov     cx, [bp+6]              ; n
        xor     ax, ax                  ; sum = 0
        jcxz    .done                   ; n = 0: nothing to add
.next:  add     ax, [si]
        add     si, 2                   ; next word
        loop    .next                   ; CX = CX - 1, repeat while CX != 0
.done:  pop     si
        pop     bp
        ret

; print AX as an unsigned decimal number, then CR LF
printdec:
        mov     bx, 10
        xor     cx, cx                  ; number of digits
.div:   xor     dx, dx
        div     bx                      ; DX:AX / 10: quotient AX, remainder DX
        push    dx                      ; digits come out last digit first
        inc     cx
        test    ax, ax
        jnz     .div
.out:   pop     dx
        add     dl, '0'
        mov     ah, 2                   ; INT 21h 02h: print the character in DL
        int     21h
        loop    .out
        mov     ah, 2
        mov     dl, 13
        int     21h
        mov     ah, 2
        mov     dl, 10
        int     21h
        ret

table   dw      1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000
count   equ     ($ - table) / 2
