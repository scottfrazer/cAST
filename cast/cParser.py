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
  TERMINAL_MOD = 0
  TERMINAL__DIRECT_ABSTRACT_DECLARATOR = 1
  TERMINAL_VOLATILE = 2
  TERMINAL_RESTRICT = 3
  TERMINAL_INT = 4
  TERMINAL__EXPR_SANS_COMMA = 5
  TERMINAL_IF = 6
  TERMINAL_LPAREN = 7
  TERMINAL_DECIMAL_FLOATING_CONSTANT = 8
  TERMINAL_RPAREN = 9
  TERMINAL_STRING_LITERAL = 10
  TERMINAL_ENDIF = 11
  TERMINAL_GT = 12
  TERMINAL_COLON = 13
  TERMINAL_FLOATING_CONSTANT = 14
  TERMINAL_CONST = 15
  TERMINAL_IDENTIFIER = 16
  TERMINAL_FLOAT = 17
  TERMINAL_UNSIGNED = 18
  TERMINAL_ELIPSIS = 19
  TERMINAL_LT = 20
  TERMINAL_RSHIFTEQ = 21
  TERMINAL_SIZEOF_SEPARATOR = 22
  TERMINAL_DO = 23
  TERMINAL_DOUBLE = 24
  TERMINAL_INCR = 25
  TERMINAL_FUNCTION_DEFINITION_HINT = 26
  TERMINAL_GOTO = 27
  TERMINAL_DIV = 28
  TERMINAL_BITOREQ = 29
  TERMINAL_RBRACE = 30
  TERMINAL_SIGNED = 31
  TERMINAL_BITAND = 32
  TERMINAL_OR = 33
  TERMINAL_CONTINUE = 34
  TERMINAL_ENUMERATION_CONSTANT = 35
  TERMINAL_BITXOREQ = 36
  TERMINAL_LSQUARE = 37
  TERMINAL_POUNDPOUND = 38
  TERMINAL_RSQUARE = 39
  TERMINAL_NOT = 40
  TERMINAL_BITANDEQ = 41
  TERMINAL_UNION = 42
  TERMINAL_GTEQ = 43
  TERMINAL_EQ = 44
  TERMINAL_BITXOR = 45
  TERMINAL_DOT = 46
  TERMINAL_BREAK = 47
  TERMINAL_LSHIFTEQ = 48
  TERMINAL_RETURN = 49
  TERMINAL_SIZEOF = 50
  TERMINAL_COMPLEX = 51
  TERMINAL_BITNOT = 52
  TERMINAL_LPAREN_CAST = 53
  TERMINAL_ADD = 54
  TERMINAL_DEFINED = 55
  TERMINAL_TYPEDEF = 56
  TERMINAL__EXPR = 57
  TERMINAL_STRUCT = 58
  TERMINAL_ELSE_IF = 59
  TERMINAL_NEQ = 60
  TERMINAL_LTEQ = 61
  TERMINAL_QUESTIONMARK = 62
  TERMINAL_INTEGER_CONSTANT = 63
  TERMINAL_EXTERN = 64
  TERMINAL_ELSE = 65
  TERMINAL_HEXADECIMAL_FLOATING_CONSTANT = 66
  TERMINAL_TRAILING_COMMA = 67
  TERMINAL_FOR = 68
  TERMINAL_POUND = 69
  TERMINAL_PP_NUMBER = 70
  TERMINAL_EXCLAMATION_POINT = 71
  TERMINAL_BOOL = 72
  TERMINAL_ADDEQ = 73
  TERMINAL_LBRACE = 74
  TERMINAL_RSHIFT = 75
  TERMINAL_SWITCH = 76
  TERMINAL_LONG = 77
  TERMINAL_IMAGINARY = 78
  TERMINAL_COMMA_VA_ARGS = 79
  TERMINAL_MULEQ = 80
  TERMINAL_DEFINED_SEPARATOR = 81
  TERMINAL_MODEQ = 82
  TERMINAL_ASTERISK = 83
  TERMINAL_WHILE = 84
  TERMINAL_DECLARATOR_HINT = 85
  TERMINAL_DEFAULT = 86
  TERMINAL_ENUM = 87
  TERMINAL_SUB = 88
  TERMINAL_FUNCTION_PROTOTYPE_HINT = 89
  TERMINAL_AMPERSAND = 90
  TERMINAL_REGISTER = 91
  TERMINAL_INLINE = 92
  TERMINAL_SUBEQ = 93
  TERMINAL_AUTO = 94
  TERMINAL_SEMI = 95
  TERMINAL_AND = 96
  TERMINAL_DECR = 97
  TERMINAL_VOID = 98
  TERMINAL_ARROW = 99
  TERMINAL_BITOR = 100
  TERMINAL_ASSIGN = 101
  TERMINAL_COMMA = 102
  TERMINAL_CASE = 103
  TERMINAL_TYPEDEF_IDENTIFIER = 104
  TERMINAL_CHAR = 105
  TERMINAL_DIVEQ = 106
  TERMINAL__DIRECT_DECLARATOR = 107
  TERMINAL_TILDE = 108
  TERMINAL_UNIVERSAL_CHARACTER_NAME = 109
  TERMINAL_CHARACTER_CONSTANT = 110
  TERMINAL_STATIC = 111
  TERMINAL_EXTERNAL_DECLARATION_HINT = 112
  TERMINAL_SHORT = 113
  TERMINAL_LSHIFT = 114
  TERMINAL_LABEL_HINT = 115
  terminal_str = {
    0: 'mod',
    1: '_direct_abstract_declarator',
    2: 'volatile',
    3: 'restrict',
    4: 'int',
    5: '_expr_sans_comma',
    6: 'if',
    7: 'lparen',
    8: 'decimal_floating_constant',
    9: 'rparen',
    10: 'string_literal',
    11: 'endif',
    12: 'gt',
    13: 'colon',
    14: 'floating_constant',
    15: 'const',
    16: 'identifier',
    17: 'float',
    18: 'unsigned',
    19: 'elipsis',
    20: 'lt',
    21: 'rshifteq',
    22: 'sizeof_separator',
    23: 'do',
    24: 'double',
    25: 'incr',
    26: 'function_definition_hint',
    27: 'goto',
    28: 'div',
    29: 'bitoreq',
    30: 'rbrace',
    31: 'signed',
    32: 'bitand',
    33: 'or',
    34: 'continue',
    35: 'enumeration_constant',
    36: 'bitxoreq',
    37: 'lsquare',
    38: 'poundpound',
    39: 'rsquare',
    40: 'not',
    41: 'bitandeq',
    42: 'union',
    43: 'gteq',
    44: 'eq',
    45: 'bitxor',
    46: 'dot',
    47: 'break',
    48: 'lshifteq',
    49: 'return',
    50: 'sizeof',
    51: 'complex',
    52: 'bitnot',
    53: 'lparen_cast',
    54: 'add',
    55: 'defined',
    56: 'typedef',
    57: '_expr',
    58: 'struct',
    59: 'else_if',
    60: 'neq',
    61: 'lteq',
    62: 'questionmark',
    63: 'integer_constant',
    64: 'extern',
    65: 'else',
    66: 'hexadecimal_floating_constant',
    67: 'trailing_comma',
    68: 'for',
    69: 'pound',
    70: 'pp_number',
    71: 'exclamation_point',
    72: 'bool',
    73: 'addeq',
    74: 'lbrace',
    75: 'rshift',
    76: 'switch',
    77: 'long',
    78: 'imaginary',
    79: 'comma_va_args',
    80: 'muleq',
    81: 'defined_separator',
    82: 'modeq',
    83: 'asterisk',
    84: 'while',
    85: 'declarator_hint',
    86: 'default',
    87: 'enum',
    88: 'sub',
    89: 'function_prototype_hint',
    90: 'ampersand',
    91: 'register',
    92: 'inline',
    93: 'subeq',
    94: 'auto',
    95: 'semi',
    96: 'and',
    97: 'decr',
    98: 'void',
    99: 'arrow',
    100: 'bitor',
    101: 'assign',
    102: 'comma',
    103: 'case',
    104: 'typedef_identifier',
    105: 'char',
    106: 'diveq',
    107: '_direct_declarator',
    108: 'tilde',
    109: 'universal_character_name',
    110: 'character_constant',
    111: 'static',
    112: 'external_declaration_hint',
    113: 'short',
    114: 'lshift',
    115: 'label_hint',
  }
  nonterminal_str = {
    116: 'storage_class_specifier',
    117: 'sizeof_body',
    118: '_gen16',
    119: 'type_specifier',
    120: 'else_if_statement_list',
    121: 'initializer_list_item',
    122: '_gen37',
    123: 'type_qualifier_list_opt',
    124: 'type_qualifier',
    125: 'token',
    126: 'typedef_name',
    127: 'function_specifier',
    128: 'else_statement',
    129: 'parameter_type_list',
    130: 'translation_unit',
    131: '_gen9',
    132: 'struct_or_union_body',
    133: '_gen10',
    134: 'external_declaration',
    135: 'pointer_opt',
    136: 'enumerator',
    137: '_direct_declarator',
    138: 'specifier_qualifier',
    139: 'pointer_sub',
    140: '_gen18',
    141: '_expr_sans_comma',
    142: 'direct_declarator_modifier_list_opt',
    143: 'direct_declarator_size',
    144: '_gen31',
    145: 'declarator_initializer',
    146: 'struct_declarator',
    147: '_gen19',
    148: 'block_item',
    149: '_gen20',
    150: '_direct_abstract_declarator',
    151: 'declaration_specifier',
    152: 'else_if_statement',
    153: '_gen1',
    154: '_gen2',
    155: '_gen25',
    156: 'struct_specifier',
    157: 'declaration_list',
    158: '_gen23',
    159: 'initializer',
    160: 'labeled_statement',
    161: 'union_specifier',
    162: 'type_name',
    163: 'external_declaration_sub',
    164: 'parameter_declaration_sub',
    165: 'enum_specifier',
    166: '_gen3',
    167: 'external_function',
    168: 'struct_declarator_body',
    169: '_gen0',
    170: 'misc',
    171: '_gen12',
    172: '_gen13',
    173: 'constant',
    174: '_gen21',
    175: 'for_init',
    176: 'for_cond',
    177: '_gen4',
    178: '_gen8',
    179: 'keyword',
    180: 'trailing_comma_opt',
    181: '_gen41',
    182: 'punctuator',
    183: 'parameter_declaration',
    184: '_gen27',
    185: '_gen11',
    186: '_gen28',
    187: 'designation',
    188: 'identifier',
    189: '_gen14',
    190: '_gen33',
    191: 'enum_specifier_sub',
    192: '_gen40',
    193: 'external_declarator',
    194: 'enum_specifier_body',
    195: 'va_args',
    196: '_gen29',
    197: 'external_declaration_sub_sub',
    198: 'external_prototype',
    199: '_gen22',
    200: '_gen15',
    201: 'selection_statement',
    202: 'designator',
    203: 'declarator',
    204: 'init_declarator_list',
    205: 'pointer',
    206: '_gen5',
    207: 'jump_statement',
    208: 'struct_or_union_sub',
    209: '_expr',
    210: '_gen30',
    211: 'direct_declarator_modifier',
    212: '_gen34',
    213: '_gen24',
    214: 'struct_declaration',
    215: 'for_incr',
    216: 'init_declarator',
    217: '_gen6',
    218: '_gen26',
    219: '_gen38',
    220: 'direct_abstract_declarator_expr',
    221: 'enumeration_constant',
    222: 'block_item_list',
    223: 'enumerator_assignment',
    224: 'static_opt',
    225: 'direct_declarator_parameter_list',
    226: 'expression_opt',
    227: '_gen35',
    228: 'declaration',
    229: '_gen7',
    230: 'abstract_declarator',
    231: 'direct_abstract_declarator_opt',
    232: '_gen36',
    233: '_gen39',
    234: '_gen32',
    235: 'iteration_statement',
    236: '_gen17',
    237: 'direct_declarator_expr',
    238: 'statement',
    239: 'pp',
    240: 'compound_statement',
    241: '_gen42',
    242: 'parameter_declaration_sub_sub',
    243: 'expression_statement',
  }
  str_terminal = {
    'mod': 0,
    '_direct_abstract_declarator': 1,
    'volatile': 2,
    'restrict': 3,
    'int': 4,
    '_expr_sans_comma': 5,
    'if': 6,
    'lparen': 7,
    'decimal_floating_constant': 8,
    'rparen': 9,
    'string_literal': 10,
    'endif': 11,
    'gt': 12,
    'colon': 13,
    'floating_constant': 14,
    'const': 15,
    'identifier': 16,
    'float': 17,
    'unsigned': 18,
    'elipsis': 19,
    'lt': 20,
    'rshifteq': 21,
    'sizeof_separator': 22,
    'do': 23,
    'double': 24,
    'incr': 25,
    'function_definition_hint': 26,
    'goto': 27,
    'div': 28,
    'bitoreq': 29,
    'rbrace': 30,
    'signed': 31,
    'bitand': 32,
    'or': 33,
    'continue': 34,
    'enumeration_constant': 35,
    'bitxoreq': 36,
    'lsquare': 37,
    'poundpound': 38,
    'rsquare': 39,
    'not': 40,
    'bitandeq': 41,
    'union': 42,
    'gteq': 43,
    'eq': 44,
    'bitxor': 45,
    'dot': 46,
    'break': 47,
    'lshifteq': 48,
    'return': 49,
    'sizeof': 50,
    'complex': 51,
    'bitnot': 52,
    'lparen_cast': 53,
    'add': 54,
    'defined': 55,
    'typedef': 56,
    '_expr': 57,
    'struct': 58,
    'else_if': 59,
    'neq': 60,
    'lteq': 61,
    'questionmark': 62,
    'integer_constant': 63,
    'extern': 64,
    'else': 65,
    'hexadecimal_floating_constant': 66,
    'trailing_comma': 67,
    'for': 68,
    'pound': 69,
    'pp_number': 70,
    'exclamation_point': 71,
    'bool': 72,
    'addeq': 73,
    'lbrace': 74,
    'rshift': 75,
    'switch': 76,
    'long': 77,
    'imaginary': 78,
    'comma_va_args': 79,
    'muleq': 80,
    'defined_separator': 81,
    'modeq': 82,
    'asterisk': 83,
    'while': 84,
    'declarator_hint': 85,
    'default': 86,
    'enum': 87,
    'sub': 88,
    'function_prototype_hint': 89,
    'ampersand': 90,
    'register': 91,
    'inline': 92,
    'subeq': 93,
    'auto': 94,
    'semi': 95,
    'and': 96,
    'decr': 97,
    'void': 98,
    'arrow': 99,
    'bitor': 100,
    'assign': 101,
    'comma': 102,
    'case': 103,
    'typedef_identifier': 104,
    'char': 105,
    'diveq': 106,
    '_direct_declarator': 107,
    'tilde': 108,
    'universal_character_name': 109,
    'character_constant': 110,
    'static': 111,
    'external_declaration_hint': 112,
    'short': 113,
    'lshift': 114,
    'label_hint': 115,
  }
  str_nonterminal = {
    'storage_class_specifier': 116,
    'sizeof_body': 117,
    '_gen16': 118,
    'type_specifier': 119,
    'else_if_statement_list': 120,
    'initializer_list_item': 121,
    '_gen37': 122,
    'type_qualifier_list_opt': 123,
    'type_qualifier': 124,
    'token': 125,
    'typedef_name': 126,
    'function_specifier': 127,
    'else_statement': 128,
    'parameter_type_list': 129,
    'translation_unit': 130,
    '_gen9': 131,
    'struct_or_union_body': 132,
    '_gen10': 133,
    'external_declaration': 134,
    'pointer_opt': 135,
    'enumerator': 136,
    '_direct_declarator': 137,
    'specifier_qualifier': 138,
    'pointer_sub': 139,
    '_gen18': 140,
    '_expr_sans_comma': 141,
    'direct_declarator_modifier_list_opt': 142,
    'direct_declarator_size': 143,
    '_gen31': 144,
    'declarator_initializer': 145,
    'struct_declarator': 146,
    '_gen19': 147,
    'block_item': 148,
    '_gen20': 149,
    '_direct_abstract_declarator': 150,
    'declaration_specifier': 151,
    'else_if_statement': 152,
    '_gen1': 153,
    '_gen2': 154,
    '_gen25': 155,
    'struct_specifier': 156,
    'declaration_list': 157,
    '_gen23': 158,
    'initializer': 159,
    'labeled_statement': 160,
    'union_specifier': 161,
    'type_name': 162,
    'external_declaration_sub': 163,
    'parameter_declaration_sub': 164,
    'enum_specifier': 165,
    '_gen3': 166,
    'external_function': 167,
    'struct_declarator_body': 168,
    '_gen0': 169,
    'misc': 170,
    '_gen12': 171,
    '_gen13': 172,
    'constant': 173,
    '_gen21': 174,
    'for_init': 175,
    'for_cond': 176,
    '_gen4': 177,
    '_gen8': 178,
    'keyword': 179,
    'trailing_comma_opt': 180,
    '_gen41': 181,
    'punctuator': 182,
    'parameter_declaration': 183,
    '_gen27': 184,
    '_gen11': 185,
    '_gen28': 186,
    'designation': 187,
    'identifier': 188,
    '_gen14': 189,
    '_gen33': 190,
    'enum_specifier_sub': 191,
    '_gen40': 192,
    'external_declarator': 193,
    'enum_specifier_body': 194,
    'va_args': 195,
    '_gen29': 196,
    'external_declaration_sub_sub': 197,
    'external_prototype': 198,
    '_gen22': 199,
    '_gen15': 200,
    'selection_statement': 201,
    'designator': 202,
    'declarator': 203,
    'init_declarator_list': 204,
    'pointer': 205,
    '_gen5': 206,
    'jump_statement': 207,
    'struct_or_union_sub': 208,
    '_expr': 209,
    '_gen30': 210,
    'direct_declarator_modifier': 211,
    '_gen34': 212,
    '_gen24': 213,
    'struct_declaration': 214,
    'for_incr': 215,
    'init_declarator': 216,
    '_gen6': 217,
    '_gen26': 218,
    '_gen38': 219,
    'direct_abstract_declarator_expr': 220,
    'enumeration_constant': 221,
    'block_item_list': 222,
    'enumerator_assignment': 223,
    'static_opt': 224,
    'direct_declarator_parameter_list': 225,
    'expression_opt': 226,
    '_gen35': 227,
    'declaration': 228,
    '_gen7': 229,
    'abstract_declarator': 230,
    'direct_abstract_declarator_opt': 231,
    '_gen36': 232,
    '_gen39': 233,
    '_gen32': 234,
    'iteration_statement': 235,
    '_gen17': 236,
    'direct_declarator_expr': 237,
    'statement': 238,
    'pp': 239,
    'compound_statement': 240,
    '_gen42': 241,
    'parameter_declaration_sub_sub': 242,
    'expression_statement': 243,
  }
  terminal_count = 116
  nonterminal_count = 128
  parse_table = [
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 39, -1, -1, -1, -1, -1, -1, -1, 415, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 44, -1, -1, 13, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 249, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, 19, -1, -1, -1, -1, -1, -1, -1, -1, 219, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, 217, 217, 217, 217, -1, -1, 217, -1, -1, -1, -1, -1, 217, -1, 217, 217, 217, 217, -1, -1, -1, -1, -1, 217, -1, 217, -1, -1, -1, -1, 217, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 217, -1, -1, -1, -1, -1, -1, -1, -1, 217, -1, -1, -1, -1, 217, -1, 217, -1, -1, -1, -1, -1, 217, -1, -1, -1, -1, -1, -1, -1, 217, -1, 53, -1, -1, 217, 217, 217, -1, -1, -1, 217, -1, 217, -1, 217, -1, 217, -1, 217, 217, -1, 217, 217, -1, -1, 217, -1, -1, -1, 217, -1, 217, 217, -1, 217, -1, -1, -1, 217, -1, 217, -1, -1],
    [-1, -1, -1, -1, 144, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 185, 274, -1, -1, -1, -1, -1, 57, -1, -1, -1, -1, -1, -1, 135, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 169, -1, -1, -1, -1, -1, -1, -1, -1, 394, -1, -1, -1, -1, -1, -1, 25, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 36, -1, -1, -1, -1, 161, 7, -1, -1, -1, -1, -1, -1, -1, -1, 73, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 205, -1, -1, -1, -1, -1, 98, 247, -1, -1, -1, -1, -1, -1, -1, 312, -1, -1],
    [-1, -1, 122, 122, 122, -1, 122, 122, 122, -1, 122, 122, -1, -1, 122, 122, 122, 122, 122, -1, -1, -1, -1, 122, 122, 122, -1, 122, -1, -1, 122, 122, 122, -1, 122, 122, -1, -1, -1, -1, -1, -1, 122, -1, -1, -1, -1, 122, -1, 122, 122, 122, -1, 122, -1, -1, 122, 122, 122, 122, -1, -1, -1, 122, 122, 122, 122, -1, 122, -1, -1, -1, 122, -1, 122, -1, 122, 122, 122, -1, -1, -1, -1, 122, 122, -1, 122, 122, -1, -1, -1, 122, 122, -1, 122, 122, -1, 122, 122, -1, -1, -1, -1, 122, 122, 122, -1, -1, -1, -1, 122, 122, -1, 122, -1, 122],
    [-1, -1, -1, -1, -1, 338, -1, 338, 338, -1, 338, -1, -1, -1, 338, -1, 338, -1, -1, -1, -1, -1, -1, -1, -1, 338, -1, -1, -1, -1, -1, -1, 338, -1, -1, 338, -1, 338, -1, -1, -1, -1, -1, -1, -1, -1, 338, -1, -1, -1, 338, -1, -1, 338, -1, -1, -1, -1, -1, -1, -1, -1, -1, 80, -1, -1, 338, -1, -1, -1, -1, -1, -1, -1, 338, -1, -1, -1, -1, -1, -1, -1, -1, 338, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 338, -1, -1, -1, 338, -1, -1, -1, -1, -1, -1, -1, -1, 338, -1, -1, -1, -1, -1],
    [-1, -1, 223, 223, 223, -1, 223, 223, 223, -1, 223, 223, -1, -1, 223, 223, 223, 223, 223, -1, -1, -1, -1, 223, 223, 223, -1, 223, -1, -1, 223, 223, 223, -1, 223, 223, -1, -1, -1, -1, -1, -1, 223, -1, -1, -1, -1, 223, -1, 223, 223, 223, -1, 223, -1, -1, 223, 223, 223, 264, -1, -1, -1, 223, 223, 223, 223, -1, 223, -1, -1, -1, 223, -1, 223, -1, 223, 223, 223, -1, -1, -1, -1, 223, 223, -1, 223, 223, -1, -1, -1, 223, 223, -1, 223, 223, -1, 223, 223, -1, -1, -1, -1, 223, 223, 223, -1, -1, -1, -1, 223, 223, -1, 223, -1, 223],
    [-1, 220, 268, 268, -1, -1, -1, 220, -1, -1, -1, -1, -1, -1, -1, 268, 220, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 220, -1, -1, -1, 220, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 220, -1, -1, -1, -1, 220, -1, -1, -1, 220, -1, -1, -1, -1],
    [-1, -1, 243, 184, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 232, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [277, -1, 275, 275, 275, -1, 275, 277, 346, 277, 295, -1, 277, 277, 346, 275, 269, 275, 275, 277, 277, 277, -1, 275, 275, 277, -1, 275, 277, 277, 277, 275, -1, 277, 275, 346, 277, 277, 277, 277, -1, 277, 275, 277, 277, 277, 277, 275, 277, 275, 275, 275, -1, -1, 277, -1, 275, -1, 275, -1, 277, 277, 277, 346, 275, 275, 346, -1, 275, 277, 337, 277, 275, 277, 277, 277, 275, 275, 275, -1, 277, -1, 277, -1, 275, -1, 275, 275, 277, -1, 277, 275, 275, 277, 275, 277, 277, 277, 275, 277, 277, 277, 277, 275, -1, 275, -1, -1, 277, -1, 346, 275, -1, 275, 277, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 115, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 320, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 28, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 381, 381, 381, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 381, -1, 381, 381, -1, -1, -1, -1, -1, 381, -1, -1, -1, -1, -1, -1, 381, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 381, -1, -1, -1, -1, -1, -1, -1, -1, 381, -1, -1, -1, -1, 381, -1, 381, -1, -1, -1, -1, -1, 381, -1, -1, -1, -1, -1, -1, -1, 381, -1, -1, -1, -1, 381, 381, -1, -1, -1, -1, -1, -1, -1, -1, 381, -1, -1, -1, 381, 381, -1, 381, -1, -1, -1, 381, -1, -1, -1, -1, -1, 381, 381, -1, -1, -1, -1, -1, 381, -1, 381, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 210, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, 258, -1, -1, -1, -1, -1, -1, -1, -1, 258, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 258, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 258, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 333, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 270, -1, -1, -1, -1, -1, -1, 240, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 26, -1, -1, -1],
    [-1, 97, -1, -1, -1, -1, -1, 97, -1, -1, -1, -1, -1, -1, -1, -1, 97, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 97, -1, -1, -1, 97, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 97, -1, -1, -1, -1, 97, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 88, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 77, 77, 362, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 77, -1, 362, 362, -1, -1, -1, -1, -1, 362, -1, -1, -1, -1, -1, -1, 362, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 362, -1, -1, -1, -1, -1, -1, -1, -1, 362, -1, -1, -1, -1, -1, -1, 362, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 362, -1, -1, -1, -1, 362, 362, -1, -1, -1, -1, -1, -1, -1, -1, 362, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 362, -1, -1, -1, -1, -1, 362, 362, -1, -1, -1, -1, -1, -1, -1, 362, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 87, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 248, 248, 248, -1, -1, 252, -1, -1, -1, -1, -1, 252, -1, 248, 252, 248, 248, -1, -1, -1, -1, -1, 248, -1, -1, -1, -1, -1, -1, 248, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 248, -1, -1, -1, -1, -1, -1, -1, -1, 248, -1, -1, -1, -1, -1, -1, 248, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 248, -1, -1, -1, -1, 248, 248, -1, -1, -1, -1, 252, -1, -1, -1, 248, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 248, -1, -1, -1, -1, -1, 248, 248, -1, 252, -1, -1, -1, -1, -1, 248, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 48, 48, -1, -1, -1, 3, 3, -1, 3, -1, -1, -1, 3, 48, 3, -1, -1, -1, -1, -1, -1, -1, -1, 3, -1, -1, -1, -1, -1, -1, 3, -1, -1, 3, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 3, -1, -1, 3, -1, -1, -1, 3, -1, -1, -1, -1, -1, 3, -1, -1, 3, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 3, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 3, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 3, 48, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, 324, 324, -1, 324, -1, -1, -1, 324, -1, 324, -1, -1, -1, -1, -1, -1, -1, -1, 324, -1, -1, -1, -1, -1, -1, 324, -1, -1, 324, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 324, -1, -1, 324, -1, -1, -1, 324, -1, -1, -1, -1, -1, 324, -1, -1, 324, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 90, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 324, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 324, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 360, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 141, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, 183, -1, -1, -1, -1, -1, 237, -1, -1, 183, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 183, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 183, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, 121, -1, -1, -1, -1, -1, 121, -1, -1, 121, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 121, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 121, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 102, 102, 102, -1, 290, 290, 290, -1, 290, -1, -1, -1, 290, 102, 290, 102, 102, -1, -1, -1, -1, 290, 102, 290, -1, 290, -1, -1, -1, 102, 290, -1, 290, 290, -1, -1, -1, -1, -1, -1, 102, -1, -1, -1, -1, 290, -1, 290, 290, 102, -1, 290, -1, -1, 102, 290, 102, -1, -1, -1, -1, 290, 102, -1, 290, -1, 290, -1, -1, -1, 102, -1, 290, -1, 290, 102, 102, -1, -1, -1, -1, 290, 290, -1, 290, 102, -1, -1, -1, 102, 102, -1, 102, 290, -1, 290, 102, -1, -1, -1, -1, 290, 102, 102, -1, -1, -1, -1, 290, 102, -1, 102, -1, 290],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 392, -1, -1, -1, -1, -1, -1, 265, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 178, 178, 251, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 178, -1, 251, 251, -1, -1, -1, -1, -1, 251, -1, -1, -1, -1, -1, -1, 251, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 251, -1, -1, -1, -1, -1, -1, -1, -1, 251, -1, -1, -1, -1, 409, -1, 251, -1, -1, -1, -1, -1, 409, -1, -1, -1, -1, -1, -1, -1, 251, -1, -1, -1, -1, 251, 251, -1, -1, -1, -1, -1, -1, -1, -1, 251, -1, -1, -1, 409, 194, -1, 409, -1, -1, -1, 251, -1, -1, -1, -1, -1, 251, 251, -1, -1, -1, -1, -1, 409, -1, 251, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 271, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 382, 382, 382, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 382, -1, 382, 382, -1, -1, -1, -1, -1, 382, -1, -1, -1, -1, -1, -1, 382, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 382, -1, -1, -1, -1, -1, -1, -1, -1, 382, -1, -1, -1, -1, 382, -1, 382, -1, -1, -1, -1, -1, 382, -1, -1, -1, -1, -1, -1, -1, 382, -1, -1, -1, -1, 382, 382, -1, -1, -1, -1, -1, -1, -1, -1, 382, -1, -1, -1, 382, 382, -1, 382, -1, -1, -1, 382, -1, -1, -1, -1, -1, 382, 382, -1, -1, -1, -1, -1, 382, -1, 382, -1, -1],
    [-1, 62, 56, 56, 56, -1, -1, 62, -1, -1, -1, -1, -1, -1, -1, 56, 62, 56, 56, -1, -1, -1, -1, -1, 56, -1, 62, -1, -1, -1, -1, 56, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 56, -1, -1, -1, -1, -1, -1, -1, -1, 56, -1, -1, -1, -1, 56, -1, 56, -1, -1, -1, -1, -1, 56, -1, -1, -1, -1, -1, -1, -1, 56, -1, -1, -1, -1, 56, 56, 62, -1, -1, -1, 62, -1, 62, -1, 56, -1, 62, -1, 56, 56, -1, 56, 62, -1, -1, 56, -1, -1, -1, 62, -1, 56, 56, -1, 62, -1, -1, -1, 56, -1, 56, -1, -1],
    [-1, 11, 9, 9, -1, -1, -1, 11, -1, -1, -1, -1, -1, -1, -1, 9, 11, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 11, -1, -1, -1, 11, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 11, -1, -1, -1, -1, 11, -1, -1, -1, 11, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 50, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 104, 104, 104, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 104, -1, 104, 104, -1, -1, -1, -1, -1, 104, -1, -1, -1, -1, -1, -1, 104, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 104, -1, -1, -1, -1, -1, -1, -1, -1, 104, -1, -1, -1, -1, 104, -1, 104, -1, -1, -1, -1, -1, 104, -1, -1, -1, -1, -1, -1, -1, 104, -1, 104, -1, -1, 104, 104, -1, -1, -1, -1, -1, -1, -1, -1, 104, -1, -1, -1, 104, 104, -1, 104, 104, -1, -1, 104, -1, -1, -1, 104, -1, 104, 104, -1, -1, -1, -1, -1, 104, -1, 104, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 147, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, 412, -1, 412, 412, -1, 412, -1, -1, -1, 412, -1, 412, -1, -1, -1, -1, -1, -1, -1, -1, 412, -1, -1, -1, -1, -1, -1, 412, -1, -1, 412, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 412, -1, -1, 412, -1, -1, -1, -1, -1, -1, -1, -1, -1, 412, -1, -1, 412, -1, -1, -1, -1, -1, -1, -1, 117, -1, -1, -1, -1, -1, -1, -1, -1, 412, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 412, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 412, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 391, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 29, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 195],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 228, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, 133, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 82, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 59, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 35, -1, -1, -1, 35, -1, -1, -1, -1, -1, 35, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, 171, -1, -1, -1, -1, -1, 171, -1, -1, -1, -1, -1, -1, -1, -1, 171, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 171, -1, -1, -1, 171, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 171, -1, -1, -1, -1, 171, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 256, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 166, -1, -1, -1, 166, -1, -1, -1, -1, -1, 105, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 376, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 406, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 38, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 284, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 216, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, 299, -1, 299, 299, -1, 299, -1, -1, -1, 299, -1, 299, -1, -1, -1, -1, -1, -1, -1, -1, 299, -1, -1, -1, -1, -1, -1, 299, -1, -1, 299, -1, 299, -1, -1, -1, -1, -1, -1, -1, -1, 299, -1, -1, -1, 299, -1, -1, 299, -1, -1, -1, -1, -1, -1, -1, -1, -1, 299, -1, -1, 299, -1, -1, -1, -1, -1, -1, -1, 299, -1, -1, -1, -1, -1, -1, -1, -1, 299, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 299, -1, -1, -1, 299, -1, -1, -1, -1, -1, -1, -1, -1, 299, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 407, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 308, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, 181, -1, -1, -1, -1, -1, 302, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 107, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 51, -1, -1, 383, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 213, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 319, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 305, -1, -1, -1, -1, -1, -1, 305, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 197, 197, 197, -1, -1, 126, 126, -1, 126, -1, -1, -1, 126, 197, 126, 197, 197, -1, -1, -1, -1, -1, 197, 126, -1, -1, -1, -1, -1, 197, 126, -1, -1, 126, -1, -1, -1, -1, -1, -1, 197, -1, -1, -1, -1, -1, -1, -1, 126, 197, -1, 126, -1, -1, 197, 126, 197, -1, -1, -1, -1, 126, 197, -1, 126, -1, -1, -1, -1, -1, 197, -1, -1, -1, -1, 197, 197, -1, -1, -1, -1, 126, -1, -1, -1, 197, -1, -1, -1, 197, 197, -1, 197, 379, -1, 126, 197, -1, -1, -1, -1, -1, 197, 197, -1, -1, -1, -1, 126, 197, -1, 197, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 136, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 101, -1, -1, -1, -1, -1, -1, 188, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, 198, -1, -1, -1, -1, -1, -1, -1, -1, 198, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 198, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 389, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 198, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 116, 297, 174, -1, 95, -1, -1, -1, -1, -1, -1, -1, -1, 373, -1, 180, 84, -1, -1, -1, -1, 114, 309, -1, -1, 54, -1, -1, -1, 351, -1, -1, 340, -1, -1, -1, -1, -1, -1, -1, 58, -1, -1, -1, -1, 191, -1, 317, 2, 418, -1, -1, -1, -1, 41, -1, 6, -1, -1, -1, -1, -1, 170, 127, -1, -1, 55, -1, -1, -1, 43, -1, -1, -1, 345, 411, 276, -1, -1, -1, -1, -1, 365, -1, 348, 15, -1, -1, -1, 160, 334, -1, 12, -1, -1, -1, 93, -1, -1, -1, -1, 65, -1, 34, -1, -1, -1, -1, -1, 176, -1, 331, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 131, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 294, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 119, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [86, -1, -1, -1, -1, -1, -1, 374, -1, 417, -1, -1, 8, 52, -1, -1, -1, -1, -1, 1, 388, 350, -1, -1, -1, 23, -1, -1, 31, 316, 245, -1, -1, 420, -1, -1, 341, 422, 10, 370, -1, 282, -1, 89, 192, 111, 154, -1, 387, -1, -1, -1, -1, -1, 385, -1, -1, -1, -1, -1, 157, 79, 353, -1, -1, -1, -1, -1, -1, 330, -1, 257, -1, 234, 96, 164, -1, -1, -1, -1, 83, -1, 66, -1, -1, -1, -1, -1, 410, -1, 313, -1, -1, 396, -1, 81, 91, 363, -1, 22, 201, 314, 47, -1, -1, -1, -1, -1, 344, -1, -1, -1, -1, -1, 368, -1],
    [-1, -1, 328, 328, 328, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 328, -1, 328, 328, -1, -1, -1, -1, -1, 328, -1, -1, -1, -1, -1, -1, 328, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 328, -1, -1, -1, -1, -1, -1, -1, -1, 328, -1, -1, -1, -1, 328, -1, 328, -1, -1, -1, -1, -1, 328, -1, -1, -1, -1, -1, -1, -1, 328, -1, -1, -1, -1, 328, 328, -1, -1, -1, -1, -1, -1, -1, -1, 328, -1, -1, -1, 328, 328, -1, 328, -1, -1, -1, 328, -1, -1, -1, -1, -1, 328, 328, -1, -1, -1, -1, -1, 328, -1, 328, -1, -1],
    [-1, -1, 318, 318, 318, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 318, -1, 318, 318, -1, -1, -1, -1, -1, 318, -1, -1, -1, -1, -1, -1, 318, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 318, -1, -1, -1, -1, -1, -1, -1, -1, 318, -1, -1, -1, -1, 318, -1, 318, -1, -1, -1, -1, -1, 318, -1, -1, -1, -1, -1, -1, -1, 318, -1, -1, -1, -1, 318, 318, -1, -1, -1, -1, -1, -1, -1, -1, 318, -1, -1, -1, 318, 318, -1, 318, -1, -1, -1, 318, -1, -1, -1, -1, -1, 318, 318, -1, -1, -1, -1, -1, 318, -1, 318, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 262, -1, -1, -1, -1, -1, 260, 262, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 325, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 143, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 60, -1, -1, -1, -1, -1, -1, -1, -1, 60, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 60, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 366, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, 288, -1, 288, 288, -1, 288, -1, -1, -1, 288, -1, 288, -1, -1, -1, -1, -1, -1, -1, -1, 288, -1, -1, -1, -1, -1, -1, 288, -1, -1, 288, -1, 322, -1, -1, -1, -1, -1, -1, -1, -1, 322, -1, -1, -1, 288, -1, -1, 288, -1, -1, -1, -1, -1, -1, -1, -1, -1, 288, -1, -1, 288, -1, -1, -1, -1, -1, -1, -1, 288, -1, -1, -1, -1, -1, -1, -1, -1, 288, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 288, -1, -1, -1, 322, -1, -1, -1, -1, -1, -1, -1, -1, 288, -1, -1, -1, -1, -1],
    [-1, 110, -1, -1, -1, -1, -1, 110, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 110, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 110, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 226, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 68, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, 118, -1, 118, 118, -1, 118, -1, -1, -1, 118, -1, 118, -1, -1, -1, -1, -1, -1, -1, -1, 118, -1, -1, -1, -1, -1, -1, 118, -1, -1, 118, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 118, -1, -1, 118, -1, -1, -1, -1, -1, -1, -1, -1, -1, 118, -1, -1, 118, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 118, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 118, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 118, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 61, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 46, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 120, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 336, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 222, -1, -1, -1, 356, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 255, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, 128, 128, 128, 128, -1, -1, 128, -1, -1, -1, -1, -1, 128, -1, 128, 128, 128, 128, -1, -1, -1, -1, -1, 128, -1, 128, -1, -1, -1, -1, 128, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 128, -1, -1, -1, -1, -1, -1, -1, -1, 128, -1, -1, -1, -1, 128, -1, 128, -1, -1, -1, -1, -1, 128, -1, -1, -1, -1, -1, -1, -1, 128, -1, 414, -1, -1, 128, 128, 128, -1, -1, -1, 128, -1, 128, -1, 128, -1, 128, -1, 128, 128, -1, 128, 128, -1, -1, 128, -1, -1, -1, 128, -1, 128, 128, -1, 128, -1, -1, -1, 128, -1, 128, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 179, -1, -1, -1, -1, -1, -1, -1, -1, 179, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 386, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, 150, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 355, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 20, -1, -1, -1, -1, -1, -1, -1, -1, 401, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, 33, -1, -1, -1, -1, -1, -1, -1, -1, 33, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 33, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 33, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, 408, -1, -1, -1, -1, -1, -1, -1, -1, 408, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 408, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 408, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, 289, -1, -1, -1, -1, -1, 289, -1, -1, -1, -1, -1, -1, -1, -1, 289, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 289, -1, -1, -1, 289, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 289, -1, -1, -1, -1, 289, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 134, 134, 134, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 134, -1, 134, 134, -1, -1, -1, -1, -1, 134, -1, -1, -1, -1, -1, -1, 134, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 134, -1, -1, -1, -1, -1, -1, -1, -1, 134, -1, -1, -1, -1, 134, -1, 134, -1, -1, -1, -1, -1, 134, -1, -1, -1, -1, -1, -1, -1, 134, -1, 134, -1, -1, 134, 134, -1, -1, -1, -1, -1, -1, -1, -1, 134, -1, -1, -1, 134, 134, -1, 134, 134, -1, -1, 134, -1, -1, -1, 134, -1, 134, 134, -1, -1, -1, -1, -1, 134, -1, 134, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 202, -1, -1, -1, -1, -1, -1, 359, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 5, -1, 310, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 124, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 416, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, 72, -1, 72, 72, 209, 72, -1, -1, 209, 72, -1, 72, -1, -1, -1, -1, -1, -1, -1, -1, 72, -1, -1, -1, -1, -1, -1, 72, -1, -1, 72, -1, 72, -1, 209, -1, -1, -1, -1, -1, -1, 72, -1, -1, -1, 72, -1, -1, 72, -1, -1, -1, -1, -1, -1, -1, -1, 209, 72, -1, -1, 72, 209, -1, -1, -1, -1, -1, -1, 72, -1, -1, -1, -1, -1, -1, -1, -1, 72, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 209, -1, 72, -1, 209, -1, 72, 100, -1, -1, -1, -1, -1, -1, -1, 72, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 358, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 21, 21, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 21, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 211, -1, -1, -1, -1],
    [-1, 149, -1, -1, -1, -1, -1, 149, -1, -1, -1, -1, -1, -1, -1, -1, 149, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 149, -1, -1, -1, 145, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 149, -1, -1, -1, -1, 149, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 152, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 92, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 42, 42, 42, -1, -1, 42, -1, -1, -1, -1, -1, 42, -1, 42, 42, 42, 42, -1, -1, -1, -1, -1, 42, -1, -1, -1, -1, -1, -1, 42, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 42, -1, -1, -1, -1, -1, -1, -1, -1, 42, -1, -1, -1, -1, -1, -1, 42, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 42, -1, -1, -1, -1, 42, 42, -1, -1, -1, -1, 42, -1, -1, -1, 42, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 42, -1, -1, -1, -1, -1, 42, 42, -1, 42, -1, -1, -1, -1, -1, 42, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, 190, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 230, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, 203, -1, -1, -1, -1, -1, -1, -1, -1, 203, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 203, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 203, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, 167, -1, -1, -1, -1, -1, -1, -1, -1, 167, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 167, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 155, -1, -1, -1, -1, -1, -1, 155, -1, -1, -1, -1, 167, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 292, 292, -1, -1, -1, 390, 390, -1, 390, -1, -1, -1, 390, 292, 390, -1, -1, -1, -1, -1, -1, -1, -1, 390, -1, -1, -1, -1, -1, -1, 390, -1, -1, 390, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 390, -1, -1, 390, -1, -1, -1, 390, -1, -1, -1, -1, -1, 390, -1, -1, 390, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 390, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 390, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 390, 292, -1, -1, -1, -1],
    [-1, -1, 224, 224, 224, -1, 224, 224, 224, -1, 224, 224, -1, -1, 224, 224, 224, 224, 224, -1, -1, -1, -1, 224, 224, 224, -1, 224, -1, -1, 224, 224, 224, -1, 224, 224, -1, -1, -1, -1, -1, -1, 224, -1, -1, -1, -1, 224, -1, 224, 224, 224, -1, 224, -1, -1, 224, 224, 224, -1, -1, -1, -1, 224, 224, 231, 224, -1, 224, -1, -1, -1, 224, -1, 224, -1, 224, 224, 224, -1, -1, -1, -1, 224, 224, -1, 224, 224, -1, -1, -1, 224, 224, -1, 224, 224, -1, 224, 224, -1, -1, -1, -1, 224, 224, 224, -1, -1, -1, -1, 224, 224, -1, 224, -1, 224],
    [-1, -1, 235, 235, -1, -1, -1, 235, 235, -1, 235, -1, -1, -1, 235, 235, 235, -1, -1, -1, -1, -1, -1, -1, -1, 235, -1, -1, -1, -1, -1, -1, 235, -1, -1, 235, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 235, -1, -1, 235, -1, -1, -1, 235, -1, -1, -1, -1, -1, 235, -1, -1, 235, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 235, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 235, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 235, 235, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 172, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 403, 403, 403, -1, 403, 403, 403, -1, 403, -1, -1, -1, 403, 403, 403, 403, 403, -1, -1, -1, -1, 403, 403, 403, -1, 403, -1, -1, 403, 403, 403, -1, 403, 403, -1, -1, -1, -1, -1, -1, 403, -1, -1, -1, -1, 403, -1, 403, 403, 403, -1, 403, -1, -1, 403, 403, 403, -1, -1, -1, -1, 403, 403, -1, 403, -1, 403, -1, -1, -1, 403, -1, 403, -1, 403, 403, 403, -1, -1, -1, -1, 403, 403, -1, 403, 403, -1, -1, -1, 403, 403, -1, 403, 403, -1, 403, 403, -1, -1, -1, -1, 403, 403, 403, -1, -1, -1, -1, 403, 403, -1, 403, -1, 403],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 204, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 227, 204, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, 349, 349, -1, 349, -1, -1, -1, 349, -1, 349, -1, -1, -1, -1, -1, -1, -1, -1, 349, -1, -1, -1, -1, -1, -1, 349, -1, -1, 349, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 349, -1, -1, 349, -1, -1, -1, 349, -1, -1, -1, -1, -1, 349, -1, -1, 349, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 349, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 349, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 349, 354, -1, -1, -1, -1],
    [-1, -1, 395, 395, 395, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 395, 14, 395, 395, -1, -1, -1, -1, -1, 395, -1, -1, -1, -1, -1, -1, 395, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 395, -1, -1, -1, -1, -1, -1, -1, -1, 395, -1, -1, -1, -1, 395, -1, 395, -1, -1, -1, -1, -1, 395, -1, -1, -1, -1, -1, -1, -1, 395, -1, -1, -1, -1, 395, 395, -1, -1, -1, -1, -1, -1, -1, -1, 395, -1, -1, -1, 395, 395, -1, 395, -1, -1, -1, 395, -1, -1, -1, -1, -1, 395, 395, -1, -1, -1, -1, -1, 395, -1, 395, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, 242, 242, 189, 242, -1, -1, -1, 242, -1, 242, -1, -1, -1, -1, -1, -1, -1, -1, 242, -1, -1, -1, -1, -1, -1, 242, -1, -1, 242, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 242, -1, -1, 242, -1, -1, -1, 242, -1, -1, -1, -1, -1, 242, -1, -1, 242, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 242, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 189, -1, 242, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 242, -1, -1, -1, -1, -1],
    [-1, -1, 293, 293, 293, -1, 293, 293, 293, -1, 293, -1, -1, -1, 293, 293, 293, 293, 293, -1, -1, -1, -1, 293, 293, 293, -1, 293, -1, -1, 293, 293, 293, -1, 293, 293, -1, -1, -1, -1, -1, -1, 293, -1, -1, -1, -1, 293, -1, 293, 293, 293, -1, 293, -1, -1, 293, 293, 293, -1, -1, -1, -1, 293, 293, -1, 293, -1, 293, -1, -1, -1, 293, -1, 293, -1, 293, 293, 293, -1, -1, -1, -1, 293, 293, -1, 293, 293, -1, -1, -1, 293, 293, -1, 293, 293, -1, 293, 293, -1, -1, -1, -1, 293, 293, 293, -1, -1, -1, -1, 293, 293, -1, 293, -1, 293],
    [-1, -1, 49, 49, 49, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 49, -1, 49, 49, -1, -1, -1, -1, -1, 49, -1, -1, -1, -1, -1, -1, 49, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 49, -1, -1, -1, -1, -1, -1, -1, -1, 49, -1, -1, -1, -1, 49, -1, 49, -1, -1, -1, -1, -1, 49, -1, -1, -1, -1, -1, -1, -1, 49, -1, -1, -1, -1, 49, 49, -1, -1, -1, -1, -1, -1, -1, -1, 49, -1, -1, -1, 49, 49, -1, 49, -1, -1, -1, 49, -1, -1, -1, -1, -1, 49, 49, -1, -1, -1, -1, -1, 49, -1, 49, -1, -1],
    [-1, -1, 246, 246, 246, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 246, -1, 246, 246, -1, -1, -1, -1, -1, 246, -1, -1, -1, -1, -1, -1, 246, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 246, -1, -1, -1, -1, -1, -1, -1, -1, 246, -1, -1, -1, -1, 246, -1, 246, -1, -1, -1, -1, -1, 246, -1, -1, -1, -1, -1, -1, -1, 246, -1, 267, -1, -1, 246, 246, -1, -1, -1, -1, -1, -1, -1, -1, 246, -1, -1, -1, 246, 246, -1, 246, 267, -1, -1, 246, -1, -1, -1, 267, -1, 246, 246, -1, -1, -1, -1, -1, 246, -1, 246, -1, -1],
    [-1, 372, -1, -1, -1, -1, -1, 372, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 372, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, 307, -1, -1, -1, -1, -1, 307, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 291, 291, 291, -1, 291, 291, 291, -1, 291, -1, -1, -1, 291, 291, 291, 291, 291, -1, -1, -1, -1, 291, 291, 291, -1, 291, -1, -1, 380, 291, 291, -1, 291, 291, -1, -1, -1, -1, -1, -1, 291, -1, -1, -1, -1, 291, -1, 291, 291, 291, -1, 291, -1, -1, 291, 291, 291, -1, -1, -1, -1, 291, 291, -1, 291, -1, 291, -1, -1, -1, 291, -1, 291, -1, 291, 291, 291, -1, -1, -1, -1, 291, 291, -1, 291, 291, -1, -1, -1, 291, 291, -1, 291, 291, -1, 291, 291, -1, -1, -1, -1, 291, 291, 291, -1, -1, -1, -1, 291, 291, -1, 291, -1, 291],
    [-1, -1, 304, 304, 304, -1, 304, 304, 304, -1, 304, 304, -1, -1, 304, 304, 304, 304, 304, -1, -1, -1, -1, 304, 304, 304, -1, 304, -1, -1, 304, 304, 304, -1, 304, 304, -1, -1, -1, -1, -1, -1, 304, -1, -1, -1, -1, 304, -1, 304, 304, 304, -1, 304, -1, -1, 304, 304, 304, 272, -1, -1, -1, 304, 304, 304, 304, -1, 304, -1, -1, -1, 304, -1, 304, -1, 304, 304, 304, -1, -1, -1, -1, 304, 304, -1, 304, 304, -1, -1, -1, 304, 304, -1, 304, 304, -1, 304, 304, -1, -1, -1, -1, 304, 304, 304, -1, -1, -1, -1, 304, 304, -1, 304, -1, 304],
    [-1, 361, -1, -1, -1, -1, -1, 361, -1, -1, -1, -1, -1, -1, -1, -1, 361, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 361, -1, -1, -1, 361, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 361, -1, -1, -1, -1, 361, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 85, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 397, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 421, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 74, 74, 74, -1, -1, 74, -1, -1, -1, -1, -1, 74, -1, 74, 74, 74, 74, -1, -1, -1, -1, -1, 74, -1, -1, -1, -1, -1, 173, 74, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 74, -1, -1, -1, -1, -1, -1, -1, -1, 74, -1, -1, -1, -1, -1, -1, 74, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 74, -1, -1, -1, -1, 74, 74, -1, -1, -1, -1, 74, -1, -1, -1, 74, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 74, -1, -1, -1, -1, -1, 74, 74, -1, 74, -1, -1, -1, -1, -1, 74, -1, -1],
    [-1, -1, 377, 377, -1, -1, -1, 377, 377, -1, 377, -1, -1, -1, 377, 377, 377, -1, -1, -1, -1, -1, -1, -1, -1, 377, -1, -1, -1, -1, -1, -1, 377, -1, -1, 377, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 377, -1, -1, 377, -1, -1, -1, 377, -1, -1, -1, -1, -1, 377, -1, -1, 377, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 377, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 377, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 377, 377, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, 378, 168, 168, -1, 168, -1, -1, -1, 168, -1, 168, -1, -1, -1, -1, -1, -1, 298, -1, 168, -1, 4, -1, -1, -1, -1, 168, -1, 4, 168, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 4, -1, 4, 168, -1, -1, 168, -1, -1, -1, 168, -1, -1, -1, -1, -1, 168, -1, -1, 168, -1, 298, -1, -1, -1, -1, -1, 326, -1, 378, -1, -1, -1, -1, -1, -1, 168, 298, -1, 311, -1, -1, -1, -1, -1, -1, -1, -1, 168, -1, 168, -1, -1, -1, -1, -1, 311, -1, -1, -1, -1, -1, -1, 168, -1, -1, -1, -1, 311],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 0, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 278, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 18, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 263, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 109, 109, 109, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 109, -1, 109, 109, -1, -1, -1, -1, -1, 109, -1, -1, -1, -1, -1, -1, 109, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 109, -1, -1, -1, -1, -1, -1, -1, -1, 109, -1, -1, -1, -1, 109, -1, 109, -1, -1, -1, -1, -1, 109, -1, -1, -1, -1, -1, -1, -1, 109, -1, -1, -1, -1, 109, 109, -1, -1, -1, -1, -1, -1, -1, -1, 109, -1, -1, -1, 109, 109, -1, 109, -1, -1, -1, 109, -1, -1, -1, -1, -1, 109, 109, -1, -1, -1, -1, -1, 109, -1, 109, -1, -1],
    [-1, 343, -1, -1, -1, -1, -1, 286, -1, -1, -1, -1, -1, -1, -1, -1, 286, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 343, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 343, -1, -1, -1, -1, 286, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, 158, 158, -1, 158, -1, -1, -1, 158, -1, 158, -1, -1, -1, -1, -1, -1, -1, -1, 158, -1, -1, -1, -1, -1, -1, 158, -1, -1, 158, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 158, -1, -1, 158, -1, -1, -1, 158, -1, -1, -1, -1, -1, 158, -1, -1, 158, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 158, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 158, -1, 158, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 158, -1, -1, -1, -1, -1],
  ]
  def terminal(self, str):
    return self.str_terminal[str]
  def terminalNames(self):
    return list(self.str_terminal.keys())
  def isTerminal(self, id):
    return 0 <= id <= 115
  def isNonTerminal(self, id):
    return 116 <= id <= 243
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
    return self.parse_table[n - 116][self.sym.getId()]
  def call(self, nt_str):
    return getattr(self, nt_str)()
  def _STORAGE_CLASS_SPECIFIER(self, depth=0, tracer=None):
    rule = self.rule(116)
    tree = ParseTree( NonTerminal(116, self.getAtomString(116)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 13:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(94, tracer) # auto
      tree.add(t)
      return tree
    elif rule == 39:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(56, tracer) # typedef
      tree.add(t)
      return tree
    elif rule == 44:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(91, tracer) # register
      tree.add(t)
      return tree
    elif rule == 249:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(111, tracer) # static
      tree.add(t)
      return tree
    elif rule == 415:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(64, tracer) # extern
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _SIZEOF_BODY(self, depth=0, tracer=None):
    rule = self.rule(117)
    tree = ParseTree( NonTerminal(117, self.getAtomString(117)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 19:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(7, tracer) # lparen
      tree.add(t)
      subtree = self._TYPE_NAME(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(9, tracer) # rparen
      tree.add(t)
      return tree
    elif rule == 219:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(16, tracer) # identifier
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN16(self, depth=0, tracer=None):
    rule = self.rule(118)
    tree = ParseTree( NonTerminal(118, self.getAtomString(118)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [1, 13, 56, 4, 87, 64, 77, 89, 111, 17, 79, 2, 94, 24, 3, 26, 58, 91, 31, 78, 104, 95, 113, 98, 18, 102, 15, 105, 72, 92, 51, 42, 85, 83, 16, 107, 7]):
      return tree
    if self.sym == None:
      return tree
    if rule == 53:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STRUCT_OR_UNION_BODY(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _TYPE_SPECIFIER(self, depth=0, tracer=None):
    rule = self.rule(119)
    tree = ParseTree( NonTerminal(119, self.getAtomString(119)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 7:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(78, tracer) # imaginary
      tree.add(t)
      return tree
    elif rule == 25:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STRUCT_SPECIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 36:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(72, tracer) # bool
      tree.add(t)
      return tree
    elif rule == 57:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(24, tracer) # double
      tree.add(t)
      return tree
    elif rule == 73:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._ENUM_SPECIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 98:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._TYPEDEF_NAME(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 135:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(31, tracer) # signed
      tree.add(t)
      return tree
    elif rule == 144:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(4, tracer) # int
      tree.add(t)
      return tree
    elif rule == 161:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(77, tracer) # long
      tree.add(t)
      return tree
    elif rule == 169:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._UNION_SPECIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 185:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(17, tracer) # float
      tree.add(t)
      return tree
    elif rule == 205:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(98, tracer) # void
      tree.add(t)
      return tree
    elif rule == 247:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(105, tracer) # char
      tree.add(t)
      return tree
    elif rule == 274:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(18, tracer) # unsigned
      tree.add(t)
      return tree
    elif rule == 312:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(113, tracer) # short
      tree.add(t)
      return tree
    elif rule == 394:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(51, tracer) # complex
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _ELSE_IF_STATEMENT_LIST(self, depth=0, tracer=None):
    rule = self.rule(120)
    tree = ParseTree( NonTerminal(120, self.getAtomString(120)), tracer )
    tree.list = False
    if self.sym == None:
      return tree
    if rule == 122:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN39(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _INITIALIZER_LIST_ITEM(self, depth=0, tracer=None):
    rule = self.rule(121)
    tree = ParseTree( NonTerminal(121, self.getAtomString(121)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 80:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(63, tracer) # integer_constant
      tree.add(t)
      return tree
    elif rule == 338:
      tree.astTransform = AstTransformNodeCreator('Initialization', {'designation': 0, 'initializer': 1})
      subtree = self.__GEN14(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self._INITIALIZER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [53, 97, 32, 63, 7, 35, 16, 8, 14, 10, 66, 25, 110, 83, 5, 50]:
      tree.astTransform = AstTransformNodeCreator('Initialization', {'designation': 0, 'initializer': 1})
      subtree = self.__GEN14(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self._INITIALIZER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN37(self, depth=0, tracer=None):
    rule = self.rule(122)
    tree = ParseTree( NonTerminal(122, self.getAtomString(122)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [2, 4, 6, 87, 63, 10, 11, 14, 16, 17, 56, 35, 24, 27, 110, 31, 32, 34, 8, 18, 115, 72, 50, 57, 47, 49, 51, 7, 53, 86, 78, 66, 64, 65, 111, 76, 77, 25, 74, 94, 83, 84, 91, 92, 23, 95, 30, 97, 98, 68, 58, 15, 104, 105, 103, 42, 3, 113]):
      return tree
    if self.sym == None:
      return tree
    if rule == 264:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._ELSE_IF_STATEMENT_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _TYPE_QUALIFIER_LIST_OPT(self, depth=0, tracer=None):
    rule = self.rule(123)
    tree = ParseTree( NonTerminal(123, self.getAtomString(123)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [102, 1, 83, 79, 111, 16, 107, 7]):
      return tree
    if self.sym == None:
      return tree
    if rule == 268:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN25(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _TYPE_QUALIFIER(self, depth=0, tracer=None):
    rule = self.rule(124)
    tree = ParseTree( NonTerminal(124, self.getAtomString(124)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 184:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(3, tracer) # restrict
      tree.add(t)
      return tree
    elif rule == 232:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(15, tracer) # const
      tree.add(t)
      return tree
    elif rule == 243:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(2, tracer) # volatile
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _TOKEN(self, depth=0, tracer=None):
    rule = self.rule(125)
    tree = ParseTree( NonTerminal(125, self.getAtomString(125)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 269:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(16, tracer) # identifier
      tree.add(t)
      return tree
    elif rule == 275:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._KEYWORD(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 277:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PUNCTUATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 295:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(10, tracer) # string_literal
      tree.add(t)
      return tree
    elif rule == 337:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(70, tracer) # pp_number
      tree.add(t)
      return tree
    elif rule == 346:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._CONSTANT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _TYPEDEF_NAME(self, depth=0, tracer=None):
    rule = self.rule(126)
    tree = ParseTree( NonTerminal(126, self.getAtomString(126)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 115:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(104, tracer) # typedef_identifier
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _FUNCTION_SPECIFIER(self, depth=0, tracer=None):
    rule = self.rule(127)
    tree = ParseTree( NonTerminal(127, self.getAtomString(127)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 320:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(92, tracer) # inline
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _ELSE_STATEMENT(self, depth=0, tracer=None):
    rule = self.rule(128)
    tree = ParseTree( NonTerminal(128, self.getAtomString(128)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 28:
      tree.astTransform = AstTransformNodeCreator('Else', {'statement': 1})
      t = self.expect(65, tracer) # else
      tree.add(t)
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(11, tracer) # endif
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _PARAMETER_TYPE_LIST(self, depth=0, tracer=None):
    rule = self.rule(129)
    tree = ParseTree( NonTerminal(129, self.getAtomString(129)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 381:
      tree.astTransform = AstTransformNodeCreator('ParameterTypeList', {'parameter_declarations': 0, 'va_args': 1})
      subtree = self.__GEN27(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN29(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _TRANSLATION_UNIT(self, depth=0, tracer=None):
    rule = self.rule(130)
    tree = ParseTree( NonTerminal(130, self.getAtomString(130)), tracer )
    tree.list = False
    if self.sym == None:
      return tree
    if rule == 210:
      tree.astTransform = AstTransformNodeCreator('TranslationUnit', {'external_declarations': 0})
      subtree = self.__GEN0(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN9(self, depth=0, tracer=None):
    rule = self.rule(131)
    tree = ParseTree( NonTerminal(131, self.getAtomString(131)), tracer )
    tree.list = 'slist'
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 258:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._INIT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN10(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [16, 107, 7]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._INIT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN10(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _STRUCT_OR_UNION_BODY(self, depth=0, tracer=None):
    rule = self.rule(132)
    tree = ParseTree( NonTerminal(132, self.getAtomString(132)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 333:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(74, tracer) # lbrace
      tree.add(t)
      subtree = self.__GEN17(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(30, tracer) # rbrace
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN10(self, depth=0, tracer=None):
    rule = self.rule(133)
    tree = ParseTree( NonTerminal(133, self.getAtomString(133)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in [95]):
      return tree
    if self.sym == None:
      return tree
    if rule == 240:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(102, tracer) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self._INIT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN10(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _EXTERNAL_DECLARATION(self, depth=0, tracer=None):
    rule = self.rule(134)
    tree = ParseTree( NonTerminal(134, self.getAtomString(134)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 26:
      tree.astTransform = AstTransformNodeCreator('ExternalDeclaration', {'declarations': 2, 'declaration_specifiers': 1})
      t = self.expect(112, tracer) # external_declaration_hint
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
  def _POINTER_OPT(self, depth=0, tracer=None):
    rule = self.rule(135)
    tree = ParseTree( NonTerminal(135, self.getAtomString(135)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [102, 1, 79, 16, 107, 7]):
      return tree
    if self.sym == None:
      return tree
    if rule == 97:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._POINTER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _ENUMERATOR(self, depth=0, tracer=None):
    rule = self.rule(136)
    tree = ParseTree( NonTerminal(136, self.getAtomString(136)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 88:
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
  def _SPECIFIER_QUALIFIER(self, depth=0, tracer=None):
    rule = self.rule(138)
    tree = ParseTree( NonTerminal(138, self.getAtomString(138)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 77:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._TYPE_QUALIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 362:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._TYPE_SPECIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _POINTER_SUB(self, depth=0, tracer=None):
    rule = self.rule(139)
    tree = ParseTree( NonTerminal(139, self.getAtomString(139)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 87:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(83, tracer) # asterisk
      tree.add(t)
      subtree = self._TYPE_QUALIFIER_LIST_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN18(self, depth=0, tracer=None):
    rule = self.rule(140)
    tree = ParseTree( NonTerminal(140, self.getAtomString(140)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [13, 16, 83, 107, 7]):
      return tree
    if self.sym == None:
      return tree
    if rule == 248:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._SPECIFIER_QUALIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN18(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _DIRECT_DECLARATOR_MODIFIER_LIST_OPT(self, depth=0, tracer=None):
    rule = self.rule(142)
    tree = ParseTree( NonTerminal(142, self.getAtomString(142)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [53, 97, 32, 16, 7, 63, 8, 10, 83, 66, 25, 110, 14, 35, 50, 57]):
      return tree
    if self.sym == None:
      return tree
    if rule == 48:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN26(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _DIRECT_DECLARATOR_SIZE(self, depth=0, tracer=None):
    rule = self.rule(143)
    tree = ParseTree( NonTerminal(143, self.getAtomString(143)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 90:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(83, tracer) # asterisk
      tree.add(t)
      return tree
    elif rule == 324:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [53, 97, 32, 7, 35, 63, 8, 14, 10, 66, 25, 110, 83, 16, 50, 57]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN31(self, depth=0, tracer=None):
    rule = self.rule(144)
    tree = ParseTree( NonTerminal(144, self.getAtomString(144)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 360:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(102, tracer) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self._IDENTIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN31(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _DECLARATOR_INITIALIZER(self, depth=0, tracer=None):
    rule = self.rule(145)
    tree = ParseTree( NonTerminal(145, self.getAtomString(145)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 141:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(101, tracer) # assign
      tree.add(t)
      subtree = self._INITIALIZER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _STRUCT_DECLARATOR(self, depth=0, tracer=None):
    rule = self.rule(146)
    tree = ParseTree( NonTerminal(146, self.getAtomString(146)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 183:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN21(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 237:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STRUCT_DECLARATOR_BODY(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [16, 107, 7]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN21(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN19(self, depth=0, tracer=None):
    rule = self.rule(147)
    tree = ParseTree( NonTerminal(147, self.getAtomString(147)), tracer )
    tree.list = 'slist'
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 121:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STRUCT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN20(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [16, 107, 7]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STRUCT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN20(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _BLOCK_ITEM(self, depth=0, tracer=None):
    rule = self.rule(148)
    tree = ParseTree( NonTerminal(148, self.getAtomString(148)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 102:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DECLARATION(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 290:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [53, 97, 32, 7, 35, 63, 8, 14, 10, 66, 25, 110, 83, 16, 50, 57]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN20(self, depth=0, tracer=None):
    rule = self.rule(149)
    tree = ParseTree( NonTerminal(149, self.getAtomString(149)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in [95]):
      return tree
    if self.sym == None:
      return tree
    if rule == 265:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(102, tracer) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self._STRUCT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN20(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _DECLARATION_SPECIFIER(self, depth=0, tracer=None):
    rule = self.rule(151)
    tree = ParseTree( NonTerminal(151, self.getAtomString(151)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 178:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._TYPE_QUALIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 194:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._FUNCTION_SPECIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 251:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._TYPE_SPECIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 409:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STORAGE_CLASS_SPECIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _ELSE_IF_STATEMENT(self, depth=0, tracer=None):
    rule = self.rule(152)
    tree = ParseTree( NonTerminal(152, self.getAtomString(152)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 271:
      tree.astTransform = AstTransformNodeCreator('ElseIf', {'statement': 4, 'condition': 2})
      t = self.expect(59, tracer) # else_if
      tree.add(t)
      t = self.expect(7, tracer) # lparen
      tree.add(t)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(9, tracer) # rparen
      tree.add(t)
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(11, tracer) # endif
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN1(self, depth=0, tracer=None):
    rule = self.rule(153)
    tree = ParseTree( NonTerminal(153, self.getAtomString(153)), tracer )
    tree.list = 'mlist'
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 382:
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
  def __GEN2(self, depth=0, tracer=None):
    rule = self.rule(154)
    tree = ParseTree( NonTerminal(154, self.getAtomString(154)), tracer )
    tree.list = 'mlist'
    if self.sym != None and (self.sym.getId() in [1, 26, 102, 95, 89, 83, 7, 85, 16, 107, 79]):
      return tree
    if self.sym == None:
      return tree
    if rule == 56:
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
  def __GEN25(self, depth=0, tracer=None):
    rule = self.rule(155)
    tree = ParseTree( NonTerminal(155, self.getAtomString(155)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [102, 1, 83, 79, 111, 16, 107, 7]):
      return tree
    if self.sym == None:
      return tree
    if rule == 9:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._TYPE_QUALIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN25(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _STRUCT_SPECIFIER(self, depth=0, tracer=None):
    rule = self.rule(156)
    tree = ParseTree( NonTerminal(156, self.getAtomString(156)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 50:
      tree.astTransform = AstTransformNodeCreator('Struct', {'definition': 1})
      t = self.expect(58, tracer) # struct
      tree.add(t)
      subtree = self._STRUCT_OR_UNION_SUB(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _DECLARATION_LIST(self, depth=0, tracer=None):
    rule = self.rule(157)
    tree = ParseTree( NonTerminal(157, self.getAtomString(157)), tracer )
    tree.list = False
    if self.sym == None:
      return tree
    if rule == 104:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN7(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN23(self, depth=0, tracer=None):
    rule = self.rule(158)
    tree = ParseTree( NonTerminal(158, self.getAtomString(158)), tracer )
    tree.list = 'slist'
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 147:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._ENUMERATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN24(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _INITIALIZER(self, depth=0, tracer=None):
    rule = self.rule(159)
    tree = ParseTree( NonTerminal(159, self.getAtomString(159)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 117:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(74, tracer) # lbrace
      tree.add(t)
      subtree = self.__GEN12(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self._TRAILING_COMMA_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(30, tracer) # rbrace
      tree.add(t)
      return tree
    elif rule == 412:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__EXPR_SANS_COMMA(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [53, 97, 32, 63, 7, 35, 16, 8, 14, 10, 66, 25, 110, 83, 5, 50]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__EXPR_SANS_COMMA(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _LABELED_STATEMENT(self, depth=0, tracer=None):
    rule = self.rule(160)
    tree = ParseTree( NonTerminal(160, self.getAtomString(160)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 29:
      tree.astTransform = AstTransformNodeCreator('Case', {'expr': 1, 'statement': 3})
      t = self.expect(103, tracer) # case
      tree.add(t)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(13, tracer) # colon
      tree.add(t)
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 195:
      tree.astTransform = AstTransformNodeCreator('Label', {'name': 0, 'statement': 1})
      t = self.expect(115, tracer) # label_hint
      tree.add(t)
      t = self.expect(16, tracer) # identifier
      tree.add(t)
      t = self.expect(13, tracer) # colon
      tree.add(t)
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 391:
      tree.astTransform = AstTransformNodeCreator('DefaultCase', {'statement': 2})
      t = self.expect(86, tracer) # default
      tree.add(t)
      t = self.expect(13, tracer) # colon
      tree.add(t)
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _UNION_SPECIFIER(self, depth=0, tracer=None):
    rule = self.rule(161)
    tree = ParseTree( NonTerminal(161, self.getAtomString(161)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 228:
      tree.astTransform = AstTransformNodeCreator('Union', {'definition': 1})
      t = self.expect(42, tracer) # union
      tree.add(t)
      subtree = self._STRUCT_OR_UNION_SUB(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _TYPE_NAME(self, depth=0, tracer=None):
    rule = self.rule(162)
    tree = ParseTree( NonTerminal(162, self.getAtomString(162)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 82:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(105, tracer) # char
      tree.add(t)
      return tree
    elif rule == 133:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(4, tracer) # int
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _EXTERNAL_DECLARATION_SUB(self, depth=0, tracer=None):
    rule = self.rule(163)
    tree = ParseTree( NonTerminal(163, self.getAtomString(163)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 35:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN3(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(95, tracer) # semi
      tree.add(t)
      return tree
    elif rule == 59:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._EXTERNAL_FUNCTION(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _PARAMETER_DECLARATION_SUB(self, depth=0, tracer=None):
    rule = self.rule(164)
    tree = ParseTree( NonTerminal(164, self.getAtomString(164)), tracer )
    tree.list = False
    if self.sym == None:
      return tree
    if rule == 171:
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
    elif self.sym.getId() in [16, 107, 7]:
      tree.astTransform = AstTransformNodeCreator('ParameterSub', {'name_and_size': 1, 'pointer': 0})
      subtree = self._POINTER_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self._PARAMETER_DECLARATION_SUB_SUB(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    elif self.sym.getId() in [1, 7, -1]:
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
  def _ENUM_SPECIFIER(self, depth=0, tracer=None):
    rule = self.rule(165)
    tree = ParseTree( NonTerminal(165, self.getAtomString(165)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 256:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(87, tracer) # enum
      tree.add(t)
      subtree = self._ENUM_SPECIFIER_SUB(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN3(self, depth=0, tracer=None):
    rule = self.rule(166)
    tree = ParseTree( NonTerminal(166, self.getAtomString(166)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in [95]):
      return tree
    if self.sym == None:
      return tree
    if rule == 166:
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
  def _EXTERNAL_FUNCTION(self, depth=0, tracer=None):
    rule = self.rule(167)
    tree = ParseTree( NonTerminal(167, self.getAtomString(167)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 376:
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
  def _STRUCT_DECLARATOR_BODY(self, depth=0, tracer=None):
    rule = self.rule(168)
    tree = ParseTree( NonTerminal(168, self.getAtomString(168)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 406:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(13, tracer) # colon
      tree.add(t)
      subtree = self._DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN0(self, depth=0, tracer=None):
    rule = self.rule(169)
    tree = ParseTree( NonTerminal(169, self.getAtomString(169)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [-1]):
      return tree
    if self.sym == None:
      return tree
    if rule == 38:
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
  def _MISC(self, depth=0, tracer=None):
    rule = self.rule(170)
    tree = ParseTree( NonTerminal(170, self.getAtomString(170)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 216:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(109, tracer) # universal_character_name
      tree.add(t)
      return tree
    elif rule == 284:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(11, tracer) # endif
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN12(self, depth=0, tracer=None):
    rule = self.rule(171)
    tree = ParseTree( NonTerminal(171, self.getAtomString(171)), tracer )
    tree.list = 'slist'
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 299:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._INITIALIZER_LIST_ITEM(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN13(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [53, 97, 32, 63, 7, 35, 16, 8, 14, 10, 66, 25, 110, 83, 5, 50]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._INITIALIZER_LIST_ITEM(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN13(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN13(self, depth=0, tracer=None):
    rule = self.rule(172)
    tree = ParseTree( NonTerminal(172, self.getAtomString(172)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in [67]):
      return tree
    if self.sym == None:
      return tree
    if rule == 308:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(102, tracer) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self._INITIALIZER_LIST_ITEM(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN13(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _CONSTANT(self, depth=0, tracer=None):
    rule = self.rule(173)
    tree = ParseTree( NonTerminal(173, self.getAtomString(173)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 51:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(63, tracer) # integer_constant
      tree.add(t)
      return tree
    elif rule == 107:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(35, tracer) # enumeration_constant
      tree.add(t)
      return tree
    elif rule == 181:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(8, tracer) # decimal_floating_constant
      tree.add(t)
      return tree
    elif rule == 213:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(110, tracer) # character_constant
      tree.add(t)
      return tree
    elif rule == 302:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(14, tracer) # floating_constant
      tree.add(t)
      return tree
    elif rule == 383:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(66, tracer) # hexadecimal_floating_constant
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN21(self, depth=0, tracer=None):
    rule = self.rule(174)
    tree = ParseTree( NonTerminal(174, self.getAtomString(174)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [102, 95]):
      return tree
    if self.sym == None:
      return tree
    if rule == 319:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STRUCT_DECLARATOR_BODY(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _FOR_INIT(self, depth=0, tracer=None):
    rule = self.rule(175)
    tree = ParseTree( NonTerminal(175, self.getAtomString(175)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [95]):
      return tree
    if self.sym == None:
      return tree
    if rule == 126:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 197:
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
    elif self.sym.getId() in [53, 97, 32, 7, 35, 63, 8, 14, 10, 66, 25, 110, 83, 16, 50, 57]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    return tree
  def _FOR_COND(self, depth=0, tracer=None):
    rule = self.rule(176)
    tree = ParseTree( NonTerminal(176, self.getAtomString(176)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 136:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(95, tracer) # semi
      tree.add(t)
      subtree = self._EXPRESSION_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN4(self, depth=0, tracer=None):
    rule = self.rule(177)
    tree = ParseTree( NonTerminal(177, self.getAtomString(177)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in [95]):
      return tree
    if self.sym == None:
      return tree
    if rule == 188:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(102, tracer) # comma
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
  def __GEN8(self, depth=0, tracer=None):
    rule = self.rule(178)
    tree = ParseTree( NonTerminal(178, self.getAtomString(178)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [95]):
      return tree
    if self.sym == None:
      return tree
    if rule == 198:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._INIT_DECLARATOR_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [16, 107, 7]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._INIT_DECLARATOR_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    return tree
  def _KEYWORD(self, depth=0, tracer=None):
    rule = self.rule(179)
    tree = ParseTree( NonTerminal(179, self.getAtomString(179)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 2:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(50, tracer) # sizeof
      tree.add(t)
      return tree
    elif rule == 6:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(58, tracer) # struct
      tree.add(t)
      return tree
    elif rule == 12:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(94, tracer) # auto
      tree.add(t)
      return tree
    elif rule == 15:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(87, tracer) # enum
      tree.add(t)
      return tree
    elif rule == 34:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(105, tracer) # char
      tree.add(t)
      return tree
    elif rule == 41:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(56, tracer) # typedef
      tree.add(t)
      return tree
    elif rule == 43:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(72, tracer) # bool
      tree.add(t)
      return tree
    elif rule == 54:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(27, tracer) # goto
      tree.add(t)
      return tree
    elif rule == 55:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(68, tracer) # for
      tree.add(t)
      return tree
    elif rule == 58:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(42, tracer) # union
      tree.add(t)
      return tree
    elif rule == 65:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(103, tracer) # case
      tree.add(t)
      return tree
    elif rule == 84:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(18, tracer) # unsigned
      tree.add(t)
      return tree
    elif rule == 93:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(98, tracer) # void
      tree.add(t)
      return tree
    elif rule == 95:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(6, tracer) # if
      tree.add(t)
      return tree
    elif rule == 114:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(23, tracer) # do
      tree.add(t)
      return tree
    elif rule == 116:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(2, tracer) # volatile
      tree.add(t)
      return tree
    elif rule == 127:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(65, tracer) # else
      tree.add(t)
      return tree
    elif rule == 160:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(91, tracer) # register
      tree.add(t)
      return tree
    elif rule == 170:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(64, tracer) # extern
      tree.add(t)
      return tree
    elif rule == 174:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(4, tracer) # int
      tree.add(t)
      return tree
    elif rule == 176:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(111, tracer) # static
      tree.add(t)
      return tree
    elif rule == 180:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(17, tracer) # float
      tree.add(t)
      return tree
    elif rule == 191:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(47, tracer) # break
      tree.add(t)
      return tree
    elif rule == 276:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(78, tracer) # imaginary
      tree.add(t)
      return tree
    elif rule == 297:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(3, tracer) # restrict
      tree.add(t)
      return tree
    elif rule == 309:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(24, tracer) # double
      tree.add(t)
      return tree
    elif rule == 317:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(49, tracer) # return
      tree.add(t)
      return tree
    elif rule == 331:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(113, tracer) # short
      tree.add(t)
      return tree
    elif rule == 334:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(92, tracer) # inline
      tree.add(t)
      return tree
    elif rule == 340:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(34, tracer) # continue
      tree.add(t)
      return tree
    elif rule == 345:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(76, tracer) # switch
      tree.add(t)
      return tree
    elif rule == 348:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(86, tracer) # default
      tree.add(t)
      return tree
    elif rule == 351:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(31, tracer) # signed
      tree.add(t)
      return tree
    elif rule == 365:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(84, tracer) # while
      tree.add(t)
      return tree
    elif rule == 373:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(15, tracer) # const
      tree.add(t)
      return tree
    elif rule == 411:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(77, tracer) # long
      tree.add(t)
      return tree
    elif rule == 418:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(51, tracer) # complex
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _TRAILING_COMMA_OPT(self, depth=0, tracer=None):
    rule = self.rule(180)
    tree = ParseTree( NonTerminal(180, self.getAtomString(180)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [30]):
      return tree
    if self.sym == None:
      return tree
    if rule == 294:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(67, tracer) # trailing_comma
      tree.add(t)
      return tree
    return tree
  def __GEN41(self, depth=0, tracer=None):
    rule = self.rule(181)
    tree = ParseTree( NonTerminal(181, self.getAtomString(181)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 119:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(102, tracer) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self.__EXPR_SANS_COMMA(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN41(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _PUNCTUATOR(self, depth=0, tracer=None):
    rule = self.rule(182)
    tree = ParseTree( NonTerminal(182, self.getAtomString(182)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 1:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(19, tracer) # elipsis
      tree.add(t)
      return tree
    elif rule == 8:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(12, tracer) # gt
      tree.add(t)
      return tree
    elif rule == 10:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(38, tracer) # poundpound
      tree.add(t)
      return tree
    elif rule == 22:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(99, tracer) # arrow
      tree.add(t)
      return tree
    elif rule == 23:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(25, tracer) # incr
      tree.add(t)
      return tree
    elif rule == 31:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(28, tracer) # div
      tree.add(t)
      return tree
    elif rule == 47:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(102, tracer) # comma
      tree.add(t)
      return tree
    elif rule == 52:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(13, tracer) # colon
      tree.add(t)
      return tree
    elif rule == 66:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(82, tracer) # modeq
      tree.add(t)
      return tree
    elif rule == 79:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(61, tracer) # lteq
      tree.add(t)
      return tree
    elif rule == 81:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(95, tracer) # semi
      tree.add(t)
      return tree
    elif rule == 83:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(80, tracer) # muleq
      tree.add(t)
      return tree
    elif rule == 86:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(0, tracer) # mod
      tree.add(t)
      return tree
    elif rule == 89:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(43, tracer) # gteq
      tree.add(t)
      return tree
    elif rule == 91:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(96, tracer) # and
      tree.add(t)
      return tree
    elif rule == 96:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(74, tracer) # lbrace
      tree.add(t)
      return tree
    elif rule == 111:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(45, tracer) # bitxor
      tree.add(t)
      return tree
    elif rule == 154:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(46, tracer) # dot
      tree.add(t)
      return tree
    elif rule == 157:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(60, tracer) # neq
      tree.add(t)
      return tree
    elif rule == 164:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(75, tracer) # rshift
      tree.add(t)
      return tree
    elif rule == 192:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(44, tracer) # eq
      tree.add(t)
      return tree
    elif rule == 201:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(100, tracer) # bitor
      tree.add(t)
      return tree
    elif rule == 234:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(73, tracer) # addeq
      tree.add(t)
      return tree
    elif rule == 245:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(30, tracer) # rbrace
      tree.add(t)
      return tree
    elif rule == 257:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(71, tracer) # exclamation_point
      tree.add(t)
      return tree
    elif rule == 282:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(41, tracer) # bitandeq
      tree.add(t)
      return tree
    elif rule == 313:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(90, tracer) # ampersand
      tree.add(t)
      return tree
    elif rule == 314:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(101, tracer) # assign
      tree.add(t)
      return tree
    elif rule == 316:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(29, tracer) # bitoreq
      tree.add(t)
      return tree
    elif rule == 330:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(69, tracer) # pound
      tree.add(t)
      return tree
    elif rule == 341:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(36, tracer) # bitxoreq
      tree.add(t)
      return tree
    elif rule == 344:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(108, tracer) # tilde
      tree.add(t)
      return tree
    elif rule == 350:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(21, tracer) # rshifteq
      tree.add(t)
      return tree
    elif rule == 353:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(62, tracer) # questionmark
      tree.add(t)
      return tree
    elif rule == 363:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(97, tracer) # decr
      tree.add(t)
      return tree
    elif rule == 368:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(114, tracer) # lshift
      tree.add(t)
      return tree
    elif rule == 370:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(39, tracer) # rsquare
      tree.add(t)
      return tree
    elif rule == 374:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(7, tracer) # lparen
      tree.add(t)
      return tree
    elif rule == 385:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(54, tracer) # add
      tree.add(t)
      return tree
    elif rule == 387:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(48, tracer) # lshifteq
      tree.add(t)
      return tree
    elif rule == 388:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(20, tracer) # lt
      tree.add(t)
      return tree
    elif rule == 396:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(93, tracer) # subeq
      tree.add(t)
      return tree
    elif rule == 410:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(88, tracer) # sub
      tree.add(t)
      return tree
    elif rule == 417:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(9, tracer) # rparen
      tree.add(t)
      return tree
    elif rule == 420:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(33, tracer) # or
      tree.add(t)
      return tree
    elif rule == 422:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(37, tracer) # lsquare
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _PARAMETER_DECLARATION(self, depth=0, tracer=None):
    rule = self.rule(183)
    tree = ParseTree( NonTerminal(183, self.getAtomString(183)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 328:
      tree.astTransform = AstTransformNodeCreator('ParameterDeclaration', {'sub': 1, 'declaration_specifiers': 0})
      subtree = self.__GEN1(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN32(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN27(self, depth=0, tracer=None):
    rule = self.rule(184)
    tree = ParseTree( NonTerminal(184, self.getAtomString(184)), tracer )
    tree.list = 'slist'
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 318:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PARAMETER_DECLARATION(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN28(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN11(self, depth=0, tracer=None):
    rule = self.rule(185)
    tree = ParseTree( NonTerminal(185, self.getAtomString(185)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [102, 95]):
      return tree
    if self.sym == None:
      return tree
    if rule == 260:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DECLARATOR_INITIALIZER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN28(self, depth=0, tracer=None):
    rule = self.rule(186)
    tree = ParseTree( NonTerminal(186, self.getAtomString(186)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in [79]):
      return tree
    if self.sym == None:
      return tree
    if rule == 143:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(102, tracer) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self._PARAMETER_DECLARATION(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN28(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _DESIGNATION(self, depth=0, tracer=None):
    rule = self.rule(187)
    tree = ParseTree( NonTerminal(187, self.getAtomString(187)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 60:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN15(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(101, tracer) # assign
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _IDENTIFIER(self, depth=0, tracer=None):
    rule = self.rule(188)
    tree = ParseTree( NonTerminal(188, self.getAtomString(188)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 366:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(16, tracer) # identifier
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN14(self, depth=0, tracer=None):
    rule = self.rule(189)
    tree = ParseTree( NonTerminal(189, self.getAtomString(189)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [53, 74, 32, 63, 7, 35, 16, 8, 10, 14, 83, 66, 25, 110, 97, 5, 50]):
      return tree
    if self.sym == None:
      return tree
    if rule == 322:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DESIGNATION(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN33(self, depth=0, tracer=None):
    rule = self.rule(190)
    tree = ParseTree( NonTerminal(190, self.getAtomString(190)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [102, 79]):
      return tree
    if self.sym == None:
      return tree
    if rule == 110:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__DIRECT_ABSTRACT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [1, 7, -1]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__DIRECT_ABSTRACT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    return tree
  def _ENUM_SPECIFIER_SUB(self, depth=0, tracer=None):
    rule = self.rule(191)
    tree = ParseTree( NonTerminal(191, self.getAtomString(191)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 68:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._ENUM_SPECIFIER_BODY(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 226:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._IDENTIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN22(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN40(self, depth=0, tracer=None):
    rule = self.rule(192)
    tree = ParseTree( NonTerminal(192, self.getAtomString(192)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 118:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__EXPR_SANS_COMMA(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN41(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _EXTERNAL_DECLARATOR(self, depth=0, tracer=None):
    rule = self.rule(193)
    tree = ParseTree( NonTerminal(193, self.getAtomString(193)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 61:
      tree.astTransform = AstTransformNodeCreator('ExternalDeclarator', {'init_declarator': 1})
      t = self.expect(85, tracer) # declarator_hint
      tree.add(t)
      subtree = self.__GEN6(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _ENUM_SPECIFIER_BODY(self, depth=0, tracer=None):
    rule = self.rule(194)
    tree = ParseTree( NonTerminal(194, self.getAtomString(194)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 46:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(74, tracer) # lbrace
      tree.add(t)
      subtree = self.__GEN23(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self._TRAILING_COMMA_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(30, tracer) # rbrace
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _VA_ARGS(self, depth=0, tracer=None):
    rule = self.rule(195)
    tree = ParseTree( NonTerminal(195, self.getAtomString(195)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 120:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(79, tracer) # comma_va_args
      tree.add(t)
      t = self.expect(19, tracer) # elipsis
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN29(self, depth=0, tracer=None):
    rule = self.rule(196)
    tree = ParseTree( NonTerminal(196, self.getAtomString(196)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 336:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._VA_ARGS(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _EXTERNAL_DECLARATION_SUB_SUB(self, depth=0, tracer=None):
    rule = self.rule(197)
    tree = ParseTree( NonTerminal(197, self.getAtomString(197)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 222:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._EXTERNAL_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 356:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._EXTERNAL_PROTOTYPE(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _EXTERNAL_PROTOTYPE(self, depth=0, tracer=None):
    rule = self.rule(198)
    tree = ParseTree( NonTerminal(198, self.getAtomString(198)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 255:
      tree.astTransform = AstTransformNodeCreator('FunctionPrototype', {'declaration_list': 2, 'declarator': 1})
      t = self.expect(89, tracer) # function_prototype_hint
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
  def __GEN22(self, depth=0, tracer=None):
    rule = self.rule(199)
    tree = ParseTree( NonTerminal(199, self.getAtomString(199)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [1, 13, 56, 4, 87, 64, 77, 89, 111, 17, 79, 2, 94, 24, 3, 26, 58, 91, 31, 78, 104, 95, 113, 98, 18, 102, 15, 105, 72, 92, 51, 42, 85, 83, 16, 107, 7]):
      return tree
    if self.sym == None:
      return tree
    if rule == 414:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._ENUM_SPECIFIER_BODY(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN15(self, depth=0, tracer=None):
    rule = self.rule(200)
    tree = ParseTree( NonTerminal(200, self.getAtomString(200)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [101]):
      return tree
    if self.sym == None:
      return tree
    if rule == 179:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DESIGNATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN15(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _SELECTION_STATEMENT(self, depth=0, tracer=None):
    rule = self.rule(201)
    tree = ParseTree( NonTerminal(201, self.getAtomString(201)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 150:
      tree.astTransform = AstTransformNodeCreator('If', {'elseif': 6, 'statement': 4, 'condition': 2, 'else': 7})
      t = self.expect(6, tracer) # if
      tree.add(t)
      t = self.expect(7, tracer) # lparen
      tree.add(t)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(9, tracer) # rparen
      tree.add(t)
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(11, tracer) # endif
      tree.add(t)
      subtree = self.__GEN37(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN38(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 355:
      tree.astTransform = AstTransformNodeCreator('Switch', {'expr': 2, 'statment': 4})
      t = self.expect(76, tracer) # switch
      tree.add(t)
      t = self.expect(7, tracer) # lparen
      tree.add(t)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(9, tracer) # rparen
      tree.add(t)
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _DESIGNATOR(self, depth=0, tracer=None):
    rule = self.rule(202)
    tree = ParseTree( NonTerminal(202, self.getAtomString(202)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 20:
      tree.astTransform = AstTransformNodeCreator('ArrayAccess', {'index': 1})
      t = self.expect(37, tracer) # lsquare
      tree.add(t)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(39, tracer) # rsquare
      tree.add(t)
      return tree
    elif rule == 401:
      tree.astTransform = AstTransformNodeCreator('MemberAccess', {'name': 1})
      t = self.expect(46, tracer) # dot
      tree.add(t)
      t = self.expect(16, tracer) # identifier
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _DECLARATOR(self, depth=0, tracer=None):
    rule = self.rule(203)
    tree = ParseTree( NonTerminal(203, self.getAtomString(203)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 33:
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
    elif self.sym.getId() in [16, 107, 7]:
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
  def _INIT_DECLARATOR_LIST(self, depth=0, tracer=None):
    rule = self.rule(204)
    tree = ParseTree( NonTerminal(204, self.getAtomString(204)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 408:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN9(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [16, 107, 7]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN9(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _POINTER(self, depth=0, tracer=None):
    rule = self.rule(205)
    tree = ParseTree( NonTerminal(205, self.getAtomString(205)), tracer )
    tree.list = False
    if self.sym == None:
      return tree
    if rule == 289:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN34(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN5(self, depth=0, tracer=None):
    rule = self.rule(206)
    tree = ParseTree( NonTerminal(206, self.getAtomString(206)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [74, 95, 102]):
      return tree
    if self.sym == None:
      return tree
    if rule == 134:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DECLARATION_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _JUMP_STATEMENT(self, depth=0, tracer=None):
    rule = self.rule(207)
    tree = ParseTree( NonTerminal(207, self.getAtomString(207)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 5:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(47, tracer) # break
      tree.add(t)
      t = self.expect(95, tracer) # semi
      tree.add(t)
      return tree
    elif rule == 202:
      tree.astTransform = AstTransformNodeCreator('Goto', {'name': 1})
      t = self.expect(27, tracer) # goto
      tree.add(t)
      t = self.expect(16, tracer) # identifier
      tree.add(t)
      t = self.expect(95, tracer) # semi
      tree.add(t)
      return tree
    elif rule == 310:
      tree.astTransform = AstTransformNodeCreator('Return', {'expr': 1})
      t = self.expect(49, tracer) # return
      tree.add(t)
      subtree = self._EXPRESSION_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(95, tracer) # semi
      tree.add(t)
      return tree
    elif rule == 359:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(34, tracer) # continue
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _STRUCT_OR_UNION_SUB(self, depth=0, tracer=None):
    rule = self.rule(208)
    tree = ParseTree( NonTerminal(208, self.getAtomString(208)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 124:
      tree.astTransform = AstTransformNodeCreator('StructOrUnion', {'body': 1, 'name': 0})
      t = self.expect(16, tracer) # identifier
      tree.add(t)
      subtree = self.__GEN16(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 416:
      tree.astTransform = AstTransformNodeCreator('StructOrUnion', {'body': 0})
      subtree = self._STRUCT_OR_UNION_BODY(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN30(self, depth=0, tracer=None):
    rule = self.rule(210)
    tree = ParseTree( NonTerminal(210, self.getAtomString(210)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 358:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._IDENTIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN31(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _DIRECT_DECLARATOR_MODIFIER(self, depth=0, tracer=None):
    rule = self.rule(211)
    tree = ParseTree( NonTerminal(211, self.getAtomString(211)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 21:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._TYPE_QUALIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 211:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(111, tracer) # static
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN34(self, depth=0, tracer=None):
    rule = self.rule(212)
    tree = ParseTree( NonTerminal(212, self.getAtomString(212)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [102, 1, 7, 16, 107, 79]):
      return tree
    if self.sym == None:
      return tree
    if rule == 145:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._POINTER_SUB(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN34(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN24(self, depth=0, tracer=None):
    rule = self.rule(213)
    tree = ParseTree( NonTerminal(213, self.getAtomString(213)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in [67]):
      return tree
    if self.sym == None:
      return tree
    if rule == 92:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(102, tracer) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self._ENUMERATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN24(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _STRUCT_DECLARATION(self, depth=0, tracer=None):
    rule = self.rule(214)
    tree = ParseTree( NonTerminal(214, self.getAtomString(214)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 42:
      tree.astTransform = AstTransformNodeCreator('StructOrUnionDeclaration', {'specifier_qualifiers': 0, 'declarators': 1})
      subtree = self.__GEN18(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN19(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(95, tracer) # semi
      tree.add(t)
      return tree
    elif self.sym.getId() in [16, 107, 7]:
      tree.astTransform = AstTransformNodeCreator('StructOrUnionDeclaration', {'specifier_qualifiers': 0, 'declarators': 1})
      subtree = self.__GEN18(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN19(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(95, tracer) ) # semi
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _FOR_INCR(self, depth=0, tracer=None):
    rule = self.rule(215)
    tree = ParseTree( NonTerminal(215, self.getAtomString(215)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [9]):
      return tree
    if self.sym == None:
      return tree
    if rule == 230:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(95, tracer) # semi
      tree.add(t)
      subtree = self._EXPRESSION_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _INIT_DECLARATOR(self, depth=0, tracer=None):
    rule = self.rule(216)
    tree = ParseTree( NonTerminal(216, self.getAtomString(216)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 203:
      tree.astTransform = AstTransformNodeCreator('InitDeclarator', {'initializer': 1, 'declarator': 0})
      subtree = self._DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN11(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [16, 107, 7]:
      tree.astTransform = AstTransformNodeCreator('InitDeclarator', {'initializer': 1, 'declarator': 0})
      subtree = self._DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN11(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN6(self, depth=0, tracer=None):
    rule = self.rule(217)
    tree = ParseTree( NonTerminal(217, self.getAtomString(217)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [102, 95]):
      return tree
    if self.sym == None:
      return tree
    if rule == 167:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._INIT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [16, 107, 7]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._INIT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    return tree
  def __GEN26(self, depth=0, tracer=None):
    rule = self.rule(218)
    tree = ParseTree( NonTerminal(218, self.getAtomString(218)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [53, 97, 32, 7, 8, 63, 14, 83, 66, 50, 25, 110, 10, 16, 35, 57]):
      return tree
    if self.sym == None:
      return tree
    if rule == 292:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DIRECT_DECLARATOR_MODIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN26(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN38(self, depth=0, tracer=None):
    rule = self.rule(219)
    tree = ParseTree( NonTerminal(219, self.getAtomString(219)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [2, 4, 6, 87, 63, 10, 11, 14, 16, 17, 56, 35, 24, 27, 110, 31, 32, 34, 8, 18, 115, 72, 50, 57, 47, 49, 51, 7, 53, 86, 78, 66, 64, 111, 76, 77, 25, 74, 94, 83, 84, 91, 92, 23, 95, 30, 97, 98, 68, 58, 15, 104, 105, 103, 42, 3, 113]):
      return tree
    if self.sym == None:
      return tree
    if rule == 231:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._ELSE_STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _DIRECT_ABSTRACT_DECLARATOR_EXPR(self, depth=0, tracer=None):
    rule = self.rule(220)
    tree = ParseTree( NonTerminal(220, self.getAtomString(220)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 235:
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
    elif rule == 369:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(83, tracer) # asterisk
      tree.add(t)
      return tree
    elif self.sym.getId() in [53, 97, 32, 7, 35, 63, 8, 14, 10, 66, 25, 110, 83, 16, 50, 57]:
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
  def _ENUMERATION_CONSTANT(self, depth=0, tracer=None):
    rule = self.rule(221)
    tree = ParseTree( NonTerminal(221, self.getAtomString(221)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 172:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(16, tracer) # identifier
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _BLOCK_ITEM_LIST(self, depth=0, tracer=None):
    rule = self.rule(222)
    tree = ParseTree( NonTerminal(222, self.getAtomString(222)), tracer )
    tree.list = False
    if self.sym == None:
      return tree
    if rule == 403:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN36(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [53, 97, 32, 7, 35, 63, 8, 14, 10, 66, 25, 110, 83, 16, 50, 57]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN36(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _ENUMERATOR_ASSIGNMENT(self, depth=0, tracer=None):
    rule = self.rule(223)
    tree = ParseTree( NonTerminal(223, self.getAtomString(223)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [102, 67]):
      return tree
    if self.sym == None:
      return tree
    if rule == 227:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(101, tracer) # assign
      tree.add(t)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _STATIC_OPT(self, depth=0, tracer=None):
    rule = self.rule(224)
    tree = ParseTree( NonTerminal(224, self.getAtomString(224)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [53, 97, 32, 7, 63, 8, 10, 14, 66, 50, 25, 110, 16, 83, 35, 57]):
      return tree
    if self.sym == None:
      return tree
    if rule == 354:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(111, tracer) # static
      tree.add(t)
      return tree
    return tree
  def _DIRECT_DECLARATOR_PARAMETER_LIST(self, depth=0, tracer=None):
    rule = self.rule(225)
    tree = ParseTree( NonTerminal(225, self.getAtomString(225)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 14:
      tree.astTransform = AstTransformNodeCreator('ParameterList', {'identifiers': 0})
      subtree = self.__GEN30(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 395:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PARAMETER_TYPE_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _EXPRESSION_OPT(self, depth=0, tracer=None):
    rule = self.rule(226)
    tree = ParseTree( NonTerminal(226, self.getAtomString(226)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [9, 95]):
      return tree
    if self.sym == None:
      return tree
    if rule == 242:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [53, 97, 32, 7, 35, 63, 8, 14, 10, 66, 25, 110, 83, 16, 50, 57]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    return tree
  def __GEN35(self, depth=0, tracer=None):
    rule = self.rule(227)
    tree = ParseTree( NonTerminal(227, self.getAtomString(227)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [30]):
      return tree
    if self.sym == None:
      return tree
    if rule == 293:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._BLOCK_ITEM_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [53, 97, 32, 7, 35, 63, 8, 14, 10, 66, 25, 110, 83, 16, 50, 57]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._BLOCK_ITEM_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    return tree
  def _DECLARATION(self, depth=0, tracer=None):
    rule = self.rule(228)
    tree = ParseTree( NonTerminal(228, self.getAtomString(228)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 49:
      tree.astTransform = AstTransformNodeCreator('Declaration', {'init_declarators': 1, 'declaration_specifiers': 0})
      subtree = self.__GEN1(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN8(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(95, tracer) # semi
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN7(self, depth=0, tracer=None):
    rule = self.rule(229)
    tree = ParseTree( NonTerminal(229, self.getAtomString(229)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [74, 95, 102]):
      return tree
    if self.sym == None:
      return tree
    if rule == 246:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DECLARATION(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN7(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _ABSTRACT_DECLARATOR(self, depth=0, tracer=None):
    rule = self.rule(230)
    tree = ParseTree( NonTerminal(230, self.getAtomString(230)), tracer )
    tree.list = False
    if self.sym == None:
      return tree
    if rule == 372:
      tree.astTransform = AstTransformNodeCreator('AbstractDeclarator', {'direct_abstract_declarator': 1, 'pointer': 1})
      subtree = self._POINTER_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__DIRECT_ABSTRACT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [1, 7, -1]:
      tree.astTransform = AstTransformNodeCreator('AbstractDeclarator', {'direct_abstract_declarator': 1, 'pointer': 1})
      subtree = self._POINTER_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__DIRECT_ABSTRACT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _DIRECT_ABSTRACT_DECLARATOR_OPT(self, depth=0, tracer=None):
    rule = self.rule(231)
    tree = ParseTree( NonTerminal(231, self.getAtomString(231)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 307:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__DIRECT_ABSTRACT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [1, 7, -1]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__DIRECT_ABSTRACT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    return tree
  def __GEN36(self, depth=0, tracer=None):
    rule = self.rule(232)
    tree = ParseTree( NonTerminal(232, self.getAtomString(232)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [30]):
      return tree
    if self.sym == None:
      return tree
    if rule == 291:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._BLOCK_ITEM(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN36(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [53, 97, 32, 7, 35, 63, 8, 14, 10, 66, 25, 110, 83, 16, 50, 57]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._BLOCK_ITEM(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN36(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    return tree
  def __GEN39(self, depth=0, tracer=None):
    rule = self.rule(233)
    tree = ParseTree( NonTerminal(233, self.getAtomString(233)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [2, 4, 6, 87, 63, 10, 11, 14, 16, 17, 56, 35, 24, 27, 110, 31, 32, 34, 8, 18, 47, 72, 50, 57, 115, 49, 51, 7, 53, 86, 78, 66, 64, 65, 111, 76, 77, 25, 74, 94, 83, 84, 91, 92, 23, 95, 30, 97, 98, 68, 58, 15, 104, 105, 103, 42, 3, 113]):
      return tree
    if self.sym == None:
      return tree
    if rule == 272:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._ELSE_IF_STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN39(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN32(self, depth=0, tracer=None):
    rule = self.rule(234)
    tree = ParseTree( NonTerminal(234, self.getAtomString(234)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [102, 79]):
      return tree
    if self.sym == None:
      return tree
    if rule == 361:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PARAMETER_DECLARATION_SUB(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [16, 107, 7]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PARAMETER_DECLARATION_SUB(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    elif self.sym.getId() in [1, 7, -1]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PARAMETER_DECLARATION_SUB(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    return tree
  def _ITERATION_STATEMENT(self, depth=0, tracer=None):
    rule = self.rule(235)
    tree = ParseTree( NonTerminal(235, self.getAtomString(235)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 85:
      tree.astTransform = AstTransformNodeCreator('DoWhile', {'expr': 4, 'statement': 1})
      t = self.expect(23, tracer) # do
      tree.add(t)
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(84, tracer) # while
      tree.add(t)
      t = self.expect(7, tracer) # lparen
      tree.add(t)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(9, tracer) # rparen
      tree.add(t)
      t = self.expect(95, tracer) # semi
      tree.add(t)
      return tree
    elif rule == 397:
      tree.astTransform = AstTransformNodeCreator('For', {'init': 2, 'cond': 3, 'incr': 4, 'statement': 6})
      t = self.expect(68, tracer) # for
      tree.add(t)
      t = self.expect(7, tracer) # lparen
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
      t = self.expect(9, tracer) # rparen
      tree.add(t)
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 421:
      tree.astTransform = AstTransformNodeCreator('While', {'expr': 2, 'statement': 4})
      t = self.expect(84, tracer) # while
      tree.add(t)
      t = self.expect(7, tracer) # lparen
      tree.add(t)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(9, tracer) # rparen
      tree.add(t)
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN17(self, depth=0, tracer=None):
    rule = self.rule(236)
    tree = ParseTree( NonTerminal(236, self.getAtomString(236)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [30]):
      return tree
    if self.sym == None:
      return tree
    if rule == 74:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STRUCT_DECLARATION(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN17(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [16, 107, 7]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STRUCT_DECLARATION(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN17(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    return tree
  def _DIRECT_DECLARATOR_EXPR(self, depth=0, tracer=None):
    rule = self.rule(237)
    tree = ParseTree( NonTerminal(237, self.getAtomString(237)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 377:
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
    elif self.sym.getId() in [53, 97, 32, 7, 35, 63, 8, 14, 10, 66, 25, 110, 83, 16, 50, 57]:
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
  def _STATEMENT(self, depth=0, tracer=None):
    rule = self.rule(238)
    tree = ParseTree( NonTerminal(238, self.getAtomString(238)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 4:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._JUMP_STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 168:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._EXPRESSION_STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 298:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._ITERATION_STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 311:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._LABELED_STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 326:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._COMPOUND_STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 378:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._SELECTION_STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [53, 97, 32, 7, 35, 63, 8, 14, 10, 66, 25, 110, 83, 16, 50, 57]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._EXPRESSION_STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _PP(self, depth=0, tracer=None):
    rule = self.rule(239)
    tree = ParseTree( NonTerminal(239, self.getAtomString(239)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 0:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(55, tracer) # defined
      tree.add(t)
      return tree
    elif rule == 18:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(81, tracer) # defined_separator
      tree.add(t)
      return tree
    elif rule == 278:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(70, tracer) # pp_number
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _COMPOUND_STATEMENT(self, depth=0, tracer=None):
    rule = self.rule(240)
    tree = ParseTree( NonTerminal(240, self.getAtomString(240)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 263:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(74, tracer) # lbrace
      tree.add(t)
      subtree = self.__GEN35(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(30, tracer) # rbrace
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN42(self, depth=0, tracer=None):
    rule = self.rule(241)
    tree = ParseTree( NonTerminal(241, self.getAtomString(241)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 109:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PARAMETER_TYPE_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _PARAMETER_DECLARATION_SUB_SUB(self, depth=0, tracer=None):
    rule = self.rule(242)
    tree = ParseTree( NonTerminal(242, self.getAtomString(242)), tracer )
    tree.list = False
    if self.sym == None:
      return tree
    if rule == 286:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__DIRECT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 343:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN33(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [16, 107, 7]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__DIRECT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    elif self.sym.getId() in [1, 7, -1]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN33(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _EXPRESSION_STATEMENT(self, depth=0, tracer=None):
    rule = self.rule(243)
    tree = ParseTree( NonTerminal(243, self.getAtomString(243)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 158:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._EXPRESSION_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(95, tracer) # semi
      tree.add(t)
      return tree
    elif self.sym.getId() in [53, 97, 32, 7, 35, 63, 8, 14, 10, 66, 25, 110, 83, 16, 50, 57]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._EXPRESSION_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(95, tracer) ) # semi
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  infixBp0 = {
    0: 12000,
    7: 15000,
    12: 9000,
    20: 9000,
    21: 1000,
    25: 15000,
    28: 12000,
    29: 1000,
    32: 5000,
    33: 3000,
    36: 1000,
    37: 15000,
    41: 1000,
    43: 9000,
    44: 8000,
    45: 6000,
    46: 15000,
    48: 1000,
    54: 11000,
    60: 8000,
    61: 9000,
    62: 2000,
    73: 1000,
    74: 14000,
    75: 10000,
    80: 1000,
    82: 1000,
    83: 12000,
    88: 11000,
    93: 1000,
    96: 4000,
    97: 15000,
    99: 15000,
    100: 7000,
    101: 1000,
    102: 16000,
    106: 1000,
    114: 10000,
  }
  prefixBp0 = {
    25: 13000,
    32: 13000,
    40: 13000,
    52: 13000,
    83: 13000,
    88: 13000,
    97: 13000,
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
    tree = ParseTree( NonTerminal(209, '_expr') )
    if not self.sym:
      return tree
    if self.sym.getId() in [83]:
      tree.astTransform = AstTransformNodeCreator('Dereference', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(83, tracer) )
      tree.add( self.__EXPR( self.prefixBp0[83] ) )
      tree.isPrefix = True
    elif self.sym.getId() in [16]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      return self.expect( 16, tracer )
    elif self.sym.getId() in [10]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      return self.expect( 10, tracer )
    elif self.sym.getId() in [53]:
      tree.astTransform = AstTransformNodeCreator('TypeInitializion', {'type': 1, 'initializer': 4})
      tree.nudMorphemeCount = 3
      tree.add( self.expect(53, tracer) )
      tree.add( self._TYPE_NAME() )
      tree.add( self.expect(9, tracer) )
    elif self.sym.getId() in [50]:
      tree.astTransform = AstTransformNodeCreator('SizeOf', {'var': 1})
      tree.nudMorphemeCount = 1
      return self.expect( 50, tracer )
    elif self.sym.getId() in [16]:
      tree.astTransform = AstTransformNodeCreator('ArrayIndex', {'params': 2, 'name': 0})
      tree.nudMorphemeCount = 1
      return self.expect( 16, tracer )
    elif self.sym.getId() in [25]:
      tree.astTransform = AstTransformNodeCreator('PreIncr', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(25, tracer) )
      tree.add( self.__EXPR( self.prefixBp0[25] ) )
      tree.isPrefix = True
    elif self.sym.getId() in [97]:
      tree.astTransform = AstTransformNodeCreator('PreDecr', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(97, tracer) )
      tree.add( self.__EXPR( self.prefixBp0[97] ) )
      tree.isPrefix = True
    elif self.sym.getId() in [16]:
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      tree.nudMorphemeCount = 1
      return self.expect( 16, tracer )
    elif self.sym.getId() in [32]:
      tree.astTransform = AstTransformNodeCreator('AddressOf', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(32, tracer) )
      tree.add( self.__EXPR( self.prefixBp0[32] ) )
      tree.isPrefix = True
    elif self.sym.getId() in [63, 35, 8, 14, 110, 66]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      tree.add( self._CONSTANT() )
    elif self.sym.getId() in [7]:
      tree.astTransform = AstTransformSubstitution(2)
      tree.nudMorphemeCount = 3
      tree.add( self.expect(7, tracer) )
      tree.add( self.__EXPR() )
      tree.add( self.expect(9, tracer) )
    return tree
  def led0(self, left, tracer):
    tree = ParseTree( NonTerminal(209, '_expr') )
    if  self.sym.getId() == 61: # 'lteq'
      tree.astTransform = AstTransformNodeCreator('LessThanEq', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(61, tracer) )
      modifier = 0
      tree.add( self.__EXPR( self.infixBp0[61] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 41: # 'bitandeq'
      tree.astTransform = AstTransformNodeCreator('ANDAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(41, tracer) )
      modifier = 1
      tree.add( self.__EXPR( self.infixBp0[41] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 80: # 'muleq'
      tree.astTransform = AstTransformNodeCreator('MultiplyAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(80, tracer) )
      modifier = 1
      tree.add( self.__EXPR( self.infixBp0[80] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 88: # 'sub'
      tree.astTransform = AstTransformNodeCreator('Sub', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(88, tracer) )
      modifier = 0
      tree.add( self.__EXPR( self.infixBp0[88] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 106: # 'diveq'
      tree.astTransform = AstTransformNodeCreator('DivideAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(106, tracer) )
      modifier = 1
      tree.add( self.__EXPR( self.infixBp0[106] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 75: # 'rshift'
      tree.astTransform = AstTransformNodeCreator('RightShift', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(75, tracer) )
      modifier = 0
      tree.add( self.__EXPR( self.infixBp0[75] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 46: # 'dot'
      tree.astTransform = AstTransformNodeCreator('MemberSelect', {'member': 2, 'object': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(46, tracer) )
      modifier = 0
      tree.add( self.__EXPR( self.infixBp0[46] - modifier ) )
    elif  self.sym.getId() == 20: # 'lt'
      tree.astTransform = AstTransformNodeCreator('LessThan', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(20, tracer) )
      modifier = 0
      tree.add( self.__EXPR( self.infixBp0[20] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 82: # 'modeq'
      tree.astTransform = AstTransformNodeCreator('ModAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(82, tracer) )
      modifier = 1
      tree.add( self.__EXPR( self.infixBp0[82] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 83: # 'asterisk'
      tree.astTransform = AstTransformNodeCreator('Mul', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(83, tracer) )
      modifier = 0
      tree.add( self.__EXPR( self.infixBp0[83] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 43: # 'gteq'
      tree.astTransform = AstTransformNodeCreator('GreaterThanEq', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(43, tracer) )
      modifier = 0
      tree.add( self.__EXPR( self.infixBp0[43] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 114: # 'lshift'
      tree.astTransform = AstTransformNodeCreator('LeftShift', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(114, tracer) )
      modifier = 0
      tree.add( self.__EXPR( self.infixBp0[114] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 44: # 'eq'
      tree.astTransform = AstTransformNodeCreator('Equals', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(44, tracer) )
      modifier = 1
      tree.add( self.__EXPR( self.infixBp0[44] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 45: # 'bitxor'
      tree.astTransform = AstTransformNodeCreator('BitXOR', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(45, tracer) )
      modifier = 0
      tree.add( self.__EXPR( self.infixBp0[45] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 93: # 'subeq'
      tree.astTransform = AstTransformNodeCreator('SubtractAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(93, tracer) )
      modifier = 1
      tree.add( self.__EXPR( self.infixBp0[93] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 54: # 'add'
      tree.astTransform = AstTransformNodeCreator('Add', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(54, tracer) )
      modifier = 0
      tree.add( self.__EXPR( self.infixBp0[54] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 62: # 'questionmark'
      tree.astTransform = AstTransformNodeCreator('TernaryOperator', {'true': 2, 'false': 4, 'cond': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(62, tracer) )
      modifier = 1
      tree.add( self.__EXPR( self.infixBp0[62] - modifier ) )
      tree.add( self.expect(13, tracer) )
      modifier = 1
      tree.add( self.__EXPR( self.infixBp0[62] - modifier ) )
    elif  self.sym.getId() == 48: # 'lshifteq'
      tree.astTransform = AstTransformNodeCreator('LeftShiftAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(48, tracer) )
      modifier = 1
      tree.add( self.__EXPR( self.infixBp0[48] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 7: # 'lparen'
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(7, tracer) )
      tree.add( self.__GEN40() )
      tree.add( self.expect(9, tracer) )
    elif  self.sym.getId() == 102: # 'comma'
      tree.astTransform = AstTransformNodeCreator('Comma', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(102, tracer) )
      modifier = 0
      tree.add( self.__EXPR( self.infixBp0[102] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 25: # 'incr'
      tree.astTransform = AstTransformNodeCreator('PostIncr', {'var': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(25, tracer) )
    elif  self.sym.getId() == 100: # 'bitor'
      tree.astTransform = AstTransformNodeCreator('BitOR', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(100, tracer) )
      modifier = 0
      tree.add( self.__EXPR( self.infixBp0[100] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 101: # 'assign'
      tree.astTransform = AstTransformNodeCreator('Assign', {'var': 0, 'value': 2})
      if left:
        tree.add(left)
      tree.add( self.expect(101, tracer) )
      modifier = 1
      tree.add( self.__EXPR( self.infixBp0[101] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 32: # 'bitand'
      tree.astTransform = AstTransformNodeCreator('BitAND', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(32, tracer) )
      modifier = 0
      tree.add( self.__EXPR( self.infixBp0[32] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 99: # 'arrow'
      tree.astTransform = AstTransformNodeCreator('DerefMemberSelect', {'member': 2, 'object': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(99, tracer) )
      modifier = 0
      tree.add( self.__EXPR( self.infixBp0[99] - modifier ) )
    elif  self.sym.getId() == 74: # 'lbrace'
      tree.astTransform = AstTransformNodeCreator('TypeInitializion', {'type': 1, 'initializer': 4})
      if left:
        tree.add(left)
      tree.add( self.expect(74, tracer) )
      tree.add( self.__GEN12() )
      tree.add( self._TRAILING_COMMA_OPT() )
      tree.add( self.expect(30, tracer) )
    elif  self.sym.getId() == 37: # 'lsquare'
      tree.astTransform = AstTransformNodeCreator('ArrayIndex', {'params': 2, 'name': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(37, tracer) )
      tree.add( self.__GEN40() )
      tree.add( self.expect(39, tracer) )
    elif  self.sym.getId() == 97: # 'decr'
      tree.astTransform = AstTransformNodeCreator('PostDecr', {'var': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(97, tracer) )
    elif  self.sym.getId() == 0: # 'mod'
      tree.astTransform = AstTransformNodeCreator('Mod', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(0, tracer) )
      modifier = 0
      tree.add( self.__EXPR( self.infixBp0[0] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 28: # 'div'
      tree.astTransform = AstTransformNodeCreator('Div', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(28, tracer) )
      modifier = 0
      tree.add( self.__EXPR( self.infixBp0[28] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 22: # 'sizeof_separator'
      tree.astTransform = AstTransformNodeCreator('SizeOf', {'var': 1})
      if left:
        tree.add(left)
      tree.add( self.expect(22, tracer) )
      tree.add( self._SIZEOF_BODY() )
    elif  self.sym.getId() == 73: # 'addeq'
      tree.astTransform = AstTransformNodeCreator('AddAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(73, tracer) )
      modifier = 1
      tree.add( self.__EXPR( self.infixBp0[73] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 21: # 'rshifteq'
      tree.astTransform = AstTransformNodeCreator('RightShiftAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(21, tracer) )
      modifier = 1
      tree.add( self.__EXPR( self.infixBp0[21] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 12: # 'gt'
      tree.astTransform = AstTransformNodeCreator('GreaterThan', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(12, tracer) )
      modifier = 0
      tree.add( self.__EXPR( self.infixBp0[12] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 36: # 'bitxoreq'
      tree.astTransform = AstTransformNodeCreator('XORAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(36, tracer) )
      modifier = 1
      tree.add( self.__EXPR( self.infixBp0[36] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 29: # 'bitoreq'
      tree.astTransform = AstTransformNodeCreator('ORAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(29, tracer) )
      modifier = 1
      tree.add( self.__EXPR( self.infixBp0[29] - modifier ) )
      tree.isInfix = True
    return tree
  infixBp1 = {
    0: 12000,
    7: 15000,
    12: 9000,
    20: 9000,
    21: 1000,
    25: 15000,
    28: 12000,
    29: 1000,
    32: 5000,
    33: 3000,
    36: 1000,
    37: 15000,
    41: 1000,
    43: 9000,
    44: 8000,
    45: 6000,
    46: 15000,
    48: 1000,
    54: 11000,
    60: 8000,
    61: 9000,
    62: 2000,
    73: 1000,
    74: 14000,
    75: 10000,
    80: 1000,
    82: 1000,
    83: 12000,
    88: 11000,
    93: 1000,
    96: 4000,
    97: 15000,
    99: 15000,
    100: 7000,
    101: 1000,
    106: 1000,
    114: 10000,
  }
  prefixBp1 = {
    25: 13000,
    32: 13000,
    40: 13000,
    52: 13000,
    83: 13000,
    88: 13000,
    97: 13000,
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
    tree = ParseTree( NonTerminal(141, '_expr_sans_comma') )
    if not self.sym:
      return tree
    elif self.sym.getId() in [50]:
      tree.astTransform = AstTransformNodeCreator('SizeOf', {'var': 1})
      tree.nudMorphemeCount = 1
      return self.expect( 50, tracer )
    elif self.sym.getId() in [16]:
      tree.astTransform = AstTransformNodeCreator('ArrayIndex', {'params': 2, 'name': 0})
      tree.nudMorphemeCount = 1
      return self.expect( 16, tracer )
    elif self.sym.getId() in [97]:
      tree.astTransform = AstTransformNodeCreator('PreDecr', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(97, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.prefixBp1[97] ) )
      tree.isPrefix = True
    elif self.sym.getId() in [83]:
      tree.astTransform = AstTransformNodeCreator('Dereference', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(83, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.prefixBp1[83] ) )
      tree.isPrefix = True
    elif self.sym.getId() in [16]:
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      tree.nudMorphemeCount = 1
      return self.expect( 16, tracer )
    elif self.sym.getId() in [10]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      return self.expect( 10, tracer )
    elif self.sym.getId() in [63, 35, 8, 14, 110, 66]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      tree.add( self._CONSTANT() )
    elif self.sym.getId() in [16]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      return self.expect( 16, tracer )
    elif self.sym.getId() in [53]:
      tree.astTransform = AstTransformNodeCreator('TypeInitializion', {'type': 1, 'initializer': 4})
      tree.nudMorphemeCount = 3
      tree.add( self.expect(53, tracer) )
      tree.add( self._TYPE_NAME() )
      tree.add( self.expect(9, tracer) )
    elif self.sym.getId() in [7]:
      tree.astTransform = AstTransformSubstitution(2)
      tree.nudMorphemeCount = 3
      tree.add( self.expect(7, tracer) )
      tree.add( self.__EXPR_SANS_COMMA() )
      tree.add( self.expect(9, tracer) )
    elif self.sym.getId() in [25]:
      tree.astTransform = AstTransformNodeCreator('PreIncr', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(25, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.prefixBp1[25] ) )
      tree.isPrefix = True
    elif self.sym.getId() in [32]:
      tree.astTransform = AstTransformNodeCreator('AddressOf', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(32, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.prefixBp1[32] ) )
      tree.isPrefix = True
    return tree
  def led1(self, left, tracer):
    tree = ParseTree( NonTerminal(141, '_expr_sans_comma') )
    if  self.sym.getId() == 44: # 'eq'
      tree.astTransform = AstTransformNodeCreator('Equals', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(44, tracer) )
      modifier = 1
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[44] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 106: # 'diveq'
      tree.astTransform = AstTransformNodeCreator('DivideAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(106, tracer) )
      modifier = 1
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[106] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 61: # 'lteq'
      tree.astTransform = AstTransformNodeCreator('LessThanEq', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(61, tracer) )
      modifier = 0
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[61] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 73: # 'addeq'
      tree.astTransform = AstTransformNodeCreator('AddAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(73, tracer) )
      modifier = 1
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[73] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 74: # 'lbrace'
      tree.astTransform = AstTransformNodeCreator('TypeInitializion', {'type': 1, 'initializer': 4})
      if left:
        tree.add(left)
      tree.add( self.expect(74, tracer) )
      tree.add( self.__GEN12() )
      tree.add( self._TRAILING_COMMA_OPT() )
      tree.add( self.expect(30, tracer) )
    elif  self.sym.getId() == 101: # 'assign'
      tree.astTransform = AstTransformNodeCreator('Assign', {'var': 0, 'value': 2})
      if left:
        tree.add(left)
      tree.add( self.expect(101, tracer) )
      modifier = 1
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[101] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 48: # 'lshifteq'
      tree.astTransform = AstTransformNodeCreator('LeftShiftAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(48, tracer) )
      modifier = 1
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[48] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 93: # 'subeq'
      tree.astTransform = AstTransformNodeCreator('SubtractAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(93, tracer) )
      modifier = 1
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[93] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 43: # 'gteq'
      tree.astTransform = AstTransformNodeCreator('GreaterThanEq', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(43, tracer) )
      modifier = 0
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[43] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 54: # 'add'
      tree.astTransform = AstTransformNodeCreator('Add', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(54, tracer) )
      modifier = 0
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[54] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 46: # 'dot'
      tree.astTransform = AstTransformNodeCreator('MemberSelect', {'member': 2, 'object': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(46, tracer) )
      modifier = 0
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[46] - modifier ) )
    elif  self.sym.getId() == 97: # 'decr'
      tree.astTransform = AstTransformNodeCreator('PostDecr', {'var': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(97, tracer) )
    elif  self.sym.getId() == 114: # 'lshift'
      tree.astTransform = AstTransformNodeCreator('LeftShift', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(114, tracer) )
      modifier = 0
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[114] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 21: # 'rshifteq'
      tree.astTransform = AstTransformNodeCreator('RightShiftAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(21, tracer) )
      modifier = 1
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[21] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 80: # 'muleq'
      tree.astTransform = AstTransformNodeCreator('MultiplyAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(80, tracer) )
      modifier = 1
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[80] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 75: # 'rshift'
      tree.astTransform = AstTransformNodeCreator('RightShift', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(75, tracer) )
      modifier = 0
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[75] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 83: # 'asterisk'
      tree.astTransform = AstTransformNodeCreator('Mul', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(83, tracer) )
      modifier = 0
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[83] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 88: # 'sub'
      tree.astTransform = AstTransformNodeCreator('Sub', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(88, tracer) )
      modifier = 0
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[88] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 62: # 'questionmark'
      tree.astTransform = AstTransformNodeCreator('TernaryOperator', {'true': 2, 'false': 4, 'cond': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(62, tracer) )
      modifier = 1
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[62] - modifier ) )
      tree.add( self.expect(13, tracer) )
      modifier = 1
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[62] - modifier ) )
    elif  self.sym.getId() == 25: # 'incr'
      tree.astTransform = AstTransformNodeCreator('PostIncr', {'var': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(25, tracer) )
    elif  self.sym.getId() == 99: # 'arrow'
      tree.astTransform = AstTransformNodeCreator('DerefMemberSelect', {'member': 2, 'object': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(99, tracer) )
      modifier = 0
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[99] - modifier ) )
    elif  self.sym.getId() == 22: # 'sizeof_separator'
      tree.astTransform = AstTransformNodeCreator('SizeOf', {'var': 1})
      if left:
        tree.add(left)
      tree.add( self.expect(22, tracer) )
      tree.add( self._SIZEOF_BODY() )
    elif  self.sym.getId() == 36: # 'bitxoreq'
      tree.astTransform = AstTransformNodeCreator('XORAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(36, tracer) )
      modifier = 1
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[36] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 82: # 'modeq'
      tree.astTransform = AstTransformNodeCreator('ModAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(82, tracer) )
      modifier = 1
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[82] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 28: # 'div'
      tree.astTransform = AstTransformNodeCreator('Div', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(28, tracer) )
      modifier = 0
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[28] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 20: # 'lt'
      tree.astTransform = AstTransformNodeCreator('LessThan', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(20, tracer) )
      modifier = 0
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[20] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 7: # 'lparen'
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(7, tracer) )
      tree.add( self.__GEN40() )
      tree.add( self.expect(9, tracer) )
    elif  self.sym.getId() == 41: # 'bitandeq'
      tree.astTransform = AstTransformNodeCreator('ANDAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(41, tracer) )
      modifier = 1
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[41] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 32: # 'bitand'
      tree.astTransform = AstTransformNodeCreator('BitAND', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(32, tracer) )
      modifier = 0
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[32] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 37: # 'lsquare'
      tree.astTransform = AstTransformNodeCreator('ArrayIndex', {'params': 2, 'name': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(37, tracer) )
      tree.add( self.__GEN40() )
      tree.add( self.expect(39, tracer) )
    elif  self.sym.getId() == 0: # 'mod'
      tree.astTransform = AstTransformNodeCreator('Mod', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(0, tracer) )
      modifier = 0
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[0] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 12: # 'gt'
      tree.astTransform = AstTransformNodeCreator('GreaterThan', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(12, tracer) )
      modifier = 0
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[12] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 29: # 'bitoreq'
      tree.astTransform = AstTransformNodeCreator('ORAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(29, tracer) )
      modifier = 1
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[29] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 100: # 'bitor'
      tree.astTransform = AstTransformNodeCreator('BitOR', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(100, tracer) )
      modifier = 0
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[100] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 45: # 'bitxor'
      tree.astTransform = AstTransformNodeCreator('BitXOR', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(45, tracer) )
      modifier = 0
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[45] - modifier ) )
      tree.isInfix = True
    return tree
  infixBp2 = {
    7: 1000,
    37: 1000,
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
    tree = ParseTree( NonTerminal(137, '_direct_declarator') )
    if not self.sym:
      return tree
    if self.sym.getId() in [7]:
      tree.astTransform = AstTransformSubstitution(1)
      tree.nudMorphemeCount = 3
      tree.add( self.expect(7, tracer) )
      tree.add( self._DECLARATOR() )
      tree.add( self.expect(9, tracer) )
    elif self.sym.getId() in [16]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      return self.expect( 16, tracer )
    return tree
  def led2(self, left, tracer):
    tree = ParseTree( NonTerminal(137, '_direct_declarator') )
    if  self.sym.getId() == 7: # 'lparen'
      tree.astTransform = AstTransformNodeCreator('FunctionSignature', {'params': 2, 'declarator': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(7, tracer) )
      tree.add( self._DIRECT_DECLARATOR_PARAMETER_LIST() )
      tree.add( self.expect(9, tracer) )
    elif  self.sym.getId() == 37: # 'lsquare'
      tree.astTransform = AstTransformNodeCreator('Array', {'name': 0, 'size': 2})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(37, tracer) )
      tree.add( self._DIRECT_DECLARATOR_EXPR() )
      tree.add( self.expect(39, tracer) )
    return tree
  infixBp3 = {
    7: 1000,
    37: 1000,
  }
  prefixBp3 = {
    7: 2000,
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
    tree = ParseTree( NonTerminal(150, '_direct_abstract_declarator') )
    if not self.sym:
      return tree
    if self.sym.getId() in [-1, 7, 1]:
      tree.astTransform = AstTransformNodeCreator('AbstractArray', {'object': 0, 'size': 2})
      tree.nudMorphemeCount = 1
      tree.add( self._DIRECT_ABSTRACT_DECLARATOR_OPT() )
    elif self.sym.getId() in [7]:
      tree.astTransform = AstTransformSubstitution(1)
      tree.nudMorphemeCount = 3
      tree.add( self.expect(7, tracer) )
      tree.add( self._ABSTRACT_DECLARATOR() )
      tree.add( self.expect(9, tracer) )
    elif self.sym.getId() in [-1, 7, 1]:
      tree.astTransform = AstTransformNodeCreator('AbstractFunction', {'object': 0, 'params': 2})
      tree.nudMorphemeCount = 1
      tree.add( self._DIRECT_ABSTRACT_DECLARATOR_OPT() )
    return tree
  def led3(self, left, tracer):
    tree = ParseTree( NonTerminal(150, '_direct_abstract_declarator') )
    if  self.sym.getId() == 37: # 'lsquare'
      tree.astTransform = AstTransformNodeCreator('AbstractArray', {'object': 0, 'size': 2})
      if left:
        tree.add(left)
      tree.add( self.expect(37, tracer) )
      tree.add( self._DIRECT_ABSTRACT_DECLARATOR_EXPR() )
      tree.add( self.expect(39, tracer) )
    elif  self.sym.getId() == 7: # 'lparen'
      tree.astTransform = AstTransformNodeCreator('AbstractFunction', {'object': 0, 'params': 2})
      if left:
        tree.add(left)
      tree.add( self.expect(7, tracer) )
      tree.add( self.__GEN42() )
      tree.add( self.expect(9, tracer) )
    return tree
