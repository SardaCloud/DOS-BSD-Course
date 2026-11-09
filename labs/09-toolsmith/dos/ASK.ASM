; ASK.ASM -- (starter) ask a question and return the answer as the exit code.
; usage: ASK keys [prompt]          e.g.  ASK YNQ Overwrite the old copy
; Prints "prompt [Y,N,Q]? ", reads one key, echoes it and exits with 1 for
; the first key, 2 for the second, ...; 0 at the end of the input (and after
; Ctrl-C); 255 if there are no keys.  Keys are not case-sensitive.
; From the keyboard a wrong key beeps; from a file or a pipe the answer is the
; first character of a line, and a line that starts with another one is skipped.
; Build (MASM 5.10): MASM ASK;  LINK ASK;  EXE2BIN ASK ASK.COM

CODE    SEGMENT
        ASSUME  CS:CODE, DS:CODE, ES:CODE, SS:CODE
        ORG     100h

START:  CLD
        MOV     SI,81h                  ; the command tail
        CALL    SKIPSP
        MOV     KEYS,SI                 ; the first word is the list of keys
NEXTK:  LODSB
        CMP     AL,' '
        JBE     ENDK
        CALL    UPPER
        MOV     [SI-1],AL               ; keep the keys in upper case
        JMP     NEXTK
ENDK:   DEC     SI
        MOV     CX,SI
        SUB     CX,KEYS
        MOV     NKEYS,CX
        OR      CX,CX
        JNZ     HAVEK
        JMP     USAGE

HAVEK:  CALL    SKIPSP                  ; the rest of the tail is the prompt
        MOV     DI,SI
FINDCR: CMP     BYTE PTR [DI],13        ; DI -> the CR at its end
        JE      TRIM
        INC     DI
        JMP     FINDCR
TRIM:   CMP     DI,SI                   ; drop the blanks before the CR
        JE      KLIST                   ; (COMMAND leaves them there when it
        CMP     BYTE PTR [DI-1],' '     ; takes "<file" out of the line)
        JE      TRIM1
        CMP     BYTE PTR [DI-1],9
        JNE     PROMPT
TRIM1:  DEC     DI
        JMP     TRIM
PROMPT: LODSB                           ; print the prompt, SI up to DI
        CALL    PUTC
        CMP     SI,DI
        JB      PROMPT
        MOV     AL,' '
        CALL    PUTC
KLIST:  MOV     AL,'['                  ; "[Y,N,Q]? "
        MOV     SI,KEYS
        MOV     CX,NKEYS
KNEXT:  CALL    PUTC
        LODSB
        CALL    PUTC
        MOV     AL,','
        LOOP    KNEXT
        MOV     AL,']'
        CALL    PUTC
        MOV     AL,'?'
        CALL    PUTC
        MOV     AL,' '
        CALL    PUTC

; TODO 1: ask DOS whether handle 0 is the keyboard.  IOCTL function 4400h
;         (AX = 4400h, BX = handle) returns the device information word in
;         DX.  If bit 7 (a device) and bit 0 (console input) are both set,
;         set CONS to 1.  Until then every input is read as a file.

GETKEY: CMP     CONS,1
        JNE     FROMF
        MOV     AH,08h                  ; keyboard: one key, no echo; Ctrl-C
        INT     21h                     ; ends the program here
        OR      AL,AL
        JNZ     GOTKEY
        MOV     AH,08h                  ; 0 = an extended key: skip its code
        INT     21h
        JMP     SHORT BADKEY
FROMF:  MOV     AH,3Fh                  ; a file, a pipe or a device: read
        XOR     BX,BX                   ; one byte from handle 0
        MOV     CX,1
        MOV     DX,OFFSET ONECH
        INT     21h
        JC      EOF
        OR      AX,AX
        JZ      EOF                     ; 0 bytes: the end of the input
        MOV     AL,ONECH
        CMP     AL,10                   ; LF: the next byte starts a line
        JNE     NOTLF
        MOV     SOL,1
        JMP     GETKEY
NOTLF:  CMP     SOL,1                   ; only the first byte of a line
        JNE     GETKEY                  ; is an answer
        MOV     SOL,0
GOTKEY: CALL    UPPER
; TODO 2: look for AL among the NKEYS keys at KEYS (REPNE SCASB with ES:DI
;         and CX).  If it is the k-th key, echo it with PUTC, end the line
;         with NEWLN and exit (function 4Ch) with code k.  Work out k from
;         what is left in CX.  If it is not there, fall through to BADKEY.
BADKEY: CMP     CONS,1
        JNE     GETKEY                  ; in a file: skip the line
        MOV     AL,7                    ; beep at the keyboard
        CALL    PUTC
        JMP     GETKEY

EOF:    CALL    NEWLN                   ; no answer: exit code 0
        MOV     AX,4C00h
        INT     21h

USAGE:  MOV     AH,40h                  ; to standard error
        MOV     BX,2
        MOV     CX,USELEN
        MOV     DX,OFFSET USEMSG
        INT     21h
        MOV     AX,4CFFh
        INT     21h

SKIPSP: CMP     BYTE PTR [SI],' '       ; skip blanks and tabs at DS:SI
        JE      SKIP1
        CMP     BYTE PTR [SI],9
        JNE     SKIP2
SKIP1:  INC     SI
        JMP     SKIPSP
SKIP2:  RET

UPPER:  CMP     AL,'a'                  ; AL to upper case
        JB      UP1
        CMP     AL,'z'
        JA      UP1
        SUB     AL,'a'-'A'
UP1:    RET

NEWLN:  MOV     AL,13
        CALL    PUTC
        MOV     AL,10
PUTC:   PUSH    AX                      ; AL to standard output; keeps AX
        PUSH    BX
        PUSH    CX
        PUSH    DX
        MOV     ONECH,AL
        MOV     AH,40h
        MOV     BX,1
        MOV     CX,1
        MOV     DX,OFFSET ONECH
        INT     21h
        POP     DX
        POP     CX
        POP     BX
        POP     AX
        RET

USEMSG  DB      'usage: ASK keys [prompt]',13,10
USELEN  EQU     $-USEMSG
KEYS    DW      ?
NKEYS   DW      ?
CONS    DB      0
SOL     DB      1                       ; 1 = at the start of a line
ONECH   DB      ?

CODE    ENDS
        END     START
