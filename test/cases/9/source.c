/* declares a function fpfi that returns a pointer to a function returning an int. The function fpfi has two parameters: a pointer to a function returning an int (with one parameter of type long int), and an int. The pointer returned by fpfi points to a function that has one int parameter and accepts zero or more additional arguments of any type. */
int (*fpfi(int (*)(long), int))(int, ...);

/* def parse_parameters(self, tokenIterator):
 *   param = []
 *   params = []
 *   hint = ABSTRACT_PARAMETER_HINT
 *   startParenLevel = self.parenLevel
 *   for token in tokenIterator:
 *     if token == lparen and next token in delcaration_specifiers:
 *       param.extend(parse_parameters(tokenIterator))
 *       continue
 *     if (token == comma) or (token == rparen and self.parenLevel == startParenLevel - 1):
 *       params.append(hint)
 *       params.extend(param)
 *       params.append(token)
 *       hint = ABSTRACT_PARAMETER_HINT
 *       if token == rparen:
 *         break
 *     if token.id == cParser.TERMINAL_IDENTIFIER:
 *       hint = NAMED_PARAMETER_HINT
 *   return params
 *
 * if funcFound and token == lparen and next token in delcaration_specifiers:
 *   // add the lparen to ztokens
 *   ztokens.extend(parse_parameters(tokenIterator))
 */
