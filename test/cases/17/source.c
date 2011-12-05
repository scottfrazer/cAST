typedef int MILES, KLICKSP();
typedef struct { double hi, lo; } range;
typedef struct s { int x; } t, * tp;

int main()
{
  MILES distance; /* int */
  extern KLICKSP * metricp; /* pointer to function with no parameters returning int */
  t w = { .x = 7 };
  tp v;
  v = &w;
  range y; /* struct */
  range z, *zp; /* struct, ptr to struct */
  printf("%d\n", v->x);
}

int test(register const int a)
{
  return a;
}
