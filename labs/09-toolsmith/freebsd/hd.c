/* hd.c -- hex dump in the format of FreeBSD's hd (hexdump -C), without the
 * "*" that hd prints for repeated lines.  Usage: hd [-t] [file]
 * -t reads the input in text mode, to show what the MS-DOS C runtime changes.
 * The same source builds on both systems:
 *   MS-DOS, Microsoft C 5.10:  CL /AS HD.C
 *   FreeBSD:                   cc -Wall -o hd hd.c
 */
#include <stdio.h>
#include <string.h>

#ifdef MSDOS
#include <fcntl.h>
#include <io.h>
#define BINARY_STDIN()  setmode(fileno(stdin), O_BINARY)
#else
#define BINARY_STDIN()
#endif

static void line(unsigned long off, unsigned char *b, int n)
{
    int i;

    printf("%08lx ", off);
    /* TODO 1: 16 columns " xx", an extra blank before the ninth, three blanks
     * for each missing byte of a short last line; then "  |", the bytes
     * from ' ' to '~' as themselves and all others as '.', and "|\n". */
}

int main(int argc, char *argv[])
{
    unsigned char b[16];
    unsigned long off = 0;
    int n, text = 0;
    FILE *fp = stdin;

    if (argc > 1 && strcmp(argv[1], "-t") == 0) {
        text = 1;
        argc--;
        argv++;
    }
    if (argc > 2) {
        fprintf(stderr, "usage: hd [-t] [file]\n");
        return 2;
    }
    /* TODO 2: with a file name, open it with "rb", or with "r" for -t, and
     * report a failure with exit code 1; without one, switch standard input
     * to binary unless -t was given. */
    while ((n = fread(b, 1, sizeof b, fp)) > 0) {
        line(off, b, n);
        off += n;
    }
    if (off > 0)
        printf("%08lx\n", off);
    return 0;
}
