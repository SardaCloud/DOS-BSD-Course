/* ARGS.C -- print argc and every argv[i], numbered (Microsoft C 5.10)
 * Build: CL /AS ARGS.C                       (no wildcard expansion)
 *        CL /AS /FeARGSW.EXE ARGS.C T:\BLD\LIB\SETARGV.OBJ /link /NOE
 *                                            (the start-up code expands *.TXT)
 */
#include <stdio.h>

int main(int argc, char *argv[])
{
    int i;

    printf("argc: %d\n", argc);
    /* TODO: print every argv[i] as  i: [text]  , numbered from 0 */
    return 0;
}
