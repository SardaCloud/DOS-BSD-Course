/*
 * rawkeys.c - print the bytes the terminal delivers, in cooked or raw mode (Lab 6.7)
 *
 *   rawkeys        cooked: one read(2) of up to 40 bytes, as KEYS.COM does on MS-DOS
 *   rawkeys -r     raw: cfmakeraw(3) + tcsetattr(3), then one byte per read(2)
 *                  until 'q' or 16 bytes; the old settings are restored at the end
 *
 * Build on FreeBSD:  cc -Wall -o rawkeys rawkeys.c
 */
#include <err.h>
#include <stdio.h>
#include <string.h>
#include <termios.h>
#include <unistd.h>

static void
report(const char *when, const struct termios *t)
{
	printf("%s: ICANON=%d ECHO=%d ISIG=%d VMIN=%d VTIME=%d\n", when,
	    (t->c_lflag & ICANON) != 0, (t->c_lflag & ECHO) != 0,
	    (t->c_lflag & ISIG) != 0, t->c_cc[VMIN], t->c_cc[VTIME]);
}

int
main(int argc, char *argv[])
{
	struct termios old, raw;
	unsigned char buf[48];
	ssize_t n, total = 0;
	int i;

	if (tcgetattr(STDIN_FILENO, &old) == -1)
		err(1, "tcgetattr (is standard input a terminal?)");
	report("before", &old);

	if (argc > 1 && strcmp(argv[1], "-r") == 0) {
		raw = old;
		cfmakeraw(&raw);	/* no ICANON, ECHO, ISIG, ICRNL, OPOST... */
		raw.c_cc[VMIN] = 1;	/* read(2) returns after 1 byte */
		raw.c_cc[VTIME] = 0;	/* and waits for it forever */
		if (tcsetattr(STDIN_FILENO, TCSAFLUSH, &raw) == -1)
			err(1, "tcsetattr");
		report("raw", &raw);
		while (total < 16) {
			n = read(STDIN_FILENO, buf + total, 1);
			if (n <= 0)
				break;
			if (buf[total++] == 'q')
				break;
		}
		tcsetattr(STDIN_FILENO, TCSAFLUSH, &old);
	} else {
		printf("cooked read(0, buf, 40)\n");
		fflush(stdout);
		total = read(STDIN_FILENO, buf, 40);
		if (total < 0)
			err(1, "read");
	}

	printf("read returned %d bytes:", (int)total);
	for (i = 0; i < total; i++)
		printf(" %02X", buf[i]);
	printf("\n");
	return (0);
}
