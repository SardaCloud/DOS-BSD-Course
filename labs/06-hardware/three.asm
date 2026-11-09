; THREE.COM - one line of text written three ways (Lab 6.1)
;   1. INT 21h function 02h: DOS writes the character to standard output (handle 1)
;   2. INT 10h function 0Eh: the BIOS writes the character at the cursor ("teletype")
;   3. direct: the program stores character/attribute pairs into video memory at B800h
; nasm -f bin -o THREE.COM three.asm
        cpu     8086
        org     100h

; 1. DOS -------------------------------------------------------------------
        mov     si, msg_dos
dos_lp: lodsb
        or      al, al
        jz      bios
        mov     dl, al                  ; DL = character
        mov     ah, 02h                 ; display output
        int     21h
        jmp     dos_lp

; 2. BIOS ------------------------------------------------------------------
bios:   mov     si, msg_bios
bios_lp:
        lodsb
        or      al, al
        jz      video
        mov     ah, 0Eh                 ; teletype output
        mov     bx, 0007h               ; BH = page 0, BL = colour (graphics modes)
        int     10h
        jmp     bios_lp

; 3. Video memory ----------------------------------------------------------
video:  mov     ax, 40h                 ; BIOS data area
        mov     es, ax
        mov     al, [es:51h]            ; cursor row on page 0 (40:50 = column)
        mov     bl, 160                 ; 80 columns * 2 bytes
        mul     bl
        mov     di, ax                  ; offset of the start of that row
        mov     ax, 0B800h              ; colour text-mode video memory
        mov     es, ax
        mov     si, msg_video
        mov     ah, 1Eh                 ; attribute: yellow on blue
vid_lp: lodsb
        or      al, al
        jz      newline
        stosw                           ; ES:[DI] = AL (character), AH (attribute)
        jmp     vid_lp

newline:                                ; the cursor did not move: move it with the BIOS
        mov     ax, 0E0Dh
        int     10h
        mov     ax, 0E0Ah
        int     10h
        mov     ax, 4C00h
        int     21h

msg_dos         db      "1 DOS   INT 21h AH=02h", 13, 10, 0
msg_bios        db      "2 BIOS  INT 10h AH=0Eh", 13, 10, 0
msg_video       db      "3 VIDEO B800:row*160  ", 0
