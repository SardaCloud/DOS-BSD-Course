CODE    SEGMENT
        ASSUME  CS:CODE
        JMP     AHEAD
        DB      10 DUP (0)
AHEAD:  JMP     AHEAD
        JMP     SHORT FAR1
        DB      10 DUP (0)
FAR1:   NOP
CODE    ENDS
        END
