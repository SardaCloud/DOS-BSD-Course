/* hello.c -- Module 5: the same program as HELLO.C, for FreeBSD */
#include <stdio.h>

int counter = 7;		/* initialized data */
int table[100];			/* uninitialized data (BSS) */

int
square(int x)
{
	return (x * x);
}

int
main(void)
{
	table[3] = square(counter);
	printf("hello, world: %d\n", table[3]);
	return (0);
}