; SEGREF.ASM -- Module 5: like HELLOC.ASM, plus one segment reference
CODE    SEGMENT
        ASSUME  CS:CODE, DS:CODE
        ORG     100h
START:  MOV     AX,SEG MSG              ; a segment address: needs a relocation
        MOV     DS,AX
        MOV     DX,OFFSET MSG
        MOV     AH,9
        INT     21h
        MOV     AX,4C00h
        INT     21h
MSG     DB      'Hello from SEGREF',13,10,'$'
CODE    ENDS
        END     START