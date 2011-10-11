import re
from cast.Lexer import PatternMatchingLexer
from cast.Token import cToken
from cast.cParser import Parser as cParser

def parseTypedef( match, terminalId, lexer ):
  queue = []
  ident = None
  token = cToken(cParser.TERMINAL_TYPEDEF, lexer.resource, 'TYPEDEF', match, lexer.lineno, lexer.colno - len(match))
  queue.append(token)
  for token in lexer:
    queue.append(token)
    if token.id == cParser.TERMINAL_IDENTIFIER:
      ident = token
    if token.id == cParser.TERMINAL_SEMI:
      break
  if ident:
    ident.id = cParser.TERMINAL_TYPEDEF_IDENTIFIER
    ident.terminal_str = 'TYPEDEF_IDENTIFIER'
  return (queue, 0)

def parseLbrace( string, lineno, colno, terminalId, lexer ):
  lexer.braceLevel += 1
  token( string, lineno, colno, terminalId, lexer )

def parseDeclarationSpecifier( string, lineno, colno, terminalId, lexer ):
  queue = []
  for token in lexer:
    queue.append(token)
    if token.id == cParser.TERMINAL_IDENTIFIER and lexer.braceLevel == 0:
      ident = True
      continue
    elif token.id == cParser.TERMINAL_SEMI and ident:
      hintId = cParser.TERMINAL_DECLARATION_HINT
      break
    elif token.id == cParser.TERMINAL_SEMI and lexer.braceLevel == 0:
      hintId = cParser.TERMINAL_FUNCTION_DEFINITION_HINT
      break
    ident = False
  hint = cToken(hintId, lexer.resource, cParser.terminal_str[hintId], match, lexer.lineno, lexer.colno - len(match))
  lexer.addToken(hint)
  for token in queue:
    lexer.addToken(token)

def parseRbrace( string, lineno, colno, terminalId, lexer ):
  lexer.braceLevel -= 1
  token( string, lineno, colno, terminalId, lexer )

def token(string, lineno, colno, terminalId, lexer):
  lexer.addToken(cToken(terminalId, lexer.resource, cParser.terminal_str[terminalId], string, lineno, colno))

class cLexer(PatternMatchingLexer):
  type_specifier = ['void', 'char', 'short', 'int', 'long', 'float', 'double', 'signed', 'unsigned', '_Bool', '_Complex']
  cRegex = [
      # Comments
      ( re.compile(r'/\*.*?\*/', re.S), None, None ),
      ( re.compile(r'//.*', 0), None, None ),

      # Keywords
      ( re.compile(r'auto(?=\s)'), cParser.TERMINAL_AUTO, token ),
      ( re.compile(r'_Bool(?=[\s\),])'), cParser.TERMINAL_BOOL, token ),
      ( re.compile(r'break(?=\s)'), cParser.TERMINAL_BREAK, token ),
      ( re.compile(r'case(?=\s)'), cParser.TERMINAL_CASE, token ),
      ( re.compile(r'char(?=[\s\),])'), cParser.TERMINAL_CHAR, token ),
      ( re.compile(r'_Complex(?=[\s\),])'), cParser.TERMINAL_COMPLEX, token ),
      ( re.compile(r'const(?=[\s\),])'), cParser.TERMINAL_CONST, token ),
      ( re.compile(r'continue(?=\s)'), cParser.TERMINAL_CONTINUE, token ),
      ( re.compile(r'default(?=\s)'), cParser.TERMINAL_DEFAULT, token ),
      ( re.compile(r'do(?=\s)'), cParser.TERMINAL_DO, token ),
      ( re.compile(r'double(?=[\s\),])'), cParser.TERMINAL_DOUBLE, token ),
      ( re.compile(r'else(?=\s)'), cParser.TERMINAL_ELSE, token ),
      ( re.compile(r'enum(?=\s)'), cParser.TERMINAL_ENUM, token ),
      ( re.compile(r'extern(?=[\s\),])'), cParser.TERMINAL_EXTERN, token ),
      ( re.compile(r'float(?=[\s\),])'), cParser.TERMINAL_FLOAT, token ),
      ( re.compile(r'for(?=\s)'), cParser.TERMINAL_FOR, token ),
      ( re.compile(r'goto(?=\s)'), cParser.TERMINAL_GOTO, token ),
      ( re.compile(r'if(?=\s)'), cParser.TERMINAL_IF, token ),
      ( re.compile(r'_Imaginary(?=\s)'), cParser.TERMINAL_IMAGINARY, token ),
      ( re.compile(r'inline(?=\s)'), cParser.TERMINAL_INLINE, token ),
      ( re.compile(r'int(?=[\s\),])'), cParser.TERMINAL_INT, token ),
      ( re.compile(r'long(?=[\s\),])'), cParser.TERMINAL_LONG, token ),
      ( re.compile(r'register(?=[\s\),])'), cParser.TERMINAL_REGISTER, token ),
      ( re.compile(r'restrict(?=[\s\),])'), cParser.TERMINAL_RESTRICT, token ),
      ( re.compile(r'return(?=\s)'), cParser.TERMINAL_RETURN, token ),
      ( re.compile(r'short(?=[\s\),])'), cParser.TERMINAL_SHORT, token ),
      ( re.compile(r'signed(?=[\s\),])'), cParser.TERMINAL_SIGNED, token ),
      ( re.compile(r'sizeof(?=\s)'), cParser.TERMINAL_SIZEOF, token ),
      ( re.compile(r'static(?=\s)'), cParser.TERMINAL_STATIC, token ),
      ( re.compile(r'struct(?=\s)'), cParser.TERMINAL_STRUCT, token ),
      ( re.compile(r'switch(?=\s)'), cParser.TERMINAL_SWITCH, token ),
      ( re.compile(r'typedef(?=\s)'), cParser.TERMINAL_TYPEDEF, parseTypedef ),
      ( re.compile(r'union(?=\s)'), cParser.TERMINAL_UNION, token ),
      ( re.compile(r'unsigned(?=\s)'), cParser.TERMINAL_UNSIGNED, token ),
      ( re.compile(r'void(?=[\s\),])'), cParser.TERMINAL_VOID, token ),
      ( re.compile(r'volatile(?=\s)'), cParser.TERMINAL_VOLATILE, token ),
      ( re.compile(r'while(?=\s)'), cParser.TERMINAL_WHILE, token ),

      # Identifiers
      ( re.compile(r'([a-zA-Z_]|\\[uU]([0-9a-fA-F]{4})([0-9a-fA-F]{4})?)([a-zA-Z_0-9]|\\[uU]([0-9a-fA-F]{4})([0-9a-fA-F]{4})?)*'), cParser.TERMINAL_IDENTIFIER, token ),

      # Unicode Characters
      ( re.compile(r'\\[uU]([0-9a-fA-F]{4})([0-9a-fA-F]{4})?'), cParser.TERMINAL_UNIVERSAL_CHARACTER_NAME, token ),

      # Digraphs
      ( re.compile(r'<%'), cParser.TERMINAL_LBRACE, token ),
      ( re.compile(r'%>'), cParser.TERMINAL_RBRACE, token ),
      ( re.compile(r'<:'), cParser.TERMINAL_LSQUARE, token ),
      ( re.compile(r':>'), cParser.TERMINAL_RSQUARE, token ),
      ( re.compile(r'%:%:'), cParser.TERMINAL_POUNDPOUND, token ),
      ( re.compile(r'%:'), cParser.TERMINAL_POUND, token ),

      # Punctuators
      ( re.compile(r'\['), cParser.TERMINAL_LSQUARE, token ),
      ( re.compile(r'\]'), cParser.TERMINAL_RSQUARE, token ),
      ( re.compile(r'\((?=' + '(' +'|'.join(type_specifier) + ')\s*\))'), cParser.TERMINAL_LPAREN_CAST, token ),
      ( re.compile(r'\('), cParser.TERMINAL_LPAREN, token ),
      ( re.compile(r'\)'), cParser.TERMINAL_RPAREN, token ),
      ( re.compile(r'\{'), cParser.TERMINAL_LBRACE, parseLbrace ),
      ( re.compile(r'\}'), cParser.TERMINAL_RBRACE, token ),
      ( re.compile(r'\.'), cParser.TERMINAL_DOT, token ),
      ( re.compile(r'->'), cParser.TERMINAL_ARROW, token ),
      ( re.compile(r'\+\+'), cParser.TERMINAL_INCR, token ),
      ( re.compile(r'--'), cParser.TERMINAL_DECR, token ),
      ( re.compile(r'&(?!&)'), cParser.TERMINAL_BITAND, token ),
      ( re.compile(r'\*(?!=)'), cParser.TERMINAL_MUL, token ),
      ( re.compile(r'\+(?!=)'), cParser.TERMINAL_ADD, token ),
      ( re.compile(r'-(?!=)'), cParser.TERMINAL_SUB, token ),
      ( re.compile(r'~'), cParser.TERMINAL_TILDE, token ),
      ( re.compile(r'!(?!=)'), cParser.TERMINAL_EXCLAMATION_POINT, token ),
      ( re.compile(r'/(?!=)'), cParser.TERMINAL_DIV, token ),
      ( re.compile(r'%(?!=)'), cParser.TERMINAL_MOD, token ),
      ( re.compile(r'<<(?!=)'), cParser.TERMINAL_LSHIFT, token ),
      ( re.compile(r'>>(?!=)'), cParser.TERMINAL_RSHIFT, token ),
      ( re.compile(r'<(?!=)'), cParser.TERMINAL_LT, token ),
      ( re.compile(r'>(?!=)'), cParser.TERMINAL_GT, token ),
      ( re.compile(r'<='), cParser.TERMINAL_LTEQ, token ),
      ( re.compile(r'>='), cParser.TERMINAL_GTEQ, token ),
      ( re.compile(r'=='), cParser.TERMINAL_EQ, token ),
      ( re.compile(r'!='), cParser.TERMINAL_NEQ, token ),
      ( re.compile(r'\^(?!=)'), cParser.TERMINAL_BITXOR, token ),
      ( re.compile(r'\|(?!\|)'), cParser.TERMINAL_BITOR, token ),
      ( re.compile(r'&&'), cParser.TERMINAL_AND, token ),
      ( re.compile(r'\|\|'), cParser.TERMINAL_OR, token ),
      ( re.compile(r'\?'), cParser.TERMINAL_QUESTIONMARK, token ),
      ( re.compile(r':'), cParser.TERMINAL_COLON, token ),
      ( re.compile(r';'), cParser.TERMINAL_SEMI, token ),
      ( re.compile(r'\.\.\.'), cParser.TERMINAL_ELIPSIS, token ),
      ( re.compile(r'=(?!=)'), cParser.TERMINAL_ASSIGN, token ),
      ( re.compile(r'\*='), cParser.TERMINAL_MULEQ, token ),
      ( re.compile(r'/='), cParser.TERMINAL_DIVEQ, token ),
      ( re.compile(r'%='), cParser.TERMINAL_MODEQ, token ),
      ( re.compile(r'\+='), cParser.TERMINAL_ADDEQ, token ),
      ( re.compile(r'-='), cParser.TERMINAL_SUBEQ, token ),
      ( re.compile(r'<<='), cParser.TERMINAL_LSHIFTEQ, token ),
      ( re.compile(r'>>='), cParser.TERMINAL_RSHIFTEQ, token ),
      ( re.compile(r'&='), cParser.TERMINAL_BITANDEQ, token ),
      ( re.compile(r'\^='), cParser.TERMINAL_BITXOREQ, token ),
      ( re.compile(r'\|='), cParser.TERMINAL_BITOREQ, token ),
      ( re.compile(r','), cParser.TERMINAL_COMMA, token ),
      ( re.compile(r'##'), cParser.TERMINAL_POUNDPOUND, token ),
      ( re.compile(r'#(?!#)'), cParser.TERMINAL_POUND, token ),

      # Constants, Literals
      ( re.compile(r'(([0-9]+)?\.([0-9]+)|[0-9]+\.)([eE][-+]?[0-9]+)?[flFL]?'), cParser.TERMINAL_DECIMAL_FLOATING_CONSTANT, token ),
      ( re.compile(r'[L]?"([^\\\"\n]|\\[\\"\'nrbtfav\?]|\\[0-7]{1,3}|\\x[0-9a-fA-F]+|\\[uU]([0-9a-fA-F]{4})([0-9a-fA-F]{4})?)*"'), cParser.TERMINAL_STRING_LITERAL, token ),
      ( re.compile(r'([1-9][0-9]*|0[xX][0-9a-fA-F]+|0[0-7]*)([uU](ll|LL)|[uU][lL]?|(ll|LL)[uU]?|[lL][uU])?'), cParser.TERMINAL_INTEGER_CONSTANT, token ),
      ( re.compile(r'0[xX](([0-9a-fA-F]+)?\.([0-9a-fA-F]+)|[0-9a-fA-F]+\.)[pP][-+]?[0-9]+[flFL]?'), cParser.TERMINAL_HEXADECIMAL_FLOATING_CONSTANT, token ),
      ( re.compile(r"[L]?'([^\\'\n]|\\[\\\"\'nrbtfav\?]|\\[0-7]{1,3}|\\x[0-9a-fA-F]+|\\[uU]([0-9a-fA-F]{4})([0-9a-fA-F]{4})?)+'"), cParser.TERMINAL_CHARACTER_CONSTANT, token ),

      # Whitespace
      ( re.compile(r'\s+', 0), None, None )
  ]

  def __init__(self, sourceCode):
    super().__init__(sourceCode, self.cRegex)
    self.braceLevel = 0
  
  def __next__(self):
    token = super().__next__()
    return cToken(token.id, self.resource, token.terminal_str, token.source_string, token.lineno, token.colno)
