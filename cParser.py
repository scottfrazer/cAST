import sys
def parse( iterator, entry ):
  p = Parser()
  return p.parse(iterator, entry)
class DebugTracer:
  def __init__(self, func, symbol, rule, callDepth ):
    self.__dict__.update(locals())
    self.children = []
  def add(self, child):
    self.children.append(child)
  def __str__(self):
    s = '%s[%s, symbol: %s, rule: %s]\n' % (' '.join(['' for i in range(self.callDepth)]), self.func, self.symbol, str(self.rule))
    for child in self.children:
      s += str(child)
    return s
class Terminal:
  def __init__(self, id):
    self.id=id
    self.str=Parser.terminal_str[id]
  def getId(self):
    return self.id
  def toAst(self):
    return self
  def __str__(self):
    return self.str
class NonTerminal():
  def __init__(self, id, string):
    self.id = id
    self.string = string
    self.list = False
  def __str__(self):
    return self.string
class AstTransform:
  pass
class AstTransformSubstitution(AstTransform):
  def __init__( self, idx ):
    self.idx = idx
  def __repr__( self ):
    return '$' + str(self.idx)
class AstTransformNodeCreator(AstTransform):
  def __init__( self, name, parameters ):
    self.name = name
    self.parameters = parameters
  def __repr__( self ):
    return self.name + '( ' + ', '.join(['%s=$%s' % (k,str(v)) for k,v in self.parameters.items()]) + ' )' 
class AstList(list):
  def toAst(self):
    retval = []
    for ast in self:
      retval.append(ast.toAst())
    return retval
class ParseTree():
  def __init__(self, nonterminal, tracer = None):
    self.__dict__.update(locals())
    self.children = []
    self.astTransform = None
    self.isExpr = False
    self.list = False
  def add( self, tree ):
    self.children.append( tree )
  def toAst( self ):
    if self.list == 'slist' or self.list == 'nlist':
      if len(self.children) == 0:
        return AstList()
      offset = 1 if not isinstance(self.children[0], ParseTree) else 0
      r = AstList([self.children[offset].toAst()])
      r.extend(self.children[offset+1].toAst())
      return r
    elif self.list == 'tlist':
      if len(self.children) == 0:
        return []
      r = AstList([self.children[0].toAst()])
      r.extend(self.children[2].toAst())
      return r
    elif self.isExpr:
      if isinstance(self.astTransform, AstTransformSubstitution):
        return self.children[self.astTransform.idx].toAst()
      elif isinstance(self.astTransform, AstTransformNodeCreator):
        parameters = {}
        for name, idx in self.astTransform.parameters.items():
          if isinstance(self.children[idx], ParseTree):
            parameters[name] = self.children[idx].toAst()
          elif isinstance(self.children[idx], list):
            parameters[name] = [x.toAst() for x in self.children[idx]]
          else:
            parameters[name] = self.children[idx]
        return Ast(self.astTransform.name, parameters)
    else:
      if isinstance(self.astTransform, AstTransformSubstitution):
        return self.children[self.astTransform.idx].toAst()
      elif isinstance(self.astTransform, AstTransformNodeCreator):
        parameters = {name: self.children[idx].toAst() for name, idx in self.astTransform.parameters.items()}
        return Ast(self.astTransform.name, parameters)
      elif len(self.children):
        return self.children[0].toAst()
      else:
        return None
  def __str__( self ):
    children = []
    for child in self.children:
      if isinstance(child, list):
        children.append('[' + ', '.join([str(a) for a in child]) + ']')
      else:
        children.append(str(child))
    return '(' + str(self.nonterminal) + ': ' + ', '.join(children) + ')'
class Ast():
  def __init__(self, name, attributes):
    self.name = name
    self.attributes = attributes
  def getAttr(self, attr):
    return self.attributes[attr]
  def __str__(self):
    return '(%s: %s)' % (self.name, ', '.join('%s=%s'%(str(k), '[' + ', '.join([str(x) for x in v]) + ']' if isinstance(v, list) else str(v) ) for k,v in self.attributes.items()))
class SyntaxError(Exception):
  def __init__(self, message, tracer = None):
    self.__dict__.update(locals())
  def __str__(self):
    return self.message
class TokenRecorder:
  def __init__(self):
    self.stack = []
    self.awake = False
  def wake(self):
    self.awake = True
    self.stack = []
    return self
  def sleep(self):
    self.awake = False
    return self
  def record(self, s):
    self.stack.append(s)
    return self
  def tokens(self):
    return self.stack
class Parser:
  def __init__(self):
    self.iterator = None
    self.sym = None
    self.recorder = TokenRecorder()
    self.entry_points = {
      'terminals': self._TERMINALS,
    }
  TERMINAL_BITNOT = 0
  TERMINAL_COLON = 1
  TERMINAL_RSHIFTEQ = 2
  TERMINAL_INTEGER_CONSTANT = 3
  TERMINAL_DOUBLE = 4
  TERMINAL__BOOL = 5
  TERMINAL__COMPLEX = 6
  TERMINAL_IMAGINARY = 7
  TERMINAL_LSHIFT = 8
  TERMINAL_BITOR = 9
  TERMINAL_REGISTER = 10
  TERMINAL__IMAGINARY = 11
  TERMINAL_TILDE = 12
  TERMINAL_LT = 13
  TERMINAL_BITXOR = 14
  TERMINAL_MODEQ = 15
  TERMINAL_BITAND = 16
  TERMINAL_STRUCT = 17
  TERMINAL_BITXOREQ = 18
  TERMINAL_AUTO = 19
  TERMINAL_GTEQ = 20
  TERMINAL_ASSIGN = 21
  TERMINAL_LBRACE = 22
  TERMINAL_WHILE = 23
  TERMINAL_NOT = 24
  TERMINAL_AND = 25
  TERMINAL_LTEQ = 26
  TERMINAL_HEADER_NAME = 27
  TERMINAL_RPAREN = 28
  TERMINAL_TYPEDEF = 29
  TERMINAL_AMPERSAND = 30
  TERMINAL_RBRACE = 31
  TERMINAL_MUL = 32
  TERMINAL_ENUM = 33
  TERMINAL_SUBEQ = 34
  TERMINAL_SIGNED = 35
  TERMINAL_RSHIFT = 36
  TERMINAL_RESTRICT = 37
  TERMINAL_POUNDPOUND = 38
  TERMINAL_NEQ = 39
  TERMINAL_INLINE = 40
  TERMINAL_RETURN = 41
  TERMINAL_ARROW = 42
  TERMINAL_STRING_LITERAL = 43
  TERMINAL_BREAK = 44
  TERMINAL_UNIVERSAL_CHARACTER_NAME = 45
  TERMINAL_BOOL = 46
  TERMINAL_LSQUARE = 47
  TERMINAL_SUB = 48
  TERMINAL_CASE = 49
  TERMINAL_FOR = 50
  TERMINAL_DECR = 51
  TERMINAL_CHAR = 52
  TERMINAL_ELSE = 53
  TERMINAL_SEMI = 54
  TERMINAL_VOID = 55
  TERMINAL_STATIC = 56
  TERMINAL_BITANDEQ = 57
  TERMINAL_COMPLEX = 58
  TERMINAL_GT = 59
  TERMINAL_CONTINUE = 60
  TERMINAL_IDENTIFIER = 61
  TERMINAL_SIZEOF = 62
  TERMINAL_NUMBER = 63
  TERMINAL_ADDEQ = 64
  TERMINAL_EXCLAMATION_POINT = 65
  TERMINAL_DEFAULT = 66
  TERMINAL_UNION = 67
  TERMINAL_DECIMAL_FLOATING_CONSTANT = 68
  TERMINAL_DIV = 69
  TERMINAL_EXTERN = 70
  TERMINAL_DO = 71
  TERMINAL_QUESTIONMARK = 72
  TERMINAL_MOD = 73
  TERMINAL_POUND = 74
  TERMINAL_FLOAT = 75
  TERMINAL_RSQUARE = 76
  TERMINAL_HEXADECIMAL_FLOATING_CONSTANT = 77
  TERMINAL_BITOREQ = 78
  TERMINAL_INT = 79
  TERMINAL_GOTO = 80
  TERMINAL_CHARACTER_CONSTANT = 81
  TERMINAL_MULEQ = 82
  TERMINAL_UNSIGNED = 83
  TERMINAL_DOT = 84
  TERMINAL_SHORT = 85
  TERMINAL_OR = 86
  TERMINAL_DIVEQ = 87
  TERMINAL_LSHIFTEQ = 88
  TERMINAL_LPAREN = 89
  TERMINAL_CONST = 90
  TERMINAL_SWITCH = 91
  TERMINAL_EQ = 92
  TERMINAL_ELIPSIS = 93
  TERMINAL_COMMA = 94
  TERMINAL_ADD = 95
  TERMINAL_VOLATILE = 96
  TERMINAL_IF = 97
  TERMINAL_INCR = 98
  TERMINAL_LONG = 99
  terminal_str = {
    0: 'bitnot',
    1: 'colon',
    2: 'rshifteq',
    3: 'integer_constant',
    4: 'double',
    5: '_bool',
    6: '_complex',
    7: 'imaginary',
    8: 'lshift',
    9: 'bitor',
    10: 'register',
    11: '_imaginary',
    12: 'tilde',
    13: 'lt',
    14: 'bitxor',
    15: 'modeq',
    16: 'bitand',
    17: 'struct',
    18: 'bitxoreq',
    19: 'auto',
    20: 'gteq',
    21: 'assign',
    22: 'lbrace',
    23: 'while',
    24: 'not',
    25: 'and',
    26: 'lteq',
    27: 'header_name',
    28: 'rparen',
    29: 'typedef',
    30: 'ampersand',
    31: 'rbrace',
    32: 'mul',
    33: 'enum',
    34: 'subeq',
    35: 'signed',
    36: 'rshift',
    37: 'restrict',
    38: 'poundpound',
    39: 'neq',
    40: 'inline',
    41: 'return',
    42: 'arrow',
    43: 'string_literal',
    44: 'break',
    45: 'universal_character_name',
    46: 'bool',
    47: 'lsquare',
    48: 'sub',
    49: 'case',
    50: 'for',
    51: 'decr',
    52: 'char',
    53: 'else',
    54: 'semi',
    55: 'void',
    56: 'static',
    57: 'bitandeq',
    58: 'complex',
    59: 'gt',
    60: 'continue',
    61: 'identifier',
    62: 'sizeof',
    63: 'number',
    64: 'addeq',
    65: 'exclamation_point',
    66: 'default',
    67: 'union',
    68: 'decimal_floating_constant',
    69: 'div',
    70: 'extern',
    71: 'do',
    72: 'questionmark',
    73: 'mod',
    74: 'pound',
    75: 'float',
    76: 'rsquare',
    77: 'hexadecimal_floating_constant',
    78: 'bitoreq',
    79: 'int',
    80: 'goto',
    81: 'character_constant',
    82: 'muleq',
    83: 'unsigned',
    84: 'dot',
    85: 'short',
    86: 'or',
    87: 'diveq',
    88: 'lshifteq',
    89: 'lparen',
    90: 'const',
    91: 'switch',
    92: 'eq',
    93: 'elipsis',
    94: 'comma',
    95: 'add',
    96: 'volatile',
    97: 'if',
    98: 'incr',
    99: 'long',
  }
  nonterminal_str = {
    100: '_expr',
    101: '_gen1',
    102: 'type_qualifier',
    103: '_gen0',
    104: '_gen2',
    105: 'token',
    106: 'punctuator',
    107: 'terminals',
    108: 'constant',
    109: 'keyword',
    110: '_direct_declarator',
  }
  str_terminal = {
    'bitnot': 0,
    'colon': 1,
    'rshifteq': 2,
    'integer_constant': 3,
    'double': 4,
    '_bool': 5,
    '_complex': 6,
    'imaginary': 7,
    'lshift': 8,
    'bitor': 9,
    'register': 10,
    '_imaginary': 11,
    'tilde': 12,
    'lt': 13,
    'bitxor': 14,
    'modeq': 15,
    'bitand': 16,
    'struct': 17,
    'bitxoreq': 18,
    'auto': 19,
    'gteq': 20,
    'assign': 21,
    'lbrace': 22,
    'while': 23,
    'not': 24,
    'and': 25,
    'lteq': 26,
    'header_name': 27,
    'rparen': 28,
    'typedef': 29,
    'ampersand': 30,
    'rbrace': 31,
    'mul': 32,
    'enum': 33,
    'subeq': 34,
    'signed': 35,
    'rshift': 36,
    'restrict': 37,
    'poundpound': 38,
    'neq': 39,
    'inline': 40,
    'return': 41,
    'arrow': 42,
    'string_literal': 43,
    'break': 44,
    'universal_character_name': 45,
    'bool': 46,
    'lsquare': 47,
    'sub': 48,
    'case': 49,
    'for': 50,
    'decr': 51,
    'char': 52,
    'else': 53,
    'semi': 54,
    'void': 55,
    'static': 56,
    'bitandeq': 57,
    'complex': 58,
    'gt': 59,
    'continue': 60,
    'identifier': 61,
    'sizeof': 62,
    'number': 63,
    'addeq': 64,
    'exclamation_point': 65,
    'default': 66,
    'union': 67,
    'decimal_floating_constant': 68,
    'div': 69,
    'extern': 70,
    'do': 71,
    'questionmark': 72,
    'mod': 73,
    'pound': 74,
    'float': 75,
    'rsquare': 76,
    'hexadecimal_floating_constant': 77,
    'bitoreq': 78,
    'int': 79,
    'goto': 80,
    'character_constant': 81,
    'muleq': 82,
    'unsigned': 83,
    'dot': 84,
    'short': 85,
    'or': 86,
    'diveq': 87,
    'lshifteq': 88,
    'lparen': 89,
    'const': 90,
    'switch': 91,
    'eq': 92,
    'elipsis': 93,
    'comma': 94,
    'add': 95,
    'volatile': 96,
    'if': 97,
    'incr': 98,
    'long': 99,
  }
  str_nonterminal = {
    '_expr': 100,
    '_gen1': 101,
    'type_qualifier': 102,
    '_gen0': 103,
    '_gen2': 104,
    'token': 105,
    'punctuator': 106,
    'terminals': 107,
    'constant': 108,
    'keyword': 109,
    '_direct_declarator': 110,
  }
  terminal_count = 100
  nonterminal_count = 11
  parse_table = [
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, 164, 164, -1, 100, 100, 100, -1, 164, 164, 100, 100, 164, 164, 164, 164, -1, 100, 164, 100, 164, 164, 164, 100, -1, 164, 164, -1, 164, 100, 164, 164, 164, 100, 164, 100, 164, 100, 164, 164, 100, 100, 164, 133, 100, -1, -1, 164, 164, 100, 100, 164, 100, 100, 164, 100, 100, 164, -1, 164, 100, 25, 100, -1, 164, 164, 100, 100, -1, 164, 100, 100, 164, 164, 164, 100, 164, -1, 164, 100, 100, -1, 164, 100, 164, 100, 164, -1, 164, 164, 100, 100, 164, 164, 164, 164, 100, 100, 164, 100],
  [-1, 30, 31, -1, -1, -1, -1, -1, 71, 147, -1, -1, 34, 41, 7, 85, -1, -1, 175, -1, 66, 58, 12, -1, -1, 51, 171, -1, 105, -1, 135, 60, 169, -1, 28, -1, 10, -1, 87, 187, -1, -1, 99, -1, -1, -1, -1, 48, 46, -1, -1, 86, -1, -1, 144, -1, -1, 163, -1, 136, -1, -1, -1, -1, 120, 22, -1, -1, -1, 140, -1, -1, 98, 116, 24, -1, 69, -1, 179, -1, -1, -1, 54, -1, 154, -1, 142, -1, 76, 84, -1, -1, 2, 132, 189, 160, -1, -1, 104, -1],
  [-1, 95, 101, 131, 127, -1, -1, 53, 62, 173, 102, -1, 37, 146, 23, 145, 21, 172, 114, 81, 155, 78, 83, 141, 149, 79, 68, 178, 121, 138, -1, 156, 16, 151, 64, 93, 75, 129, 29, 45, 73, 56, 63, 112, 61, 14, 94, 26, 106, 123, 152, 153, 126, 103, 6, 122, 55, 109, 134, 117, 161, 77, 5, 82, 188, 159, 167, 181, 165, 91, 8, 158, 108, 15, 110, 90, 43, 174, 13, 125, 70, 44, 137, 113, 35, 19, 92, 148, 183, 9, 52, 80, 33, 89, 177, 139, 176, 42, 65, 96],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, 20, 49, 67, -1, -1, -1, 1, 47, -1, -1, -1, -1, -1, 118, -1, 4, -1, -1, -1, 32, -1, -1, -1, -1, -1, 59, -1, -1, -1, 72, -1, 168, -1, 124, -1, -1, 3, 111, -1, -1, 130, -1, -1, -1, -1, 0, 36, -1, 119, 38, -1, 11, 88, -1, -1, -1, 143, -1, 184, -1, -1, -1, 185, 162, -1, -1, 74, 180, -1, -1, -1, 170, -1, -1, -1, 50, 97, -1, -1, 17, -1, 107, -1, -1, -1, -1, 57, 115, -1, -1, -1, -1, 39, 18, -1, 27],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1]
  ]
  def terminal(self, str):
    return self.str_terminal[str]
  def terminalNames(self):
    return list(self.str_terminal.keys())
  def isTerminal(self, id):
    return 0 <= id <= 99
  def isNonTerminal(self, id):
    return 100 <= id <= 110
  def rewind(self, recorder):
    global tokens
    tokens = recorder.tokens().append(tokens)
  def binding_power(self, sym, bp):
    try:
      return bp[sym.getId()]
    except KeyError:
      return 0
    except AttributeError:
      return 0
  def getAtomString(self, id):
    if self.isTerminal(id):
      return self.terminal_str[id]
    elif self.isNonTerminal(id):
      return self.nonterminal_str[id]
    return ''
  def getsym(self):
    try:
      return next( self.iterator )
    except StopIteration:
      return None
  def parse(self, iterator, entry):
    self.iterator = iter(iterator)
    self.sym = self.getsym()
    tree = self.entry_points[entry]()
    if self.sym != None:
      raise SyntaxError('Syntax Error: Finished parsing without consuming all tokens.', tree.tracer)
    self.iterator = None
    self.sym = None
    return tree
  def next(self):
    self.sym = self.getsym()
    if self.sym is not None and not self.isTerminal(self.sym.getId()):
      self.sym = None
      raise SyntaxError('Invalid symbol ID: %d (%s)'%(self.sym.getId(), self.sym), None)
    if self.recorder.awake and self.sym is not None:
      self.recorder.record(self.sym)
    return self.sym
  def expect(self, s, tracer):
    if self.sym and s == self.sym.getId():
      symbol = self.sym
      self.sym = self.next()
      return symbol
    else:
      raise SyntaxError('Unexpected symbol.  Expected %s, got %s.' %(self.terminal_str[s], self.sym if self.sym else 'None'), tracer)
  def rule(self, n):
    if self.sym == None: return -1
    return self.parse_table[n - 100][self.sym.getId()]
  def call(self, nt_str):
    return getattr(self, nt_str)()
  def __GEN1(self, depth = 0):
    rule = self.rule(101)
    if depth is not False:
      tracer = DebugTracer("__GEN1", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(101, self.getAtomString(101)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _TYPE_QUALIFIER(self, depth = 0):
    rule = self.rule(102)
    if depth is not False:
      tracer = DebugTracer("_TYPE_QUALIFIER", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(102, self.getAtomString(102)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def __GEN0(self, depth = 0):
    rule = self.rule(103)
    if depth is not False:
      tracer = DebugTracer("__GEN0", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(103, self.getAtomString(103)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def __GEN2(self, depth = 0):
    rule = self.rule(104)
    if depth is not False:
      tracer = DebugTracer("__GEN2", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(104, self.getAtomString(104)), tracer )
    tree.list = 'nlist'
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _TOKEN(self, depth = 0):
    rule = self.rule(105)
    if depth is not False:
      tracer = DebugTracer("_TOKEN", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(105, self.getAtomString(105)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 25:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_IDENTIFIER, tracer) )
      return tree
    elif rule == 40:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._CONSTANT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 100:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._KEYWORD(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 133:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_STRING_LITERAL, tracer) )
      return tree
    elif rule == 164:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PUNCTUATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _PUNCTUATOR(self, depth = 0):
    rule = self.rule(106)
    if depth is not False:
      tracer = DebugTracer("_PUNCTUATOR", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(106, self.getAtomString(106)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 2:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_EQ, tracer) )
      return tree
    elif rule == 7:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_BITXOR, tracer) )
      return tree
    elif rule == 10:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_RSHIFT, tracer) )
      return tree
    elif rule == 12:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LBRACE, tracer) )
      return tree
    elif rule == 22:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_EXCLAMATION_POINT, tracer) )
      return tree
    elif rule == 24:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_POUND, tracer) )
      return tree
    elif rule == 28:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_SUBEQ, tracer) )
      return tree
    elif rule == 30:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_COLON, tracer) )
      return tree
    elif rule == 31:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_RSHIFTEQ, tracer) )
      return tree
    elif rule == 34:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_TILDE, tracer) )
      return tree
    elif rule == 41:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LT, tracer) )
      return tree
    elif rule == 46:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_SUB, tracer) )
      return tree
    elif rule == 48:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LSQUARE, tracer) )
      return tree
    elif rule == 51:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_AND, tracer) )
      return tree
    elif rule == 54:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_MULEQ, tracer) )
      return tree
    elif rule == 58:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_ASSIGN, tracer) )
      return tree
    elif rule == 60:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_RBRACE, tracer) )
      return tree
    elif rule == 66:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_GTEQ, tracer) )
      return tree
    elif rule == 69:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_RSQUARE, tracer) )
      return tree
    elif rule == 71:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LSHIFT, tracer) )
      return tree
    elif rule == 76:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LSHIFTEQ, tracer) )
      return tree
    elif rule == 84:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LPAREN, tracer) )
      return tree
    elif rule == 85:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_MODEQ, tracer) )
      return tree
    elif rule == 86:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_DECR, tracer) )
      return tree
    elif rule == 87:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_POUNDPOUND, tracer) )
      return tree
    elif rule == 98:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_QUESTIONMARK, tracer) )
      return tree
    elif rule == 99:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_ARROW, tracer) )
      return tree
    elif rule == 104:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_INCR, tracer) )
      return tree
    elif rule == 105:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_RPAREN, tracer) )
      return tree
    elif rule == 116:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_MOD, tracer) )
      return tree
    elif rule == 120:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_ADDEQ, tracer) )
      return tree
    elif rule == 132:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_ELIPSIS, tracer) )
      return tree
    elif rule == 135:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_AMPERSAND, tracer) )
      return tree
    elif rule == 136:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_GT, tracer) )
      return tree
    elif rule == 140:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_DIV, tracer) )
      return tree
    elif rule == 142:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_OR, tracer) )
      return tree
    elif rule == 144:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_SEMI, tracer) )
      return tree
    elif rule == 147:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_BITOR, tracer) )
      return tree
    elif rule == 154:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_DOT, tracer) )
      return tree
    elif rule == 160:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_ADD, tracer) )
      return tree
    elif rule == 163:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_BITANDEQ, tracer) )
      return tree
    elif rule == 169:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_MUL, tracer) )
      return tree
    elif rule == 171:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LTEQ, tracer) )
      return tree
    elif rule == 175:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_BITXOREQ, tracer) )
      return tree
    elif rule == 179:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_BITOREQ, tracer) )
      return tree
    elif rule == 187:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_NEQ, tracer) )
      return tree
    elif rule == 189:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_COMMA, tracer) )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _TERMINALS(self, depth = 0):
    rule = self.rule(107)
    if depth is not False:
      tracer = DebugTracer("_TERMINALS", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(107, self.getAtomString(107)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 5:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_SIZEOF, tracer) )
      return tree
    elif rule == 6:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_SEMI, tracer) )
      return tree
    elif rule == 8:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_EXTERN, tracer) )
      return tree
    elif rule == 9:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LPAREN, tracer) )
      return tree
    elif rule == 13:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_BITOREQ, tracer) )
      return tree
    elif rule == 14:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_UNIVERSAL_CHARACTER_NAME, tracer) )
      return tree
    elif rule == 15:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_MOD, tracer) )
      return tree
    elif rule == 16:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_MUL, tracer) )
      return tree
    elif rule == 19:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_SHORT, tracer) )
      return tree
    elif rule == 21:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_BITAND, tracer) )
      return tree
    elif rule == 23:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_BITXOR, tracer) )
      return tree
    elif rule == 26:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LSQUARE, tracer) )
      return tree
    elif rule == 29:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_POUNDPOUND, tracer) )
      return tree
    elif rule == 33:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_EQ, tracer) )
      return tree
    elif rule == 35:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_DOT, tracer) )
      return tree
    elif rule == 37:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_TILDE, tracer) )
      return tree
    elif rule == 42:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_IF, tracer) )
      return tree
    elif rule == 43:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_RSQUARE, tracer) )
      return tree
    elif rule == 44:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_CHARACTER_CONSTANT, tracer) )
      return tree
    elif rule == 45:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_NEQ, tracer) )
      return tree
    elif rule == 52:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_CONST, tracer) )
      return tree
    elif rule == 53:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_IMAGINARY, tracer) )
      return tree
    elif rule == 55:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_STATIC, tracer) )
      return tree
    elif rule == 56:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_RETURN, tracer) )
      return tree
    elif rule == 61:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_BREAK, tracer) )
      return tree
    elif rule == 62:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LSHIFT, tracer) )
      return tree
    elif rule == 63:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_ARROW, tracer) )
      return tree
    elif rule == 64:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_SUBEQ, tracer) )
      return tree
    elif rule == 65:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_INCR, tracer) )
      return tree
    elif rule == 68:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LTEQ, tracer) )
      return tree
    elif rule == 70:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_GOTO, tracer) )
      return tree
    elif rule == 73:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_INLINE, tracer) )
      return tree
    elif rule == 75:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_RSHIFT, tracer) )
      return tree
    elif rule == 77:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_IDENTIFIER, tracer) )
      return tree
    elif rule == 78:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_ASSIGN, tracer) )
      return tree
    elif rule == 79:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_AND, tracer) )
      return tree
    elif rule == 80:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_SWITCH, tracer) )
      return tree
    elif rule == 81:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_AUTO, tracer) )
      return tree
    elif rule == 82:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_NUMBER, tracer) )
      return tree
    elif rule == 83:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LBRACE, tracer) )
      return tree
    elif rule == 89:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_ELIPSIS, tracer) )
      return tree
    elif rule == 90:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_FLOAT, tracer) )
      return tree
    elif rule == 91:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_DIV, tracer) )
      return tree
    elif rule == 92:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_OR, tracer) )
      return tree
    elif rule == 93:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_SIGNED, tracer) )
      return tree
    elif rule == 94:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_BOOL, tracer) )
      return tree
    elif rule == 95:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_COLON, tracer) )
      return tree
    elif rule == 96:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LONG, tracer) )
      return tree
    elif rule == 101:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_RSHIFTEQ, tracer) )
      return tree
    elif rule == 102:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_REGISTER, tracer) )
      return tree
    elif rule == 103:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_ELSE, tracer) )
      return tree
    elif rule == 106:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_SUB, tracer) )
      return tree
    elif rule == 108:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_QUESTIONMARK, tracer) )
      return tree
    elif rule == 109:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_BITANDEQ, tracer) )
      return tree
    elif rule == 110:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_POUND, tracer) )
      return tree
    elif rule == 112:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_STRING_LITERAL, tracer) )
      return tree
    elif rule == 113:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_UNSIGNED, tracer) )
      return tree
    elif rule == 114:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_BITXOREQ, tracer) )
      return tree
    elif rule == 117:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_GT, tracer) )
      return tree
    elif rule == 121:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_RPAREN, tracer) )
      return tree
    elif rule == 122:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_VOID, tracer) )
      return tree
    elif rule == 123:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_CASE, tracer) )
      return tree
    elif rule == 125:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_INT, tracer) )
      return tree
    elif rule == 126:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_CHAR, tracer) )
      return tree
    elif rule == 127:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_DOUBLE, tracer) )
      return tree
    elif rule == 128:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_POUNDPOUND, tracer) )
      return tree
    elif rule == 129:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_RESTRICT, tracer) )
      return tree
    elif rule == 131:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_INTEGER_CONSTANT, tracer) )
      return tree
    elif rule == 134:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_COMPLEX, tracer) )
      return tree
    elif rule == 137:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_MULEQ, tracer) )
      return tree
    elif rule == 138:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_TYPEDEF, tracer) )
      return tree
    elif rule == 139:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_ADD, tracer) )
      return tree
    elif rule == 141:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_WHILE, tracer) )
      return tree
    elif rule == 145:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_MODEQ, tracer) )
      return tree
    elif rule == 146:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LT, tracer) )
      return tree
    elif rule == 148:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_DIVEQ, tracer) )
      return tree
    elif rule == 149:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_NOT, tracer) )
      return tree
    elif rule == 150:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_POUND, tracer) )
      return tree
    elif rule == 151:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_ENUM, tracer) )
      return tree
    elif rule == 152:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_FOR, tracer) )
      return tree
    elif rule == 153:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_DECR, tracer) )
      return tree
    elif rule == 155:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_GTEQ, tracer) )
      return tree
    elif rule == 156:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_RBRACE, tracer) )
      return tree
    elif rule == 157:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_RBRACE, tracer) )
      return tree
    elif rule == 158:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_DO, tracer) )
      return tree
    elif rule == 159:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_EXCLAMATION_POINT, tracer) )
      return tree
    elif rule == 161:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_CONTINUE, tracer) )
      return tree
    elif rule == 165:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_DECIMAL_FLOATING_CONSTANT, tracer) )
      return tree
    elif rule == 166:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_RSQUARE, tracer) )
      return tree
    elif rule == 167:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_DEFAULT, tracer) )
      return tree
    elif rule == 172:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_STRUCT, tracer) )
      return tree
    elif rule == 173:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_BITOR, tracer) )
      return tree
    elif rule == 174:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_HEXADECIMAL_FLOATING_CONSTANT, tracer) )
      return tree
    elif rule == 176:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_VOLATILE, tracer) )
      return tree
    elif rule == 177:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_COMMA, tracer) )
      return tree
    elif rule == 178:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_HEADER_NAME, tracer) )
      return tree
    elif rule == 181:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_UNION, tracer) )
      return tree
    elif rule == 182:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LBRACE, tracer) )
      return tree
    elif rule == 183:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LSHIFTEQ, tracer) )
      return tree
    elif rule == 186:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LSQUARE, tracer) )
      return tree
    elif rule == 188:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_ADDEQ, tracer) )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _CONSTANT(self, depth = 0):
    rule = self.rule(108)
    if depth is not False:
      tracer = DebugTracer("_CONSTANT", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(108, self.getAtomString(108)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _KEYWORD(self, depth = 0):
    rule = self.rule(109)
    if depth is not False:
      tracer = DebugTracer("_KEYWORD", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(109, self.getAtomString(109)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 0:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_CASE, tracer) )
      return tree
    elif rule == 1:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_REGISTER, tracer) )
      return tree
    elif rule == 3:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_INLINE, tracer) )
      return tree
    elif rule == 4:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_AUTO, tracer) )
      return tree
    elif rule == 11:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_VOID, tracer) )
      return tree
    elif rule == 17:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_UNSIGNED, tracer) )
      return tree
    elif rule == 18:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_IF, tracer) )
      return tree
    elif rule == 20:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_DOUBLE, tracer) )
      return tree
    elif rule == 27:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LONG, tracer) )
      return tree
    elif rule == 32:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_WHILE, tracer) )
      return tree
    elif rule == 36:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_FOR, tracer) )
      return tree
    elif rule == 38:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_ELSE, tracer) )
      return tree
    elif rule == 39:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_VOLATILE, tracer) )
      return tree
    elif rule == 47:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL__IMAGINARY, tracer) )
      return tree
    elif rule == 49:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL__BOOL, tracer) )
      return tree
    elif rule == 50:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_INT, tracer) )
      return tree
    elif rule == 57:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_CONST, tracer) )
      return tree
    elif rule == 59:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_TYPEDEF, tracer) )
      return tree
    elif rule == 67:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL__COMPLEX, tracer) )
      return tree
    elif rule == 72:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_ENUM, tracer) )
      return tree
    elif rule == 74:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_EXTERN, tracer) )
      return tree
    elif rule == 88:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_STATIC, tracer) )
      return tree
    elif rule == 97:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_GOTO, tracer) )
      return tree
    elif rule == 107:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_SHORT, tracer) )
      return tree
    elif rule == 111:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_RETURN, tracer) )
      return tree
    elif rule == 115:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_SWITCH, tracer) )
      return tree
    elif rule == 118:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_STRUCT, tracer) )
      return tree
    elif rule == 119:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_CHAR, tracer) )
      return tree
    elif rule == 124:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_RESTRICT, tracer) )
      return tree
    elif rule == 130:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_BREAK, tracer) )
      return tree
    elif rule == 143:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_CONTINUE, tracer) )
      return tree
    elif rule == 162:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_UNION, tracer) )
      return tree
    elif rule == 168:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_SIGNED, tracer) )
      return tree
    elif rule == 170:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_FLOAT, tracer) )
      return tree
    elif rule == 180:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_DO, tracer) )
      return tree
    elif rule == 184:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_SIZEOF, tracer) )
      return tree
    elif rule == 185:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_DEFAULT, tracer) )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def __DIRECT_DECLARATOR(self, depth = 0):
    rule = self.rule(110)
    if depth is not False:
      tracer = DebugTracer("__DIRECT_DECLARATOR", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(110, self.getAtomString(110)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  bp0 = {
    2: 2000,
    8: 11000,
    9: 8000,
    13: 10000,
    14: 7000,
    15: 2000,
    16: 6000,
    18: 2000,
    20: 10000,
    21: 2000,
    25: 5000,
    26: 10000,
    32: 13000,
    34: 2000,
    36: 11000,
    39: 9000,
    42: 15000,
    47: 15000,
    48: 12000,
    51: 15000,
    57: 2000,
    59: 10000,
    64: 2000,
    69: 13000,
    72: 3000,
    73: 13000,
    78: 2000,
    82: 2000,
    84: 15000,
    86: 4000,
    87: 2000,
    88: 2000,
    89: 15000,
    92: 9000,
    94: 1000,
    95: 12000,
    98: 15000,
  }
  def expr(self):
    return self.__EXPR()
  def __EXPR( self, rbp = 0, depth = 0 ):
    t = self.sym
    if depth is not False:
      tracer = DebugTracer("(expr) __EXPR", str(self.sym), 'N/A', depth)
      depth = depth + 1
    else:
      tracer = None
    left = self.nud0(depth)
    if isinstance(left, ParseTree):
      tracer.add(left.tracer)
    while rbp < self.binding_power(self.sym, self.bp0):
      left = self.led0(left, depth)
      if isinstance(left, ParseTree):
        tracer.add(left.tracer)
    if left:
      left.isExpr = True
      left.tracer = tracer
    return left
  def nud0(self, tracer):
    tree = ParseTree( NonTerminal(self.str_nonterminal['_expr'], '_expr') )
    if self.sym.getId() == 32:
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(14000) )
      tree.astTransform = AstTransformNodeCreator('Dereference', {'var': 1})
      return tree
    if self.sym.getId() == 98:
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(14000) )
      tree.astTransform = AstTransformNodeCreator('PreIncr', {'var': 1})
      return tree
    if self.sym.getId() == 100:
      return tree
    if self.sym.getId() == 43:
      return self.expect( 43, tracer )
      return tree
    if self.sym.getId() == 108:
      return self.expect( 108, tracer )
      return tree
    if self.sym.getId() == 16:
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(14000) )
      tree.astTransform = AstTransformNodeCreator('AddressOf', {'var': 1})
      return tree
    if self.sym.getId() == 51:
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(14000) )
      tree.astTransform = AstTransformNodeCreator('PreDecr', {'var': 1})
      return tree
    if self.sym.getId() == 89:
      tree.add( self.expect( 89, tracer ) ) #here?
      tree.add(self.__EXPR())
      tree.add( self.expect( 28, tracer ) ) #here?
      return tree
    if self.sym.getId() == 61:
      return self.expect( 61, tracer )
      tree.astTransform = AstTransformNodeCreator('ArrayIndex', {'params': 2, 'name': 0})
      return tree
  def led0(self, left, tracer):
    tree = ParseTree( NonTerminal(self.str_nonterminal['_expr'], '_expr') )
    if self.sym.getId() == 2:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(1999) )
      tree.astTransform = AstTransformNodeCreator('RightShiftAssign', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 8:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(11000) )
      tree.astTransform = AstTransformNodeCreator('LeftShift', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 9:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(8000) )
      tree.astTransform = AstTransformNodeCreator('BitOR', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 13:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(10000) )
      tree.astTransform = AstTransformNodeCreator('LessThan', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 14:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(7000) )
      tree.astTransform = AstTransformNodeCreator('BitXOR', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 15:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(1999) )
      tree.astTransform = AstTransformNodeCreator('ModAssign', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 16:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(6000) )
      tree.astTransform = AstTransformNodeCreator('BitAND', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 18:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(1999) )
      tree.astTransform = AstTransformNodeCreator('XORAssign', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 20:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(10000) )
      tree.astTransform = AstTransformNodeCreator('GreaterThanEq', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 21:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(1999) )
      tree.astTransform = AstTransformNodeCreator('Assign', {'var': 0, 'value': 2})
      return tree
    if self.sym.getId() == 26:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(10000) )
      tree.astTransform = AstTransformNodeCreator('LessThanEq', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 32:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(13000) )
      tree.astTransform = AstTransformNodeCreator('Mul', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 34:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(1999) )
      tree.astTransform = AstTransformNodeCreator('SubtractAssign', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 36:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(11000) )
      tree.astTransform = AstTransformNodeCreator('RightShift', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 42:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(0) )
      tree.astTransform = AstTransformNodeCreator('DerefMemberSelect', {'member': 2, 'object': 0})
      return tree
    if self.sym.getId() == 47:
      if left:
        tree.add( left )
      ls = AstList()
      tree.add( self.expect( 47, tracer ) )
      if self.sym.getId() != 76:
        while 1:
          ls.append( self.__EXPR() )
          if self.sym.getId() != 94:
            break
          self.expect( 94, tracer )
      tree.add( ls )
      tree.add( self.expect(76, tracer ) )
      tree.astTransform = AstTransformNodeCreator('ArrayIndex', {'params': 2, 'name': 0})
      return tree
    if self.sym.getId() == 48:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(12000) )
      tree.astTransform = AstTransformNodeCreator('Sub', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 51:
      if left:
        tree.add( left )
      tree.add( self.expect( 51, tracer ) )
      tree.astTransform = AstTransformNodeCreator('PostDecr', {'var': 0})
      return tree
    if self.sym.getId() == 57:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(1999) )
      tree.astTransform = AstTransformNodeCreator('ANDAssign', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 59:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(10000) )
      tree.astTransform = AstTransformNodeCreator('GreaterThan', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 64:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(1999) )
      tree.astTransform = AstTransformNodeCreator('AddAssign', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 69:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(13000) )
      tree.astTransform = AstTransformNodeCreator('Div', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 72:
      if left:
        tree.add( left )
      tree.add( self.expect( 72, tracer ) )
      tree.astTransform = AstTransformNodeCreator('TernaryOperator', {'true': 2, 'false': 4, 'cond': 0})
      tree.add(self.__EXPR())
      tree.astTransform = AstTransformNodeCreator('TernaryOperator', {'true': 2, 'false': 4, 'cond': 0})
      tree.add( self.expect( 1, tracer ) )
      tree.astTransform = AstTransformNodeCreator('TernaryOperator', {'true': 2, 'false': 4, 'cond': 0})
      tree.add(self.__EXPR())
      tree.astTransform = AstTransformNodeCreator('TernaryOperator', {'true': 2, 'false': 4, 'cond': 0})
      return tree
    if self.sym.getId() == 73:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(13000) )
      tree.astTransform = AstTransformNodeCreator('Mod', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 78:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(1999) )
      tree.astTransform = AstTransformNodeCreator('ORAssign', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 82:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(1999) )
      tree.astTransform = AstTransformNodeCreator('MultiplyAssign', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 84:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(0) )
      tree.astTransform = AstTransformNodeCreator('MemberSelect', {'member': 2, 'object': 0})
      return tree
    if self.sym.getId() == 87:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(1999) )
      tree.astTransform = AstTransformNodeCreator('DivideAssign', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 88:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(1999) )
      tree.astTransform = AstTransformNodeCreator('LeftShiftAssign', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 89:
      if left:
        tree.add( left )
      ls = AstList()
      tree.add( self.expect( 89, tracer ) )
      if self.sym.getId() != 28:
        while 1:
          ls.append( self.__EXPR() )
          if self.sym.getId() != 94:
            break
          self.expect( 94, tracer )
      tree.add( ls )
      tree.add( self.expect(28, tracer ) )
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      return tree
    if self.sym.getId() == 92:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(8999) )
      tree.astTransform = AstTransformNodeCreator('Equals', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 94:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(1000) )
      tree.astTransform = AstTransformNodeCreator('Comma', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 95:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(12000) )
      tree.astTransform = AstTransformNodeCreator('Add', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 98:
      if left:
        tree.add( left )
      tree.add( self.expect( 98, tracer ) )
      tree.astTransform = AstTransformNodeCreator('PostIncr', {'var': 0})
      return tree
  bp1 = {
    47: 1000,
  }
  def direct_declarator(self):
    return self.__DIRECT_DECLARATOR()
  def __DIRECT_DECLARATOR( self, rbp = 0, depth = 0 ):
    t = self.sym
    if depth is not False:
      tracer = DebugTracer("(expr) __DIRECT_DECLARATOR", str(self.sym), 'N/A', depth)
      depth = depth + 1
    else:
      tracer = None
    left = self.nud1(depth)
    if isinstance(left, ParseTree):
      tracer.add(left.tracer)
    while rbp < self.binding_power(self.sym, self.bp1):
      left = self.led1(left, depth)
      if isinstance(left, ParseTree):
        tracer.add(left.tracer)
    if left:
      left.isExpr = True
      left.tracer = tracer
    return left
  def nud1(self, tracer):
    tree = ParseTree( NonTerminal(self.str_nonterminal['_direct_declarator'], '_direct_declarator') )
    if self.sym.getId() == 61:
      return self.expect( 61, tracer )
      return tree
    if self.sym.getId() == 110:
      return tree
  def led1(self, left, tracer):
    tree = ParseTree( NonTerminal(self.str_nonterminal['_expr'], '_expr') )
    if self.sym.getId() == 47:
      if left:
        tree.add( left )
      tree.add( self.expect( 47, tracer ) )
      tree.add( self.expect( 76, tracer ) )
      return tree
