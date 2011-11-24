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
class ParseTreePrettyPrintable:
  def __init__(self, ast, tokenFormat='type'):
    self.__dict__.update(locals())
  def __str__(self):
    return self._prettyPrint(self.ast, 0)
  def _prettyPrint(self, parsetree, indent = 0):
    indentStr = ''.join([' ' for x in range(indent)])
    if isinstance(parsetree, ParseTree):
      if len(parsetree.children) == 0:
        return '(%s: )' % (parsetree.nonterminal)
      string = '%s(%s:\n' % (indentStr, parsetree.nonterminal)
      string += ',\n'.join([ \
        '%s  %s' % (indentStr, self._prettyPrint(value, indent + 2).lstrip()) for value in parsetree.children \
      ])
      string += '\n%s)' % (indentStr)
      return string
    elif isinstance(parsetree, Terminal):
      return '%s%s' % (indentStr, parsetree.toString(self.tokenFormat))
    else:
      return '%s%s' % (indentStr, parsetree)
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
  TERMINAL_EXTERNAL_DECLARATION_HINT = 0
  TERMINAL_DEFINED_SEPARATOR = 1
  TERMINAL_RPAREN = 2
  TERMINAL_TRAILING_COMMA = 3
  TERMINAL__DIRECT_DECLARATOR = 4
  TERMINAL_COLON = 5
  TERMINAL_ADDEQ = 6
  TERMINAL_PP_NUMBER = 7
  TERMINAL_GTEQ = 8
  TERMINAL_ENDIF = 9
  TERMINAL_DOT = 10
  TERMINAL_SIGNED = 11
  TERMINAL_IDENTIFIER = 12
  TERMINAL_MULEQ = 13
  TERMINAL_WHILE = 14
  TERMINAL_POUND = 15
  TERMINAL_BITOR = 16
  TERMINAL_TYPEDEF = 17
  TERMINAL_ELSE = 18
  TERMINAL_FUNCTION_DEFINITION_HINT = 19
  TERMINAL_DIV = 20
  TERMINAL_DO = 21
  TERMINAL_OR = 22
  TERMINAL_INLINE = 23
  TERMINAL__EXPR_SANS_COMMA = 24
  TERMINAL_EXTERN = 25
  TERMINAL_RETURN = 26
  TERMINAL_RBRACE = 27
  TERMINAL_LSHIFT = 28
  TERMINAL_POUNDPOUND = 29
  TERMINAL_COMPLEX = 30
  TERMINAL_INCR = 31
  TERMINAL_COMMA = 32
  TERMINAL_STATIC = 33
  TERMINAL_IMAGINARY = 34
  TERMINAL_COMMA_VA_ARGS = 35
  TERMINAL_ASSIGN = 36
  TERMINAL_RSHIFT = 37
  TERMINAL_AUTO = 38
  TERMINAL_EXCLAMATION_POINT = 39
  TERMINAL_BITAND = 40
  TERMINAL_TILDE = 41
  TERMINAL_NOT = 42
  TERMINAL_REGISTER = 43
  TERMINAL_MOD = 44
  TERMINAL_LPAREN = 45
  TERMINAL_UNSIGNED = 46
  TERMINAL_TYPEDEF_IDENTIFIER = 47
  TERMINAL_AMPERSAND = 48
  TERMINAL_LBRACE = 49
  TERMINAL_FUNCTION_PROTOTYPE_HINT = 50
  TERMINAL_VOID = 51
  TERMINAL_STRUCT = 52
  TERMINAL_FLOATING_CONSTANT = 53
  TERMINAL__EXPR = 54
  TERMINAL_DECLARATOR_HINT = 55
  TERMINAL_CONST = 56
  TERMINAL_CHAR = 57
  TERMINAL_ELIPSIS = 58
  TERMINAL_BOOL = 59
  TERMINAL_SIZEOF_SEPARATOR = 60
  TERMINAL_BITXOR = 61
  TERMINAL_QUESTIONMARK = 62
  TERMINAL_UNIVERSAL_CHARACTER_NAME = 63
  TERMINAL_LONG = 64
  TERMINAL_ADD = 65
  TERMINAL_ARROW = 66
  TERMINAL_SIZEOF = 67
  TERMINAL_GT = 68
  TERMINAL_GOTO = 69
  TERMINAL_BITOREQ = 70
  TERMINAL_RSQUARE = 71
  TERMINAL_LSQUARE = 72
  TERMINAL_VOLATILE = 73
  TERMINAL_RESTRICT = 74
  TERMINAL_INT = 75
  TERMINAL_SUB = 76
  TERMINAL_CHARACTER_CONSTANT = 77
  TERMINAL_RSHIFTEQ = 78
  TERMINAL_BITXOREQ = 79
  TERMINAL_DECR = 80
  TERMINAL_BITNOT = 81
  TERMINAL_DIVEQ = 82
  TERMINAL_ASTERISK = 83
  TERMINAL_MODEQ = 84
  TERMINAL_ENUM = 85
  TERMINAL_SWITCH = 86
  TERMINAL_BITANDEQ = 87
  TERMINAL_SEMI = 88
  TERMINAL_BREAK = 89
  TERMINAL_CONTINUE = 90
  TERMINAL_FLOAT = 91
  TERMINAL_NEQ = 92
  TERMINAL_ENUMERATION_CONSTANT = 93
  TERMINAL_LABEL_HINT = 94
  TERMINAL_UNION = 95
  TERMINAL_LSHIFTEQ = 96
  TERMINAL_SHORT = 97
  TERMINAL_LPAREN_CAST = 98
  TERMINAL_DOUBLE = 99
  TERMINAL_FOR = 100
  TERMINAL_HEXADECIMAL_FLOATING_CONSTANT = 101
  TERMINAL_IF = 102
  TERMINAL_AND = 103
  TERMINAL_DEFAULT = 104
  TERMINAL_CASE = 105
  TERMINAL_INTEGER_CONSTANT = 106
  TERMINAL_DEFINED = 107
  TERMINAL_ELSE_IF = 108
  TERMINAL_LT = 109
  TERMINAL_EQ = 110
  TERMINAL_DECIMAL_FLOATING_CONSTANT = 111
  TERMINAL_LTEQ = 112
  TERMINAL_SUBEQ = 113
  TERMINAL_STRING_LITERAL = 114
  terminal_str = {
    0: 'external_declaration_hint',
    1: 'defined_separator',
    2: 'rparen',
    3: 'trailing_comma',
    4: '_direct_declarator',
    5: 'colon',
    6: 'addeq',
    7: 'pp_number',
    8: 'gteq',
    9: 'endif',
    10: 'dot',
    11: 'signed',
    12: 'identifier',
    13: 'muleq',
    14: 'while',
    15: 'pound',
    16: 'bitor',
    17: 'typedef',
    18: 'else',
    19: 'function_definition_hint',
    20: 'div',
    21: 'do',
    22: 'or',
    23: 'inline',
    24: '_expr_sans_comma',
    25: 'extern',
    26: 'return',
    27: 'rbrace',
    28: 'lshift',
    29: 'poundpound',
    30: 'complex',
    31: 'incr',
    32: 'comma',
    33: 'static',
    34: 'imaginary',
    35: 'comma_va_args',
    36: 'assign',
    37: 'rshift',
    38: 'auto',
    39: 'exclamation_point',
    40: 'bitand',
    41: 'tilde',
    42: 'not',
    43: 'register',
    44: 'mod',
    45: 'lparen',
    46: 'unsigned',
    47: 'typedef_identifier',
    48: 'ampersand',
    49: 'lbrace',
    50: 'function_prototype_hint',
    51: 'void',
    52: 'struct',
    53: 'floating_constant',
    54: '_expr',
    55: 'declarator_hint',
    56: 'const',
    57: 'char',
    58: 'elipsis',
    59: 'bool',
    60: 'sizeof_separator',
    61: 'bitxor',
    62: 'questionmark',
    63: 'universal_character_name',
    64: 'long',
    65: 'add',
    66: 'arrow',
    67: 'sizeof',
    68: 'gt',
    69: 'goto',
    70: 'bitoreq',
    71: 'rsquare',
    72: 'lsquare',
    73: 'volatile',
    74: 'restrict',
    75: 'int',
    76: 'sub',
    77: 'character_constant',
    78: 'rshifteq',
    79: 'bitxoreq',
    80: 'decr',
    81: 'bitnot',
    82: 'diveq',
    83: 'asterisk',
    84: 'modeq',
    85: 'enum',
    86: 'switch',
    87: 'bitandeq',
    88: 'semi',
    89: 'break',
    90: 'continue',
    91: 'float',
    92: 'neq',
    93: 'enumeration_constant',
    94: 'label_hint',
    95: 'union',
    96: 'lshifteq',
    97: 'short',
    98: 'lparen_cast',
    99: 'double',
    100: 'for',
    101: 'hexadecimal_floating_constant',
    102: 'if',
    103: 'and',
    104: 'default',
    105: 'case',
    106: 'integer_constant',
    107: 'defined',
    108: 'else_if',
    109: 'lt',
    110: 'eq',
    111: 'decimal_floating_constant',
    112: 'lteq',
    113: 'subeq',
    114: 'string_literal',
  }
  nonterminal_str = {
    115: '_gen36',
    116: 'pointer_opt',
    117: '_direct_declarator',
    118: 'trailing_comma_opt',
    119: 'specifier_qualifier',
    120: '_gen20',
    121: 'union_specifier',
    122: 'external_declarator',
    123: 'direct_declarator_modifier_list_opt',
    124: 'direct_declarator_size',
    125: 'keyword',
    126: 'struct_declarator',
    127: '_gen21',
    128: 'block_item',
    129: 'type_qualifier',
    130: '_gen38',
    131: 'declarator',
    132: '_gen5',
    133: '_gen28',
    134: 'enumeration_constant',
    135: 'enumerator_assignment',
    136: 'block_item_list',
    137: 'direct_abstract_declarator_sub1',
    138: '_gen9',
    139: 'compound_statement',
    140: 'punctuator',
    141: 'enumerator',
    142: '_gen2',
    143: '_gen8',
    144: 'init_declarator',
    145: 'struct_declarator_body',
    146: 'abstract_declarator',
    147: '_gen25',
    148: 'labeled_statement',
    149: 'direct_declarator_expr',
    150: 'enum_specifier_sub',
    151: '_gen23',
    152: '_gen42',
    153: '_gen43',
    154: '_gen6',
    155: '_gen26',
    156: 'direct_abstract_declarator_expr',
    157: 'expression_statement',
    158: 'token',
    159: 'parameter_declaration',
    160: '_gen29',
    161: 'sizeof_body',
    162: '_gen40',
    163: 'selection_statement',
    164: 'type_name',
    165: 'direct_abstract_declarator_sub2',
    166: 'jump_statement',
    167: 'iteration_statement',
    168: '_gen27',
    169: '_gen37',
    170: '_gen7',
    171: 'va_args',
    172: 'init_declarator_list',
    173: 'else_if_statement',
    174: '_gen31',
    175: '_gen41',
    176: 'parameter_type_list',
    177: 'for_cond',
    178: 'enum_specifier_body',
    179: '_gen24',
    180: 'pp',
    181: 'storage_class_specifier',
    182: 'direct_declarator_parameter_list',
    183: 'misc',
    184: 'type_specifier',
    185: 'external_prototype',
    186: 'identifier',
    187: '_gen11',
    188: '_gen12',
    189: '_gen33',
    190: 'pointer',
    191: '_gen10',
    192: 'initializer_list_item',
    193: '_expr_sans_comma',
    194: 'function_specifier',
    195: 'direct_abstract_declarator_sub0',
    196: 'declarator_initializer',
    197: 'else_if_statement_list',
    198: '_gen13',
    199: '_gen22',
    200: 'translation_unit',
    201: 'direct_abstract_declarator',
    202: 'static_opt',
    203: 'struct_specifier',
    204: '_gen15',
    205: '_gen39',
    206: 'for_init',
    207: '_gen0',
    208: 'for_incr',
    209: 'initializer',
    210: 'declaration',
    211: 'enum_specifier',
    212: 'parameter_declaration_sub',
    213: 'direct_declarator_modifier',
    214: '_expr',
    215: 'expression_opt',
    216: 'typedef_name',
    217: 'declaration_specifier',
    218: 'declaration_list',
    219: '_gen14',
    220: 'struct_or_union_sub',
    221: 'parameter_declaration_sub_sub',
    222: 'constant',
    223: 'external_declaration_sub',
    224: '_gen35',
    225: 'struct_or_union_body',
    226: '_gen18',
    227: '_gen32',
    228: 'external_function',
    229: 'type_qualifier_list_opt',
    230: 'designation',
    231: '_gen19',
    232: '_gen16',
    233: 'external_declaration_sub_sub',
    234: '_gen3',
    235: 'else_statement',
    236: '_gen4',
    237: 'struct_declaration',
    238: 'external_declaration',
    239: 'designator',
    240: '_gen17',
    241: '_gen34',
    242: '_gen1',
    243: '_gen30',
    244: 'pointer_sub',
    245: 'statement',
  }
  str_terminal = {
    'external_declaration_hint': 0,
    'defined_separator': 1,
    'rparen': 2,
    'trailing_comma': 3,
    '_direct_declarator': 4,
    'colon': 5,
    'addeq': 6,
    'pp_number': 7,
    'gteq': 8,
    'endif': 9,
    'dot': 10,
    'signed': 11,
    'identifier': 12,
    'muleq': 13,
    'while': 14,
    'pound': 15,
    'bitor': 16,
    'typedef': 17,
    'else': 18,
    'function_definition_hint': 19,
    'div': 20,
    'do': 21,
    'or': 22,
    'inline': 23,
    '_expr_sans_comma': 24,
    'extern': 25,
    'return': 26,
    'rbrace': 27,
    'lshift': 28,
    'poundpound': 29,
    'complex': 30,
    'incr': 31,
    'comma': 32,
    'static': 33,
    'imaginary': 34,
    'comma_va_args': 35,
    'assign': 36,
    'rshift': 37,
    'auto': 38,
    'exclamation_point': 39,
    'bitand': 40,
    'tilde': 41,
    'not': 42,
    'register': 43,
    'mod': 44,
    'lparen': 45,
    'unsigned': 46,
    'typedef_identifier': 47,
    'ampersand': 48,
    'lbrace': 49,
    'function_prototype_hint': 50,
    'void': 51,
    'struct': 52,
    'floating_constant': 53,
    '_expr': 54,
    'declarator_hint': 55,
    'const': 56,
    'char': 57,
    'elipsis': 58,
    'bool': 59,
    'sizeof_separator': 60,
    'bitxor': 61,
    'questionmark': 62,
    'universal_character_name': 63,
    'long': 64,
    'add': 65,
    'arrow': 66,
    'sizeof': 67,
    'gt': 68,
    'goto': 69,
    'bitoreq': 70,
    'rsquare': 71,
    'lsquare': 72,
    'volatile': 73,
    'restrict': 74,
    'int': 75,
    'sub': 76,
    'character_constant': 77,
    'rshifteq': 78,
    'bitxoreq': 79,
    'decr': 80,
    'bitnot': 81,
    'diveq': 82,
    'asterisk': 83,
    'modeq': 84,
    'enum': 85,
    'switch': 86,
    'bitandeq': 87,
    'semi': 88,
    'break': 89,
    'continue': 90,
    'float': 91,
    'neq': 92,
    'enumeration_constant': 93,
    'label_hint': 94,
    'union': 95,
    'lshifteq': 96,
    'short': 97,
    'lparen_cast': 98,
    'double': 99,
    'for': 100,
    'hexadecimal_floating_constant': 101,
    'if': 102,
    'and': 103,
    'default': 104,
    'case': 105,
    'integer_constant': 106,
    'defined': 107,
    'else_if': 108,
    'lt': 109,
    'eq': 110,
    'decimal_floating_constant': 111,
    'lteq': 112,
    'subeq': 113,
    'string_literal': 114,
  }
  str_nonterminal = {
    '_gen36': 115,
    'pointer_opt': 116,
    '_direct_declarator': 117,
    'trailing_comma_opt': 118,
    'specifier_qualifier': 119,
    '_gen20': 120,
    'union_specifier': 121,
    'external_declarator': 122,
    'direct_declarator_modifier_list_opt': 123,
    'direct_declarator_size': 124,
    'keyword': 125,
    'struct_declarator': 126,
    '_gen21': 127,
    'block_item': 128,
    'type_qualifier': 129,
    '_gen38': 130,
    'declarator': 131,
    '_gen5': 132,
    '_gen28': 133,
    'enumeration_constant': 134,
    'enumerator_assignment': 135,
    'block_item_list': 136,
    'direct_abstract_declarator_sub1': 137,
    '_gen9': 138,
    'compound_statement': 139,
    'punctuator': 140,
    'enumerator': 141,
    '_gen2': 142,
    '_gen8': 143,
    'init_declarator': 144,
    'struct_declarator_body': 145,
    'abstract_declarator': 146,
    '_gen25': 147,
    'labeled_statement': 148,
    'direct_declarator_expr': 149,
    'enum_specifier_sub': 150,
    '_gen23': 151,
    '_gen42': 152,
    '_gen43': 153,
    '_gen6': 154,
    '_gen26': 155,
    'direct_abstract_declarator_expr': 156,
    'expression_statement': 157,
    'token': 158,
    'parameter_declaration': 159,
    '_gen29': 160,
    'sizeof_body': 161,
    '_gen40': 162,
    'selection_statement': 163,
    'type_name': 164,
    'direct_abstract_declarator_sub2': 165,
    'jump_statement': 166,
    'iteration_statement': 167,
    '_gen27': 168,
    '_gen37': 169,
    '_gen7': 170,
    'va_args': 171,
    'init_declarator_list': 172,
    'else_if_statement': 173,
    '_gen31': 174,
    '_gen41': 175,
    'parameter_type_list': 176,
    'for_cond': 177,
    'enum_specifier_body': 178,
    '_gen24': 179,
    'pp': 180,
    'storage_class_specifier': 181,
    'direct_declarator_parameter_list': 182,
    'misc': 183,
    'type_specifier': 184,
    'external_prototype': 185,
    'identifier': 186,
    '_gen11': 187,
    '_gen12': 188,
    '_gen33': 189,
    'pointer': 190,
    '_gen10': 191,
    'initializer_list_item': 192,
    '_expr_sans_comma': 193,
    'function_specifier': 194,
    'direct_abstract_declarator_sub0': 195,
    'declarator_initializer': 196,
    'else_if_statement_list': 197,
    '_gen13': 198,
    '_gen22': 199,
    'translation_unit': 200,
    'direct_abstract_declarator': 201,
    'static_opt': 202,
    'struct_specifier': 203,
    '_gen15': 204,
    '_gen39': 205,
    'for_init': 206,
    '_gen0': 207,
    'for_incr': 208,
    'initializer': 209,
    'declaration': 210,
    'enum_specifier': 211,
    'parameter_declaration_sub': 212,
    'direct_declarator_modifier': 213,
    '_expr': 214,
    'expression_opt': 215,
    'typedef_name': 216,
    'declaration_specifier': 217,
    'declaration_list': 218,
    '_gen14': 219,
    'struct_or_union_sub': 220,
    'parameter_declaration_sub_sub': 221,
    'constant': 222,
    'external_declaration_sub': 223,
    '_gen35': 224,
    'struct_or_union_body': 225,
    '_gen18': 226,
    '_gen32': 227,
    'external_function': 228,
    'type_qualifier_list_opt': 229,
    'designation': 230,
    '_gen19': 231,
    '_gen16': 232,
    'external_declaration_sub_sub': 233,
    '_gen3': 234,
    'else_statement': 235,
    '_gen4': 236,
    'struct_declaration': 237,
    'external_declaration': 238,
    'designator': 239,
    '_gen17': 240,
    '_gen34': 241,
    '_gen1': 242,
    '_gen30': 243,
    'pointer_sub': 244,
    'statement': 245,
  }
  terminal_count = 115
  nonterminal_count = 131
  parse_table = [
    [-1, -1, 213, -1, 213, -1, -1, -1, -1, -1, -1, -1, 213, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 213, -1, -1, 213, -1, -1, -1, -1, -1, -1, -1, -1, -1, 213, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 213, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 210, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 100, -1, 100, -1, -1, -1, -1, -1, -1, -1, 100, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 100, -1, -1, 100, -1, -1, -1, -1, -1, -1, -1, -1, -1, 100, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 100, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 100, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, 403, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 343, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 171, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 171, -1, -1, -1, 171, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 171, 171, -1, -1, -1, 171, 171, -1, -1, -1, 277, 171, -1, 171, -1, -1, -1, -1, 171, -1, -1, -1, -1, -1, -1, -1, -1, 277, 277, 171, -1, -1, -1, -1, -1, -1, -1, -1, -1, 171, -1, -1, -1, -1, -1, 171, -1, -1, -1, 171, -1, 171, -1, 171, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, 222, 222, -1, -1, -1, -1, -1, 217, 222, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 217, -1, -1, -1, 217, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 222, 217, 217, -1, -1, -1, 217, 217, -1, -1, -1, 217, 217, -1, 217, -1, -1, -1, -1, 217, -1, -1, -1, -1, -1, -1, -1, -1, 217, 217, 217, -1, -1, -1, -1, -1, -1, -1, 222, -1, 217, -1, -1, -1, -1, -1, 217, -1, -1, -1, 217, -1, 217, -1, 217, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 56, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 313, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 201, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 201, -1, 257, -1, -1, -1, -1, -1, -1, 201, -1, -1, -1, -1, 201, -1, -1, -1, -1, -1, -1, -1, 201, 201, -1, 257, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 201, -1, -1, -1, -1, -1, 257, 257, -1, -1, 201, -1, -1, 201, -1, -1, 201, -1, -1, -1, -1, -1, -1, -1, -1, -1, 201, -1, -1, -1, -1, 201, -1, -1, 201, -1, -1, -1, -1, 201, -1, -1, -1, -1, 201, -1, -1, 201],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 225, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 225, -1, -1, -1, -1, -1, -1, -1, -1, 225, -1, -1, -1, -1, 225, -1, -1, -1, -1, -1, -1, -1, 225, 225, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 225, -1, -1, -1, -1, -1, -1, -1, -1, -1, 225, -1, -1, 225, -1, -1, 225, -1, -1, -1, -1, -1, -1, -1, -1, -1, 225, -1, -1, -1, -1, 225, -1, -1, 225, -1, -1, -1, -1, 225, -1, -1, -1, -1, 225, -1, -1, 225],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 373, -1, -1, 130, -1, -1, 195, 148, -1, -1, 336, -1, 40, -1, 307, 419, -1, -1, -1, 235, -1, -1, 299, 205, -1, -1, -1, 379, -1, -1, -1, -1, 31, -1, -1, 141, -1, -1, -1, -1, 160, 169, -1, -1, -1, 384, 232, -1, 103, -1, -1, -1, -1, 113, -1, -1, 342, -1, 349, -1, -1, -1, 306, 346, 276, -1, -1, -1, -1, -1, -1, -1, -1, -1, 177, 137, -1, -1, 358, 168, 129, -1, -1, -1, 42, -1, 98, -1, 14, 271, -1, 193, -1, 108, 401, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, 208, 199, -1, -1, -1, -1, -1, -1, 208, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 208, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 208, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, 283, 283, -1, -1, -1, -1, -1, -1, 283, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 283, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 283, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 354, 318, -1, 318, -1, -1, 354, -1, -1, -1, 318, -1, 354, -1, 354, 318, -1, -1, -1, 354, 318, -1, 354, 354, -1, -1, -1, 354, -1, 318, -1, -1, 354, -1, 318, 354, 354, -1, 318, -1, 354, 354, 318, 318, -1, 354, 354, -1, 354, -1, -1, -1, -1, 354, -1, -1, 318, -1, 318, -1, -1, -1, 354, 354, 354, -1, 318, -1, -1, 318, -1, -1, 318, -1, 354, 318, -1, 318, 318, 318, 354, -1, 318, 318, 354, -1, 354, 318, 354, 318, 318, 318, -1, 318, 318, 318, -1, -1, -1, -1, 318, -1, -1, 318],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 230, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 376, 363, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 22, 22, -1, 22, -1, -1, 22, -1, -1, -1, 22, -1, 22, -1, 22, 22, 174, -1, -1, 22, 22, -1, 22, 22, -1, -1, -1, 22, -1, 22, -1, -1, 22, -1, 22, 22, 22, -1, 22, -1, 22, 22, 22, 22, -1, 22, 22, -1, 22, -1, -1, -1, -1, 22, -1, -1, 22, -1, 22, -1, -1, -1, 22, 22, 22, -1, 22, -1, -1, 22, -1, -1, 22, -1, 22, 22, -1, 22, 22, 22, 22, -1, 22, 22, 22, -1, 22, 22, 22, 22, 22, 22, -1, 22, 22, 22, -1, -1, -1, -1, 22, -1, -1, 22],
    [-1, -1, -1, -1, 246, -1, -1, -1, -1, -1, -1, -1, 246, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 246, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 246, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 184, -1, -1, -1, -1, -1, 184, -1, -1, -1, -1, -1, 184, -1, 184, -1, -1, -1, -1, 184, -1, 184, 184, 184, -1, -1, -1, 184, -1, -1, -1, -1, 184, -1, -1, 184, 184, -1, 184, -1, 184, 184, -1, -1, -1, 184, 184, -1, 184, -1, -1, -1, -1, 184, -1, -1, -1, -1, -1, -1, -1, -1, 184, 184, 184, -1, -1, -1, -1, -1, -1, -1, -1, -1, 184, -1, -1, 184, -1, -1, 184, -1, -1, -1, 184, -1, 184, -1, 184, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 30, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 30, -1, 25, -1, -1, -1, -1, -1, -1, 30, -1, -1, -1, -1, 30, -1, -1, -1, -1, -1, -1, -1, 30, 30, -1, 25, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 30, -1, -1, -1, -1, -1, 25, 25, -1, -1, 30, -1, -1, 30, -1, -1, 30, -1, -1, -1, -1, -1, -1, -1, -1, -1, 30, -1, -1, -1, -1, 30, -1, -1, 30, -1, -1, -1, -1, 30, -1, -1, -1, -1, 30, -1, -1, 30],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 256, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, 157, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 157, -1, -1, -1, 164, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 50, 50, -1, 50, -1, -1, 50, -1, -1, -1, 50, -1, 50, -1, 50, 50, 50, -1, -1, 50, 50, -1, 50, 50, -1, -1, -1, 50, -1, 50, -1, -1, 50, -1, 50, 50, 50, -1, 50, -1, 50, 50, 50, 50, -1, 50, 50, -1, 50, -1, -1, -1, -1, 50, -1, -1, 50, -1, 50, -1, -1, -1, 50, 50, 50, -1, 50, -1, -1, 50, -1, -1, 50, -1, 50, 50, -1, 50, 50, 50, 50, -1, 50, 50, 50, -1, 50, 50, 50, 50, 50, 50, -1, 50, 50, 50, -1, -1, -1, -1, 50, -1, -1, 50],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 52, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 87, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 259, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 259, -1, -1, 259, -1, -1, -1, -1, -1, -1, -1, -1, -1, 378, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 378, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 240, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 282, -1, -1, 247, 6, -1, 35, -1, 252, -1, -1, 65, -1, 226, 344, -1, -1, -1, 53, -1, 214, -1, -1, -1, -1, 216, 250, 404, -1, 156, 34, -1, -1, -1, 417, 125, -1, 161, -1, 74, -1, -1, 44, 126, -1, -1, 206, 332, -1, -1, -1, -1, -1, -1, -1, -1, 67, -1, -1, 73, 136, -1, -1, 178, 260, -1, 59, -1, 27, 263, 124, -1, -1, -1, 244, -1, 3, 114, 45, -1, -1, -1, 391, -1, -1, 48, 372, -1, -1, -1, 23, -1, -1, -1, 109, -1, -1, -1, -1, -1, -1, 265, -1, -1, -1, -1, -1, 229, 80, -1, 180, 189, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 127, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 287, -1, 287, -1, -1, -1, -1, -1, -1, 24, 287, -1, -1, -1, -1, 24, -1, 287, -1, -1, -1, 24, -1, 24, -1, -1, -1, -1, 24, -1, 287, 24, 24, 287, -1, -1, 24, -1, -1, -1, -1, 24, -1, 287, 24, 24, -1, -1, 287, 24, 24, -1, -1, 287, 24, 24, -1, 24, -1, -1, -1, -1, 24, -1, -1, -1, -1, -1, -1, -1, 287, 24, 24, 24, -1, -1, -1, -1, -1, -1, -1, 287, -1, 24, -1, -1, 287, -1, -1, 24, -1, -1, -1, 24, -1, 24, -1, 24, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 238, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 238, -1, -1, 238, -1, -1, -1, -1, -1, -1, -1, -1, -1, 234, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 238, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, 8, -1, -1, -1, -1, -1, -1, -1, 8, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 8, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 8, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, 279, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 64, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 64, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 64, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 64, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 9, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 297, -1, -1, -1, -1, -1, -1, -1, -1, -1, 183, 274, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 399, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 399, -1, 399, -1, -1, -1, -1, -1, -1, 399, -1, -1, -1, -1, 399, -1, -1, -1, -1, -1, -1, -1, 399, 399, -1, 399, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 399, -1, -1, -1, -1, -1, 399, 399, -1, -1, 399, -1, -1, 399, -1, -1, 399, -1, -1, -1, -1, -1, -1, -1, -1, -1, 399, -1, -1, -1, -1, 399, -1, -1, 399, -1, -1, -1, -1, 399, -1, -1, -1, -1, 399, -1, -1, 399],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 162, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 267, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, 269, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 66, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 66, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 275, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 275, -1, -1, -1, -1, -1, -1, 275, -1, -1, -1, -1, -1, -1, -1, -1, 275, -1, -1, -1, -1, 275, -1, -1, -1, -1, -1, -1, -1, 275, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 275, -1, -1, -1, -1, -1, -1, -1, -1, -1, 275, -1, -1, 275, -1, -1, 275, -1, -1, -1, -1, -1, -1, -1, -1, -1, 275, -1, -1, -1, -1, 275, -1, -1, 275, -1, -1, -1, -1, 275, -1, -1, -1, -1, 275, -1, -1, 275],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 261, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 388, -1, -1, -1, -1, -1, 388, -1, -1, -1, -1, -1, 388, -1, 388, -1, -1, -1, -1, 388, -1, 186, 388, 388, -1, -1, -1, 388, -1, -1, -1, -1, 388, -1, -1, 388, 388, -1, 186, -1, 388, 388, -1, -1, -1, 388, 388, -1, 388, -1, -1, -1, -1, 388, -1, -1, -1, -1, -1, -1, -1, -1, 388, 388, 388, -1, -1, -1, -1, -1, -1, -1, -1, -1, 388, -1, -1, 186, -1, -1, 388, -1, -1, -1, 388, -1, 388, -1, 388, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, 16, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 12, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 107, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 107, -1, 107, -1, -1, -1, -1, -1, -1, 107, -1, -1, -1, -1, 107, -1, -1, -1, -1, -1, -1, -1, 107, 107, -1, 107, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 107, -1, -1, -1, 233, -1, 107, 107, -1, -1, 107, -1, -1, 107, -1, -1, 107, -1, -1, -1, -1, -1, -1, -1, -1, -1, 107, -1, -1, -1, -1, 107, -1, -1, 107, -1, -1, -1, -1, 107, -1, -1, -1, -1, 107, -1, -1, 107],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 20, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 20, -1, -1, -1, -1, -1, -1, -1, -1, 20, -1, -1, -1, -1, 20, -1, -1, -1, -1, -1, -1, -1, 20, 20, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 20, -1, -1, -1, -1, -1, -1, -1, -1, -1, 20, -1, -1, 20, -1, -1, 20, -1, -1, -1, -1, 20, -1, -1, -1, -1, 20, -1, -1, -1, -1, 20, -1, -1, 20, -1, -1, -1, -1, 20, -1, -1, -1, -1, 20, -1, -1, 20],
    [-1, -1, 7, -1, -1, 7, 7, 295, 7, -1, 7, 289, 2, 7, 289, 7, 7, 289, 289, -1, 7, 289, 7, 289, -1, 289, 289, 7, 7, 7, 289, 7, 7, 289, 289, -1, 7, 7, 289, 7, -1, 7, -1, 289, 7, 7, 289, -1, 7, 7, -1, 289, 289, 120, -1, -1, 289, 289, 7, 289, -1, 7, 7, -1, 289, 7, 7, 289, 7, 289, 7, 7, 7, 289, 289, 289, 7, 120, 7, 7, 7, -1, -1, -1, 7, 289, 289, 7, 7, 289, 289, 289, 7, 120, -1, 289, 7, 289, -1, 289, 289, 120, 289, 7, 289, 289, 120, -1, -1, 7, 7, 120, 7, 7, 60],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 220, -1, -1, -1, -1, -1, 220, -1, -1, -1, -1, -1, 220, -1, 220, -1, -1, -1, -1, 220, -1, -1, 220, 220, -1, -1, -1, 220, -1, -1, -1, -1, 220, -1, -1, 220, 220, -1, -1, -1, 220, 220, -1, -1, -1, 220, 220, -1, 220, -1, -1, -1, -1, 220, -1, -1, -1, -1, -1, -1, -1, -1, 220, 220, 220, -1, -1, -1, -1, -1, -1, -1, -1, -1, 220, -1, -1, -1, -1, -1, 220, -1, -1, -1, 220, -1, 220, -1, 220, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 69, -1, -1, -1, -1, -1, 69, -1, -1, -1, -1, -1, 69, -1, 69, -1, -1, -1, -1, 69, -1, -1, 69, 69, -1, -1, -1, 69, -1, -1, -1, -1, 69, -1, -1, 69, 69, -1, -1, -1, 69, 69, -1, -1, -1, 69, 69, -1, 69, -1, -1, -1, -1, 69, -1, -1, -1, -1, -1, -1, -1, -1, 69, 69, 69, -1, -1, -1, -1, -1, -1, -1, -1, -1, 69, -1, -1, -1, -1, -1, 69, -1, -1, -1, 69, -1, 69, -1, 69, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 133, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 134, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, 102, -1, 102, 102, -1, 102, -1, -1, 102, 11, -1, -1, 102, -1, 102, -1, 102, 102, 102, -1, -1, 102, 102, -1, 102, 102, -1, -1, -1, 102, -1, 102, -1, -1, 102, -1, 102, 102, 102, -1, 102, -1, 102, 102, 102, 102, -1, 102, 102, -1, 102, -1, -1, -1, -1, 102, -1, -1, 102, -1, 102, -1, -1, -1, 102, 102, 102, -1, 102, -1, -1, 102, -1, -1, 102, -1, 102, 102, -1, 102, 102, 102, 102, -1, 102, 102, 102, -1, 102, 102, 102, 102, 102, 102, -1, 102, 102, 102, -1, -1, -1, -1, 102, -1, -1, 102],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 116, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 38, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 302, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 151, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 132, -1, -1, -1, -1, -1, -1, -1, -1, 132, -1, -1, -1, -1, -1, 132, -1, -1, -1, -1, -1, 132, -1, 132, -1, -1, -1, -1, 132, -1, -1, 132, 132, -1, -1, -1, 132, -1, -1, -1, -1, 132, -1, -1, 132, 132, -1, -1, -1, 132, 132, -1, -1, -1, 132, 132, -1, 132, -1, -1, -1, -1, 132, -1, -1, -1, -1, -1, -1, -1, -1, 132, 132, 132, -1, -1, -1, -1, -1, -1, -1, 37, -1, 132, -1, -1, -1, -1, -1, 132, -1, -1, -1, 132, -1, 132, -1, 132, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 309, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 93, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 106, 272, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 17, -1, -1, -1, -1, -1, -1, 46, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 237, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 82, -1, 82, -1, -1, -1, -1, -1, -1, -1, 82, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 82, 82, -1, 82, -1, -1, -1, -1, -1, -1, -1, -1, -1, 82, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 79, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 82, 79, 79, -1, -1, -1, -1, -1, -1, -1, -1, 82, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 58, 58, -1, 58, -1, -1, 58, -1, -1, -1, 58, -1, 58, -1, 58, 58, 58, -1, -1, 58, 58, -1, 58, 58, -1, -1, -1, 58, -1, 58, -1, -1, 58, -1, 58, 58, 58, -1, 58, -1, 58, 58, 58, 58, -1, 58, 58, -1, 58, -1, -1, -1, -1, 58, -1, -1, 58, -1, 58, -1, -1, -1, 58, 58, 58, -1, 58, -1, -1, 58, -1, -1, 58, -1, 58, 58, -1, 58, 58, 58, 58, -1, 58, 58, 58, -1, 58, 58, 58, 58, 58, 58, -1, 58, 58, 58, -1, -1, -1, -1, 58, -1, -1, 58],
    [-1, -1, -1, -1, 81, -1, -1, -1, -1, -1, -1, -1, 81, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 81, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 81, -1, -1, -1, -1, 101, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 243, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, 33, -1, -1, -1, -1, -1, -1, -1, 33, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 33, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 33, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 158, -1, -1, -1, -1, -1, -1],
    [-1, -1, 119, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 165, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, 128, -1, 128, 128, -1, 128, -1, -1, 128, 128, -1, -1, 128, -1, 128, -1, 128, 128, 128, -1, -1, 128, 128, -1, 128, 128, -1, -1, -1, 128, -1, 128, -1, -1, 128, -1, 128, 128, 128, -1, 128, -1, 128, 128, 128, 128, -1, 128, 128, -1, 128, -1, -1, -1, -1, 128, -1, -1, 128, -1, 128, -1, -1, -1, 128, 128, 128, -1, 128, -1, -1, 128, -1, -1, 128, -1, 128, 128, -1, 128, 128, 128, 128, -1, 128, 128, 128, -1, 128, 128, 128, 128, 128, 128, -1, 128, 128, 128, -1, 85, -1, -1, 128, -1, -1, 128],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 13, -1, -1, -1, -1, -1, 13, -1, -1, -1, -1, -1, 13, -1, 13, -1, -1, -1, -1, 13, -1, -1, 13, 13, -1, -1, -1, 13, -1, -1, -1, -1, 13, -1, -1, 13, 13, -1, -1, -1, 13, 13, -1, -1, -1, 13, 13, -1, 13, -1, -1, -1, -1, 13, -1, -1, -1, -1, -1, -1, -1, -1, 13, 13, 13, -1, -1, -1, -1, -1, -1, -1, -1, -1, 13, -1, -1, -1, -1, -1, 13, -1, -1, -1, 13, -1, 13, -1, 13, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 96, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 310, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 308, -1, 308, 308, -1, -1, -1, -1, -1, 308, 308, -1, -1, -1, -1, 308, -1, 308, -1, -1, -1, 308, -1, 308, -1, -1, -1, -1, 308, -1, 308, 308, 308, 308, -1, -1, 308, -1, -1, -1, -1, 308, -1, 308, 308, 308, -1, 304, 308, 308, 308, -1, -1, 308, 308, 308, -1, 308, -1, -1, -1, -1, 308, -1, -1, -1, -1, -1, -1, -1, 308, 308, 308, 308, -1, -1, -1, -1, -1, -1, -1, 308, -1, 308, -1, -1, 308, -1, -1, 308, -1, -1, -1, 308, -1, 308, -1, 308, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, 239, -1, -1, -1, -1, -1, 298, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 99, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 192, -1, -1, -1, -1, -1, -1, -1, 123, -1, -1, -1, -1, -1, -1, -1, 190, -1, -1, -1, -1, 211, -1, -1, -1, -1, 191, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 185, 51, -1, -1, -1, -1, 185, -1, -1, -1, -1, -1, 185, -1, 185, -1, -1, -1, -1, 185, -1, -1, 185, 185, -1, -1, -1, 185, -1, -1, -1, -1, 185, -1, -1, 185, 185, -1, -1, -1, 185, 185, -1, -1, -1, 185, 185, -1, 185, -1, -1, -1, -1, 185, -1, -1, -1, -1, -1, -1, -1, -1, 185, 185, 185, -1, -1, -1, -1, -1, -1, -1, -1, -1, 185, -1, -1, -1, -1, -1, 185, -1, -1, -1, 185, -1, 185, -1, 185, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 395, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 143, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 155, -1, -1, -1, 47, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 76, 61, -1, -1, -1, 49, 94, -1, -1, -1, -1, 345, -1, 312, -1, -1, -1, -1, 303, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 355, -1, -1, -1, -1, -1, -1, -1, -1, -1, 181, -1, -1, -1, -1, -1, 255, -1, -1, -1, 10, -1, 285, -1, 412, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 290, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 91, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, 321, -1, -1, -1, -1, -1, -1, -1, 321, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 321, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 321, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 324, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 407, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 111, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 416, -1, 416, -1, -1, -1, -1, -1, -1, -1, 416, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 416, -1, -1, 416, -1, -1, -1, -1, -1, -1, -1, -1, -1, 416, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 416, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 416, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 414, -1, -1, -1, -1, -1, -1, -1, -1, 273, -1, -1, -1, -1, -1, 273, -1, -1, -1, -1, -1, 273, -1, 273, -1, -1, -1, -1, 273, -1, -1, 273, 273, -1, -1, -1, 273, -1, -1, -1, -1, 273, -1, -1, 273, 273, -1, -1, -1, 273, 273, -1, -1, -1, 273, 273, -1, 273, -1, -1, -1, -1, 273, -1, -1, -1, -1, -1, -1, -1, -1, 273, 273, 273, -1, -1, -1, -1, -1, -1, -1, -1, -1, 273, -1, -1, -1, -1, -1, 273, -1, -1, -1, 273, -1, 273, -1, 273, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 28, -1, 28, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 28, -1, -1, -1, -1, 28, -1, -1, -1, 28, -1, -1, -1, -1, 28, -1, -1, -1, 28, -1, -1, -1, 28, 28, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 28, -1, -1, -1, -1, 28, -1, -1, -1, -1, 28, -1, -1, 28, -1, -1, 28, -1, -1, -1, -1, -1, -1, -1, -1, -1, 28, -1, -1, -1, -1, 28, -1, -1, 28, -1, -1, -1, -1, 28, -1, -1, -1, -1, 28, -1, -1, 28],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 172, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 29, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 15, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, 145, -1, 145, 145, -1, 145, -1, -1, 145, 145, -1, -1, 145, -1, 145, -1, 145, 145, 145, -1, -1, 145, 145, -1, 145, 145, -1, -1, -1, 145, -1, 145, -1, -1, 145, -1, 145, 145, 145, -1, 145, -1, 145, 145, 145, 145, -1, 145, 145, -1, 145, -1, -1, -1, -1, 145, -1, -1, 145, -1, 145, -1, -1, -1, 145, 145, 145, -1, 145, -1, -1, 145, -1, -1, 145, -1, 145, 145, -1, 145, 145, 145, 145, -1, 145, 145, 145, -1, 145, 145, 145, 145, 145, 145, -1, 145, 145, 145, -1, 145, -1, -1, 145, -1, -1, 145],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 340, -1, -1, -1, 337, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 340, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 54, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 241, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [311, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 62, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 62, -1, -1, 62, -1, -1, -1, -1, -1, -1, -1, -1, -1, 62, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 62, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 196, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 196, -1, 398, -1, -1, -1, -1, -1, -1, 196, -1, -1, -1, -1, 196, -1, -1, -1, -1, -1, -1, -1, 196, 196, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 196, -1, -1, -1, -1, -1, -1, -1, -1, -1, 196, -1, -1, 196, -1, -1, 196, -1, -1, -1, -1, -1, -1, -1, -1, -1, 196, -1, -1, -1, -1, 196, -1, -1, 196, -1, -1, -1, -1, 196, -1, -1, -1, -1, 196, -1, -1, 196],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 110, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, 383, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 380, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, 57, -1, 57, 57, -1, 57, -1, -1, 57, 57, -1, -1, 57, -1, 57, -1, 57, 57, 57, -1, -1, 57, 57, -1, 57, 57, -1, -1, -1, 57, -1, 57, -1, -1, 57, -1, 57, 57, 57, -1, 57, -1, 57, 57, 57, 57, -1, 57, 57, -1, 57, -1, -1, -1, -1, 57, -1, -1, 57, -1, 57, -1, -1, -1, 57, 57, 57, -1, 57, -1, -1, 57, -1, -1, 57, -1, 57, 57, -1, 57, 57, 57, 57, -1, 57, 57, 57, -1, 57, 57, 57, 57, 57, 57, -1, 57, 57, 57, -1, 57, -1, -1, 57, -1, -1, 57],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 163, 72, -1, -1, -1, -1, 163, -1, -1, -1, -1, -1, 163, -1, 163, -1, -1, -1, -1, 163, 72, -1, 163, 163, -1, -1, -1, 163, -1, 72, -1, -1, 163, -1, 72, 163, 163, -1, -1, -1, 163, 163, 72, 72, -1, 163, 163, -1, 163, -1, -1, -1, -1, 163, -1, -1, 72, -1, -1, -1, -1, -1, 163, 163, 163, -1, 72, -1, -1, 72, -1, -1, 72, -1, 163, -1, -1, 92, -1, -1, 163, -1, 72, -1, 163, -1, 163, 72, 163, -1, 72, -1, -1, -1, -1, 72, -1, -1, -1, -1, 72, -1, -1, 72],
    [350, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 41, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 117, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 364, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 364, -1, -1, -1, -1, -1, -1, -1, -1, 364, -1, -1, -1, -1, 364, -1, -1, -1, 386, -1, -1, -1, 364, 364, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 364, -1, -1, -1, -1, -1, -1, -1, -1, -1, 364, -1, -1, 364, -1, -1, 364, -1, -1, -1, -1, -1, -1, -1, -1, -1, 364, -1, -1, -1, -1, 364, -1, -1, 364, -1, -1, -1, -1, 364, -1, -1, -1, -1, 364, -1, -1, 364],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 144, -1, -1, -1, -1, -1, 144, -1, -1, -1, -1, -1, 144, -1, 144, -1, -1, -1, -1, 144, -1, -1, 144, 144, -1, -1, -1, 144, -1, -1, -1, -1, 144, -1, -1, 144, 144, -1, -1, -1, 144, 144, -1, -1, -1, 144, 144, -1, 144, -1, -1, -1, -1, 144, -1, -1, -1, -1, -1, -1, -1, -1, 144, 144, 144, -1, -1, -1, -1, -1, -1, -1, -1, -1, 144, -1, -1, -1, -1, -1, 144, -1, -1, -1, 144, -1, 144, -1, 144, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 242, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 352, -1, 352, -1, -1, -1, -1, -1, -1, -1, 352, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 352, -1, -1, 352, -1, -1, -1, -1, -1, -1, -1, -1, -1, 352, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 352, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 352, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 152, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 140, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 140, 140, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 351, 351, -1, 351, -1, -1, -1, -1, 63, -1, 63, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 154, -1, -1, -1, -1, -1, -1, 63, 326, -1, -1, -1, 63, -1, -1, -1, 63, -1, -1, -1, -1, 63, -1, -1, -1, 63, -1, -1, -1, 63, 63, -1, -1, -1, -1, -1, -1, -1, 351, -1, -1, -1, 351, 63, -1, -1, -1, 351, 63, -1, -1, -1, -1, 63, -1, -1, 63, -1, -1, 63, -1, -1, -1, -1, 351, -1, -1, -1, -1, 63, -1, -1, -1, -1, 63, -1, -1, 63, -1, -1, -1, -1, 63, -1, -1, -1, -1, 63, -1, -1, 63],
    [-1, -1, 212, -1, -1, -1, -1, -1, -1, -1, -1, -1, 236, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 236, -1, -1, -1, -1, -1, -1, -1, -1, 236, -1, -1, -1, -1, 236, -1, -1, -1, -1, -1, -1, -1, 236, 236, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 236, -1, -1, -1, -1, -1, -1, -1, -1, -1, 236, -1, -1, 236, -1, -1, 236, -1, -1, -1, -1, 212, -1, -1, -1, -1, 236, -1, -1, -1, -1, 236, -1, -1, 236, -1, -1, -1, -1, 236, -1, -1, -1, -1, 236, -1, -1, 236],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 194, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 5, -1, -1, -1, -1, -1, 21, -1, -1, -1, -1, -1, 293, -1, 21, -1, -1, -1, -1, 5, -1, -1, 21, 5, -1, -1, -1, 21, -1, -1, -1, -1, 21, -1, -1, 5, 5, -1, -1, -1, 5, 5, -1, -1, -1, 173, 5, -1, 5, -1, -1, -1, -1, 5, -1, -1, -1, -1, -1, -1, -1, -1, 173, 173, 5, -1, -1, -1, -1, -1, -1, -1, -1, -1, 5, -1, -1, -1, -1, -1, 5, -1, -1, -1, 5, -1, 5, -1, 5, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 286, -1, -1, -1, -1, -1, 286, -1, -1, -1, -1, -1, 286, -1, 286, -1, -1, -1, -1, 286, -1, 286, 286, 286, -1, -1, -1, 286, -1, -1, -1, -1, 286, -1, -1, 286, 286, -1, 286, -1, 286, 286, -1, -1, -1, 286, 286, -1, 286, -1, -1, -1, -1, 286, -1, -1, -1, -1, -1, -1, -1, -1, 286, 286, 286, -1, -1, -1, -1, -1, -1, -1, -1, -1, 286, -1, -1, 286, -1, -1, 286, -1, -1, -1, 286, -1, 286, -1, 286, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 410, -1, 410, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 410, -1, -1, -1, -1, 410, -1, -1, -1, 410, -1, -1, -1, -1, 410, -1, -1, -1, 410, -1, -1, -1, 410, 410, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 410, -1, -1, -1, -1, 410, -1, -1, -1, -1, 410, -1, -1, 410, -1, -1, 410, -1, -1, -1, -1, -1, -1, -1, -1, -1, 410, -1, -1, -1, -1, 410, -1, -1, 410, -1, -1, -1, -1, 410, -1, -1, -1, -1, 410, -1, -1, 410],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 84, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 288, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 281, -1, 118, -1, -1, -1, -1, -1, -1, -1, 118, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 281, -1, -1, 281, -1, -1, -1, -1, -1, -1, -1, -1, -1, 118, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 281, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 316, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 278, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 70, -1, -1, -1, -1, -1, -1, -1, 314, -1, -1, -1, -1, 83, -1, -1, -1, -1, 335, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 209, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 418, -1, -1, -1, -1, 418, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 418, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 175, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 175, -1, -1, 175, -1, -1, -1, -1, -1, -1, -1, -1, -1, 175, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 175, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 135, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 182, -1, 182, 182, -1, -1, -1, -1, -1, 182, 182, -1, -1, -1, -1, 182, -1, 182, -1, -1, -1, 182, -1, 182, -1, -1, -1, -1, 182, -1, 182, 182, 182, 182, -1, -1, 182, -1, -1, -1, -1, 182, -1, 182, 182, 182, -1, 179, 182, 182, 182, -1, -1, 182, 182, 182, -1, 182, -1, -1, -1, -1, 182, -1, -1, -1, -1, -1, -1, -1, 182, 182, 182, 182, -1, -1, -1, -1, -1, -1, -1, 182, -1, 182, -1, -1, 182, -1, -1, 182, -1, -1, -1, 182, -1, 182, -1, 182, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 262, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 122, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 78, -1, 78, -1, -1, -1, -1, -1, -1, -1, 78, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 78, 78, -1, 78, -1, -1, -1, -1, -1, -1, -1, -1, -1, 78, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 78, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 78, 78, 78, -1, -1, -1, -1, -1, -1, -1, -1, 78, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 360, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 360, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 360, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, 200, 200, -1, -1, -1, -1, -1, 200, 200, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 409, -1, -1, 200, -1, -1, -1, 200, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 200, 200, 200, -1, -1, -1, 200, 200, -1, -1, -1, 200, 200, -1, 200, -1, -1, -1, -1, 200, -1, -1, -1, -1, -1, -1, -1, -1, 200, 200, 200, -1, -1, -1, -1, -1, -1, -1, 200, -1, 200, -1, -1, -1, -1, -1, 200, -1, -1, -1, 200, -1, 200, -1, 200, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 402, -1, 408, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 408, -1, -1, -1, -1, 402, -1, -1, -1, 408, -1, -1, -1, -1, 408, -1, -1, -1, 408, -1, -1, -1, 408, 408, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 408, -1, -1, -1, -1, 402, -1, -1, -1, -1, 408, -1, -1, 408, -1, -1, 408, -1, -1, -1, -1, -1, -1, -1, -1, -1, 408, -1, -1, -1, -1, 408, -1, -1, 408, -1, -1, -1, -1, 408, -1, -1, -1, -1, 408, -1, -1, 408],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 4, -1, -1, -1, -1, 104, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 361, -1, -1, -1, -1, 361, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 0, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 420, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 423, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, 55, 55, -1, -1, -1, -1, -1, 55, 55, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 55, -1, -1, -1, 55, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 55, 55, 55, -1, -1, -1, 55, 55, -1, -1, -1, 55, 55, -1, 55, -1, -1, -1, -1, 55, -1, -1, -1, -1, -1, -1, -1, -1, 55, 55, 55, -1, -1, -1, -1, -1, -1, -1, 55, -1, 55, -1, -1, -1, -1, -1, 55, -1, -1, -1, 55, -1, 55, -1, 55, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [323, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 26, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 254, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 325, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 424, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 325, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 147, -1, 147, -1, -1, -1, -1, -1, -1, -1, 147, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 147, -1, -1, 147, -1, -1, -1, -1, -1, -1, -1, -1, -1, 147, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 147, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 147, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 377, -1, -1, -1, -1, -1, 377, -1, -1, -1, -1, -1, 377, -1, 377, -1, -1, -1, -1, 377, -1, -1, 377, 377, -1, -1, -1, 377, -1, -1, -1, -1, 377, -1, -1, 377, 377, -1, -1, -1, 377, 377, -1, -1, -1, 377, 377, -1, 377, -1, -1, -1, -1, 377, -1, -1, -1, -1, -1, -1, -1, -1, 377, 377, 377, -1, -1, -1, -1, -1, -1, -1, -1, -1, 377, -1, -1, -1, -1, -1, 377, -1, -1, -1, 377, -1, 377, -1, 377, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 75, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 32, -1, -1, 75, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 170, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 197, -1, 219, -1, -1, -1, -1, -1, -1, 219, -1, -1, -1, -1, 121, -1, -1, -1, -1, 197, -1, -1, -1, -1, -1, -1, -1, -1, 197, -1, -1, -1, -1, 197, -1, -1, -1, 112, -1, -1, -1, 197, 197, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 197, -1, 121, -1, -1, -1, -1, -1, -1, -1, 197, -1, -1, 197, -1, -1, 197, -1, -1, 90, -1, 197, 121, 121, -1, -1, 197, 19, -1, -1, -1, 197, -1, 219, 197, 90, -1, 19, 19, 197, -1, -1, -1, -1, 197, -1, -1, 197],
  ]
  def terminal(self, str):
    return self.str_terminal[str]
  def terminalNames(self):
    return list(self.str_terminal.keys())
  def isTerminal(self, id):
    return 0 <= id <= 114
  def isNonTerminal(self, id):
    return 115 <= id <= 245
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
    return self.parse_table[n - 115][self.sym.getId()]
  def call(self, nt_str):
    return getattr(self, nt_str)()
  def __GEN36(self, depth=0, tracer=None):
    rule = self.rule(115)
    tree = ParseTree( NonTerminal(115, self.getAtomString(115)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [2, 12, 4, 32, 72, 35, 45]):
      return tree
    if self.sym == None:
      return tree
    if rule == 210:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._POINTER_SUB(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN36(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _POINTER_OPT(self, depth=0, tracer=None):
    rule = self.rule(116)
    tree = ParseTree( NonTerminal(116, self.getAtomString(116)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [2, 12, 4, 32, 72, 35, 45]):
      return tree
    if self.sym == None:
      return tree
    if rule == 100:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._POINTER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _TRAILING_COMMA_OPT(self, depth=0, tracer=None):
    rule = self.rule(118)
    tree = ParseTree( NonTerminal(118, self.getAtomString(118)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [27]):
      return tree
    if self.sym == None:
      return tree
    if rule == 403:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(3, tracer) # trailing_comma
      tree.add(t)
      return tree
    return tree
  def _SPECIFIER_QUALIFIER(self, depth=0, tracer=None):
    rule = self.rule(119)
    tree = ParseTree( NonTerminal(119, self.getAtomString(119)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 171:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._TYPE_SPECIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 277:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._TYPE_QUALIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN20(self, depth=0, tracer=None):
    rule = self.rule(120)
    tree = ParseTree( NonTerminal(120, self.getAtomString(120)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [83, 45, 12, 5, 4]):
      return tree
    if self.sym == None:
      return tree
    if rule == 217:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._SPECIFIER_QUALIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN20(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _UNION_SPECIFIER(self, depth=0, tracer=None):
    rule = self.rule(121)
    tree = ParseTree( NonTerminal(121, self.getAtomString(121)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 56:
      tree.astTransform = AstTransformNodeCreator('Union', {'definition': 1})
      t = self.expect(95, tracer) # union
      tree.add(t)
      t = self.expect(55, tracer) # declarator_hint
      tree.add(t)
      subtree = self._STRUCT_OR_UNION_SUB(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _EXTERNAL_DECLARATOR(self, depth=0, tracer=None):
    rule = self.rule(122)
    tree = ParseTree( NonTerminal(122, self.getAtomString(122)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 313:
      tree.astTransform = AstTransformNodeCreator('ExternalDeclarator', {'init_declarator': 1})
      t = self.expect(55, tracer) # declarator_hint
      tree.add(t)
      subtree = self._INIT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _DIRECT_DECLARATOR_MODIFIER_LIST_OPT(self, depth=0, tracer=None):
    rule = self.rule(123)
    tree = ParseTree( NonTerminal(123, self.getAtomString(123)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [83, 53, 77, 31, 114, 93, 54, 98, 12, 101, 40, 106, 67, 80, 45, 111]):
      return tree
    if self.sym == None:
      return tree
    if rule == 257:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN28(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _DIRECT_DECLARATOR_SIZE(self, depth=0, tracer=None):
    rule = self.rule(124)
    tree = ParseTree( NonTerminal(124, self.getAtomString(124)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 225:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 249:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(83, tracer) # asterisk
      tree.add(t)
      return tree
    elif self.sym.getId() in [54, 53, 77, 31, 114, 93, 83, 98, 12, 101, 40, 106, 67, 80, 45, 111]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _KEYWORD(self, depth=0, tracer=None):
    rule = self.rule(125)
    tree = ParseTree( NonTerminal(125, self.getAtomString(125)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 14:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(99, tracer) # double
      tree.add(t)
      return tree
    elif rule == 31:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(43, tracer) # register
      tree.add(t)
      return tree
    elif rule == 40:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(23, tracer) # inline
      tree.add(t)
      return tree
    elif rule == 42:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(95, tracer) # union
      tree.add(t)
      return tree
    elif rule == 98:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(97, tracer) # short
      tree.add(t)
      return tree
    elif rule == 103:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(59, tracer) # bool
      tree.add(t)
      return tree
    elif rule == 108:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(104, tracer) # default
      tree.add(t)
      return tree
    elif rule == 113:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(64, tracer) # long
      tree.add(t)
      return tree
    elif rule == 129:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(91, tracer) # float
      tree.add(t)
      return tree
    elif rule == 130:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(14, tracer) # while
      tree.add(t)
      return tree
    elif rule == 137:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(86, tracer) # switch
      tree.add(t)
      return tree
    elif rule == 141:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(46, tracer) # unsigned
      tree.add(t)
      return tree
    elif rule == 148:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(18, tracer) # else
      tree.add(t)
      return tree
    elif rule == 160:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(51, tracer) # void
      tree.add(t)
      return tree
    elif rule == 168:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(90, tracer) # continue
      tree.add(t)
      return tree
    elif rule == 169:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(52, tracer) # struct
      tree.add(t)
      return tree
    elif rule == 177:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(85, tracer) # enum
      tree.add(t)
      return tree
    elif rule == 193:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(102, tracer) # if
      tree.add(t)
      return tree
    elif rule == 195:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(17, tracer) # typedef
      tree.add(t)
      return tree
    elif rule == 205:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(34, tracer) # imaginary
      tree.add(t)
      return tree
    elif rule == 232:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(57, tracer) # char
      tree.add(t)
      return tree
    elif rule == 235:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(30, tracer) # complex
      tree.add(t)
      return tree
    elif rule == 271:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(100, tracer) # for
      tree.add(t)
      return tree
    elif rule == 276:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(75, tracer) # int
      tree.add(t)
      return tree
    elif rule == 299:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(33, tracer) # static
      tree.add(t)
      return tree
    elif rule == 306:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(73, tracer) # volatile
      tree.add(t)
      return tree
    elif rule == 307:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(25, tracer) # extern
      tree.add(t)
      return tree
    elif rule == 336:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(21, tracer) # do
      tree.add(t)
      return tree
    elif rule == 342:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(67, tracer) # sizeof
      tree.add(t)
      return tree
    elif rule == 346:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(74, tracer) # restrict
      tree.add(t)
      return tree
    elif rule == 349:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(69, tracer) # goto
      tree.add(t)
      return tree
    elif rule == 358:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(89, tracer) # break
      tree.add(t)
      return tree
    elif rule == 373:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(11, tracer) # signed
      tree.add(t)
      return tree
    elif rule == 379:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(38, tracer) # auto
      tree.add(t)
      return tree
    elif rule == 384:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(56, tracer) # const
      tree.add(t)
      return tree
    elif rule == 401:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(105, tracer) # case
      tree.add(t)
      return tree
    elif rule == 419:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(26, tracer) # return
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _STRUCT_DECLARATOR(self, depth=0, tracer=None):
    rule = self.rule(126)
    tree = ParseTree( NonTerminal(126, self.getAtomString(126)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 199:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STRUCT_DECLARATOR_BODY(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 208:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN23(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [45, 4, 12]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN23(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN21(self, depth=0, tracer=None):
    rule = self.rule(127)
    tree = ParseTree( NonTerminal(127, self.getAtomString(127)), tracer )
    tree.list = 'slist'
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 283:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STRUCT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN22(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [45, 4, 12]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STRUCT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN22(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _BLOCK_ITEM(self, depth=0, tracer=None):
    rule = self.rule(128)
    tree = ParseTree( NonTerminal(128, self.getAtomString(128)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 318:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 354:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DECLARATION(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [54, 53, 77, 31, 114, 93, 83, 98, 12, 101, 40, 106, 67, 80, 45, 111]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _TYPE_QUALIFIER(self, depth=0, tracer=None):
    rule = self.rule(129)
    tree = ParseTree( NonTerminal(129, self.getAtomString(129)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 230:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(56, tracer) # const
      tree.add(t)
      return tree
    elif rule == 363:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(74, tracer) # restrict
      tree.add(t)
      return tree
    elif rule == 376:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(73, tracer) # volatile
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN38(self, depth=0, tracer=None):
    rule = self.rule(130)
    tree = ParseTree( NonTerminal(130, self.getAtomString(130)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [27]):
      return tree
    if self.sym == None:
      return tree
    if rule == 22:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._BLOCK_ITEM(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN38(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [54, 53, 77, 31, 114, 93, 83, 98, 12, 101, 40, 106, 67, 80, 45, 111]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._BLOCK_ITEM(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN38(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    return tree
  def _DECLARATOR(self, depth=0, tracer=None):
    rule = self.rule(131)
    tree = ParseTree( NonTerminal(131, self.getAtomString(131)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 246:
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
    elif self.sym.getId() in [45, 4, 12]:
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
  def __GEN5(self, depth=0, tracer=None):
    rule = self.rule(132)
    tree = ParseTree( NonTerminal(132, self.getAtomString(132)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [49, 88, 32]):
      return tree
    if self.sym == None:
      return tree
    if rule == 184:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DECLARATION_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN28(self, depth=0, tracer=None):
    rule = self.rule(133)
    tree = ParseTree( NonTerminal(133, self.getAtomString(133)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [83, 53, 40, 31, 114, 93, 54, 98, 12, 101, 77, 111, 67, 80, 45, 106]):
      return tree
    if self.sym == None:
      return tree
    if rule == 25:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DIRECT_DECLARATOR_MODIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN28(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _ENUMERATION_CONSTANT(self, depth=0, tracer=None):
    rule = self.rule(134)
    tree = ParseTree( NonTerminal(134, self.getAtomString(134)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 256:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(12, tracer) # identifier
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _ENUMERATOR_ASSIGNMENT(self, depth=0, tracer=None):
    rule = self.rule(135)
    tree = ParseTree( NonTerminal(135, self.getAtomString(135)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [32, 3]):
      return tree
    if self.sym == None:
      return tree
    if rule == 164:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(36, tracer) # assign
      tree.add(t)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _BLOCK_ITEM_LIST(self, depth=0, tracer=None):
    rule = self.rule(136)
    tree = ParseTree( NonTerminal(136, self.getAtomString(136)), tracer )
    tree.list = False
    if self.sym == None:
      return tree
    if rule == 50:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN38(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [54, 53, 77, 31, 114, 93, 83, 98, 12, 101, 40, 106, 67, 80, 45, 111]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN38(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _DIRECT_ABSTRACT_DECLARATOR_SUB1(self, depth=0, tracer=None):
    rule = self.rule(137)
    tree = ParseTree( NonTerminal(137, self.getAtomString(137)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 52:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(45, tracer) # lparen
      tree.add(t)
      subtree = self._DIRECT_ABSTRACT_DECLARATOR_SUB2(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(2, tracer) # rparen
      tree.add(t)
      return tree
    elif rule == 87:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(72, tracer) # lsquare
      tree.add(t)
      subtree = self._DIRECT_ABSTRACT_DECLARATOR_EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(71, tracer) # rsquare
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN9(self, depth=0, tracer=None):
    rule = self.rule(138)
    tree = ParseTree( NonTerminal(138, self.getAtomString(138)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [2, 35, 32]):
      return tree
    if self.sym == None:
      return tree
    if rule == 378:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DIRECT_ABSTRACT_DECLARATOR_SUB1(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN9(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _COMPOUND_STATEMENT(self, depth=0, tracer=None):
    rule = self.rule(139)
    tree = ParseTree( NonTerminal(139, self.getAtomString(139)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 240:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(49, tracer) # lbrace
      tree.add(t)
      subtree = self.__GEN37(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(27, tracer) # rbrace
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _PUNCTUATOR(self, depth=0, tracer=None):
    rule = self.rule(140)
    tree = ParseTree( NonTerminal(140, self.getAtomString(140)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 3:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(78, tracer) # rshifteq
      tree.add(t)
      return tree
    elif rule == 6:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(6, tracer) # addeq
      tree.add(t)
      return tree
    elif rule == 23:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(92, tracer) # neq
      tree.add(t)
      return tree
    elif rule == 27:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(70, tracer) # bitoreq
      tree.add(t)
      return tree
    elif rule == 34:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(32, tracer) # comma
      tree.add(t)
      return tree
    elif rule == 35:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(8, tracer) # gteq
      tree.add(t)
      return tree
    elif rule == 44:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(44, tracer) # mod
      tree.add(t)
      return tree
    elif rule == 45:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(80, tracer) # decr
      tree.add(t)
      return tree
    elif rule == 48:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(87, tracer) # bitandeq
      tree.add(t)
      return tree
    elif rule == 53:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(20, tracer) # div
      tree.add(t)
      return tree
    elif rule == 59:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(68, tracer) # gt
      tree.add(t)
      return tree
    elif rule == 65:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(13, tracer) # muleq
      tree.add(t)
      return tree
    elif rule == 67:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(58, tracer) # elipsis
      tree.add(t)
      return tree
    elif rule == 73:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(61, tracer) # bitxor
      tree.add(t)
      return tree
    elif rule == 74:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(41, tracer) # tilde
      tree.add(t)
      return tree
    elif rule == 80:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(110, tracer) # eq
      tree.add(t)
      return tree
    elif rule == 109:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(96, tracer) # lshifteq
      tree.add(t)
      return tree
    elif rule == 114:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(79, tracer) # bitxoreq
      tree.add(t)
      return tree
    elif rule == 124:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(72, tracer) # lsquare
      tree.add(t)
      return tree
    elif rule == 125:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(37, tracer) # rshift
      tree.add(t)
      return tree
    elif rule == 126:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(45, tracer) # lparen
      tree.add(t)
      return tree
    elif rule == 136:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(62, tracer) # questionmark
      tree.add(t)
      return tree
    elif rule == 156:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(31, tracer) # incr
      tree.add(t)
      return tree
    elif rule == 161:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(39, tracer) # exclamation_point
      tree.add(t)
      return tree
    elif rule == 178:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(65, tracer) # add
      tree.add(t)
      return tree
    elif rule == 180:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(112, tracer) # lteq
      tree.add(t)
      return tree
    elif rule == 189:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(113, tracer) # subeq
      tree.add(t)
      return tree
    elif rule == 206:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(48, tracer) # ampersand
      tree.add(t)
      return tree
    elif rule == 214:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(22, tracer) # or
      tree.add(t)
      return tree
    elif rule == 216:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(27, tracer) # rbrace
      tree.add(t)
      return tree
    elif rule == 226:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(15, tracer) # pound
      tree.add(t)
      return tree
    elif rule == 229:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(109, tracer) # lt
      tree.add(t)
      return tree
    elif rule == 244:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(76, tracer) # sub
      tree.add(t)
      return tree
    elif rule == 247:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(5, tracer) # colon
      tree.add(t)
      return tree
    elif rule == 250:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(28, tracer) # lshift
      tree.add(t)
      return tree
    elif rule == 252:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(10, tracer) # dot
      tree.add(t)
      return tree
    elif rule == 260:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(66, tracer) # arrow
      tree.add(t)
      return tree
    elif rule == 263:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(71, tracer) # rsquare
      tree.add(t)
      return tree
    elif rule == 265:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(103, tracer) # and
      tree.add(t)
      return tree
    elif rule == 282:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(2, tracer) # rparen
      tree.add(t)
      return tree
    elif rule == 332:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(49, tracer) # lbrace
      tree.add(t)
      return tree
    elif rule == 344:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(16, tracer) # bitor
      tree.add(t)
      return tree
    elif rule == 372:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(88, tracer) # semi
      tree.add(t)
      return tree
    elif rule == 391:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(84, tracer) # modeq
      tree.add(t)
      return tree
    elif rule == 404:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(29, tracer) # poundpound
      tree.add(t)
      return tree
    elif rule == 417:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(36, tracer) # assign
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _ENUMERATOR(self, depth=0, tracer=None):
    rule = self.rule(141)
    tree = ParseTree( NonTerminal(141, self.getAtomString(141)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 127:
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
  def __GEN2(self, depth=0, tracer=None):
    rule = self.rule(142)
    tree = ParseTree( NonTerminal(142, self.getAtomString(142)), tracer )
    tree.list = 'mlist'
    if self.sym != None and (self.sym.getId() in [50, 83, 2, 88, 4, 72, 45, 32, 35, 12, 55, 19]):
      return tree
    if self.sym == None:
      return tree
    if rule == 24:
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
  def __GEN8(self, depth=0, tracer=None):
    rule = self.rule(143)
    tree = ParseTree( NonTerminal(143, self.getAtomString(143)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [2, 72, 32, 45, 35]):
      return tree
    if self.sym == None:
      return tree
    if rule == 234:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DIRECT_ABSTRACT_DECLARATOR_SUB0(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _INIT_DECLARATOR(self, depth=0, tracer=None):
    rule = self.rule(144)
    tree = ParseTree( NonTerminal(144, self.getAtomString(144)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 8:
      tree.astTransform = AstTransformNodeCreator('InitDeclarator', {'initializer': 1, 'declarator': 0})
      subtree = self._DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN13(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [45, 4, 12]:
      tree.astTransform = AstTransformNodeCreator('InitDeclarator', {'initializer': 1, 'declarator': 0})
      subtree = self._DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN13(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _STRUCT_DECLARATOR_BODY(self, depth=0, tracer=None):
    rule = self.rule(145)
    tree = ParseTree( NonTerminal(145, self.getAtomString(145)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 279:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(5, tracer) # colon
      tree.add(t)
      subtree = self._DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _ABSTRACT_DECLARATOR(self, depth=0, tracer=None):
    rule = self.rule(146)
    tree = ParseTree( NonTerminal(146, self.getAtomString(146)), tracer )
    tree.list = False
    if self.sym == None:
      return tree
    if rule == 64:
      tree.astTransform = AstTransformNodeCreator('AbstractDeclarator', {'direct_abstract_declarator': 1, 'pointer': 1})
      subtree = self._POINTER_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN35(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN25(self, depth=0, tracer=None):
    rule = self.rule(147)
    tree = ParseTree( NonTerminal(147, self.getAtomString(147)), tracer )
    tree.list = 'slist'
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 9:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._ENUMERATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN26(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _LABELED_STATEMENT(self, depth=0, tracer=None):
    rule = self.rule(148)
    tree = ParseTree( NonTerminal(148, self.getAtomString(148)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 183:
      tree.astTransform = AstTransformNodeCreator('DefaultCase', {'statement': 2})
      t = self.expect(104, tracer) # default
      tree.add(t)
      t = self.expect(5, tracer) # colon
      tree.add(t)
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 274:
      tree.astTransform = AstTransformNodeCreator('Case', {'expr': 1, 'statement': 3})
      t = self.expect(105, tracer) # case
      tree.add(t)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(5, tracer) # colon
      tree.add(t)
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 297:
      tree.astTransform = AstTransformNodeCreator('Label', {'name': 0, 'statement': 1})
      t = self.expect(94, tracer) # label_hint
      tree.add(t)
      t = self.expect(12, tracer) # identifier
      tree.add(t)
      t = self.expect(5, tracer) # colon
      tree.add(t)
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _DIRECT_DECLARATOR_EXPR(self, depth=0, tracer=None):
    rule = self.rule(149)
    tree = ParseTree( NonTerminal(149, self.getAtomString(149)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 399:
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
    elif self.sym.getId() in [54, 53, 77, 31, 114, 93, 83, 98, 12, 101, 40, 106, 67, 80, 45, 111]:
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
  def _ENUM_SPECIFIER_SUB(self, depth=0, tracer=None):
    rule = self.rule(150)
    tree = ParseTree( NonTerminal(150, self.getAtomString(150)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 162:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._IDENTIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN24(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 267:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._ENUM_SPECIFIER_BODY(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN23(self, depth=0, tracer=None):
    rule = self.rule(151)
    tree = ParseTree( NonTerminal(151, self.getAtomString(151)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [32, 88]):
      return tree
    if self.sym == None:
      return tree
    if rule == 269:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STRUCT_DECLARATOR_BODY(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN42(self, depth=0, tracer=None):
    rule = self.rule(152)
    tree = ParseTree( NonTerminal(152, self.getAtomString(152)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 275:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__EXPR_SANS_COMMA(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN43(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN43(self, depth=0, tracer=None):
    rule = self.rule(153)
    tree = ParseTree( NonTerminal(153, self.getAtomString(153)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 261:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(32, tracer) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self.__EXPR_SANS_COMMA(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN43(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN6(self, depth=0, tracer=None):
    rule = self.rule(154)
    tree = ParseTree( NonTerminal(154, self.getAtomString(154)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [49, 88, 32]):
      return tree
    if self.sym == None:
      return tree
    if rule == 388:
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
  def __GEN26(self, depth=0, tracer=None):
    rule = self.rule(155)
    tree = ParseTree( NonTerminal(155, self.getAtomString(155)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in [3]):
      return tree
    if self.sym == None:
      return tree
    if rule == 12:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(32, tracer) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self._ENUMERATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN26(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _DIRECT_ABSTRACT_DECLARATOR_EXPR(self, depth=0, tracer=None):
    rule = self.rule(156)
    tree = ParseTree( NonTerminal(156, self.getAtomString(156)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [71]):
      return tree
    if self.sym == None:
      return tree
    if rule == 107:
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
    elif rule == 115:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(83, tracer) # asterisk
      tree.add(t)
      return tree
    elif self.sym.getId() in [54, 53, 77, 31, 114, 93, 83, 98, 12, 101, 40, 106, 67, 80, 45, 111]:
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
  def _EXPRESSION_STATEMENT(self, depth=0, tracer=None):
    rule = self.rule(157)
    tree = ParseTree( NonTerminal(157, self.getAtomString(157)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 20:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._EXPRESSION_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(88, tracer) # semi
      tree.add(t)
      return tree
    elif self.sym.getId() in [54, 53, 77, 31, 114, 93, 83, 98, 12, 101, 40, 106, 67, 80, 45, 111]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._EXPRESSION_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(88, tracer) ) # semi
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _TOKEN(self, depth=0, tracer=None):
    rule = self.rule(158)
    tree = ParseTree( NonTerminal(158, self.getAtomString(158)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 2:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(12, tracer) # identifier
      tree.add(t)
      return tree
    elif rule == 7:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PUNCTUATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 60:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(114, tracer) # string_literal
      tree.add(t)
      return tree
    elif rule == 120:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._CONSTANT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 289:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._KEYWORD(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 295:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(7, tracer) # pp_number
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _PARAMETER_DECLARATION(self, depth=0, tracer=None):
    rule = self.rule(159)
    tree = ParseTree( NonTerminal(159, self.getAtomString(159)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 220:
      tree.astTransform = AstTransformNodeCreator('ParameterDeclaration', {'sub': 1, 'declaration_specifiers': 0})
      subtree = self.__GEN1(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN34(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN29(self, depth=0, tracer=None):
    rule = self.rule(160)
    tree = ParseTree( NonTerminal(160, self.getAtomString(160)), tracer )
    tree.list = 'slist'
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 69:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PARAMETER_DECLARATION(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN30(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _SIZEOF_BODY(self, depth=0, tracer=None):
    rule = self.rule(161)
    tree = ParseTree( NonTerminal(161, self.getAtomString(161)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 133:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(12, tracer) # identifier
      tree.add(t)
      return tree
    elif rule == 134:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(45, tracer) # lparen
      tree.add(t)
      subtree = self._TYPE_NAME(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(2, tracer) # rparen
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN40(self, depth=0, tracer=None):
    rule = self.rule(162)
    tree = ParseTree( NonTerminal(162, self.getAtomString(162)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [54, 102, 46, 77, 86, 51, 12, 27, 14, 17, 34, 21, 25, 98, 100, 31, 33, 38, 40, 85, 43, 45, 47, 49, 9, 52, 53, 56, 57, 59, 111, 95, 83, 74, 97, 69, 93, 73, 75, 90, 80, 23, 64, 88, 89, 91, 94, 67, 26, 99, 101, 105, 106, 11, 30, 104, 114]):
      return tree
    if self.sym == None:
      return tree
    if rule == 11:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._ELSE_STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _SELECTION_STATEMENT(self, depth=0, tracer=None):
    rule = self.rule(163)
    tree = ParseTree( NonTerminal(163, self.getAtomString(163)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 38:
      tree.astTransform = AstTransformNodeCreator('If', {'elseif': 6, 'statement': 4, 'condition': 2, 'else': 7})
      t = self.expect(102, tracer) # if
      tree.add(t)
      t = self.expect(45, tracer) # lparen
      tree.add(t)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(2, tracer) # rparen
      tree.add(t)
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(9, tracer) # endif
      tree.add(t)
      subtree = self.__GEN39(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN40(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 116:
      tree.astTransform = AstTransformNodeCreator('Switch', {'expr': 2, 'statment': 4})
      t = self.expect(86, tracer) # switch
      tree.add(t)
      t = self.expect(45, tracer) # lparen
      tree.add(t)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(2, tracer) # rparen
      tree.add(t)
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _TYPE_NAME(self, depth=0, tracer=None):
    rule = self.rule(164)
    tree = ParseTree( NonTerminal(164, self.getAtomString(164)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 151:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(75, tracer) # int
      tree.add(t)
      return tree
    elif rule == 302:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(57, tracer) # char
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _DIRECT_ABSTRACT_DECLARATOR_SUB2(self, depth=0, tracer=None):
    rule = self.rule(165)
    tree = ParseTree( NonTerminal(165, self.getAtomString(165)), tracer )
    tree.list = False
    if self.sym == None:
      return tree
    if rule == 37:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(83, tracer) # asterisk
      tree.add(t)
      return tree
    elif rule == 132:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN10(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _JUMP_STATEMENT(self, depth=0, tracer=None):
    rule = self.rule(166)
    tree = ParseTree( NonTerminal(166, self.getAtomString(166)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 93:
      tree.astTransform = AstTransformNodeCreator('Goto', {'name': 1})
      t = self.expect(69, tracer) # goto
      tree.add(t)
      t = self.expect(12, tracer) # identifier
      tree.add(t)
      t = self.expect(88, tracer) # semi
      tree.add(t)
      return tree
    elif rule == 106:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(89, tracer) # break
      tree.add(t)
      t = self.expect(88, tracer) # semi
      tree.add(t)
      return tree
    elif rule == 272:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(90, tracer) # continue
      tree.add(t)
      return tree
    elif rule == 309:
      tree.astTransform = AstTransformNodeCreator('Return', {'expr': 1})
      t = self.expect(26, tracer) # return
      tree.add(t)
      subtree = self._EXPRESSION_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(88, tracer) # semi
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _ITERATION_STATEMENT(self, depth=0, tracer=None):
    rule = self.rule(167)
    tree = ParseTree( NonTerminal(167, self.getAtomString(167)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 17:
      tree.astTransform = AstTransformNodeCreator('While', {'expr': 2, 'statement': 4})
      t = self.expect(14, tracer) # while
      tree.add(t)
      t = self.expect(45, tracer) # lparen
      tree.add(t)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(2, tracer) # rparen
      tree.add(t)
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 46:
      tree.astTransform = AstTransformNodeCreator('DoWhile', {'expr': 4, 'statement': 1})
      t = self.expect(21, tracer) # do
      tree.add(t)
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(14, tracer) # while
      tree.add(t)
      t = self.expect(45, tracer) # lparen
      tree.add(t)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(2, tracer) # rparen
      tree.add(t)
      t = self.expect(88, tracer) # semi
      tree.add(t)
      return tree
    elif rule == 237:
      tree.astTransform = AstTransformNodeCreator('For', {'init': 2, 'cond': 3, 'incr': 4})
      t = self.expect(100, tracer) # for
      tree.add(t)
      t = self.expect(45, tracer) # lparen
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
      t = self.expect(2, tracer) # rparen
      tree.add(t)
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN27(self, depth=0, tracer=None):
    rule = self.rule(168)
    tree = ParseTree( NonTerminal(168, self.getAtomString(168)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [2, 83, 4, 72, 35, 32, 12, 45, 33]):
      return tree
    if self.sym == None:
      return tree
    if rule == 79:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._TYPE_QUALIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN27(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN37(self, depth=0, tracer=None):
    rule = self.rule(169)
    tree = ParseTree( NonTerminal(169, self.getAtomString(169)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [27]):
      return tree
    if self.sym == None:
      return tree
    if rule == 58:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._BLOCK_ITEM_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [54, 53, 77, 31, 114, 93, 83, 98, 12, 101, 40, 106, 67, 80, 45, 111]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._BLOCK_ITEM_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    return tree
  def __GEN7(self, depth=0, tracer=None):
    rule = self.rule(170)
    tree = ParseTree( NonTerminal(170, self.getAtomString(170)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [88]):
      return tree
    if self.sym == None:
      return tree
    if rule == 81:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._INIT_DECLARATOR_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [45, 4, 12]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._INIT_DECLARATOR_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    return tree
  def _VA_ARGS(self, depth=0, tracer=None):
    rule = self.rule(171)
    tree = ParseTree( NonTerminal(171, self.getAtomString(171)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 243:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(35, tracer) # comma_va_args
      tree.add(t)
      t = self.expect(58, tracer) # elipsis
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _INIT_DECLARATOR_LIST(self, depth=0, tracer=None):
    rule = self.rule(172)
    tree = ParseTree( NonTerminal(172, self.getAtomString(172)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 33:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN11(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [45, 4, 12]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN11(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _ELSE_IF_STATEMENT(self, depth=0, tracer=None):
    rule = self.rule(173)
    tree = ParseTree( NonTerminal(173, self.getAtomString(173)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 158:
      tree.astTransform = AstTransformNodeCreator('ElseIf', {'statement': 4, 'condition': 2})
      t = self.expect(108, tracer) # else_if
      tree.add(t)
      t = self.expect(45, tracer) # lparen
      tree.add(t)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(2, tracer) # rparen
      tree.add(t)
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(9, tracer) # endif
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN31(self, depth=0, tracer=None):
    rule = self.rule(174)
    tree = ParseTree( NonTerminal(174, self.getAtomString(174)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [2]):
      return tree
    if self.sym == None:
      return tree
    if rule == 165:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._VA_ARGS(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN41(self, depth=0, tracer=None):
    rule = self.rule(175)
    tree = ParseTree( NonTerminal(175, self.getAtomString(175)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [54, 102, 18, 77, 86, 51, 12, 27, 14, 17, 46, 34, 21, 25, 98, 100, 31, 33, 38, 40, 85, 43, 45, 47, 49, 9, 52, 53, 56, 57, 59, 111, 95, 83, 74, 97, 69, 93, 73, 75, 90, 80, 23, 64, 88, 89, 91, 94, 67, 26, 99, 101, 105, 106, 11, 30, 104, 114]):
      return tree
    if self.sym == None:
      return tree
    if rule == 85:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._ELSE_IF_STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN41(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _PARAMETER_TYPE_LIST(self, depth=0, tracer=None):
    rule = self.rule(176)
    tree = ParseTree( NonTerminal(176, self.getAtomString(176)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 13:
      tree.astTransform = AstTransformNodeCreator('ParameterTypeList', {'parameter_declarations': 0, 'va_args': 1})
      subtree = self.__GEN29(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN31(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _FOR_COND(self, depth=0, tracer=None):
    rule = self.rule(177)
    tree = ParseTree( NonTerminal(177, self.getAtomString(177)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 96:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(88, tracer) # semi
      tree.add(t)
      subtree = self._EXPRESSION_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _ENUM_SPECIFIER_BODY(self, depth=0, tracer=None):
    rule = self.rule(178)
    tree = ParseTree( NonTerminal(178, self.getAtomString(178)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 310:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(49, tracer) # lbrace
      tree.add(t)
      subtree = self.__GEN25(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self._TRAILING_COMMA_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(27, tracer) # rbrace
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN24(self, depth=0, tracer=None):
    rule = self.rule(179)
    tree = ParseTree( NonTerminal(179, self.getAtomString(179)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [50, 51, 2, 46, 4, 56, 57, 35, 59, 95, 64, 74, 11, 97, 30, 5, 72, 73, 17, 52, 19, 85, 75, 83, 88, 12, 33, 34, 32, 38, 43, 99, 55, 23, 45, 47, 25, 91]):
      return tree
    if self.sym == None:
      return tree
    if rule == 304:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._ENUM_SPECIFIER_BODY(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _PP(self, depth=0, tracer=None):
    rule = self.rule(180)
    tree = ParseTree( NonTerminal(180, self.getAtomString(180)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 99:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(107, tracer) # defined
      tree.add(t)
      return tree
    elif rule == 239:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(1, tracer) # defined_separator
      tree.add(t)
      return tree
    elif rule == 298:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(7, tracer) # pp_number
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _STORAGE_CLASS_SPECIFIER(self, depth=0, tracer=None):
    rule = self.rule(181)
    tree = ParseTree( NonTerminal(181, self.getAtomString(181)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 123:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(25, tracer) # extern
      tree.add(t)
      return tree
    elif rule == 190:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(33, tracer) # static
      tree.add(t)
      return tree
    elif rule == 191:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(43, tracer) # register
      tree.add(t)
      return tree
    elif rule == 192:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(17, tracer) # typedef
      tree.add(t)
      return tree
    elif rule == 211:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(38, tracer) # auto
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _DIRECT_DECLARATOR_PARAMETER_LIST(self, depth=0, tracer=None):
    rule = self.rule(182)
    tree = ParseTree( NonTerminal(182, self.getAtomString(182)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 51:
      tree.astTransform = AstTransformNodeCreator('ParameterList', {'identifiers': 0})
      subtree = self.__GEN32(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 185:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PARAMETER_TYPE_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _MISC(self, depth=0, tracer=None):
    rule = self.rule(183)
    tree = ParseTree( NonTerminal(183, self.getAtomString(183)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 395:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(63, tracer) # universal_character_name
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _TYPE_SPECIFIER(self, depth=0, tracer=None):
    rule = self.rule(184)
    tree = ParseTree( NonTerminal(184, self.getAtomString(184)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 10:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._UNION_SPECIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 47:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(34, tracer) # imaginary
      tree.add(t)
      return tree
    elif rule == 49:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(51, tracer) # void
      tree.add(t)
      return tree
    elif rule == 61:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._TYPEDEF_NAME(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 76:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(46, tracer) # unsigned
      tree.add(t)
      return tree
    elif rule == 94:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STRUCT_SPECIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 143:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(11, tracer) # signed
      tree.add(t)
      return tree
    elif rule == 155:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(30, tracer) # complex
      tree.add(t)
      return tree
    elif rule == 181:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._ENUM_SPECIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 255:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(91, tracer) # float
      tree.add(t)
      return tree
    elif rule == 285:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(97, tracer) # short
      tree.add(t)
      return tree
    elif rule == 303:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(64, tracer) # long
      tree.add(t)
      return tree
    elif rule == 312:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(59, tracer) # bool
      tree.add(t)
      return tree
    elif rule == 345:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(57, tracer) # char
      tree.add(t)
      return tree
    elif rule == 355:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(75, tracer) # int
      tree.add(t)
      return tree
    elif rule == 412:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(99, tracer) # double
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _EXTERNAL_PROTOTYPE(self, depth=0, tracer=None):
    rule = self.rule(185)
    tree = ParseTree( NonTerminal(185, self.getAtomString(185)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 290:
      tree.astTransform = AstTransformNodeCreator('FunctionPrototype', {'declaration_list': 2, 'declarator': 1})
      t = self.expect(50, tracer) # function_prototype_hint
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
  def _IDENTIFIER(self, depth=0, tracer=None):
    rule = self.rule(186)
    tree = ParseTree( NonTerminal(186, self.getAtomString(186)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 91:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(12, tracer) # identifier
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN11(self, depth=0, tracer=None):
    rule = self.rule(187)
    tree = ParseTree( NonTerminal(187, self.getAtomString(187)), tracer )
    tree.list = 'slist'
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 321:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._INIT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN12(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [45, 4, 12]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._INIT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN12(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN12(self, depth=0, tracer=None):
    rule = self.rule(188)
    tree = ParseTree( NonTerminal(188, self.getAtomString(188)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in [88]):
      return tree
    if self.sym == None:
      return tree
    if rule == 324:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(32, tracer) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self._INIT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN12(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN33(self, depth=0, tracer=None):
    rule = self.rule(189)
    tree = ParseTree( NonTerminal(189, self.getAtomString(189)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 111:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(32, tracer) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self._IDENTIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN33(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _POINTER(self, depth=0, tracer=None):
    rule = self.rule(190)
    tree = ParseTree( NonTerminal(190, self.getAtomString(190)), tracer )
    tree.list = False
    if self.sym == None:
      return tree
    if rule == 416:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN36(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN10(self, depth=0, tracer=None):
    rule = self.rule(191)
    tree = ParseTree( NonTerminal(191, self.getAtomString(191)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [2]):
      return tree
    if self.sym == None:
      return tree
    if rule == 273:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PARAMETER_TYPE_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _INITIALIZER_LIST_ITEM(self, depth=0, tracer=None):
    rule = self.rule(192)
    tree = ParseTree( NonTerminal(192, self.getAtomString(192)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 28:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN16(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self._INITIALIZER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 89:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(106, tracer) # integer_constant
      tree.add(t)
      return tree
    elif self.sym.getId() in [54, 53, 77, 31, 114, 93, 83, 98, 12, 101, 40, 106, 67, 80, 45, 111]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN16(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self._INITIALIZER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _FUNCTION_SPECIFIER(self, depth=0, tracer=None):
    rule = self.rule(194)
    tree = ParseTree( NonTerminal(194, self.getAtomString(194)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 172:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(23, tracer) # inline
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _DIRECT_ABSTRACT_DECLARATOR_SUB0(self, depth=0, tracer=None):
    rule = self.rule(195)
    tree = ParseTree( NonTerminal(195, self.getAtomString(195)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 29:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(45, tracer) # lparen
      tree.add(t)
      subtree = self._ABSTRACT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(2, tracer) # rparen
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _DECLARATOR_INITIALIZER(self, depth=0, tracer=None):
    rule = self.rule(196)
    tree = ParseTree( NonTerminal(196, self.getAtomString(196)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 15:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(36, tracer) # assign
      tree.add(t)
      subtree = self._INITIALIZER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _ELSE_IF_STATEMENT_LIST(self, depth=0, tracer=None):
    rule = self.rule(197)
    tree = ParseTree( NonTerminal(197, self.getAtomString(197)), tracer )
    tree.list = False
    if self.sym == None:
      return tree
    if rule == 145:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN41(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN13(self, depth=0, tracer=None):
    rule = self.rule(198)
    tree = ParseTree( NonTerminal(198, self.getAtomString(198)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [32, 88]):
      return tree
    if self.sym == None:
      return tree
    if rule == 337:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DECLARATOR_INITIALIZER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN22(self, depth=0, tracer=None):
    rule = self.rule(199)
    tree = ParseTree( NonTerminal(199, self.getAtomString(199)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in [88]):
      return tree
    if self.sym == None:
      return tree
    if rule == 54:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(32, tracer) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self._STRUCT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN22(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _TRANSLATION_UNIT(self, depth=0, tracer=None):
    rule = self.rule(200)
    tree = ParseTree( NonTerminal(200, self.getAtomString(200)), tracer )
    tree.list = False
    if self.sym == None:
      return tree
    if rule == 311:
      tree.astTransform = AstTransformNodeCreator('TranslationUnit', {'external_declarations': 0})
      subtree = self.__GEN0(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _DIRECT_ABSTRACT_DECLARATOR(self, depth=0, tracer=None):
    rule = self.rule(201)
    tree = ParseTree( NonTerminal(201, self.getAtomString(201)), tracer )
    tree.list = False
    if self.sym == None:
      return tree
    if rule == 62:
      tree.astTransform = AstTransformNodeCreator('DirectAbstractDeclarator', {})
      subtree = self.__GEN8(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN9(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _STATIC_OPT(self, depth=0, tracer=None):
    rule = self.rule(202)
    tree = ParseTree( NonTerminal(202, self.getAtomString(202)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [54, 53, 77, 31, 114, 93, 83, 98, 12, 101, 40, 106, 67, 80, 45, 111]):
      return tree
    if self.sym == None:
      return tree
    if rule == 398:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(33, tracer) # static
      tree.add(t)
      return tree
    return tree
  def _STRUCT_SPECIFIER(self, depth=0, tracer=None):
    rule = self.rule(203)
    tree = ParseTree( NonTerminal(203, self.getAtomString(203)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 110:
      tree.astTransform = AstTransformNodeCreator('Struct', {'definition': 2})
      t = self.expect(52, tracer) # struct
      tree.add(t)
      t = self.expect(55, tracer) # declarator_hint
      tree.add(t)
      subtree = self._STRUCT_OR_UNION_SUB(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN15(self, depth=0, tracer=None):
    rule = self.rule(204)
    tree = ParseTree( NonTerminal(204, self.getAtomString(204)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in [3]):
      return tree
    if self.sym == None:
      return tree
    if rule == 380:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(32, tracer) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self._INITIALIZER_LIST_ITEM(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN15(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN39(self, depth=0, tracer=None):
    rule = self.rule(205)
    tree = ParseTree( NonTerminal(205, self.getAtomString(205)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [54, 102, 18, 77, 86, 51, 12, 27, 14, 17, 46, 34, 21, 25, 98, 100, 31, 33, 38, 40, 85, 43, 45, 47, 49, 9, 52, 53, 56, 57, 59, 111, 95, 83, 74, 97, 69, 93, 73, 75, 90, 80, 23, 64, 88, 89, 91, 94, 67, 26, 99, 101, 105, 106, 11, 30, 104, 114]):
      return tree
    if self.sym == None:
      return tree
    if rule == 57:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._ELSE_IF_STATEMENT_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _FOR_INIT(self, depth=0, tracer=None):
    rule = self.rule(206)
    tree = ParseTree( NonTerminal(206, self.getAtomString(206)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [88]):
      return tree
    if self.sym == None:
      return tree
    if rule == 72:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 163:
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
    elif self.sym.getId() in [54, 53, 77, 31, 114, 93, 83, 98, 12, 101, 40, 106, 67, 80, 45, 111]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    return tree
  def __GEN0(self, depth=0, tracer=None):
    rule = self.rule(207)
    tree = ParseTree( NonTerminal(207, self.getAtomString(207)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [-1]):
      return tree
    if self.sym == None:
      return tree
    if rule == 350:
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
  def _FOR_INCR(self, depth=0, tracer=None):
    rule = self.rule(208)
    tree = ParseTree( NonTerminal(208, self.getAtomString(208)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [2]):
      return tree
    if self.sym == None:
      return tree
    if rule == 117:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(88, tracer) # semi
      tree.add(t)
      subtree = self._EXPRESSION_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _INITIALIZER(self, depth=0, tracer=None):
    rule = self.rule(209)
    tree = ParseTree( NonTerminal(209, self.getAtomString(209)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 364:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 386:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(49, tracer) # lbrace
      tree.add(t)
      subtree = self.__GEN14(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self._TRAILING_COMMA_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(27, tracer) # rbrace
      tree.add(t)
      return tree
    elif self.sym.getId() in [54, 53, 77, 31, 114, 93, 83, 98, 12, 101, 40, 106, 67, 80, 45, 111]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _DECLARATION(self, depth=0, tracer=None):
    rule = self.rule(210)
    tree = ParseTree( NonTerminal(210, self.getAtomString(210)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 144:
      tree.astTransform = AstTransformNodeCreator('Declaration', {'init_declarators': 1, 'declaration_specifiers': 0})
      subtree = self.__GEN1(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN7(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(88, tracer) # semi
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _ENUM_SPECIFIER(self, depth=0, tracer=None):
    rule = self.rule(211)
    tree = ParseTree( NonTerminal(211, self.getAtomString(211)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 242:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(85, tracer) # enum
      tree.add(t)
      subtree = self._ENUM_SPECIFIER_SUB(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _PARAMETER_DECLARATION_SUB(self, depth=0, tracer=None):
    rule = self.rule(212)
    tree = ParseTree( NonTerminal(212, self.getAtomString(212)), tracer )
    tree.list = False
    if self.sym == None:
      return tree
    if rule == 352:
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
    elif self.sym.getId() in [45, 4, 12]:
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
  def _DIRECT_DECLARATOR_MODIFIER(self, depth=0, tracer=None):
    rule = self.rule(213)
    tree = ParseTree( NonTerminal(213, self.getAtomString(213)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 140:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._TYPE_QUALIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 152:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(33, tracer) # static
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _EXPRESSION_OPT(self, depth=0, tracer=None):
    rule = self.rule(215)
    tree = ParseTree( NonTerminal(215, self.getAtomString(215)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [2, 88]):
      return tree
    if self.sym == None:
      return tree
    if rule == 236:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [54, 53, 77, 31, 114, 93, 83, 98, 12, 101, 40, 106, 67, 80, 45, 111]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    return tree
  def _TYPEDEF_NAME(self, depth=0, tracer=None):
    rule = self.rule(216)
    tree = ParseTree( NonTerminal(216, self.getAtomString(216)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 194:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(47, tracer) # typedef_identifier
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _DECLARATION_SPECIFIER(self, depth=0, tracer=None):
    rule = self.rule(217)
    tree = ParseTree( NonTerminal(217, self.getAtomString(217)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 5:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._TYPE_SPECIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 21:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STORAGE_CLASS_SPECIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 173:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._TYPE_QUALIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 293:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._FUNCTION_SPECIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _DECLARATION_LIST(self, depth=0, tracer=None):
    rule = self.rule(218)
    tree = ParseTree( NonTerminal(218, self.getAtomString(218)), tracer )
    tree.list = False
    if self.sym == None:
      return tree
    if rule == 286:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN6(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN14(self, depth=0, tracer=None):
    rule = self.rule(219)
    tree = ParseTree( NonTerminal(219, self.getAtomString(219)), tracer )
    tree.list = 'slist'
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 410:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._INITIALIZER_LIST_ITEM(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN15(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [54, 53, 77, 31, 114, 93, 83, 98, 12, 101, 40, 106, 67, 80, 45, 111]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._INITIALIZER_LIST_ITEM(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN15(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _STRUCT_OR_UNION_SUB(self, depth=0, tracer=None):
    rule = self.rule(220)
    tree = ParseTree( NonTerminal(220, self.getAtomString(220)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 84:
      tree.astTransform = AstTransformNodeCreator('StructOrUnion', {'body': 1, 'name': 0})
      t = self.expect(12, tracer) # identifier
      tree.add(t)
      subtree = self.__GEN18(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 288:
      tree.astTransform = AstTransformNodeCreator('StructOrUnion', {'body': 0})
      subtree = self._STRUCT_OR_UNION_BODY(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _PARAMETER_DECLARATION_SUB_SUB(self, depth=0, tracer=None):
    rule = self.rule(221)
    tree = ParseTree( NonTerminal(221, self.getAtomString(221)), tracer )
    tree.list = False
    if self.sym == None:
      return tree
    if rule == 118:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__DIRECT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 281:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN35(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [45, 4, 12]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__DIRECT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _CONSTANT(self, depth=0, tracer=None):
    rule = self.rule(222)
    tree = ParseTree( NonTerminal(222, self.getAtomString(222)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 70:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(93, tracer) # enumeration_constant
      tree.add(t)
      return tree
    elif rule == 83:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(106, tracer) # integer_constant
      tree.add(t)
      return tree
    elif rule == 278:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(77, tracer) # character_constant
      tree.add(t)
      return tree
    elif rule == 314:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(101, tracer) # hexadecimal_floating_constant
      tree.add(t)
      return tree
    elif rule == 316:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(53, tracer) # floating_constant
      tree.add(t)
      return tree
    elif rule == 335:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(111, tracer) # decimal_floating_constant
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _EXTERNAL_DECLARATION_SUB(self, depth=0, tracer=None):
    rule = self.rule(223)
    tree = ParseTree( NonTerminal(223, self.getAtomString(223)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 209:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._EXTERNAL_FUNCTION(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 418:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN3(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(88, tracer) # semi
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN35(self, depth=0, tracer=None):
    rule = self.rule(224)
    tree = ParseTree( NonTerminal(224, self.getAtomString(224)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [2, 35, 32]):
      return tree
    if self.sym == None:
      return tree
    if rule == 175:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DIRECT_ABSTRACT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _STRUCT_OR_UNION_BODY(self, depth=0, tracer=None):
    rule = self.rule(225)
    tree = ParseTree( NonTerminal(225, self.getAtomString(225)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 135:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(49, tracer) # lbrace
      tree.add(t)
      subtree = self.__GEN19(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(27, tracer) # rbrace
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN18(self, depth=0, tracer=None):
    rule = self.rule(226)
    tree = ParseTree( NonTerminal(226, self.getAtomString(226)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [50, 51, 2, 46, 4, 56, 57, 35, 59, 95, 83, 74, 97, 30, 5, 73, 17, 52, 19, 85, 75, 23, 64, 88, 12, 33, 34, 32, 99, 43, 91, 38, 55, 11, 45, 47, 25, 72]):
      return tree
    if self.sym == None:
      return tree
    if rule == 179:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STRUCT_OR_UNION_BODY(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN32(self, depth=0, tracer=None):
    rule = self.rule(227)
    tree = ParseTree( NonTerminal(227, self.getAtomString(227)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 262:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._IDENTIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN33(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _EXTERNAL_FUNCTION(self, depth=0, tracer=None):
    rule = self.rule(228)
    tree = ParseTree( NonTerminal(228, self.getAtomString(228)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 122:
      tree.astTransform = AstTransformNodeCreator('FunctionDefinition', {'body': 3, 'declaration_list': 2, 'signature': 1})
      t = self.expect(19, tracer) # function_definition_hint
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
  def _TYPE_QUALIFIER_LIST_OPT(self, depth=0, tracer=None):
    rule = self.rule(229)
    tree = ParseTree( NonTerminal(229, self.getAtomString(229)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [2, 83, 4, 72, 32, 45, 12, 35, 33]):
      return tree
    if self.sym == None:
      return tree
    if rule == 78:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN27(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _DESIGNATION(self, depth=0, tracer=None):
    rule = self.rule(230)
    tree = ParseTree( NonTerminal(230, self.getAtomString(230)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 360:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN17(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(36, tracer) # assign
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN19(self, depth=0, tracer=None):
    rule = self.rule(231)
    tree = ParseTree( NonTerminal(231, self.getAtomString(231)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [27]):
      return tree
    if self.sym == None:
      return tree
    if rule == 200:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STRUCT_DECLARATION(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN19(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [45, 4, 12]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STRUCT_DECLARATION(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN19(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    return tree
  def __GEN16(self, depth=0, tracer=None):
    rule = self.rule(232)
    tree = ParseTree( NonTerminal(232, self.getAtomString(232)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [49, 54, 53, 77, 31, 114, 93, 83, 98, 12, 101, 40, 106, 67, 80, 45, 111]):
      return tree
    if self.sym == None:
      return tree
    if rule == 402:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DESIGNATION(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _EXTERNAL_DECLARATION_SUB_SUB(self, depth=0, tracer=None):
    rule = self.rule(233)
    tree = ParseTree( NonTerminal(233, self.getAtomString(233)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 4:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._EXTERNAL_PROTOTYPE(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 104:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._EXTERNAL_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN3(self, depth=0, tracer=None):
    rule = self.rule(234)
    tree = ParseTree( NonTerminal(234, self.getAtomString(234)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in [88]):
      return tree
    if self.sym == None:
      return tree
    if rule == 361:
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
  def _ELSE_STATEMENT(self, depth=0, tracer=None):
    rule = self.rule(235)
    tree = ParseTree( NonTerminal(235, self.getAtomString(235)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 1:
      tree.astTransform = AstTransformNodeCreator('Else', {'statement': 1})
      t = self.expect(18, tracer) # else
      tree.add(t)
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(9, tracer) # endif
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN4(self, depth=0, tracer=None):
    rule = self.rule(236)
    tree = ParseTree( NonTerminal(236, self.getAtomString(236)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in [88]):
      return tree
    if self.sym == None:
      return tree
    if rule == 420:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(32, tracer) # comma
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
  def _STRUCT_DECLARATION(self, depth=0, tracer=None):
    rule = self.rule(237)
    tree = ParseTree( NonTerminal(237, self.getAtomString(237)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 55:
      tree.astTransform = AstTransformNodeCreator('StructOrUnionDeclaration', {'specifier_qualifiers': 0, 'declarators': 1})
      subtree = self.__GEN20(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN21(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(88, tracer) # semi
      tree.add(t)
      return tree
    elif self.sym.getId() in [45, 4, 12]:
      tree.astTransform = AstTransformNodeCreator('StructOrUnionDeclaration', {'specifier_qualifiers': 0, 'declarators': 1})
      subtree = self.__GEN20(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN21(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(88, tracer) ) # semi
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _EXTERNAL_DECLARATION(self, depth=0, tracer=None):
    rule = self.rule(238)
    tree = ParseTree( NonTerminal(238, self.getAtomString(238)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 323:
      tree.astTransform = AstTransformNodeCreator('ExternalDeclaration', {'declarations': 2, 'declaration_specifiers': 1})
      t = self.expect(0, tracer) # external_declaration_hint
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
  def _DESIGNATOR(self, depth=0, tracer=None):
    rule = self.rule(239)
    tree = ParseTree( NonTerminal(239, self.getAtomString(239)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 26:
      tree.astTransform = AstTransformNodeCreator('MemberAccess', {'name': 1})
      t = self.expect(10, tracer) # dot
      tree.add(t)
      t = self.expect(12, tracer) # identifier
      tree.add(t)
      return tree
    elif rule == 254:
      tree.astTransform = AstTransformNodeCreator('ArrayAccess', {'index': 1})
      t = self.expect(72, tracer) # lsquare
      tree.add(t)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(71, tracer) # rsquare
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN17(self, depth=0, tracer=None):
    rule = self.rule(240)
    tree = ParseTree( NonTerminal(240, self.getAtomString(240)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [36]):
      return tree
    if self.sym == None:
      return tree
    if rule == 325:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DESIGNATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN17(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN34(self, depth=0, tracer=None):
    rule = self.rule(241)
    tree = ParseTree( NonTerminal(241, self.getAtomString(241)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [2, 32, 35]):
      return tree
    if self.sym == None:
      return tree
    if rule == 147:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PARAMETER_DECLARATION_SUB(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [45, 4, 12]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PARAMETER_DECLARATION_SUB(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    return tree
  def __GEN1(self, depth=0, tracer=None):
    rule = self.rule(242)
    tree = ParseTree( NonTerminal(242, self.getAtomString(242)), tracer )
    tree.list = 'mlist'
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 377:
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
  def __GEN30(self, depth=0, tracer=None):
    rule = self.rule(243)
    tree = ParseTree( NonTerminal(243, self.getAtomString(243)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in [35, 2]):
      return tree
    if self.sym == None:
      return tree
    if rule == 32:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(32, tracer) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self._PARAMETER_DECLARATION(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN30(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _POINTER_SUB(self, depth=0, tracer=None):
    rule = self.rule(244)
    tree = ParseTree( NonTerminal(244, self.getAtomString(244)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 170:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(83, tracer) # asterisk
      tree.add(t)
      subtree = self._TYPE_QUALIFIER_LIST_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _STATEMENT(self, depth=0, tracer=None):
    rule = self.rule(245)
    tree = ParseTree( NonTerminal(245, self.getAtomString(245)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 19:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._LABELED_STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 90:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._SELECTION_STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 112:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._COMPOUND_STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 121:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._JUMP_STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 197:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._EXPRESSION_STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 219:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._ITERATION_STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [54, 53, 77, 31, 114, 93, 83, 98, 12, 101, 40, 106, 67, 80, 45, 111]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._EXPRESSION_STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  infixBp0 = {
    6: 1000,
    8: 9000,
    10: 15000,
    13: 1000,
    16: 7000,
    20: 12000,
    22: 3000,
    28: 10000,
    31: 15000,
    32: 16000,
    36: 1000,
    37: 10000,
    40: 5000,
    44: 12000,
    45: 15000,
    49: 14000,
    61: 6000,
    62: 2000,
    65: 11000,
    66: 15000,
    68: 9000,
    70: 1000,
    72: 15000,
    76: 11000,
    78: 1000,
    79: 1000,
    80: 15000,
    82: 1000,
    83: 12000,
    84: 1000,
    87: 1000,
    92: 8000,
    96: 1000,
    103: 4000,
    109: 9000,
    110: 8000,
    112: 9000,
    113: 1000,
  }
  prefixBp0 = {
    31: 13000,
    40: 13000,
    42: 13000,
    76: 13000,
    80: 13000,
    81: 13000,
    83: 13000,
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
    tree = ParseTree( NonTerminal(214, '_expr') )
    if not self.sym:
      return tree
    elif self.sym.getId() in [45]:
      tree.astTransform = AstTransformSubstitution(2)
      tree.nudMorphemeCount = 3
      tree.add( self.expect(45, tracer) )
      tree.add( self.__EXPR() )
      tree.add( self.expect(2, tracer) )
    elif self.sym.getId() in [12]:
      tree.astTransform = AstTransformNodeCreator('ArrayIndex', {'params': 2, 'name': 0})
      tree.nudMorphemeCount = 1
      return self.expect( 12, tracer )
    elif self.sym.getId() in [12]:
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      tree.nudMorphemeCount = 1
      return self.expect( 12, tracer )
    elif self.sym.getId() in [31]:
      tree.astTransform = AstTransformNodeCreator('PreIncr', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(31, tracer) )
      tree.add( self.__EXPR( self.prefixBp0[31] ) )
      tree.isPrefix = True
    elif self.sym.getId() in [12]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      return self.expect( 12, tracer )
    elif self.sym.getId() in [67]:
      tree.astTransform = AstTransformNodeCreator('SizeOf', {'var': 1})
      tree.nudMorphemeCount = 1
      return self.expect( 67, tracer )
    elif self.sym.getId() in [101, 106, 53, 93, 77, 111]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      tree.add( self._CONSTANT() )
    elif self.sym.getId() in [114]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      return self.expect( 114, tracer )
    elif self.sym.getId() in [98]:
      tree.astTransform = AstTransformNodeCreator('TypeInitializion', {'type': 1, 'initializer': 4})
      tree.nudMorphemeCount = 3
      tree.add( self.expect(98, tracer) )
      tree.add( self._TYPE_NAME() )
      tree.add( self.expect(2, tracer) )
    elif self.sym.getId() in [83]:
      tree.astTransform = AstTransformNodeCreator('Dereference', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(83, tracer) )
      tree.add( self.__EXPR( self.prefixBp0[83] ) )
      tree.isPrefix = True
    elif self.sym.getId() in [40]:
      tree.astTransform = AstTransformNodeCreator('AddressOf', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(40, tracer) )
      tree.add( self.__EXPR( self.prefixBp0[40] ) )
      tree.isPrefix = True
    elif self.sym.getId() in [80]:
      tree.astTransform = AstTransformNodeCreator('PreDecr', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(80, tracer) )
      tree.add( self.__EXPR( self.prefixBp0[80] ) )
      tree.isPrefix = True
    return tree
  def led0(self, left, tracer):
    tree = ParseTree( NonTerminal(214, '_expr') )
    if  self.sym.getId() == 83: # 'asterisk'
      tree.astTransform = AstTransformNodeCreator('Mul', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(83, tracer) )
      tree.add( self.__EXPR( self.infixBp0[83] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 78: # 'rshifteq'
      tree.astTransform = AstTransformNodeCreator('RightShiftAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(78, tracer) )
      tree.add( self.__EXPR( self.infixBp0[78] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 37: # 'rshift'
      tree.astTransform = AstTransformNodeCreator('RightShift', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(37, tracer) )
      tree.add( self.__EXPR( self.infixBp0[37] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 36: # 'assign'
      tree.astTransform = AstTransformNodeCreator('Assign', {'var': 0, 'value': 2})
      if left:
        tree.add(left)
      tree.add( self.expect(36, tracer) )
      tree.add( self.__EXPR( self.infixBp0[36] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 13: # 'muleq'
      tree.astTransform = AstTransformNodeCreator('MultiplyAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(13, tracer) )
      tree.add( self.__EXPR( self.infixBp0[13] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 31: # 'incr'
      tree.astTransform = AstTransformNodeCreator('PostIncr', {'var': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      return self.expect( 31, tracer )
    elif  self.sym.getId() == 6: # 'addeq'
      tree.astTransform = AstTransformNodeCreator('AddAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(6, tracer) )
      tree.add( self.__EXPR( self.infixBp0[6] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 62: # 'questionmark'
      tree.astTransform = AstTransformNodeCreator('TernaryOperator', {'true': 2, 'false': 4, 'cond': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(62, tracer) )
      tree.add( self.__EXPR() )
      tree.add( self.expect(5, tracer) )
      tree.add( self.__EXPR() )
    elif  self.sym.getId() == 76: # 'sub'
      tree.astTransform = AstTransformNodeCreator('Sub', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(76, tracer) )
      tree.add( self.__EXPR( self.infixBp0[76] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 65: # 'add'
      tree.astTransform = AstTransformNodeCreator('Add', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(65, tracer) )
      tree.add( self.__EXPR( self.infixBp0[65] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 61: # 'bitxor'
      tree.astTransform = AstTransformNodeCreator('BitXOR', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(61, tracer) )
      tree.add( self.__EXPR( self.infixBp0[61] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 10: # 'dot'
      tree.astTransform = AstTransformNodeCreator('MemberSelect', {'member': 2, 'object': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(10, tracer) )
      tree.add( self.__EXPR() )
    elif  self.sym.getId() == 87: # 'bitandeq'
      tree.astTransform = AstTransformNodeCreator('ANDAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(87, tracer) )
      tree.add( self.__EXPR( self.infixBp0[87] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 66: # 'arrow'
      tree.astTransform = AstTransformNodeCreator('DerefMemberSelect', {'member': 2, 'object': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(66, tracer) )
      tree.add( self.__EXPR() )
    elif  self.sym.getId() == 32: # 'comma'
      tree.astTransform = AstTransformNodeCreator('Comma', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(32, tracer) )
      tree.add( self.__EXPR( self.infixBp0[32] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 113: # 'subeq'
      tree.astTransform = AstTransformNodeCreator('SubtractAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(113, tracer) )
      tree.add( self.__EXPR( self.infixBp0[113] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 40: # 'bitand'
      tree.astTransform = AstTransformNodeCreator('BitAND', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(40, tracer) )
      tree.add( self.__EXPR( self.infixBp0[40] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 112: # 'lteq'
      tree.astTransform = AstTransformNodeCreator('LessThanEq', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(112, tracer) )
      tree.add( self.__EXPR( self.infixBp0[112] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 8: # 'gteq'
      tree.astTransform = AstTransformNodeCreator('GreaterThanEq', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(8, tracer) )
      tree.add( self.__EXPR( self.infixBp0[8] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 79: # 'bitxoreq'
      tree.astTransform = AstTransformNodeCreator('XORAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(79, tracer) )
      tree.add( self.__EXPR( self.infixBp0[79] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 84: # 'modeq'
      tree.astTransform = AstTransformNodeCreator('ModAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(84, tracer) )
      tree.add( self.__EXPR( self.infixBp0[84] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 60: # 'sizeof_separator'
      tree.astTransform = AstTransformNodeCreator('SizeOf', {'var': 1})
      if left:
        tree.add(left)
      tree.add( self.expect(60, tracer) )
      tree.add( self._SIZEOF_BODY() )
    elif  self.sym.getId() == 80: # 'decr'
      tree.astTransform = AstTransformNodeCreator('PostDecr', {'var': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      return self.expect( 80, tracer )
    elif  self.sym.getId() == 110: # 'eq'
      tree.astTransform = AstTransformNodeCreator('Equals', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(110, tracer) )
      tree.add( self.__EXPR( self.infixBp0[110] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 44: # 'mod'
      tree.astTransform = AstTransformNodeCreator('Mod', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(44, tracer) )
      tree.add( self.__EXPR( self.infixBp0[44] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 16: # 'bitor'
      tree.astTransform = AstTransformNodeCreator('BitOR', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(16, tracer) )
      tree.add( self.__EXPR( self.infixBp0[16] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 45: # 'lparen'
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(45, tracer) )
      tree.add( self.__GEN42() )
      tree.add( self.expect(2, tracer) )
    elif  self.sym.getId() == 70: # 'bitoreq'
      tree.astTransform = AstTransformNodeCreator('ORAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(70, tracer) )
      tree.add( self.__EXPR( self.infixBp0[70] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 28: # 'lshift'
      tree.astTransform = AstTransformNodeCreator('LeftShift', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(28, tracer) )
      tree.add( self.__EXPR( self.infixBp0[28] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 20: # 'div'
      tree.astTransform = AstTransformNodeCreator('Div', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(20, tracer) )
      tree.add( self.__EXPR( self.infixBp0[20] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 96: # 'lshifteq'
      tree.astTransform = AstTransformNodeCreator('LeftShiftAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(96, tracer) )
      tree.add( self.__EXPR( self.infixBp0[96] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 82: # 'diveq'
      tree.astTransform = AstTransformNodeCreator('DivideAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(82, tracer) )
      tree.add( self.__EXPR( self.infixBp0[82] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 68: # 'gt'
      tree.astTransform = AstTransformNodeCreator('GreaterThan', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(68, tracer) )
      tree.add( self.__EXPR( self.infixBp0[68] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 49: # 'lbrace'
      tree.astTransform = AstTransformNodeCreator('TypeInitializion', {'type': 1, 'initializer': 4})
      if left:
        tree.add(left)
      tree.add( self.expect(49, tracer) )
      tree.add( self.__GEN14() )
      tree.add( self._TRAILING_COMMA_OPT() )
      tree.add( self.expect(27, tracer) )
    elif  self.sym.getId() == 72: # 'lsquare'
      tree.astTransform = AstTransformNodeCreator('ArrayIndex', {'params': 2, 'name': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(72, tracer) )
      tree.add( self.__GEN42() )
      tree.add( self.expect(71, tracer) )
    elif  self.sym.getId() == 109: # 'lt'
      tree.astTransform = AstTransformNodeCreator('LessThan', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(109, tracer) )
      tree.add( self.__EXPR( self.infixBp0[109] ) )
      tree.isInfix = True
    return tree
  infixBp1 = {
    6: 1000,
    8: 9000,
    10: 15000,
    13: 1000,
    16: 7000,
    20: 12000,
    22: 3000,
    28: 10000,
    31: 15000,
    36: 1000,
    37: 10000,
    40: 5000,
    44: 12000,
    45: 15000,
    49: 14000,
    61: 6000,
    62: 2000,
    65: 11000,
    66: 15000,
    68: 9000,
    70: 1000,
    72: 15000,
    76: 11000,
    78: 1000,
    79: 1000,
    80: 15000,
    82: 1000,
    83: 12000,
    84: 1000,
    87: 1000,
    92: 8000,
    96: 1000,
    103: 4000,
    109: 9000,
    110: 8000,
    112: 9000,
    113: 1000,
  }
  prefixBp1 = {
    31: 13000,
    40: 13000,
    42: 13000,
    76: 13000,
    80: 13000,
    81: 13000,
    83: 13000,
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
    tree = ParseTree( NonTerminal(193, '_expr_sans_comma') )
    if not self.sym:
      return tree
    if self.sym.getId() in [12]:
      tree.astTransform = AstTransformNodeCreator('ArrayIndex', {'params': 2, 'name': 0})
      tree.nudMorphemeCount = 1
      return self.expect( 12, tracer )
    elif self.sym.getId() in [83]:
      tree.astTransform = AstTransformNodeCreator('Dereference', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(83, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.prefixBp1[83] ) )
      tree.isPrefix = True
    elif self.sym.getId() in [101, 106, 53, 93, 77, 111]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      tree.add( self._CONSTANT() )
    elif self.sym.getId() in [12]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      return self.expect( 12, tracer )
    elif self.sym.getId() in [45]:
      tree.astTransform = AstTransformSubstitution(2)
      tree.nudMorphemeCount = 3
      tree.add( self.expect(45, tracer) )
      tree.add( self.__EXPR_SANS_COMMA() )
      tree.add( self.expect(2, tracer) )
    elif self.sym.getId() in [31]:
      tree.astTransform = AstTransformNodeCreator('PreIncr', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(31, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.prefixBp1[31] ) )
      tree.isPrefix = True
    elif self.sym.getId() in [12]:
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      tree.nudMorphemeCount = 1
      return self.expect( 12, tracer )
    elif self.sym.getId() in [67]:
      tree.astTransform = AstTransformNodeCreator('SizeOf', {'var': 1})
      tree.nudMorphemeCount = 1
      return self.expect( 67, tracer )
    elif self.sym.getId() in [80]:
      tree.astTransform = AstTransformNodeCreator('PreDecr', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(80, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.prefixBp1[80] ) )
      tree.isPrefix = True
    elif self.sym.getId() in [40]:
      tree.astTransform = AstTransformNodeCreator('AddressOf', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(40, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.prefixBp1[40] ) )
      tree.isPrefix = True
    elif self.sym.getId() in [114]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      return self.expect( 114, tracer )
    elif self.sym.getId() in [98]:
      tree.astTransform = AstTransformNodeCreator('TypeInitializion', {'type': 1, 'initializer': 4})
      tree.nudMorphemeCount = 3
      tree.add( self.expect(98, tracer) )
      tree.add( self._TYPE_NAME() )
      tree.add( self.expect(2, tracer) )
    return tree
  def led1(self, left, tracer):
    tree = ParseTree( NonTerminal(193, '_expr_sans_comma') )
    if  self.sym.getId() == 8: # 'gteq'
      tree.astTransform = AstTransformNodeCreator('GreaterThanEq', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(8, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[8] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 65: # 'add'
      tree.astTransform = AstTransformNodeCreator('Add', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(65, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[65] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 6: # 'addeq'
      tree.astTransform = AstTransformNodeCreator('AddAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(6, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[6] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 84: # 'modeq'
      tree.astTransform = AstTransformNodeCreator('ModAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(84, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[84] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 10: # 'dot'
      tree.astTransform = AstTransformNodeCreator('MemberSelect', {'member': 2, 'object': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(10, tracer) )
      tree.add( self.__EXPR_SANS_COMMA() )
    elif  self.sym.getId() == 28: # 'lshift'
      tree.astTransform = AstTransformNodeCreator('LeftShift', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(28, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[28] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 83: # 'asterisk'
      tree.astTransform = AstTransformNodeCreator('Mul', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(83, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[83] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 78: # 'rshifteq'
      tree.astTransform = AstTransformNodeCreator('RightShiftAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(78, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[78] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 13: # 'muleq'
      tree.astTransform = AstTransformNodeCreator('MultiplyAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(13, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[13] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 76: # 'sub'
      tree.astTransform = AstTransformNodeCreator('Sub', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(76, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[76] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 87: # 'bitandeq'
      tree.astTransform = AstTransformNodeCreator('ANDAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(87, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[87] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 113: # 'subeq'
      tree.astTransform = AstTransformNodeCreator('SubtractAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(113, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[113] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 60: # 'sizeof_separator'
      tree.astTransform = AstTransformNodeCreator('SizeOf', {'var': 1})
      if left:
        tree.add(left)
      tree.add( self.expect(60, tracer) )
      tree.add( self._SIZEOF_BODY() )
    elif  self.sym.getId() == 37: # 'rshift'
      tree.astTransform = AstTransformNodeCreator('RightShift', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(37, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[37] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 20: # 'div'
      tree.astTransform = AstTransformNodeCreator('Div', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(20, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[20] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 109: # 'lt'
      tree.astTransform = AstTransformNodeCreator('LessThan', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(109, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[109] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 62: # 'questionmark'
      tree.astTransform = AstTransformNodeCreator('TernaryOperator', {'true': 2, 'false': 4, 'cond': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(62, tracer) )
      tree.add( self.__EXPR_SANS_COMMA() )
      tree.add( self.expect(5, tracer) )
      tree.add( self.__EXPR_SANS_COMMA() )
    elif  self.sym.getId() == 61: # 'bitxor'
      tree.astTransform = AstTransformNodeCreator('BitXOR', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(61, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[61] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 80: # 'decr'
      tree.astTransform = AstTransformNodeCreator('PostDecr', {'var': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      return self.expect( 80, tracer )
    elif  self.sym.getId() == 40: # 'bitand'
      tree.astTransform = AstTransformNodeCreator('BitAND', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(40, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[40] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 70: # 'bitoreq'
      tree.astTransform = AstTransformNodeCreator('ORAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(70, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[70] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 44: # 'mod'
      tree.astTransform = AstTransformNodeCreator('Mod', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(44, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[44] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 68: # 'gt'
      tree.astTransform = AstTransformNodeCreator('GreaterThan', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(68, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[68] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 82: # 'diveq'
      tree.astTransform = AstTransformNodeCreator('DivideAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(82, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[82] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 79: # 'bitxoreq'
      tree.astTransform = AstTransformNodeCreator('XORAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(79, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[79] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 31: # 'incr'
      tree.astTransform = AstTransformNodeCreator('PostIncr', {'var': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      return self.expect( 31, tracer )
    elif  self.sym.getId() == 16: # 'bitor'
      tree.astTransform = AstTransformNodeCreator('BitOR', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(16, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[16] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 110: # 'eq'
      tree.astTransform = AstTransformNodeCreator('Equals', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(110, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[110] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 96: # 'lshifteq'
      tree.astTransform = AstTransformNodeCreator('LeftShiftAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(96, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[96] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 112: # 'lteq'
      tree.astTransform = AstTransformNodeCreator('LessThanEq', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(112, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[112] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 45: # 'lparen'
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(45, tracer) )
      tree.add( self.__GEN42() )
      tree.add( self.expect(2, tracer) )
    elif  self.sym.getId() == 49: # 'lbrace'
      tree.astTransform = AstTransformNodeCreator('TypeInitializion', {'type': 1, 'initializer': 4})
      if left:
        tree.add(left)
      tree.add( self.expect(49, tracer) )
      tree.add( self.__GEN14() )
      tree.add( self._TRAILING_COMMA_OPT() )
      tree.add( self.expect(27, tracer) )
    elif  self.sym.getId() == 66: # 'arrow'
      tree.astTransform = AstTransformNodeCreator('DerefMemberSelect', {'member': 2, 'object': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(66, tracer) )
      tree.add( self.__EXPR_SANS_COMMA() )
    elif  self.sym.getId() == 36: # 'assign'
      tree.astTransform = AstTransformNodeCreator('Assign', {'var': 0, 'value': 2})
      if left:
        tree.add(left)
      tree.add( self.expect(36, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[36] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 72: # 'lsquare'
      tree.astTransform = AstTransformNodeCreator('ArrayIndex', {'params': 2, 'name': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(72, tracer) )
      tree.add( self.__GEN42() )
      tree.add( self.expect(71, tracer) )
    return tree
  infixBp2 = {
    45: 1000,
    72: 1000,
  }
  prefixBp2 = {
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
    tree = ParseTree( NonTerminal(117, '_direct_declarator') )
    if not self.sym:
      return tree
    if self.sym.getId() in [12]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      return self.expect( 12, tracer )
    elif self.sym.getId() in [45]:
      tree.astTransform = AstTransformSubstitution(1)
      tree.nudMorphemeCount = 3
      tree.add( self.expect(45, tracer) )
      tree.add( self._DECLARATOR() )
      tree.add( self.expect(2, tracer) )
    return tree
  def led2(self, left, tracer):
    tree = ParseTree( NonTerminal(117, '_direct_declarator') )
    if  self.sym.getId() == 45: # 'lparen'
      tree.astTransform = AstTransformNodeCreator('FunctionSignature', {'params': 2, 'declarator': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(45, tracer) )
      tree.add( self._DIRECT_DECLARATOR_PARAMETER_LIST() )
      tree.add( self.expect(2, tracer) )
    elif  self.sym.getId() == 72: # 'lsquare'
      tree.astTransform = AstTransformNodeCreator('Array', {'name': 0, 'size': 2})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(72, tracer) )
      tree.add( self._DIRECT_DECLARATOR_EXPR() )
      tree.add( self.expect(71, tracer) )
    return tree
