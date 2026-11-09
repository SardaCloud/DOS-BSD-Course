# wstep.gdb - Lab 4.7: follow write(2) through the libsys stub
# gdb -batch -x wstep.gdb ./callwrite
set pagination off
set breakpoint pending on
break __sys_write
run
backtrace
info symbol $pc
x/5i $pc
stepi 2
info registers rax rdi rsi rdx r10 rcx r11 rip
tbreak *($pc + 2)
continue
info registers rax rdx rcx r8 r9 r10 r11 eflags rip
continue
tbreak *($pc + 10)
continue
info registers rax rdx rcx r8 r9 r10 r11 eflags rip
stepi
x/3i $pc
finish
continue