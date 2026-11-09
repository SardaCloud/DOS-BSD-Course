/* MODELS.C -- Module 5: the same C code in two memory models */
#include <stdio.h>

int data[4] = { 1, 2, 3, 4 };

int sum(int *a, int n)
{
    int s = 0, i;

    for (i = 0; i < n; i++)
        s += a[i];
    return s;
}

int main(void)
{
    printf("sum = %d\n", sum(data, 4));
    return 0;
}