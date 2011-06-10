import sys
def parse( iterator, entry ):
  p = Parser()
  return p.parse(iterator, entry)
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
class ParseTree():
  def __init__(self, nonterminal):
    self.children = []
    self.nonterminal = nonterminal
    self.astTransform = None
    self.isExpr = False
    self.list = False
  def add( self, tree ):
    self.children.append( tree )
  def toAst( self ):
    if self.list == 'slist' or self.list == 'nlist':
      if len(self.children) == 0:
        return []
      offset = 1 if not isinstance(self.children[0], ParseTree) else 0
      r = [self.children[offset].toAst()]
      r.extend(self.children[offset+1].toAst())
      return r
    elif self.list == 'tlist':
      if len(self.children) == 0:
        return []
      r = [self.children[0].toAst()]
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
  def __init__(self, message):
    self.message = message
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
  TERMINAL_COLON = 0
  TERMINAL_EXTERN = 1
  TERMINAL_LT = 2
  TERMINAL_POUNDPOUND = 3
  TERMINAL_QUESTIONMARK = 4
  TERMINAL_RSHIFT = 5
  TERMINAL_UNIVERSAL_CHARACTER_NAME = 6
  TERMINAL_OCTAL_CONSTANT = 7
  TERMINAL_FLOAT = 8
  TERMINAL_STRUCT = 9
  TERMINAL_NUMBER = 10
  TERMINAL_ADD = 11
  TERMINAL_GTEQ = 12
  TERMINAL_DOUBLE = 13
  TERMINAL_FOR = 14
  TERMINAL_GOTO = 15
  TERMINAL_MULEQ = 16
  TERMINAL_DECIMAL_FLOATING_CONSTANT = 17
  TERMINAL_MOD = 18
  TERMINAL__COMPLEX = 19
  TERMINAL_HEADER_NAME = 20
  TERMINAL_BITANDEQ = 21
  TERMINAL_ASSIGN = 22
  TERMINAL_IF = 23
  TERMINAL_STATIC = 24
  TERMINAL_INCR = 25
  TERMINAL_CHARACTER_CONSTANT = 26
  TERMINAL_INLINE = 27
  TERMINAL_SEMI = 28
  TERMINAL_SIGNED = 29
  TERMINAL_RSHIFTEQ = 30
  TERMINAL_VOLATILE = 31
  TERMINAL_DIVEQ = 32
  TERMINAL_DEFAULT = 33
  TERMINAL_INT = 34
  TERMINAL_DECIMAL_CONSTANT = 35
  TERMINAL_SUBEQ = 36
  TERMINAL_ADDEQ = 37
  TERMINAL_LONG = 38
  TERMINAL_BITOR = 39
  TERMINAL_INTEGER_CONSTANT = 40
  TERMINAL_CHAR = 41
  TERMINAL_STRING_LITERAL = 42
  TERMINAL_HEXADECIMAL_FLOATING_CONSTANT = 43
  TERMINAL_MODEQ = 44
  TERMINAL_TILDE = 45
  TERMINAL_SHORT = 46
  TERMINAL_RESTRICT = 47
  TERMINAL_IMAGINARY = 48
  TERMINAL_LBRACE = 49
  TERMINAL_RETURN = 50
  TERMINAL_LSHIFTEQ = 51
  TERMINAL_DOT = 52
  TERMINAL_ELSE = 53
  TERMINAL_MUL = 54
  TERMINAL_REGISTER = 55
  TERMINAL_BREAK = 56
  TERMINAL_LTEQ = 57
  TERMINAL_OR = 58
  TERMINAL_WHILE = 59
  TERMINAL_BITAND = 60
  TERMINAL_LPAREN = 61
  TERMINAL_EQ = 62
  TERMINAL_RBRACE = 63
  TERMINAL_Q_NAME = 64
  TERMINAL__IMAGINARY = 65
  TERMINAL_BITXOR = 66
  TERMINAL_SIZEOF = 67
  TERMINAL_COMPLEX = 68
  TERMINAL_COMMA = 69
  TERMINAL_ARROW = 70
  TERMINAL_CASE = 71
  TERMINAL_NOT = 72
  TERMINAL_CONST = 73
  TERMINAL_DQUOTE = 74
  TERMINAL_GT = 75
  TERMINAL_H_NAME = 76
  TERMINAL_AMPERSAND = 77
  TERMINAL_BITNOT = 78
  TERMINAL_CONTINUE = 79
  TERMINAL_LSHIFT = 80
  TERMINAL_DECR = 81
  TERMINAL_POUND = 82
  TERMINAL_LSQUARE = 83
  TERMINAL_SWITCH = 84
  TERMINAL_HEXADECIMAL_CONSTANT = 85
  TERMINAL_DO = 86
  TERMINAL_EXCLAMATION_POINT = 87
  TERMINAL__BOOL = 88
  TERMINAL_AUTO = 89
  TERMINAL_RSQUARE = 90
  TERMINAL_UNION = 91
  TERMINAL_RPAREN = 92
  TERMINAL_ELIPSIS = 93
  TERMINAL_TYPEDEF = 94
  TERMINAL_BOOL = 95
  TERMINAL_NEQ = 96
  TERMINAL_UNSIGNED = 97
  TERMINAL_ENUM = 98
  TERMINAL_DIV = 99
  TERMINAL_SUB = 100
  TERMINAL_BITXOREQ = 101
  TERMINAL_BITOREQ = 102
  TERMINAL_VOID = 103
  TERMINAL_AND = 104
  TERMINAL_IDENTIFIER = 105
  terminal_str = {
    0: 'colon',
    1: 'extern',
    2: 'lt',
    3: 'poundpound',
    4: 'questionmark',
    5: 'rshift',
    6: 'universal_character_name',
    7: 'octal_constant',
    8: 'float',
    9: 'struct',
    10: 'number',
    11: 'add',
    12: 'gteq',
    13: 'double',
    14: 'for',
    15: 'goto',
    16: 'muleq',
    17: 'decimal_floating_constant',
    18: 'mod',
    19: '_complex',
    20: 'header_name',
    21: 'bitandeq',
    22: 'assign',
    23: 'if',
    24: 'static',
    25: 'incr',
    26: 'character_constant',
    27: 'inline',
    28: 'semi',
    29: 'signed',
    30: 'rshifteq',
    31: 'volatile',
    32: 'diveq',
    33: 'default',
    34: 'int',
    35: 'decimal_constant',
    36: 'subeq',
    37: 'addeq',
    38: 'long',
    39: 'bitor',
    40: 'integer_constant',
    41: 'char',
    42: 'string_literal',
    43: 'hexadecimal_floating_constant',
    44: 'modeq',
    45: 'tilde',
    46: 'short',
    47: 'restrict',
    48: 'imaginary',
    49: 'lbrace',
    50: 'return',
    51: 'lshifteq',
    52: 'dot',
    53: 'else',
    54: 'mul',
    55: 'register',
    56: 'break',
    57: 'lteq',
    58: 'or',
    59: 'while',
    60: 'bitand',
    61: 'lparen',
    62: 'eq',
    63: 'rbrace',
    64: 'q_name',
    65: '_imaginary',
    66: 'bitxor',
    67: 'sizeof',
    68: 'complex',
    69: 'comma',
    70: 'arrow',
    71: 'case',
    72: 'not',
    73: 'const',
    74: 'dquote',
    75: 'gt',
    76: 'h_name',
    77: 'ampersand',
    78: 'bitnot',
    79: 'continue',
    80: 'lshift',
    81: 'decr',
    82: 'pound',
    83: 'lsquare',
    84: 'switch',
    85: 'hexadecimal_constant',
    86: 'do',
    87: 'exclamation_point',
    88: '_bool',
    89: 'auto',
    90: 'rsquare',
    91: 'union',
    92: 'rparen',
    93: 'elipsis',
    94: 'typedef',
    95: 'bool',
    96: 'neq',
    97: 'unsigned',
    98: 'enum',
    99: 'div',
    100: 'sub',
    101: 'bitxoreq',
    102: 'bitoreq',
    103: 'void',
    104: 'and',
    105: 'identifier',
  }
  nonterminal_str = {
    106: 'constant',
    107: '_expr',
    108: 'type_qualifier',
    109: 'punctuator',
    110: 'enumeration_constant',
    111: 'keyword',
    112: 'header_name',
    113: 'terminals',
    114: '_gen0',
    115: '_direct_declarator',
    116: '_gen2',
    117: 'token',
    118: 'integer_constant',
    119: '_gen1',
  }
  str_terminal = {
    'colon': 0,
    'extern': 1,
    'lt': 2,
    'poundpound': 3,
    'questionmark': 4,
    'rshift': 5,
    'universal_character_name': 6,
    'octal_constant': 7,
    'float': 8,
    'struct': 9,
    'number': 10,
    'add': 11,
    'gteq': 12,
    'double': 13,
    'for': 14,
    'goto': 15,
    'muleq': 16,
    'decimal_floating_constant': 17,
    'mod': 18,
    '_complex': 19,
    'header_name': 20,
    'bitandeq': 21,
    'assign': 22,
    'if': 23,
    'static': 24,
    'incr': 25,
    'character_constant': 26,
    'inline': 27,
    'semi': 28,
    'signed': 29,
    'rshifteq': 30,
    'volatile': 31,
    'diveq': 32,
    'default': 33,
    'int': 34,
    'decimal_constant': 35,
    'subeq': 36,
    'addeq': 37,
    'long': 38,
    'bitor': 39,
    'integer_constant': 40,
    'char': 41,
    'string_literal': 42,
    'hexadecimal_floating_constant': 43,
    'modeq': 44,
    'tilde': 45,
    'short': 46,
    'restrict': 47,
    'imaginary': 48,
    'lbrace': 49,
    'return': 50,
    'lshifteq': 51,
    'dot': 52,
    'else': 53,
    'mul': 54,
    'register': 55,
    'break': 56,
    'lteq': 57,
    'or': 58,
    'while': 59,
    'bitand': 60,
    'lparen': 61,
    'eq': 62,
    'rbrace': 63,
    'q_name': 64,
    '_imaginary': 65,
    'bitxor': 66,
    'sizeof': 67,
    'complex': 68,
    'comma': 69,
    'arrow': 70,
    'case': 71,
    'not': 72,
    'const': 73,
    'dquote': 74,
    'gt': 75,
    'h_name': 76,
    'ampersand': 77,
    'bitnot': 78,
    'continue': 79,
    'lshift': 80,
    'decr': 81,
    'pound': 82,
    'lsquare': 83,
    'switch': 84,
    'hexadecimal_constant': 85,
    'do': 86,
    'exclamation_point': 87,
    '_bool': 88,
    'auto': 89,
    'rsquare': 90,
    'union': 91,
    'rparen': 92,
    'elipsis': 93,
    'typedef': 94,
    'bool': 95,
    'neq': 96,
    'unsigned': 97,
    'enum': 98,
    'div': 99,
    'sub': 100,
    'bitxoreq': 101,
    'bitoreq': 102,
    'void': 103,
    'and': 104,
    'identifier': 105,
  }
  str_nonterminal = {
    'constant': 106,
    '_expr': 107,
    'type_qualifier': 108,
    'punctuator': 109,
    'enumeration_constant': 110,
    'keyword': 111,
    'header_name': 112,
    'terminals': 113,
    '_gen0': 114,
    '_direct_declarator': 115,
    '_gen2': 116,
    'token': 117,
    'integer_constant': 118,
    '_gen1': 119,
  }
  terminal_count = 106
  nonterminal_count = 14
  parse_table = [
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [28, -1, 37, 186, 63, 144, -1, -1, -1, -1, -1, 179, 27, -1, -1, -1, 136, -1, 49, -1, -1, 119, 33, -1, -1, 167, -1, -1, 159, -1, 51, -1, -1, -1, -1, -1, 69, 90, -1, 129, -1, -1, -1, -1, 2, 78, -1, -1, -1, 43, -1, 38, 77, -1, 3, -1, -1, 126, 188, -1, -1, 143, 20, 125, -1, -1, 177, -1, -1, 84, 111, -1, -1, -1, -1, 36, -1, 141, -1, -1, 132, 133, 184, 191, -1, -1, -1, 162, -1, -1, 166, -1, 110, 149, -1, -1, 120, -1, -1, 70, 180, 40, 156, -1, 189, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 55],
  [-1, 73, -1, -1, -1, -1, -1, -1, 92, 102, -1, -1, -1, 157, 190, 14, -1, -1, -1, 152, -1, -1, -1, 187, 88, -1, -1, 47, -1, 131, -1, 140, -1, 32, 128, -1, -1, -1, 116, -1, -1, 80, -1, -1, -1, -1, 164, 11, -1, -1, 25, -1, -1, 74, -1, 94, 45, -1, -1, 127, -1, -1, -1, -1, -1, 172, -1, 57, -1, -1, -1, 62, -1, 98, -1, -1, -1, -1, -1, 79, -1, -1, -1, -1, 23, -1, 53, -1, 193, 112, -1, 142, -1, -1, 29, -1, -1, 46, 65, -1, -1, -1, -1, 171, -1, -1],
  [-1, -1, 44, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 42, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [107, 183, 58, 134, 31, 108, 104, -1, 192, 145, 41, 101, 160, 99, 21, 18, 117, 76, 8, -1, 130, 168, 26, 48, 82, 6, 161, 170, 68, 163, 12, 1, 154, 147, 138, -1, 194, 150, 137, 71, 35, 115, 64, 155, 75, 17, 10, 93, 114, 89, 176, 61, 19, 169, 5, 113, 96, 118, 52, 85, 81, 122, 87, 95, -1, -1, 59, 72, 121, 148, 22, 165, 185, 7, -1, 91, -1, -1, -1, 139, 67, 195, 30, 66, 16, -1, 123, 175, -1, 124, 54, 151, 4, 97, 56, 178, 24, 106, 50, 15, 13, 9, 100, 146, 39, 86],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [105, 34, 105, 105, 105, 105, -1, -1, 34, 34, -1, 105, 105, 34, 34, 34, 105, -1, 105, 34, -1, 105, 105, 34, 34, 105, -1, 34, 105, 34, 105, 34, -1, 34, 34, -1, 105, 105, 34, 105, -1, 34, 103, -1, 105, 105, 34, 34, -1, 105, 34, 105, 105, 34, 105, 34, 34, 105, 105, 34, -1, 105, 105, 105, -1, 34, 105, 34, -1, 105, 105, 34, -1, 34, -1, 105, -1, 105, -1, 34, 105, 105, 105, 105, 34, -1, 34, 105, 34, 34, 105, 34, 105, 105, 34, -1, 105, 34, 34, 105, 105, 105, 105, 34, 105, 60],
  [-1, -1, -1, -1, -1, -1, -1, 109, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 0, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 174, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1]
  ]
  def terminal(self, str):
    return self.str_terminal[str]
  def terminalNames(self):
    return list(self.str_terminal.keys())
  def isTerminal(self, id):
    return 0 <= id <= 105
  def isNonTerminal(self, id):
    return 106 <= id <= 119
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
      raise SyntaxError('Syntax Error: Finished parsing without consuming all tokens.')
    self.iterator = None
    self.sym = None
    return tree
  def next(self):
    self.sym = self.getsym()
    if self.sym is not None and not self.isTerminal(self.sym.getId()):
      self.sym = None
      raise SyntaxError('Invalid symbol ID: %d (%s)'%(self.sym.getId(), self.sym))
    if self.recorder.awake and self.sym is not None:
      self.recorder.record(self.sym)
    return self.sym
  def expect(self, s):
    if self.sym and s == self.sym.getId():
      symbol = self.sym
      self.sym = self.next()
      return symbol
    else:
      raise SyntaxError('Unexpected symbol.  Expected %s, got %s.' %(self.terminal_str[s], self.sym if self.sym else 'None'))
  def rule(self, n):
    if self.sym == None: return -1
    return self.parse_table[n - 106][self.sym.getId()]
  def _CONSTANT(self):
    rule = self.rule(106)
    tree = ParseTree( NonTerminal(106, self.getAtomString(106)) )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    raise SyntaxError('Error: Unexpected symbol')
  def _TYPE_QUALIFIER(self):
    rule = self.rule(108)
    tree = ParseTree( NonTerminal(108, self.getAtomString(108)) )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    raise SyntaxError('Error: Unexpected symbol')
  def _PUNCTUATOR(self):
    rule = self.rule(109)
    tree = ParseTree( NonTerminal(109, self.getAtomString(109)) )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 2:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_MODEQ) )
      return tree
    elif rule == 3:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_MUL) )
      return tree
    elif rule == 20:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_EQ) )
      return tree
    elif rule == 27:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_GTEQ) )
      return tree
    elif rule == 28:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_COLON) )
      return tree
    elif rule == 33:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_ASSIGN) )
      return tree
    elif rule == 36:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_GT) )
      return tree
    elif rule == 37:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LT) )
      return tree
    elif rule == 38:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LSHIFTEQ) )
      return tree
    elif rule == 40:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_BITXOREQ) )
      return tree
    elif rule == 43:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LBRACE) )
      return tree
    elif rule == 49:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_MOD) )
      return tree
    elif rule == 51:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_RSHIFTEQ) )
      return tree
    elif rule == 63:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_QUESTIONMARK) )
      return tree
    elif rule == 69:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_SUBEQ) )
      return tree
    elif rule == 70:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_DIV) )
      return tree
    elif rule == 77:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_DOT) )
      return tree
    elif rule == 78:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_TILDE) )
      return tree
    elif rule == 84:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_COMMA) )
      return tree
    elif rule == 90:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_ADDEQ) )
      return tree
    elif rule == 110:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_RPAREN) )
      return tree
    elif rule == 111:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_ARROW) )
      return tree
    elif rule == 119:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_BITANDEQ) )
      return tree
    elif rule == 120:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_NEQ) )
      return tree
    elif rule == 125:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_RBRACE) )
      return tree
    elif rule == 126:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LTEQ) )
      return tree
    elif rule == 129:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_BITOR) )
      return tree
    elif rule == 132:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LSHIFT) )
      return tree
    elif rule == 133:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_DECR) )
      return tree
    elif rule == 136:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_MULEQ) )
      return tree
    elif rule == 141:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_AMPERSAND) )
      return tree
    elif rule == 143:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LPAREN) )
      return tree
    elif rule == 144:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_RSHIFT) )
      return tree
    elif rule == 149:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_ELIPSIS) )
      return tree
    elif rule == 156:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_BITOREQ) )
      return tree
    elif rule == 159:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_SEMI) )
      return tree
    elif rule == 162:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_EXCLAMATION_POINT) )
      return tree
    elif rule == 166:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_RSQUARE) )
      return tree
    elif rule == 167:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_INCR) )
      return tree
    elif rule == 177:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_BITXOR) )
      return tree
    elif rule == 179:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_ADD) )
      return tree
    elif rule == 180:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_SUB) )
      return tree
    elif rule == 184:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_POUND) )
      return tree
    elif rule == 186:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_POUNDPOUND) )
      return tree
    elif rule == 188:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_OR) )
      return tree
    elif rule == 189:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_AND) )
      return tree
    elif rule == 191:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LSQUARE) )
      return tree
    raise SyntaxError('Error: Unexpected symbol')
  def _ENUMERATION_CONSTANT(self):
    rule = self.rule(110)
    tree = ParseTree( NonTerminal(110, self.getAtomString(110)) )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 55:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_IDENTIFIER) )
      return tree
    raise SyntaxError('Error: Unexpected symbol')
  def _KEYWORD(self):
    rule = self.rule(111)
    tree = ParseTree( NonTerminal(111, self.getAtomString(111)) )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 11:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_RESTRICT) )
      return tree
    elif rule == 14:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_GOTO) )
      return tree
    elif rule == 23:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_SWITCH) )
      return tree
    elif rule == 25:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_RETURN) )
      return tree
    elif rule == 29:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_TYPEDEF) )
      return tree
    elif rule == 32:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_DEFAULT) )
      return tree
    elif rule == 45:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_BREAK) )
      return tree
    elif rule == 46:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_UNSIGNED) )
      return tree
    elif rule == 47:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_INLINE) )
      return tree
    elif rule == 53:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_DO) )
      return tree
    elif rule == 57:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_SIZEOF) )
      return tree
    elif rule == 62:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_CASE) )
      return tree
    elif rule == 65:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_ENUM) )
      return tree
    elif rule == 73:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_EXTERN) )
      return tree
    elif rule == 74:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_ELSE) )
      return tree
    elif rule == 79:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_CONTINUE) )
      return tree
    elif rule == 80:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_CHAR) )
      return tree
    elif rule == 88:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_STATIC) )
      return tree
    elif rule == 92:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_FLOAT) )
      return tree
    elif rule == 94:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_REGISTER) )
      return tree
    elif rule == 98:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_CONST) )
      return tree
    elif rule == 102:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_STRUCT) )
      return tree
    elif rule == 112:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_AUTO) )
      return tree
    elif rule == 116:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LONG) )
      return tree
    elif rule == 127:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_WHILE) )
      return tree
    elif rule == 128:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_INT) )
      return tree
    elif rule == 131:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_SIGNED) )
      return tree
    elif rule == 140:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_VOLATILE) )
      return tree
    elif rule == 142:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_UNION) )
      return tree
    elif rule == 152:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL__COMPLEX) )
      return tree
    elif rule == 157:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_DOUBLE) )
      return tree
    elif rule == 164:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_SHORT) )
      return tree
    elif rule == 171:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_VOID) )
      return tree
    elif rule == 172:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL__IMAGINARY) )
      return tree
    elif rule == 187:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_IF) )
      return tree
    elif rule == 190:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_FOR) )
      return tree
    elif rule == 193:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL__BOOL) )
      return tree
    raise SyntaxError('Error: Unexpected symbol')
  def _HEADER_NAME(self):
    rule = self.rule(112)
    tree = ParseTree( NonTerminal(112, self.getAtomString(112)) )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 42:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_DQUOTE) )
      tree.add( self.expect(self.TERMINAL_Q_NAME) )
      tree.add( self.expect(self.TERMINAL_DQUOTE) )
      return tree
    elif rule == 44:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LT) )
      tree.add( self.expect(self.TERMINAL_H_NAME) )
      tree.add( self.expect(self.TERMINAL_GT) )
      return tree
    raise SyntaxError('Error: Unexpected symbol')
  def _TERMINALS(self):
    rule = self.rule(113)
    tree = ParseTree( NonTerminal(113, self.getAtomString(113)) )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 1:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_VOLATILE) )
      return tree
    elif rule == 4:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_RPAREN) )
      return tree
    elif rule == 5:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_MUL) )
      return tree
    elif rule == 6:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_INCR) )
      return tree
    elif rule == 7:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_CONST) )
      return tree
    elif rule == 8:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_MOD) )
      return tree
    elif rule == 9:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_BITXOREQ) )
      return tree
    elif rule == 10:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_SHORT) )
      return tree
    elif rule == 12:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_RSHIFTEQ) )
      return tree
    elif rule == 13:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_SUB) )
      return tree
    elif rule == 15:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_DIV) )
      return tree
    elif rule == 16:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_SWITCH) )
      return tree
    elif rule == 17:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_TILDE) )
      return tree
    elif rule == 18:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_GOTO) )
      return tree
    elif rule == 19:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_DOT) )
      return tree
    elif rule == 21:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_FOR) )
      return tree
    elif rule == 22:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_ARROW) )
      return tree
    elif rule == 24:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_NEQ) )
      return tree
    elif rule == 26:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_ASSIGN) )
      return tree
    elif rule == 30:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_POUND) )
      return tree
    elif rule == 31:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_QUESTIONMARK) )
      return tree
    elif rule == 35:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_INTEGER_CONSTANT) )
      return tree
    elif rule == 39:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_AND) )
      return tree
    elif rule == 41:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_NUMBER) )
      return tree
    elif rule == 48:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_IF) )
      return tree
    elif rule == 50:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_ENUM) )
      return tree
    elif rule == 52:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_OR) )
      return tree
    elif rule == 54:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_RSQUARE) )
      return tree
    elif rule == 56:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_TYPEDEF) )
      return tree
    elif rule == 58:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LT) )
      return tree
    elif rule == 59:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_BITXOR) )
      return tree
    elif rule == 61:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LSHIFTEQ) )
      return tree
    elif rule == 64:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_STRING_LITERAL) )
      return tree
    elif rule == 66:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LSQUARE) )
      return tree
    elif rule == 67:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LSHIFT) )
      return tree
    elif rule == 68:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_SEMI) )
      return tree
    elif rule == 71:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_BITOR) )
      return tree
    elif rule == 72:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_SIZEOF) )
      return tree
    elif rule == 75:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_MODEQ) )
      return tree
    elif rule == 76:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_DECIMAL_FLOATING_CONSTANT) )
      return tree
    elif rule == 81:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_BITAND) )
      return tree
    elif rule == 82:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_STATIC) )
      return tree
    elif rule == 85:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_WHILE) )
      return tree
    elif rule == 86:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_IDENTIFIER) )
      return tree
    elif rule == 87:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_EQ) )
      return tree
    elif rule == 89:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LBRACE) )
      return tree
    elif rule == 91:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_GT) )
      return tree
    elif rule == 93:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_RESTRICT) )
      return tree
    elif rule == 95:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_RBRACE) )
      return tree
    elif rule == 96:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_BREAK) )
      return tree
    elif rule == 97:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_ELIPSIS) )
      return tree
    elif rule == 99:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_DOUBLE) )
      return tree
    elif rule == 100:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_BITOREQ) )
      return tree
    elif rule == 101:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_ADD) )
      return tree
    elif rule == 104:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_UNIVERSAL_CHARACTER_NAME) )
      return tree
    elif rule == 106:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_UNSIGNED) )
      return tree
    elif rule == 107:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_COLON) )
      return tree
    elif rule == 108:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_RSHIFT) )
      return tree
    elif rule == 113:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_REGISTER) )
      return tree
    elif rule == 114:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_IMAGINARY) )
      return tree
    elif rule == 115:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_CHAR) )
      return tree
    elif rule == 117:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_MULEQ) )
      return tree
    elif rule == 118:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LTEQ) )
      return tree
    elif rule == 121:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_COMPLEX) )
      return tree
    elif rule == 122:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LPAREN) )
      return tree
    elif rule == 123:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_DO) )
      return tree
    elif rule == 124:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_AUTO) )
      return tree
    elif rule == 130:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_HEADER_NAME) )
      return tree
    elif rule == 134:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_POUNDPOUND) )
      return tree
    elif rule == 135:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_RBRACE) )
      return tree
    elif rule == 137:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LONG) )
      return tree
    elif rule == 138:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_INT) )
      return tree
    elif rule == 139:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_CONTINUE) )
      return tree
    elif rule == 145:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_STRUCT) )
      return tree
    elif rule == 146:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_VOID) )
      return tree
    elif rule == 147:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_DEFAULT) )
      return tree
    elif rule == 148:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_COMMA) )
      return tree
    elif rule == 150:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_ADDEQ) )
      return tree
    elif rule == 151:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_UNION) )
      return tree
    elif rule == 153:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LBRACE) )
      return tree
    elif rule == 154:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_DIVEQ) )
      return tree
    elif rule == 155:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_HEXADECIMAL_FLOATING_CONSTANT) )
      return tree
    elif rule == 158:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LSQUARE) )
      return tree
    elif rule == 160:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_GTEQ) )
      return tree
    elif rule == 161:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_CHARACTER_CONSTANT) )
      return tree
    elif rule == 163:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_SIGNED) )
      return tree
    elif rule == 165:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_CASE) )
      return tree
    elif rule == 168:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_BITANDEQ) )
      return tree
    elif rule == 169:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_ELSE) )
      return tree
    elif rule == 170:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_INLINE) )
      return tree
    elif rule == 173:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_POUND) )
      return tree
    elif rule == 175:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_EXCLAMATION_POINT) )
      return tree
    elif rule == 176:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_RETURN) )
      return tree
    elif rule == 178:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_BOOL) )
      return tree
    elif rule == 181:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_RSQUARE) )
      return tree
    elif rule == 182:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_POUNDPOUND) )
      return tree
    elif rule == 183:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_EXTERN) )
      return tree
    elif rule == 185:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_NOT) )
      return tree
    elif rule == 192:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_FLOAT) )
      return tree
    elif rule == 194:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_SUBEQ) )
      return tree
    elif rule == 195:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_DECR) )
      return tree
    raise SyntaxError('Error: Unexpected symbol')
  def __GEN0(self):
    rule = self.rule(114)
    tree = ParseTree( NonTerminal(114, self.getAtomString(114)) )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    raise SyntaxError('Error: Unexpected symbol')
  def __DIRECT_DECLARATOR(self):
    rule = self.rule(115)
    tree = ParseTree( NonTerminal(115, self.getAtomString(115)) )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    raise SyntaxError('Error: Unexpected symbol')
  def __GEN2(self):
    rule = self.rule(116)
    tree = ParseTree( NonTerminal(116, self.getAtomString(116)) )
    tree.list = 'nlist'
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    raise SyntaxError('Error: Unexpected symbol')
  def _TOKEN(self):
    rule = self.rule(117)
    tree = ParseTree( NonTerminal(117, self.getAtomString(117)) )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 34:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self._KEYWORD() )
      return tree
    elif rule == 60:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_IDENTIFIER) )
      return tree
    elif rule == 83:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self._CONSTANT() )
      return tree
    elif rule == 103:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_STRING_LITERAL) )
      return tree
    elif rule == 105:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self._PUNCTUATOR() )
      return tree
    raise SyntaxError('Error: Unexpected symbol')
  def _INTEGER_CONSTANT(self):
    rule = self.rule(118)
    tree = ParseTree( NonTerminal(118, self.getAtomString(118)) )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 0:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_DECIMAL_CONSTANT) )
      return tree
    elif rule == 109:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_OCTAL_CONSTANT) )
      return tree
    elif rule == 174:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_HEXADECIMAL_CONSTANT) )
      return tree
    raise SyntaxError('Error: Unexpected symbol')
  def __GEN1(self):
    rule = self.rule(119)
    tree = ParseTree( NonTerminal(119, self.getAtomString(119)) )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    raise SyntaxError('Error: Unexpected symbol')
  bp0 = {
    2: 10000,
    4: 3000,
    5: 11000,
    11: 12000,
    12: 10000,
    16: 2000,
    18: 13000,
    21: 2000,
    22: 2000,
    25: 15000,
    30: 2000,
    32: 2000,
    36: 2000,
    37: 2000,
    39: 8000,
    44: 2000,
    51: 2000,
    52: 15000,
    54: 13000,
    57: 10000,
    58: 4000,
    60: 6000,
    61: 15000,
    62: 9000,
    66: 7000,
    69: 1000,
    70: 15000,
    75: 10000,
    80: 11000,
    81: 15000,
    83: 15000,
    96: 9000,
    99: 13000,
    100: 12000,
    101: 2000,
    102: 2000,
    104: 5000,
  }
  def __EXPR( self, rbp = 0 ):
    t = self.sym
    left = self.nud0()
    while rbp < self.binding_power(self.sym, self.bp0):
      left = self.led0(left)
    left.isExpr = True
    return left
  def nud0(self):
    tree = ParseTree( NonTerminal(self.str_nonterminal['_expr'], '_expr') )
    if self.sym.getId() == 105:
      return self.expect(105)
      tree.astTransform = AstTransformNodeCreator('ArrayIndex', {'params': 2, 'name': 0})
      return tree
    if self.sym.getId() == 42:
      return self.expect(42)
      return tree
    if self.sym.getId() == 107:
      return tree
    if self.sym.getId() == 61:
      tree.add( self.expect(61) ) #here?
      tree.add(self.__EXPR())
      tree.add( self.expect(92) ) #here?
      return tree
    if self.sym.getId() == 81:
      tree.add( self.expect(self.sym.getId()) )
      tree.add( self.__EXPR(14000) )
      tree.astTransform = AstTransformNodeCreator('PreDecr', {'var': 1})
      return tree
    if self.sym.getId() == 54:
      tree.add( self.expect(self.sym.getId()) )
      tree.add( self.__EXPR(14000) )
      tree.astTransform = AstTransformNodeCreator('Dereference', {'var': 1})
      return tree
    if self.sym.getId() == 25:
      tree.add( self.expect(self.sym.getId()) )
      tree.add( self.__EXPR(14000) )
      tree.astTransform = AstTransformNodeCreator('PreIncr', {'var': 1})
      return tree
    if self.sym.getId() == 60:
      tree.add( self.expect(self.sym.getId()) )
      tree.add( self.__EXPR(14000) )
      tree.astTransform = AstTransformNodeCreator('AddressOf', {'var': 1})
      return tree
    if self.sym.getId() == 106:
      return self.expect(106)
      return tree
  def led0(self, left):
    tree = ParseTree( NonTerminal(self.str_nonterminal['_expr'], '_expr') )
    if self.sym.getId() == 2:
      if left:
        tree.add( left )
      tree.add( self.expect(self.sym.getId()) )
      tree.add( self.__EXPR(10000) )
      tree.astTransform = AstTransformNodeCreator('LessThan', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 4:
      if left:
        tree.add( left )
      tree.add( self.expect(4) )
      tree.astTransform = AstTransformNodeCreator('TernaryOperator', {'true': 2, 'false': 4, 'cond': 0})
      tree.add(self.__EXPR(0))
      tree.astTransform = AstTransformNodeCreator('TernaryOperator', {'true': 2, 'false': 4, 'cond': 0})
      tree.add( self.expect(0) )
      tree.astTransform = AstTransformNodeCreator('TernaryOperator', {'true': 2, 'false': 4, 'cond': 0})
      tree.add(self.__EXPR(0))
      tree.astTransform = AstTransformNodeCreator('TernaryOperator', {'true': 2, 'false': 4, 'cond': 0})
      return tree
    if self.sym.getId() == 5:
      if left:
        tree.add( left )
      tree.add( self.expect(self.sym.getId()) )
      tree.add( self.__EXPR(11000) )
      tree.astTransform = AstTransformNodeCreator('RightShift', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 11:
      if left:
        tree.add( left )
      tree.add( self.expect(self.sym.getId()) )
      tree.add( self.__EXPR(12000) )
      tree.astTransform = AstTransformNodeCreator('Add', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 12:
      if left:
        tree.add( left )
      tree.add( self.expect(self.sym.getId()) )
      tree.add( self.__EXPR(10000) )
      tree.astTransform = AstTransformNodeCreator('GreaterThanEq', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 16:
      if left:
        tree.add( left )
      tree.add( self.expect(self.sym.getId()) )
      tree.add( self.__EXPR(1999) )
      tree.astTransform = AstTransformNodeCreator('MultiplyAssign', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 18:
      if left:
        tree.add( left )
      tree.add( self.expect(self.sym.getId()) )
      tree.add( self.__EXPR(13000) )
      tree.astTransform = AstTransformNodeCreator('Mod', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 21:
      if left:
        tree.add( left )
      tree.add( self.expect(self.sym.getId()) )
      tree.add( self.__EXPR(1999) )
      tree.astTransform = AstTransformNodeCreator('ANDAssign', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 22:
      if left:
        tree.add( left )
      tree.add( self.expect(self.sym.getId()) )
      tree.add( self.__EXPR(1999) )
      tree.astTransform = AstTransformNodeCreator('Assign', {'var': 0, 'value': 2})
      return tree
    if self.sym.getId() == 25:
      if left:
        tree.add( left )
      tree.add( self.expect(25) )
      tree.astTransform = AstTransformNodeCreator('PostIncr', {'var': 0})
      return tree
    if self.sym.getId() == 30:
      if left:
        tree.add( left )
      tree.add( self.expect(self.sym.getId()) )
      tree.add( self.__EXPR(1999) )
      tree.astTransform = AstTransformNodeCreator('RightShiftAssign', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 32:
      if left:
        tree.add( left )
      tree.add( self.expect(self.sym.getId()) )
      tree.add( self.__EXPR(1999) )
      tree.astTransform = AstTransformNodeCreator('DivideAssign', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 36:
      if left:
        tree.add( left )
      tree.add( self.expect(self.sym.getId()) )
      tree.add( self.__EXPR(1999) )
      tree.astTransform = AstTransformNodeCreator('SubtractAssign', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 37:
      if left:
        tree.add( left )
      tree.add( self.expect(self.sym.getId()) )
      tree.add( self.__EXPR(1999) )
      tree.astTransform = AstTransformNodeCreator('AddAssign', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 39:
      if left:
        tree.add( left )
      tree.add( self.expect(self.sym.getId()) )
      tree.add( self.__EXPR(8000) )
      tree.astTransform = AstTransformNodeCreator('BitOR', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 44:
      if left:
        tree.add( left )
      tree.add( self.expect(self.sym.getId()) )
      tree.add( self.__EXPR(1999) )
      tree.astTransform = AstTransformNodeCreator('ModAssign', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 51:
      if left:
        tree.add( left )
      tree.add( self.expect(self.sym.getId()) )
      tree.add( self.__EXPR(1999) )
      tree.astTransform = AstTransformNodeCreator('LeftShiftAssign', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 52:
      if left:
        tree.add( left )
      tree.add( self.expect(self.sym.getId()) )
      tree.add( self.__EXPR(0) )
      tree.astTransform = AstTransformNodeCreator('MemberSelect', {'member': 2, 'object': 0})
      return tree
    if self.sym.getId() == 54:
      if left:
        tree.add( left )
      tree.add( self.expect(self.sym.getId()) )
      tree.add( self.__EXPR(13000) )
      tree.astTransform = AstTransformNodeCreator('Mul', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 57:
      if left:
        tree.add( left )
      tree.add( self.expect(self.sym.getId()) )
      tree.add( self.__EXPR(10000) )
      tree.astTransform = AstTransformNodeCreator('LessThanEq', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 60:
      if left:
        tree.add( left )
      tree.add( self.expect(self.sym.getId()) )
      tree.add( self.__EXPR(6000) )
      tree.astTransform = AstTransformNodeCreator('BitAND', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 61:
      if left:
        tree.add( left )
      ls = []
      tree.add( self.expect(61) )
      if self.sym.getId() != 92:
        while 1:
          ls.append( self.__EXPR() )
          if self.sym.getId() != 69:
            break
          self.expect(69)
      tree.add( ls )
      tree.add( self.expect(92) )
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      return tree
    if self.sym.getId() == 62:
      if left:
        tree.add( left )
      tree.add( self.expect(self.sym.getId()) )
      tree.add( self.__EXPR(8999) )
      tree.astTransform = AstTransformNodeCreator('Equals', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 66:
      if left:
        tree.add( left )
      tree.add( self.expect(self.sym.getId()) )
      tree.add( self.__EXPR(7000) )
      tree.astTransform = AstTransformNodeCreator('BitXOR', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 69:
      if left:
        tree.add( left )
      tree.add( self.expect(self.sym.getId()) )
      tree.add( self.__EXPR(1000) )
      tree.astTransform = AstTransformNodeCreator('Comma', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 70:
      if left:
        tree.add( left )
      tree.add( self.expect(self.sym.getId()) )
      tree.add( self.__EXPR(0) )
      tree.astTransform = AstTransformNodeCreator('DerefMemberSelect', {'member': 2, 'object': 0})
      return tree
    if self.sym.getId() == 75:
      if left:
        tree.add( left )
      tree.add( self.expect(self.sym.getId()) )
      tree.add( self.__EXPR(10000) )
      tree.astTransform = AstTransformNodeCreator('GreaterThan', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 80:
      if left:
        tree.add( left )
      tree.add( self.expect(self.sym.getId()) )
      tree.add( self.__EXPR(11000) )
      tree.astTransform = AstTransformNodeCreator('LeftShift', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 81:
      if left:
        tree.add( left )
      tree.add( self.expect(81) )
      tree.astTransform = AstTransformNodeCreator('PostDecr', {'var': 0})
      return tree
    if self.sym.getId() == 83:
      if left:
        tree.add( left )
      ls = []
      tree.add( self.expect(83) )
      if self.sym.getId() != 90:
        while 1:
          ls.append( self.__EXPR() )
          if self.sym.getId() != 69:
            break
          self.expect(69)
      tree.add( ls )
      tree.add( self.expect(90) )
      tree.astTransform = AstTransformNodeCreator('ArrayIndex', {'params': 2, 'name': 0})
      return tree
    if self.sym.getId() == 99:
      if left:
        tree.add( left )
      tree.add( self.expect(self.sym.getId()) )
      tree.add( self.__EXPR(13000) )
      tree.astTransform = AstTransformNodeCreator('Div', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 100:
      if left:
        tree.add( left )
      tree.add( self.expect(self.sym.getId()) )
      tree.add( self.__EXPR(12000) )
      tree.astTransform = AstTransformNodeCreator('Sub', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 101:
      if left:
        tree.add( left )
      tree.add( self.expect(self.sym.getId()) )
      tree.add( self.__EXPR(1999) )
      tree.astTransform = AstTransformNodeCreator('XORAssign', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 102:
      if left:
        tree.add( left )
      tree.add( self.expect(self.sym.getId()) )
      tree.add( self.__EXPR(1999) )
      tree.astTransform = AstTransformNodeCreator('ORAssign', {'right': 2, 'left': 0})
      return tree
  bp1 = {
    83: 1000,
  }
  def __DIRECT_DECLARATOR( self, rbp = 0 ):
    t = self.sym
    left = self.nud1()
    while rbp < self.binding_power(self.sym, self.bp1):
      left = self.led1(left)
    left.isExpr = True
    return left
  def nud1(self):
    tree = ParseTree( NonTerminal(self.str_nonterminal['_direct_declarator'], '_direct_declarator') )
    if self.sym.getId() == 105:
      return self.expect(105)
      return tree
    if self.sym.getId() == 115:
      return tree
  def led1(self, left):
    tree = ParseTree( NonTerminal(self.str_nonterminal['_expr'], '_expr') )
    if self.sym.getId() == 83:
      if left:
        tree.add( left )
      tree.add( self.expect(83) )
      tree.add( self.expect(90) )
      return tree
