/* USELIB.C -- Module 5, Lab 5.5: uses one function of MYLIB.LIB */
#include <stdio.h>

int addup(int a, int b);

int main(void)
{
    printf("2 + 3 = %d\n", addup(2, 3));
    return 0;
}