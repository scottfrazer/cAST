#define true 1
#define false 0
#define pass printf("pass\n")
#define fail printf("fail\n")

int main()
{
  int x;

  if (true) pass;
  if (true) {pass;}
  if (false) fail; else pass;
  if (false) {fail;} else pass;
  if (false) {fail;} else {pass;}
  if (true) for(x=0;x<1;x++){pass;}
  if (false) for(x=0;x<1;x++)fail; else for(x=0;x<1;x++)pass;
  if (false) {for(x=0;x<1;x++){fail;}} else {for(x=0;x<1;x++){pass;}}
  if (false) for(x=0;x<1;x++){fail;} else for(x=0;x<1;x++){pass;}
  if(false)fail;else if(true)pass;else fail;
}

