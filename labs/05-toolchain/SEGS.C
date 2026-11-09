/* SEGS.C -- Module 5, Study case 5.B: where did EXEC put the segments? */
#include <stdio.h>
#include <dos.h>

extern unsigned _psp;           /* set by the start-up code */
int counter = 7;

int main(void)
{
    struct SREGS r;
    int far *p = (int far *)&counter;

    segread(&r);
    printf("PSP %04X  CS %04X  DS %04X  SS %04X  &counter %04X:%04X\n",
           _psp, r.cs, r.ds, r.ss, FP_SEG(p), FP_OFF(p));
    return 0;
}