/* sysinfo.c -- what FreeBSD tells a program about the system it runs on:
 * uname(3), the current directory, statfs(2) for the file system of ".",
 * the hw.physmem sysctl and the data size limit.
 * Build: cc -Wall -o sysinfo sysinfo.c
 */
#include <sys/param.h>
#include <sys/mount.h>
#include <sys/resource.h>
#include <sys/sysctl.h>
#include <sys/utsname.h>
#include <stdint.h>
#include <stdio.h>
#include <unistd.h>

int
main(void)
{
	struct utsname u;
	struct statfs fs;
	struct rlimit rl;
	char cwd[MAXPATHLEN];
	unsigned long physmem;
	size_t len = sizeof(physmem);
	int status = 0;

	if (uname(&u) == 0)
		printf("system:    %s %s %s\n", u.sysname, u.release, u.machine);
	else {
		perror("uname");
		status = 1;
	}
	if (getcwd(cwd, sizeof(cwd)) != NULL)
		printf("directory: %s\n", cwd);
	else {
		perror("getcwd");
		status = 1;
	}
	/* TODO: statfs(2) on "." gives f_bavail and f_blocks in units of f_bsize,
	 * and the names f_mntfromname and f_mntonname; sysctlbyname(3) reads
	 * "hw.physmem" into an unsigned long; getrlimit(2) with RLIMIT_DATA gives
	 * the data size limit.  Print them as  disk:  ,  memory:  and a second
	 * memory line, and set status to 1 if a call fails. */
	return status;
}
