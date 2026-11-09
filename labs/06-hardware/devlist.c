/* DEVLIST.C - walk the MS-DOS device driver chain (Lab 6.5)
 *
 * INT 21h function 52h returns ES:BX -> the DOS "List of Lists" (SYSINITVAR in
 * DOS/MSCONST.ASM). The header of the NUL device is embedded in it at offset 22h,
 * and every driver header starts with a far pointer to the next one; the last
 * one has offset FFFFh.
 *
 * Build with Microsoft C 5.10:  CL DEVLIST.C
 */
#include <stdio.h>
#include <dos.h>

struct devhdr {                         /* SYSDEV in INC/DEVSYM.INC */
    struct devhdr far *next;
    unsigned attr;
    unsigned strategy;
    unsigned intr;                      /* "interrupt" is a keyword in MS C */
    unsigned char name[8];              /* character devices: name; block: units */
};

static void flags(unsigned a)
{
    if (a & 0x8000) {
        printf("char");
        if (a & 0x0001) printf(" STDIN");
        if (a & 0x0002) printf(" STDOUT");
        if (a & 0x0004) printf(" NUL");
        if (a & 0x0008) printf(" CLOCK");
        if (a & 0x0010) printf(" INT29");
        if (a & 0x2000) printf(" OUTBUSY");
    } else {
        printf("block");
        if (a & 0x0002) printf(" 32BIT");
    }
    if (a & 0x4000) printf(" IOCTL");
    if (a & 0x0800) printf(" OPCL");
    if (a & 0x0040) printf(" GENIOCTL");
}

int main(void)
{
    union REGS r;
    struct SREGS s;
    unsigned char far *lol;
    struct devhdr far *d, far *next;
    struct devhdr far * far *p;
    int i, n = 0;

    r.h.ah = 0x52;
    segread(&s);
    intdosx(&r, &r, &s);
    lol = (unsigned char far *)(((unsigned long)s.es << 16) | r.x.bx);
    printf("List of Lists at %04X:%04X\n", s.es, r.x.bx);
    p = (struct devhdr far * far *)(lol + 0x08);
    d = *p;
    printf("  CLOCK device (offset 08h): %04X:%04X\n", FP_SEG(d), FP_OFF(d));
    p = (struct devhdr far * far *)(lol + 0x0C);
    d = *p;
    printf("  CON device   (offset 0Ch): %04X:%04X\n\n", FP_SEG(d), FP_OFF(d));

    printf("  # header     attr strat intr  name      flags\n");
    d = (struct devhdr far *)(lol + 0x22);
    for (;;) {
        printf("%3d %04X:%04X %04X %04X  %04X  ", ++n, FP_SEG(d), FP_OFF(d),
               d->attr, d->strategy, d->intr);
        if (d->attr & 0x8000) {
            for (i = 0; i < 8; i++)
                putchar(d->name[i]);
        } else {
            printf("%u unit%s ", d->name[0], d->name[0] == 1 ? " " : "s");
        }
        printf("  ");
        flags(d->attr);
        putchar('\n');
        next = d->next;                 /* FP_OFF needs a variable: it takes */
        if (FP_OFF(next) == 0xFFFF)     /* the address of its argument       */
            break;
        d = next;
    }
    return 0;
}
