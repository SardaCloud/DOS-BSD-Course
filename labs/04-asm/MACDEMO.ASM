        PAGE    ,132
        .LALL                           ; list macro expansions in full
; MACDEMO.ASM - Study case 4.C: the MS-DOS kernel's own macros at work
; Copy DOSMAC.INC from v4.0\src\INC, then: MASM MACDEMO,,MACDEMO;
DEBUG   EQU     0               ; DOSMAC.INC tests it (line 376)
        .XLIST                          ; do not list the include file
INCLUDE DOSMAC.INC
        .LIST

DOSGROUP GROUP  CODE
CODE    SEGMENT BYTE PUBLIC 'CODE'
        ASSUME  CS:DOSGROUP

; CountChars: CX = number of bytes before the '$' at DS:SI, ZF=1 if none
        procedure CountChars,NEAR
        SaveReg <AX,SI>
        XOR     CX,CX
Next:   LODSB
        CMP     AL,'$'
        JZ      Done
        INC     CX
        JMP     Next
Done:   RestoreReg <SI,AX>
        OR      CX,CX
        retz                            ; nothing to do if the string is empty
        context ES                      ; ES = DOSGROUP, as the kernel does
        return
EndProc CountChars

; IsEmpty: ZF=1 if the byte at DS:SI is '$'
        procedure IsEmpty,NEAR
        CMP     BYTE PTR [SI],'$'
        retz                            ; a short jump to an earlier RET
        CMP     BYTE PTR [SI],0
        return
EndProc IsEmpty

; Unbalanced: pushes a register and forgets to pop it
        procedure Unbalanced,NEAR
        SaveReg <BX>
        return
EndProc Unbalanced

CODE    ENDS
        END
