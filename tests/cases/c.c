#define qux0 7
#define qux qux0
#define foo(x, y) x+y
//          s  s  |c|
#define bar foo - foo(66,33) - foo - foo
//          |---------c----------|
#define baz foo(4,5)
//              c c
#define var(s, t, ...) s+t+foo(__VA_ARGS__)
// functions take ctokens as params, return ctokens.
// replacement tokens are stored as ctokens.

int main()
{
  int foo = 2;
  printf("%d\n", 1000+7000);
  printf("%d\n", var(1,2,qux,4));
  printf("%d\n", bar(7,8));
  printf("%d\n", foo(4+1,7-1));
  return 0;
}
