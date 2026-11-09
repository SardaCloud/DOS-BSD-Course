; setup.asm - section 4.3: boot-sector set-up code in NASM syntax
; nasm -f bin -o setup.bin setup.asm
        bits    16
start:  cld
        xor     ax, ax
        mov     es, ax
        mov     ds, ax
        mov     ss, ax
        mov     sp, 7C00h
