# sum.gdb - Lab 4.8: the stack frame of sum()
# gdb -batch -x sum.gdb ./sumtest
set pagination off
break *sum+4
run
info registers rdi rsi rbp rsp
x/2gx $rsp
info symbol *(long *)($rsp + 8)
x/10gd $rdi
finish