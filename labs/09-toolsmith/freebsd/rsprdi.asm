; rsprdi.asm -- exit with status rdi - rsp, as the kernel set them at entry.
; Build: nasm -f elf64 rsprdi.asm && ld -o rsprdi rsprdi.o

        global  _start
_start: sub     rdi, rsp                ; 0: rsp points at argc, 8: 8 bytes below
        mov     eax, 1                  ; SYS_exit, status = low byte of rdi
        syscall
