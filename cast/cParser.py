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
  TERMINAL_LBRACE = 0
  TERMINAL__EXPR_SANS_COMMA = 1
  TERMINAL_TYPEDEF = 2
  TERMINAL_IMAGINARY = 3
  TERMINAL_DECR = 4
  TERMINAL_LONG = 5
  TERMINAL_DO = 6
  TERMINAL_GT = 7
  TERMINAL_NOT = 8
  TERMINAL_EXTERN = 9
  TERMINAL_ELSE = 10
  TERMINAL_FOR = 11
  TERMINAL_VOLATILE = 12
  TERMINAL_LSHIFT = 13
  TERMINAL_ELIPSIS = 14
  TERMINAL_STATIC = 15
  TERMINAL_SHORT = 16
  TERMINAL_STRUCT = 17
  TERMINAL_INT = 18
  TERMINAL_EQ = 19
  TERMINAL_LABEL_HINT = 20
  TERMINAL_RSHIFT = 21
  TERMINAL_CHARACTER_CONSTANT = 22
  TERMINAL_UNIVERSAL_CHARACTER_NAME = 23
  TERMINAL_ELSE_IF = 24
  TERMINAL_LT = 25
  TERMINAL_DECLARATOR_HINT = 26
  TERMINAL_MOD = 27
  TERMINAL_REGISTER = 28
  TERMINAL_MODEQ = 29
  TERMINAL_LPAREN = 30
  TERMINAL_MULEQ = 31
  TERMINAL_DIVEQ = 32
  TERMINAL_RPAREN = 33
  TERMINAL_AUTO = 34
  TERMINAL_ENDIF = 35
  TERMINAL_BITNOT = 36
  TERMINAL_INTEGER_CONSTANT = 37
  TERMINAL_BITXOR = 38
  TERMINAL_DEFAULT = 39
  TERMINAL_CONST = 40
  TERMINAL_ENUM = 41
  TERMINAL_FLOATING_CONSTANT = 42
  TERMINAL_ADD = 43
  TERMINAL_CHAR = 44
  TERMINAL_RSQUARE = 45
  TERMINAL_BOOL = 46
  TERMINAL_RESTRICT = 47
  TERMINAL_LSQUARE = 48
  TERMINAL_QUESTIONMARK = 49
  TERMINAL__EXPR = 50
  TERMINAL_AMPERSAND = 51
  TERMINAL_COLON = 52
  TERMINAL_FUNCTION_DEFINITION_HINT = 53
  TERMINAL_EXCLAMATION_POINT = 54
  TERMINAL_CASE = 55
  TERMINAL_BITOREQ = 56
  TERMINAL_VOID = 57
  TERMINAL_LPAREN_CAST = 58
  TERMINAL_CONTINUE = 59
  TERMINAL_UNSIGNED = 60
  TERMINAL_SIZEOF = 61
  TERMINAL_SUB = 62
  TERMINAL_BITXOREQ = 63
  TERMINAL_ASTERISK = 64
  TERMINAL_POUND = 65
  TERMINAL_IF = 66
  TERMINAL_SEMI = 67
  TERMINAL_BREAK = 68
  TERMINAL_UNION = 69
  TERMINAL_RBRACE = 70
  TERMINAL_BITANDEQ = 71
  TERMINAL_RSHIFTEQ = 72
  TERMINAL_COMMA = 73
  TERMINAL_HEXADECIMAL_FLOATING_CONSTANT = 74
  TERMINAL_TILDE = 75
  TERMINAL_INCR = 76
  TERMINAL_SIGNED = 77
  TERMINAL_RETURN = 78
  TERMINAL_DIV = 79
  TERMINAL_STRING_LITERAL = 80
  TERMINAL_LSHIFTEQ = 81
  TERMINAL_POUNDPOUND = 82
  TERMINAL_LTEQ = 83
  TERMINAL_DEFINED = 84
  TERMINAL_EXTERNAL_DECLARATION_HINT = 85
  TERMINAL_INLINE = 86
  TERMINAL_ASSIGN = 87
  TERMINAL_COMMA_VA_ARGS = 88
  TERMINAL_GTEQ = 89
  TERMINAL_DOUBLE = 90
  TERMINAL_OR = 91
  TERMINAL_DEFINED_SEPARATOR = 92
  TERMINAL_ENUMERATION_CONSTANT = 93
  TERMINAL_SIZEOF_SEPARATOR = 94
  TERMINAL_SUBEQ = 95
  TERMINAL_WHILE = 96
  TERMINAL_AND = 97
  TERMINAL_ARROW = 98
  TERMINAL_DECIMAL_FLOATING_CONSTANT = 99
  TERMINAL_TRAILING_COMMA = 100
  TERMINAL_PP_NUMBER = 101
  TERMINAL_BITOR = 102
  TERMINAL_GOTO = 103
  TERMINAL_ADDEQ = 104
  TERMINAL_TYPEDEF_IDENTIFIER = 105
  TERMINAL_DOT = 106
  TERMINAL_IDENTIFIER = 107
  TERMINAL_FUNCTION_PROTOTYPE_HINT = 108
  TERMINAL_FLOAT = 109
  TERMINAL_NEQ = 110
  TERMINAL_COMPLEX = 111
  TERMINAL__DIRECT_DECLARATOR = 112
  TERMINAL_SWITCH = 113
  TERMINAL_BITAND = 114
  terminal_str = {
    0: 'lbrace',
    1: '_expr_sans_comma',
    2: 'typedef',
    3: 'imaginary',
    4: 'decr',
    5: 'long',
    6: 'do',
    7: 'gt',
    8: 'not',
    9: 'extern',
    10: 'else',
    11: 'for',
    12: 'volatile',
    13: 'lshift',
    14: 'elipsis',
    15: 'static',
    16: 'short',
    17: 'struct',
    18: 'int',
    19: 'eq',
    20: 'label_hint',
    21: 'rshift',
    22: 'character_constant',
    23: 'universal_character_name',
    24: 'else_if',
    25: 'lt',
    26: 'declarator_hint',
    27: 'mod',
    28: 'register',
    29: 'modeq',
    30: 'lparen',
    31: 'muleq',
    32: 'diveq',
    33: 'rparen',
    34: 'auto',
    35: 'endif',
    36: 'bitnot',
    37: 'integer_constant',
    38: 'bitxor',
    39: 'default',
    40: 'const',
    41: 'enum',
    42: 'floating_constant',
    43: 'add',
    44: 'char',
    45: 'rsquare',
    46: 'bool',
    47: 'restrict',
    48: 'lsquare',
    49: 'questionmark',
    50: '_expr',
    51: 'ampersand',
    52: 'colon',
    53: 'function_definition_hint',
    54: 'exclamation_point',
    55: 'case',
    56: 'bitoreq',
    57: 'void',
    58: 'lparen_cast',
    59: 'continue',
    60: 'unsigned',
    61: 'sizeof',
    62: 'sub',
    63: 'bitxoreq',
    64: 'asterisk',
    65: 'pound',
    66: 'if',
    67: 'semi',
    68: 'break',
    69: 'union',
    70: 'rbrace',
    71: 'bitandeq',
    72: 'rshifteq',
    73: 'comma',
    74: 'hexadecimal_floating_constant',
    75: 'tilde',
    76: 'incr',
    77: 'signed',
    78: 'return',
    79: 'div',
    80: 'string_literal',
    81: 'lshifteq',
    82: 'poundpound',
    83: 'lteq',
    84: 'defined',
    85: 'external_declaration_hint',
    86: 'inline',
    87: 'assign',
    88: 'comma_va_args',
    89: 'gteq',
    90: 'double',
    91: 'or',
    92: 'defined_separator',
    93: 'enumeration_constant',
    94: 'sizeof_separator',
    95: 'subeq',
    96: 'while',
    97: 'and',
    98: 'arrow',
    99: 'decimal_floating_constant',
    100: 'trailing_comma',
    101: 'pp_number',
    102: 'bitor',
    103: 'goto',
    104: 'addeq',
    105: 'typedef_identifier',
    106: 'dot',
    107: 'identifier',
    108: 'function_prototype_hint',
    109: 'float',
    110: 'neq',
    111: 'complex',
    112: '_direct_declarator',
    113: 'switch',
    114: 'bitand',
  }
  nonterminal_str = {
    115: 'direct_abstract_declarator_sub0',
    116: '_gen8',
    117: '_gen38',
    118: 'init_declarator',
    119: 'declaration_specifier',
    120: 'for_init',
    121: 'for_cond',
    122: '_gen24',
    123: 'direct_abstract_declarator_sub1',
    124: '_gen9',
    125: '_gen14',
    126: 'block_item',
    127: 'pointer',
    128: '_gen2',
    129: 'abstract_declarator',
    130: 'storage_class_specifier',
    131: '_direct_declarator',
    132: 'else_if_statement_list',
    133: '_gen39',
    134: 'direct_declarator_modifier',
    135: 'direct_abstract_declarator_expr',
    136: '_gen19',
    137: '_gen6',
    138: 'else_statement',
    139: '_gen40',
    140: 'translation_unit',
    141: 'direct_abstract_declarator_sub2',
    142: '_gen5',
    143: 'direct_declarator_parameter_list',
    144: '_gen0',
    145: 'else_if_statement',
    146: '_gen41',
    147: 'parameter_type_list',
    148: '_gen10',
    149: 'enumerator_assignment',
    150: '_gen1',
    151: '_gen42',
    152: 'enumerator',
    153: 'type_qualifier_list_opt',
    154: '_gen11',
    155: '_gen43',
    156: '_gen12',
    157: 'direct_declarator_expr',
    158: 'type_name',
    159: '_expr_sans_comma',
    160: '_gen28',
    161: 'for_incr',
    162: 'keyword',
    163: '_gen21',
    164: 'trailing_comma_opt',
    165: '_gen22',
    166: '_gen13',
    167: 'misc',
    168: 'declaration_list',
    169: 'pointer_opt',
    170: 'direct_abstract_declarator',
    171: 'declarator_initializer',
    172: 'struct_specifier',
    173: 'external_declarator',
    174: 'external_declaration',
    175: 'statement',
    176: 'union_specifier',
    177: 'block_item_list',
    178: 'compound_statement',
    179: 'initializer',
    180: 'punctuator',
    181: 'enum_specifier',
    182: 'parameter_declaration_sub',
    183: '_gen34',
    184: 'specifier_qualifier',
    185: 'typedef_name',
    186: 'labeled_statement',
    187: 'initializer_list_item',
    188: 'enumeration_constant',
    189: '_gen23',
    190: '_gen25',
    191: '_gen15',
    192: 'declaration',
    193: 'iteration_statement',
    194: 'parameter_declaration_sub_sub',
    195: 'expression_statement',
    196: 'parameter_declaration',
    197: '_gen26',
    198: '_gen29',
    199: '_gen30',
    200: 'enum_specifier_sub',
    201: 'external_declaration_sub',
    202: '_gen35',
    203: 'designation',
    204: 'struct_or_union_body',
    205: '_gen18',
    206: 'struct_or_union_sub',
    207: 'external_function',
    208: 'init_declarator_list',
    209: 'token',
    210: '_gen16',
    211: 'jump_statement',
    212: '_expr',
    213: '_gen31',
    214: 'direct_declarator_size',
    215: 'identifier',
    216: 'static_opt',
    217: 'enum_specifier_body',
    218: 'va_args',
    219: '_gen3',
    220: '_gen4',
    221: 'struct_declaration',
    222: 'constant',
    223: 'designator',
    224: 'selection_statement',
    225: '_gen17',
    226: 'type_specifier',
    227: 'struct_declarator_body',
    228: 'pointer_sub',
    229: '_gen36',
    230: 'type_qualifier',
    231: '_gen33',
    232: '_gen37',
    233: 'pp',
    234: '_gen20',
    235: '_gen27',
    236: 'function_specifier',
    237: 'direct_declarator_modifier_list_opt',
    238: '_gen7',
    239: 'expression_opt',
    240: '_gen32',
    241: 'sizeof_body',
    242: 'external_declaration_sub_sub',
    243: 'external_prototype',
    244: 'declarator',
    245: 'struct_declarator',
  }
  str_terminal = {
    'lbrace': 0,
    '_expr_sans_comma': 1,
    'typedef': 2,
    'imaginary': 3,
    'decr': 4,
    'long': 5,
    'do': 6,
    'gt': 7,
    'not': 8,
    'extern': 9,
    'else': 10,
    'for': 11,
    'volatile': 12,
    'lshift': 13,
    'elipsis': 14,
    'static': 15,
    'short': 16,
    'struct': 17,
    'int': 18,
    'eq': 19,
    'label_hint': 20,
    'rshift': 21,
    'character_constant': 22,
    'universal_character_name': 23,
    'else_if': 24,
    'lt': 25,
    'declarator_hint': 26,
    'mod': 27,
    'register': 28,
    'modeq': 29,
    'lparen': 30,
    'muleq': 31,
    'diveq': 32,
    'rparen': 33,
    'auto': 34,
    'endif': 35,
    'bitnot': 36,
    'integer_constant': 37,
    'bitxor': 38,
    'default': 39,
    'const': 40,
    'enum': 41,
    'floating_constant': 42,
    'add': 43,
    'char': 44,
    'rsquare': 45,
    'bool': 46,
    'restrict': 47,
    'lsquare': 48,
    'questionmark': 49,
    '_expr': 50,
    'ampersand': 51,
    'colon': 52,
    'function_definition_hint': 53,
    'exclamation_point': 54,
    'case': 55,
    'bitoreq': 56,
    'void': 57,
    'lparen_cast': 58,
    'continue': 59,
    'unsigned': 60,
    'sizeof': 61,
    'sub': 62,
    'bitxoreq': 63,
    'asterisk': 64,
    'pound': 65,
    'if': 66,
    'semi': 67,
    'break': 68,
    'union': 69,
    'rbrace': 70,
    'bitandeq': 71,
    'rshifteq': 72,
    'comma': 73,
    'hexadecimal_floating_constant': 74,
    'tilde': 75,
    'incr': 76,
    'signed': 77,
    'return': 78,
    'div': 79,
    'string_literal': 80,
    'lshifteq': 81,
    'poundpound': 82,
    'lteq': 83,
    'defined': 84,
    'external_declaration_hint': 85,
    'inline': 86,
    'assign': 87,
    'comma_va_args': 88,
    'gteq': 89,
    'double': 90,
    'or': 91,
    'defined_separator': 92,
    'enumeration_constant': 93,
    'sizeof_separator': 94,
    'subeq': 95,
    'while': 96,
    'and': 97,
    'arrow': 98,
    'decimal_floating_constant': 99,
    'trailing_comma': 100,
    'pp_number': 101,
    'bitor': 102,
    'goto': 103,
    'addeq': 104,
    'typedef_identifier': 105,
    'dot': 106,
    'identifier': 107,
    'function_prototype_hint': 108,
    'float': 109,
    'neq': 110,
    'complex': 111,
    '_direct_declarator': 112,
    'switch': 113,
    'bitand': 114,
  }
  str_nonterminal = {
    'direct_abstract_declarator_sub0': 115,
    '_gen8': 116,
    '_gen38': 117,
    'init_declarator': 118,
    'declaration_specifier': 119,
    'for_init': 120,
    'for_cond': 121,
    '_gen24': 122,
    'direct_abstract_declarator_sub1': 123,
    '_gen9': 124,
    '_gen14': 125,
    'block_item': 126,
    'pointer': 127,
    '_gen2': 128,
    'abstract_declarator': 129,
    'storage_class_specifier': 130,
    '_direct_declarator': 131,
    'else_if_statement_list': 132,
    '_gen39': 133,
    'direct_declarator_modifier': 134,
    'direct_abstract_declarator_expr': 135,
    '_gen19': 136,
    '_gen6': 137,
    'else_statement': 138,
    '_gen40': 139,
    'translation_unit': 140,
    'direct_abstract_declarator_sub2': 141,
    '_gen5': 142,
    'direct_declarator_parameter_list': 143,
    '_gen0': 144,
    'else_if_statement': 145,
    '_gen41': 146,
    'parameter_type_list': 147,
    '_gen10': 148,
    'enumerator_assignment': 149,
    '_gen1': 150,
    '_gen42': 151,
    'enumerator': 152,
    'type_qualifier_list_opt': 153,
    '_gen11': 154,
    '_gen43': 155,
    '_gen12': 156,
    'direct_declarator_expr': 157,
    'type_name': 158,
    '_expr_sans_comma': 159,
    '_gen28': 160,
    'for_incr': 161,
    'keyword': 162,
    '_gen21': 163,
    'trailing_comma_opt': 164,
    '_gen22': 165,
    '_gen13': 166,
    'misc': 167,
    'declaration_list': 168,
    'pointer_opt': 169,
    'direct_abstract_declarator': 170,
    'declarator_initializer': 171,
    'struct_specifier': 172,
    'external_declarator': 173,
    'external_declaration': 174,
    'statement': 175,
    'union_specifier': 176,
    'block_item_list': 177,
    'compound_statement': 178,
    'initializer': 179,
    'punctuator': 180,
    'enum_specifier': 181,
    'parameter_declaration_sub': 182,
    '_gen34': 183,
    'specifier_qualifier': 184,
    'typedef_name': 185,
    'labeled_statement': 186,
    'initializer_list_item': 187,
    'enumeration_constant': 188,
    '_gen23': 189,
    '_gen25': 190,
    '_gen15': 191,
    'declaration': 192,
    'iteration_statement': 193,
    'parameter_declaration_sub_sub': 194,
    'expression_statement': 195,
    'parameter_declaration': 196,
    '_gen26': 197,
    '_gen29': 198,
    '_gen30': 199,
    'enum_specifier_sub': 200,
    'external_declaration_sub': 201,
    '_gen35': 202,
    'designation': 203,
    'struct_or_union_body': 204,
    '_gen18': 205,
    'struct_or_union_sub': 206,
    'external_function': 207,
    'init_declarator_list': 208,
    'token': 209,
    '_gen16': 210,
    'jump_statement': 211,
    '_expr': 212,
    '_gen31': 213,
    'direct_declarator_size': 214,
    'identifier': 215,
    'static_opt': 216,
    'enum_specifier_body': 217,
    'va_args': 218,
    '_gen3': 219,
    '_gen4': 220,
    'struct_declaration': 221,
    'constant': 222,
    'designator': 223,
    'selection_statement': 224,
    '_gen17': 225,
    'type_specifier': 226,
    'struct_declarator_body': 227,
    'pointer_sub': 228,
    '_gen36': 229,
    'type_qualifier': 230,
    '_gen33': 231,
    '_gen37': 232,
    'pp': 233,
    '_gen20': 234,
    '_gen27': 235,
    'function_specifier': 236,
    'direct_declarator_modifier_list_opt': 237,
    '_gen7': 238,
    'expression_opt': 239,
    '_gen32': 240,
    'sizeof_body': 241,
    'external_declaration_sub_sub': 242,
    'external_prototype': 243,
    'declarator': 244,
    'struct_declarator': 245,
  }
  terminal_count = 115
  nonterminal_count = 131
  parse_table = [
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 95, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 201, -1, -1, 203, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 203, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 203, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 203, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [6, -1, 6, 6, 6, 6, 6, -1, -1, 6, -1, 6, 6, -1, -1, 6, 6, 6, 6, -1, 6, -1, 6, -1, -1, -1, -1, -1, 6, -1, 6, -1, -1, -1, 6, -1, -1, 6, -1, 6, 6, 6, 6, -1, 6, -1, 6, 6, -1, -1, 6, -1, -1, -1, -1, 6, -1, 6, 6, 6, 6, 6, -1, -1, 6, -1, 6, 6, 6, 6, 8, -1, -1, -1, 6, -1, 6, 6, 6, -1, 6, -1, -1, -1, -1, -1, 6, -1, -1, -1, 6, -1, -1, 6, -1, -1, 6, -1, -1, 6, -1, -1, -1, 6, -1, 6, -1, 6, -1, 6, -1, 6, -1, 6, 6],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 213, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 213, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 213, -1, -1, -1, -1, 213, -1, -1],
    [-1, -1, 391, 261, -1, 261, -1, -1, -1, 391, -1, -1, 277, -1, -1, 391, 261, 261, 261, -1, -1, -1, -1, -1, -1, -1, -1, -1, 391, -1, -1, -1, -1, -1, 391, -1, -1, -1, -1, -1, 277, 261, -1, -1, 261, -1, 261, 277, -1, -1, -1, -1, -1, -1, -1, -1, -1, 261, -1, -1, 261, -1, -1, -1, -1, -1, -1, -1, -1, 261, -1, -1, -1, -1, -1, -1, -1, 261, -1, -1, -1, -1, -1, -1, -1, -1, 386, -1, -1, -1, 261, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 261, -1, -1, -1, 261, -1, 261, -1, -1, -1],
    [-1, -1, 273, 273, 351, 273, -1, -1, -1, 273, -1, -1, 273, -1, -1, 273, 273, 273, 273, -1, -1, -1, 351, -1, -1, -1, -1, -1, 273, -1, 351, -1, -1, -1, 273, -1, -1, 351, -1, -1, 273, 273, 351, -1, 273, -1, 273, 273, -1, -1, 351, -1, -1, -1, -1, -1, -1, 273, 351, -1, 273, 351, -1, -1, 351, -1, -1, 204, -1, 273, -1, -1, -1, -1, 351, -1, 351, 273, -1, -1, 351, -1, -1, -1, -1, -1, 273, -1, -1, -1, 273, -1, -1, 351, -1, -1, -1, -1, -1, 351, -1, -1, -1, -1, -1, 273, -1, 351, -1, 273, -1, 273, -1, -1, 351],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 190, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [394, -1, 97, 97, -1, 97, -1, -1, -1, 97, -1, -1, 97, -1, -1, 97, 97, 97, 97, -1, -1, -1, -1, -1, -1, -1, 97, -1, 97, -1, 97, -1, -1, 97, 97, -1, -1, -1, -1, -1, 97, 97, -1, -1, 97, -1, 97, 97, 97, -1, -1, -1, 97, 97, -1, -1, -1, 97, -1, -1, 97, -1, -1, -1, 97, -1, -1, 97, -1, 97, -1, -1, -1, 97, -1, -1, -1, 97, -1, -1, -1, -1, -1, -1, -1, -1, 97, -1, 97, -1, 97, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 97, -1, 97, 97, 97, -1, 97, 97, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 230, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 413, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 214, -1, -1, 334, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 214, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 334, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 334, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [232, -1, -1, -1, 232, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 232, -1, -1, -1, -1, -1, -1, -1, 232, -1, -1, -1, -1, -1, -1, 232, -1, -1, -1, -1, 232, -1, -1, -1, -1, -1, 232, -1, 232, -1, -1, -1, -1, -1, -1, -1, 232, -1, -1, 232, -1, -1, 232, -1, -1, -1, -1, -1, -1, -1, -1, -1, 232, -1, 232, -1, -1, -1, 232, -1, -1, -1, -1, -1, -1, 232, -1, -1, -1, -1, -1, 232, -1, -1, -1, -1, -1, 232, -1, -1, -1, -1, -1, -1, 232, 232, -1, -1, -1, -1, -1, -1, 232],
    [178, -1, 184, 184, 178, 184, 178, -1, -1, 184, -1, 178, 184, -1, -1, 184, 184, 184, 184, -1, 178, -1, 178, -1, -1, -1, -1, -1, 184, -1, 178, -1, -1, -1, 184, -1, -1, 178, -1, 178, 184, 184, 178, -1, 184, -1, 184, 184, -1, -1, 178, -1, -1, -1, -1, 178, -1, 184, 178, 178, 184, 178, -1, -1, 178, -1, 178, 178, 178, 184, -1, -1, -1, -1, 178, -1, 178, 184, 178, -1, 178, -1, -1, -1, -1, -1, 184, -1, -1, -1, 184, -1, -1, 178, -1, -1, 178, -1, -1, 178, -1, -1, -1, 178, -1, 184, -1, 178, -1, 184, -1, 184, -1, 178, 178],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 59, -1, -1, 59, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 59, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 59, -1, -1, -1, -1, -1, -1, -1, -1, 59, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 59, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 59, -1, -1, -1, -1, 59, -1, -1],
    [-1, -1, 316, 316, -1, 316, -1, -1, -1, 316, -1, -1, 316, -1, -1, 316, 316, 316, 316, -1, -1, -1, -1, -1, -1, -1, 144, -1, 316, -1, 144, -1, -1, 144, 316, -1, -1, -1, -1, -1, 316, 316, -1, -1, 316, -1, 316, 316, 144, -1, -1, -1, -1, 144, -1, -1, -1, 316, -1, -1, 316, -1, -1, -1, 144, -1, -1, 144, -1, 316, -1, -1, -1, 144, -1, -1, -1, 316, -1, -1, -1, -1, -1, -1, -1, -1, 316, -1, 144, -1, 316, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 316, -1, 144, 144, 316, -1, 316, 144, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 346, -1, -1, 346, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 346, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 346, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 332, -1, -1, -1, -1, -1, -1, 323, -1, -1, -1, -1, -1, 314, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 292, -1, -1, -1, -1, -1, 240, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [264, -1, 264, 264, 264, 264, 264, -1, -1, 264, 264, 264, 264, -1, -1, 264, 264, 264, 264, -1, 264, -1, 264, -1, 264, -1, -1, -1, 264, -1, 264, -1, -1, -1, 264, 264, -1, 264, -1, 264, 264, 264, 264, -1, 264, -1, 264, 264, -1, -1, 264, -1, -1, -1, -1, 264, -1, 264, 264, 264, 264, 264, -1, -1, 264, -1, 264, 264, 264, 264, 264, -1, -1, -1, 264, -1, 264, 264, 264, -1, 264, -1, -1, -1, -1, -1, 264, -1, -1, -1, 264, -1, -1, 264, -1, -1, 264, -1, -1, 264, -1, -1, -1, 264, -1, 264, -1, 264, -1, 264, -1, 264, -1, 264, 264],
    [242, -1, 242, 242, 242, 242, 242, -1, -1, 242, 242, 242, 242, -1, -1, 242, 242, 242, 242, -1, 242, -1, 242, -1, 242, -1, -1, -1, 242, -1, 242, -1, -1, -1, 242, 242, -1, 242, -1, 242, 242, 242, 242, -1, 242, -1, 242, 242, -1, -1, 242, -1, -1, -1, -1, 242, -1, 242, 242, 242, 242, 242, -1, -1, 242, -1, 242, 242, 242, 242, 242, -1, -1, -1, 242, -1, 242, 242, 242, -1, 242, -1, -1, -1, -1, -1, 242, -1, -1, -1, 242, -1, -1, 242, -1, -1, 242, -1, -1, 242, -1, -1, -1, 242, -1, 242, -1, 242, -1, 242, -1, 242, -1, 242, 242],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 202, -1, -1, 329, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 202, -1, -1, -1, -1, -1, -1, 202, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, 197, -1, -1, -1, -1, -1, -1, -1, 197, -1, -1, 197, -1, -1, -1, -1, -1, -1, 197, -1, -1, -1, -1, -1, -1, -1, 197, -1, -1, -1, -1, -1, -1, 197, -1, -1, 197, -1, 197, -1, -1, 333, -1, 197, -1, -1, 197, -1, -1, -1, -1, -1, -1, -1, 197, -1, -1, 197, -1, -1, 197, -1, -1, -1, -1, -1, -1, -1, -1, -1, 197, -1, 197, -1, -1, -1, 197, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 197, -1, -1, -1, -1, -1, 197, -1, -1, -1, -1, -1, -1, -1, 197, -1, -1, -1, -1, -1, -1, 197],
    [-1, -1, -1, 172, -1, 172, -1, -1, -1, -1, -1, -1, 172, -1, -1, -1, 172, 172, 172, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 172, -1, -1, -1, -1, -1, -1, -1, -1, -1, 172, 172, -1, -1, 172, -1, 172, 172, -1, -1, -1, -1, 172, -1, -1, -1, -1, 172, -1, -1, 172, -1, -1, -1, 172, -1, -1, -1, -1, 172, 175, -1, -1, -1, -1, -1, -1, 172, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 172, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 172, -1, 172, -1, 172, -1, 172, 172, -1, -1],
    [362, -1, 336, 336, -1, 336, -1, -1, -1, 336, -1, -1, 336, -1, -1, 336, 336, 336, 336, -1, -1, -1, -1, -1, -1, -1, -1, -1, 336, -1, -1, -1, -1, -1, 336, -1, -1, -1, -1, -1, 336, 336, -1, -1, 336, -1, 336, 336, -1, -1, -1, -1, -1, -1, -1, -1, -1, 336, -1, -1, 336, -1, -1, -1, -1, -1, -1, 362, -1, 336, -1, -1, -1, 362, -1, -1, -1, 336, -1, -1, -1, -1, -1, -1, -1, -1, 336, -1, -1, -1, 336, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 336, -1, -1, -1, 336, -1, 336, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 223, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [112, -1, 112, 112, 112, 112, 112, -1, -1, 112, 49, 112, 112, -1, -1, 112, 112, 112, 112, -1, 112, -1, 112, -1, -1, -1, -1, -1, 112, -1, 112, -1, -1, -1, 112, 112, -1, 112, -1, 112, 112, 112, 112, -1, 112, -1, 112, 112, -1, -1, 112, -1, -1, -1, -1, 112, -1, 112, 112, 112, 112, 112, -1, -1, 112, -1, 112, 112, 112, 112, 112, -1, -1, -1, 112, -1, 112, 112, 112, -1, 112, -1, -1, -1, -1, -1, 112, -1, -1, -1, 112, -1, -1, 112, -1, -1, 112, -1, -1, 112, -1, -1, -1, 112, -1, 112, -1, 112, -1, 112, -1, 112, -1, 112, 112],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 32, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 274, 274, -1, 274, -1, -1, -1, 274, -1, -1, 274, -1, -1, 274, 274, 274, 274, -1, -1, -1, -1, -1, -1, -1, -1, -1, 274, -1, -1, -1, -1, 274, 274, -1, -1, -1, -1, -1, 274, 274, -1, -1, 274, -1, 274, 274, -1, -1, -1, -1, -1, -1, -1, -1, -1, 274, -1, -1, 274, -1, -1, -1, 215, -1, -1, -1, -1, 274, -1, -1, -1, -1, -1, -1, -1, 274, -1, -1, -1, -1, -1, -1, -1, -1, 274, -1, -1, -1, 274, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 274, -1, -1, -1, 274, -1, 274, -1, -1, -1],
    [324, -1, 324, 324, -1, 324, -1, -1, -1, 324, -1, -1, 324, -1, -1, 324, 324, 324, 324, -1, -1, -1, -1, -1, -1, -1, -1, -1, 324, -1, -1, -1, -1, -1, 324, -1, -1, -1, -1, -1, 324, 324, -1, -1, 324, -1, 324, 324, -1, -1, -1, -1, -1, -1, -1, -1, -1, 324, -1, -1, 324, -1, -1, -1, -1, -1, -1, 324, -1, 324, -1, -1, -1, 324, -1, -1, -1, 324, -1, -1, -1, -1, -1, -1, -1, -1, 324, -1, -1, -1, 324, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 324, -1, -1, -1, 324, -1, 324, -1, -1, -1],
    [-1, -1, 250, 250, -1, 250, -1, -1, -1, 250, -1, -1, 250, -1, -1, 250, 250, 250, 250, -1, -1, -1, -1, -1, -1, -1, -1, -1, 250, -1, -1, -1, -1, -1, 250, -1, -1, -1, -1, -1, 250, 250, -1, -1, 250, -1, 250, 250, -1, -1, -1, -1, -1, -1, -1, -1, -1, 250, -1, -1, 250, -1, -1, -1, -1, -1, -1, -1, -1, 250, -1, -1, -1, -1, -1, -1, -1, 250, -1, -1, -1, -1, -1, -1, -1, -1, 250, -1, -1, -1, 250, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 250, -1, 257, -1, 250, -1, 250, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 114, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 289, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [23, -1, 23, 23, 23, 23, 23, -1, -1, 23, 23, 23, 23, -1, -1, 23, 23, 23, 23, -1, 23, -1, 23, -1, 65, -1, -1, -1, 23, -1, 23, -1, -1, -1, 23, 23, -1, 23, -1, 23, 23, 23, 23, -1, 23, -1, 23, 23, -1, -1, 23, -1, -1, -1, -1, 23, -1, 23, 23, 23, 23, 23, -1, -1, 23, -1, 23, 23, 23, 23, 23, -1, -1, -1, 23, -1, 23, 23, 23, -1, 23, -1, -1, -1, -1, -1, 23, -1, -1, -1, 23, -1, -1, 23, -1, -1, 23, -1, -1, 23, -1, -1, -1, 23, -1, 23, -1, 23, -1, 23, -1, 23, -1, 23, 23],
    [-1, -1, 220, 220, -1, 220, -1, -1, -1, 220, -1, -1, 220, -1, -1, 220, 220, 220, 220, -1, -1, -1, -1, -1, -1, -1, -1, -1, 220, -1, -1, -1, -1, -1, 220, -1, -1, -1, -1, -1, 220, 220, -1, -1, 220, -1, 220, 220, -1, -1, -1, -1, -1, -1, -1, -1, -1, 220, -1, -1, 220, -1, -1, -1, -1, -1, -1, -1, -1, 220, -1, -1, -1, -1, -1, -1, -1, 220, -1, -1, -1, -1, -1, -1, -1, -1, 220, -1, -1, -1, 220, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 220, -1, -1, -1, 220, -1, 220, -1, -1, -1],
    [-1, -1, 331, 331, -1, 331, -1, -1, -1, 331, -1, -1, 331, -1, -1, 331, 331, 331, 331, -1, -1, -1, -1, -1, -1, -1, -1, -1, 331, -1, -1, -1, -1, 416, 331, -1, -1, -1, -1, -1, 331, 331, -1, -1, 331, -1, 331, 331, -1, -1, -1, -1, -1, -1, -1, -1, -1, 331, -1, -1, 331, -1, -1, -1, -1, -1, -1, -1, -1, 331, -1, -1, -1, -1, -1, -1, -1, 331, -1, -1, -1, -1, -1, -1, -1, -1, 331, -1, -1, -1, 331, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 331, -1, -1, -1, 331, -1, 331, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 35, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 115, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 35, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 138, 138, -1, 138, -1, -1, -1, 138, -1, -1, 138, -1, -1, 138, 138, 138, 138, -1, -1, -1, -1, -1, -1, -1, -1, -1, 138, -1, -1, -1, -1, -1, 138, -1, -1, -1, -1, -1, 138, 138, -1, -1, 138, -1, 138, 138, -1, -1, -1, -1, -1, -1, -1, -1, -1, 138, -1, -1, 138, -1, -1, -1, -1, -1, -1, -1, -1, 138, -1, -1, -1, -1, -1, -1, -1, 138, -1, -1, -1, -1, -1, -1, -1, -1, 138, -1, -1, -1, 138, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 138, -1, -1, -1, 138, -1, 138, -1, -1, -1],
    [-1, 369, -1, -1, 369, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 369, -1, -1, -1, -1, -1, -1, -1, 369, -1, -1, -1, -1, -1, -1, 369, -1, -1, -1, -1, 369, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 369, -1, -1, 369, -1, -1, 369, -1, -1, -1, -1, -1, -1, -1, -1, -1, 369, -1, 369, -1, -1, -1, 369, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 369, -1, -1, -1, -1, -1, 369, -1, -1, -1, -1, -1, -1, -1, 369, -1, -1, -1, -1, -1, -1, 369],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 9, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 185, -1, -1, 185, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 185, -1, -1, 185, -1, -1, -1, -1, -1, -1, 185, -1, -1, -1, -1, -1, -1, 185, 185, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 185, -1, -1, -1, -1, -1, -1, -1, -1, 185, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 185, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 185, -1, -1, -1, -1, 185, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 294, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 294, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 294, -1, -1, -1, -1, 294, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 33, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 162, -1, -1, -1, -1, -1, 297, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, 17, -1, -1, -1, -1, -1, -1, -1, 17, -1, -1, 17, -1, -1, -1, -1, -1, -1, 17, -1, -1, -1, -1, -1, -1, -1, 17, -1, -1, -1, -1, -1, -1, 17, -1, -1, 17, -1, 17, -1, -1, -1, -1, 17, -1, -1, 17, -1, -1, -1, -1, -1, -1, -1, 17, -1, -1, 17, -1, -1, 17, -1, -1, -1, -1, -1, -1, -1, -1, -1, 17, -1, 17, -1, -1, -1, 17, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 17, -1, -1, -1, -1, -1, 17, -1, -1, -1, -1, -1, -1, -1, 17, -1, -1, -1, -1, -1, -1, 17],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 140, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 361, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, 401, -1, -1, -1, -1, -1, -1, -1, 321, -1, -1, 321, -1, -1, -1, -1, -1, -1, 401, -1, -1, -1, -1, -1, -1, -1, 401, -1, -1, -1, -1, -1, -1, 401, -1, -1, 321, -1, 401, -1, -1, -1, -1, 321, -1, -1, 401, -1, -1, -1, -1, -1, -1, -1, 401, -1, -1, 401, -1, -1, 401, -1, -1, -1, -1, -1, -1, -1, -1, -1, 401, -1, 401, -1, -1, -1, 401, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 401, -1, -1, -1, -1, -1, 401, -1, -1, -1, -1, -1, -1, -1, 401, -1, -1, -1, -1, -1, -1, 401],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 268, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 248, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 60, 235, -1, 26, 72, -1, -1, 14, 249, 341, 365, -1, -1, 58, 90, 83, 5, -1, -1, -1, -1, -1, -1, -1, -1, -1, 38, -1, -1, -1, -1, -1, 275, -1, -1, -1, -1, 258, 53, 199, -1, -1, 328, -1, 228, 40, -1, -1, -1, -1, -1, -1, -1, 89, -1, 167, -1, 1, 408, 227, -1, -1, -1, -1, 370, -1, 81, 243, -1, -1, -1, -1, -1, -1, -1, 61, 73, -1, -1, -1, -1, -1, -1, -1, 216, -1, -1, -1, 181, -1, -1, -1, -1, -1, 252, -1, -1, -1, -1, -1, -1, 219, -1, -1, -1, -1, -1, 143, -1, 105, -1, 419, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 236, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 236, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 236, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 236, -1, -1, -1, -1, 236, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 390, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 335, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 342, -1, -1, -1, -1, -1, 319, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 106, -1, -1, -1, -1, -1, 106, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 104, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 412, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 376, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [269, -1, 269, 269, -1, 269, -1, -1, -1, 269, -1, -1, 269, -1, -1, 269, 269, 269, 269, -1, -1, -1, -1, -1, -1, -1, -1, -1, 269, -1, -1, -1, -1, -1, 269, -1, -1, -1, -1, -1, 269, 269, -1, -1, 269, -1, 269, 269, -1, -1, -1, -1, -1, -1, -1, -1, -1, 269, -1, -1, 269, -1, -1, -1, -1, -1, -1, 269, -1, 269, -1, -1, -1, 269, -1, -1, -1, 269, -1, -1, -1, -1, -1, -1, -1, -1, 269, -1, -1, -1, 269, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 269, -1, -1, -1, 269, -1, 269, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 155, -1, -1, 155, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 155, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 155, -1, -1, -1, -1, -1, -1, -1, -1, 155, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 155, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 155, -1, -1, -1, -1, 155, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 135, -1, -1, 135, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 135, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 135, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 135, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 84, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 231, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 304, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 3, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [93, -1, -1, -1, 19, -1, 123, -1, -1, -1, -1, 123, -1, -1, -1, -1, -1, -1, -1, -1, 79, -1, 19, -1, -1, -1, -1, -1, -1, -1, 19, -1, -1, -1, -1, -1, -1, 19, -1, 79, -1, -1, 19, -1, -1, -1, -1, -1, -1, -1, 19, -1, -1, -1, -1, 79, -1, -1, 19, 414, -1, 19, -1, -1, 19, -1, 51, 19, 414, -1, -1, -1, -1, -1, 19, -1, 19, -1, 414, -1, 19, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 19, -1, -1, 123, -1, -1, 19, -1, -1, -1, 414, -1, -1, -1, 19, -1, -1, -1, -1, -1, 51, 19],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 221, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [62, -1, 62, 62, 62, 62, 62, -1, -1, 62, -1, 62, 62, -1, -1, 62, 62, 62, 62, -1, 62, -1, 62, -1, -1, -1, -1, -1, 62, -1, 62, -1, -1, -1, 62, -1, -1, 62, -1, 62, 62, 62, 62, -1, 62, -1, 62, 62, -1, -1, 62, -1, -1, -1, -1, 62, -1, 62, 62, 62, 62, 62, -1, -1, 62, -1, 62, 62, 62, 62, 62, -1, -1, -1, 62, -1, 62, 62, 62, -1, 62, -1, -1, -1, -1, -1, 62, -1, -1, -1, 62, -1, -1, 62, -1, -1, 62, -1, -1, 62, -1, -1, -1, 62, -1, 62, -1, 62, -1, 62, -1, 62, -1, 62, 62],
    [75, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [196, -1, -1, -1, 218, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 218, -1, -1, -1, -1, -1, -1, -1, 218, -1, -1, -1, -1, -1, -1, 218, -1, -1, -1, -1, 218, -1, -1, -1, -1, -1, -1, -1, 218, -1, -1, -1, -1, -1, -1, -1, 218, -1, -1, 218, -1, -1, 218, -1, -1, -1, -1, -1, -1, -1, -1, -1, 218, -1, 218, -1, -1, -1, 218, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 218, -1, -1, -1, -1, -1, 218, -1, -1, -1, -1, -1, -1, -1, 218, -1, -1, -1, -1, -1, -1, 218],
    [217, -1, -1, -1, 96, -1, -1, 327, -1, -1, -1, -1, -1, 146, 134, -1, -1, -1, -1, 131, -1, 44, -1, -1, -1, 171, -1, 337, -1, 271, 224, 245, -1, 322, -1, -1, -1, -1, 76, -1, -1, -1, -1, 358, -1, 210, -1, -1, 101, 339, -1, 22, 251, -1, 238, -1, 400, -1, -1, -1, -1, -1, 94, 39, -1, 15, -1, 192, -1, -1, 194, 237, 2, 239, -1, 371, 272, -1, -1, 366, -1, 288, 168, 206, -1, -1, -1, 267, -1, 78, -1, 34, -1, -1, -1, 24, -1, 70, 211, -1, -1, -1, 159, -1, 207, -1, 86, -1, -1, -1, 233, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 37, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 298, -1, -1, 298, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 298, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 298, -1, -1, -1, -1, -1, -1, -1, -1, 298, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 298, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 298, -1, -1, -1, -1, 298, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 126, -1, -1, 126, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 126, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 126, -1, -1, -1, -1, -1, -1, -1, -1, 126, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 126, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 126, -1, -1, -1, -1, 126, -1, -1],
    [-1, -1, -1, 225, -1, 225, -1, -1, -1, -1, -1, -1, 50, -1, -1, -1, 225, 225, 225, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 50, 225, -1, -1, 225, -1, 225, 50, -1, -1, -1, -1, -1, -1, -1, -1, -1, 225, -1, -1, 225, -1, -1, -1, -1, -1, -1, -1, -1, 225, -1, -1, -1, -1, -1, -1, -1, 225, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 225, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 225, -1, -1, -1, 225, -1, 225, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 241, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 330, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 283, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 52, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [367, -1, -1, -1, 367, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 367, -1, -1, -1, -1, -1, -1, -1, 367, -1, -1, -1, -1, -1, -1, 367, -1, -1, -1, -1, 367, -1, -1, -1, -1, -1, 367, -1, 367, -1, -1, -1, -1, -1, -1, -1, 367, -1, -1, 367, -1, -1, 367, -1, -1, -1, -1, -1, -1, -1, -1, -1, 367, -1, 367, -1, -1, -1, 367, -1, -1, -1, -1, -1, -1, 367, -1, -1, -1, -1, -1, 367, -1, -1, -1, -1, -1, 367, -1, -1, -1, -1, -1, -1, 367, 367, -1, -1, -1, -1, -1, -1, 367],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 380, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 353, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 354, -1, -1, -1, -1, -1, 354, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 265, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 141, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 182, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 111, 111, -1, 111, -1, -1, -1, 111, -1, -1, 111, -1, -1, 111, 111, 111, 111, -1, -1, -1, -1, -1, -1, -1, -1, -1, 111, -1, -1, -1, -1, -1, 111, -1, -1, -1, -1, -1, 111, 111, -1, -1, 111, -1, 111, 111, -1, -1, -1, -1, -1, -1, -1, -1, -1, 111, -1, -1, 111, -1, -1, -1, -1, -1, -1, -1, -1, 111, -1, -1, -1, -1, -1, -1, -1, 111, -1, -1, -1, -1, -1, -1, -1, -1, 111, -1, -1, -1, 111, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 111, -1, -1, -1, 111, -1, 111, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, 280, -1, -1, -1, -1, 147, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 286, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 25, -1, -1, 389, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 389, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 389, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 389, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 25, -1, -1, -1, -1, 25, -1, -1],
    [-1, -1, -1, -1, 195, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 195, -1, -1, -1, -1, -1, -1, -1, 195, -1, -1, -1, -1, -1, -1, 195, -1, -1, -1, -1, 195, -1, -1, -1, -1, -1, -1, -1, 195, -1, -1, -1, -1, -1, -1, -1, 195, -1, -1, 195, -1, -1, 195, -1, -1, 195, -1, -1, -1, -1, -1, -1, 195, -1, 195, -1, -1, -1, 195, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 195, -1, -1, -1, -1, -1, 195, -1, -1, -1, -1, -1, -1, -1, 195, -1, -1, -1, -1, -1, -1, 195],
    [-1, -1, 363, 363, -1, 363, -1, -1, -1, 363, -1, -1, 363, -1, -1, 363, 363, 363, 363, -1, -1, -1, -1, -1, -1, -1, -1, -1, 363, -1, -1, -1, -1, -1, 363, -1, -1, -1, -1, -1, 363, 363, -1, -1, 363, -1, 363, 363, -1, -1, -1, -1, -1, -1, -1, -1, -1, 363, -1, -1, 363, -1, -1, -1, -1, -1, -1, -1, -1, 363, -1, -1, -1, -1, -1, -1, -1, 363, -1, -1, -1, -1, -1, -1, -1, -1, 363, -1, -1, -1, 363, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 363, -1, -1, -1, 363, -1, 363, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 425, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 98, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 368, 368, -1, 368, -1, -1, -1, 368, -1, -1, 368, -1, -1, 368, 368, 368, 368, -1, -1, -1, -1, -1, -1, -1, -1, -1, 368, -1, -1, -1, -1, -1, 368, -1, -1, -1, -1, -1, 368, 368, -1, -1, 368, -1, 368, 368, -1, -1, -1, -1, -1, -1, -1, -1, -1, 368, -1, -1, 368, -1, -1, -1, -1, -1, -1, -1, -1, 368, -1, -1, -1, -1, -1, -1, -1, 368, -1, -1, -1, -1, -1, -1, -1, -1, 368, -1, -1, -1, 368, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 368, -1, -1, -1, 368, -1, 368, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 377, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 403, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 377, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [357, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 405, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 384, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 57, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 384, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 384, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 127, -1, -1, 127, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 127, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 127, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 127, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 290, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 290, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 290, -1, -1, -1, -1, -1, -1, -1, -1],
    [12, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [387, -1, 166, 166, -1, 166, -1, -1, -1, 166, -1, -1, 166, -1, -1, 166, 166, 166, 166, -1, -1, -1, -1, -1, -1, -1, 166, -1, 166, -1, 166, -1, -1, 166, 166, -1, -1, -1, -1, -1, 166, 166, -1, -1, 166, -1, 166, 166, 166, -1, -1, -1, 166, 166, -1, -1, -1, 166, -1, -1, 166, -1, -1, -1, 166, -1, -1, 166, -1, 166, -1, -1, -1, 166, -1, -1, -1, 166, -1, -1, -1, -1, -1, -1, -1, -1, 166, -1, 166, -1, 166, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 166, -1, 166, 166, 166, -1, 166, 166, -1, -1],
    [116, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 42, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 187, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 395, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 395, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 395, -1, -1, -1, -1, 395, -1, -1],
    [247, -1, 300, 300, 247, 300, 300, 247, -1, 300, 300, 300, 300, 247, 247, 300, 300, 300, 300, 247, -1, 247, 299, -1, -1, 247, -1, 247, 300, 247, 247, 247, -1, 247, 300, -1, -1, 299, 247, 300, 300, 300, 299, 247, 300, 247, 300, 300, 247, 247, -1, 247, 247, -1, 247, 300, 247, 300, -1, 300, 300, 300, 247, 247, -1, 247, 300, 247, 300, 300, 247, 247, 247, 247, 299, 247, 247, 300, 300, 247, 279, 247, 247, 247, -1, -1, 300, 247, -1, 247, 300, 247, -1, 299, -1, 247, 300, 247, 247, 299, -1, 85, 247, 300, 247, -1, 247, 164, -1, 300, 247, 300, -1, 300, -1],
    [163, -1, -1, -1, 163, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 163, -1, -1, -1, -1, -1, -1, -1, 163, -1, -1, -1, -1, -1, -1, 163, -1, -1, -1, -1, 163, -1, -1, -1, -1, -1, 173, -1, 163, -1, -1, -1, -1, -1, -1, -1, 163, -1, -1, 163, -1, -1, 163, -1, -1, -1, -1, -1, -1, -1, -1, -1, 163, -1, 163, -1, -1, -1, 163, -1, -1, -1, -1, -1, -1, 173, -1, -1, -1, -1, -1, 163, -1, -1, -1, -1, -1, 163, -1, -1, -1, -1, -1, -1, 173, 163, -1, -1, -1, -1, -1, -1, 163],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 200, -1, -1, -1, -1, -1, -1, -1, -1, 229, -1, -1, -1, -1, -1, -1, -1, -1, -1, 253, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 287, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [350, 309, -1, -1, 4, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 309, -1, -1, -1, -1, -1, -1, -1, 309, -1, -1, 4, -1, -1, -1, 309, -1, -1, -1, -1, 309, -1, -1, 4, -1, -1, 350, 4, 350, -1, 4, -1, -1, -1, -1, -1, 309, -1, -1, 309, -1, -1, 309, -1, -1, 4, -1, -1, -1, -1, -1, 4, 309, -1, 4, -1, -1, -1, 309, -1, -1, -1, -1, -1, -1, 350, -1, -1, -1, -1, -1, 309, -1, -1, -1, -1, 4, 309, 4, -1, -1, -1, -1, -1, 4, 309, -1, -1, -1, -1, -1, -1, 309],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 208, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 122, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, 160, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 160, -1, -1, -1, -1, -1, -1, -1, 160, -1, -1, -1, -1, -1, -1, 160, -1, -1, -1, -1, 160, -1, -1, -1, -1, -1, -1, -1, 160, -1, -1, -1, -1, -1, -1, -1, 160, -1, -1, 160, -1, -1, 158, -1, -1, -1, -1, -1, -1, -1, -1, -1, 160, -1, 160, -1, -1, -1, 160, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 160, -1, -1, -1, -1, -1, 160, -1, -1, -1, -1, -1, -1, -1, 160, -1, -1, -1, -1, -1, -1, 160],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 424, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, 43, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 177, -1, -1, -1, -1, -1, -1, 43, -1, -1, -1, -1, -1, -1, -1, 43, -1, -1, -1, -1, -1, -1, 43, -1, -1, -1, -1, 43, -1, -1, -1, -1, -1, -1, -1, 43, -1, -1, -1, -1, -1, -1, -1, 43, -1, -1, 43, -1, -1, 43, -1, -1, -1, -1, -1, -1, -1, -1, -1, 43, -1, 43, -1, -1, -1, 43, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 43, -1, -1, -1, -1, -1, 43, -1, -1, -1, -1, -1, -1, -1, 43, -1, -1, -1, -1, -1, -1, 43],
    [145, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 41, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 169, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 179, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 169, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 285, -1, -1, -1, -1, -1, 263, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, 10, -1, 10, -1, -1, -1, -1, -1, -1, 10, -1, -1, -1, 10, 10, 10, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 10, -1, -1, -1, -1, -1, -1, -1, -1, -1, 10, 10, -1, -1, 10, -1, 10, 10, -1, -1, -1, -1, 10, -1, -1, -1, -1, 10, -1, -1, 10, -1, -1, -1, 10, -1, -1, -1, -1, 10, -1, -1, -1, -1, -1, -1, -1, 10, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 10, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 10, -1, 10, -1, 10, -1, 10, 10, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 13, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 64, -1, -1, -1, -1, 191, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 82, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 30, -1, -1, -1, -1, -1, 364, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 420, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 313, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 36, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 262, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 174, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 296, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 174, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, 153, -1, 77, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 209, 308, 68, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 55, -1, -1, 293, -1, 45, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 54, -1, -1, 305, -1, -1, -1, -1, -1, -1, -1, -1, 7, -1, -1, -1, -1, -1, -1, -1, 150, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 110, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 352, -1, -1, -1, 349, -1, 91, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 74, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 402, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 186, -1, -1, 186, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 186, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 183, -1, -1, -1, -1, -1, -1, -1, -1, 186, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 186, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 186, -1, -1, -1, -1, 186, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 278, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 46, -1, -1, -1, -1, -1, -1, 307, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 374, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [418, -1, 418, 418, 418, 418, 418, -1, -1, 418, -1, 418, 418, -1, -1, 418, 418, 418, 418, -1, 418, -1, 418, -1, -1, -1, -1, -1, 418, -1, 418, -1, -1, -1, 418, -1, -1, 418, -1, 418, 418, 418, 418, -1, 418, -1, 418, 418, -1, -1, 418, -1, -1, -1, -1, 418, -1, 418, 418, 418, 418, 418, -1, -1, 418, -1, 418, 418, 418, 418, 295, -1, -1, -1, 418, -1, 418, 418, 418, -1, 418, -1, -1, -1, -1, -1, 418, -1, -1, -1, 418, -1, -1, 418, -1, -1, 418, -1, -1, 418, -1, -1, -1, 418, -1, 418, -1, 418, -1, 418, -1, 418, -1, 418, 418],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 71, -1, -1, -1, -1, -1, -1, -1, 198, -1, -1, -1, -1, -1, -1, -1, -1, 375, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, 189, -1, 189, -1, -1, -1, -1, -1, -1, 189, -1, -1, -1, 189, 189, 189, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 193, -1, -1, -1, -1, -1, -1, -1, -1, -1, 189, 189, -1, -1, 189, -1, 189, 189, -1, -1, -1, -1, 193, -1, -1, -1, -1, 189, -1, -1, 189, -1, -1, -1, 193, -1, -1, -1, -1, 189, -1, -1, -1, -1, -1, -1, -1, 189, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 189, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 189, -1, 193, -1, 189, -1, 189, 193, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 157, -1, -1, 161, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 161, -1, -1, 161, -1, -1, -1, -1, -1, -1, 157, -1, -1, -1, -1, -1, -1, 157, 161, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 161, -1, -1, -1, -1, -1, -1, -1, -1, 161, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 161, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 161, -1, -1, -1, -1, 161, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 409, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, 226, -1, -1, -1, -1, -1, -1, -1, 276, -1, -1, 276, -1, -1, -1, -1, -1, -1, 226, -1, -1, -1, -1, -1, -1, -1, 226, -1, -1, -1, -1, -1, -1, 226, -1, -1, 276, -1, 226, -1, -1, -1, -1, 276, -1, -1, 226, -1, -1, -1, -1, -1, -1, -1, 226, -1, -1, 226, -1, -1, 226, -1, -1, -1, -1, -1, -1, -1, -1, -1, 226, -1, 226, -1, -1, -1, 226, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 226, -1, -1, -1, -1, -1, 226, -1, -1, -1, -1, -1, -1, -1, 226, -1, -1, -1, -1, -1, -1, 226],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 119, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 119, -1, -1, 388, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 119, -1, -1, -1, -1, 119, -1, -1],
    [-1, -1, -1, -1, 63, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 63, -1, -1, -1, -1, -1, -1, -1, 63, -1, -1, 348, -1, -1, -1, 63, -1, -1, -1, -1, 63, -1, -1, -1, -1, -1, -1, -1, 63, -1, -1, -1, -1, -1, -1, -1, 63, -1, -1, 63, -1, -1, 63, -1, -1, 348, -1, -1, -1, -1, -1, -1, 63, -1, 63, -1, -1, -1, 63, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 63, -1, -1, -1, -1, -1, 63, -1, -1, -1, -1, -1, -1, -1, 63, -1, -1, -1, -1, -1, -1, 63],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 132, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 21, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 281, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 317, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 27, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 121, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 301, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 301, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 301, -1, -1, -1, -1, 301, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 80, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 139, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 80, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 80, -1, -1, -1, -1, 80, -1, -1],
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
  def _DIRECT_ABSTRACT_DECLARATOR_SUB0(self, depth=0, tracer=None):
    rule = self.rule(115)
    tree = ParseTree( NonTerminal(115, self.getAtomString(115)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 95:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(30, tracer) # lparen
      tree.add(t)
      subtree = self._ABSTRACT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(33, tracer) # rparen
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN8(self, depth=0, tracer=None):
    rule = self.rule(116)
    tree = ParseTree( NonTerminal(116, self.getAtomString(116)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [33, 48, 30, 88, 73]):
      return tree
    if self.sym == None:
      return tree
    if rule == 201:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DIRECT_ABSTRACT_DECLARATOR_SUB0(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN38(self, depth=0, tracer=None):
    rule = self.rule(117)
    tree = ParseTree( NonTerminal(117, self.getAtomString(117)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [70]):
      return tree
    if self.sym == None:
      return tree
    if rule == 6:
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
    elif self.sym.getId() in [58, 30, 74, 114, 99, 64, 37, 93, 80, 4, 76, 107, 22, 61, 50, 42]:
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
  def _INIT_DECLARATOR(self, depth=0, tracer=None):
    rule = self.rule(118)
    tree = ParseTree( NonTerminal(118, self.getAtomString(118)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 213:
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
    elif self.sym.getId() in [112, 30, 107]:
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
  def _DECLARATION_SPECIFIER(self, depth=0, tracer=None):
    rule = self.rule(119)
    tree = ParseTree( NonTerminal(119, self.getAtomString(119)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 261:
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
    elif rule == 386:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._FUNCTION_SPECIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 391:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STORAGE_CLASS_SPECIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _FOR_INIT(self, depth=0, tracer=None):
    rule = self.rule(120)
    tree = ParseTree( NonTerminal(120, self.getAtomString(120)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [67]):
      return tree
    if self.sym == None:
      return tree
    if rule == 273:
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
    elif rule == 351:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [58, 30, 74, 114, 99, 64, 37, 93, 80, 4, 76, 107, 22, 61, 50, 42]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    return tree
  def _FOR_COND(self, depth=0, tracer=None):
    rule = self.rule(121)
    tree = ParseTree( NonTerminal(121, self.getAtomString(121)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 190:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(67, tracer) # semi
      tree.add(t)
      subtree = self._EXPRESSION_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN24(self, depth=0, tracer=None):
    rule = self.rule(122)
    tree = ParseTree( NonTerminal(122, self.getAtomString(122)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [52, 86, 12, 2, 3, 88, 5, 41, 60, 64, 9, 112, 67, 15, 73, 77, 18, 34, 107, 26, 28, 30, 53, 105, 111, 108, 109, 90, 57, 17, 40, 48, 69, 46, 47, 44, 16, 33]):
      return tree
    if self.sym == None:
      return tree
    if rule == 394:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._ENUM_SPECIFIER_BODY(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _DIRECT_ABSTRACT_DECLARATOR_SUB1(self, depth=0, tracer=None):
    rule = self.rule(123)
    tree = ParseTree( NonTerminal(123, self.getAtomString(123)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 230:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(30, tracer) # lparen
      tree.add(t)
      subtree = self._DIRECT_ABSTRACT_DECLARATOR_SUB2(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(33, tracer) # rparen
      tree.add(t)
      return tree
    elif rule == 413:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(48, tracer) # lsquare
      tree.add(t)
      subtree = self._DIRECT_ABSTRACT_DECLARATOR_EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(45, tracer) # rsquare
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN9(self, depth=0, tracer=None):
    rule = self.rule(124)
    tree = ParseTree( NonTerminal(124, self.getAtomString(124)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [33, 88, 73]):
      return tree
    if self.sym == None:
      return tree
    if rule == 214:
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
  def __GEN14(self, depth=0, tracer=None):
    rule = self.rule(125)
    tree = ParseTree( NonTerminal(125, self.getAtomString(125)), tracer )
    tree.list = 'slist'
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 232:
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
    elif self.sym.getId() in [58, 30, 74, 114, 99, 64, 37, 93, 80, 4, 76, 107, 22, 61, 50, 42]:
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
  def _BLOCK_ITEM(self, depth=0, tracer=None):
    rule = self.rule(126)
    tree = ParseTree( NonTerminal(126, self.getAtomString(126)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 178:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 184:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DECLARATION(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [58, 30, 74, 114, 99, 64, 37, 93, 80, 4, 76, 107, 22, 61, 50, 42]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _POINTER(self, depth=0, tracer=None):
    rule = self.rule(127)
    tree = ParseTree( NonTerminal(127, self.getAtomString(127)), tracer )
    tree.list = False
    if self.sym == None:
      return tree
    if rule == 59:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN36(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN2(self, depth=0, tracer=None):
    rule = self.rule(128)
    tree = ParseTree( NonTerminal(128, self.getAtomString(128)), tracer )
    tree.list = 'mlist'
    if self.sym != None and (self.sym.getId() in [26, 112, 53, 73, 108, 64, 30, 67, 48, 88, 107, 33]):
      return tree
    if self.sym == None:
      return tree
    if rule == 316:
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
  def _ABSTRACT_DECLARATOR(self, depth=0, tracer=None):
    rule = self.rule(129)
    tree = ParseTree( NonTerminal(129, self.getAtomString(129)), tracer )
    tree.list = False
    if self.sym == None:
      return tree
    if rule == 346:
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
  def _STORAGE_CLASS_SPECIFIER(self, depth=0, tracer=None):
    rule = self.rule(130)
    tree = ParseTree( NonTerminal(130, self.getAtomString(130)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 240:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(34, tracer) # auto
      tree.add(t)
      return tree
    elif rule == 292:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(28, tracer) # register
      tree.add(t)
      return tree
    elif rule == 314:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(15, tracer) # static
      tree.add(t)
      return tree
    elif rule == 323:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(9, tracer) # extern
      tree.add(t)
      return tree
    elif rule == 332:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(2, tracer) # typedef
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _ELSE_IF_STATEMENT_LIST(self, depth=0, tracer=None):
    rule = self.rule(132)
    tree = ParseTree( NonTerminal(132, self.getAtomString(132)), tracer )
    tree.list = False
    if self.sym == None:
      return tree
    if rule == 264:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN41(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN39(self, depth=0, tracer=None):
    rule = self.rule(133)
    tree = ParseTree( NonTerminal(133, self.getAtomString(133)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [2, 3, 74, 6, 35, 10, 9, 11, 70, 15, 4, 61, 58, 93, 22, 34, 42, 28, 30, 105, 0, 57, 17, 37, 40, 41, 44, 69, 47, 113, 16, 50, 103, 12, 18, 59, 114, 64, 5, 67, 68, 109, 20, 76, 78, 77, 90, 55, 86, 39, 96, 60, 99, 46, 107, 80, 111, 66]):
      return tree
    if self.sym == None:
      return tree
    if rule == 242:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._ELSE_IF_STATEMENT_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _DIRECT_DECLARATOR_MODIFIER(self, depth=0, tracer=None):
    rule = self.rule(134)
    tree = ParseTree( NonTerminal(134, self.getAtomString(134)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 202:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._TYPE_QUALIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 329:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(15, tracer) # static
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _DIRECT_ABSTRACT_DECLARATOR_EXPR(self, depth=0, tracer=None):
    rule = self.rule(135)
    tree = ParseTree( NonTerminal(135, self.getAtomString(135)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [45]):
      return tree
    if self.sym == None:
      return tree
    if rule == 197:
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
    elif rule == 260:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(64, tracer) # asterisk
      tree.add(t)
      return tree
    elif self.sym.getId() in [58, 30, 74, 114, 99, 64, 37, 93, 80, 4, 76, 107, 22, 61, 50, 42]:
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
  def __GEN19(self, depth=0, tracer=None):
    rule = self.rule(136)
    tree = ParseTree( NonTerminal(136, self.getAtomString(136)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [70]):
      return tree
    if self.sym == None:
      return tree
    if rule == 172:
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
    elif self.sym.getId() in [112, 30, 107]:
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
  def __GEN6(self, depth=0, tracer=None):
    rule = self.rule(137)
    tree = ParseTree( NonTerminal(137, self.getAtomString(137)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [67, 0, 73]):
      return tree
    if self.sym == None:
      return tree
    if rule == 336:
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
  def _ELSE_STATEMENT(self, depth=0, tracer=None):
    rule = self.rule(138)
    tree = ParseTree( NonTerminal(138, self.getAtomString(138)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 223:
      tree.astTransform = AstTransformNodeCreator('Else', {'statement': 1})
      t = self.expect(10, tracer) # else
      tree.add(t)
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(35, tracer) # endif
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN40(self, depth=0, tracer=None):
    rule = self.rule(139)
    tree = ParseTree( NonTerminal(139, self.getAtomString(139)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [2, 3, 74, 6, 35, 9, 11, 70, 15, 4, 61, 58, 93, 22, 34, 42, 28, 30, 105, 0, 57, 17, 37, 40, 41, 44, 69, 47, 113, 16, 50, 103, 12, 18, 59, 114, 64, 5, 67, 68, 109, 20, 76, 78, 77, 90, 55, 86, 39, 96, 60, 99, 46, 107, 80, 111, 66]):
      return tree
    if self.sym == None:
      return tree
    if rule == 49:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._ELSE_STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _TRANSLATION_UNIT(self, depth=0, tracer=None):
    rule = self.rule(140)
    tree = ParseTree( NonTerminal(140, self.getAtomString(140)), tracer )
    tree.list = False
    if self.sym == None:
      return tree
    if rule == 32:
      tree.astTransform = AstTransformNodeCreator('TranslationUnit', {'external_declarations': 0})
      subtree = self.__GEN0(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _DIRECT_ABSTRACT_DECLARATOR_SUB2(self, depth=0, tracer=None):
    rule = self.rule(141)
    tree = ParseTree( NonTerminal(141, self.getAtomString(141)), tracer )
    tree.list = False
    if self.sym == None:
      return tree
    if rule == 215:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(64, tracer) # asterisk
      tree.add(t)
      return tree
    elif rule == 274:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN10(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN5(self, depth=0, tracer=None):
    rule = self.rule(142)
    tree = ParseTree( NonTerminal(142, self.getAtomString(142)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [67, 0, 73]):
      return tree
    if self.sym == None:
      return tree
    if rule == 324:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DECLARATION_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _DIRECT_DECLARATOR_PARAMETER_LIST(self, depth=0, tracer=None):
    rule = self.rule(143)
    tree = ParseTree( NonTerminal(143, self.getAtomString(143)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 250:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PARAMETER_TYPE_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 257:
      tree.astTransform = AstTransformNodeCreator('ParameterList', {'identifiers': 0})
      subtree = self.__GEN32(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN0(self, depth=0, tracer=None):
    rule = self.rule(144)
    tree = ParseTree( NonTerminal(144, self.getAtomString(144)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [-1]):
      return tree
    if self.sym == None:
      return tree
    if rule == 114:
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
  def _ELSE_IF_STATEMENT(self, depth=0, tracer=None):
    rule = self.rule(145)
    tree = ParseTree( NonTerminal(145, self.getAtomString(145)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 289:
      tree.astTransform = AstTransformNodeCreator('ElseIf', {'statement': 4, 'condition': 2})
      t = self.expect(24, tracer) # else_if
      tree.add(t)
      t = self.expect(30, tracer) # lparen
      tree.add(t)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(33, tracer) # rparen
      tree.add(t)
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(35, tracer) # endif
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN41(self, depth=0, tracer=None):
    rule = self.rule(146)
    tree = ParseTree( NonTerminal(146, self.getAtomString(146)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [2, 3, 74, 6, 35, 10, 9, 11, 70, 15, 4, 61, 58, 93, 22, 34, 42, 28, 30, 105, 0, 57, 17, 37, 40, 41, 44, 69, 47, 113, 16, 50, 103, 12, 18, 59, 114, 64, 5, 67, 68, 109, 20, 76, 78, 77, 90, 55, 86, 39, 96, 60, 99, 46, 107, 80, 111, 66]):
      return tree
    if self.sym == None:
      return tree
    if rule == 65:
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
    rule = self.rule(147)
    tree = ParseTree( NonTerminal(147, self.getAtomString(147)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 220:
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
  def __GEN10(self, depth=0, tracer=None):
    rule = self.rule(148)
    tree = ParseTree( NonTerminal(148, self.getAtomString(148)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [33]):
      return tree
    if self.sym == None:
      return tree
    if rule == 331:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PARAMETER_TYPE_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _ENUMERATOR_ASSIGNMENT(self, depth=0, tracer=None):
    rule = self.rule(149)
    tree = ParseTree( NonTerminal(149, self.getAtomString(149)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [100, 73]):
      return tree
    if self.sym == None:
      return tree
    if rule == 115:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(87, tracer) # assign
      tree.add(t)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN1(self, depth=0, tracer=None):
    rule = self.rule(150)
    tree = ParseTree( NonTerminal(150, self.getAtomString(150)), tracer )
    tree.list = 'mlist'
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 138:
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
  def __GEN42(self, depth=0, tracer=None):
    rule = self.rule(151)
    tree = ParseTree( NonTerminal(151, self.getAtomString(151)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 369:
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
  def _ENUMERATOR(self, depth=0, tracer=None):
    rule = self.rule(152)
    tree = ParseTree( NonTerminal(152, self.getAtomString(152)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 9:
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
  def _TYPE_QUALIFIER_LIST_OPT(self, depth=0, tracer=None):
    rule = self.rule(153)
    tree = ParseTree( NonTerminal(153, self.getAtomString(153)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [112, 15, 73, 88, 30, 33, 48, 64, 107]):
      return tree
    if self.sym == None:
      return tree
    if rule == 185:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN27(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN11(self, depth=0, tracer=None):
    rule = self.rule(154)
    tree = ParseTree( NonTerminal(154, self.getAtomString(154)), tracer )
    tree.list = 'slist'
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 294:
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
    elif self.sym.getId() in [112, 30, 107]:
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
  def __GEN43(self, depth=0, tracer=None):
    rule = self.rule(155)
    tree = ParseTree( NonTerminal(155, self.getAtomString(155)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 33:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(73, tracer) # comma
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
  def __GEN12(self, depth=0, tracer=None):
    rule = self.rule(156)
    tree = ParseTree( NonTerminal(156, self.getAtomString(156)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in [67]):
      return tree
    if self.sym == None:
      return tree
    if rule == 297:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(73, tracer) # comma
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
  def _DIRECT_DECLARATOR_EXPR(self, depth=0, tracer=None):
    rule = self.rule(157)
    tree = ParseTree( NonTerminal(157, self.getAtomString(157)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 17:
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
    elif self.sym.getId() in [58, 30, 74, 114, 99, 64, 37, 93, 80, 4, 76, 107, 22, 61, 50, 42]:
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
  def _TYPE_NAME(self, depth=0, tracer=None):
    rule = self.rule(158)
    tree = ParseTree( NonTerminal(158, self.getAtomString(158)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 140:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(18, tracer) # int
      tree.add(t)
      return tree
    elif rule == 361:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(44, tracer) # char
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN28(self, depth=0, tracer=None):
    rule = self.rule(160)
    tree = ParseTree( NonTerminal(160, self.getAtomString(160)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [58, 30, 4, 114, 99, 64, 37, 80, 74, 61, 76, 107, 22, 93, 50, 42]):
      return tree
    if self.sym == None:
      return tree
    if rule == 321:
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
  def _FOR_INCR(self, depth=0, tracer=None):
    rule = self.rule(161)
    tree = ParseTree( NonTerminal(161, self.getAtomString(161)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [33]):
      return tree
    if self.sym == None:
      return tree
    if rule == 248:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(67, tracer) # semi
      tree.add(t)
      subtree = self._EXPRESSION_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _KEYWORD(self, depth=0, tracer=None):
    rule = self.rule(162)
    tree = ParseTree( NonTerminal(162, self.getAtomString(162)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 1:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(59, tracer) # continue
      tree.add(t)
      return tree
    elif rule == 5:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(18, tracer) # int
      tree.add(t)
      return tree
    elif rule == 14:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(9, tracer) # extern
      tree.add(t)
      return tree
    elif rule == 26:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(5, tracer) # long
      tree.add(t)
      return tree
    elif rule == 38:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(28, tracer) # register
      tree.add(t)
      return tree
    elif rule == 40:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(47, tracer) # restrict
      tree.add(t)
      return tree
    elif rule == 53:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(40, tracer) # const
      tree.add(t)
      return tree
    elif rule == 58:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(15, tracer) # static
      tree.add(t)
      return tree
    elif rule == 60:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(2, tracer) # typedef
      tree.add(t)
      return tree
    elif rule == 61:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(77, tracer) # signed
      tree.add(t)
      return tree
    elif rule == 72:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(6, tracer) # do
      tree.add(t)
      return tree
    elif rule == 73:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(78, tracer) # return
      tree.add(t)
      return tree
    elif rule == 81:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(68, tracer) # break
      tree.add(t)
      return tree
    elif rule == 83:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(17, tracer) # struct
      tree.add(t)
      return tree
    elif rule == 89:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(55, tracer) # case
      tree.add(t)
      return tree
    elif rule == 90:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(16, tracer) # short
      tree.add(t)
      return tree
    elif rule == 105:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(111, tracer) # complex
      tree.add(t)
      return tree
    elif rule == 143:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(109, tracer) # float
      tree.add(t)
      return tree
    elif rule == 167:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(57, tracer) # void
      tree.add(t)
      return tree
    elif rule == 181:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(90, tracer) # double
      tree.add(t)
      return tree
    elif rule == 199:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(41, tracer) # enum
      tree.add(t)
      return tree
    elif rule == 216:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(86, tracer) # inline
      tree.add(t)
      return tree
    elif rule == 219:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(103, tracer) # goto
      tree.add(t)
      return tree
    elif rule == 227:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(61, tracer) # sizeof
      tree.add(t)
      return tree
    elif rule == 228:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(46, tracer) # bool
      tree.add(t)
      return tree
    elif rule == 235:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(3, tracer) # imaginary
      tree.add(t)
      return tree
    elif rule == 243:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(69, tracer) # union
      tree.add(t)
      return tree
    elif rule == 249:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(10, tracer) # else
      tree.add(t)
      return tree
    elif rule == 252:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(96, tracer) # while
      tree.add(t)
      return tree
    elif rule == 258:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(39, tracer) # default
      tree.add(t)
      return tree
    elif rule == 275:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(34, tracer) # auto
      tree.add(t)
      return tree
    elif rule == 328:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(44, tracer) # char
      tree.add(t)
      return tree
    elif rule == 341:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(11, tracer) # for
      tree.add(t)
      return tree
    elif rule == 365:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(12, tracer) # volatile
      tree.add(t)
      return tree
    elif rule == 370:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(66, tracer) # if
      tree.add(t)
      return tree
    elif rule == 408:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(60, tracer) # unsigned
      tree.add(t)
      return tree
    elif rule == 419:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(113, tracer) # switch
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN21(self, depth=0, tracer=None):
    rule = self.rule(163)
    tree = ParseTree( NonTerminal(163, self.getAtomString(163)), tracer )
    tree.list = 'slist'
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 236:
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
    elif self.sym.getId() in [112, 30, 107]:
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
  def _TRAILING_COMMA_OPT(self, depth=0, tracer=None):
    rule = self.rule(164)
    tree = ParseTree( NonTerminal(164, self.getAtomString(164)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [70]):
      return tree
    if self.sym == None:
      return tree
    if rule == 335:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(100, tracer) # trailing_comma
      tree.add(t)
      return tree
    return tree
  def __GEN22(self, depth=0, tracer=None):
    rule = self.rule(165)
    tree = ParseTree( NonTerminal(165, self.getAtomString(165)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in [67]):
      return tree
    if self.sym == None:
      return tree
    if rule == 319:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(73, tracer) # comma
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
  def __GEN13(self, depth=0, tracer=None):
    rule = self.rule(166)
    tree = ParseTree( NonTerminal(166, self.getAtomString(166)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [67, 73]):
      return tree
    if self.sym == None:
      return tree
    if rule == 104:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DECLARATOR_INITIALIZER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _MISC(self, depth=0, tracer=None):
    rule = self.rule(167)
    tree = ParseTree( NonTerminal(167, self.getAtomString(167)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 376:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(35, tracer) # endif
      tree.add(t)
      return tree
    elif rule == 412:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(23, tracer) # universal_character_name
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _DECLARATION_LIST(self, depth=0, tracer=None):
    rule = self.rule(168)
    tree = ParseTree( NonTerminal(168, self.getAtomString(168)), tracer )
    tree.list = False
    if self.sym == None:
      return tree
    if rule == 269:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN6(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _POINTER_OPT(self, depth=0, tracer=None):
    rule = self.rule(169)
    tree = ParseTree( NonTerminal(169, self.getAtomString(169)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [112, 48, 73, 88, 33, 30, 107]):
      return tree
    if self.sym == None:
      return tree
    if rule == 155:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._POINTER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _DIRECT_ABSTRACT_DECLARATOR(self, depth=0, tracer=None):
    rule = self.rule(170)
    tree = ParseTree( NonTerminal(170, self.getAtomString(170)), tracer )
    tree.list = False
    if self.sym == None:
      return tree
    if rule == 135:
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
  def _DECLARATOR_INITIALIZER(self, depth=0, tracer=None):
    rule = self.rule(171)
    tree = ParseTree( NonTerminal(171, self.getAtomString(171)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 84:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(87, tracer) # assign
      tree.add(t)
      subtree = self._INITIALIZER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _STRUCT_SPECIFIER(self, depth=0, tracer=None):
    rule = self.rule(172)
    tree = ParseTree( NonTerminal(172, self.getAtomString(172)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 231:
      tree.astTransform = AstTransformNodeCreator('Struct', {'definition': 2})
      t = self.expect(17, tracer) # struct
      tree.add(t)
      t = self.expect(26, tracer) # declarator_hint
      tree.add(t)
      subtree = self._STRUCT_OR_UNION_SUB(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _EXTERNAL_DECLARATOR(self, depth=0, tracer=None):
    rule = self.rule(173)
    tree = ParseTree( NonTerminal(173, self.getAtomString(173)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 304:
      tree.astTransform = AstTransformNodeCreator('ExternalDeclarator', {'init_declarator': 1})
      t = self.expect(26, tracer) # declarator_hint
      tree.add(t)
      subtree = self._INIT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _EXTERNAL_DECLARATION(self, depth=0, tracer=None):
    rule = self.rule(174)
    tree = ParseTree( NonTerminal(174, self.getAtomString(174)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 3:
      tree.astTransform = AstTransformNodeCreator('ExternalDeclaration', {'declarations': 2, 'declaration_specifiers': 1})
      t = self.expect(85, tracer) # external_declaration_hint
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
  def _STATEMENT(self, depth=0, tracer=None):
    rule = self.rule(175)
    tree = ParseTree( NonTerminal(175, self.getAtomString(175)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 19:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._EXPRESSION_STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 51:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._SELECTION_STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 79:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._LABELED_STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 93:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._COMPOUND_STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 123:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._ITERATION_STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 414:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._JUMP_STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [58, 30, 74, 114, 99, 64, 37, 93, 80, 4, 76, 107, 22, 61, 50, 42]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._EXPRESSION_STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _UNION_SPECIFIER(self, depth=0, tracer=None):
    rule = self.rule(176)
    tree = ParseTree( NonTerminal(176, self.getAtomString(176)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 221:
      tree.astTransform = AstTransformNodeCreator('Union', {'definition': 1})
      t = self.expect(69, tracer) # union
      tree.add(t)
      t = self.expect(26, tracer) # declarator_hint
      tree.add(t)
      subtree = self._STRUCT_OR_UNION_SUB(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _BLOCK_ITEM_LIST(self, depth=0, tracer=None):
    rule = self.rule(177)
    tree = ParseTree( NonTerminal(177, self.getAtomString(177)), tracer )
    tree.list = False
    if self.sym == None:
      return tree
    if rule == 62:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN38(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [58, 30, 74, 114, 99, 64, 37, 93, 80, 4, 76, 107, 22, 61, 50, 42]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN38(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _COMPOUND_STATEMENT(self, depth=0, tracer=None):
    rule = self.rule(178)
    tree = ParseTree( NonTerminal(178, self.getAtomString(178)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 75:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(0, tracer) # lbrace
      tree.add(t)
      subtree = self.__GEN37(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(70, tracer) # rbrace
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _INITIALIZER(self, depth=0, tracer=None):
    rule = self.rule(179)
    tree = ParseTree( NonTerminal(179, self.getAtomString(179)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 196:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(0, tracer) # lbrace
      tree.add(t)
      subtree = self.__GEN14(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self._TRAILING_COMMA_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(70, tracer) # rbrace
      tree.add(t)
      return tree
    elif rule == 218:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [58, 30, 74, 114, 99, 64, 37, 93, 80, 4, 76, 107, 22, 61, 50, 42]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _PUNCTUATOR(self, depth=0, tracer=None):
    rule = self.rule(180)
    tree = ParseTree( NonTerminal(180, self.getAtomString(180)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 2:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(72, tracer) # rshifteq
      tree.add(t)
      return tree
    elif rule == 15:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(65, tracer) # pound
      tree.add(t)
      return tree
    elif rule == 22:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(51, tracer) # ampersand
      tree.add(t)
      return tree
    elif rule == 24:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(95, tracer) # subeq
      tree.add(t)
      return tree
    elif rule == 34:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(91, tracer) # or
      tree.add(t)
      return tree
    elif rule == 39:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(63, tracer) # bitxoreq
      tree.add(t)
      return tree
    elif rule == 44:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(21, tracer) # rshift
      tree.add(t)
      return tree
    elif rule == 70:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(97, tracer) # and
      tree.add(t)
      return tree
    elif rule == 76:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(38, tracer) # bitxor
      tree.add(t)
      return tree
    elif rule == 78:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(89, tracer) # gteq
      tree.add(t)
      return tree
    elif rule == 86:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(106, tracer) # dot
      tree.add(t)
      return tree
    elif rule == 94:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(62, tracer) # sub
      tree.add(t)
      return tree
    elif rule == 96:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(4, tracer) # decr
      tree.add(t)
      return tree
    elif rule == 101:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(48, tracer) # lsquare
      tree.add(t)
      return tree
    elif rule == 131:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(19, tracer) # eq
      tree.add(t)
      return tree
    elif rule == 134:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(14, tracer) # elipsis
      tree.add(t)
      return tree
    elif rule == 146:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(13, tracer) # lshift
      tree.add(t)
      return tree
    elif rule == 159:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(102, tracer) # bitor
      tree.add(t)
      return tree
    elif rule == 168:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(82, tracer) # poundpound
      tree.add(t)
      return tree
    elif rule == 171:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(25, tracer) # lt
      tree.add(t)
      return tree
    elif rule == 192:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(67, tracer) # semi
      tree.add(t)
      return tree
    elif rule == 194:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(70, tracer) # rbrace
      tree.add(t)
      return tree
    elif rule == 206:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(83, tracer) # lteq
      tree.add(t)
      return tree
    elif rule == 207:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(104, tracer) # addeq
      tree.add(t)
      return tree
    elif rule == 210:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(45, tracer) # rsquare
      tree.add(t)
      return tree
    elif rule == 211:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(98, tracer) # arrow
      tree.add(t)
      return tree
    elif rule == 217:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(0, tracer) # lbrace
      tree.add(t)
      return tree
    elif rule == 224:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(30, tracer) # lparen
      tree.add(t)
      return tree
    elif rule == 233:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(110, tracer) # neq
      tree.add(t)
      return tree
    elif rule == 237:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(71, tracer) # bitandeq
      tree.add(t)
      return tree
    elif rule == 238:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(54, tracer) # exclamation_point
      tree.add(t)
      return tree
    elif rule == 239:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(73, tracer) # comma
      tree.add(t)
      return tree
    elif rule == 245:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(31, tracer) # muleq
      tree.add(t)
      return tree
    elif rule == 251:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(52, tracer) # colon
      tree.add(t)
      return tree
    elif rule == 267:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(87, tracer) # assign
      tree.add(t)
      return tree
    elif rule == 271:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(29, tracer) # modeq
      tree.add(t)
      return tree
    elif rule == 272:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(76, tracer) # incr
      tree.add(t)
      return tree
    elif rule == 288:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(81, tracer) # lshifteq
      tree.add(t)
      return tree
    elif rule == 322:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(33, tracer) # rparen
      tree.add(t)
      return tree
    elif rule == 327:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(7, tracer) # gt
      tree.add(t)
      return tree
    elif rule == 337:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(27, tracer) # mod
      tree.add(t)
      return tree
    elif rule == 339:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(49, tracer) # questionmark
      tree.add(t)
      return tree
    elif rule == 358:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(43, tracer) # add
      tree.add(t)
      return tree
    elif rule == 366:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(79, tracer) # div
      tree.add(t)
      return tree
    elif rule == 371:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(75, tracer) # tilde
      tree.add(t)
      return tree
    elif rule == 400:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(56, tracer) # bitoreq
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _ENUM_SPECIFIER(self, depth=0, tracer=None):
    rule = self.rule(181)
    tree = ParseTree( NonTerminal(181, self.getAtomString(181)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 37:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(41, tracer) # enum
      tree.add(t)
      subtree = self._ENUM_SPECIFIER_SUB(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _PARAMETER_DECLARATION_SUB(self, depth=0, tracer=None):
    rule = self.rule(182)
    tree = ParseTree( NonTerminal(182, self.getAtomString(182)), tracer )
    tree.list = False
    if self.sym == None:
      return tree
    if rule == 298:
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
    elif self.sym.getId() in [112, 30, 107]:
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
  def __GEN34(self, depth=0, tracer=None):
    rule = self.rule(183)
    tree = ParseTree( NonTerminal(183, self.getAtomString(183)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [73, 33, 88]):
      return tree
    if self.sym == None:
      return tree
    if rule == 126:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PARAMETER_DECLARATION_SUB(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [112, 30, 107]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PARAMETER_DECLARATION_SUB(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    return tree
  def _SPECIFIER_QUALIFIER(self, depth=0, tracer=None):
    rule = self.rule(184)
    tree = ParseTree( NonTerminal(184, self.getAtomString(184)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 50:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._TYPE_QUALIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 225:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._TYPE_SPECIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _TYPEDEF_NAME(self, depth=0, tracer=None):
    rule = self.rule(185)
    tree = ParseTree( NonTerminal(185, self.getAtomString(185)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 241:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(105, tracer) # typedef_identifier
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _LABELED_STATEMENT(self, depth=0, tracer=None):
    rule = self.rule(186)
    tree = ParseTree( NonTerminal(186, self.getAtomString(186)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 52:
      tree.astTransform = AstTransformNodeCreator('Case', {'expr': 1, 'statement': 3})
      t = self.expect(55, tracer) # case
      tree.add(t)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(52, tracer) # colon
      tree.add(t)
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 283:
      tree.astTransform = AstTransformNodeCreator('DefaultCase', {'statement': 2})
      t = self.expect(39, tracer) # default
      tree.add(t)
      t = self.expect(52, tracer) # colon
      tree.add(t)
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 330:
      tree.astTransform = AstTransformNodeCreator('Label', {'name': 0, 'statement': 1})
      t = self.expect(20, tracer) # label_hint
      tree.add(t)
      t = self.expect(107, tracer) # identifier
      tree.add(t)
      t = self.expect(52, tracer) # colon
      tree.add(t)
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _INITIALIZER_LIST_ITEM(self, depth=0, tracer=None):
    rule = self.rule(187)
    tree = ParseTree( NonTerminal(187, self.getAtomString(187)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 367:
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
    elif rule == 396:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(37, tracer) # integer_constant
      tree.add(t)
      return tree
    elif self.sym.getId() in [58, 30, 74, 114, 99, 64, 37, 93, 80, 4, 76, 107, 22, 61, 50, 42]:
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
  def _ENUMERATION_CONSTANT(self, depth=0, tracer=None):
    rule = self.rule(188)
    tree = ParseTree( NonTerminal(188, self.getAtomString(188)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 380:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(107, tracer) # identifier
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN23(self, depth=0, tracer=None):
    rule = self.rule(189)
    tree = ParseTree( NonTerminal(189, self.getAtomString(189)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [67, 73]):
      return tree
    if self.sym == None:
      return tree
    if rule == 353:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STRUCT_DECLARATOR_BODY(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN25(self, depth=0, tracer=None):
    rule = self.rule(190)
    tree = ParseTree( NonTerminal(190, self.getAtomString(190)), tracer )
    tree.list = 'slist'
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 265:
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
  def __GEN15(self, depth=0, tracer=None):
    rule = self.rule(191)
    tree = ParseTree( NonTerminal(191, self.getAtomString(191)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in [100]):
      return tree
    if self.sym == None:
      return tree
    if rule == 141:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(73, tracer) # comma
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
  def _DECLARATION(self, depth=0, tracer=None):
    rule = self.rule(192)
    tree = ParseTree( NonTerminal(192, self.getAtomString(192)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 111:
      tree.astTransform = AstTransformNodeCreator('Declaration', {'init_declarators': 1, 'declaration_specifiers': 0})
      subtree = self.__GEN1(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN7(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(67, tracer) # semi
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _ITERATION_STATEMENT(self, depth=0, tracer=None):
    rule = self.rule(193)
    tree = ParseTree( NonTerminal(193, self.getAtomString(193)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 147:
      tree.astTransform = AstTransformNodeCreator('For', {'init': 2, 'cond': 3, 'incr': 4, 'statement': 6})
      t = self.expect(11, tracer) # for
      tree.add(t)
      t = self.expect(30, tracer) # lparen
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
      t = self.expect(33, tracer) # rparen
      tree.add(t)
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 280:
      tree.astTransform = AstTransformNodeCreator('DoWhile', {'expr': 4, 'statement': 1})
      t = self.expect(6, tracer) # do
      tree.add(t)
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(96, tracer) # while
      tree.add(t)
      t = self.expect(30, tracer) # lparen
      tree.add(t)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(33, tracer) # rparen
      tree.add(t)
      t = self.expect(67, tracer) # semi
      tree.add(t)
      return tree
    elif rule == 286:
      tree.astTransform = AstTransformNodeCreator('While', {'expr': 2, 'statement': 4})
      t = self.expect(96, tracer) # while
      tree.add(t)
      t = self.expect(30, tracer) # lparen
      tree.add(t)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(33, tracer) # rparen
      tree.add(t)
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _PARAMETER_DECLARATION_SUB_SUB(self, depth=0, tracer=None):
    rule = self.rule(194)
    tree = ParseTree( NonTerminal(194, self.getAtomString(194)), tracer )
    tree.list = False
    if self.sym == None:
      return tree
    if rule == 25:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__DIRECT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 389:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN35(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [112, 30, 107]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__DIRECT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _EXPRESSION_STATEMENT(self, depth=0, tracer=None):
    rule = self.rule(195)
    tree = ParseTree( NonTerminal(195, self.getAtomString(195)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 195:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._EXPRESSION_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(67, tracer) # semi
      tree.add(t)
      return tree
    elif self.sym.getId() in [58, 30, 74, 114, 99, 64, 37, 93, 80, 4, 76, 107, 22, 61, 50, 42]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._EXPRESSION_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(67, tracer) ) # semi
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _PARAMETER_DECLARATION(self, depth=0, tracer=None):
    rule = self.rule(196)
    tree = ParseTree( NonTerminal(196, self.getAtomString(196)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 363:
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
  def __GEN26(self, depth=0, tracer=None):
    rule = self.rule(197)
    tree = ParseTree( NonTerminal(197, self.getAtomString(197)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in [100]):
      return tree
    if self.sym == None:
      return tree
    if rule == 425:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(73, tracer) # comma
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
  def __GEN29(self, depth=0, tracer=None):
    rule = self.rule(198)
    tree = ParseTree( NonTerminal(198, self.getAtomString(198)), tracer )
    tree.list = 'slist'
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 368:
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
  def __GEN30(self, depth=0, tracer=None):
    rule = self.rule(199)
    tree = ParseTree( NonTerminal(199, self.getAtomString(199)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in [88, 33]):
      return tree
    if self.sym == None:
      return tree
    if rule == 403:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(73, tracer) # comma
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
  def _ENUM_SPECIFIER_SUB(self, depth=0, tracer=None):
    rule = self.rule(200)
    tree = ParseTree( NonTerminal(200, self.getAtomString(200)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 357:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._ENUM_SPECIFIER_BODY(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 405:
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
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _EXTERNAL_DECLARATION_SUB(self, depth=0, tracer=None):
    rule = self.rule(201)
    tree = ParseTree( NonTerminal(201, self.getAtomString(201)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 57:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._EXTERNAL_FUNCTION(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 384:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN3(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(67, tracer) # semi
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN35(self, depth=0, tracer=None):
    rule = self.rule(202)
    tree = ParseTree( NonTerminal(202, self.getAtomString(202)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [33, 88, 73]):
      return tree
    if self.sym == None:
      return tree
    if rule == 127:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DIRECT_ABSTRACT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _DESIGNATION(self, depth=0, tracer=None):
    rule = self.rule(203)
    tree = ParseTree( NonTerminal(203, self.getAtomString(203)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 290:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN17(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(87, tracer) # assign
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _STRUCT_OR_UNION_BODY(self, depth=0, tracer=None):
    rule = self.rule(204)
    tree = ParseTree( NonTerminal(204, self.getAtomString(204)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 12:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(0, tracer) # lbrace
      tree.add(t)
      subtree = self.__GEN19(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(70, tracer) # rbrace
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN18(self, depth=0, tracer=None):
    rule = self.rule(205)
    tree = ParseTree( NonTerminal(205, self.getAtomString(205)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [52, 86, 12, 2, 3, 88, 5, 41, 60, 64, 9, 112, 67, 15, 73, 77, 18, 34, 107, 26, 28, 30, 53, 105, 111, 108, 109, 90, 57, 17, 40, 48, 69, 46, 47, 44, 16, 33]):
      return tree
    if self.sym == None:
      return tree
    if rule == 387:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STRUCT_OR_UNION_BODY(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _STRUCT_OR_UNION_SUB(self, depth=0, tracer=None):
    rule = self.rule(206)
    tree = ParseTree( NonTerminal(206, self.getAtomString(206)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 42:
      tree.astTransform = AstTransformNodeCreator('StructOrUnion', {'body': 1, 'name': 0})
      t = self.expect(107, tracer) # identifier
      tree.add(t)
      subtree = self.__GEN18(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 116:
      tree.astTransform = AstTransformNodeCreator('StructOrUnion', {'body': 0})
      subtree = self._STRUCT_OR_UNION_BODY(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _EXTERNAL_FUNCTION(self, depth=0, tracer=None):
    rule = self.rule(207)
    tree = ParseTree( NonTerminal(207, self.getAtomString(207)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 187:
      tree.astTransform = AstTransformNodeCreator('FunctionDefinition', {'body': 3, 'declaration_list': 2, 'signature': 1})
      t = self.expect(53, tracer) # function_definition_hint
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
  def _INIT_DECLARATOR_LIST(self, depth=0, tracer=None):
    rule = self.rule(208)
    tree = ParseTree( NonTerminal(208, self.getAtomString(208)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 395:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN11(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [112, 30, 107]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN11(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _TOKEN(self, depth=0, tracer=None):
    rule = self.rule(209)
    tree = ParseTree( NonTerminal(209, self.getAtomString(209)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 85:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(101, tracer) # pp_number
      tree.add(t)
      return tree
    elif rule == 164:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(107, tracer) # identifier
      tree.add(t)
      return tree
    elif rule == 247:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PUNCTUATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 279:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(80, tracer) # string_literal
      tree.add(t)
      return tree
    elif rule == 299:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._CONSTANT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 300:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._KEYWORD(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN16(self, depth=0, tracer=None):
    rule = self.rule(210)
    tree = ParseTree( NonTerminal(210, self.getAtomString(210)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [22, 30, 74, 0, 99, 64, 80, 37, 93, 42, 4, 76, 107, 58, 61, 50, 114]):
      return tree
    if self.sym == None:
      return tree
    if rule == 173:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DESIGNATION(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _JUMP_STATEMENT(self, depth=0, tracer=None):
    rule = self.rule(211)
    tree = ParseTree( NonTerminal(211, self.getAtomString(211)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 200:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(59, tracer) # continue
      tree.add(t)
      return tree
    elif rule == 229:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(68, tracer) # break
      tree.add(t)
      t = self.expect(67, tracer) # semi
      tree.add(t)
      return tree
    elif rule == 253:
      tree.astTransform = AstTransformNodeCreator('Return', {'expr': 1})
      t = self.expect(78, tracer) # return
      tree.add(t)
      subtree = self._EXPRESSION_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(67, tracer) # semi
      tree.add(t)
      return tree
    elif rule == 287:
      tree.astTransform = AstTransformNodeCreator('Goto', {'name': 1})
      t = self.expect(103, tracer) # goto
      tree.add(t)
      t = self.expect(107, tracer) # identifier
      tree.add(t)
      t = self.expect(67, tracer) # semi
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN31(self, depth=0, tracer=None):
    rule = self.rule(213)
    tree = ParseTree( NonTerminal(213, self.getAtomString(213)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [33]):
      return tree
    if self.sym == None:
      return tree
    if rule == 122:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._VA_ARGS(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _DIRECT_DECLARATOR_SIZE(self, depth=0, tracer=None):
    rule = self.rule(214)
    tree = ParseTree( NonTerminal(214, self.getAtomString(214)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 158:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(64, tracer) # asterisk
      tree.add(t)
      return tree
    elif rule == 160:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [58, 30, 74, 114, 99, 64, 37, 93, 80, 4, 76, 107, 22, 61, 50, 42]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _IDENTIFIER(self, depth=0, tracer=None):
    rule = self.rule(215)
    tree = ParseTree( NonTerminal(215, self.getAtomString(215)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 424:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(107, tracer) # identifier
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _STATIC_OPT(self, depth=0, tracer=None):
    rule = self.rule(216)
    tree = ParseTree( NonTerminal(216, self.getAtomString(216)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [58, 30, 74, 114, 99, 64, 37, 93, 80, 4, 76, 107, 22, 61, 50, 42]):
      return tree
    if self.sym == None:
      return tree
    if rule == 177:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(15, tracer) # static
      tree.add(t)
      return tree
    return tree
  def _ENUM_SPECIFIER_BODY(self, depth=0, tracer=None):
    rule = self.rule(217)
    tree = ParseTree( NonTerminal(217, self.getAtomString(217)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 145:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(0, tracer) # lbrace
      tree.add(t)
      subtree = self.__GEN25(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self._TRAILING_COMMA_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(70, tracer) # rbrace
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _VA_ARGS(self, depth=0, tracer=None):
    rule = self.rule(218)
    tree = ParseTree( NonTerminal(218, self.getAtomString(218)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 41:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(88, tracer) # comma_va_args
      tree.add(t)
      t = self.expect(14, tracer) # elipsis
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN3(self, depth=0, tracer=None):
    rule = self.rule(219)
    tree = ParseTree( NonTerminal(219, self.getAtomString(219)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in [67]):
      return tree
    if self.sym == None:
      return tree
    if rule == 169:
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
  def __GEN4(self, depth=0, tracer=None):
    rule = self.rule(220)
    tree = ParseTree( NonTerminal(220, self.getAtomString(220)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in [67]):
      return tree
    if self.sym == None:
      return tree
    if rule == 263:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(73, tracer) # comma
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
    rule = self.rule(221)
    tree = ParseTree( NonTerminal(221, self.getAtomString(221)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 10:
      tree.astTransform = AstTransformNodeCreator('StructOrUnionDeclaration', {'specifier_qualifiers': 0, 'declarators': 1})
      subtree = self.__GEN20(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN21(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(67, tracer) # semi
      tree.add(t)
      return tree
    elif self.sym.getId() in [112, 30, 107]:
      tree.astTransform = AstTransformNodeCreator('StructOrUnionDeclaration', {'specifier_qualifiers': 0, 'declarators': 1})
      subtree = self.__GEN20(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN21(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(67, tracer) ) # semi
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _CONSTANT(self, depth=0, tracer=None):
    rule = self.rule(222)
    tree = ParseTree( NonTerminal(222, self.getAtomString(222)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 13:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(22, tracer) # character_constant
      tree.add(t)
      return tree
    elif rule == 30:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(93, tracer) # enumeration_constant
      tree.add(t)
      return tree
    elif rule == 64:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(37, tracer) # integer_constant
      tree.add(t)
      return tree
    elif rule == 82:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(74, tracer) # hexadecimal_floating_constant
      tree.add(t)
      return tree
    elif rule == 191:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(42, tracer) # floating_constant
      tree.add(t)
      return tree
    elif rule == 364:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(99, tracer) # decimal_floating_constant
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _DESIGNATOR(self, depth=0, tracer=None):
    rule = self.rule(223)
    tree = ParseTree( NonTerminal(223, self.getAtomString(223)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 313:
      tree.astTransform = AstTransformNodeCreator('MemberAccess', {'name': 1})
      t = self.expect(106, tracer) # dot
      tree.add(t)
      t = self.expect(107, tracer) # identifier
      tree.add(t)
      return tree
    elif rule == 420:
      tree.astTransform = AstTransformNodeCreator('ArrayAccess', {'index': 1})
      t = self.expect(48, tracer) # lsquare
      tree.add(t)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(45, tracer) # rsquare
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _SELECTION_STATEMENT(self, depth=0, tracer=None):
    rule = self.rule(224)
    tree = ParseTree( NonTerminal(224, self.getAtomString(224)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 36:
      tree.astTransform = AstTransformNodeCreator('If', {'elseif': 6, 'statement': 4, 'condition': 2, 'else': 7})
      t = self.expect(66, tracer) # if
      tree.add(t)
      t = self.expect(30, tracer) # lparen
      tree.add(t)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(33, tracer) # rparen
      tree.add(t)
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(35, tracer) # endif
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
    elif rule == 262:
      tree.astTransform = AstTransformNodeCreator('Switch', {'expr': 2, 'statment': 4})
      t = self.expect(113, tracer) # switch
      tree.add(t)
      t = self.expect(30, tracer) # lparen
      tree.add(t)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(33, tracer) # rparen
      tree.add(t)
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN17(self, depth=0, tracer=None):
    rule = self.rule(225)
    tree = ParseTree( NonTerminal(225, self.getAtomString(225)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [87]):
      return tree
    if self.sym == None:
      return tree
    if rule == 174:
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
  def _TYPE_SPECIFIER(self, depth=0, tracer=None):
    rule = self.rule(226)
    tree = ParseTree( NonTerminal(226, self.getAtomString(226)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 7:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._UNION_SPECIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 45:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(46, tracer) # bool
      tree.add(t)
      return tree
    elif rule == 54:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(57, tracer) # void
      tree.add(t)
      return tree
    elif rule == 55:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._ENUM_SPECIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 68:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(18, tracer) # int
      tree.add(t)
      return tree
    elif rule == 77:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(5, tracer) # long
      tree.add(t)
      return tree
    elif rule == 91:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(111, tracer) # complex
      tree.add(t)
      return tree
    elif rule == 110:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(90, tracer) # double
      tree.add(t)
      return tree
    elif rule == 150:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(77, tracer) # signed
      tree.add(t)
      return tree
    elif rule == 153:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(3, tracer) # imaginary
      tree.add(t)
      return tree
    elif rule == 209:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(16, tracer) # short
      tree.add(t)
      return tree
    elif rule == 293:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(44, tracer) # char
      tree.add(t)
      return tree
    elif rule == 305:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(60, tracer) # unsigned
      tree.add(t)
      return tree
    elif rule == 308:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STRUCT_SPECIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 349:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(109, tracer) # float
      tree.add(t)
      return tree
    elif rule == 352:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._TYPEDEF_NAME(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _STRUCT_DECLARATOR_BODY(self, depth=0, tracer=None):
    rule = self.rule(227)
    tree = ParseTree( NonTerminal(227, self.getAtomString(227)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 74:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(52, tracer) # colon
      tree.add(t)
      subtree = self._DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _POINTER_SUB(self, depth=0, tracer=None):
    rule = self.rule(228)
    tree = ParseTree( NonTerminal(228, self.getAtomString(228)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 402:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(64, tracer) # asterisk
      tree.add(t)
      subtree = self._TYPE_QUALIFIER_LIST_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN36(self, depth=0, tracer=None):
    rule = self.rule(229)
    tree = ParseTree( NonTerminal(229, self.getAtomString(229)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [112, 48, 73, 88, 30, 33, 107]):
      return tree
    if self.sym == None:
      return tree
    if rule == 183:
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
  def _TYPE_QUALIFIER(self, depth=0, tracer=None):
    rule = self.rule(230)
    tree = ParseTree( NonTerminal(230, self.getAtomString(230)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 46:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(40, tracer) # const
      tree.add(t)
      return tree
    elif rule == 278:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(12, tracer) # volatile
      tree.add(t)
      return tree
    elif rule == 307:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(47, tracer) # restrict
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN33(self, depth=0, tracer=None):
    rule = self.rule(231)
    tree = ParseTree( NonTerminal(231, self.getAtomString(231)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 374:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(73, tracer) # comma
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
  def __GEN37(self, depth=0, tracer=None):
    rule = self.rule(232)
    tree = ParseTree( NonTerminal(232, self.getAtomString(232)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [70]):
      return tree
    if self.sym == None:
      return tree
    if rule == 418:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._BLOCK_ITEM_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [58, 30, 74, 114, 99, 64, 37, 93, 80, 4, 76, 107, 22, 61, 50, 42]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._BLOCK_ITEM_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    return tree
  def _PP(self, depth=0, tracer=None):
    rule = self.rule(233)
    tree = ParseTree( NonTerminal(233, self.getAtomString(233)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 71:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(84, tracer) # defined
      tree.add(t)
      return tree
    elif rule == 198:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(92, tracer) # defined_separator
      tree.add(t)
      return tree
    elif rule == 375:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(101, tracer) # pp_number
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN20(self, depth=0, tracer=None):
    rule = self.rule(234)
    tree = ParseTree( NonTerminal(234, self.getAtomString(234)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [52, 112, 64, 30, 107]):
      return tree
    if self.sym == None:
      return tree
    if rule == 189:
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
  def __GEN27(self, depth=0, tracer=None):
    rule = self.rule(235)
    tree = ParseTree( NonTerminal(235, self.getAtomString(235)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [112, 30, 88, 33, 64, 15, 73, 107, 48]):
      return tree
    if self.sym == None:
      return tree
    if rule == 157:
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
  def _FUNCTION_SPECIFIER(self, depth=0, tracer=None):
    rule = self.rule(236)
    tree = ParseTree( NonTerminal(236, self.getAtomString(236)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 409:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(86, tracer) # inline
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _DIRECT_DECLARATOR_MODIFIER_LIST_OPT(self, depth=0, tracer=None):
    rule = self.rule(237)
    tree = ParseTree( NonTerminal(237, self.getAtomString(237)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [58, 30, 74, 114, 99, 64, 37, 93, 80, 4, 76, 107, 22, 61, 50, 42]):
      return tree
    if self.sym == None:
      return tree
    if rule == 276:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN28(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN7(self, depth=0, tracer=None):
    rule = self.rule(238)
    tree = ParseTree( NonTerminal(238, self.getAtomString(238)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [67]):
      return tree
    if self.sym == None:
      return tree
    if rule == 119:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._INIT_DECLARATOR_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [112, 30, 107]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._INIT_DECLARATOR_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    return tree
  def _EXPRESSION_OPT(self, depth=0, tracer=None):
    rule = self.rule(239)
    tree = ParseTree( NonTerminal(239, self.getAtomString(239)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [67, 33]):
      return tree
    if self.sym == None:
      return tree
    if rule == 63:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [58, 30, 74, 114, 99, 64, 37, 93, 80, 4, 76, 107, 22, 61, 50, 42]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    return tree
  def __GEN32(self, depth=0, tracer=None):
    rule = self.rule(240)
    tree = ParseTree( NonTerminal(240, self.getAtomString(240)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 132:
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
  def _SIZEOF_BODY(self, depth=0, tracer=None):
    rule = self.rule(241)
    tree = ParseTree( NonTerminal(241, self.getAtomString(241)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 21:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(30, tracer) # lparen
      tree.add(t)
      subtree = self._TYPE_NAME(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(33, tracer) # rparen
      tree.add(t)
      return tree
    elif rule == 281:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(107, tracer) # identifier
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _EXTERNAL_DECLARATION_SUB_SUB(self, depth=0, tracer=None):
    rule = self.rule(242)
    tree = ParseTree( NonTerminal(242, self.getAtomString(242)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 27:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._EXTERNAL_PROTOTYPE(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 317:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._EXTERNAL_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _EXTERNAL_PROTOTYPE(self, depth=0, tracer=None):
    rule = self.rule(243)
    tree = ParseTree( NonTerminal(243, self.getAtomString(243)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 121:
      tree.astTransform = AstTransformNodeCreator('FunctionPrototype', {'declaration_list': 2, 'declarator': 1})
      t = self.expect(108, tracer) # function_prototype_hint
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
  def _DECLARATOR(self, depth=0, tracer=None):
    rule = self.rule(244)
    tree = ParseTree( NonTerminal(244, self.getAtomString(244)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 301:
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
    elif self.sym.getId() in [112, 30, 107]:
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
  def _STRUCT_DECLARATOR(self, depth=0, tracer=None):
    rule = self.rule(245)
    tree = ParseTree( NonTerminal(245, self.getAtomString(245)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 80:
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
    elif rule == 139:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STRUCT_DECLARATOR_BODY(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [112, 30, 107]:
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
  infixBp0 = {
    0: 14000,
    4: 15000,
    7: 9000,
    13: 10000,
    19: 8000,
    21: 10000,
    25: 9000,
    27: 12000,
    29: 1000,
    30: 15000,
    31: 1000,
    32: 1000,
    38: 6000,
    43: 11000,
    48: 15000,
    49: 2000,
    56: 1000,
    62: 11000,
    63: 1000,
    64: 12000,
    71: 1000,
    72: 1000,
    73: 16000,
    76: 15000,
    79: 12000,
    81: 1000,
    83: 9000,
    87: 1000,
    89: 9000,
    91: 3000,
    95: 1000,
    97: 4000,
    98: 15000,
    102: 7000,
    104: 1000,
    106: 15000,
    110: 8000,
    114: 5000,
  }
  prefixBp0 = {
    4: 13000,
    8: 13000,
    36: 13000,
    62: 13000,
    64: 13000,
    76: 13000,
    114: 13000,
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
    tree = ParseTree( NonTerminal(212, '_expr') )
    if not self.sym:
      return tree
    if self.sym.getId() in [58]:
      tree.astTransform = AstTransformNodeCreator('TypeInitializion', {'type': 1, 'initializer': 4})
      tree.nudMorphemeCount = 3
      tree.add( self.expect(58, tracer) )
      tree.add( self._TYPE_NAME() )
      tree.add( self.expect(33, tracer) )
    elif self.sym.getId() in [76]:
      tree.astTransform = AstTransformNodeCreator('PreIncr', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(76, tracer) )
      tree.add( self.__EXPR( self.prefixBp0[76] ) )
      tree.isPrefix = True
    elif self.sym.getId() in [107]:
      tree.astTransform = AstTransformNodeCreator('ArrayIndex', {'params': 2, 'name': 0})
      tree.nudMorphemeCount = 1
      return self.expect( 107, tracer )
    elif self.sym.getId() in [99, 93, 22, 74, 37, 42]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      tree.add( self._CONSTANT() )
    elif self.sym.getId() in [107]:
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      tree.nudMorphemeCount = 1
      return self.expect( 107, tracer )
    elif self.sym.getId() in [61]:
      tree.astTransform = AstTransformNodeCreator('SizeOf', {'var': 1})
      tree.nudMorphemeCount = 1
      return self.expect( 61, tracer )
    elif self.sym.getId() in [30]:
      tree.astTransform = AstTransformSubstitution(2)
      tree.nudMorphemeCount = 3
      tree.add( self.expect(30, tracer) )
      tree.add( self.__EXPR() )
      tree.add( self.expect(33, tracer) )
    elif self.sym.getId() in [4]:
      tree.astTransform = AstTransformNodeCreator('PreDecr', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(4, tracer) )
      tree.add( self.__EXPR( self.prefixBp0[4] ) )
      tree.isPrefix = True
    elif self.sym.getId() in [64]:
      tree.astTransform = AstTransformNodeCreator('Dereference', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(64, tracer) )
      tree.add( self.__EXPR( self.prefixBp0[64] ) )
      tree.isPrefix = True
    elif self.sym.getId() in [80]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      return self.expect( 80, tracer )
    elif self.sym.getId() in [107]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      return self.expect( 107, tracer )
    elif self.sym.getId() in [114]:
      tree.astTransform = AstTransformNodeCreator('AddressOf', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(114, tracer) )
      tree.add( self.__EXPR( self.prefixBp0[114] ) )
      tree.isPrefix = True
    return tree
  def led0(self, left, tracer):
    tree = ParseTree( NonTerminal(212, '_expr') )
    if  self.sym.getId() == 76: # 'incr'
      tree.astTransform = AstTransformNodeCreator('PostIncr', {'var': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(76, tracer) )
    elif  self.sym.getId() == 32: # 'diveq'
      tree.astTransform = AstTransformNodeCreator('DivideAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(32, tracer) )
      tree.add( self.__EXPR( self.infixBp0[32] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 31: # 'muleq'
      tree.astTransform = AstTransformNodeCreator('MultiplyAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(31, tracer) )
      tree.add( self.__EXPR( self.infixBp0[31] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 94: # 'sizeof_separator'
      tree.astTransform = AstTransformNodeCreator('SizeOf', {'var': 1})
      if left:
        tree.add(left)
      tree.add( self.expect(94, tracer) )
      tree.add( self._SIZEOF_BODY() )
    elif  self.sym.getId() == 48: # 'lsquare'
      tree.astTransform = AstTransformNodeCreator('ArrayIndex', {'params': 2, 'name': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(48, tracer) )
      tree.add( self.__GEN42() )
      tree.add( self.expect(45, tracer) )
    elif  self.sym.getId() == 102: # 'bitor'
      tree.astTransform = AstTransformNodeCreator('BitOR', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(102, tracer) )
      tree.add( self.__EXPR( self.infixBp0[102] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 73: # 'comma'
      tree.astTransform = AstTransformNodeCreator('Comma', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(73, tracer) )
      tree.add( self.__EXPR( self.infixBp0[73] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 89: # 'gteq'
      tree.astTransform = AstTransformNodeCreator('GreaterThanEq', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(89, tracer) )
      tree.add( self.__EXPR( self.infixBp0[89] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 63: # 'bitxoreq'
      tree.astTransform = AstTransformNodeCreator('XORAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(63, tracer) )
      tree.add( self.__EXPR( self.infixBp0[63] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 95: # 'subeq'
      tree.astTransform = AstTransformNodeCreator('SubtractAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(95, tracer) )
      tree.add( self.__EXPR( self.infixBp0[95] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 43: # 'add'
      tree.astTransform = AstTransformNodeCreator('Add', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(43, tracer) )
      tree.add( self.__EXPR( self.infixBp0[43] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 30: # 'lparen'
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(30, tracer) )
      tree.add( self.__GEN42() )
      tree.add( self.expect(33, tracer) )
    elif  self.sym.getId() == 21: # 'rshift'
      tree.astTransform = AstTransformNodeCreator('RightShift', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(21, tracer) )
      tree.add( self.__EXPR( self.infixBp0[21] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 62: # 'sub'
      tree.astTransform = AstTransformNodeCreator('Sub', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(62, tracer) )
      tree.add( self.__EXPR( self.infixBp0[62] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 4: # 'decr'
      tree.astTransform = AstTransformNodeCreator('PostDecr', {'var': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(4, tracer) )
    elif  self.sym.getId() == 114: # 'bitand'
      tree.astTransform = AstTransformNodeCreator('BitAND', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(114, tracer) )
      tree.add( self.__EXPR( self.infixBp0[114] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 98: # 'arrow'
      tree.astTransform = AstTransformNodeCreator('DerefMemberSelect', {'member': 2, 'object': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(98, tracer) )
      tree.add( self.__EXPR() )
    elif  self.sym.getId() == 25: # 'lt'
      tree.astTransform = AstTransformNodeCreator('LessThan', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(25, tracer) )
      tree.add( self.__EXPR( self.infixBp0[25] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 27: # 'mod'
      tree.astTransform = AstTransformNodeCreator('Mod', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(27, tracer) )
      tree.add( self.__EXPR( self.infixBp0[27] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 38: # 'bitxor'
      tree.astTransform = AstTransformNodeCreator('BitXOR', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(38, tracer) )
      tree.add( self.__EXPR( self.infixBp0[38] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 83: # 'lteq'
      tree.astTransform = AstTransformNodeCreator('LessThanEq', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(83, tracer) )
      tree.add( self.__EXPR( self.infixBp0[83] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 64: # 'asterisk'
      tree.astTransform = AstTransformNodeCreator('Mul', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(64, tracer) )
      tree.add( self.__EXPR( self.infixBp0[64] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 7: # 'gt'
      tree.astTransform = AstTransformNodeCreator('GreaterThan', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(7, tracer) )
      tree.add( self.__EXPR( self.infixBp0[7] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 106: # 'dot'
      tree.astTransform = AstTransformNodeCreator('MemberSelect', {'member': 2, 'object': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(106, tracer) )
      tree.add( self.__EXPR() )
    elif  self.sym.getId() == 79: # 'div'
      tree.astTransform = AstTransformNodeCreator('Div', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(79, tracer) )
      tree.add( self.__EXPR( self.infixBp0[79] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 81: # 'lshifteq'
      tree.astTransform = AstTransformNodeCreator('LeftShiftAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(81, tracer) )
      tree.add( self.__EXPR( self.infixBp0[81] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 56: # 'bitoreq'
      tree.astTransform = AstTransformNodeCreator('ORAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(56, tracer) )
      tree.add( self.__EXPR( self.infixBp0[56] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 72: # 'rshifteq'
      tree.astTransform = AstTransformNodeCreator('RightShiftAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(72, tracer) )
      tree.add( self.__EXPR( self.infixBp0[72] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 13: # 'lshift'
      tree.astTransform = AstTransformNodeCreator('LeftShift', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(13, tracer) )
      tree.add( self.__EXPR( self.infixBp0[13] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 0: # 'lbrace'
      tree.astTransform = AstTransformNodeCreator('TypeInitializion', {'type': 1, 'initializer': 4})
      if left:
        tree.add(left)
      tree.add( self.expect(0, tracer) )
      tree.add( self.__GEN14() )
      tree.add( self._TRAILING_COMMA_OPT() )
      tree.add( self.expect(70, tracer) )
    elif  self.sym.getId() == 29: # 'modeq'
      tree.astTransform = AstTransformNodeCreator('ModAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(29, tracer) )
      tree.add( self.__EXPR( self.infixBp0[29] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 49: # 'questionmark'
      tree.astTransform = AstTransformNodeCreator('TernaryOperator', {'true': 2, 'false': 4, 'cond': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(49, tracer) )
      tree.add( self.__EXPR() )
      tree.add( self.expect(52, tracer) )
      tree.add( self.__EXPR() )
    elif  self.sym.getId() == 19: # 'eq'
      tree.astTransform = AstTransformNodeCreator('Equals', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(19, tracer) )
      tree.add( self.__EXPR( self.infixBp0[19] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 104: # 'addeq'
      tree.astTransform = AstTransformNodeCreator('AddAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(104, tracer) )
      tree.add( self.__EXPR( self.infixBp0[104] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 87: # 'assign'
      tree.astTransform = AstTransformNodeCreator('Assign', {'var': 0, 'value': 2})
      if left:
        tree.add(left)
      tree.add( self.expect(87, tracer) )
      tree.add( self.__EXPR( self.infixBp0[87] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 71: # 'bitandeq'
      tree.astTransform = AstTransformNodeCreator('ANDAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(71, tracer) )
      tree.add( self.__EXPR( self.infixBp0[71] ) )
      tree.isInfix = True
    return tree
  infixBp1 = {
    0: 14000,
    4: 15000,
    7: 9000,
    13: 10000,
    19: 8000,
    21: 10000,
    25: 9000,
    27: 12000,
    29: 1000,
    30: 15000,
    31: 1000,
    32: 1000,
    38: 6000,
    43: 11000,
    48: 15000,
    49: 2000,
    56: 1000,
    62: 11000,
    63: 1000,
    64: 12000,
    71: 1000,
    72: 1000,
    76: 15000,
    79: 12000,
    81: 1000,
    83: 9000,
    87: 1000,
    89: 9000,
    91: 3000,
    95: 1000,
    97: 4000,
    98: 15000,
    102: 7000,
    104: 1000,
    106: 15000,
    110: 8000,
    114: 5000,
  }
  prefixBp1 = {
    4: 13000,
    8: 13000,
    36: 13000,
    62: 13000,
    64: 13000,
    76: 13000,
    114: 13000,
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
    tree = ParseTree( NonTerminal(159, '_expr_sans_comma') )
    if not self.sym:
      return tree
    elif self.sym.getId() in [58]:
      tree.astTransform = AstTransformNodeCreator('TypeInitializion', {'type': 1, 'initializer': 4})
      tree.nudMorphemeCount = 3
      tree.add( self.expect(58, tracer) )
      tree.add( self._TYPE_NAME() )
      tree.add( self.expect(33, tracer) )
    elif self.sym.getId() in [30]:
      tree.astTransform = AstTransformSubstitution(2)
      tree.nudMorphemeCount = 3
      tree.add( self.expect(30, tracer) )
      tree.add( self.__EXPR_SANS_COMMA() )
      tree.add( self.expect(33, tracer) )
    elif self.sym.getId() in [64]:
      tree.astTransform = AstTransformNodeCreator('Dereference', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(64, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.prefixBp1[64] ) )
      tree.isPrefix = True
    elif self.sym.getId() in [99, 93, 22, 74, 37, 42]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      tree.add( self._CONSTANT() )
    elif self.sym.getId() in [61]:
      tree.astTransform = AstTransformNodeCreator('SizeOf', {'var': 1})
      tree.nudMorphemeCount = 1
      return self.expect( 61, tracer )
    elif self.sym.getId() in [4]:
      tree.astTransform = AstTransformNodeCreator('PreDecr', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(4, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.prefixBp1[4] ) )
      tree.isPrefix = True
    elif self.sym.getId() in [107]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      return self.expect( 107, tracer )
    elif self.sym.getId() in [76]:
      tree.astTransform = AstTransformNodeCreator('PreIncr', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(76, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.prefixBp1[76] ) )
      tree.isPrefix = True
    elif self.sym.getId() in [107]:
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      tree.nudMorphemeCount = 1
      return self.expect( 107, tracer )
    elif self.sym.getId() in [114]:
      tree.astTransform = AstTransformNodeCreator('AddressOf', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(114, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.prefixBp1[114] ) )
      tree.isPrefix = True
    elif self.sym.getId() in [80]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      return self.expect( 80, tracer )
    elif self.sym.getId() in [107]:
      tree.astTransform = AstTransformNodeCreator('ArrayIndex', {'params': 2, 'name': 0})
      tree.nudMorphemeCount = 1
      return self.expect( 107, tracer )
    return tree
  def led1(self, left, tracer):
    tree = ParseTree( NonTerminal(159, '_expr_sans_comma') )
    if  self.sym.getId() == 64: # 'asterisk'
      tree.astTransform = AstTransformNodeCreator('Mul', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(64, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[64] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 62: # 'sub'
      tree.astTransform = AstTransformNodeCreator('Sub', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(62, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[62] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 95: # 'subeq'
      tree.astTransform = AstTransformNodeCreator('SubtractAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(95, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[95] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 71: # 'bitandeq'
      tree.astTransform = AstTransformNodeCreator('ANDAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(71, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[71] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 31: # 'muleq'
      tree.astTransform = AstTransformNodeCreator('MultiplyAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(31, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[31] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 98: # 'arrow'
      tree.astTransform = AstTransformNodeCreator('DerefMemberSelect', {'member': 2, 'object': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(98, tracer) )
      tree.add( self.__EXPR_SANS_COMMA() )
    elif  self.sym.getId() == 21: # 'rshift'
      tree.astTransform = AstTransformNodeCreator('RightShift', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(21, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[21] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 72: # 'rshifteq'
      tree.astTransform = AstTransformNodeCreator('RightShiftAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(72, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[72] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 79: # 'div'
      tree.astTransform = AstTransformNodeCreator('Div', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(79, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[79] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 32: # 'diveq'
      tree.astTransform = AstTransformNodeCreator('DivideAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(32, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[32] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 25: # 'lt'
      tree.astTransform = AstTransformNodeCreator('LessThan', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(25, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[25] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 30: # 'lparen'
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(30, tracer) )
      tree.add( self.__GEN42() )
      tree.add( self.expect(33, tracer) )
    elif  self.sym.getId() == 4: # 'decr'
      tree.astTransform = AstTransformNodeCreator('PostDecr', {'var': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(4, tracer) )
    elif  self.sym.getId() == 114: # 'bitand'
      tree.astTransform = AstTransformNodeCreator('BitAND', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(114, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[114] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 38: # 'bitxor'
      tree.astTransform = AstTransformNodeCreator('BitXOR', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(38, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[38] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 27: # 'mod'
      tree.astTransform = AstTransformNodeCreator('Mod', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(27, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[27] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 56: # 'bitoreq'
      tree.astTransform = AstTransformNodeCreator('ORAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(56, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[56] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 7: # 'gt'
      tree.astTransform = AstTransformNodeCreator('GreaterThan', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(7, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[7] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 48: # 'lsquare'
      tree.astTransform = AstTransformNodeCreator('ArrayIndex', {'params': 2, 'name': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(48, tracer) )
      tree.add( self.__GEN42() )
      tree.add( self.expect(45, tracer) )
    elif  self.sym.getId() == 104: # 'addeq'
      tree.astTransform = AstTransformNodeCreator('AddAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(104, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[104] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 76: # 'incr'
      tree.astTransform = AstTransformNodeCreator('PostIncr', {'var': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(76, tracer) )
    elif  self.sym.getId() == 102: # 'bitor'
      tree.astTransform = AstTransformNodeCreator('BitOR', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(102, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[102] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 63: # 'bitxoreq'
      tree.astTransform = AstTransformNodeCreator('XORAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(63, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[63] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 19: # 'eq'
      tree.astTransform = AstTransformNodeCreator('Equals', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(19, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[19] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 83: # 'lteq'
      tree.astTransform = AstTransformNodeCreator('LessThanEq', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(83, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[83] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 81: # 'lshifteq'
      tree.astTransform = AstTransformNodeCreator('LeftShiftAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(81, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[81] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 0: # 'lbrace'
      tree.astTransform = AstTransformNodeCreator('TypeInitializion', {'type': 1, 'initializer': 4})
      if left:
        tree.add(left)
      tree.add( self.expect(0, tracer) )
      tree.add( self.__GEN14() )
      tree.add( self._TRAILING_COMMA_OPT() )
      tree.add( self.expect(70, tracer) )
    elif  self.sym.getId() == 49: # 'questionmark'
      tree.astTransform = AstTransformNodeCreator('TernaryOperator', {'true': 2, 'false': 4, 'cond': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(49, tracer) )
      tree.add( self.__EXPR_SANS_COMMA() )
      tree.add( self.expect(52, tracer) )
      tree.add( self.__EXPR_SANS_COMMA() )
    elif  self.sym.getId() == 87: # 'assign'
      tree.astTransform = AstTransformNodeCreator('Assign', {'var': 0, 'value': 2})
      if left:
        tree.add(left)
      tree.add( self.expect(87, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[87] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 94: # 'sizeof_separator'
      tree.astTransform = AstTransformNodeCreator('SizeOf', {'var': 1})
      if left:
        tree.add(left)
      tree.add( self.expect(94, tracer) )
      tree.add( self._SIZEOF_BODY() )
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
    elif  self.sym.getId() == 106: # 'dot'
      tree.astTransform = AstTransformNodeCreator('MemberSelect', {'member': 2, 'object': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(106, tracer) )
      tree.add( self.__EXPR_SANS_COMMA() )
    elif  self.sym.getId() == 13: # 'lshift'
      tree.astTransform = AstTransformNodeCreator('LeftShift', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(13, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[13] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 29: # 'modeq'
      tree.astTransform = AstTransformNodeCreator('ModAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(29, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[29] ) )
      tree.isInfix = True
    return tree
  infixBp2 = {
    30: 1000,
    48: 1000,
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
    tree = ParseTree( NonTerminal(131, '_direct_declarator') )
    if not self.sym:
      return tree
    if self.sym.getId() in [107]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      return self.expect( 107, tracer )
    elif self.sym.getId() in [30]:
      tree.astTransform = AstTransformSubstitution(1)
      tree.nudMorphemeCount = 3
      tree.add( self.expect(30, tracer) )
      tree.add( self._DECLARATOR() )
      tree.add( self.expect(33, tracer) )
    return tree
  def led2(self, left, tracer):
    tree = ParseTree( NonTerminal(131, '_direct_declarator') )
    if  self.sym.getId() == 30: # 'lparen'
      tree.astTransform = AstTransformNodeCreator('FunctionSignature', {'params': 2, 'declarator': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(30, tracer) )
      tree.add( self._DIRECT_DECLARATOR_PARAMETER_LIST() )
      tree.add( self.expect(33, tracer) )
    elif  self.sym.getId() == 48: # 'lsquare'
      tree.astTransform = AstTransformNodeCreator('Array', {'name': 0, 'size': 2})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(48, tracer) )
      tree.add( self._DIRECT_DECLARATOR_EXPR() )
      tree.add( self.expect(45, tracer) )
    return tree
