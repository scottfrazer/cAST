#include    <stdio.h>
#include<stdlib.h>
#define stdin   (&__sF[0])
#ifdef stdin
int func();
#else
int func1();
#endif
/* this is a comment */
#define FUNC(A,B) A+B
#define Y 7
#define J 2
#define PATH "b.c"
#define PHI(X, Y) X-Y
int add(int x, int y) {return x+y;}
#define X FUNC(1,J) + Y
#define Z add(1,2)
#define THETA 1 + PHI(10, 2)
#include PATH
#define PATH "c.c"
int main()
{
printf("THETA %d\n", THETA);
printf("EXT %d\n", EXT);
#if X==10
    printf("first\n");

#endif
int a = 0;
#define A 1
#define FOO 1
#ifdef FOO
    #ifndef B
    printf("second %d\n", A);
    printf("third\n");
    #endif
#elif 0
#elif 2-1
printf("elif!\n");
#elif 3-1
printf("elif, again!\n");
#endif
a += 1;
#undef A
    return 0;
#undef FOO
}
