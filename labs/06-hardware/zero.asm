; ZERO.SYS - a character device "ZERO$" that reads as zero bytes (Exercise 6.1, starter)
;   CONFIG.SYS:  DEVICE=\ZERO.SYS
;   Complete the parts marked TODO. Reads should return zeros, at most LIMIT bytes after
;   each open and then 0 bytes (end of file); writes are accepted and thrown away.
; nasm -f bin -o ZERO.SYS zero.asm
        cpu     8086
        org     0                       ; a driver image starts at offset 0 (no PSP)

; device header (SYSDEV in INC/DEVSYM.INC) ---------------------------------
header: dw      -1, -1                  ; link to the next driver, set by SYSINIT
        dw      8800h                   ; TODO: explain each bit set here
        dw      strategy
        dw      interrupt
        db      'ZERO$   '              ; 8 characters, padded with blanks

LIMIT   equ     1000                    ; bytes per open
packet  dd      0                       ; request packet saved by the strategy routine
left    dw      LIMIT

; offsets in the request packet (SRHEAD in INC/DEVSYM.INC, MSBIO1.ASM lines 309-317)
CMD     equ     2
STATUS  equ     3
NDBYTE  equ     13                      ; non-destructive read: the character
TRANS   equ     14                      ; read/write: transfer address (dword)
COUNT   equ     18                      ; read/write: byte count
DONE    equ     0100h                   ; status: done
ERROR   equ     8000h                   ; status: error
BUSY    equ     0200h                   ; status: busy (no input waiting)

strategy:                               ; ES:BX -> request packet
        mov     [cs:packet], bx
        mov     [cs:packet+2], es
        retf

interrupt:
        push    ax                      ; a driver must preserve every register
        push    bx
        push    cx
        push    dx
        push    di
        push    ds
        push    es
        lds     bx, [cs:packet]
        mov     ax, DONE
        mov     cl, [bx+CMD]
        cmp     cl, 0
        je      init
        ; TODO: command 4 (read), 5 (non-destructive read), 13 (open);
        ;       which commands can simply report "done"? Which must report
        ;       "unknown command" (ERROR | DONE | 3)?
exit:   mov     [bx+STATUS], ax
        pop     es
        pop     ds
        pop     di
        pop     dx
        pop     cx
        pop     bx
        pop     ax
        retf

; initialisation: runs once, from SYSINIT, and is then thrown away ----------
init:   ; TODO: set the break address (TRANS, TRANS+2) so that this code is freed,
        ;       and print a message. Careful: function 09h ends strings at '$'.
        jmp     exit
