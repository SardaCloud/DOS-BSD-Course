/* main.c -- Module 5, Labs 5.6 and 5.8: the C side of bump.asm (FreeBSD) */
#include <stdio.h>

int counter = 10;
void bump(void);

void
report(int value)
{
	printf("counter is now %d\n", value);
}

int
main(void)
{
	bump();
	bump();
	return (0);
}