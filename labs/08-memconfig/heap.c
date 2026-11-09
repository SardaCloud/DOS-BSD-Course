/* HEAP.C - Lab 8.4: how much heap does a C program get on MS-DOS 4.00?
 *
 * Build twice with Microsoft C 5.10 (tools/dos_tools.py), small and large model:
 *     CL /AS /FeHEAPS.EXE HEAP.C
 *     CL /AL /FeHEAPL.EXE HEAP.C
 */
#include <stdio.h>
#include <stdlib.h>
#include <malloc.h>
#include <dos.h>

#define CHUNK 1024

static void dos_free(const char *when)
{
    unsigned maxpara;

    /* 0xFFFF paragraphs never fit: DOS fails with error 8 and returns the largest block */
    if (_dos_allocmem(0xFFFF, &maxpara) != 0)
        printf("%-28s DOS largest free block %6lu bytes\n", when, (unsigned long)maxpara * 16);
}

int main(void)
{
    unsigned n = 0, nf = 0;
    char *p, *first = NULL;
    char far *fp;

    printf("model: %s, sizeof(char *) = %u, PSP at segment %04X\n",
           sizeof(char *) == 2 ? "small" : "large", sizeof(char *), _psp);
    dos_free("at start:");
    printf("%-28s _memavl() %6u bytes, _memmax() %u\n", "near heap:", _memavl(), _memmax());

    while ((p = malloc(CHUNK)) != NULL) {   /* malloc is _nmalloc in small, _fmalloc in large model */
        p[0] = 1;
        if (first == NULL)
            first = p;
        n++;
    }
    printf("malloc(%d) succeeded %u times: %lu bytes; first block at %Fp\n",
           CHUNK, n, (unsigned long)n * CHUNK, (char far *)first);
    dos_free("after malloc:");

    while ((fp = _fmalloc(CHUNK)) != NULL) {  /* the far heap: more segments from DOS */
        fp[0] = 1;
        nf++;
    }
    printf("then _fmalloc(%d) succeeded %u times: %lu bytes\n", CHUNK, nf, (unsigned long)nf * CHUNK);
    dos_free("after _fmalloc:");
    return 0;
}
