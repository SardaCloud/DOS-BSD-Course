# Makefile -- Module 5, Lab 5.8 (FreeBSD make). Run "make" in this directory.
# Every step of the pipeline is a separate target, so you can look at each file.

all: hello hello-static bumper

hello.i: hello.c
	cc -E hello.c -o hello.i

hello.s: hello.c
	cc -O2 -S hello.c -o hello.s

hello.o: hello.c
	cc -O2 -c hello.c -o hello.o

hello: hello.o
	cc -o hello hello.o

hello-static: hello.o
	cc -static -o hello-static hello.o

bump.o: bump.asm
	nasm -f elf64 -o bump.o bump.asm

bumper: main.c bump.o
	cc -o bumper main.c bump.o

clean:
	rm -f hello.i hello.s hello.o hello hello-static bump.o bumper