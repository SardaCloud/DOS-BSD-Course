; HELLOC.ASM -- Module 5: a .COM program for MASM 5.10, LINK and EXE2BIN
CODE    SEGMENT
        ASSUME  CS:CODE, DS:CODE
        ORG     100h                    ; the PSP occupies 0-0FFh
START:  MOV     DX,OFFSET MSG           ; DS = CS = the PSP segment
        MOV     AH,9                    ; display a '$'-terminated string
        INT     21h
        MOV     AX,4C00h                ; terminate, return code 0
        INT     21h
MSG     DB      'Hello from a .COM file made by EXE2BIN',13,10,'$'
CODE    ENDS
        END     START