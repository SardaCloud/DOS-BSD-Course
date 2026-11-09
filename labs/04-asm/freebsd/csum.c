/* csum.c - Lab 4.8: the same function in C, to compare with the compiler's code */
long
csum(const long *a, long n)
{
	long s = 0;

	while (n-- > 0)
		s += *a++;
	return (s);
}