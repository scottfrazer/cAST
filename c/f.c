#define FOO(x) x+1
#define BAR(y) y+2
#define BAZ(z) FOO(BAR(z))

int main()
{
	printf("%d\n", FOO(BAR(1000)));
	return 0;
}