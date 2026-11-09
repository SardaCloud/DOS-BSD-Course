; bump.asm -- Module 5, Lab 5.6: a small x86-64 function as an ELF relocatable object
; Build:  nasm -f elf64 -o bump.o bump.asm
; C view: extern int counter; int step = 3;
;         void bump(void) { counter += step; report(counter); }
        default rel                     ; [name] means [rip + name]

        extern  counter                 ; an int defined in another object (main.c)
        extern  report                  ; a function defined in another object
        global  bump                    ; this object defines bump ...
        global  step                    ; ... and step for the others

        section .data
step:   dd      3

        section .text
bump:
        mov     eax, [counter]          ; counter is not in this file: relocation
        add     eax, [step]             ; step is, but .data has no address yet: relocation
        mov     [counter], eax
        mov     edi, eax                ; first integer argument in %edi (System V AMD64 ABI)
        jmp     report wrt ..plt        ; tail call through the PLT if report is in a library