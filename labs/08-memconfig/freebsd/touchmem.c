/*
 * touchmem.c - Lab 8.6: allocate memory, then touch it in steps, and watch the
 * process's virtual size (VSZ) and resident set size (RSS) with ps(1).
 *
 *     cc -O0 -o touchmem touchmem.c
 *     ./touchmem 256          # allocate 256 MB, touch it in four steps, free it
 *     MALLOC_CONF=dirty_decay_ms:0,muzzy_decay_ms:0 ./touchmem 256
 *                             # the same, but jemalloc returns freed pages at once
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static void
show(const char *what)
{
	char cmd[80];

	printf("--- %s\n", what);
	fflush(stdout);
	/*
	 * Two -o options: in "-o vsz=,rss=" the header after '=' would swallow
	 * ",rss=". An empty MALLOC_CONF keeps ps from inheriting ours (with
	 * stats_print:true it would print its own statistics).
	 */
	snprintf(cmd, sizeof(cmd), "MALLOC_CONF= ps -o vsz= -o rss= -p %d",
	    (int)getpid());
	system(cmd);			/* VSZ and RSS in KB */
}

int
main(int argc, char *argv[])
{
	size_t mb = argc > 1 ? strtoul(argv[1], NULL, 10) : 256;
	size_t size = mb << 20, step = size / 4, off;
	long page = sysconf(_SC_PAGESIZE);
	char *p;
	int i;

	printf("pid %d, page size %ld, allocating %zu MB\n", (int)getpid(), page, mb);
	show("before malloc");
	if ((p = malloc(size)) == NULL) {
		perror("malloc");
		return (1);
	}
	show("after malloc, nothing touched");
	for (i = 1; i <= 4; i++) {
		for (off = (i - 1) * step; off < i * step; off += page)
			p[off] = 1;		/* first write to a page: a page fault */
		printf("touched %zu MB\n", i * step >> 20);
		show("after touching");
		sleep(2);
	}
	free(p);
	show("after free");
	sleep(12);
	show("12 s after free");
	return (0);
}
