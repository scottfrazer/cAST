cAST
====

C Preprocessor and Parser

Example
-------

```bash
$ cat source.c
```

```c
int main( int argc, char * argv[] )
{
  int y;
  y = factorial(6);
  printf("6! = %d\n", y);
}

int factorial(int x)
{
  if ( x == 1 )
    return 1;
  return x * factorial(x-1);
}
```

```bash
$ cast ast source.c
```

```ast
(TranslationUnit:
  external_declarations=[
    (ExternalDeclaration:
      declarations=(FunctionDefinition:
        body=[
          (Declaration:
            init_declarators=[
              (InitDeclarator:
                initializer=None,
                declarator=(Declarator:
                  direct_declarator=[c:115] identifier (y) [source.c line 3, col 7],
                  pointer=None
                )
              )
            ],
            declaration_specifiers=[
              [c:13] int (int) [source.c line 3, col 3]
            ]
          ),
          (Assign:
            var=[c:115] identifier (y) [source.c line 4, col 3],
            value=(FuncCall:
              params=[
                [c:49] integer_constant (6) [source.c line 4, col 17]
              ],
              name=[c:115] identifier (factorial) [source.c line 4, col 7]
            )
          ),
          (FuncCall:
            params=[
              [c:82] string_literal ("6! = %d\n") [source.c line 5, col 10],
              [c:115] identifier (y) [source.c line 5, col 23]
            ],
            name=[c:115] identifier (printf) [source.c line 5, col 3]
          )
        ],
        declaration_list=None,
        signature=(Declarator:
          direct_declarator=(FunctionSignature:
            params=(ParameterTypeList:
              parameter_declarations=[
                (NamedParameter:
                  declaration_specifiers=[
                    [c:13] int (int) [source.c line 1, col 11]
                  ],
                  declarator=(Declarator:
                    direct_declarator=[c:115] identifier (argc) [source.c line 1, col 15],
                    pointer=None
                  )
                ),
                (NamedParameter:
                  declaration_specifiers=[
                    [c:43] char (char) [source.c line 1, col 21]
                  ],
                  declarator=(Declarator:
                    direct_declarator=(Array:
                      name=[c:115] identifier (argv) [source.c line 1, col 28],
                      size=None
                    ),
                    pointer=[
                      [c:92] asterisk (*) [source.c line 1, col 26]
                    ]
                  )
                )
              ],
              va_args=None
            ),
            declarator=[c:115] identifier (main) [source.c line 1, col 5]
          ),
          pointer=None
        )
      ),
      declaration_specifiers=[
        [c:13] int (int) [source.c line 1, col 1]
      ]
    ),
    (ExternalDeclaration:
      declarations=(FunctionDefinition:
        body=[
          (If:
            elseif=None,
            statement=(Return:
              expr=[c:49] integer_constant (1) [source.c line 11, col 12]
            ),
            condition=(Equals:
              right=[c:49] integer_constant (1) [source.c line 10, col 13],
              left=[c:115] identifier (x) [source.c line 10, col 8]
            ),
            else=None
          ),
          (Return:
            expr=(Mul:
              right=(FuncCall:
                params=[
                  (Sub:
                    right=[c:49] integer_constant (1) [source.c line 12, col 26],
                    left=[c:115] identifier (x) [source.c line 12, col 24]
                  )
                ],
                name=[c:115] identifier (factorial) [source.c line 12, col 14]
              ),
              left=[c:115] identifier (x) [source.c line 12, col 10]
            )
          )
        ],
        declaration_list=None,
        signature=(Declarator:
          direct_declarator=(FunctionSignature:
            params=(ParameterTypeList:
              parameter_declarations=[
                (NamedParameter:
                  declaration_specifiers=[
                    [c:13] int (int) [source.c line 8, col 15]
                  ],
                  declarator=(Declarator:
                    direct_declarator=[c:115] identifier (x) [source.c line 8, col 19],
                    pointer=None
                  )
                )
              ],
              va_args=None
            ),
            declarator=[c:115] identifier (factorial) [source.c line 8, col 5]
          ),
          pointer=None
        )
      ),
      declaration_specifiers=[
        [c:13] int (int) [source.c line 8, col 1]
      ]
    )
  ]
)
```
