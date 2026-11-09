/* HELLO.C -- Module 5: one small C program for both toolchains */
#include <stdio.h>

int counter = 7;                /* initialized data */
int table[100];                 /* uninitialized data (BSS) */

int square(int x)
{
    return x * x;
}

int main(void)
{
    table[3] = square(counter);
    printf("hello, world: %d\n", table[3]);
    return 0;
}