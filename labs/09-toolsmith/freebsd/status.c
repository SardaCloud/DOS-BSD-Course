/* status.c -- show the raw wait(2) status word for a child's exit (section 9.4)
 * usage: ./status N     child calls _exit(N)
 *        ./status -S    child kills itself with signal S
 */
#include <sys/wait.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

int
main(int argc, char *argv[])
{
	int n, status;
	pid_t pid;

	if (argc != 2) {
		fprintf(stderr, "usage: status N | -SIGNAL\n");
		return 2;
	}
	n = atoi(argv[1]);
	pid = fork();
	if (pid == -1) {
		perror("fork");
		return 1;
	}
	if (pid == 0) {
		if (n < 0)
			kill(getpid(), -n);
		_exit(n);
	}
	waitpid(pid, &status, 0);
	printf("status 0x%04x: ", status);
	if (WIFEXITED(status))
		printf("exited, WEXITSTATUS = %d\n", WEXITSTATUS(status));
	else if (WIFSIGNALED(status))
		printf("killed by signal %d\n", WTERMSIG(status));
	return 0;
}
