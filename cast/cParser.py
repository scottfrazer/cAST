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
  def toString(self, format):
    if format == 'type':
      return self.str
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
    self.isNud = False
    self.isPrefix = False
    self.isInfix = False
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
          if idx == '$':
            child = self.children[0]
          elif isinstance(self.children[0], ParseTree) and \
               self.children[0].isNud and \
               not self.children[0].isPrefix and \
               not self.isInfix and \
               not self.children[0].isInfix: # implies .isExpr
            if idx < len(self.children[0].children):
              child = self.children[0].children[idx]
            else:
              index = idx - len(self.children[0].children) + 1
              child = self.children[index]
          else:
            child = self.children[idx]
          if isinstance(child, ParseTree):
            parameters[name] = child.toAst()
          elif isinstance(child, list):
            parameters[name] = [x.toAst() for x in child]
          else:
            parameters[name] = child
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
class AstPrettyPrintable(Ast):
  def __init__(self, ast, tokenFormat='type'):
    self.__dict__.update(locals())
  def getAttr(self, attr):
    return self.ast.getAttr(attr)
  def __str__(self):
    return self._prettyPrint(self.ast, 0)
  def _prettyPrint(self, ast, indent = 0):
    indentStr = ''.join([' ' for x in range(indent)])
    if isinstance(ast, Ast):
      string = '%s(%s:\n' % (indentStr, ast.name)
      string += ',\n'.join([ \
        '%s  %s=%s' % (indentStr, name, self._prettyPrint(value, indent + 2).lstrip()) for name, value in ast.attributes.items() \
      ])
      string += '\n%s)' % (indentStr)
      return string
    elif isinstance(ast, list):
      if len(ast) == 0:
        return '%s[]' % (indentStr)
      string = '%s[\n' % (indentStr)
      string += ',\n'.join([self._prettyPrint(element, indent + 2) for element in ast])
      string += '\n%s]' % (indentStr)
      return string
    elif isinstance(ast, Terminal):
      return '%s%s' % (indentStr, ast.toString(self.tokenFormat))
    else:
      return '%s%s' % (indentStr, ast)
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
      'translation_unit': self._TRANSLATION_UNIT,
    }
  TERMINAL__BOOL = 53
  TERMINAL__COMPLEX = 0
  TERMINAL__IMAGINARY = 24
  TERMINAL_ADD = 25
  TERMINAL_ADDEQ = 72
  TERMINAL_AMPERSAND = 26
  TERMINAL_AND = 98
  TERMINAL_ARROW = 36
  TERMINAL_ASSIGN = 33
  TERMINAL_AUTO = 112
  TERMINAL_BITAND = 4
  TERMINAL_BITANDEQ = 97
  TERMINAL_BITNOT = 59
  TERMINAL_BITOR = 57
  TERMINAL_BITOREQ = 81
  TERMINAL_BITXOR = 66
  TERMINAL_BITXOREQ = 69
  TERMINAL_BOOL = 70
  TERMINAL_BREAK = 1
  TERMINAL_CASE = 9
  TERMINAL_CHAR = 103
  TERMINAL_CHARACTER_CONSTANT = 108
  TERMINAL_COLON = 40
  TERMINAL_COMMA = 51
  TERMINAL_COMPLEX = 84
  TERMINAL_CONST = 28
  TERMINAL_CONTINUE = 31
  TERMINAL_CSOURCE = 56
  TERMINAL_DECIMAL_FLOATING_CONSTANT = 39
  TERMINAL_DECR = 82
  TERMINAL_DEFAULT = 37
  TERMINAL_DEFINE = 111
  TERMINAL_DEFINE_FUNCTION = 12
  TERMINAL_DEFINED = 91
  TERMINAL_DEFINED_SEPARATOR = 80
  TERMINAL_DIV = 114
  TERMINAL_DIVEQ = 17
  TERMINAL_DO = 44
  TERMINAL_DOT = 115
  TERMINAL_DOUBLE = 87
  TERMINAL_ELIF = 19
  TERMINAL_ELIPSIS = 27
  TERMINAL_ELSE = 52
  TERMINAL_ENDIF = 104
  TERMINAL_ENUM = 61
  TERMINAL_EQ = 83
  TERMINAL_ERROR = 94
  TERMINAL_EXCLAMATION_POINT = 119
  TERMINAL_EXTERN = 90
  TERMINAL_FLOAT = 78
  TERMINAL_FOR = 105
  TERMINAL_GOTO = 96
  TERMINAL_GT = 100
  TERMINAL_GTEQ = 99
  TERMINAL_HEADER_GLOBAL = 68
  TERMINAL_HEADER_LOCAL = 7
  TERMINAL_HEADER_NAME = 64
  TERMINAL_HEXADECIMAL_FLOATING_CONSTANT = 74
  TERMINAL_IDENTIFIER = 34
  TERMINAL_IF = 5
  TERMINAL_IFDEF = 101
  TERMINAL_IFNDEF = 85
  TERMINAL_IMAGINARY = 60
  TERMINAL_INCLUDE = 67
  TERMINAL_INCR = 10
  TERMINAL_INLINE = 110
  TERMINAL_INT = 118
  TERMINAL_INTEGER_CONSTANT = 38
  TERMINAL_LBRACE = 49
  TERMINAL_LINE = 13
  TERMINAL_LONG = 8
  TERMINAL_LPAREN = 88
  TERMINAL_LPAREN_CAST = 47
  TERMINAL_LSHIFT = 6
  TERMINAL_LSHIFTEQ = 106
  TERMINAL_LSQUARE = 63
  TERMINAL_LT = 117
  TERMINAL_LTEQ = 92
  TERMINAL_MOD = 21
  TERMINAL_MODEQ = 54
  TERMINAL_MUL = 65
  TERMINAL_MULEQ = 62
  TERMINAL_NEQ = 75
  TERMINAL_NOT = 77
  TERMINAL_NUMBER = 23
  TERMINAL_OR = 50
  TERMINAL_POUND = 46
  TERMINAL_POUNDPOUND = 11
  TERMINAL_PP_NUMBER = 20
  TERMINAL_PRAGMA = 86
  TERMINAL_QUESTIONMARK = 76
  TERMINAL_RBRACE = 55
  TERMINAL_REGISTER = 16
  TERMINAL_RESTRICT = 22
  TERMINAL_RETURN = 29
  TERMINAL_RPAREN = 89
  TERMINAL_RSHIFT = 14
  TERMINAL_RSHIFTEQ = 113
  TERMINAL_RSQUARE = 73
  TERMINAL_SEMI = 35
  TERMINAL_SEPARATOR = 41
  TERMINAL_SHORT = 107
  TERMINAL_SIGNED = 42
  TERMINAL_SIZEOF = 48
  TERMINAL_STATIC = 2
  TERMINAL_STRING_LITERAL = 116
  TERMINAL_STRUCT = 45
  TERMINAL_SUB = 30
  TERMINAL_SUBEQ = 3
  TERMINAL_SWITCH = 71
  TERMINAL_TILDE = 43
  TERMINAL_TYPEDEF = 18
  TERMINAL_UNDEF = 79
  TERMINAL_UNION = 109
  TERMINAL_UNIVERSAL_CHARACTER_NAME = 95
  TERMINAL_UNSIGNED = 93
  TERMINAL_VOID = 32
  TERMINAL_VOLATILE = 58
  TERMINAL_WARNING = 102
  TERMINAL_WHILE = 15
  terminal_str = {
    53: '_bool',
    0: '_complex',
    24: '_imaginary',
    25: 'add',
    72: 'addeq',
    26: 'ampersand',
    98: 'and',
    36: 'arrow',
    33: 'assign',
    112: 'auto',
    4: 'bitand',
    97: 'bitandeq',
    59: 'bitnot',
    57: 'bitor',
    81: 'bitoreq',
    66: 'bitxor',
    69: 'bitxoreq',
    70: 'bool',
    1: 'break',
    9: 'case',
    103: 'char',
    108: 'character_constant',
    40: 'colon',
    51: 'comma',
    84: 'complex',
    28: 'const',
    31: 'continue',
    56: 'csource',
    39: 'decimal_floating_constant',
    82: 'decr',
    37: 'default',
    111: 'define',
    12: 'define_function',
    91: 'defined',
    80: 'defined_separator',
    114: 'div',
    17: 'diveq',
    44: 'do',
    115: 'dot',
    87: 'double',
    19: 'elif',
    27: 'elipsis',
    52: 'else',
    104: 'endif',
    61: 'enum',
    83: 'eq',
    94: 'error',
    119: 'exclamation_point',
    90: 'extern',
    78: 'float',
    105: 'for',
    96: 'goto',
    100: 'gt',
    99: 'gteq',
    68: 'header_global',
    7: 'header_local',
    64: 'header_name',
    74: 'hexadecimal_floating_constant',
    34: 'identifier',
    5: 'if',
    101: 'ifdef',
    85: 'ifndef',
    60: 'imaginary',
    67: 'include',
    10: 'incr',
    110: 'inline',
    118: 'int',
    38: 'integer_constant',
    49: 'lbrace',
    13: 'line',
    8: 'long',
    88: 'lparen',
    47: 'lparen_cast',
    6: 'lshift',
    106: 'lshifteq',
    63: 'lsquare',
    117: 'lt',
    92: 'lteq',
    21: 'mod',
    54: 'modeq',
    65: 'mul',
    62: 'muleq',
    75: 'neq',
    77: 'not',
    23: 'number',
    50: 'or',
    46: 'pound',
    11: 'poundpound',
    20: 'pp_number',
    86: 'pragma',
    76: 'questionmark',
    55: 'rbrace',
    16: 'register',
    22: 'restrict',
    29: 'return',
    89: 'rparen',
    14: 'rshift',
    113: 'rshifteq',
    73: 'rsquare',
    35: 'semi',
    41: 'separator',
    107: 'short',
    42: 'signed',
    48: 'sizeof',
    2: 'static',
    116: 'string_literal',
    45: 'struct',
    30: 'sub',
    3: 'subeq',
    71: 'switch',
    43: 'tilde',
    18: 'typedef',
    79: 'undef',
    109: 'union',
    95: 'universal_character_name',
    93: 'unsigned',
    32: 'void',
    58: 'volatile',
    102: 'warning',
    15: 'while',
  }
  nonterminal_str = {
    164: '_direct_declarator',
    121: '_expr',
    159: '_gen0',
    147: '_gen1',
    134: '_gen2',
    156: '_gen3',
    125: '_gen4',
    126: '_gen5',
    150: '_gen6',
    142: '_gen7',
    151: '_gen8',
    143: '_gen9',
    162: 'comma_opt',
    144: 'constant',
    137: 'control_line',
    131: 'define_func_param',
    158: 'define_line',
    124: 'defined_identifier',
    120: 'elipsis_opt',
    138: 'else_part',
    160: 'elseif_part',
    122: 'error_line',
    163: 'identifier',
    161: 'if_part',
    139: 'if_section',
    153: 'include_line',
    149: 'include_type',
    133: 'initilizer_list_item',
    148: 'keyword',
    141: 'line_line',
    155: 'pp',
    152: 'pp_directive',
    136: 'pp_file',
    128: 'pp_nodes',
    140: 'pp_nodes_list',
    132: 'pp_tokens',
    129: 'pragma_line',
    146: 'punctuator',
    165: 'replacement_list',
    157: 'terminals',
    154: 'token',
    145: 'translation_unit',
    123: 'type_name',
    127: 'type_qualifier',
    135: 'undef_line',
    130: 'warning_line',
  }
  str_terminal = {
    '_bool': 53,
    '_complex': 0,
    '_imaginary': 24,
    'add': 25,
    'addeq': 72,
    'ampersand': 26,
    'and': 98,
    'arrow': 36,
    'assign': 33,
    'auto': 112,
    'bitand': 4,
    'bitandeq': 97,
    'bitnot': 59,
    'bitor': 57,
    'bitoreq': 81,
    'bitxor': 66,
    'bitxoreq': 69,
    'bool': 70,
    'break': 1,
    'case': 9,
    'char': 103,
    'character_constant': 108,
    'colon': 40,
    'comma': 51,
    'complex': 84,
    'const': 28,
    'continue': 31,
    'csource': 56,
    'decimal_floating_constant': 39,
    'decr': 82,
    'default': 37,
    'define': 111,
    'define_function': 12,
    'defined': 91,
    'defined_separator': 80,
    'div': 114,
    'diveq': 17,
    'do': 44,
    'dot': 115,
    'double': 87,
    'elif': 19,
    'elipsis': 27,
    'else': 52,
    'endif': 104,
    'enum': 61,
    'eq': 83,
    'error': 94,
    'exclamation_point': 119,
    'extern': 90,
    'float': 78,
    'for': 105,
    'goto': 96,
    'gt': 100,
    'gteq': 99,
    'header_global': 68,
    'header_local': 7,
    'header_name': 64,
    'hexadecimal_floating_constant': 74,
    'identifier': 34,
    'if': 5,
    'ifdef': 101,
    'ifndef': 85,
    'imaginary': 60,
    'include': 67,
    'incr': 10,
    'inline': 110,
    'int': 118,
    'integer_constant': 38,
    'lbrace': 49,
    'line': 13,
    'long': 8,
    'lparen': 88,
    'lparen_cast': 47,
    'lshift': 6,
    'lshifteq': 106,
    'lsquare': 63,
    'lt': 117,
    'lteq': 92,
    'mod': 21,
    'modeq': 54,
    'mul': 65,
    'muleq': 62,
    'neq': 75,
    'not': 77,
    'number': 23,
    'or': 50,
    'pound': 46,
    'poundpound': 11,
    'pp_number': 20,
    'pragma': 86,
    'questionmark': 76,
    'rbrace': 55,
    'register': 16,
    'restrict': 22,
    'return': 29,
    'rparen': 89,
    'rshift': 14,
    'rshifteq': 113,
    'rsquare': 73,
    'semi': 35,
    'separator': 41,
    'short': 107,
    'signed': 42,
    'sizeof': 48,
    'static': 2,
    'string_literal': 116,
    'struct': 45,
    'sub': 30,
    'subeq': 3,
    'switch': 71,
    'tilde': 43,
    'typedef': 18,
    'undef': 79,
    'union': 109,
    'universal_character_name': 95,
    'unsigned': 93,
    'void': 32,
    'volatile': 58,
    'warning': 102,
    'while': 15,
  }
  str_nonterminal = {
    '_direct_declarator': 164,
    '_expr': 121,
    '_gen0': 159,
    '_gen1': 147,
    '_gen2': 134,
    '_gen3': 156,
    '_gen4': 125,
    '_gen5': 126,
    '_gen6': 150,
    '_gen7': 142,
    '_gen8': 151,
    '_gen9': 143,
    'comma_opt': 162,
    'constant': 144,
    'control_line': 137,
    'define_func_param': 131,
    'define_line': 158,
    'defined_identifier': 124,
    'elipsis_opt': 120,
    'else_part': 138,
    'elseif_part': 160,
    'error_line': 122,
    'identifier': 163,
    'if_part': 161,
    'if_section': 139,
    'include_line': 153,
    'include_type': 149,
    'initilizer_list_item': 133,
    'keyword': 148,
    'line_line': 141,
    'pp': 155,
    'pp_directive': 152,
    'pp_file': 136,
    'pp_nodes': 128,
    'pp_nodes_list': 140,
    'pp_tokens': 132,
    'pragma_line': 129,
    'punctuator': 146,
    'replacement_list': 165,
    'terminals': 157,
    'token': 154,
    'translation_unit': 145,
    'type_name': 123,
    'type_qualifier': 127,
    'undef_line': 135,
    'warning_line': 130,
  }
  terminal_count = 120
  nonterminal_count = 46
  parse_table = [
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, 14, -1, -1, 91, -1, -1, -1, 40, 140, -1, -1, 83, -1, -1, -1, -1, -1, -1, 98, -1, -1, -1, 175, 43, 113, -1, -1, 73, -1, -1, 101, -1, 86, 93, -1, -1, -1, 122, -1, -1, 50, -1, -1, 1, -1, -1, 78, 49, 166, -1, -1, 62, 66, -1, 81, -1, -1, -1, -1, 80, 154, -1, 115, 7, -1, -1, 192, -1, -1, 151, 156, -1, 111, 157, -1, -1, -1, -1, 15, 106, 125, -1, -1, -1, -1, 131, 16, -1, -1, 85, -1, -1, -1, -1, 87, 64, 25, 172, -1, -1, -1, -1, -1, 92, -1, -1, -1, -1, -1, -1, 171, 44, 112, -1, 130, -1, 35],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [4, 118, 180, -1, -1, 19, -1, -1, 27, 79, -1, -1, -1, -1, -1, 20, 67, -1, 119, -1, -1, -1, 89, -1, 152, -1, -1, -1, 74, 82, -1, 32, 179, -1, -1, -1, -1, 53, -1, -1, -1, -1, 205, -1, 75, 193, -1, -1, 203, -1, -1, -1, 59, 41, -1, -1, -1, -1, 2, -1, -1, 124, -1, -1, -1, -1, -1, -1, -1, -1, -1, 158, -1, -1, -1, -1, -1, -1, 109, -1, -1, -1, -1, -1, -1, -1, -1, 121, -1, -1, 23, -1, -1, 11, -1, -1, 99, -1, -1, -1, -1, -1, -1, 42, -1, 206, -1, 128, -1, 149, 139, -1, 104, -1, -1, -1, -1, -1, 36, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 133, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [46, 46, 46, 108, -1, 46, 108, -1, 46, 46, 108, 108, -1, -1, 108, 46, 46, -1, 46, -1, 3, 108, 46, -1, 46, 108, 108, 108, 46, 46, 108, 46, 46, 108, 159, 108, 108, 46, -1, -1, 108, -1, 46, 108, 46, 46, 108, -1, 46, 108, 108, 108, 46, 46, 108, 108, -1, 108, 46, -1, -1, 46, 108, 108, -1, 108, 108, -1, -1, 108, -1, 46, 108, 108, -1, 108, 108, -1, 46, -1, -1, 108, 108, 108, -1, -1, -1, 46, 108, 108, 46, -1, 108, 46, -1, -1, 46, 108, 108, 108, 108, -1, -1, 46, -1, 46, 108, 46, -1, 46, 46, -1, 46, 108, 108, 108, 5, 108, 46, 108],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 161, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 174, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 141, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, 117, 56, 24, 48, 12, 165, -1, 10, 132, 188, 26, -1, -1, 54, 120, 168, 58, 45, -1, -1, 146, 8, 34, -1, 135, -1, 150, 181, 198, 72, 33, 136, 183, 127, 28, 123, 204, 103, 195, 6, -1, 160, 22, 9, 177, 102, -1, 126, 18, 37, 96, 197, -1, 68, 107, -1, 114, 105, -1, 52, 88, 189, 21, 29, 194, 143, -1, -1, 145, 38, 202, 116, 178, 84, 47, 169, 138, 94, -1, -1, 163, 61, 182, 153, -1, -1, 51, 13, 142, 65, -1, 63, 76, -1, 148, 129, 167, 39, 90, 147, -1, -1, 155, -1, 30, 17, 170, 164, 57, 199, -1, 187, 31, 191, 0, 208, 110, 71, 144],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1]
  ]
  def terminal(self, str):
    return self.str_terminal[str]
  def terminalNames(self):
    return list(self.str_terminal.keys())
  def isTerminal(self, id):
    return 0 <= id <= 119
  def isNonTerminal(self, id):
    return 120 <= id <= 165
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
    return self.parse_table[n - 120][self.sym.getId()]
  def call(self, nt_str):
    return getattr(self, nt_str)()
  def __DIRECT_DECLARATOR(self, depth = 0):
    rule = self.rule(164)
    if depth is not False:
      tracer = DebugTracer("__DIRECT_DECLARATOR", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(164, self.getAtomString(164)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def __GEN0(self, depth = 0):
    rule = self.rule(159)
    if depth is not False:
      tracer = DebugTracer("__GEN0", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(159, self.getAtomString(159)), tracer )
    tree.list = 'tlist'
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 69:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PP_NODES(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(41, tracer) ) # separator
      subtree = self.__GEN0(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN1(self, depth = 0):
    rule = self.rule(147)
    if depth is not False:
      tracer = DebugTracer("__GEN1", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(147, self.getAtomString(147)), tracer )
    tree.list = 'nlist'
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 185:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._ELSEIF_PART(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN1(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN2(self, depth = 0):
    rule = self.rule(134)
    if depth is not False:
      tracer = DebugTracer("__GEN2", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(134, self.getAtomString(134)), tracer )
    tree.list = 'slist'
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 100:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DEFINE_FUNC_PARAM(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN3(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN3(self, depth = 0):
    rule = self.rule(156)
    if depth is not False:
      tracer = DebugTracer("__GEN3", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(156, self.getAtomString(156)), tracer )
    tree.list = 'slist'
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 141:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(51, tracer) ) # comma
      subtree = self._DEFINE_FUNC_PARAM(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN3(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN4(self, depth = 0):
    rule = self.rule(125)
    if depth is not False:
      tracer = DebugTracer("__GEN4", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(125, self.getAtomString(125)), tracer )
    tree.list = 'nlist'
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 134:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PP_TOKENS(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN4(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN5(self, depth = 0):
    rule = self.rule(126)
    if depth is not False:
      tracer = DebugTracer("__GEN5", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(126, self.getAtomString(126)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def __GEN6(self, depth = 0):
    rule = self.rule(150)
    if depth is not False:
      tracer = DebugTracer("__GEN6", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(150, self.getAtomString(150)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def __GEN7(self, depth = 0):
    rule = self.rule(142)
    if depth is not False:
      tracer = DebugTracer("__GEN7", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(142, self.getAtomString(142)), tracer )
    tree.list = 'slist'
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 95:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._INITILIZER_LIST_ITEM(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN8(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN8(self, depth = 0):
    rule = self.rule(151)
    if depth is not False:
      tracer = DebugTracer("__GEN8", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(151, self.getAtomString(151)), tracer )
    tree.list = 'slist'
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 133:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(51, tracer) ) # comma
      subtree = self._INITILIZER_LIST_ITEM(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN8(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN9(self, depth = 0):
    rule = self.rule(143)
    if depth is not False:
      tracer = DebugTracer("__GEN9", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(143, self.getAtomString(143)), tracer )
    tree.list = 'nlist'
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 173:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._TYPE_QUALIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN9(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _COMMA_OPT(self, depth = 0):
    rule = self.rule(162)
    if depth is not False:
      tracer = DebugTracer("_COMMA_OPT", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(162, self.getAtomString(162)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _CONSTANT(self, depth = 0):
    rule = self.rule(144)
    if depth is not False:
      tracer = DebugTracer("_CONSTANT", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(144, self.getAtomString(144)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _CONTROL_LINE(self, depth = 0):
    rule = self.rule(137)
    if depth is not False:
      tracer = DebugTracer("_CONTROL_LINE", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(137, self.getAtomString(137)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _DEFINE_FUNC_PARAM(self, depth = 0):
    rule = self.rule(131)
    if depth is not False:
      tracer = DebugTracer("_DEFINE_FUNC_PARAM", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(131, self.getAtomString(131)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _DEFINE_LINE(self, depth = 0):
    rule = self.rule(158)
    if depth is not False:
      tracer = DebugTracer("_DEFINE_LINE", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(158, self.getAtomString(158)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _DEFINED_IDENTIFIER(self, depth = 0):
    rule = self.rule(124)
    if depth is not False:
      tracer = DebugTracer("_DEFINED_IDENTIFIER", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(124, self.getAtomString(124)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _ELIPSIS_OPT(self, depth = 0):
    rule = self.rule(120)
    if depth is not False:
      tracer = DebugTracer("_ELIPSIS_OPT", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(120, self.getAtomString(120)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _ELSE_PART(self, depth = 0):
    rule = self.rule(138)
    if depth is not False:
      tracer = DebugTracer("_ELSE_PART", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(138, self.getAtomString(138)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _ELSEIF_PART(self, depth = 0):
    rule = self.rule(160)
    if depth is not False:
      tracer = DebugTracer("_ELSEIF_PART", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(160, self.getAtomString(160)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _ERROR_LINE(self, depth = 0):
    rule = self.rule(122)
    if depth is not False:
      tracer = DebugTracer("_ERROR_LINE", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(122, self.getAtomString(122)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _IDENTIFIER(self, depth = 0):
    rule = self.rule(163)
    if depth is not False:
      tracer = DebugTracer("_IDENTIFIER", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(163, self.getAtomString(163)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _IF_PART(self, depth = 0):
    rule = self.rule(161)
    if depth is not False:
      tracer = DebugTracer("_IF_PART", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(161, self.getAtomString(161)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _IF_SECTION(self, depth = 0):
    rule = self.rule(139)
    if depth is not False:
      tracer = DebugTracer("_IF_SECTION", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(139, self.getAtomString(139)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _INCLUDE_LINE(self, depth = 0):
    rule = self.rule(153)
    if depth is not False:
      tracer = DebugTracer("_INCLUDE_LINE", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(153, self.getAtomString(153)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _INCLUDE_TYPE(self, depth = 0):
    rule = self.rule(149)
    if depth is not False:
      tracer = DebugTracer("_INCLUDE_TYPE", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(149, self.getAtomString(149)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _INITILIZER_LIST_ITEM(self, depth = 0):
    rule = self.rule(133)
    if depth is not False:
      tracer = DebugTracer("_INITILIZER_LIST_ITEM", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(133, self.getAtomString(133)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _KEYWORD(self, depth = 0):
    rule = self.rule(148)
    if depth is not False:
      tracer = DebugTracer("_KEYWORD", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(148, self.getAtomString(148)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 2:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(58, tracer) ) # volatile
      return tree
    elif rule == 4:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(0, tracer) ) # _complex
      return tree
    elif rule == 11:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(93, tracer) ) # unsigned
      return tree
    elif rule == 19:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(5, tracer) ) # if
      return tree
    elif rule == 20:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(15, tracer) ) # while
      return tree
    elif rule == 23:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(90, tracer) ) # extern
      return tree
    elif rule == 27:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(8, tracer) ) # long
      return tree
    elif rule == 32:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(31, tracer) ) # continue
      return tree
    elif rule == 36:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(118, tracer) ) # int
      return tree
    elif rule == 41:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(53, tracer) ) # _bool
      return tree
    elif rule == 42:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(103, tracer) ) # char
      return tree
    elif rule == 53:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(37, tracer) ) # default
      return tree
    elif rule == 59:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(52, tracer) ) # else
      return tree
    elif rule == 67:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(16, tracer) ) # register
      return tree
    elif rule == 74:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(28, tracer) ) # const
      return tree
    elif rule == 75:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(44, tracer) ) # do
      return tree
    elif rule == 79:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(9, tracer) ) # case
      return tree
    elif rule == 82:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(29, tracer) ) # return
      return tree
    elif rule == 89:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(22, tracer) ) # restrict
      return tree
    elif rule == 99:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(96, tracer) ) # goto
      return tree
    elif rule == 104:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(112, tracer) ) # auto
      return tree
    elif rule == 109:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(78, tracer) ) # float
      return tree
    elif rule == 118:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(1, tracer) ) # break
      return tree
    elif rule == 119:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(18, tracer) ) # typedef
      return tree
    elif rule == 121:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(87, tracer) ) # double
      return tree
    elif rule == 124:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(61, tracer) ) # enum
      return tree
    elif rule == 128:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(107, tracer) ) # short
      return tree
    elif rule == 139:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(110, tracer) ) # inline
      return tree
    elif rule == 149:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(109, tracer) ) # union
      return tree
    elif rule == 152:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(24, tracer) ) # _imaginary
      return tree
    elif rule == 158:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(71, tracer) ) # switch
      return tree
    elif rule == 179:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(32, tracer) ) # void
      return tree
    elif rule == 180:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(2, tracer) ) # static
      return tree
    elif rule == 193:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(45, tracer) ) # struct
      return tree
    elif rule == 203:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(48, tracer) ) # sizeof
      return tree
    elif rule == 205:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(42, tracer) ) # signed
      return tree
    elif rule == 206:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(105, tracer) ) # for
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _LINE_LINE(self, depth = 0):
    rule = self.rule(141)
    if depth is not False:
      tracer = DebugTracer("_LINE_LINE", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(141, self.getAtomString(141)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _PP(self, depth = 0):
    rule = self.rule(155)
    if depth is not False:
      tracer = DebugTracer("_PP", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(155, self.getAtomString(155)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 161:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(80, tracer) ) # defined_separator
      return tree
    elif rule == 174:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(91, tracer) ) # defined
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _PP_DIRECTIVE(self, depth = 0):
    rule = self.rule(152)
    if depth is not False:
      tracer = DebugTracer("_PP_DIRECTIVE", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(152, self.getAtomString(152)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _PP_FILE(self, depth = 0):
    rule = self.rule(136)
    if depth is not False:
      tracer = DebugTracer("_PP_FILE", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(136, self.getAtomString(136)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _PP_NODES(self, depth = 0):
    rule = self.rule(128)
    if depth is not False:
      tracer = DebugTracer("_PP_NODES", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(128, self.getAtomString(128)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _PP_NODES_LIST(self, depth = 0):
    rule = self.rule(140)
    if depth is not False:
      tracer = DebugTracer("_PP_NODES_LIST", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(140, self.getAtomString(140)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _PP_TOKENS(self, depth = 0):
    rule = self.rule(132)
    if depth is not False:
      tracer = DebugTracer("_PP_TOKENS", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(132, self.getAtomString(132)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _PRAGMA_LINE(self, depth = 0):
    rule = self.rule(129)
    if depth is not False:
      tracer = DebugTracer("_PRAGMA_LINE", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(129, self.getAtomString(129)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _PUNCTUATOR(self, depth = 0):
    rule = self.rule(146)
    if depth is not False:
      tracer = DebugTracer("_PUNCTUATOR", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(146, self.getAtomString(146)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 1:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(46, tracer) ) # pound
      return tree
    elif rule == 7:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(66, tracer) ) # bitxor
      return tree
    elif rule == 14:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(3, tracer) ) # subeq
      return tree
    elif rule == 15:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(81, tracer) ) # bitoreq
      return tree
    elif rule == 16:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(89, tracer) ) # rparen
      return tree
    elif rule == 25:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(99, tracer) ) # gteq
      return tree
    elif rule == 35:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(119, tracer) ) # exclamation_point
      return tree
    elif rule == 40:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(10, tracer) ) # incr
      return tree
    elif rule == 43:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(26, tracer) ) # ampersand
      return tree
    elif rule == 44:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(114, tracer) ) # div
      return tree
    elif rule == 49:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(50, tracer) ) # or
      return tree
    elif rule == 50:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(43, tracer) ) # tilde
      return tree
    elif rule == 62:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(54, tracer) ) # modeq
      return tree
    elif rule == 64:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(98, tracer) ) # and
      return tree
    elif rule == 66:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(55, tracer) ) # rbrace
      return tree
    elif rule == 73:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(30, tracer) ) # sub
      return tree
    elif rule == 78:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(49, tracer) ) # lbrace
      return tree
    elif rule == 80:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(62, tracer) ) # muleq
      return tree
    elif rule == 81:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(57, tracer) ) # bitor
      return tree
    elif rule == 83:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(14, tracer) ) # rshift
      return tree
    elif rule == 85:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(92, tracer) ) # lteq
      return tree
    elif rule == 86:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(35, tracer) ) # semi
      return tree
    elif rule == 87:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(97, tracer) ) # bitandeq
      return tree
    elif rule == 91:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(6, tracer) ) # lshift
      return tree
    elif rule == 92:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(106, tracer) ) # lshifteq
      return tree
    elif rule == 93:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(36, tracer) ) # arrow
      return tree
    elif rule == 98:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(21, tracer) ) # mod
      return tree
    elif rule == 101:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(33, tracer) ) # assign
      return tree
    elif rule == 106:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(82, tracer) ) # decr
      return tree
    elif rule == 111:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(75, tracer) ) # neq
      return tree
    elif rule == 112:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(115, tracer) ) # dot
      return tree
    elif rule == 113:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(27, tracer) ) # elipsis
      return tree
    elif rule == 115:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(65, tracer) ) # mul
      return tree
    elif rule == 122:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(40, tracer) ) # colon
      return tree
    elif rule == 125:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(83, tracer) ) # eq
      return tree
    elif rule == 130:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(117, tracer) ) # lt
      return tree
    elif rule == 131:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(88, tracer) ) # lparen
      return tree
    elif rule == 140:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(11, tracer) ) # poundpound
      return tree
    elif rule == 151:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(72, tracer) ) # addeq
      return tree
    elif rule == 154:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(63, tracer) ) # lsquare
      return tree
    elif rule == 156:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(73, tracer) ) # rsquare
      return tree
    elif rule == 157:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(76, tracer) ) # questionmark
      return tree
    elif rule == 166:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(51, tracer) ) # comma
      return tree
    elif rule == 171:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(113, tracer) ) # rshifteq
      return tree
    elif rule == 172:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(100, tracer) ) # gt
      return tree
    elif rule == 175:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(25, tracer) ) # add
      return tree
    elif rule == 192:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(69, tracer) ) # bitxoreq
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _REPLACEMENT_LIST(self, depth = 0):
    rule = self.rule(165)
    if depth is not False:
      tracer = DebugTracer("_REPLACEMENT_LIST", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(165, self.getAtomString(165)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _TERMINALS(self, depth = 0):
    rule = self.rule(157)
    if depth is not False:
      tracer = DebugTracer("_TERMINALS", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(157, self.getAtomString(157)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 0:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(115, tracer) ) # dot
      return tree
    elif rule == 6:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(40, tracer) ) # colon
      return tree
    elif rule == 8:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(22, tracer) ) # restrict
      return tree
    elif rule == 9:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(44, tracer) ) # do
      return tree
    elif rule == 10:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(8, tracer) ) # long
      return tree
    elif rule == 12:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(5, tracer) ) # if
      return tree
    elif rule == 13:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(88, tracer) ) # lparen
      return tree
    elif rule == 17:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(106, tracer) ) # lshifteq
      return tree
    elif rule == 18:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(49, tracer) ) # lbrace
      return tree
    elif rule == 21:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(63, tracer) ) # lsquare
      return tree
    elif rule == 22:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(43, tracer) ) # tilde
      return tree
    elif rule == 24:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(3, tracer) ) # subeq
      return tree
    elif rule == 26:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(11, tracer) ) # poundpound
      return tree
    elif rule == 28:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(35, tracer) ) # semi
      return tree
    elif rule == 29:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(64, tracer) ) # header_name
      return tree
    elif rule == 30:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(105, tracer) ) # for
      return tree
    elif rule == 31:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(113, tracer) ) # rshifteq
      return tree
    elif rule == 33:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(31, tracer) ) # continue
      return tree
    elif rule == 34:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(23, tracer) ) # number
      return tree
    elif rule == 37:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(50, tracer) ) # or
      return tree
    elif rule == 38:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(70, tracer) ) # bool
      return tree
    elif rule == 39:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(98, tracer) ) # and
      return tree
    elif rule == 45:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(18, tracer) ) # typedef
      return tree
    elif rule == 47:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(75, tracer) ) # neq
      return tree
    elif rule == 48:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(4, tracer) ) # bitand
      return tree
    elif rule == 51:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(87, tracer) ) # double
      return tree
    elif rule == 52:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(60, tracer) ) # imaginary
      return tree
    elif rule == 54:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(14, tracer) ) # rshift
      return tree
    elif rule == 56:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(2, tracer) ) # static
      return tree
    elif rule == 57:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(109, tracer) ) # union
      return tree
    elif rule == 58:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(17, tracer) ) # diveq
      return tree
    elif rule == 61:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(82, tracer) ) # decr
      return tree
    elif rule == 63:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(92, tracer) ) # lteq
      return tree
    elif rule == 65:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(90, tracer) ) # extern
      return tree
    elif rule == 68:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(54, tracer) ) # modeq
      return tree
    elif rule == 70:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(11, tracer) ) # poundpound
      return tree
    elif rule == 71:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(118, tracer) ) # int
      return tree
    elif rule == 72:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(30, tracer) ) # sub
      return tree
    elif rule == 76:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(93, tracer) ) # unsigned
      return tree
    elif rule == 84:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(74, tracer) ) # hexadecimal_floating_constant
      return tree
    elif rule == 88:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(61, tracer) ) # enum
      return tree
    elif rule == 90:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(99, tracer) ) # gteq
      return tree
    elif rule == 94:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(78, tracer) ) # float
      return tree
    elif rule == 96:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(51, tracer) ) # comma
      return tree
    elif rule == 102:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(46, tracer) ) # pound
      return tree
    elif rule == 103:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(38, tracer) ) # integer_constant
      return tree
    elif rule == 105:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(58, tracer) ) # volatile
      return tree
    elif rule == 107:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(55, tracer) ) # rbrace
      return tree
    elif rule == 110:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(117, tracer) ) # lt
      return tree
    elif rule == 114:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(57, tracer) ) # bitor
      return tree
    elif rule == 116:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(72, tracer) ) # addeq
      return tree
    elif rule == 117:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(1, tracer) ) # break
      return tree
    elif rule == 120:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(15, tracer) ) # while
      return tree
    elif rule == 123:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(36, tracer) ) # arrow
      return tree
    elif rule == 126:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(48, tracer) ) # sizeof
      return tree
    elif rule == 127:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(34, tracer) ) # identifier
      return tree
    elif rule == 129:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(96, tracer) ) # goto
      return tree
    elif rule == 132:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(9, tracer) ) # case
      return tree
    elif rule == 135:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(25, tracer) ) # add
      return tree
    elif rule == 136:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(32, tracer) ) # void
      return tree
    elif rule == 137:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(46, tracer) ) # pound
      return tree
    elif rule == 138:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(77, tracer) ) # not
      return tree
    elif rule == 142:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(89, tracer) ) # rparen
      return tree
    elif rule == 143:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(66, tracer) ) # bitxor
      return tree
    elif rule == 144:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(119, tracer) ) # exclamation_point
      return tree
    elif rule == 145:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(69, tracer) ) # bitxoreq
      return tree
    elif rule == 146:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(21, tracer) ) # mod
      return tree
    elif rule == 147:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(100, tracer) ) # gt
      return tree
    elif rule == 148:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(95, tracer) ) # universal_character_name
      return tree
    elif rule == 150:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(27, tracer) ) # elipsis
      return tree
    elif rule == 153:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(84, tracer) ) # complex
      return tree
    elif rule == 155:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(103, tracer) ) # char
      return tree
    elif rule == 160:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(42, tracer) ) # signed
      return tree
    elif rule == 163:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(81, tracer) ) # bitoreq
      return tree
    elif rule == 164:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(108, tracer) ) # character_constant
      return tree
    elif rule == 165:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(6, tracer) ) # lshift
      return tree
    elif rule == 167:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(97, tracer) ) # bitandeq
      return tree
    elif rule == 168:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(16, tracer) ) # register
      return tree
    elif rule == 169:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(76, tracer) ) # questionmark
      return tree
    elif rule == 170:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(107, tracer) ) # short
      return tree
    elif rule == 176:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(63, tracer) ) # lsquare
      return tree
    elif rule == 177:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(45, tracer) ) # struct
      return tree
    elif rule == 178:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(73, tracer) ) # rsquare
      return tree
    elif rule == 181:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(28, tracer) ) # const
      return tree
    elif rule == 182:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(83, tracer) ) # eq
      return tree
    elif rule == 183:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(33, tracer) ) # assign
      return tree
    elif rule == 184:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(49, tracer) ) # lbrace
      return tree
    elif rule == 187:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(112, tracer) ) # auto
      return tree
    elif rule == 188:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(10, tracer) ) # incr
      return tree
    elif rule == 189:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(62, tracer) ) # muleq
      return tree
    elif rule == 190:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(55, tracer) ) # rbrace
      return tree
    elif rule == 191:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(114, tracer) ) # div
      return tree
    elif rule == 194:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(65, tracer) ) # mul
      return tree
    elif rule == 195:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(39, tracer) ) # decimal_floating_constant
      return tree
    elif rule == 197:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(52, tracer) ) # else
      return tree
    elif rule == 198:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(29, tracer) ) # return
      return tree
    elif rule == 199:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(110, tracer) ) # inline
      return tree
    elif rule == 201:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(73, tracer) ) # rsquare
      return tree
    elif rule == 202:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(71, tracer) ) # switch
      return tree
    elif rule == 204:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(37, tracer) ) # default
      return tree
    elif rule == 208:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(116, tracer) ) # string_literal
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _TOKEN(self, depth = 0):
    rule = self.rule(154)
    if depth is not False:
      tracer = DebugTracer("_TOKEN", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(154, self.getAtomString(154)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 3:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(20, tracer) ) # pp_number
      return tree
    elif rule == 5:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(116, tracer) ) # string_literal
      return tree
    elif rule == 46:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._KEYWORD(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 60:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._CONSTANT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 108:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PUNCTUATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 159:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(34, tracer) ) # identifier
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _TRANSLATION_UNIT(self, depth = 0):
    rule = self.rule(145)
    if depth is not False:
      tracer = DebugTracer("_TRANSLATION_UNIT", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(145, self.getAtomString(145)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _TYPE_NAME(self, depth = 0):
    rule = self.rule(123)
    if depth is not False:
      tracer = DebugTracer("_TYPE_NAME", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(123, self.getAtomString(123)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _TYPE_QUALIFIER(self, depth = 0):
    rule = self.rule(127)
    if depth is not False:
      tracer = DebugTracer("_TYPE_QUALIFIER", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(127, self.getAtomString(127)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _UNDEF_LINE(self, depth = 0):
    rule = self.rule(135)
    if depth is not False:
      tracer = DebugTracer("_UNDEF_LINE", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(135, self.getAtomString(135)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _WARNING_LINE(self, depth = 0):
    rule = self.rule(130)
    if depth is not False:
      tracer = DebugTracer("_WARNING_LINE", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(130, self.getAtomString(130)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  infixBp0 = {
    3: 2000,
    4: 6000,
    6: 11000,
    10: 16000,
    14: 11000,
    17: 2000,
    21: 13000,
    25: 12000,
    30: 12000,
    33: 2000,
    36: 16000,
    49: 15000,
    50: 4000,
    51: 1000,
    54: 2000,
    57: 8000,
    62: 2000,
    63: 16000,
    65: 13000,
    66: 7000,
    69: 2000,
    72: 2000,
    75: 9000,
    76: 3000,
    81: 2000,
    82: 16000,
    83: 9000,
    88: 16000,
    92: 10000,
    97: 2000,
    98: 5000,
    99: 10000,
    100: 10000,
    106: 2000,
    113: 2000,
    114: 13000,
    115: 16000,
    117: 10000,
  }
  prefixBp0 = {
    4: 14000,
    10: 14000,
    30: 14000,
    59: 14000,
    65: 14000,
    77: 14000,
    82: 14000,
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
      left.isExpr = True
      left.isNud = True
      tracer.add(left.tracer)
    while rbp < self.binding_power(self.sym, self.infixBp0):
      left = self.led0(left, depth)
      if isinstance(left, ParseTree):
        tracer.add(left.tracer)
    if left:
      left.isExpr = True
      left.tracer = tracer
    return left
  def nud0(self, tracer):
    tree = ParseTree( NonTerminal(121, '_expr') )
    if self.sym.getId() == 82: # 'decr'
      tree.astTransform = AstTransformNodeCreator('PreDecr', {'var': 1})
      tree.add( self.expect(82, tracer) )
      tree.add( self.__EXPR( self.prefixBp0[82] ) )
      tree.isPrefix = True
    elif self.sym.getId() == 47: # 'lparen_cast'
      tree.astTransform = AstTransformNodeCreator('TypeInitializion', {'type': 0, 'initializer': 4})
      tree.add( self.expect(47, tracer) )
      tree.add( self._TYPE_NAME() )
      tree.add( self.expect(89, tracer) )
    elif self.sym.getId() == 65: # 'mul'
      tree.astTransform = AstTransformNodeCreator('Dereference', {'var': 1})
      tree.add( self.expect(65, tracer) )
      tree.add( self.__EXPR( self.prefixBp0[65] ) )
      tree.isPrefix = True
    elif self.sym.getId() == 34: # 'identifier'
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      return self.expect( 34, tracer )
    elif self.sym.getId() == 10: # 'incr'
      tree.astTransform = AstTransformNodeCreator('PreIncr', {'var': 1})
      tree.add( self.expect(10, tracer) )
      tree.add( self.__EXPR( self.prefixBp0[10] ) )
      tree.isPrefix = True
    elif self.sym.getId() == 121: # _expr
      tree.astTransform = AstTransformNodeCreator('MemberSelect', {'member': 2, 'object': 0})
      return self.expect( 121, tracer )
    elif self.sym.getId() == 48: # 'sizeof'
      tree.astTransform = AstTransformNodeCreator('SizeOfVar', {'var': 1})
      tree.add( self.expect(48, tracer) )
      tree.add( self.__EXPR() )
    elif self.sym.getId() == 116: # 'string_literal'
      tree.astTransform = AstTransformSubstitution(0)
      return self.expect( 116, tracer )
    elif self.sym.getId() == 144: # constant
      tree.astTransform = AstTransformSubstitution(0)
      return self.expect( 144, tracer )
    elif self.sym.getId() == 4: # 'bitand'
      tree.astTransform = AstTransformNodeCreator('AddressOf', {'var': 1})
      tree.add( self.expect(4, tracer) )
      tree.add( self.__EXPR( self.prefixBp0[4] ) )
      tree.isPrefix = True
    elif self.sym.getId() == 88: # 'lparen'
      tree.astTransform = AstTransformSubstitution(2)
      tree.add( self.expect(88, tracer) )
      tree.add( self.__EXPR() )
      tree.add( self.expect(89, tracer) )
    return tree
  def led0(self, left, tracer):
    tree = ParseTree( NonTerminal(121, '_expr') )
    if  self.sym.getId() == 4: # 'bitand'
      tree.astTransform = AstTransformNodeCreator('BitAND', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(4, tracer) )
      tree.add( self.__EXPR( self.infixBp0[4] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 49: # 'lbrace'
      tree.astTransform = AstTransformNodeCreator('TypeInitializion', {'type': 0, 'initializer': 4})
      if left:
        tree.add(left)
      tree.add( self.expect(49, tracer) )
      tree.add( self.__GEN7() )
      tree.add( self._COMMA_OPT() )
      tree.add( self.expect(55, tracer) )
    elif  self.sym.getId() == 92: # 'lteq'
      tree.astTransform = AstTransformNodeCreator('LessThanEq', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(92, tracer) )
      tree.add( self.__EXPR( self.infixBp0[92] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 54: # 'modeq'
      tree.astTransform = AstTransformNodeCreator('ModAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(54, tracer) )
      tree.add( self.__EXPR( self.infixBp0[54] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 3: # 'subeq'
      tree.astTransform = AstTransformNodeCreator('SubtractAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(3, tracer) )
      tree.add( self.__EXPR( self.infixBp0[3] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 57: # 'bitor'
      tree.astTransform = AstTransformNodeCreator('BitOR', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(57, tracer) )
      tree.add( self.__EXPR( self.infixBp0[57] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 88: # 'lparen'
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(88, tracer) )
      ls = AstList()
      if self.sym.getId() not in [73]:
        while 1:
          ls.append( self.__EXPR() )
          if self.sym.getId() != 51:
            break
          self.expect(51, tracer)
      tree.add( ls )
      tree.add( self.expect(89, tracer) )
    elif  self.sym.getId() == 97: # 'bitandeq'
      tree.astTransform = AstTransformNodeCreator('ANDAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(97, tracer) )
      tree.add( self.__EXPR( self.infixBp0[97] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 115: # 'dot'
      tree.astTransform = AstTransformNodeCreator('MemberSelect', {'member': 2, 'object': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(115, tracer) )
      tree.add( self.__EXPR() )
    elif  self.sym.getId() == 99: # 'gteq'
      tree.astTransform = AstTransformNodeCreator('GreaterThanEq', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(99, tracer) )
      tree.add( self.__EXPR( self.infixBp0[99] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 25: # 'add'
      tree.astTransform = AstTransformNodeCreator('Add', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(25, tracer) )
      tree.add( self.__EXPR( self.infixBp0[25] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 81: # 'bitoreq'
      tree.astTransform = AstTransformNodeCreator('ORAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(81, tracer) )
      tree.add( self.__EXPR( self.infixBp0[81] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 63: # 'lsquare'
      tree.astTransform = AstTransformNodeCreator('ArrayIndex', {'params': 2, 'name': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(63, tracer) )
      ls = AstList()
      if self.sym.getId() not in [73]:
        while 1:
          ls.append( self.__EXPR() )
          if self.sym.getId() != 51:
            break
          self.expect(51, tracer)
      tree.add( ls )
      tree.add( self.expect(73, tracer) )
    elif  self.sym.getId() == 83: # 'eq'
      tree.astTransform = AstTransformNodeCreator('Equals', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(83, tracer) )
      tree.add( self.__EXPR( self.infixBp0[83] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 36: # 'arrow'
      tree.astTransform = AstTransformNodeCreator('DerefMemberSelect', {'member': 2, 'object': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(36, tracer) )
      tree.add( self.__EXPR() )
    elif  self.sym.getId() == 65: # 'mul'
      tree.astTransform = AstTransformNodeCreator('Mul', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(65, tracer) )
      tree.add( self.__EXPR( self.infixBp0[65] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 69: # 'bitxoreq'
      tree.astTransform = AstTransformNodeCreator('XORAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(69, tracer) )
      tree.add( self.__EXPR( self.infixBp0[69] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 72: # 'addeq'
      tree.astTransform = AstTransformNodeCreator('AddAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(72, tracer) )
      tree.add( self.__EXPR( self.infixBp0[72] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 30: # 'sub'
      tree.astTransform = AstTransformNodeCreator('Sub', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(30, tracer) )
      tree.add( self.__EXPR( self.infixBp0[30] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 33: # 'assign'
      tree.astTransform = AstTransformNodeCreator('Assign', {'var': 0, 'value': 2})
      if left:
        tree.add(left)
      tree.add( self.expect(33, tracer) )
      tree.add( self.__EXPR( self.infixBp0[33] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 106: # 'lshifteq'
      tree.astTransform = AstTransformNodeCreator('LeftShiftAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(106, tracer) )
      tree.add( self.__EXPR( self.infixBp0[106] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 82: # 'decr'
      tree.astTransform = AstTransformNodeCreator('PostDecr', {'var': 0})
      if left:
        tree.add(left)
      return self.expect( 82, tracer )
    elif  self.sym.getId() == 114: # 'div'
      tree.astTransform = AstTransformNodeCreator('Div', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(114, tracer) )
      tree.add( self.__EXPR( self.infixBp0[114] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 51: # 'comma'
      tree.astTransform = AstTransformNodeCreator('Comma', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(51, tracer) )
      tree.add( self.__EXPR( self.infixBp0[51] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 117: # 'lt'
      tree.astTransform = AstTransformNodeCreator('LessThan', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(117, tracer) )
      tree.add( self.__EXPR( self.infixBp0[117] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 113: # 'rshifteq'
      tree.astTransform = AstTransformNodeCreator('RightShiftAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(113, tracer) )
      tree.add( self.__EXPR( self.infixBp0[113] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 76: # 'questionmark'
      tree.astTransform = AstTransformNodeCreator('TernaryOperator', {'true': 2, 'false': 4, 'cond': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(76, tracer) )
      tree.add( self.__EXPR() )
      tree.add( self.expect(40, tracer) )
      tree.add( self.__EXPR() )
    elif  self.sym.getId() == 62: # 'muleq'
      tree.astTransform = AstTransformNodeCreator('MultiplyAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(62, tracer) )
      tree.add( self.__EXPR( self.infixBp0[62] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 6: # 'lshift'
      tree.astTransform = AstTransformNodeCreator('LeftShift', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(6, tracer) )
      tree.add( self.__EXPR( self.infixBp0[6] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 10: # 'incr'
      tree.astTransform = AstTransformNodeCreator('PostIncr', {'var': 0})
      if left:
        tree.add(left)
      return self.expect( 10, tracer )
    elif  self.sym.getId() == 21: # 'mod'
      tree.astTransform = AstTransformNodeCreator('Mod', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(21, tracer) )
      tree.add( self.__EXPR( self.infixBp0[21] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 66: # 'bitxor'
      tree.astTransform = AstTransformNodeCreator('BitXOR', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(66, tracer) )
      tree.add( self.__EXPR( self.infixBp0[66] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 100: # 'gt'
      tree.astTransform = AstTransformNodeCreator('GreaterThan', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(100, tracer) )
      tree.add( self.__EXPR( self.infixBp0[100] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 14: # 'rshift'
      tree.astTransform = AstTransformNodeCreator('RightShift', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(14, tracer) )
      tree.add( self.__EXPR( self.infixBp0[14] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 17: # 'diveq'
      tree.astTransform = AstTransformNodeCreator('DivideAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(17, tracer) )
      tree.add( self.__EXPR( self.infixBp0[17] ) )
      tree.isInfix = True
    return tree
  infixBp1 = {
    63: 1000,
  }
  prefixBp1 = {
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
      left.isExpr = True
      left.isNud = True
      tracer.add(left.tracer)
    while rbp < self.binding_power(self.sym, self.infixBp1):
      left = self.led1(left, depth)
      if isinstance(left, ParseTree):
        tracer.add(left.tracer)
    if left:
      left.isExpr = True
      left.tracer = tracer
    return left
  def nud1(self, tracer):
    tree = ParseTree( NonTerminal(164, '_direct_declarator') )
    if self.sym.getId() == 164: # _direct_declarator
      tree.astTransform = AstTransformSubstitution(0)
      return self.expect( 164, tracer )
    elif self.sym.getId() == 34: # 'identifier'
      tree.astTransform = AstTransformSubstitution(0)
      return self.expect( 34, tracer )
    return tree
  def led1(self, left, tracer):
    tree = ParseTree( NonTerminal(164, '_direct_declarator') )
    if  self.sym.getId() == 63: # 'lsquare'
      tree.astTransform = AstTransformSubstitution(0)
      if left:
        tree.add(left)
      tree.add( self.expect(63, tracer) )
      tree.add( self.__GEN9() )
      tree.add( self.expect(73, tracer) )
    return tree
