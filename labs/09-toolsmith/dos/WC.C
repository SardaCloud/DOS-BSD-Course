/* wc.c -- count lines, words and bytes, like wc(1), in files or standard input.
 * The input is read in binary: a line is a LF, a word is a run of bytes other
 * than blank, tab, LF, VT, FF and CR, and every byte counts, CR and Ctrl-Z too.
 * The same source builds on both systems:
 *   MS-DOS, Microsoft C 5.10:  CL /AS WC.C T:\BLD\LIB\SETARGV.OBJ /link /NOE
 *   FreeBSD:                   cc -Wall -o wc wc.c
 */
#include <stdio.h>

#ifdef MSDOS
#include <fcntl.h>
#include <io.h>
#define BINARY_STDIN()  setmode(fileno(stdin), O_BINARY)
#else
#define BINARY_STDIN()
#endif

static unsigned long total_l, total_w, total_c;

static void count(FILE *fp, char *name)
{
    unsigned long l = 0, w = 0, c = 0;
    int ch, inword = 0;

    while ((ch = getc(fp)) != EOF) {
        /* TODO: count the byte; a LF ends a line; a word starts at a byte that
         * is not blank or tab..CR ('\t'..'\r') and follows such a byte or
         * the start of the input. */
    }
    printf("%8lu%8lu%8lu", l, w, c);
    if (name != NULL)
        printf(" %s", name);
    printf("\n");
    total_l += l;
    total_w += w;
    total_c += c;
}

int main(int argc, char *argv[])
{
    FILE *fp;
    int i, status = 0;

    if (argc < 2) {
        BINARY_STDIN();
        count(stdin, NULL);
        return 0;
    }
    for (i = 1; i < argc; i++) {
        if ((fp = fopen(argv[i], "rb")) == NULL) {
            fprintf(stderr, "wc: %s: cannot open\n", argv[i]);
            status = 1;
            continue;
        }
        count(fp, argv[i]);
        fclose(fp);
    }
    if (argc > 2)
        printf("%8lu%8lu%8lu total\n", total_l, total_w, total_c);
    return status;
}
