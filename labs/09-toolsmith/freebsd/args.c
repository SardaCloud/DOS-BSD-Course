/* args.c -- print argc, every argv[i] numbered, and the executable's path
 * Build: cc -Wall -o args args.c
 */
#include <sys/auxv.h>
#include <stdio.h>

int
main(int argc, char *argv[])
{
	char path[1024];
	int i;

	printf("argc: %d\n", argc);
	/* TODO 1: print every argv[i] as  i: [text]  , numbered from 0 */
	/* TODO 2: use elf_aux_info(3) with AT_EXECPATH to print  path: [..] */
	return 0;
}
