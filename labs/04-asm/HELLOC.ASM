        PAGE    ,132
; HELLOC.ASM - Lab 4.3: "hello" as a .COM program, MASM 5.10 syntax
; Build: MASM HELLOC;  LINK HELLOC;  EXE2BIN HELLOC HELLOC.COM
CODE    SEGMENT
        ASSUME  CS:CODE,DS:CODE
        ORG     100h            ; the first 256 bytes are the PSP
START:  MOV     AH,9            ; INT 21h function 09h: print string
        MOV     DX,OFFSET MSG   ; DS:DX -> text ending in '$'
        INT     21h
        MOV     AX,4C00h        ; function 4Ch: exit with code 0
        INT     21h
MSG     DB      'Hello from MASM (.COM)',13,10,'$'
CODE    ENDS
        END     START           ; entry point
