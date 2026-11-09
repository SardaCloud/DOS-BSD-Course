        PAGE    ,132
; HELLOE.ASM - Lab 4.3: the same program as an .EXE, MASM 5.10 syntax
; Build: MASM HELLOE;  LINK HELLOE;
CODE    SEGMENT PARA PUBLIC 'CODE'
        ASSUME  CS:CODE,DS:DATA,SS:STACK
MAIN    PROC    FAR
        MOV     AX,DATA         ; paragraph of DATA: a relocation,
        MOV     DS,AX           ;   fixed up by EXEC at load time
        MOV     AH,9            ; INT 21h function 09h: print string
        MOV     DX,OFFSET MSG   ; DS:DX -> text ending in '$'
        INT     21h
        MOV     AX,4C00h        ; function 4Ch: exit with code 0
        INT     21h
MAIN    ENDP
CODE    ENDS

DATA    SEGMENT PARA PUBLIC 'DATA'
MSG     DB      'Hello from MASM (.EXE)',13,10,'$'
DATA    ENDS

STACK   SEGMENT PARA STACK 'STACK'
        DW      128 DUP (?)     ; 256 bytes of stack
STACK   ENDS
        END     MAIN            ; entry point
