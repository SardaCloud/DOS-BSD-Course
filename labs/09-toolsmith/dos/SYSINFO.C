/* SYSINFO.C -- what MS-DOS tells a program about the system it runs on:
 * the DOS version, the current drive and directory, the free disk space and
 * the largest free memory block.  Microsoft C 5.10, small model.
 * Build: CL /AS SYSINFO.C
 */
#include <stdio.h>
#include <dos.h>

int main(void)
{
    union REGS r;
    char cwd[64];
    int drive;

    r.h.ah = 0x30;                      /* get version: AL major, AH minor */
    intdos(&r, &r);
    printf("system:    MS-DOS %u.%02u\n", r.h.al, r.h.ah);

    r.h.ah = 0x19;                      /* current drive: 0 = A */
    intdos(&r, &r);
    drive = r.h.al;
    r.h.ah = 0x47;                      /* current directory of drive DL */
    r.h.dl = 0;                         /* 0 = the current drive */
    r.x.si = (unsigned) cwd;            /* DS:SI = 64-byte buffer */
    intdos(&r, &r);
    printf("directory: %c:\\%s\n", 'A' + drive, cwd);

    /* TODO 1: function 36h with DL = 0 returns AX = sectors per cluster (FFFFh
     * for an invalid drive), BX = free clusters, CX = bytes per sector and
     * DX = total clusters.  Print  disk:      N bytes free of M  ; compute in
     * unsigned long, because the products do not fit in 16 bits. */

    /* TODO 2: function 48h with BX = FFFFh asks for 1 MB and fails; BX then
     * holds the size of the largest free block in paragraphs.  Print
     *  memory:    largest free block N bytes  . */
    return 0;
}
