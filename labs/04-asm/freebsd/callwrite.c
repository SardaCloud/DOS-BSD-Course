/* callwrite.c - Lab 4.7: two write(2) calls to follow in gdb */
#include <errno.h>
#include <stdio.h>
#include <unistd.h>

int
main(void)
{
	ssize_t n;

	n = write(1, "hi\n", 3);
	printf("write(1) returned %zd\n", n);
	n = write(99, "hi\n", 3);
	printf("write(99) returned %zd, errno %d\n", n, errno);
	return (0);
}