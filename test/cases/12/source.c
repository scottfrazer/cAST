#define msg "Hello World\n"
int main( int argc, char * argv[] )
{
  int y;
  y = factorial(6);
  printf(msg);
  printf("6! = %d\n", y);
}

int factorial(int x)
{
  if ( x == 1 )
    return 1;
  return x * factorial(x-1);
}
