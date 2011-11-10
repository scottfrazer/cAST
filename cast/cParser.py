import sys
import inspect
def whoami():
  return inspect.stack()[1][3]
def whosdaddy():
  return inspect.stack()[2][3]
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
    self.nudMorphemeCount = 0
    self.isExprNud = False # true for rules like _expr := {_expr} + {...}
    self.listSeparator = None
    self.list = False
  def add( self, tree ):
    self.children.append( tree )
  def toAst( self ):
    if self.list == 'slist' or self.list == 'nlist':
      if len(self.children) == 0:
        return AstList()
      offset = 1 if self.children[0] == self.listSeparator else 0
      r = AstList([self.children[offset].toAst()])
      r.extend(self.children[offset+1].toAst())
      return r
    elif self.list == 'tlist':
      if len(self.children) == 0:
        return AstList()
      r = AstList([self.children[0].toAst()])
      r.extend(self.children[2].toAst())
      return r
    elif self.list == 'mlist':
      r = AstList()
      if len(self.children) == 0:
        return r
      lastElement = len(self.children) - 1
      for i in range(lastElement):
        r.append(self.children[i].toAst())
      r.extend(self.children[lastElement].toAst())
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
               not self.isExprNud and \
               not self.isInfix:
            if idx < self.children[0].nudMorphemeCount:
              child = self.children[0].children[idx]
            else:
              index = idx - self.children[0].nudMorphemeCount + 1
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
class Parser:
  def __init__(self):
    self.iterator = None
    self.sym = None
  TERMINAL_COMMA = 0
  TERMINAL_EXCLAMATION_POINT = 1
  TERMINAL_PP_NUMBER = 2
  TERMINAL_HEXADECIMAL_FLOATING_CONSTANT = 3
  TERMINAL_REGISTER = 4
  TERMINAL_FLOAT = 5
  TERMINAL_SEMI = 6
  TERMINAL_MODEQ = 7
  TERMINAL_DEFINED = 8
  TERMINAL_CHARACTER_CONSTANT = 9
  TERMINAL_DOUBLE = 10
  TERMINAL_TILDE = 11
  TERMINAL_FLOATING_CONSTANT = 12
  TERMINAL_EXTERNAL_DECLARATION_HINT = 13
  TERMINAL_RSHIFTEQ = 14
  TERMINAL_LTEQ = 15
  TERMINAL_BITAND = 16
  TERMINAL_MOD = 17
  TERMINAL_SIGNED = 18
  TERMINAL_SHORT = 19
  TERMINAL_DECR = 20
  TERMINAL_FUNCTION_PROTOTYPE_HINT = 21
  TERMINAL_LSHIFTEQ = 22
  TERMINAL_IF = 23
  TERMINAL_BITOR = 24
  TERMINAL_BREAK = 25
  TERMINAL_FUNCTION_DEFINITION_HINT = 26
  TERMINAL_RETURN = 27
  TERMINAL__COMPLEX = 28
  TERMINAL_BITANDEQ = 29
  TERMINAL_BITNOT = 30
  TERMINAL_ASSIGN = 31
  TERMINAL_POUND = 32
  TERMINAL_INLINE = 33
  TERMINAL_COLON = 34
  TERMINAL_DEFAULT = 35
  TERMINAL_CASE = 36
  TERMINAL_ELSE_IF = 37
  TERMINAL_UNION = 38
  TERMINAL_IDENTIFIER = 39
  TERMINAL_LSHIFT = 40
  TERMINAL_EQ = 41
  TERMINAL_LONG = 42
  TERMINAL_ADD = 43
  TERMINAL_GOTO = 44
  TERMINAL_DEFINED_SEPARATOR = 45
  TERMINAL_TYPEDEF = 46
  TERMINAL_VOID = 47
  TERMINAL_DECLARATOR_HINT = 48
  TERMINAL_ELSE = 49
  TERMINAL_NUMBER = 50
  TERMINAL_HEADER_NAME = 51
  TERMINAL_EXTERN = 52
  TERMINAL_NEQ = 53
  TERMINAL_BOOL = 54
  TERMINAL_TRAILING_COMMA = 55
  TERMINAL_ENUMERATION_CONSTANT = 56
  TERMINAL_BITXOR = 57
  TERMINAL_ELIPSIS = 58
  TERMINAL_UNIVERSAL_CHARACTER_NAME = 59
  TERMINAL_INCR = 60
  TERMINAL_OR = 61
  TERMINAL__IMAGINARY = 62
  TERMINAL_ADDEQ = 63
  TERMINAL_SUBEQ = 64
  TERMINAL_INTEGER_CONSTANT = 65
  TERMINAL_AUTO = 66
  TERMINAL_LSQUARE = 67
  TERMINAL_AND = 68
  TERMINAL_ENDIF = 69
  TERMINAL_TYPEDEF_IDENTIFIER = 70
  TERMINAL_STRUCT = 71
  TERMINAL_DIV = 72
  TERMINAL__DIRECT_DECLARATOR = 73
  TERMINAL_FOR = 74
  TERMINAL_SUB = 75
  TERMINAL_DO = 76
  TERMINAL_LBRACE = 77
  TERMINAL_LPAREN = 78
  TERMINAL_QUESTIONMARK = 79
  TERMINAL_COMPLEX = 80
  TERMINAL_DOT = 81
  TERMINAL_NOT = 82
  TERMINAL_CONST = 83
  TERMINAL__EXPR_SANS_COMMA = 84
  TERMINAL_MULEQ = 85
  TERMINAL_ASTERISK = 86
  TERMINAL_BITXOREQ = 87
  TERMINAL_COMMA_VA_ARGS = 88
  TERMINAL_GTEQ = 89
  TERMINAL_DIVEQ = 90
  TERMINAL_LPAREN_CAST = 91
  TERMINAL_ARROW = 92
  TERMINAL_RESTRICT = 93
  TERMINAL_CONTINUE = 94
  TERMINAL_CHAR = 95
  TERMINAL_STATIC = 96
  TERMINAL_RSHIFT = 97
  TERMINAL__EXPR = 98
  TERMINAL_RSQUARE = 99
  TERMINAL_SWITCH = 100
  TERMINAL_VOLATILE = 101
  TERMINAL__DIRECT_ABSTRACT_DECLARATOR = 102
  TERMINAL_UNSIGNED = 103
  TERMINAL_STRING_LITERAL = 104
  TERMINAL_RPAREN = 105
  TERMINAL_ENUM = 106
  TERMINAL_POUNDPOUND = 107
  TERMINAL__BOOL = 108
  TERMINAL_GT = 109
  TERMINAL_INT = 110
  TERMINAL_LT = 111
  TERMINAL_BITOREQ = 112
  TERMINAL_WHILE = 113
  TERMINAL_DECIMAL_FLOATING_CONSTANT = 114
  TERMINAL_RBRACE = 115
  TERMINAL_SIZEOF_SEPARATOR = 116
  TERMINAL_SIZEOF = 117
  TERMINAL_LABEL_HINT = 118
  TERMINAL_IMAGINARY = 119
  TERMINAL_AMPERSAND = 120
  terminal_str = {
    0: 'comma',
    1: 'exclamation_point',
    2: 'pp_number',
    3: 'hexadecimal_floating_constant',
    4: 'register',
    5: 'float',
    6: 'semi',
    7: 'modeq',
    8: 'defined',
    9: 'character_constant',
    10: 'double',
    11: 'tilde',
    12: 'floating_constant',
    13: 'external_declaration_hint',
    14: 'rshifteq',
    15: 'lteq',
    16: 'bitand',
    17: 'mod',
    18: 'signed',
    19: 'short',
    20: 'decr',
    21: 'function_prototype_hint',
    22: 'lshifteq',
    23: 'if',
    24: 'bitor',
    25: 'break',
    26: 'function_definition_hint',
    27: 'return',
    28: '_complex',
    29: 'bitandeq',
    30: 'bitnot',
    31: 'assign',
    32: 'pound',
    33: 'inline',
    34: 'colon',
    35: 'default',
    36: 'case',
    37: 'else_if',
    38: 'union',
    39: 'identifier',
    40: 'lshift',
    41: 'eq',
    42: 'long',
    43: 'add',
    44: 'goto',
    45: 'defined_separator',
    46: 'typedef',
    47: 'void',
    48: 'declarator_hint',
    49: 'else',
    50: 'number',
    51: 'header_name',
    52: 'extern',
    53: 'neq',
    54: 'bool',
    55: 'trailing_comma',
    56: 'enumeration_constant',
    57: 'bitxor',
    58: 'elipsis',
    59: 'universal_character_name',
    60: 'incr',
    61: 'or',
    62: '_imaginary',
    63: 'addeq',
    64: 'subeq',
    65: 'integer_constant',
    66: 'auto',
    67: 'lsquare',
    68: 'and',
    69: 'endif',
    70: 'typedef_identifier',
    71: 'struct',
    72: 'div',
    73: '_direct_declarator',
    74: 'for',
    75: 'sub',
    76: 'do',
    77: 'lbrace',
    78: 'lparen',
    79: 'questionmark',
    80: 'complex',
    81: 'dot',
    82: 'not',
    83: 'const',
    84: '_expr_sans_comma',
    85: 'muleq',
    86: 'asterisk',
    87: 'bitxoreq',
    88: 'comma_va_args',
    89: 'gteq',
    90: 'diveq',
    91: 'lparen_cast',
    92: 'arrow',
    93: 'restrict',
    94: 'continue',
    95: 'char',
    96: 'static',
    97: 'rshift',
    98: '_expr',
    99: 'rsquare',
    100: 'switch',
    101: 'volatile',
    102: '_direct_abstract_declarator',
    103: 'unsigned',
    104: 'string_literal',
    105: 'rparen',
    106: 'enum',
    107: 'poundpound',
    108: '_bool',
    109: 'gt',
    110: 'int',
    111: 'lt',
    112: 'bitoreq',
    113: 'while',
    114: 'decimal_floating_constant',
    115: 'rbrace',
    116: 'sizeof_separator',
    117: 'sizeof',
    118: 'label_hint',
    119: 'imaginary',
    120: 'ampersand',
  }
  nonterminal_str = {
    121: 'enum_specifier_body',
    122: 'union_specifier',
    123: '_gen21',
    124: '_gen35',
    125: '_gen18',
    126: 'direct_declarator_expr',
    127: 'struct_declaration',
    128: 'direct_abstract_declarator_opt',
    129: 'parameter_type_list',
    130: '_gen32',
    131: 'iteration_statement',
    132: 'direct_declarator_modifier_list_opt',
    133: '_gen37',
    134: 'designator',
    135: 'direct_declarator_parameter_list',
    136: 'external_declarator',
    137: '_gen30',
    138: 'for_cond',
    139: 'jump_statement',
    140: 'for_init',
    141: 'pp',
    142: 'struct_declarator_body',
    143: 'external_declaration_sub_sub',
    144: 'pointer_opt',
    145: 'labeled_statement',
    146: '_gen36',
    147: 'selection_statement',
    148: 'enumerator',
    149: '_gen22',
    150: '_direct_declarator',
    151: 'enum_specifier',
    152: '_gen23',
    153: 'declarator',
    154: 'static_opt',
    155: 'declaration_list',
    156: '_gen5',
    157: '_gen29',
    158: 'declaration_specifier',
    159: 'external_declaration_sub',
    160: 'sizeof_body',
    161: 'specifier_qualifier',
    162: 'external_declaration',
    163: '_gen14',
    164: '_gen0',
    165: 'direct_declarator_modifier',
    166: '_gen20',
    167: 'compound_statement',
    168: 'type_qualifier',
    169: 'constant',
    170: 'type_name',
    171: '_gen4',
    172: 'enumeration_constant',
    173: '_gen28',
    174: 'enumerator_assignment',
    175: 'type_qualifier_list_opt',
    176: '_gen25',
    177: 'init_declarator',
    178: 'trailing_comma_opt',
    179: 'expression_statement',
    180: 'direct_abstract_declarator_expr',
    181: '_gen8',
    182: '_gen16',
    183: 'expression_opt',
    184: 'parameter_type_list_opt',
    185: 'parameter_declaration_sub',
    186: '_gen19',
    187: 'external_prototype',
    188: 'block_item',
    189: 'storage_class_specifier',
    190: 'initializer',
    191: '_gen1',
    192: 'initializer_list_item',
    193: '_gen38',
    194: '_gen2',
    195: 'pointer',
    196: 'declaration',
    197: 'abstract_declarator',
    198: '_gen17',
    199: '_gen6',
    200: 'block_item_list',
    201: 'typedef_name',
    202: 'translation_unit',
    203: 'struct_specifier',
    204: 'declarator_initializer',
    205: 'parameter_declaration_sub_sub',
    206: 'statement',
    207: 'token',
    208: 'punctuator',
    209: 'direct_declarator_size',
    210: 'else_if_statement',
    211: 'for_incr',
    212: '_gen12',
    213: '_gen13',
    214: 'external_function',
    215: 'function_specifier',
    216: '_gen33',
    217: 'init_declarator_list',
    218: '_gen7',
    219: 'terminals',
    220: 'parameter_declaration',
    221: 'designation',
    222: '_gen26',
    223: '_gen9',
    224: 'keyword',
    225: '_gen27',
    226: '_expr',
    227: '_direct_abstract_declarator',
    228: 'struct_or_union_body',
    229: '_gen10',
    230: '_gen15',
    231: '_gen3',
    232: 'else_if_statement_list',
    233: '_gen11',
    234: 'else_statement',
    235: '_gen34',
    236: 'identifier',
    237: 'struct_or_union_sub',
    238: 'enum_specifier_sub',
    239: '_gen31',
    240: 'pointer_sub',
    241: '_expr_sans_comma',
    242: 'va_args',
    243: '_gen24',
    244: 'type_specifier',
    245: 'struct_declarator',
  }
  str_terminal = {
    'comma': 0,
    'exclamation_point': 1,
    'pp_number': 2,
    'hexadecimal_floating_constant': 3,
    'register': 4,
    'float': 5,
    'semi': 6,
    'modeq': 7,
    'defined': 8,
    'character_constant': 9,
    'double': 10,
    'tilde': 11,
    'floating_constant': 12,
    'external_declaration_hint': 13,
    'rshifteq': 14,
    'lteq': 15,
    'bitand': 16,
    'mod': 17,
    'signed': 18,
    'short': 19,
    'decr': 20,
    'function_prototype_hint': 21,
    'lshifteq': 22,
    'if': 23,
    'bitor': 24,
    'break': 25,
    'function_definition_hint': 26,
    'return': 27,
    '_complex': 28,
    'bitandeq': 29,
    'bitnot': 30,
    'assign': 31,
    'pound': 32,
    'inline': 33,
    'colon': 34,
    'default': 35,
    'case': 36,
    'else_if': 37,
    'union': 38,
    'identifier': 39,
    'lshift': 40,
    'eq': 41,
    'long': 42,
    'add': 43,
    'goto': 44,
    'defined_separator': 45,
    'typedef': 46,
    'void': 47,
    'declarator_hint': 48,
    'else': 49,
    'number': 50,
    'header_name': 51,
    'extern': 52,
    'neq': 53,
    'bool': 54,
    'trailing_comma': 55,
    'enumeration_constant': 56,
    'bitxor': 57,
    'elipsis': 58,
    'universal_character_name': 59,
    'incr': 60,
    'or': 61,
    '_imaginary': 62,
    'addeq': 63,
    'subeq': 64,
    'integer_constant': 65,
    'auto': 66,
    'lsquare': 67,
    'and': 68,
    'endif': 69,
    'typedef_identifier': 70,
    'struct': 71,
    'div': 72,
    '_direct_declarator': 73,
    'for': 74,
    'sub': 75,
    'do': 76,
    'lbrace': 77,
    'lparen': 78,
    'questionmark': 79,
    'complex': 80,
    'dot': 81,
    'not': 82,
    'const': 83,
    '_expr_sans_comma': 84,
    'muleq': 85,
    'asterisk': 86,
    'bitxoreq': 87,
    'comma_va_args': 88,
    'gteq': 89,
    'diveq': 90,
    'lparen_cast': 91,
    'arrow': 92,
    'restrict': 93,
    'continue': 94,
    'char': 95,
    'static': 96,
    'rshift': 97,
    '_expr': 98,
    'rsquare': 99,
    'switch': 100,
    'volatile': 101,
    '_direct_abstract_declarator': 102,
    'unsigned': 103,
    'string_literal': 104,
    'rparen': 105,
    'enum': 106,
    'poundpound': 107,
    '_bool': 108,
    'gt': 109,
    'int': 110,
    'lt': 111,
    'bitoreq': 112,
    'while': 113,
    'decimal_floating_constant': 114,
    'rbrace': 115,
    'sizeof_separator': 116,
    'sizeof': 117,
    'label_hint': 118,
    'imaginary': 119,
    'ampersand': 120,
  }
  str_nonterminal = {
    'enum_specifier_body': 121,
    'union_specifier': 122,
    '_gen21': 123,
    '_gen35': 124,
    '_gen18': 125,
    'direct_declarator_expr': 126,
    'struct_declaration': 127,
    'direct_abstract_declarator_opt': 128,
    'parameter_type_list': 129,
    '_gen32': 130,
    'iteration_statement': 131,
    'direct_declarator_modifier_list_opt': 132,
    '_gen37': 133,
    'designator': 134,
    'direct_declarator_parameter_list': 135,
    'external_declarator': 136,
    '_gen30': 137,
    'for_cond': 138,
    'jump_statement': 139,
    'for_init': 140,
    'pp': 141,
    'struct_declarator_body': 142,
    'external_declaration_sub_sub': 143,
    'pointer_opt': 144,
    'labeled_statement': 145,
    '_gen36': 146,
    'selection_statement': 147,
    'enumerator': 148,
    '_gen22': 149,
    '_direct_declarator': 150,
    'enum_specifier': 151,
    '_gen23': 152,
    'declarator': 153,
    'static_opt': 154,
    'declaration_list': 155,
    '_gen5': 156,
    '_gen29': 157,
    'declaration_specifier': 158,
    'external_declaration_sub': 159,
    'sizeof_body': 160,
    'specifier_qualifier': 161,
    'external_declaration': 162,
    '_gen14': 163,
    '_gen0': 164,
    'direct_declarator_modifier': 165,
    '_gen20': 166,
    'compound_statement': 167,
    'type_qualifier': 168,
    'constant': 169,
    'type_name': 170,
    '_gen4': 171,
    'enumeration_constant': 172,
    '_gen28': 173,
    'enumerator_assignment': 174,
    'type_qualifier_list_opt': 175,
    '_gen25': 176,
    'init_declarator': 177,
    'trailing_comma_opt': 178,
    'expression_statement': 179,
    'direct_abstract_declarator_expr': 180,
    '_gen8': 181,
    '_gen16': 182,
    'expression_opt': 183,
    'parameter_type_list_opt': 184,
    'parameter_declaration_sub': 185,
    '_gen19': 186,
    'external_prototype': 187,
    'block_item': 188,
    'storage_class_specifier': 189,
    'initializer': 190,
    '_gen1': 191,
    'initializer_list_item': 192,
    '_gen38': 193,
    '_gen2': 194,
    'pointer': 195,
    'declaration': 196,
    'abstract_declarator': 197,
    '_gen17': 198,
    '_gen6': 199,
    'block_item_list': 200,
    'typedef_name': 201,
    'translation_unit': 202,
    'struct_specifier': 203,
    'declarator_initializer': 204,
    'parameter_declaration_sub_sub': 205,
    'statement': 206,
    'token': 207,
    'punctuator': 208,
    'direct_declarator_size': 209,
    'else_if_statement': 210,
    'for_incr': 211,
    '_gen12': 212,
    '_gen13': 213,
    'external_function': 214,
    'function_specifier': 215,
    '_gen33': 216,
    'init_declarator_list': 217,
    '_gen7': 218,
    'terminals': 219,
    'parameter_declaration': 220,
    'designation': 221,
    '_gen26': 222,
    '_gen9': 223,
    'keyword': 224,
    '_gen27': 225,
    '_expr': 226,
    '_direct_abstract_declarator': 227,
    'struct_or_union_body': 228,
    '_gen10': 229,
    '_gen15': 230,
    '_gen3': 231,
    'else_if_statement_list': 232,
    '_gen11': 233,
    'else_statement': 234,
    '_gen34': 235,
    'identifier': 236,
    'struct_or_union_sub': 237,
    'enum_specifier_sub': 238,
    '_gen31': 239,
    'pointer_sub': 240,
    '_expr_sans_comma': 241,
    'va_args': 242,
    '_gen24': 243,
    'type_specifier': 244,
    'struct_declarator': 245,
  }
  terminal_count = 121
  nonterminal_count = 125
  parse_table = [
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 107, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 392, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [65, -1, -1, -1, 65, 65, 65, -1, -1, -1, 65, -1, -1, -1, -1, -1, -1, -1, 65, 65, -1, 65, -1, -1, -1, -1, 65, -1, 65, -1, -1, -1, -1, 65, 65, -1, -1, -1, 65, 65, -1, -1, 65, -1, -1, -1, 65, 65, 65, -1, -1, -1, 65, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 65, -1, -1, -1, 65, 65, -1, 65, -1, -1, -1, 312, 65, -1, -1, -1, -1, 65, -1, -1, 65, -1, 65, -1, -1, -1, -1, 65, -1, 65, 65, -1, -1, -1, -1, 65, 65, 65, -1, -1, 65, -1, 65, -1, 65, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, 376, 376, 376, -1, -1, 376, 376, -1, 376, -1, -1, -1, 376, -1, 376, 376, 376, -1, -1, 376, -1, 376, -1, 376, 376, -1, -1, -1, -1, 376, -1, 376, 376, -1, 376, 376, -1, -1, 376, -1, 376, -1, 376, 376, -1, 371, -1, -1, 376, -1, -1, -1, 376, -1, -1, -1, 376, -1, -1, -1, -1, 376, 376, -1, -1, 376, 376, 376, -1, -1, 376, -1, 376, 376, 376, -1, -1, -1, -1, 376, -1, -1, 376, -1, -1, -1, -1, 376, -1, 376, 376, 376, 376, -1, 376, -1, 376, 376, -1, 376, 376, -1, 376, -1, 376, -1, 376, -1, -1, 376, -1, 376, -1, 376, 376, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 417, -1, -1, -1, -1, 417, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 417, -1, -1, -1, -1, 417, -1, -1, -1, -1, -1, -1, -1, 417, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, 211, -1, -1, 211, -1, -1, -1, 211, -1, -1, -1, 211, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 211, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 211, -1, -1, -1, 211, -1, -1, -1, -1, 211, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 211, -1, -1, -1, -1, 211, -1, -1, 211, -1, -1, -1, -1, 211, -1, 211, -1, -1, 211, -1, 211, -1, -1, 211, -1, -1, 211, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 211, -1, -1, -1],
    [-1, -1, -1, -1, -1, 339, -1, -1, -1, -1, 339, -1, -1, -1, -1, -1, -1, -1, 339, 339, -1, -1, -1, -1, -1, -1, -1, -1, 339, -1, -1, -1, -1, -1, 339, -1, -1, -1, 339, 339, -1, -1, 339, -1, -1, -1, -1, 339, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 339, 339, -1, 339, -1, -1, -1, -1, 339, -1, -1, -1, -1, 339, -1, -1, 339, -1, -1, -1, -1, -1, -1, 339, -1, 339, -1, -1, -1, -1, -1, 339, -1, 339, -1, -1, 339, -1, 339, -1, 339, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [85, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 230, -1, -1, -1, -1, -1, -1, -1, -1, -1, 85, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 230, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, 60, 60, -1, -1, -1, -1, 60, -1, -1, -1, -1, -1, -1, -1, 60, 60, -1, -1, -1, -1, -1, -1, -1, -1, 60, -1, -1, -1, -1, 60, -1, -1, -1, -1, 60, -1, -1, -1, 60, -1, -1, -1, 60, 60, -1, -1, -1, -1, 60, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 60, -1, -1, -1, 60, 60, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 60, -1, -1, -1, -1, -1, -1, -1, -1, -1, 60, -1, 60, 60, -1, -1, -1, -1, 60, -1, 60, -1, -1, 60, -1, 60, -1, 60, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, 336, 336, 336, -1, -1, 336, 336, -1, 336, -1, -1, -1, 336, -1, 336, 336, 336, -1, -1, 336, -1, 336, -1, 336, 336, -1, -1, -1, -1, 336, -1, 336, 336, -1, 336, 336, -1, -1, 336, -1, 336, -1, 336, 336, -1, -1, -1, -1, 336, -1, -1, -1, 336, -1, -1, -1, 336, -1, -1, -1, -1, 336, 336, -1, -1, -1, 336, 336, -1, -1, 336, -1, 336, 336, 336, -1, -1, -1, -1, 336, -1, -1, 336, -1, -1, -1, -1, 336, -1, 336, 336, 336, 336, -1, 336, -1, 336, 336, -1, 336, 336, -1, 336, -1, 336, -1, 336, -1, -1, 336, -1, 336, -1, 336, 336, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 97, -1, 382, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 367, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, 138, -1, -1, 138, -1, -1, -1, 138, -1, -1, -1, 138, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 138, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 138, -1, -1, -1, 138, -1, -1, -1, -1, 138, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 138, -1, -1, -1, -1, 352, -1, -1, 138, -1, -1, -1, -1, 138, -1, 352, -1, -1, 352, -1, 138, -1, -1, 352, -1, -1, 138, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 138, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, 218, -1, -1, 218, -1, -1, -1, 218, -1, -1, -1, 218, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 218, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 218, -1, -1, -1, 218, -1, -1, -1, -1, 218, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 218, -1, -1, -1, -1, -1, 218, -1, 218, -1, -1, -1, -1, 218, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 218, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 218, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 396, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 59, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, 378, 378, -1, -1, -1, -1, 378, -1, -1, -1, -1, -1, -1, -1, 378, 378, -1, -1, -1, -1, -1, -1, -1, -1, 378, -1, -1, -1, -1, 378, -1, -1, -1, -1, 378, 174, -1, -1, 378, -1, -1, -1, 378, 378, -1, -1, -1, -1, 378, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 378, -1, -1, -1, 378, 378, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 378, -1, -1, -1, -1, -1, -1, -1, -1, -1, 378, -1, 378, 378, -1, -1, -1, -1, 378, -1, 378, -1, -1, 378, -1, 378, -1, 378, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 279, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [202, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 300, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 300, -1, -1, -1, -1, 300, -1, -1, -1, -1, -1, -1, -1, 300, -1, 202, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 300, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, 329, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 368, -1, 151, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 127, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 251, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, 244, 244, 497, -1, -1, 475, 244, -1, 475, -1, -1, -1, 475, -1, 244, 244, 475, -1, -1, -1, -1, -1, -1, -1, 244, -1, -1, -1, -1, 244, -1, -1, -1, -1, 244, 475, -1, -1, 244, -1, -1, -1, 244, 244, -1, -1, -1, -1, 244, -1, -1, -1, 475, -1, -1, -1, 475, -1, -1, -1, -1, 475, 244, -1, -1, -1, 244, 244, -1, -1, -1, -1, -1, -1, 475, -1, -1, -1, -1, 244, -1, -1, 475, -1, -1, -1, -1, 475, -1, 244, -1, 244, 244, -1, 475, -1, -1, 244, -1, 244, 475, -1, 244, -1, 244, -1, 244, -1, -1, -1, -1, -1, -1, 475, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, 6, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 361, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 246, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 132, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 84, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [305, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 305, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 305, -1, -1, -1, -1, 305, -1, -1, -1, -1, -1, -1, -1, 313, -1, 305, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 305, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 17, 263, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 45, -1, -1],
    [-1, -1, -1, -1, 402, 402, 402, -1, -1, 402, 402, -1, 402, -1, -1, -1, 402, -1, 402, 402, 402, -1, -1, 402, -1, 402, -1, 402, 402, -1, -1, -1, -1, 402, -1, 402, 402, 328, 402, 402, -1, -1, 402, -1, 402, -1, 402, 402, -1, 402, -1, -1, 402, -1, -1, -1, 402, -1, -1, -1, 402, -1, -1, -1, -1, 402, 402, -1, -1, 402, 402, 402, -1, -1, 402, -1, 402, 402, 402, -1, -1, -1, -1, 402, -1, -1, 402, -1, -1, -1, -1, 402, -1, 402, 402, 402, 402, -1, 402, -1, 402, 402, -1, 402, 402, -1, 402, -1, 402, -1, 402, -1, -1, 402, -1, 402, -1, 402, 402, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 241, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 385, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 209, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 198, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 182, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [38, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 41, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 47, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 47, -1, -1, -1, -1, 47, -1, -1, -1, -1, -1, -1, -1, 47, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, 236, -1, -1, 236, -1, -1, -1, 236, -1, -1, -1, 236, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 236, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 236, -1, -1, -1, 236, -1, -1, -1, -1, 236, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 236, -1, -1, -1, -1, -1, -1, -1, 236, -1, -1, -1, -1, 236, -1, -1, -1, -1, 37, -1, 236, -1, -1, -1, -1, -1, 236, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 236, -1, -1, -1],
    [403, -1, -1, -1, 403, 403, 403, -1, -1, -1, 403, -1, -1, -1, -1, -1, -1, -1, 403, 403, -1, -1, -1, -1, -1, -1, -1, -1, 403, -1, -1, -1, -1, 403, -1, -1, -1, -1, 403, -1, -1, -1, 403, -1, -1, -1, 403, 403, -1, -1, -1, -1, 403, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 403, -1, -1, -1, 403, 403, -1, -1, -1, -1, -1, 403, -1, -1, -1, -1, -1, 403, -1, -1, -1, -1, -1, -1, -1, -1, -1, 403, -1, 403, 403, -1, -1, -1, -1, 403, -1, 403, -1, -1, 403, -1, 403, -1, 403, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [284, -1, -1, -1, 284, 284, 284, -1, -1, -1, 284, -1, -1, -1, -1, -1, -1, -1, 284, 284, -1, -1, -1, -1, -1, -1, -1, -1, 284, -1, -1, -1, -1, 284, -1, -1, -1, -1, 284, -1, -1, -1, 284, -1, -1, -1, 284, 284, -1, -1, -1, -1, 284, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 284, -1, -1, -1, 284, 284, -1, -1, -1, -1, -1, 284, -1, -1, -1, -1, -1, 284, -1, -1, -1, -1, -1, -1, -1, -1, -1, 284, -1, 284, 284, -1, -1, -1, -1, 284, -1, 284, -1, -1, 284, -1, 284, -1, 284, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [20, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, 264, 68, -1, -1, -1, -1, 68, -1, -1, -1, -1, -1, -1, -1, 68, 68, -1, -1, -1, -1, -1, -1, -1, -1, 68, -1, -1, -1, -1, 317, -1, -1, -1, -1, 68, -1, -1, -1, 68, -1, -1, -1, 264, 68, -1, -1, -1, -1, 264, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 264, -1, -1, -1, 68, 68, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 66, -1, -1, -1, -1, -1, -1, -1, -1, -1, 66, -1, 68, 264, -1, -1, -1, -1, 66, -1, 68, -1, -1, 68, -1, 68, -1, 68, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, 70, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 70, -1, -1, -1, -1, 5, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 70, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 487, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 478, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, 337, -1, -1, -1, -1, 337, -1, -1, -1, -1, -1, -1, -1, 337, 337, -1, -1, -1, -1, -1, -1, -1, -1, 337, -1, -1, -1, -1, -1, -1, -1, -1, -1, 337, -1, -1, -1, 337, -1, -1, -1, -1, 337, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 337, 337, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 394, -1, -1, -1, -1, -1, -1, -1, -1, -1, 394, -1, 337, -1, -1, -1, -1, -1, 394, -1, 337, -1, -1, 337, -1, 337, -1, 337, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 502, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 23, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 18, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 18, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 281, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 369, -1, -1, -1, -1, -1, -1, -1, -1, -1, 369, -1, -1, 501, -1, -1, -1, -1, 369, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [473, -1, -1, -1, -1, -1, 473, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 258, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 307, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 294, -1, -1, -1, -1, -1, -1, -1, -1, -1, 160, -1, -1, -1, -1, -1, -1, -1, 162, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, 29, -1, -1, 308, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 114, -1, -1, -1, -1, -1, -1, -1, -1, 121, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 3, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 333, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [359, -1, -1, -1, -1, -1, 229, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 43, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 399, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [271, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 462, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 271, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [86, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 86, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 86, -1, -1, -1, -1, 86, -1, -1, -1, -1, 111, -1, -1, 86, -1, 86, -1, -1, -1, -1, 111, -1, -1, 86, -1, -1, -1, -1, 111, 86, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, 438, -1, -1, 438, -1, -1, -1, 438, -1, -1, -1, 438, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 438, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 438, -1, -1, -1, 438, -1, -1, -1, -1, 438, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 438, -1, -1, -1, -1, 314, -1, -1, 438, -1, -1, -1, -1, 438, -1, 314, -1, -1, 314, -1, 438, -1, -1, 314, -1, -1, 438, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 438, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 101, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 101, -1, -1, -1, -1, 101, -1, -1, -1, -1, -1, -1, -1, 101, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 332, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 320, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, 2, -1, -1, 2, -1, -1, 2, -1, -1, -1, 2, -1, -1, -1, 2, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 2, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 2, -1, -1, -1, 2, -1, -1, -1, -1, 2, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 2, -1, -1, -1, -1, -1, -1, -1, 2, -1, -1, -1, -1, 2, -1, -1, -1, -1, -1, -1, 2, -1, -1, -1, -1, -1, 2, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 2, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, 381, -1, -1, 381, -1, -1, -1, 381, -1, -1, -1, 381, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 381, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 381, -1, -1, -1, 381, -1, -1, -1, -1, 381, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 381, -1, -1, -1, -1, 381, -1, -1, 381, -1, -1, -1, -1, 381, -1, 381, -1, -1, 381, -1, 381, -1, -1, 381, -1, -1, 381, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 381, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 249, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 249, -1, -1, -1, -1, 249, -1, -1, -1, -1, -1, -1, -1, 249, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, 228, -1, -1, -1, -1, 228, -1, -1, -1, -1, -1, -1, -1, 228, 228, -1, -1, -1, -1, -1, -1, -1, -1, 228, -1, -1, -1, -1, -1, 228, -1, -1, -1, 228, 228, -1, -1, 228, -1, -1, -1, -1, 228, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 228, 228, -1, 228, -1, -1, -1, -1, 228, -1, -1, -1, -1, 228, -1, -1, 228, -1, -1, -1, -1, -1, -1, 228, -1, 228, -1, -1, -1, -1, -1, 228, -1, 228, -1, -1, 228, -1, 228, -1, 228, -1, -1, -1, -1, 423, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, 260, -1, -1, 449, -1, -1, 449, -1, -1, -1, 449, -1, -1, -1, 449, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 449, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 449, -1, -1, -1, 449, -1, -1, -1, -1, 449, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 449, -1, -1, -1, -1, -1, -1, -1, 449, -1, -1, -1, -1, 449, -1, -1, -1, -1, -1, -1, 449, -1, -1, -1, -1, -1, 449, 260, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 449, -1, -1, -1],
    [-1, -1, -1, -1, 391, 391, -1, -1, -1, -1, 391, -1, -1, -1, -1, -1, -1, -1, 391, 391, -1, -1, -1, -1, -1, -1, -1, -1, 391, -1, -1, -1, -1, 391, -1, -1, -1, -1, 391, -1, -1, -1, 391, -1, -1, -1, 391, 391, -1, -1, -1, -1, 391, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 391, -1, -1, -1, 391, 391, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 391, -1, -1, -1, -1, -1, -1, -1, -1, -1, 391, -1, 391, 391, -1, -1, -1, -1, 391, -1, 391, -1, -1, 391, -1, 391, -1, 391, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [13, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 13, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 13, -1, -1, -1, -1, 13, -1, -1, -1, -1, -1, -1, -1, 13, -1, 13, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 13, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [191, -1, -1, -1, -1, -1, 428, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 446, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, 196, 196, 311, -1, -1, 311, 196, -1, 311, -1, -1, -1, 311, -1, 196, 196, 311, -1, -1, 311, -1, 311, -1, 311, 196, -1, -1, -1, -1, 196, -1, 311, 311, -1, 196, 311, -1, -1, 196, -1, 311, -1, 196, 196, -1, -1, -1, -1, 196, -1, -1, -1, 311, -1, -1, -1, 311, -1, -1, -1, -1, 311, 196, -1, -1, -1, 196, 196, -1, -1, 311, -1, 311, 311, 311, -1, -1, -1, -1, 196, -1, -1, 311, -1, -1, -1, -1, 311, -1, 196, 311, 196, 196, -1, 311, -1, 311, 196, -1, 196, 311, -1, 196, -1, 196, -1, 196, -1, -1, 311, -1, -1, -1, 311, 311, -1, -1],
    [-1, -1, -1, -1, 28, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 36, -1, -1, -1, -1, -1, 283, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 92, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 435, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, 321, -1, -1, 321, -1, -1, -1, 321, -1, -1, -1, 321, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 321, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 321, -1, -1, -1, 321, -1, -1, -1, -1, 321, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 293, 321, -1, -1, -1, -1, -1, -1, -1, 321, -1, -1, -1, -1, 321, -1, -1, -1, -1, -1, -1, 321, -1, -1, -1, -1, -1, 321, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 321, -1, -1, -1],
    [-1, -1, -1, -1, 309, 309, -1, -1, -1, -1, 309, -1, -1, -1, -1, -1, -1, -1, 309, 309, -1, -1, -1, -1, -1, -1, -1, -1, 309, -1, -1, -1, -1, 309, -1, -1, -1, -1, 309, -1, -1, -1, 309, -1, -1, -1, 309, 309, -1, -1, -1, -1, 309, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 309, -1, -1, -1, 309, 309, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 309, -1, -1, -1, -1, -1, -1, -1, -1, -1, 309, -1, 309, 309, -1, -1, -1, -1, 309, -1, 309, -1, -1, 309, -1, 309, -1, 309, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, 363, -1, -1, 363, -1, -1, -1, 363, -1, -1, -1, 363, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 363, -1, -1, -1, -1, -1, -1, -1, 363, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 363, -1, -1, -1, 363, -1, -1, -1, -1, 295, -1, 363, -1, -1, -1, -1, -1, -1, -1, -1, -1, 363, 363, -1, -1, 363, -1, -1, -1, -1, 363, -1, -1, -1, -1, 363, -1, -1, -1, -1, -1, -1, 363, -1, -1, -1, -1, -1, 363, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 363, -1, -1, -1],
    [137, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [297, -1, -1, -1, 489, 489, 297, -1, -1, -1, 489, -1, -1, -1, -1, -1, -1, -1, 489, 489, -1, 297, -1, -1, -1, -1, 297, -1, 489, -1, -1, -1, -1, 489, -1, -1, -1, -1, 489, 297, -1, -1, 489, -1, -1, -1, 489, 489, 297, -1, -1, -1, 489, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 489, -1, -1, -1, 489, 489, -1, 297, -1, -1, -1, -1, 297, -1, -1, -1, -1, 489, -1, -1, 297, -1, 297, -1, -1, -1, -1, 489, -1, 489, 489, -1, -1, -1, -1, 489, 297, 489, -1, -1, 489, -1, 489, -1, 489, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [275, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 275, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 275, -1, -1, -1, -1, 275, -1, -1, -1, -1, -1, -1, -1, 275, -1, 275, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 275, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, 247, 247, -1, -1, -1, -1, 247, -1, -1, -1, -1, -1, -1, -1, 247, 247, -1, -1, -1, -1, -1, -1, -1, -1, 247, -1, -1, -1, -1, 247, -1, -1, -1, -1, 247, -1, -1, -1, 247, -1, -1, -1, 247, 247, -1, -1, -1, -1, 247, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 247, -1, -1, -1, 247, 247, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 247, -1, -1, -1, -1, -1, -1, -1, -1, -1, 247, -1, 247, 247, -1, -1, -1, -1, 247, -1, 247, -1, -1, 247, -1, 247, -1, 247, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 287, -1, -1, -1, -1, -1, -1, -1, 287, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 287, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, 79, -1, -1, -1, -1, 79, -1, -1, -1, -1, -1, -1, -1, 79, 79, -1, -1, -1, -1, -1, -1, -1, -1, 79, -1, -1, -1, -1, -1, 405, -1, -1, -1, 79, 405, -1, -1, 79, -1, -1, -1, -1, 79, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 79, 79, -1, 405, -1, -1, -1, -1, 405, -1, -1, -1, -1, 79, -1, -1, 405, -1, -1, -1, -1, -1, -1, 79, -1, 79, -1, -1, -1, -1, -1, 79, -1, 79, -1, -1, 79, -1, 79, -1, 79, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [253, -1, -1, -1, 331, 331, 253, -1, -1, -1, 331, -1, -1, -1, -1, -1, -1, -1, 331, 331, -1, -1, -1, -1, -1, -1, -1, -1, 331, -1, -1, -1, -1, 331, -1, -1, -1, -1, 331, -1, -1, -1, 331, -1, -1, -1, 331, 331, -1, -1, -1, -1, 331, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 331, -1, -1, -1, 331, 331, -1, -1, -1, -1, -1, 253, -1, -1, -1, -1, -1, 331, -1, -1, -1, -1, -1, -1, -1, -1, -1, 331, -1, 331, 331, -1, -1, -1, -1, 331, -1, 331, -1, -1, 331, -1, 331, -1, 331, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, 404, 404, 404, -1, -1, 404, 404, -1, 404, -1, -1, -1, 404, -1, 404, 404, 404, -1, -1, 404, -1, 404, -1, 404, 404, -1, -1, -1, -1, 404, -1, 404, 404, -1, 404, 404, -1, -1, 404, -1, 404, -1, 404, 404, -1, -1, -1, -1, 404, -1, -1, -1, 404, -1, -1, -1, 404, -1, -1, -1, -1, 404, 404, -1, -1, -1, 404, 404, -1, -1, 404, -1, 404, 404, 404, -1, -1, -1, -1, 404, -1, -1, 404, -1, -1, -1, -1, 404, -1, 404, 404, 404, 404, -1, 404, -1, 404, 404, -1, 404, 404, -1, 404, -1, 404, -1, 404, -1, -1, 404, -1, 404, -1, 404, 404, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 419, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 217, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 349, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 342, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [115, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 185, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 185, -1, -1, -1, -1, 115, -1, -1, -1, -1, -1, -1, -1, -1, -1, 115, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 115, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, 136, -1, -1, 136, -1, -1, 136, -1, -1, -1, 136, -1, -1, -1, 136, -1, -1, 353, -1, 31, -1, 31, -1, -1, -1, -1, -1, -1, -1, 348, 348, -1, -1, 136, -1, -1, -1, -1, 31, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 136, -1, -1, -1, 136, -1, -1, -1, -1, 136, -1, -1, -1, -1, -1, -1, -1, -1, 356, -1, 356, 318, 136, -1, -1, -1, -1, -1, -1, -1, 136, -1, -1, -1, -1, 136, -1, -1, 31, -1, -1, -1, 136, -1, 353, -1, -1, -1, 136, -1, -1, -1, -1, -1, -1, -1, -1, 356, -1, -1, -1, 136, 348, -1, -1],
    [366, 366, 496, -1, 44, 44, 366, 366, -1, 420, 44, 366, 420, -1, 366, 366, -1, 366, 44, 44, 366, -1, 366, 44, 366, 44, -1, 44, 44, 366, -1, 366, 366, 44, 366, 44, 44, -1, 44, 296, 366, 366, 44, 366, 44, -1, 44, 44, -1, 44, -1, -1, 44, 366, -1, -1, 420, 366, 366, -1, 366, 366, 44, 366, 366, 420, 44, 366, 366, -1, -1, 44, 366, -1, 44, 366, 44, 366, 366, 366, -1, 366, -1, 44, -1, 366, -1, 366, -1, 366, -1, -1, 366, 44, 44, 44, 44, 366, -1, 366, 44, 44, -1, 44, 362, 366, 44, 366, 44, 366, 44, 366, 366, 44, -1, 366, -1, 44, -1, -1, 366],
    [133, 63, -1, -1, -1, -1, 213, 9, -1, -1, -1, 102, -1, -1, 104, 453, -1, 464, -1, -1, 245, -1, 123, -1, 62, -1, -1, -1, -1, 200, -1, 187, 389, -1, 470, -1, -1, -1, -1, -1, 486, 256, -1, 165, -1, -1, -1, -1, -1, -1, -1, -1, -1, 319, -1, -1, -1, 465, 422, -1, 364, 505, -1, 383, 128, -1, -1, 483, 411, -1, -1, -1, 298, -1, -1, 379, -1, 7, 344, 430, -1, 0, -1, -1, -1, 341, -1, 161, -1, 324, -1, -1, 409, -1, -1, -1, -1, 488, -1, 255, -1, -1, -1, -1, -1, 153, -1, 195, -1, 224, -1, 177, 197, -1, -1, 105, -1, -1, -1, -1, 269],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, 257, -1, -1, 257, -1, -1, -1, 257, -1, -1, -1, 257, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 257, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 257, -1, -1, -1, 257, -1, -1, -1, -1, 257, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 257, -1, -1, -1, -1, -1, -1, -1, 257, -1, -1, -1, -1, 257, -1, -1, -1, -1, -1, -1, 257, -1, -1, -1, -1, -1, 257, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 257, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 290, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, 144, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 345, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [338, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 442, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, 4, -1, -1, 4, -1, -1, -1, 4, -1, -1, -1, 4, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 225, -1, -1, -1, -1, -1, -1, -1, 4, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 4, -1, -1, -1, 4, -1, -1, -1, -1, 4, -1, 225, -1, -1, -1, -1, -1, -1, -1, -1, -1, 4, 4, -1, -1, 225, -1, -1, -1, -1, 4, -1, -1, -1, -1, 4, -1, -1, -1, -1, -1, -1, 4, -1, -1, -1, -1, -1, 4, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 4, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 397, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 19, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, 450, 450, 450, -1, -1, 450, 450, -1, 450, -1, -1, -1, 450, -1, 450, 450, 450, -1, -1, 450, -1, 450, -1, 450, 450, -1, -1, -1, -1, 450, -1, 450, 450, -1, 450, 450, -1, -1, 450, -1, 450, -1, 450, 450, -1, -1, -1, -1, 450, -1, -1, -1, 450, -1, -1, -1, 450, -1, -1, -1, -1, 450, 450, -1, -1, -1, 450, 450, -1, -1, 450, -1, 450, 450, 450, -1, -1, -1, -1, 450, -1, -1, 450, -1, -1, -1, -1, 450, -1, 450, 450, 450, 450, -1, 450, -1, 450, 450, -1, 450, 450, -1, 450, -1, 450, -1, 450, -1, -1, 450, -1, 448, -1, 450, 450, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 261, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 261, -1, -1, -1, -1, 261, -1, -1, -1, -1, -1, -1, -1, 261, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, 343, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 340, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 340, -1, -1, -1, -1, 340, -1, -1, -1, -1, -1, -1, -1, 340, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [384, 408, -1, 15, 410, 154, 139, 418, -1, 188, 159, 83, -1, -1, 243, 221, 89, 67, 444, 458, 494, -1, 277, 231, 471, 147, -1, 95, -1, 477, -1, 108, 456, 206, 64, 116, 163, -1, 75, 157, 259, 122, 72, 155, 106, -1, 481, 99, -1, 30, 427, 248, 440, 21, 1, -1, -1, 374, 334, 170, 346, 80, -1, 459, 183, 239, 412, 288, 292, -1, -1, 117, 57, -1, 351, 238, 189, 212, 49, 180, 273, 434, 109, 414, -1, 204, -1, 474, -1, 323, 472, -1, 55, 425, 32, 495, 276, 433, -1, 51, 226, 240, -1, 77, 96, 61, 82, 499, -1, 306, 219, 429, 232, 289, 69, 10, -1, 491, -1, 181, -1],
    [-1, -1, -1, -1, 441, 441, -1, -1, -1, -1, 441, -1, -1, -1, -1, -1, -1, -1, 441, 441, -1, -1, -1, -1, -1, -1, -1, -1, 441, -1, -1, -1, -1, 441, -1, -1, -1, -1, 441, -1, -1, -1, 441, -1, -1, -1, 441, 441, -1, -1, -1, -1, 441, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 441, -1, -1, -1, 441, 441, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 441, -1, -1, -1, -1, -1, -1, -1, -1, -1, 441, -1, 441, 441, -1, -1, -1, -1, 441, -1, 441, -1, -1, 441, -1, 441, -1, 441, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 172, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 172, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 172, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, 143, 143, -1, -1, -1, -1, 143, -1, -1, -1, -1, -1, -1, -1, 143, 143, -1, -1, -1, -1, -1, -1, -1, -1, 143, -1, -1, -1, -1, 143, -1, -1, -1, -1, 143, -1, -1, -1, 143, -1, -1, -1, 143, 143, -1, -1, -1, -1, 143, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 143, -1, -1, -1, 143, 143, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 143, -1, -1, -1, -1, -1, -1, -1, -1, -1, 143, -1, 143, 143, -1, -1, -1, -1, 143, -1, 143, -1, -1, 143, -1, 143, -1, 143, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [377, -1, -1, -1, -1, -1, 149, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, 347, 88, -1, -1, -1, -1, 439, -1, -1, -1, -1, -1, -1, -1, 184, 395, -1, -1, -1, 302, -1, 167, -1, 12, 350, -1, -1, -1, -1, 388, -1, 216, 254, -1, 237, -1, -1, -1, 432, -1, 150, -1, 141, 90, -1, 54, -1, -1, 40, -1, -1, -1, -1, -1, -1, -1, -1, -1, 504, -1, -1, -1, 14, -1, -1, -1, -1, 173, -1, -1, 503, -1, 34, -1, -1, -1, -1, -1, -1, 25, -1, -1, -1, -1, -1, -1, -1, -1, -1, 285, 120, 58, 291, -1, -1, -1, 52, 299, -1, 262, -1, -1, 222, -1, 335, -1, 126, -1, -1, 118, -1, -1, -1, 42, -1, -1, -1],
    [168, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 190, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [74, -1, -1, -1, -1, -1, 74, -1, -1, 131, -1, -1, 131, -1, -1, -1, 131, -1, -1, -1, 74, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 164, -1, -1, 74, -1, -1, -1, -1, 131, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 74, 131, -1, -1, -1, 74, -1, -1, -1, -1, 131, -1, 164, -1, -1, -1, -1, -1, -1, -1, -1, -1, 164, 131, 74, -1, 74, -1, -1, 131, -1, 131, -1, -1, -1, -1, 131, 74, -1, -1, -1, -1, -1, 164, 74, -1, -1, -1, -1, 131, 74, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 131, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 437, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [169, -1, -1, -1, -1, -1, 169, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 71, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [460, -1, -1, -1, 460, 460, 460, -1, -1, -1, 460, -1, -1, -1, -1, -1, -1, -1, 460, 460, -1, 460, -1, -1, -1, -1, 460, -1, 460, -1, -1, -1, -1, 460, 460, -1, -1, -1, 460, 460, -1, -1, 460, -1, -1, -1, 460, 460, 460, -1, -1, -1, 460, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 460, -1, -1, -1, 460, 460, -1, 460, -1, -1, -1, 178, 460, -1, -1, -1, -1, 460, -1, -1, 460, -1, 460, -1, -1, -1, -1, 460, -1, 460, 460, -1, -1, -1, -1, 460, 460, 460, -1, -1, 460, -1, 460, -1, 460, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, 233, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 355, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 355, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, 266, 266, 266, -1, -1, 266, 266, -1, 266, -1, -1, -1, 266, -1, 266, 266, 266, -1, -1, 266, -1, 266, -1, 266, 266, -1, -1, -1, -1, 266, -1, 266, 266, 266, 266, 266, -1, -1, 266, -1, 266, -1, 266, 266, -1, 266, -1, -1, 266, -1, -1, -1, 266, -1, -1, -1, 266, -1, -1, -1, -1, 266, 266, -1, -1, 266, 266, 266, -1, -1, 266, -1, 266, 266, 266, -1, -1, -1, -1, 266, -1, -1, 266, -1, -1, -1, -1, 266, -1, 266, 266, 266, 266, -1, 266, -1, 266, 266, -1, 266, 266, -1, 266, -1, 266, -1, 266, -1, -1, 266, -1, 266, -1, 266, 266, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, 310, -1, -1, 310, -1, -1, -1, 310, -1, -1, -1, 310, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 310, -1, -1, -1, -1, -1, -1, -1, 310, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 310, -1, -1, -1, 310, -1, -1, -1, -1, 310, -1, 310, -1, -1, -1, -1, -1, -1, -1, -1, -1, 310, 310, -1, -1, 310, -1, -1, -1, -1, 310, -1, -1, -1, -1, 310, -1, -1, -1, -1, -1, -1, 310, -1, -1, -1, -1, -1, 310, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 310, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 316, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, 110, 110, 110, -1, -1, 110, 110, -1, 110, -1, -1, -1, 110, -1, 110, 110, 110, -1, -1, 110, -1, 110, -1, 110, 110, -1, -1, -1, -1, 110, -1, 110, 110, 201, 110, 110, -1, -1, 110, -1, 110, -1, 110, 110, -1, 110, -1, -1, 110, -1, -1, -1, 110, -1, -1, -1, 110, -1, -1, -1, -1, 110, 110, -1, -1, 110, 110, 110, -1, -1, 110, -1, 110, 110, 110, -1, -1, -1, -1, 110, -1, -1, 110, -1, -1, -1, -1, 110, -1, 110, 110, 110, 110, -1, 110, -1, 110, 110, -1, 110, 110, -1, 110, -1, 110, -1, 110, -1, -1, 110, -1, 110, -1, 110, 110, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 192, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 235, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 272, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 16, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 78, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [406, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 406, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 406, -1, -1, -1, -1, 406, -1, -1, -1, -1, -1, -1, -1, 401, -1, 406, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 406, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 214, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 145, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [210, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 210, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 210, -1, -1, -1, -1, 210, -1, -1, -1, -1, 100, -1, -1, 210, -1, 210, -1, -1, -1, -1, 100, -1, -1, 210, -1, -1, -1, -1, 100, 210, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, 301, -1, -1, -1, -1, 325, -1, -1, -1, -1, -1, -1, -1, 360, 26, -1, -1, -1, -1, -1, -1, -1, -1, 304, -1, -1, -1, -1, -1, -1, -1, -1, -1, 94, -1, -1, -1, 278, -1, -1, -1, -1, 463, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 81, 208, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 46, -1, -1, -1, -1, -1, -1, -1, 484, -1, -1, 443, -1, 250, -1, 354, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 370, -1, -1, -1, -1, 91, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 91, -1, -1, -1, -1, 91, -1, -1, -1, -1, -1, -1, -1, 91, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  ]
  def terminal(self, str):
    return self.str_terminal[str]
  def terminalNames(self):
    return list(self.str_terminal.keys())
  def isTerminal(self, id):
    return 0 <= id <= 120
  def isNonTerminal(self, id):
    return 121 <= id <= 245
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
  def parse(self, iterator):
    self.iterator = iter(iterator)
    self.sym = self.getsym()
    self.start = 'TRANSLATION_UNIT'
    tree = self._TRANSLATION_UNIT()
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
    return self.sym
  def expect(self, s, tracer):
    if self.sym and s == self.sym.getId():
      symbol = self.sym
      self.sym = self.next()
      return symbol
    else:
      raise SyntaxError('Unexpected symbol when parsing %s.  Expected %s, got %s.' %(whosdaddy(), self.terminal_str[s], self.sym if self.sym else 'None'), tracer)
  def rule(self, n):
    if self.sym == None: return -1
    return self.parse_table[n - 121][self.sym.getId()]
  def call(self, nt_str):
    return getattr(self, nt_str)()
  def _ENUM_SPECIFIER_BODY(self, depth=0, tracer=None):
    rule = self.rule(121)
    tree = ParseTree( NonTerminal(121, self.getAtomString(121)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 107:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(77, tracer) # lbrace
      tree.add(t)
      subtree = self.__GEN22(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self._TRAILING_COMMA_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(115, tracer) # rbrace
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _UNION_SPECIFIER(self, depth=0, tracer=None):
    rule = self.rule(122)
    tree = ParseTree( NonTerminal(122, self.getAtomString(122)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 392:
      tree.astTransform = AstTransformNodeCreator('Union', {'definition': 1})
      t = self.expect(38, tracer) # union
      tree.add(t)
      subtree = self._STRUCT_OR_UNION_SUB(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN21(self, depth=0, tracer=None):
    rule = self.rule(123)
    tree = ParseTree( NonTerminal(123, self.getAtomString(123)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [26, 88, 96, 46, 5, 102, 66, 28, 33, 70, 4, 78, 18, 19, 71, 21, 83, 86, 103, 38, 10, 93, 95, 52, 108, 34, 101, 39, 73, 106, 110, 47, 48, 0, 42, 6]):
      return tree
    if self.sym == None:
      return tree
    if rule == 312:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._ENUM_SPECIFIER_BODY(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN35(self, depth=0, tracer=None):
    rule = self.rule(124)
    tree = ParseTree( NonTerminal(124, self.getAtomString(124)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [74, 44, 23, 9, 33, 12, 16, 78, 18, 118, 25, 103, 27, 36, 108, 35, 39, 69, 28, 5, 46, 86, 100, 52, 56, 113, 96, 60, 76, 70, 4, 66, 77, 71, 83, 47, 38, 91, 10, 93, 94, 95, 65, 6, 101, 19, 104, 115, 106, 110, 20, 117, 42, 98]):
      return tree
    if self.sym == None:
      return tree
    if rule == 371:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._ELSE_STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN18(self, depth=0, tracer=None):
    rule = self.rule(125)
    tree = ParseTree( NonTerminal(125, self.getAtomString(125)), tracer )
    tree.list = 'slist'
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 417:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STRUCT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN19(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [73, 39, 78]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STRUCT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN19(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _DIRECT_DECLARATOR_EXPR(self, depth=0, tracer=None):
    rule = self.rule(126)
    tree = ParseTree( NonTerminal(126, self.getAtomString(126)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 211:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DIRECT_DECLARATOR_MODIFIER_LIST_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self._DIRECT_DECLARATOR_SIZE(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [91, 56, 16, 65, 98, 9, 39, 104, 60, 78, 12, 20, 117, 86]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DIRECT_DECLARATOR_MODIFIER_LIST_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self._DIRECT_DECLARATOR_SIZE(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    return tree
  def _STRUCT_DECLARATION(self, depth=0, tracer=None):
    rule = self.rule(127)
    tree = ParseTree( NonTerminal(127, self.getAtomString(127)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 339:
      tree.astTransform = AstTransformNodeCreator('StructOrUnionDeclaration', {'specifier_qualifiers': 0, 'declarators': 1})
      subtree = self.__GEN17(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN18(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(6, tracer) # semi
      tree.add(t)
      return tree
    elif self.sym.getId() in [73, 39, 78]:
      tree.astTransform = AstTransformNodeCreator('StructOrUnionDeclaration', {'specifier_qualifiers': 0, 'declarators': 1})
      subtree = self.__GEN17(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN18(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(6, tracer) ) # semi
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _DIRECT_ABSTRACT_DECLARATOR_OPT(self, depth=0, tracer=None):
    rule = self.rule(128)
    tree = ParseTree( NonTerminal(128, self.getAtomString(128)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [0, 88]):
      return tree
    if self.sym == None:
      return tree
    if rule == 230:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__DIRECT_ABSTRACT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [-1, 102, 78]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__DIRECT_ABSTRACT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    return tree
  def _PARAMETER_TYPE_LIST(self, depth=0, tracer=None):
    rule = self.rule(129)
    tree = ParseTree( NonTerminal(129, self.getAtomString(129)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 60:
      tree.astTransform = AstTransformNodeCreator('ParameterTypeList', {'parameter_declarations': 0, 'va_args': 1})
      subtree = self.__GEN26(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self._VA_ARGS(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN32(self, depth=0, tracer=None):
    rule = self.rule(130)
    tree = ParseTree( NonTerminal(130, self.getAtomString(130)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [115]):
      return tree
    if self.sym == None:
      return tree
    if rule == 336:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._BLOCK_ITEM_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [91, 56, 16, 65, 98, 9, 39, 104, 60, 78, 12, 20, 117, 86]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._BLOCK_ITEM_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    return tree
  def _ITERATION_STATEMENT(self, depth=0, tracer=None):
    rule = self.rule(131)
    tree = ParseTree( NonTerminal(131, self.getAtomString(131)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 97:
      tree.astTransform = AstTransformNodeCreator('For', {'init': 2, 'cond': 3, 'incr': 4})
      t = self.expect(74, tracer) # for
      tree.add(t)
      t = self.expect(78, tracer) # lparen
      tree.add(t)
      subtree = self._FOR_INIT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self._FOR_COND(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self._FOR_INCR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(105, tracer) # rparen
      tree.add(t)
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 367:
      tree.astTransform = AstTransformNodeCreator('While', {'expr': 2, 'statement': 4})
      t = self.expect(113, tracer) # while
      tree.add(t)
      t = self.expect(78, tracer) # lparen
      tree.add(t)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(105, tracer) # rparen
      tree.add(t)
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 382:
      tree.astTransform = AstTransformNodeCreator('DoWhile', {'expr': 4, 'statement': 1})
      t = self.expect(76, tracer) # do
      tree.add(t)
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(113, tracer) # while
      tree.add(t)
      t = self.expect(78, tracer) # lparen
      tree.add(t)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(105, tracer) # rparen
      tree.add(t)
      t = self.expect(6, tracer) # semi
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _DIRECT_DECLARATOR_MODIFIER_LIST_OPT(self, depth=0, tracer=None):
    rule = self.rule(132)
    tree = ParseTree( NonTerminal(132, self.getAtomString(132)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [91, 104, 56, 16, 39, 60, 65, 78, 98, 9, 12, 117, 86, 20]):
      return tree
    if self.sym == None:
      return tree
    if rule == 352:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN25(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN37(self, depth=0, tracer=None):
    rule = self.rule(133)
    tree = ParseTree( NonTerminal(133, self.getAtomString(133)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 218:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__EXPR_SANS_COMMA(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN38(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _DESIGNATOR(self, depth=0, tracer=None):
    rule = self.rule(134)
    tree = ParseTree( NonTerminal(134, self.getAtomString(134)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 59:
      tree.astTransform = AstTransformNodeCreator('MemberAccess', {'name': 1})
      t = self.expect(81, tracer) # dot
      tree.add(t)
      t = self.expect(39, tracer) # identifier
      tree.add(t)
      return tree
    elif rule == 396:
      tree.astTransform = AstTransformNodeCreator('ArrayAccess', {'index': 1})
      t = self.expect(67, tracer) # lsquare
      tree.add(t)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(99, tracer) # rsquare
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _DIRECT_DECLARATOR_PARAMETER_LIST(self, depth=0, tracer=None):
    rule = self.rule(135)
    tree = ParseTree( NonTerminal(135, self.getAtomString(135)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 174:
      tree.astTransform = AstTransformNodeCreator('ParameterList', {'identifiers': 0})
      subtree = self.__GEN28(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 378:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PARAMETER_TYPE_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _EXTERNAL_DECLARATOR(self, depth=0, tracer=None):
    rule = self.rule(136)
    tree = ParseTree( NonTerminal(136, self.getAtomString(136)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 279:
      tree.astTransform = AstTransformNodeCreator('ExternalDeclarator', {'init_declarator': 1})
      t = self.expect(48, tracer) # declarator_hint
      tree.add(t)
      subtree = self._INIT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN30(self, depth=0, tracer=None):
    rule = self.rule(137)
    tree = ParseTree( NonTerminal(137, self.getAtomString(137)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [0, 88]):
      return tree
    if self.sym == None:
      return tree
    if rule == 300:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PARAMETER_DECLARATION_SUB(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [-1, 102, 78]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PARAMETER_DECLARATION_SUB(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    elif self.sym.getId() in [73, 39, 78]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PARAMETER_DECLARATION_SUB(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    return tree
  def _FOR_COND(self, depth=0, tracer=None):
    rule = self.rule(138)
    tree = ParseTree( NonTerminal(138, self.getAtomString(138)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 329:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(6, tracer) # semi
      tree.add(t)
      subtree = self._EXPRESSION_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _JUMP_STATEMENT(self, depth=0, tracer=None):
    rule = self.rule(139)
    tree = ParseTree( NonTerminal(139, self.getAtomString(139)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 127:
      tree.astTransform = AstTransformNodeCreator('Goto', {'name': 1})
      t = self.expect(44, tracer) # goto
      tree.add(t)
      t = self.expect(39, tracer) # identifier
      tree.add(t)
      t = self.expect(6, tracer) # semi
      tree.add(t)
      return tree
    elif rule == 151:
      tree.astTransform = AstTransformNodeCreator('Return', {'expr': 1})
      t = self.expect(27, tracer) # return
      tree.add(t)
      subtree = self._EXPRESSION_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(6, tracer) # semi
      tree.add(t)
      return tree
    elif rule == 251:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(94, tracer) # continue
      tree.add(t)
      return tree
    elif rule == 368:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(25, tracer) # break
      tree.add(t)
      t = self.expect(6, tracer) # semi
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _FOR_INIT(self, depth=0, tracer=None):
    rule = self.rule(140)
    tree = ParseTree( NonTerminal(140, self.getAtomString(140)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [6]):
      return tree
    if self.sym == None:
      return tree
    if rule == 244:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DECLARATION(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self._EXPRESSION_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 475:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [91, 56, 16, 65, 98, 9, 39, 104, 60, 78, 12, 20, 117, 86]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    return tree
  def _PP(self, depth=0, tracer=None):
    rule = self.rule(141)
    tree = ParseTree( NonTerminal(141, self.getAtomString(141)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 6:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(8, tracer) # defined
      tree.add(t)
      return tree
    elif rule == 361:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(45, tracer) # defined_separator
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _STRUCT_DECLARATOR_BODY(self, depth=0, tracer=None):
    rule = self.rule(142)
    tree = ParseTree( NonTerminal(142, self.getAtomString(142)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 246:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(34, tracer) # colon
      tree.add(t)
      subtree = self._DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _EXTERNAL_DECLARATION_SUB_SUB(self, depth=0, tracer=None):
    rule = self.rule(143)
    tree = ParseTree( NonTerminal(143, self.getAtomString(143)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 84:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._EXTERNAL_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 132:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._EXTERNAL_PROTOTYPE(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _POINTER_OPT(self, depth=0, tracer=None):
    rule = self.rule(144)
    tree = ParseTree( NonTerminal(144, self.getAtomString(144)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [0, 73, 88, 78, 39, 102]):
      return tree
    if self.sym == None:
      return tree
    if rule == 313:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._POINTER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _LABELED_STATEMENT(self, depth=0, tracer=None):
    rule = self.rule(145)
    tree = ParseTree( NonTerminal(145, self.getAtomString(145)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 17:
      tree.astTransform = AstTransformNodeCreator('DefaultCase', {'statement': 2})
      t = self.expect(35, tracer) # default
      tree.add(t)
      t = self.expect(34, tracer) # colon
      tree.add(t)
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 45:
      tree.astTransform = AstTransformNodeCreator('Label', {'name': 0, 'statement': 1})
      t = self.expect(118, tracer) # label_hint
      tree.add(t)
      t = self.expect(39, tracer) # identifier
      tree.add(t)
      t = self.expect(34, tracer) # colon
      tree.add(t)
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 263:
      tree.astTransform = AstTransformNodeCreator('Case', {'expr': 1, 'statement': 3})
      t = self.expect(36, tracer) # case
      tree.add(t)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(34, tracer) # colon
      tree.add(t)
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN36(self, depth=0, tracer=None):
    rule = self.rule(146)
    tree = ParseTree( NonTerminal(146, self.getAtomString(146)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [74, 44, 23, 9, 33, 12, 16, 78, 18, 118, 25, 103, 27, 36, 108, 35, 39, 69, 28, 5, 49, 46, 86, 100, 52, 56, 113, 96, 60, 76, 70, 4, 66, 77, 71, 83, 47, 38, 91, 10, 93, 94, 95, 65, 6, 101, 19, 104, 115, 106, 110, 20, 117, 42, 98]):
      return tree
    if self.sym == None:
      return tree
    if rule == 328:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._ELSE_IF_STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN36(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _SELECTION_STATEMENT(self, depth=0, tracer=None):
    rule = self.rule(147)
    tree = ParseTree( NonTerminal(147, self.getAtomString(147)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 241:
      tree.astTransform = AstTransformNodeCreator('If', {'elseif': 6, 'statement': 4, 'condition': 2, 'else': 7})
      t = self.expect(23, tracer) # if
      tree.add(t)
      t = self.expect(78, tracer) # lparen
      tree.add(t)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(105, tracer) # rparen
      tree.add(t)
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(69, tracer) # endif
      tree.add(t)
      subtree = self.__GEN34(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN35(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 385:
      tree.astTransform = AstTransformNodeCreator('Switch', {'expr': 2, 'statment': 4})
      t = self.expect(100, tracer) # switch
      tree.add(t)
      t = self.expect(78, tracer) # lparen
      tree.add(t)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(105, tracer) # rparen
      tree.add(t)
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _ENUMERATOR(self, depth=0, tracer=None):
    rule = self.rule(148)
    tree = ParseTree( NonTerminal(148, self.getAtomString(148)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 209:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._ENUMERATION_CONSTANT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self._ENUMERATOR_ASSIGNMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN22(self, depth=0, tracer=None):
    rule = self.rule(149)
    tree = ParseTree( NonTerminal(149, self.getAtomString(149)), tracer )
    tree.list = 'slist'
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 198:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._ENUMERATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN23(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _ENUM_SPECIFIER(self, depth=0, tracer=None):
    rule = self.rule(151)
    tree = ParseTree( NonTerminal(151, self.getAtomString(151)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 182:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(106, tracer) # enum
      tree.add(t)
      subtree = self._ENUM_SPECIFIER_SUB(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN23(self, depth=0, tracer=None):
    rule = self.rule(152)
    tree = ParseTree( NonTerminal(152, self.getAtomString(152)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in [55]):
      return tree
    if self.sym == None:
      return tree
    if rule == 38:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(0, tracer) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self._ENUMERATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN23(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _DECLARATOR(self, depth=0, tracer=None):
    rule = self.rule(153)
    tree = ParseTree( NonTerminal(153, self.getAtomString(153)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 47:
      tree.astTransform = AstTransformNodeCreator('Declarator', {'direct_declarator': 1, 'pointer': 0})
      subtree = self._POINTER_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__DIRECT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [73, 39, 78]:
      tree.astTransform = AstTransformNodeCreator('Declarator', {'direct_declarator': 1, 'pointer': 0})
      subtree = self._POINTER_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__DIRECT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _STATIC_OPT(self, depth=0, tracer=None):
    rule = self.rule(154)
    tree = ParseTree( NonTerminal(154, self.getAtomString(154)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [91, 104, 56, 16, 39, 60, 65, 78, 98, 9, 12, 117, 86, 20]):
      return tree
    if self.sym == None:
      return tree
    if rule == 37:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(96, tracer) # static
      tree.add(t)
      return tree
    return tree
  def _DECLARATION_LIST(self, depth=0, tracer=None):
    rule = self.rule(155)
    tree = ParseTree( NonTerminal(155, self.getAtomString(155)), tracer )
    tree.list = False
    if self.sym == None:
      return tree
    if rule == 403:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN6(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN5(self, depth=0, tracer=None):
    rule = self.rule(156)
    tree = ParseTree( NonTerminal(156, self.getAtomString(156)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [77, 6, 0]):
      return tree
    if self.sym == None:
      return tree
    if rule == 284:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DECLARATION_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN29(self, depth=0, tracer=None):
    rule = self.rule(157)
    tree = ParseTree( NonTerminal(157, self.getAtomString(157)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 20:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(0, tracer) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self._IDENTIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN29(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _DECLARATION_SPECIFIER(self, depth=0, tracer=None):
    rule = self.rule(158)
    tree = ParseTree( NonTerminal(158, self.getAtomString(158)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 66:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._TYPE_QUALIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 68:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._TYPE_SPECIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 264:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STORAGE_CLASS_SPECIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 317:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._FUNCTION_SPECIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _EXTERNAL_DECLARATION_SUB(self, depth=0, tracer=None):
    rule = self.rule(159)
    tree = ParseTree( NonTerminal(159, self.getAtomString(159)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 5:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._EXTERNAL_FUNCTION(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 70:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN3(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(6, tracer) # semi
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _SIZEOF_BODY(self, depth=0, tracer=None):
    rule = self.rule(160)
    tree = ParseTree( NonTerminal(160, self.getAtomString(160)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 478:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(78, tracer) # lparen
      tree.add(t)
      subtree = self._TYPE_NAME(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(105, tracer) # rparen
      tree.add(t)
      return tree
    elif rule == 487:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(39, tracer) # identifier
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _SPECIFIER_QUALIFIER(self, depth=0, tracer=None):
    rule = self.rule(161)
    tree = ParseTree( NonTerminal(161, self.getAtomString(161)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 337:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._TYPE_SPECIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 394:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._TYPE_QUALIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _EXTERNAL_DECLARATION(self, depth=0, tracer=None):
    rule = self.rule(162)
    tree = ParseTree( NonTerminal(162, self.getAtomString(162)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 502:
      tree.astTransform = AstTransformNodeCreator('ExternalDeclaration', {'declarations': 2, 'declaration_specifiers': 1})
      t = self.expect(13, tracer) # external_declaration_hint
      tree.add(t)
      subtree = self.__GEN1(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self._EXTERNAL_DECLARATION_SUB(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN14(self, depth=0, tracer=None):
    rule = self.rule(163)
    tree = ParseTree( NonTerminal(163, self.getAtomString(163)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [31]):
      return tree
    if self.sym == None:
      return tree
    if rule == 18:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DESIGNATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN14(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN0(self, depth=0, tracer=None):
    rule = self.rule(164)
    tree = ParseTree( NonTerminal(164, self.getAtomString(164)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [-1]):
      return tree
    if self.sym == None:
      return tree
    if rule == 281:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._EXTERNAL_DECLARATION(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN0(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _DIRECT_DECLARATOR_MODIFIER(self, depth=0, tracer=None):
    rule = self.rule(165)
    tree = ParseTree( NonTerminal(165, self.getAtomString(165)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 369:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._TYPE_QUALIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 501:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(96, tracer) # static
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN20(self, depth=0, tracer=None):
    rule = self.rule(166)
    tree = ParseTree( NonTerminal(166, self.getAtomString(166)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [0, 6]):
      return tree
    if self.sym == None:
      return tree
    if rule == 258:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STRUCT_DECLARATOR_BODY(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _COMPOUND_STATEMENT(self, depth=0, tracer=None):
    rule = self.rule(167)
    tree = ParseTree( NonTerminal(167, self.getAtomString(167)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 307:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(77, tracer) # lbrace
      tree.add(t)
      subtree = self.__GEN32(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(115, tracer) # rbrace
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _TYPE_QUALIFIER(self, depth=0, tracer=None):
    rule = self.rule(168)
    tree = ParseTree( NonTerminal(168, self.getAtomString(168)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 160:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(93, tracer) # restrict
      tree.add(t)
      return tree
    elif rule == 162:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(101, tracer) # volatile
      tree.add(t)
      return tree
    elif rule == 294:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(83, tracer) # const
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _CONSTANT(self, depth=0, tracer=None):
    rule = self.rule(169)
    tree = ParseTree( NonTerminal(169, self.getAtomString(169)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 29:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(9, tracer) # character_constant
      tree.add(t)
      return tree
    elif rule == 114:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(56, tracer) # enumeration_constant
      tree.add(t)
      return tree
    elif rule == 121:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(65, tracer) # integer_constant
      tree.add(t)
      return tree
    elif rule == 308:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(12, tracer) # floating_constant
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _TYPE_NAME(self, depth=0, tracer=None):
    rule = self.rule(170)
    tree = ParseTree( NonTerminal(170, self.getAtomString(170)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 3:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(95, tracer) # char
      tree.add(t)
      return tree
    elif rule == 333:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(110, tracer) # int
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN4(self, depth=0, tracer=None):
    rule = self.rule(171)
    tree = ParseTree( NonTerminal(171, self.getAtomString(171)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in [6]):
      return tree
    if self.sym == None:
      return tree
    if rule == 359:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(0, tracer) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self._EXTERNAL_DECLARATION_SUB_SUB(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN4(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _ENUMERATION_CONSTANT(self, depth=0, tracer=None):
    rule = self.rule(172)
    tree = ParseTree( NonTerminal(172, self.getAtomString(172)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 43:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(39, tracer) # identifier
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN28(self, depth=0, tracer=None):
    rule = self.rule(173)
    tree = ParseTree( NonTerminal(173, self.getAtomString(173)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 399:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._IDENTIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN29(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _ENUMERATOR_ASSIGNMENT(self, depth=0, tracer=None):
    rule = self.rule(174)
    tree = ParseTree( NonTerminal(174, self.getAtomString(174)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [0, 55]):
      return tree
    if self.sym == None:
      return tree
    if rule == 462:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(31, tracer) # assign
      tree.add(t)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _TYPE_QUALIFIER_LIST_OPT(self, depth=0, tracer=None):
    rule = self.rule(175)
    tree = ParseTree( NonTerminal(175, self.getAtomString(175)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [0, 73, 88, 78, 96, 39, 102, 86]):
      return tree
    if self.sym == None:
      return tree
    if rule == 111:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN24(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN25(self, depth=0, tracer=None):
    rule = self.rule(176)
    tree = ParseTree( NonTerminal(176, self.getAtomString(176)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [91, 104, 56, 16, 39, 65, 78, 98, 9, 12, 60, 117, 86, 20]):
      return tree
    if self.sym == None:
      return tree
    if rule == 314:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DIRECT_DECLARATOR_MODIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN25(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _INIT_DECLARATOR(self, depth=0, tracer=None):
    rule = self.rule(177)
    tree = ParseTree( NonTerminal(177, self.getAtomString(177)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 101:
      tree.astTransform = AstTransformNodeCreator('InitDeclarator', {'initializer': 1, 'declarator': 0})
      subtree = self._DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN10(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [73, 39, 78]:
      tree.astTransform = AstTransformNodeCreator('InitDeclarator', {'initializer': 1, 'declarator': 0})
      subtree = self._DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN10(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _TRAILING_COMMA_OPT(self, depth=0, tracer=None):
    rule = self.rule(178)
    tree = ParseTree( NonTerminal(178, self.getAtomString(178)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [115]):
      return tree
    if self.sym == None:
      return tree
    if rule == 332:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(55, tracer) # trailing_comma
      tree.add(t)
      return tree
    return tree
  def _EXPRESSION_STATEMENT(self, depth=0, tracer=None):
    rule = self.rule(179)
    tree = ParseTree( NonTerminal(179, self.getAtomString(179)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 2:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._EXPRESSION_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(6, tracer) # semi
      tree.add(t)
      return tree
    elif self.sym.getId() in [91, 56, 16, 65, 98, 9, 39, 104, 60, 78, 12, 20, 117, 86]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._EXPRESSION_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(6, tracer) ) # semi
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _DIRECT_ABSTRACT_DECLARATOR_EXPR(self, depth=0, tracer=None):
    rule = self.rule(180)
    tree = ParseTree( NonTerminal(180, self.getAtomString(180)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 381:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._TYPE_QUALIFIER_LIST_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self._STATIC_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 424:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(86, tracer) # asterisk
      tree.add(t)
      return tree
    elif self.sym.getId() in [91, 56, 16, 65, 98, 9, 39, 104, 60, 78, 12, 20, 117, 86]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._TYPE_QUALIFIER_LIST_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self._STATIC_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    return tree
  def __GEN8(self, depth=0, tracer=None):
    rule = self.rule(181)
    tree = ParseTree( NonTerminal(181, self.getAtomString(181)), tracer )
    tree.list = 'slist'
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 249:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._INIT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN9(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [73, 39, 78]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._INIT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN9(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN16(self, depth=0, tracer=None):
    rule = self.rule(182)
    tree = ParseTree( NonTerminal(182, self.getAtomString(182)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [115]):
      return tree
    if self.sym == None:
      return tree
    if rule == 228:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STRUCT_DECLARATION(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN16(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [73, 39, 78]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STRUCT_DECLARATION(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN16(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    return tree
  def _EXPRESSION_OPT(self, depth=0, tracer=None):
    rule = self.rule(183)
    tree = ParseTree( NonTerminal(183, self.getAtomString(183)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [105, 6]):
      return tree
    if self.sym == None:
      return tree
    if rule == 449:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [91, 56, 16, 65, 98, 9, 39, 104, 60, 78, 12, 20, 117, 86]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    return tree
  def _PARAMETER_TYPE_LIST_OPT(self, depth=0, tracer=None):
    rule = self.rule(184)
    tree = ParseTree( NonTerminal(184, self.getAtomString(184)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 391:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PARAMETER_TYPE_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _PARAMETER_DECLARATION_SUB(self, depth=0, tracer=None):
    rule = self.rule(185)
    tree = ParseTree( NonTerminal(185, self.getAtomString(185)), tracer )
    tree.list = False
    if self.sym == None:
      return tree
    if rule == 13:
      tree.astTransform = AstTransformNodeCreator('ParameterSub', {'name_and_size': 1, 'pointer': 0})
      subtree = self._POINTER_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self._PARAMETER_DECLARATION_SUB_SUB(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [-1, 102, 78]:
      tree.astTransform = AstTransformNodeCreator('ParameterSub', {'name_and_size': 1, 'pointer': 0})
      subtree = self._POINTER_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self._PARAMETER_DECLARATION_SUB_SUB(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    elif self.sym.getId() in [73, 39, 78]:
      tree.astTransform = AstTransformNodeCreator('ParameterSub', {'name_and_size': 1, 'pointer': 0})
      subtree = self._POINTER_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self._PARAMETER_DECLARATION_SUB_SUB(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN19(self, depth=0, tracer=None):
    rule = self.rule(186)
    tree = ParseTree( NonTerminal(186, self.getAtomString(186)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in [6]):
      return tree
    if self.sym == None:
      return tree
    if rule == 191:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(0, tracer) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self._STRUCT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN19(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _EXTERNAL_PROTOTYPE(self, depth=0, tracer=None):
    rule = self.rule(187)
    tree = ParseTree( NonTerminal(187, self.getAtomString(187)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 446:
      tree.astTransform = AstTransformNodeCreator('FunctionPrototype', {'declaration_list': 2, 'declarator': 1})
      t = self.expect(21, tracer) # function_prototype_hint
      tree.add(t)
      subtree = self._DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN5(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _BLOCK_ITEM(self, depth=0, tracer=None):
    rule = self.rule(188)
    tree = ParseTree( NonTerminal(188, self.getAtomString(188)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 196:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DECLARATION(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 311:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [91, 56, 16, 65, 98, 9, 39, 104, 60, 78, 12, 20, 117, 86]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _STORAGE_CLASS_SPECIFIER(self, depth=0, tracer=None):
    rule = self.rule(189)
    tree = ParseTree( NonTerminal(189, self.getAtomString(189)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 28:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(4, tracer) # register
      tree.add(t)
      return tree
    elif rule == 36:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(46, tracer) # typedef
      tree.add(t)
      return tree
    elif rule == 92:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(66, tracer) # auto
      tree.add(t)
      return tree
    elif rule == 283:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(52, tracer) # extern
      tree.add(t)
      return tree
    elif rule == 435:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(96, tracer) # static
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _INITIALIZER(self, depth=0, tracer=None):
    rule = self.rule(190)
    tree = ParseTree( NonTerminal(190, self.getAtomString(190)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 293:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(77, tracer) # lbrace
      tree.add(t)
      subtree = self.__GEN11(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self._TRAILING_COMMA_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(115, tracer) # rbrace
      tree.add(t)
      return tree
    elif rule == 321:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [91, 56, 16, 65, 98, 9, 39, 104, 60, 78, 12, 20, 117, 86]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN1(self, depth=0, tracer=None):
    rule = self.rule(191)
    tree = ParseTree( NonTerminal(191, self.getAtomString(191)), tracer )
    tree.list = 'mlist'
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 309:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DECLARATION_SPECIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN2(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _INITIALIZER_LIST_ITEM(self, depth=0, tracer=None):
    rule = self.rule(192)
    tree = ParseTree( NonTerminal(192, self.getAtomString(192)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 295:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(65, tracer) # integer_constant
      tree.add(t)
      return tree
    elif rule == 363:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN13(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self._INITIALIZER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [91, 56, 16, 65, 98, 9, 39, 104, 60, 78, 12, 20, 117, 86]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN13(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self._INITIALIZER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN38(self, depth=0, tracer=None):
    rule = self.rule(193)
    tree = ParseTree( NonTerminal(193, self.getAtomString(193)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 137:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(0, tracer) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self.__EXPR_SANS_COMMA(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN38(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN2(self, depth=0, tracer=None):
    rule = self.rule(194)
    tree = ParseTree( NonTerminal(194, self.getAtomString(194)), tracer )
    tree.list = 'mlist'
    if self.sym != None and (self.sym.getId() in [26, 73, 88, 78, 86, 102, 6, 21, 0, 39, 48]):
      return tree
    if self.sym == None:
      return tree
    if rule == 489:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DECLARATION_SPECIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN2(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _POINTER(self, depth=0, tracer=None):
    rule = self.rule(195)
    tree = ParseTree( NonTerminal(195, self.getAtomString(195)), tracer )
    tree.list = False
    if self.sym == None:
      return tree
    if rule == 275:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN31(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _DECLARATION(self, depth=0, tracer=None):
    rule = self.rule(196)
    tree = ParseTree( NonTerminal(196, self.getAtomString(196)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 247:
      tree.astTransform = AstTransformNodeCreator('Declaration', {'init_declarators': 1, 'declaration_specifiers': 0})
      subtree = self.__GEN1(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN7(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(6, tracer) # semi
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _ABSTRACT_DECLARATOR(self, depth=0, tracer=None):
    rule = self.rule(197)
    tree = ParseTree( NonTerminal(197, self.getAtomString(197)), tracer )
    tree.list = False
    if self.sym == None:
      return tree
    if rule == 287:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._POINTER_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self._DIRECT_ABSTRACT_DECLARATOR_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [-1, 102, 78]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._POINTER_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self._DIRECT_ABSTRACT_DECLARATOR_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN17(self, depth=0, tracer=None):
    rule = self.rule(198)
    tree = ParseTree( NonTerminal(198, self.getAtomString(198)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [73, 34, 86, 39, 78]):
      return tree
    if self.sym == None:
      return tree
    if rule == 79:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._SPECIFIER_QUALIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN17(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN6(self, depth=0, tracer=None):
    rule = self.rule(199)
    tree = ParseTree( NonTerminal(199, self.getAtomString(199)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [77, 6, 0]):
      return tree
    if self.sym == None:
      return tree
    if rule == 331:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DECLARATION(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN6(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _BLOCK_ITEM_LIST(self, depth=0, tracer=None):
    rule = self.rule(200)
    tree = ParseTree( NonTerminal(200, self.getAtomString(200)), tracer )
    tree.list = False
    if self.sym == None:
      return tree
    if rule == 404:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN33(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [91, 56, 16, 65, 98, 9, 39, 104, 60, 78, 12, 20, 117, 86]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN33(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _TYPEDEF_NAME(self, depth=0, tracer=None):
    rule = self.rule(201)
    tree = ParseTree( NonTerminal(201, self.getAtomString(201)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 419:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(70, tracer) # typedef_identifier
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _TRANSLATION_UNIT(self, depth=0, tracer=None):
    rule = self.rule(202)
    tree = ParseTree( NonTerminal(202, self.getAtomString(202)), tracer )
    tree.list = False
    if self.sym == None:
      return tree
    if rule == 217:
      tree.astTransform = AstTransformNodeCreator('TranslationUnit', {'external_declarations': 0})
      subtree = self.__GEN0(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _STRUCT_SPECIFIER(self, depth=0, tracer=None):
    rule = self.rule(203)
    tree = ParseTree( NonTerminal(203, self.getAtomString(203)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 349:
      tree.astTransform = AstTransformNodeCreator('Struct', {'definition': 1})
      t = self.expect(71, tracer) # struct
      tree.add(t)
      subtree = self._STRUCT_OR_UNION_SUB(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _DECLARATOR_INITIALIZER(self, depth=0, tracer=None):
    rule = self.rule(204)
    tree = ParseTree( NonTerminal(204, self.getAtomString(204)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 342:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(31, tracer) # assign
      tree.add(t)
      subtree = self._INITIALIZER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _PARAMETER_DECLARATION_SUB_SUB(self, depth=0, tracer=None):
    rule = self.rule(205)
    tree = ParseTree( NonTerminal(205, self.getAtomString(205)), tracer )
    tree.list = False
    if self.sym == None:
      return tree
    if rule == 115:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DIRECT_ABSTRACT_DECLARATOR_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 185:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__DIRECT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [-1, 102, 78]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DIRECT_ABSTRACT_DECLARATOR_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    elif self.sym.getId() in [73, 39, 78]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__DIRECT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _STATEMENT(self, depth=0, tracer=None):
    rule = self.rule(206)
    tree = ParseTree( NonTerminal(206, self.getAtomString(206)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 31:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._JUMP_STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 136:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._EXPRESSION_STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 318:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._COMPOUND_STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 348:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._LABELED_STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 353:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._SELECTION_STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 356:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._ITERATION_STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [91, 56, 16, 65, 98, 9, 39, 104, 60, 78, 12, 20, 117, 86]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._EXPRESSION_STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _TOKEN(self, depth=0, tracer=None):
    rule = self.rule(207)
    tree = ParseTree( NonTerminal(207, self.getAtomString(207)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 44:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._KEYWORD(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 296:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(39, tracer) # identifier
      tree.add(t)
      return tree
    elif rule == 362:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(104, tracer) # string_literal
      tree.add(t)
      return tree
    elif rule == 366:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PUNCTUATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 420:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._CONSTANT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 496:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(2, tracer) # pp_number
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _PUNCTUATOR(self, depth=0, tracer=None):
    rule = self.rule(208)
    tree = ParseTree( NonTerminal(208, self.getAtomString(208)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 0:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(81, tracer) # dot
      tree.add(t)
      return tree
    elif rule == 7:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(77, tracer) # lbrace
      tree.add(t)
      return tree
    elif rule == 9:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(7, tracer) # modeq
      tree.add(t)
      return tree
    elif rule == 62:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(24, tracer) # bitor
      tree.add(t)
      return tree
    elif rule == 63:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(1, tracer) # exclamation_point
      tree.add(t)
      return tree
    elif rule == 102:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(11, tracer) # tilde
      tree.add(t)
      return tree
    elif rule == 104:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(14, tracer) # rshifteq
      tree.add(t)
      return tree
    elif rule == 105:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(115, tracer) # rbrace
      tree.add(t)
      return tree
    elif rule == 123:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(22, tracer) # lshifteq
      tree.add(t)
      return tree
    elif rule == 128:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(64, tracer) # subeq
      tree.add(t)
      return tree
    elif rule == 133:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(0, tracer) # comma
      tree.add(t)
      return tree
    elif rule == 153:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(105, tracer) # rparen
      tree.add(t)
      return tree
    elif rule == 161:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(87, tracer) # bitxoreq
      tree.add(t)
      return tree
    elif rule == 165:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(43, tracer) # add
      tree.add(t)
      return tree
    elif rule == 177:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(111, tracer) # lt
      tree.add(t)
      return tree
    elif rule == 187:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(31, tracer) # assign
      tree.add(t)
      return tree
    elif rule == 195:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(107, tracer) # poundpound
      tree.add(t)
      return tree
    elif rule == 197:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(112, tracer) # bitoreq
      tree.add(t)
      return tree
    elif rule == 200:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(29, tracer) # bitandeq
      tree.add(t)
      return tree
    elif rule == 213:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(6, tracer) # semi
      tree.add(t)
      return tree
    elif rule == 224:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(109, tracer) # gt
      tree.add(t)
      return tree
    elif rule == 245:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(20, tracer) # decr
      tree.add(t)
      return tree
    elif rule == 255:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(99, tracer) # rsquare
      tree.add(t)
      return tree
    elif rule == 256:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(41, tracer) # eq
      tree.add(t)
      return tree
    elif rule == 269:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(120, tracer) # ampersand
      tree.add(t)
      return tree
    elif rule == 298:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(72, tracer) # div
      tree.add(t)
      return tree
    elif rule == 319:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(53, tracer) # neq
      tree.add(t)
      return tree
    elif rule == 324:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(89, tracer) # gteq
      tree.add(t)
      return tree
    elif rule == 341:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(85, tracer) # muleq
      tree.add(t)
      return tree
    elif rule == 344:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(78, tracer) # lparen
      tree.add(t)
      return tree
    elif rule == 364:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(60, tracer) # incr
      tree.add(t)
      return tree
    elif rule == 379:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(75, tracer) # sub
      tree.add(t)
      return tree
    elif rule == 383:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(63, tracer) # addeq
      tree.add(t)
      return tree
    elif rule == 389:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(32, tracer) # pound
      tree.add(t)
      return tree
    elif rule == 409:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(92, tracer) # arrow
      tree.add(t)
      return tree
    elif rule == 411:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(68, tracer) # and
      tree.add(t)
      return tree
    elif rule == 422:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(58, tracer) # elipsis
      tree.add(t)
      return tree
    elif rule == 430:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(79, tracer) # questionmark
      tree.add(t)
      return tree
    elif rule == 453:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(15, tracer) # lteq
      tree.add(t)
      return tree
    elif rule == 464:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(17, tracer) # mod
      tree.add(t)
      return tree
    elif rule == 465:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(57, tracer) # bitxor
      tree.add(t)
      return tree
    elif rule == 470:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(34, tracer) # colon
      tree.add(t)
      return tree
    elif rule == 483:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(67, tracer) # lsquare
      tree.add(t)
      return tree
    elif rule == 486:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(40, tracer) # lshift
      tree.add(t)
      return tree
    elif rule == 488:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(97, tracer) # rshift
      tree.add(t)
      return tree
    elif rule == 505:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(61, tracer) # or
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _DIRECT_DECLARATOR_SIZE(self, depth=0, tracer=None):
    rule = self.rule(209)
    tree = ParseTree( NonTerminal(209, self.getAtomString(209)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 257:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 426:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(86, tracer) # asterisk
      tree.add(t)
      return tree
    elif self.sym.getId() in [91, 56, 16, 65, 98, 9, 39, 104, 60, 78, 12, 20, 117, 86]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _ELSE_IF_STATEMENT(self, depth=0, tracer=None):
    rule = self.rule(210)
    tree = ParseTree( NonTerminal(210, self.getAtomString(210)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 290:
      tree.astTransform = AstTransformNodeCreator('ElseIf', {'statement': 4, 'condition': 2})
      t = self.expect(37, tracer) # else_if
      tree.add(t)
      t = self.expect(78, tracer) # lparen
      tree.add(t)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(105, tracer) # rparen
      tree.add(t)
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(69, tracer) # endif
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _FOR_INCR(self, depth=0, tracer=None):
    rule = self.rule(211)
    tree = ParseTree( NonTerminal(211, self.getAtomString(211)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [105]):
      return tree
    if self.sym == None:
      return tree
    if rule == 144:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(6, tracer) # semi
      tree.add(t)
      subtree = self._EXPRESSION_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN12(self, depth=0, tracer=None):
    rule = self.rule(212)
    tree = ParseTree( NonTerminal(212, self.getAtomString(212)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in [55]):
      return tree
    if self.sym == None:
      return tree
    if rule == 338:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(0, tracer) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self._INITIALIZER_LIST_ITEM(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN12(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN13(self, depth=0, tracer=None):
    rule = self.rule(213)
    tree = ParseTree( NonTerminal(213, self.getAtomString(213)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [91, 56, 60, 65, 98, 9, 78, 104, 12, 16, 39, 77, 20, 117, 86]):
      return tree
    if self.sym == None:
      return tree
    if rule == 225:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DESIGNATION(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _EXTERNAL_FUNCTION(self, depth=0, tracer=None):
    rule = self.rule(214)
    tree = ParseTree( NonTerminal(214, self.getAtomString(214)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 397:
      tree.astTransform = AstTransformNodeCreator('FunctionDefinition', {'body': 3, 'declaration_list': 2, 'signature': 1})
      t = self.expect(26, tracer) # function_definition_hint
      tree.add(t)
      subtree = self._DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN5(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self._COMPOUND_STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _FUNCTION_SPECIFIER(self, depth=0, tracer=None):
    rule = self.rule(215)
    tree = ParseTree( NonTerminal(215, self.getAtomString(215)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 19:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(33, tracer) # inline
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN33(self, depth=0, tracer=None):
    rule = self.rule(216)
    tree = ParseTree( NonTerminal(216, self.getAtomString(216)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [115]):
      return tree
    if self.sym == None:
      return tree
    if rule == 450:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._BLOCK_ITEM(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN33(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [91, 56, 16, 65, 98, 9, 39, 104, 60, 78, 12, 20, 117, 86]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._BLOCK_ITEM(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN33(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    return tree
  def _INIT_DECLARATOR_LIST(self, depth=0, tracer=None):
    rule = self.rule(217)
    tree = ParseTree( NonTerminal(217, self.getAtomString(217)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 261:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN8(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [73, 39, 78]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN8(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN7(self, depth=0, tracer=None):
    rule = self.rule(218)
    tree = ParseTree( NonTerminal(218, self.getAtomString(218)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [6]):
      return tree
    if self.sym == None:
      return tree
    if rule == 340:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._INIT_DECLARATOR_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [73, 39, 78]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._INIT_DECLARATOR_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    return tree
  def _TERMINALS(self, depth=0, tracer=None):
    rule = self.rule(219)
    tree = ParseTree( NonTerminal(219, self.getAtomString(219)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 1:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(54, tracer) # bool
      tree.add(t)
      return tree
    elif rule == 10:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(115, tracer) # rbrace
      tree.add(t)
      return tree
    elif rule == 15:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(3, tracer) # hexadecimal_floating_constant
      tree.add(t)
      return tree
    elif rule == 21:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(53, tracer) # neq
      tree.add(t)
      return tree
    elif rule == 30:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(49, tracer) # else
      tree.add(t)
      return tree
    elif rule == 32:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(94, tracer) # continue
      tree.add(t)
      return tree
    elif rule == 49:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(78, tracer) # lparen
      tree.add(t)
      return tree
    elif rule == 51:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(99, tracer) # rsquare
      tree.add(t)
      return tree
    elif rule == 55:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(92, tracer) # arrow
      tree.add(t)
      return tree
    elif rule == 57:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(72, tracer) # div
      tree.add(t)
      return tree
    elif rule == 61:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(105, tracer) # rparen
      tree.add(t)
      return tree
    elif rule == 64:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(34, tracer) # colon
      tree.add(t)
      return tree
    elif rule == 67:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(17, tracer) # mod
      tree.add(t)
      return tree
    elif rule == 69:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(114, tracer) # decimal_floating_constant
      tree.add(t)
      return tree
    elif rule == 72:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(42, tracer) # long
      tree.add(t)
      return tree
    elif rule == 75:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(38, tracer) # union
      tree.add(t)
      return tree
    elif rule == 77:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(103, tracer) # unsigned
      tree.add(t)
      return tree
    elif rule == 80:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(61, tracer) # or
      tree.add(t)
      return tree
    elif rule == 82:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(106, tracer) # enum
      tree.add(t)
      return tree
    elif rule == 83:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(11, tracer) # tilde
      tree.add(t)
      return tree
    elif rule == 89:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(16, tracer) # bitand
      tree.add(t)
      return tree
    elif rule == 95:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(27, tracer) # return
      tree.add(t)
      return tree
    elif rule == 96:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(104, tracer) # string_literal
      tree.add(t)
      return tree
    elif rule == 99:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(47, tracer) # void
      tree.add(t)
      return tree
    elif rule == 106:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(44, tracer) # goto
      tree.add(t)
      return tree
    elif rule == 108:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(31, tracer) # assign
      tree.add(t)
      return tree
    elif rule == 109:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(82, tracer) # not
      tree.add(t)
      return tree
    elif rule == 116:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(35, tracer) # default
      tree.add(t)
      return tree
    elif rule == 117:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(71, tracer) # struct
      tree.add(t)
      return tree
    elif rule == 122:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(41, tracer) # eq
      tree.add(t)
      return tree
    elif rule == 139:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(6, tracer) # semi
      tree.add(t)
      return tree
    elif rule == 147:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(25, tracer) # break
      tree.add(t)
      return tree
    elif rule == 154:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(5, tracer) # float
      tree.add(t)
      return tree
    elif rule == 155:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(43, tracer) # add
      tree.add(t)
      return tree
    elif rule == 157:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(39, tracer) # identifier
      tree.add(t)
      return tree
    elif rule == 159:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(10, tracer) # double
      tree.add(t)
      return tree
    elif rule == 163:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(36, tracer) # case
      tree.add(t)
      return tree
    elif rule == 170:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(59, tracer) # universal_character_name
      tree.add(t)
      return tree
    elif rule == 180:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(79, tracer) # questionmark
      tree.add(t)
      return tree
    elif rule == 181:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(119, tracer) # imaginary
      tree.add(t)
      return tree
    elif rule == 183:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(64, tracer) # subeq
      tree.add(t)
      return tree
    elif rule == 188:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(9, tracer) # character_constant
      tree.add(t)
      return tree
    elif rule == 189:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(76, tracer) # do
      tree.add(t)
      return tree
    elif rule == 204:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(85, tracer) # muleq
      tree.add(t)
      return tree
    elif rule == 206:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(33, tracer) # inline
      tree.add(t)
      return tree
    elif rule == 212:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(77, tracer) # lbrace
      tree.add(t)
      return tree
    elif rule == 219:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(110, tracer) # int
      tree.add(t)
      return tree
    elif rule == 221:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(15, tracer) # lteq
      tree.add(t)
      return tree
    elif rule == 226:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(100, tracer) # switch
      tree.add(t)
      return tree
    elif rule == 231:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(23, tracer) # if
      tree.add(t)
      return tree
    elif rule == 232:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(112, tracer) # bitoreq
      tree.add(t)
      return tree
    elif rule == 238:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(75, tracer) # sub
      tree.add(t)
      return tree
    elif rule == 239:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(65, tracer) # integer_constant
      tree.add(t)
      return tree
    elif rule == 240:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(101, tracer) # volatile
      tree.add(t)
      return tree
    elif rule == 243:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(14, tracer) # rshifteq
      tree.add(t)
      return tree
    elif rule == 248:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(51, tracer) # header_name
      tree.add(t)
      return tree
    elif rule == 259:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(40, tracer) # lshift
      tree.add(t)
      return tree
    elif rule == 273:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(80, tracer) # complex
      tree.add(t)
      return tree
    elif rule == 276:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(96, tracer) # static
      tree.add(t)
      return tree
    elif rule == 277:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(22, tracer) # lshifteq
      tree.add(t)
      return tree
    elif rule == 288:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(67, tracer) # lsquare
      tree.add(t)
      return tree
    elif rule == 289:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(113, tracer) # while
      tree.add(t)
      return tree
    elif rule == 292:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(68, tracer) # and
      tree.add(t)
      return tree
    elif rule == 306:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(109, tracer) # gt
      tree.add(t)
      return tree
    elif rule == 323:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(89, tracer) # gteq
      tree.add(t)
      return tree
    elif rule == 334:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(58, tracer) # elipsis
      tree.add(t)
      return tree
    elif rule == 346:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(60, tracer) # incr
      tree.add(t)
      return tree
    elif rule == 351:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(74, tracer) # for
      tree.add(t)
      return tree
    elif rule == 374:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(57, tracer) # bitxor
      tree.add(t)
      return tree
    elif rule == 384:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(0, tracer) # comma
      tree.add(t)
      return tree
    elif rule == 408:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(1, tracer) # exclamation_point
      tree.add(t)
      return tree
    elif rule == 410:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(4, tracer) # register
      tree.add(t)
      return tree
    elif rule == 412:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(66, tracer) # auto
      tree.add(t)
      return tree
    elif rule == 414:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(83, tracer) # const
      tree.add(t)
      return tree
    elif rule == 418:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(7, tracer) # modeq
      tree.add(t)
      return tree
    elif rule == 425:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(93, tracer) # restrict
      tree.add(t)
      return tree
    elif rule == 427:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(50, tracer) # number
      tree.add(t)
      return tree
    elif rule == 429:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(111, tracer) # lt
      tree.add(t)
      return tree
    elif rule == 433:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(97, tracer) # rshift
      tree.add(t)
      return tree
    elif rule == 434:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(81, tracer) # dot
      tree.add(t)
      return tree
    elif rule == 440:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(52, tracer) # extern
      tree.add(t)
      return tree
    elif rule == 444:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(18, tracer) # signed
      tree.add(t)
      return tree
    elif rule == 456:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(32, tracer) # pound
      tree.add(t)
      return tree
    elif rule == 458:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(19, tracer) # short
      tree.add(t)
      return tree
    elif rule == 459:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(63, tracer) # addeq
      tree.add(t)
      return tree
    elif rule == 471:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(24, tracer) # bitor
      tree.add(t)
      return tree
    elif rule == 472:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(90, tracer) # diveq
      tree.add(t)
      return tree
    elif rule == 474:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(87, tracer) # bitxoreq
      tree.add(t)
      return tree
    elif rule == 477:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(29, tracer) # bitandeq
      tree.add(t)
      return tree
    elif rule == 481:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(46, tracer) # typedef
      tree.add(t)
      return tree
    elif rule == 491:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(117, tracer) # sizeof
      tree.add(t)
      return tree
    elif rule == 494:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(20, tracer) # decr
      tree.add(t)
      return tree
    elif rule == 495:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(95, tracer) # char
      tree.add(t)
      return tree
    elif rule == 499:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(107, tracer) # poundpound
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _PARAMETER_DECLARATION(self, depth=0, tracer=None):
    rule = self.rule(220)
    tree = ParseTree( NonTerminal(220, self.getAtomString(220)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 441:
      tree.astTransform = AstTransformNodeCreator('ParameterDeclaration', {'sub': 1, 'declaration_specifiers': 0})
      subtree = self.__GEN1(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN30(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _DESIGNATION(self, depth=0, tracer=None):
    rule = self.rule(221)
    tree = ParseTree( NonTerminal(221, self.getAtomString(221)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 172:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN14(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(31, tracer) # assign
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN26(self, depth=0, tracer=None):
    rule = self.rule(222)
    tree = ParseTree( NonTerminal(222, self.getAtomString(222)), tracer )
    tree.list = 'slist'
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 143:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PARAMETER_DECLARATION(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN27(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN9(self, depth=0, tracer=None):
    rule = self.rule(223)
    tree = ParseTree( NonTerminal(223, self.getAtomString(223)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in [6]):
      return tree
    if self.sym == None:
      return tree
    if rule == 377:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(0, tracer) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self._INIT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN9(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _KEYWORD(self, depth=0, tracer=None):
    rule = self.rule(224)
    tree = ParseTree( NonTerminal(224, self.getAtomString(224)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 12:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(27, tracer) # return
      tree.add(t)
      return tree
    elif rule == 14:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(66, tracer) # auto
      tree.add(t)
      return tree
    elif rule == 25:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(83, tracer) # const
      tree.add(t)
      return tree
    elif rule == 34:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(76, tracer) # do
      tree.add(t)
      return tree
    elif rule == 40:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(52, tracer) # extern
      tree.add(t)
      return tree
    elif rule == 42:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(117, tracer) # sizeof
      tree.add(t)
      return tree
    elif rule == 52:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(100, tracer) # switch
      tree.add(t)
      return tree
    elif rule == 54:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(49, tracer) # else
      tree.add(t)
      return tree
    elif rule == 58:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(95, tracer) # char
      tree.add(t)
      return tree
    elif rule == 88:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(5, tracer) # float
      tree.add(t)
      return tree
    elif rule == 90:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(47, tracer) # void
      tree.add(t)
      return tree
    elif rule == 118:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(113, tracer) # while
      tree.add(t)
      return tree
    elif rule == 120:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(94, tracer) # continue
      tree.add(t)
      return tree
    elif rule == 126:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(110, tracer) # int
      tree.add(t)
      return tree
    elif rule == 141:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(46, tracer) # typedef
      tree.add(t)
      return tree
    elif rule == 150:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(44, tracer) # goto
      tree.add(t)
      return tree
    elif rule == 167:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(25, tracer) # break
      tree.add(t)
      return tree
    elif rule == 173:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(71, tracer) # struct
      tree.add(t)
      return tree
    elif rule == 184:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(18, tracer) # signed
      tree.add(t)
      return tree
    elif rule == 216:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(35, tracer) # default
      tree.add(t)
      return tree
    elif rule == 222:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(106, tracer) # enum
      tree.add(t)
      return tree
    elif rule == 237:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(38, tracer) # union
      tree.add(t)
      return tree
    elif rule == 254:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(36, tracer) # case
      tree.add(t)
      return tree
    elif rule == 262:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(103, tracer) # unsigned
      tree.add(t)
      return tree
    elif rule == 285:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(93, tracer) # restrict
      tree.add(t)
      return tree
    elif rule == 291:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(96, tracer) # static
      tree.add(t)
      return tree
    elif rule == 299:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(101, tracer) # volatile
      tree.add(t)
      return tree
    elif rule == 302:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(23, tracer) # if
      tree.add(t)
      return tree
    elif rule == 335:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(108, tracer) # _bool
      tree.add(t)
      return tree
    elif rule == 347:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(4, tracer) # register
      tree.add(t)
      return tree
    elif rule == 350:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(28, tracer) # _complex
      tree.add(t)
      return tree
    elif rule == 388:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(33, tracer) # inline
      tree.add(t)
      return tree
    elif rule == 395:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(19, tracer) # short
      tree.add(t)
      return tree
    elif rule == 432:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(42, tracer) # long
      tree.add(t)
      return tree
    elif rule == 439:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(10, tracer) # double
      tree.add(t)
      return tree
    elif rule == 503:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(74, tracer) # for
      tree.add(t)
      return tree
    elif rule == 504:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(62, tracer) # _imaginary
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN27(self, depth=0, tracer=None):
    rule = self.rule(225)
    tree = ParseTree( NonTerminal(225, self.getAtomString(225)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in [88]):
      return tree
    if self.sym == None:
      return tree
    if rule == 168:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(0, tracer) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self._PARAMETER_DECLARATION(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN27(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _STRUCT_OR_UNION_BODY(self, depth=0, tracer=None):
    rule = self.rule(228)
    tree = ParseTree( NonTerminal(228, self.getAtomString(228)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 437:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(77, tracer) # lbrace
      tree.add(t)
      subtree = self.__GEN16(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(115, tracer) # rbrace
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN10(self, depth=0, tracer=None):
    rule = self.rule(229)
    tree = ParseTree( NonTerminal(229, self.getAtomString(229)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [0, 6]):
      return tree
    if self.sym == None:
      return tree
    if rule == 71:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DECLARATOR_INITIALIZER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN15(self, depth=0, tracer=None):
    rule = self.rule(230)
    tree = ParseTree( NonTerminal(230, self.getAtomString(230)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [26, 88, 96, 46, 5, 102, 66, 28, 33, 70, 4, 78, 18, 19, 71, 21, 83, 47, 103, 38, 10, 93, 95, 108, 34, 101, 39, 73, 106, 110, 86, 42, 48, 0, 52, 6]):
      return tree
    if self.sym == None:
      return tree
    if rule == 178:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STRUCT_OR_UNION_BODY(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN3(self, depth=0, tracer=None):
    rule = self.rule(231)
    tree = ParseTree( NonTerminal(231, self.getAtomString(231)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in [6]):
      return tree
    if self.sym == None:
      return tree
    if rule == 355:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._EXTERNAL_DECLARATION_SUB_SUB(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN4(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _ELSE_IF_STATEMENT_LIST(self, depth=0, tracer=None):
    rule = self.rule(232)
    tree = ParseTree( NonTerminal(232, self.getAtomString(232)), tracer )
    tree.list = False
    if self.sym == None:
      return tree
    if rule == 266:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN36(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN11(self, depth=0, tracer=None):
    rule = self.rule(233)
    tree = ParseTree( NonTerminal(233, self.getAtomString(233)), tracer )
    tree.list = 'slist'
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 310:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._INITIALIZER_LIST_ITEM(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN12(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [91, 56, 16, 65, 98, 9, 39, 104, 60, 78, 12, 20, 117, 86]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._INITIALIZER_LIST_ITEM(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN12(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _ELSE_STATEMENT(self, depth=0, tracer=None):
    rule = self.rule(234)
    tree = ParseTree( NonTerminal(234, self.getAtomString(234)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 316:
      tree.astTransform = AstTransformNodeCreator('Else', {'statement': 1})
      t = self.expect(49, tracer) # else
      tree.add(t)
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(69, tracer) # endif
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN34(self, depth=0, tracer=None):
    rule = self.rule(235)
    tree = ParseTree( NonTerminal(235, self.getAtomString(235)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [74, 44, 23, 9, 33, 12, 16, 78, 18, 118, 25, 103, 27, 36, 108, 35, 39, 69, 28, 5, 49, 46, 86, 100, 52, 56, 113, 96, 60, 76, 70, 4, 66, 77, 71, 83, 47, 38, 91, 10, 93, 94, 95, 65, 6, 101, 19, 104, 115, 106, 110, 20, 117, 42, 98]):
      return tree
    if self.sym == None:
      return tree
    if rule == 201:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._ELSE_IF_STATEMENT_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _IDENTIFIER(self, depth=0, tracer=None):
    rule = self.rule(236)
    tree = ParseTree( NonTerminal(236, self.getAtomString(236)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 192:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(39, tracer) # identifier
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _STRUCT_OR_UNION_SUB(self, depth=0, tracer=None):
    rule = self.rule(237)
    tree = ParseTree( NonTerminal(237, self.getAtomString(237)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 235:
      tree.astTransform = AstTransformNodeCreator('StructOrUnion', {'body': 1, 'name': 0})
      t = self.expect(39, tracer) # identifier
      tree.add(t)
      subtree = self.__GEN15(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 272:
      tree.astTransform = AstTransformNodeCreator('StructOrUnion', {'body': 0})
      subtree = self._STRUCT_OR_UNION_BODY(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _ENUM_SPECIFIER_SUB(self, depth=0, tracer=None):
    rule = self.rule(238)
    tree = ParseTree( NonTerminal(238, self.getAtomString(238)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 16:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._IDENTIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN21(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 78:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._ENUM_SPECIFIER_BODY(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN31(self, depth=0, tracer=None):
    rule = self.rule(239)
    tree = ParseTree( NonTerminal(239, self.getAtomString(239)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [0, 73, 88, 102, 78, 39]):
      return tree
    if self.sym == None:
      return tree
    if rule == 401:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._POINTER_SUB(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN31(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _POINTER_SUB(self, depth=0, tracer=None):
    rule = self.rule(240)
    tree = ParseTree( NonTerminal(240, self.getAtomString(240)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 214:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(86, tracer) # asterisk
      tree.add(t)
      subtree = self._TYPE_QUALIFIER_LIST_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _VA_ARGS(self, depth=0, tracer=None):
    rule = self.rule(242)
    tree = ParseTree( NonTerminal(242, self.getAtomString(242)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 145:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(88, tracer) # comma_va_args
      tree.add(t)
      t = self.expect(58, tracer) # elipsis
      tree.add(t)
      return tree
    return tree
  def __GEN24(self, depth=0, tracer=None):
    rule = self.rule(243)
    tree = ParseTree( NonTerminal(243, self.getAtomString(243)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [0, 73, 88, 96, 39, 78, 102, 86]):
      return tree
    if self.sym == None:
      return tree
    if rule == 100:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._TYPE_QUALIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN24(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _TYPE_SPECIFIER(self, depth=0, tracer=None):
    rule = self.rule(244)
    tree = ParseTree( NonTerminal(244, self.getAtomString(244)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 26:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(19, tracer) # short
      tree.add(t)
      return tree
    elif rule == 46:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(95, tracer) # char
      tree.add(t)
      return tree
    elif rule == 81:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._TYPEDEF_NAME(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 94:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._UNION_SPECIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 208:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STRUCT_SPECIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 250:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(108, tracer) # _bool
      tree.add(t)
      return tree
    elif rule == 278:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(42, tracer) # long
      tree.add(t)
      return tree
    elif rule == 301:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(5, tracer) # float
      tree.add(t)
      return tree
    elif rule == 304:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(28, tracer) # _complex
      tree.add(t)
      return tree
    elif rule == 325:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(10, tracer) # double
      tree.add(t)
      return tree
    elif rule == 354:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(110, tracer) # int
      tree.add(t)
      return tree
    elif rule == 360:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(18, tracer) # signed
      tree.add(t)
      return tree
    elif rule == 443:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._ENUM_SPECIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 463:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(47, tracer) # void
      tree.add(t)
      return tree
    elif rule == 484:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(103, tracer) # unsigned
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _STRUCT_DECLARATOR(self, depth=0, tracer=None):
    rule = self.rule(245)
    tree = ParseTree( NonTerminal(245, self.getAtomString(245)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 91:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN20(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 370:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STRUCT_DECLARATOR_BODY(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [73, 39, 78]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN20(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  infixBp0 = {
    0: 16000,
    7: 1000,
    14: 1000,
    15: 9000,
    16: 5000,
    17: 12000,
    20: 15000,
    22: 1000,
    24: 7000,
    29: 1000,
    31: 1000,
    40: 10000,
    41: 8000,
    43: 11000,
    53: 8000,
    57: 6000,
    60: 15000,
    61: 3000,
    63: 1000,
    64: 1000,
    67: 15000,
    68: 4000,
    72: 12000,
    75: 11000,
    77: 14000,
    78: 15000,
    79: 2000,
    81: 15000,
    85: 1000,
    86: 12000,
    87: 1000,
    89: 9000,
    90: 1000,
    92: 15000,
    97: 10000,
    109: 9000,
    111: 9000,
    112: 1000,
  }
  prefixBp0 = {
    16: 13000,
    20: 13000,
    30: 13000,
    60: 13000,
    75: 13000,
    82: 13000,
    86: 13000,
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
    tree = ParseTree( NonTerminal(226, '_expr') )
    if not self.sym:
      return tree
    elif self.sym.getId() in [104]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      return self.expect( 104, tracer )
    elif self.sym.getId() in [60]:
      tree.astTransform = AstTransformNodeCreator('PreIncr', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(60, tracer) )
      tree.add( self.__EXPR( self.prefixBp0[60] ) )
      tree.isPrefix = True
    elif self.sym.getId() in [78]:
      tree.astTransform = AstTransformSubstitution(2)
      tree.nudMorphemeCount = 3
      tree.add( self.expect(78, tracer) )
      tree.add( self.__EXPR() )
      tree.add( self.expect(105, tracer) )
    elif self.sym.getId() in [86]:
      tree.astTransform = AstTransformNodeCreator('Dereference', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(86, tracer) )
      tree.add( self.__EXPR( self.prefixBp0[86] ) )
      tree.isPrefix = True
    elif self.sym.getId() in [16]:
      tree.astTransform = AstTransformNodeCreator('AddressOf', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(16, tracer) )
      tree.add( self.__EXPR( self.prefixBp0[16] ) )
      tree.isPrefix = True
    elif self.sym.getId() in [39]:
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      tree.nudMorphemeCount = 1
      return self.expect( 39, tracer )
    elif self.sym.getId() in [117]:
      tree.astTransform = AstTransformNodeCreator('SizeOf', {'var': 1})
      tree.nudMorphemeCount = 1
      return self.expect( 117, tracer )
    elif self.sym.getId() in [39]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      return self.expect( 39, tracer )
    elif self.sym.getId() in [39]:
      tree.astTransform = AstTransformNodeCreator('ArrayIndex', {'params': 2, 'name': 0})
      tree.nudMorphemeCount = 1
      return self.expect( 39, tracer )
    elif self.sym.getId() in [9, 12, 56, 65]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      tree.add( self._CONSTANT() )
    elif self.sym.getId() in [20]:
      tree.astTransform = AstTransformNodeCreator('PreDecr', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(20, tracer) )
      tree.add( self.__EXPR( self.prefixBp0[20] ) )
      tree.isPrefix = True
    elif self.sym.getId() in [91]:
      tree.astTransform = AstTransformNodeCreator('TypeInitializion', {'type': 1, 'initializer': 4})
      tree.nudMorphemeCount = 3
      tree.add( self.expect(91, tracer) )
      tree.add( self._TYPE_NAME() )
      tree.add( self.expect(105, tracer) )
    return tree
  def led0(self, left, tracer):
    tree = ParseTree( NonTerminal(226, '_expr') )
    if  self.sym.getId() == 16: # 'bitand'
      tree.astTransform = AstTransformNodeCreator('BitAND', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(16, tracer) )
      tree.add( self.__EXPR( self.infixBp0[16] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 22: # 'lshifteq'
      tree.astTransform = AstTransformNodeCreator('LeftShiftAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(22, tracer) )
      tree.add( self.__EXPR( self.infixBp0[22] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 63: # 'addeq'
      tree.astTransform = AstTransformNodeCreator('AddAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(63, tracer) )
      tree.add( self.__EXPR( self.infixBp0[63] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 79: # 'questionmark'
      tree.astTransform = AstTransformNodeCreator('TernaryOperator', {'true': 2, 'false': 4, 'cond': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(79, tracer) )
      tree.add( self.__EXPR() )
      tree.add( self.expect(34, tracer) )
      tree.add( self.__EXPR() )
    elif  self.sym.getId() == 64: # 'subeq'
      tree.astTransform = AstTransformNodeCreator('SubtractAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(64, tracer) )
      tree.add( self.__EXPR( self.infixBp0[64] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 85: # 'muleq'
      tree.astTransform = AstTransformNodeCreator('MultiplyAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(85, tracer) )
      tree.add( self.__EXPR( self.infixBp0[85] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 78: # 'lparen'
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(78, tracer) )
      tree.add( self.__GEN37() )
      tree.add( self.expect(105, tracer) )
    elif  self.sym.getId() == 20: # 'decr'
      tree.astTransform = AstTransformNodeCreator('PostDecr', {'var': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      return self.expect( 20, tracer )
    elif  self.sym.getId() == 31: # 'assign'
      tree.astTransform = AstTransformNodeCreator('Assign', {'var': 0, 'value': 2})
      if left:
        tree.add(left)
      tree.add( self.expect(31, tracer) )
      tree.add( self.__EXPR( self.infixBp0[31] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 41: # 'eq'
      tree.astTransform = AstTransformNodeCreator('Equals', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(41, tracer) )
      tree.add( self.__EXPR( self.infixBp0[41] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 90: # 'diveq'
      tree.astTransform = AstTransformNodeCreator('DivideAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(90, tracer) )
      tree.add( self.__EXPR( self.infixBp0[90] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 111: # 'lt'
      tree.astTransform = AstTransformNodeCreator('LessThan', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(111, tracer) )
      tree.add( self.__EXPR( self.infixBp0[111] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 29: # 'bitandeq'
      tree.astTransform = AstTransformNodeCreator('ANDAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(29, tracer) )
      tree.add( self.__EXPR( self.infixBp0[29] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 43: # 'add'
      tree.astTransform = AstTransformNodeCreator('Add', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(43, tracer) )
      tree.add( self.__EXPR( self.infixBp0[43] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 0: # 'comma'
      tree.astTransform = AstTransformNodeCreator('Comma', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(0, tracer) )
      tree.add( self.__EXPR( self.infixBp0[0] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 17: # 'mod'
      tree.astTransform = AstTransformNodeCreator('Mod', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(17, tracer) )
      tree.add( self.__EXPR( self.infixBp0[17] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 15: # 'lteq'
      tree.astTransform = AstTransformNodeCreator('LessThanEq', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(15, tracer) )
      tree.add( self.__EXPR( self.infixBp0[15] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 72: # 'div'
      tree.astTransform = AstTransformNodeCreator('Div', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(72, tracer) )
      tree.add( self.__EXPR( self.infixBp0[72] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 109: # 'gt'
      tree.astTransform = AstTransformNodeCreator('GreaterThan', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(109, tracer) )
      tree.add( self.__EXPR( self.infixBp0[109] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 97: # 'rshift'
      tree.astTransform = AstTransformNodeCreator('RightShift', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(97, tracer) )
      tree.add( self.__EXPR( self.infixBp0[97] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 92: # 'arrow'
      tree.astTransform = AstTransformNodeCreator('DerefMemberSelect', {'member': 2, 'object': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(92, tracer) )
      tree.add( self.__EXPR() )
    elif  self.sym.getId() == 14: # 'rshifteq'
      tree.astTransform = AstTransformNodeCreator('RightShiftAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(14, tracer) )
      tree.add( self.__EXPR( self.infixBp0[14] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 86: # 'asterisk'
      tree.astTransform = AstTransformNodeCreator('Mul', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(86, tracer) )
      tree.add( self.__EXPR( self.infixBp0[86] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 67: # 'lsquare'
      tree.astTransform = AstTransformNodeCreator('ArrayIndex', {'params': 2, 'name': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(67, tracer) )
      tree.add( self.__GEN37() )
      tree.add( self.expect(99, tracer) )
    elif  self.sym.getId() == 87: # 'bitxoreq'
      tree.astTransform = AstTransformNodeCreator('XORAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(87, tracer) )
      tree.add( self.__EXPR( self.infixBp0[87] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 60: # 'incr'
      tree.astTransform = AstTransformNodeCreator('PostIncr', {'var': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      return self.expect( 60, tracer )
    elif  self.sym.getId() == 57: # 'bitxor'
      tree.astTransform = AstTransformNodeCreator('BitXOR', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(57, tracer) )
      tree.add( self.__EXPR( self.infixBp0[57] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 116: # 'sizeof_separator'
      tree.astTransform = AstTransformNodeCreator('SizeOf', {'var': 1})
      if left:
        tree.add(left)
      tree.add( self.expect(116, tracer) )
      tree.add( self._SIZEOF_BODY() )
    elif  self.sym.getId() == 89: # 'gteq'
      tree.astTransform = AstTransformNodeCreator('GreaterThanEq', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(89, tracer) )
      tree.add( self.__EXPR( self.infixBp0[89] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 77: # 'lbrace'
      tree.astTransform = AstTransformNodeCreator('TypeInitializion', {'type': 1, 'initializer': 4})
      if left:
        tree.add(left)
      tree.add( self.expect(77, tracer) )
      tree.add( self.__GEN11() )
      tree.add( self._TRAILING_COMMA_OPT() )
      tree.add( self.expect(115, tracer) )
    elif  self.sym.getId() == 24: # 'bitor'
      tree.astTransform = AstTransformNodeCreator('BitOR', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(24, tracer) )
      tree.add( self.__EXPR( self.infixBp0[24] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 112: # 'bitoreq'
      tree.astTransform = AstTransformNodeCreator('ORAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(112, tracer) )
      tree.add( self.__EXPR( self.infixBp0[112] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 81: # 'dot'
      tree.astTransform = AstTransformNodeCreator('MemberSelect', {'member': 2, 'object': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(81, tracer) )
      tree.add( self.__EXPR() )
    elif  self.sym.getId() == 75: # 'sub'
      tree.astTransform = AstTransformNodeCreator('Sub', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(75, tracer) )
      tree.add( self.__EXPR( self.infixBp0[75] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 7: # 'modeq'
      tree.astTransform = AstTransformNodeCreator('ModAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(7, tracer) )
      tree.add( self.__EXPR( self.infixBp0[7] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 40: # 'lshift'
      tree.astTransform = AstTransformNodeCreator('LeftShift', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(40, tracer) )
      tree.add( self.__EXPR( self.infixBp0[40] ) )
      tree.isInfix = True
    return tree
  infixBp1 = {
    7: 1000,
    14: 1000,
    15: 9000,
    16: 5000,
    17: 12000,
    20: 15000,
    22: 1000,
    24: 7000,
    29: 1000,
    31: 1000,
    40: 10000,
    41: 8000,
    43: 11000,
    53: 8000,
    57: 6000,
    60: 15000,
    61: 3000,
    63: 1000,
    64: 1000,
    67: 15000,
    68: 4000,
    72: 12000,
    75: 11000,
    77: 14000,
    78: 15000,
    79: 2000,
    81: 15000,
    85: 1000,
    86: 12000,
    87: 1000,
    89: 9000,
    90: 1000,
    92: 15000,
    97: 10000,
    109: 9000,
    111: 9000,
    112: 1000,
  }
  prefixBp1 = {
    16: 13000,
    20: 13000,
    30: 13000,
    60: 13000,
    75: 13000,
    82: 13000,
    86: 13000,
  }
  def expr_sans_comma(self):
    return self.__EXPR_SANS_COMMA()
  def __EXPR_SANS_COMMA( self, rbp = 0, depth = 0 ):
    t = self.sym
    if depth is not False:
      tracer = DebugTracer("(expr) __EXPR_SANS_COMMA", str(self.sym), 'N/A', depth)
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
    tree = ParseTree( NonTerminal(241, '_expr_sans_comma') )
    if not self.sym:
      return tree
    if self.sym.getId() in [86]:
      tree.astTransform = AstTransformNodeCreator('Dereference', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(86, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.prefixBp1[86] ) )
      tree.isPrefix = True
    elif self.sym.getId() in [39]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      return self.expect( 39, tracer )
    elif self.sym.getId() in [39]:
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      tree.nudMorphemeCount = 1
      return self.expect( 39, tracer )
    elif self.sym.getId() in [20]:
      tree.astTransform = AstTransformNodeCreator('PreDecr', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(20, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.prefixBp1[20] ) )
      tree.isPrefix = True
    elif self.sym.getId() in [117]:
      tree.astTransform = AstTransformNodeCreator('SizeOf', {'var': 1})
      tree.nudMorphemeCount = 1
      return self.expect( 117, tracer )
    elif self.sym.getId() in [104]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      return self.expect( 104, tracer )
    elif self.sym.getId() in [60]:
      tree.astTransform = AstTransformNodeCreator('PreIncr', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(60, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.prefixBp1[60] ) )
      tree.isPrefix = True
    elif self.sym.getId() in [16]:
      tree.astTransform = AstTransformNodeCreator('AddressOf', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(16, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.prefixBp1[16] ) )
      tree.isPrefix = True
    elif self.sym.getId() in [9, 12, 56, 65]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      tree.add( self._CONSTANT() )
    elif self.sym.getId() in [78]:
      tree.astTransform = AstTransformSubstitution(2)
      tree.nudMorphemeCount = 3
      tree.add( self.expect(78, tracer) )
      tree.add( self.__EXPR_SANS_COMMA() )
      tree.add( self.expect(105, tracer) )
    elif self.sym.getId() in [91]:
      tree.astTransform = AstTransformNodeCreator('TypeInitializion', {'type': 1, 'initializer': 4})
      tree.nudMorphemeCount = 3
      tree.add( self.expect(91, tracer) )
      tree.add( self._TYPE_NAME() )
      tree.add( self.expect(105, tracer) )
    elif self.sym.getId() in [39]:
      tree.astTransform = AstTransformNodeCreator('ArrayIndex', {'params': 2, 'name': 0})
      tree.nudMorphemeCount = 1
      return self.expect( 39, tracer )
    return tree
  def led1(self, left, tracer):
    tree = ParseTree( NonTerminal(241, '_expr_sans_comma') )
    if  self.sym.getId() == 92: # 'arrow'
      tree.astTransform = AstTransformNodeCreator('DerefMemberSelect', {'member': 2, 'object': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(92, tracer) )
      tree.add( self.__EXPR_SANS_COMMA() )
    elif  self.sym.getId() == 116: # 'sizeof_separator'
      tree.astTransform = AstTransformNodeCreator('SizeOf', {'var': 1})
      if left:
        tree.add(left)
      tree.add( self.expect(116, tracer) )
      tree.add( self._SIZEOF_BODY() )
    elif  self.sym.getId() == 22: # 'lshifteq'
      tree.astTransform = AstTransformNodeCreator('LeftShiftAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(22, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[22] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 20: # 'decr'
      tree.astTransform = AstTransformNodeCreator('PostDecr', {'var': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      return self.expect( 20, tracer )
    elif  self.sym.getId() == 72: # 'div'
      tree.astTransform = AstTransformNodeCreator('Div', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(72, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[72] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 111: # 'lt'
      tree.astTransform = AstTransformNodeCreator('LessThan', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(111, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[111] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 78: # 'lparen'
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(78, tracer) )
      tree.add( self.__GEN37() )
      tree.add( self.expect(105, tracer) )
    elif  self.sym.getId() == 64: # 'subeq'
      tree.astTransform = AstTransformNodeCreator('SubtractAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(64, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[64] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 16: # 'bitand'
      tree.astTransform = AstTransformNodeCreator('BitAND', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(16, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[16] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 29: # 'bitandeq'
      tree.astTransform = AstTransformNodeCreator('ANDAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(29, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[29] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 17: # 'mod'
      tree.astTransform = AstTransformNodeCreator('Mod', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(17, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[17] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 109: # 'gt'
      tree.astTransform = AstTransformNodeCreator('GreaterThan', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(109, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[109] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 79: # 'questionmark'
      tree.astTransform = AstTransformNodeCreator('TernaryOperator', {'true': 2, 'false': 4, 'cond': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(79, tracer) )
      tree.add( self.__EXPR_SANS_COMMA() )
      tree.add( self.expect(34, tracer) )
      tree.add( self.__EXPR_SANS_COMMA() )
    elif  self.sym.getId() == 85: # 'muleq'
      tree.astTransform = AstTransformNodeCreator('MultiplyAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(85, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[85] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 60: # 'incr'
      tree.astTransform = AstTransformNodeCreator('PostIncr', {'var': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      return self.expect( 60, tracer )
    elif  self.sym.getId() == 97: # 'rshift'
      tree.astTransform = AstTransformNodeCreator('RightShift', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(97, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[97] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 24: # 'bitor'
      tree.astTransform = AstTransformNodeCreator('BitOR', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(24, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[24] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 41: # 'eq'
      tree.astTransform = AstTransformNodeCreator('Equals', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(41, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[41] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 90: # 'diveq'
      tree.astTransform = AstTransformNodeCreator('DivideAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(90, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[90] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 15: # 'lteq'
      tree.astTransform = AstTransformNodeCreator('LessThanEq', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(15, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[15] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 57: # 'bitxor'
      tree.astTransform = AstTransformNodeCreator('BitXOR', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(57, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[57] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 77: # 'lbrace'
      tree.astTransform = AstTransformNodeCreator('TypeInitializion', {'type': 1, 'initializer': 4})
      if left:
        tree.add(left)
      tree.add( self.expect(77, tracer) )
      tree.add( self.__GEN11() )
      tree.add( self._TRAILING_COMMA_OPT() )
      tree.add( self.expect(115, tracer) )
    elif  self.sym.getId() == 7: # 'modeq'
      tree.astTransform = AstTransformNodeCreator('ModAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(7, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[7] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 31: # 'assign'
      tree.astTransform = AstTransformNodeCreator('Assign', {'var': 0, 'value': 2})
      if left:
        tree.add(left)
      tree.add( self.expect(31, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[31] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 89: # 'gteq'
      tree.astTransform = AstTransformNodeCreator('GreaterThanEq', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(89, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[89] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 43: # 'add'
      tree.astTransform = AstTransformNodeCreator('Add', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(43, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[43] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 63: # 'addeq'
      tree.astTransform = AstTransformNodeCreator('AddAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(63, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[63] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 14: # 'rshifteq'
      tree.astTransform = AstTransformNodeCreator('RightShiftAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(14, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[14] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 67: # 'lsquare'
      tree.astTransform = AstTransformNodeCreator('ArrayIndex', {'params': 2, 'name': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(67, tracer) )
      tree.add( self.__GEN37() )
      tree.add( self.expect(99, tracer) )
    elif  self.sym.getId() == 81: # 'dot'
      tree.astTransform = AstTransformNodeCreator('MemberSelect', {'member': 2, 'object': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(81, tracer) )
      tree.add( self.__EXPR_SANS_COMMA() )
    elif  self.sym.getId() == 112: # 'bitoreq'
      tree.astTransform = AstTransformNodeCreator('ORAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(112, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[112] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 40: # 'lshift'
      tree.astTransform = AstTransformNodeCreator('LeftShift', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(40, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[40] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 86: # 'asterisk'
      tree.astTransform = AstTransformNodeCreator('Mul', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(86, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[86] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 75: # 'sub'
      tree.astTransform = AstTransformNodeCreator('Sub', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(75, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[75] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 87: # 'bitxoreq'
      tree.astTransform = AstTransformNodeCreator('XORAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(87, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[87] ) )
      tree.isInfix = True
    return tree
  infixBp2 = {
    67: 1000,
    78: 1000,
  }
  prefixBp2 = {
  }
  def direct_abstract_declarator(self):
    return self.__DIRECT_ABSTRACT_DECLARATOR()
  def __DIRECT_ABSTRACT_DECLARATOR( self, rbp = 0, depth = 0 ):
    t = self.sym
    if depth is not False:
      tracer = DebugTracer("(expr) __DIRECT_ABSTRACT_DECLARATOR", str(self.sym), 'N/A', depth)
      depth = depth + 1
    else:
      tracer = None
    left = self.nud2(depth)
    if isinstance(left, ParseTree):
      left.isExpr = True
      left.isNud = True
      tracer.add(left.tracer)
    while rbp < self.binding_power(self.sym, self.infixBp2):
      left = self.led2(left, depth)
      if isinstance(left, ParseTree):
        tracer.add(left.tracer)
    if left:
      left.isExpr = True
      left.tracer = tracer
    return left
  def nud2(self, tracer):
    tree = ParseTree( NonTerminal(227, '_direct_abstract_declarator') )
    if not self.sym:
      return tree
    if self.sym.getId() in [78]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 3
      tree.add( self.expect(78, tracer) )
      tree.add( self._ABSTRACT_DECLARATOR() )
      tree.add( self.expect(105, tracer) )
    elif self.sym.getId() in [-1, 102, 78]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      tree.add( self._DIRECT_ABSTRACT_DECLARATOR_OPT() )
    elif self.sym.getId() in [-1, 102, 78]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      tree.add( self._DIRECT_ABSTRACT_DECLARATOR_OPT() )
    return tree
  def led2(self, left, tracer):
    tree = ParseTree( NonTerminal(227, '_direct_abstract_declarator') )
    if  self.sym.getId() == 67: # 'lsquare'
      tree.astTransform = AstTransformSubstitution(0)
      if left:
        tree.add(left)
      tree.add( self.expect(67, tracer) )
      tree.add( self._DIRECT_ABSTRACT_DECLARATOR_EXPR() )
      tree.add( self.expect(99, tracer) )
    elif  self.sym.getId() == 78: # 'lparen'
      tree.astTransform = AstTransformSubstitution(0)
      if left:
        tree.add(left)
      tree.add( self.expect(78, tracer) )
      tree.add( self._PARAMETER_TYPE_LIST_OPT() )
      tree.add( self.expect(105, tracer) )
    return tree
  infixBp3 = {
    67: 1000,
    78: 1000,
  }
  prefixBp3 = {
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
    left = self.nud3(depth)
    if isinstance(left, ParseTree):
      left.isExpr = True
      left.isNud = True
      tracer.add(left.tracer)
    while rbp < self.binding_power(self.sym, self.infixBp3):
      left = self.led3(left, depth)
      if isinstance(left, ParseTree):
        tracer.add(left.tracer)
    if left:
      left.isExpr = True
      left.tracer = tracer
    return left
  def nud3(self, tracer):
    tree = ParseTree( NonTerminal(150, '_direct_declarator') )
    if not self.sym:
      return tree
    if self.sym.getId() in [39]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      return self.expect( 39, tracer )
    elif self.sym.getId() in [78]:
      tree.astTransform = AstTransformSubstitution(1)
      tree.nudMorphemeCount = 3
      tree.add( self.expect(78, tracer) )
      tree.add( self._DECLARATOR() )
      tree.add( self.expect(105, tracer) )
    return tree
  def led3(self, left, tracer):
    tree = ParseTree( NonTerminal(150, '_direct_declarator') )
    if  self.sym.getId() == 78: # 'lparen'
      tree.astTransform = AstTransformNodeCreator('FunctionSignature', {'params': 2, 'declarator': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(78, tracer) )
      tree.add( self._DIRECT_DECLARATOR_PARAMETER_LIST() )
      tree.add( self.expect(105, tracer) )
    elif  self.sym.getId() == 67: # 'lsquare'
      tree.astTransform = AstTransformNodeCreator('Array', {'name': 0, 'size': 2})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(67, tracer) )
      tree.add( self._DIRECT_DECLARATOR_EXPR() )
      tree.add( self.expect(99, tracer) )
    return tree
