/* sumtest.c - Lab 4.8: call the assembly function sum() from C */
#include <stdio.h>

long sum(const long *a, long n);

static const long table[] = { 1000, 2000, 3000, 4000, 5000, 6000, 7000,
    8000, 9000, 10000 };

int
main(void)
{
	printf("%ld\n", sum(table, sizeof(table) / sizeof(table[0])));
	return (0);
}