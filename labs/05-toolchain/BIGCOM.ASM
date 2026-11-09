; BIGCOM.ASM -- Module 5, Lab 5.4: a tiny .COM program that mkbig.py pads to a chosen size
; Build: nasm -f bin -o BIGCOM.BIN BIGCOM.ASM
        org     0x100
        mov     dx, msg
        mov     ah, 0x09                ; display a '$'-terminated string
        int     0x21
        mov     ax, 0x4C00              ; terminate, return code 0
        int     0x21
msg     db      "loaded and running", 13, 10, "$"