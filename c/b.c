#include <stdio.h>
#define EXT(a,b) a+b
#define alias EXT
int main() {
    printf("%d\n", alias(7,8));
}
