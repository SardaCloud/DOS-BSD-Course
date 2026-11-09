        PAGE    ,132
; SETUPM.ASM - section 4.3: boot-sector set-up code in MASM syntax
CODE    SEGMENT
        ASSUME  CS:CODE
START:  CLD
        XOR     AX,AX
        MOV     ES,AX
        MOV     DS,AX
        MOV     SS,AX
        MOV     SP,7C00h
CODE    ENDS
        END     START
