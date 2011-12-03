

int f(void), *fip(), (*pfi)();

/* Array of pointers to three functions that have
 * two integer pointers as parameters and return
 * an int
 */

int (*apfi[3])(int *x, int *y);

/*
 * declares a function fpfi that returns a pointer 
 * to a function returning an int. The function 
 * fpfi has two parameters: a pointer to a 
 * function returning an int (with one parameter 
 * of type long int), and an int. The pointer 
 * returned by fpfi points to a function that has 
 * one int parameter and accepts zero or more 
 * additional arguments of any type.
 */

int (*fpfi(int (*)(long), int))(int, ...);

int main() { char str[]={'a','b','c',}; return 0; }
