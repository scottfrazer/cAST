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
  TERMINAL_RESTRICT = 0
  TERMINAL_TILDE = 1
  TERMINAL__DIRECT_DECLARATOR = 2
  TERMINAL_ARROW = 3
  TERMINAL_SUB = 4
  TERMINAL_DEFINED = 5
  TERMINAL_FLOATING_CONSTANT = 6
  TERMINAL_RSHIFTEQ = 7
  TERMINAL_DEFAULT = 8
  TERMINAL_EXCLAMATION_POINT = 9
  TERMINAL_RPAREN = 10
  TERMINAL_EQ = 11
  TERMINAL_DEFINED_SEPARATOR = 12
  TERMINAL_ENDIF = 13
  TERMINAL_SUBEQ = 14
  TERMINAL_UNSIGNED = 15
  TERMINAL_SWITCH = 16
  TERMINAL_TRAILING_COMMA = 17
  TERMINAL_PP_NUMBER = 18
  TERMINAL_LONG = 19
  TERMINAL_AND = 20
  TERMINAL_ADDEQ = 21
  TERMINAL_ENUMERATION_CONSTANT = 22
  TERMINAL_CASE = 23
  TERMINAL_FUNCTION_DEFINITION_HINT = 24
  TERMINAL_IDENTIFIER = 25
  TERMINAL_UNION = 26
  TERMINAL_MODEQ = 27
  TERMINAL_INT = 28
  TERMINAL_LT = 29
  TERMINAL_TYPEDEF = 30
  TERMINAL_IMAGINARY = 31
  TERMINAL_DECIMAL_FLOATING_CONSTANT = 32
  TERMINAL_DO = 33
  TERMINAL_GTEQ = 34
  TERMINAL_COLON = 35
  TERMINAL_EXTERN = 36
  TERMINAL_GT = 37
  TERMINAL_FOR = 38
  TERMINAL_SIGNED = 39
  TERMINAL_LSHIFT = 40
  TERMINAL_STATIC = 41
  TERMINAL_WHILE = 42
  TERMINAL_SHORT = 43
  TERMINAL__EXPR_SANS_COMMA = 44
  TERMINAL_ELIPSIS = 45
  TERMINAL_RSHIFT = 46
  TERMINAL_UNIVERSAL_CHARACTER_NAME = 47
  TERMINAL_OR = 48
  TERMINAL_POUND = 49
  TERMINAL_EXTERNAL_DECLARATION_HINT = 50
  TERMINAL_INLINE = 51
  TERMINAL_BOOL = 52
  TERMINAL_COMPLEX = 53
  TERMINAL_MOD = 54
  TERMINAL_REGISTER = 55
  TERMINAL_POUNDPOUND = 56
  TERMINAL_DECR = 57
  TERMINAL_LPAREN = 58
  TERMINAL_SIZEOF = 59
  TERMINAL_DIVEQ = 60
  TERMINAL_LBRACE = 61
  TERMINAL_FUNCTION_PROTOTYPE_HINT = 62
  TERMINAL_LSHIFTEQ = 63
  TERMINAL_NOT = 64
  TERMINAL_SIZEOF_SEPARATOR = 65
  TERMINAL_BITNOT = 66
  TERMINAL_STRUCT = 67
  TERMINAL_COMMA_VA_ARGS = 68
  TERMINAL_BITAND = 69
  TERMINAL_CONST = 70
  TERMINAL_CHAR = 71
  TERMINAL_VOID = 72
  TERMINAL_RSQUARE = 73
  TERMINAL_BITOR = 74
  TERMINAL_ADD = 75
  TERMINAL_BITANDEQ = 76
  TERMINAL_QUESTIONMARK = 77
  TERMINAL_ASSIGN = 78
  TERMINAL_GOTO = 79
  TERMINAL_ELSE = 80
  TERMINAL_TYPEDEF_IDENTIFIER = 81
  TERMINAL_RBRACE = 82
  TERMINAL_ELSE_IF = 83
  TERMINAL_BITOREQ = 84
  TERMINAL_DIV = 85
  TERMINAL_CHARACTER_CONSTANT = 86
  TERMINAL_INTEGER_CONSTANT = 87
  TERMINAL_INCR = 88
  TERMINAL_CONTINUE = 89
  TERMINAL_LSQUARE = 90
  TERMINAL__EXPR = 91
  TERMINAL_COMMA = 92
  TERMINAL_BITXOREQ = 93
  TERMINAL_LPAREN_CAST = 94
  TERMINAL_ASTERISK = 95
  TERMINAL_DECLARATOR_HINT = 96
  TERMINAL_AMPERSAND = 97
  TERMINAL_VOLATILE = 98
  TERMINAL_DOT = 99
  TERMINAL_MULEQ = 100
  TERMINAL_BREAK = 101
  TERMINAL_STRING_LITERAL = 102
  TERMINAL_FLOAT = 103
  TERMINAL_IF = 104
  TERMINAL_AUTO = 105
  TERMINAL_HEXADECIMAL_FLOATING_CONSTANT = 106
  TERMINAL_LABEL_HINT = 107
  TERMINAL_BITXOR = 108
  TERMINAL_LTEQ = 109
  TERMINAL_RETURN = 110
  TERMINAL_SEMI = 111
  TERMINAL_NEQ = 112
  TERMINAL_DOUBLE = 113
  TERMINAL_ENUM = 114
  terminal_str = {
    0: 'restrict',
    1: 'tilde',
    2: '_direct_declarator',
    3: 'arrow',
    4: 'sub',
    5: 'defined',
    6: 'floating_constant',
    7: 'rshifteq',
    8: 'default',
    9: 'exclamation_point',
    10: 'rparen',
    11: 'eq',
    12: 'defined_separator',
    13: 'endif',
    14: 'subeq',
    15: 'unsigned',
    16: 'switch',
    17: 'trailing_comma',
    18: 'pp_number',
    19: 'long',
    20: 'and',
    21: 'addeq',
    22: 'enumeration_constant',
    23: 'case',
    24: 'function_definition_hint',
    25: 'identifier',
    26: 'union',
    27: 'modeq',
    28: 'int',
    29: 'lt',
    30: 'typedef',
    31: 'imaginary',
    32: 'decimal_floating_constant',
    33: 'do',
    34: 'gteq',
    35: 'colon',
    36: 'extern',
    37: 'gt',
    38: 'for',
    39: 'signed',
    40: 'lshift',
    41: 'static',
    42: 'while',
    43: 'short',
    44: '_expr_sans_comma',
    45: 'elipsis',
    46: 'rshift',
    47: 'universal_character_name',
    48: 'or',
    49: 'pound',
    50: 'external_declaration_hint',
    51: 'inline',
    52: 'bool',
    53: 'complex',
    54: 'mod',
    55: 'register',
    56: 'poundpound',
    57: 'decr',
    58: 'lparen',
    59: 'sizeof',
    60: 'diveq',
    61: 'lbrace',
    62: 'function_prototype_hint',
    63: 'lshifteq',
    64: 'not',
    65: 'sizeof_separator',
    66: 'bitnot',
    67: 'struct',
    68: 'comma_va_args',
    69: 'bitand',
    70: 'const',
    71: 'char',
    72: 'void',
    73: 'rsquare',
    74: 'bitor',
    75: 'add',
    76: 'bitandeq',
    77: 'questionmark',
    78: 'assign',
    79: 'goto',
    80: 'else',
    81: 'typedef_identifier',
    82: 'rbrace',
    83: 'else_if',
    84: 'bitoreq',
    85: 'div',
    86: 'character_constant',
    87: 'integer_constant',
    88: 'incr',
    89: 'continue',
    90: 'lsquare',
    91: '_expr',
    92: 'comma',
    93: 'bitxoreq',
    94: 'lparen_cast',
    95: 'asterisk',
    96: 'declarator_hint',
    97: 'ampersand',
    98: 'volatile',
    99: 'dot',
    100: 'muleq',
    101: 'break',
    102: 'string_literal',
    103: 'float',
    104: 'if',
    105: 'auto',
    106: 'hexadecimal_floating_constant',
    107: 'label_hint',
    108: 'bitxor',
    109: 'lteq',
    110: 'return',
    111: 'semi',
    112: 'neq',
    113: 'double',
    114: 'enum',
  }
  nonterminal_str = {
    115: 'direct_declarator_parameter_list',
    116: '_gen18',
    117: 'parameter_declaration_sub_sub',
    118: 'type_specifier',
    119: 'external_declarator',
    120: 'expression_opt',
    121: 'pointer_opt',
    122: '_direct_declarator',
    123: 'external_prototype',
    124: 'enumeration_constant',
    125: 'function_specifier',
    126: 'direct_declarator_modifier_list_opt',
    127: 'direct_declarator_size',
    128: 'declarator',
    129: 'declaration_list',
    130: '_gen5',
    131: 'enumerator_assignment',
    132: 'direct_abstract_declarator_sub0',
    133: '_expr_sans_comma',
    134: '_gen9',
    135: '_gen39',
    136: 'direct_declarator_modifier',
    137: '_gen43',
    138: '_gen29',
    139: 'compound_statement',
    140: 'direct_abstract_declarator_sub1',
    141: '_gen30',
    142: 'init_declarator',
    143: '_gen6',
    144: 'parameter_declaration_sub',
    145: '_gen41',
    146: '_gen35',
    147: 'statement',
    148: 'sizeof_body',
    149: 'abstract_declarator',
    150: 'trailing_comma_opt',
    151: 'else_if_statement_list',
    152: '_gen40',
    153: '_gen10',
    154: 'declaration',
    155: '_gen7',
    156: '_gen12',
    157: 'direct_abstract_declarator_expr',
    158: 'direct_abstract_declarator_sub2',
    159: 'parameter_declaration',
    160: '_gen44',
    161: '_gen31',
    162: 'type_qualifier',
    163: '_gen36',
    164: 'designator',
    165: 'init_declarator_list',
    166: '_gen8',
    167: 'block_item_list',
    168: 'else_statement',
    169: 'else_if_statement',
    170: '_gen42',
    171: 'parameter_type_list',
    172: '_gen33',
    173: '_gen11',
    174: '_gen38',
    175: 'pointer',
    176: 'storage_class_specifier',
    177: 'external_declaration_sub_sub',
    178: '_gen20',
    179: 'specifier_qualifier',
    180: '_gen21',
    181: 'type_qualifier_list_opt',
    182: 'jump_statement',
    183: '_gen28',
    184: 'pointer_sub',
    185: '_gen37',
    186: '_gen13',
    187: 'enumerator',
    188: '_gen26',
    189: 'pp',
    190: '_gen27',
    191: 'type_name',
    192: '_gen1',
    193: 'keyword',
    194: 'direct_abstract_declarator',
    195: '_gen34',
    196: 'va_args',
    197: '_gen22',
    198: 'declarator_initializer',
    199: 'external_declaration',
    200: '_gen0',
    201: 'constant',
    202: '_gen32',
    203: 'struct_specifier',
    204: 'for_init',
    205: 'struct_declarator_body',
    206: 'for_cond',
    207: 'for_incr',
    208: 'union_specifier',
    209: 'initializer',
    210: 'punctuator',
    211: 'enum_specifier',
    212: 'declaration_specifier',
    213: 'translation_unit',
    214: '_expr',
    215: '_gen2',
    216: 'typedef_name',
    217: 'labeled_statement',
    218: 'initializer_list_item',
    219: 'struct_declarator',
    220: '_gen24',
    221: 'designation',
    222: '_gen16',
    223: 'struct_or_union_sub',
    224: 'external_declaration_sub',
    225: 'direct_declarator_expr',
    226: 'expression_statement',
    227: 'static_opt',
    228: 'external_function',
    229: 'block_item',
    230: 'selection_statement',
    231: '_gen15',
    232: 'struct_or_union_body',
    233: '_gen23',
    234: '_gen19',
    235: 'iteration_statement',
    236: 'enum_specifier_sub',
    237: '_gen3',
    238: '_gen17',
    239: '_gen4',
    240: '_gen14',
    241: 'identifier',
    242: 'enum_specifier_body',
    243: '_gen25',
    244: 'token',
    245: 'struct_declaration',
    246: 'misc',
  }
  str_terminal = {
    'restrict': 0,
    'tilde': 1,
    '_direct_declarator': 2,
    'arrow': 3,
    'sub': 4,
    'defined': 5,
    'floating_constant': 6,
    'rshifteq': 7,
    'default': 8,
    'exclamation_point': 9,
    'rparen': 10,
    'eq': 11,
    'defined_separator': 12,
    'endif': 13,
    'subeq': 14,
    'unsigned': 15,
    'switch': 16,
    'trailing_comma': 17,
    'pp_number': 18,
    'long': 19,
    'and': 20,
    'addeq': 21,
    'enumeration_constant': 22,
    'case': 23,
    'function_definition_hint': 24,
    'identifier': 25,
    'union': 26,
    'modeq': 27,
    'int': 28,
    'lt': 29,
    'typedef': 30,
    'imaginary': 31,
    'decimal_floating_constant': 32,
    'do': 33,
    'gteq': 34,
    'colon': 35,
    'extern': 36,
    'gt': 37,
    'for': 38,
    'signed': 39,
    'lshift': 40,
    'static': 41,
    'while': 42,
    'short': 43,
    '_expr_sans_comma': 44,
    'elipsis': 45,
    'rshift': 46,
    'universal_character_name': 47,
    'or': 48,
    'pound': 49,
    'external_declaration_hint': 50,
    'inline': 51,
    'bool': 52,
    'complex': 53,
    'mod': 54,
    'register': 55,
    'poundpound': 56,
    'decr': 57,
    'lparen': 58,
    'sizeof': 59,
    'diveq': 60,
    'lbrace': 61,
    'function_prototype_hint': 62,
    'lshifteq': 63,
    'not': 64,
    'sizeof_separator': 65,
    'bitnot': 66,
    'struct': 67,
    'comma_va_args': 68,
    'bitand': 69,
    'const': 70,
    'char': 71,
    'void': 72,
    'rsquare': 73,
    'bitor': 74,
    'add': 75,
    'bitandeq': 76,
    'questionmark': 77,
    'assign': 78,
    'goto': 79,
    'else': 80,
    'typedef_identifier': 81,
    'rbrace': 82,
    'else_if': 83,
    'bitoreq': 84,
    'div': 85,
    'character_constant': 86,
    'integer_constant': 87,
    'incr': 88,
    'continue': 89,
    'lsquare': 90,
    '_expr': 91,
    'comma': 92,
    'bitxoreq': 93,
    'lparen_cast': 94,
    'asterisk': 95,
    'declarator_hint': 96,
    'ampersand': 97,
    'volatile': 98,
    'dot': 99,
    'muleq': 100,
    'break': 101,
    'string_literal': 102,
    'float': 103,
    'if': 104,
    'auto': 105,
    'hexadecimal_floating_constant': 106,
    'label_hint': 107,
    'bitxor': 108,
    'lteq': 109,
    'return': 110,
    'semi': 111,
    'neq': 112,
    'double': 113,
    'enum': 114,
  }
  str_nonterminal = {
    'direct_declarator_parameter_list': 115,
    '_gen18': 116,
    'parameter_declaration_sub_sub': 117,
    'type_specifier': 118,
    'external_declarator': 119,
    'expression_opt': 120,
    'pointer_opt': 121,
    '_direct_declarator': 122,
    'external_prototype': 123,
    'enumeration_constant': 124,
    'function_specifier': 125,
    'direct_declarator_modifier_list_opt': 126,
    'direct_declarator_size': 127,
    'declarator': 128,
    'declaration_list': 129,
    '_gen5': 130,
    'enumerator_assignment': 131,
    'direct_abstract_declarator_sub0': 132,
    '_expr_sans_comma': 133,
    '_gen9': 134,
    '_gen39': 135,
    'direct_declarator_modifier': 136,
    '_gen43': 137,
    '_gen29': 138,
    'compound_statement': 139,
    'direct_abstract_declarator_sub1': 140,
    '_gen30': 141,
    'init_declarator': 142,
    '_gen6': 143,
    'parameter_declaration_sub': 144,
    '_gen41': 145,
    '_gen35': 146,
    'statement': 147,
    'sizeof_body': 148,
    'abstract_declarator': 149,
    'trailing_comma_opt': 150,
    'else_if_statement_list': 151,
    '_gen40': 152,
    '_gen10': 153,
    'declaration': 154,
    '_gen7': 155,
    '_gen12': 156,
    'direct_abstract_declarator_expr': 157,
    'direct_abstract_declarator_sub2': 158,
    'parameter_declaration': 159,
    '_gen44': 160,
    '_gen31': 161,
    'type_qualifier': 162,
    '_gen36': 163,
    'designator': 164,
    'init_declarator_list': 165,
    '_gen8': 166,
    'block_item_list': 167,
    'else_statement': 168,
    'else_if_statement': 169,
    '_gen42': 170,
    'parameter_type_list': 171,
    '_gen33': 172,
    '_gen11': 173,
    '_gen38': 174,
    'pointer': 175,
    'storage_class_specifier': 176,
    'external_declaration_sub_sub': 177,
    '_gen20': 178,
    'specifier_qualifier': 179,
    '_gen21': 180,
    'type_qualifier_list_opt': 181,
    'jump_statement': 182,
    '_gen28': 183,
    'pointer_sub': 184,
    '_gen37': 185,
    '_gen13': 186,
    'enumerator': 187,
    '_gen26': 188,
    'pp': 189,
    '_gen27': 190,
    'type_name': 191,
    '_gen1': 192,
    'keyword': 193,
    'direct_abstract_declarator': 194,
    '_gen34': 195,
    'va_args': 196,
    '_gen22': 197,
    'declarator_initializer': 198,
    'external_declaration': 199,
    '_gen0': 200,
    'constant': 201,
    '_gen32': 202,
    'struct_specifier': 203,
    'for_init': 204,
    'struct_declarator_body': 205,
    'for_cond': 206,
    'for_incr': 207,
    'union_specifier': 208,
    'initializer': 209,
    'punctuator': 210,
    'enum_specifier': 211,
    'declaration_specifier': 212,
    'translation_unit': 213,
    '_expr': 214,
    '_gen2': 215,
    'typedef_name': 216,
    'labeled_statement': 217,
    'initializer_list_item': 218,
    'struct_declarator': 219,
    '_gen24': 220,
    'designation': 221,
    '_gen16': 222,
    'struct_or_union_sub': 223,
    'external_declaration_sub': 224,
    'direct_declarator_expr': 225,
    'expression_statement': 226,
    'static_opt': 227,
    'external_function': 228,
    'block_item': 229,
    'selection_statement': 230,
    '_gen15': 231,
    'struct_or_union_body': 232,
    '_gen23': 233,
    '_gen19': 234,
    'iteration_statement': 235,
    'enum_specifier_sub': 236,
    '_gen3': 237,
    '_gen17': 238,
    '_gen4': 239,
    '_gen14': 240,
    'identifier': 241,
    'enum_specifier_body': 242,
    '_gen25': 243,
    'token': 244,
    'struct_declaration': 245,
    'misc': 246,
  }
  terminal_count = 115
  nonterminal_count = 132
  parse_table = [
    [363, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 363, -1, -1, -1, 363, -1, -1, -1, -1, -1, 411, 363, -1, 363, -1, 363, 363, -1, -1, -1, -1, 363, -1, -1, 363, -1, 363, -1, 363, -1, -1, -1, -1, -1, -1, -1, 363, 363, 363, -1, 363, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 363, -1, -1, 363, 363, 363, -1, -1, -1, -1, -1, -1, -1, -1, 363, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 363, -1, -1, -1, -1, 363, -1, 363, -1, -1, -1, -1, -1, -1, -1, 363, 363],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 196, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 191, -1, -1, -1, -1, -1, -1, -1, -1, 191, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 12, -1, -1, -1, -1, -1, -1, -1, 214, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 12, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 12, -1, -1, -1, -1, -1, -1, -1, -1, -1, 214, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 214, -1, 214, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 179, -1, -1, -1, 172, -1, -1, -1, -1, -1, -1, 69, -1, 38, -1, -1, 253, -1, -1, -1, -1, -1, -1, -1, 264, -1, -1, -1, 21, -1, -1, -1, -1, -1, -1, -1, -1, 296, 380, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 230, -1, -1, -1, 188, 400, -1, -1, -1, -1, -1, -1, -1, -1, 44, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 329, -1, -1, -1, -1, -1, -1, -1, -1, -1, 116, 131],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 357, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, 54, -1, -1, -1, 421, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 54, -1, -1, 54, -1, -1, -1, -1, -1, -1, 54, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 54, 54, 54, -1, -1, -1, -1, -1, -1, -1, -1, -1, 54, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 54, 54, 54, -1, -1, 54, -1, -1, 54, 54, -1, -1, -1, -1, -1, -1, 54, -1, -1, -1, 54, -1, -1, -1, -1, 421, -1, -1, -1],
    [-1, -1, 52, -1, -1, -1, -1, -1, -1, -1, 52, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 52, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 52, -1, -1, -1, -1, -1, -1, -1, -1, -1, 52, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 52, -1, 52, -1, -1, 52, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 397, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 159, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 353, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [289, -1, -1, -1, -1, -1, 29, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 29, -1, -1, 29, -1, -1, -1, -1, -1, -1, 29, -1, -1, -1, -1, -1, -1, -1, -1, 289, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 29, 29, 29, -1, -1, -1, -1, -1, -1, -1, -1, -1, 29, 289, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 29, 29, 29, -1, -1, 29, -1, -1, 29, 29, -1, -1, 289, -1, -1, -1, 29, -1, -1, -1, 29, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, 422, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 422, -1, -1, 422, -1, -1, -1, -1, -1, -1, 422, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 422, 422, 422, -1, -1, -1, -1, -1, -1, -1, -1, -1, 422, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 422, 422, 422, -1, -1, 422, -1, -1, 422, 371, -1, -1, -1, -1, -1, -1, 422, -1, -1, -1, 422, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 280, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 280, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 280, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 280, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [40, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 40, -1, -1, -1, 40, -1, -1, -1, -1, -1, -1, 40, -1, 40, -1, 40, 40, -1, -1, -1, -1, 40, -1, -1, 40, -1, 40, -1, 40, -1, -1, -1, -1, -1, -1, -1, 40, 40, 40, -1, 40, -1, -1, -1, -1, -1, 40, -1, -1, -1, -1, -1, 40, -1, -1, 40, 40, 40, -1, -1, -1, -1, -1, -1, -1, -1, 40, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 40, -1, -1, -1, -1, -1, 40, -1, -1, -1, -1, 40, -1, 40, -1, -1, -1, -1, -1, 40, -1, 40, 40],
    [215, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 215, -1, -1, -1, 215, -1, -1, -1, -1, -1, -1, 215, -1, 215, -1, 215, 215, -1, -1, -1, -1, 215, -1, -1, 215, -1, 215, -1, 215, -1, -1, -1, -1, -1, -1, -1, 215, 215, 215, -1, 215, -1, -1, -1, -1, -1, 215, -1, -1, -1, -1, -1, 215, -1, -1, 215, 215, 215, -1, -1, -1, -1, -1, -1, -1, -1, 215, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 215, -1, -1, -1, -1, -1, 215, -1, -1, -1, -1, 215, -1, 215, -1, -1, -1, -1, -1, 215, -1, 215, 215],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 186, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 227, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 186, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 192, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 303, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 27, -1, -1, -1, -1, -1, -1, -1, -1, -1, 303, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 303, -1, 303, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [221, -1, -1, -1, -1, -1, 221, -1, 221, -1, -1, -1, -1, -1, -1, 221, 221, -1, -1, 221, -1, -1, 221, 221, -1, 221, 221, -1, 221, -1, 221, 221, 221, 221, -1, -1, 221, -1, 221, 221, -1, 221, 221, 221, -1, -1, -1, -1, -1, -1, -1, 221, 221, 221, -1, 221, -1, 221, 221, 221, -1, 221, -1, -1, -1, -1, -1, 221, -1, 221, 221, 221, 221, -1, -1, -1, -1, -1, -1, 221, -1, 221, 226, -1, -1, -1, 221, 221, 221, 221, -1, 221, -1, -1, 221, 221, -1, -1, 221, -1, -1, 221, 221, 221, 221, 221, 221, 221, -1, -1, 221, 221, -1, 221, 221],
    [347, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 377, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 347, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 347, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, 73, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 73, -1, -1, 73, -1, -1, -1, -1, -1, -1, 73, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 73, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 73, 73, 73, -1, -1, -1, -1, -1, -1, -1, -1, -1, 73, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 73, 73, 73, -1, -1, -1, -1, -1, 73, 73, -1, -1, -1, -1, -1, -1, 73, -1, -1, -1, 73, -1, -1, -1, -1, -1, -1, -1, -1],
    [33, -1, -1, -1, -1, -1, 77, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 77, -1, -1, 77, -1, -1, -1, -1, -1, -1, 77, -1, -1, -1, -1, -1, -1, -1, -1, 33, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 77, 77, 77, -1, -1, -1, -1, -1, -1, -1, -1, -1, 77, 33, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 77, 77, 77, -1, -1, 77, -1, -1, 77, 77, -1, -1, 33, -1, -1, -1, 77, -1, -1, -1, 77, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 109, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 30, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 9, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [66, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 66, -1, -1, -1, 66, -1, -1, -1, -1, -1, -1, 66, -1, 66, -1, 66, 66, -1, -1, -1, -1, 66, -1, -1, 66, -1, 66, -1, 66, -1, -1, -1, -1, -1, -1, -1, 66, 66, 66, -1, 66, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 66, -1, -1, 66, 66, 66, -1, -1, -1, -1, -1, -1, -1, -1, 66, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 66, -1, -1, -1, -1, 66, -1, 66, -1, -1, -1, -1, -1, -1, -1, 66, 66],
    [-1, -1, 177, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 177, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 177, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 177, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 234, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 234, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 234, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 385, -1, -1, 234, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 385, -1, -1, -1],
    [-1, -1, 93, -1, -1, -1, -1, -1, -1, -1, 93, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 93, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 93, -1, -1, -1, -1, -1, -1, -1, -1, -1, 93, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 93, -1, 93, -1, -1, 93, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [115, -1, -1, -1, -1, -1, 115, -1, 115, -1, -1, -1, -1, 115, -1, 115, 115, -1, -1, 115, -1, -1, 115, 115, -1, 115, 115, -1, 115, -1, 115, 115, 115, 115, -1, -1, 115, -1, 115, 115, -1, 115, 115, 115, -1, -1, -1, -1, -1, -1, -1, 115, 115, 115, -1, 115, -1, 115, 115, 115, -1, 115, -1, -1, -1, -1, -1, 115, -1, 115, 115, 115, 115, -1, -1, -1, -1, -1, -1, 115, 271, 115, 115, -1, -1, -1, 115, 115, 115, 115, -1, 115, -1, -1, 115, 115, -1, -1, 115, -1, -1, 115, 115, 115, 115, 115, 115, 115, -1, -1, 115, 115, -1, 115, 115],
    [-1, -1, 349, -1, -1, -1, -1, -1, -1, -1, 239, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 349, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 349, -1, -1, -1, -1, -1, -1, -1, -1, -1, 239, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 349, -1, 239, -1, -1, 349, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, 142, -1, 245, -1, -1, -1, -1, -1, -1, -1, 117, -1, -1, -1, -1, -1, 142, 245, -1, 142, -1, -1, -1, -1, -1, -1, 142, 247, -1, -1, -1, -1, 247, -1, -1, -1, 247, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 142, 142, 142, -1, 269, -1, -1, -1, -1, -1, -1, -1, 142, -1, -1, -1, -1, -1, -1, -1, -1, -1, 398, -1, -1, -1, -1, -1, -1, 142, 142, 142, 398, -1, 142, -1, -1, 142, 142, -1, -1, -1, -1, -1, 398, 142, -1, 117, -1, 142, 245, -1, -1, 398, 142, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 162, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 182, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 74, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 74, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 74, -1, -1, -1, -1, 74, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 224, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 99, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [208, -1, -1, -1, -1, -1, 208, -1, 208, -1, -1, -1, -1, 208, -1, 208, 208, -1, -1, 208, -1, -1, 208, 208, -1, 208, 208, -1, 208, -1, 208, 208, 208, 208, -1, -1, 208, -1, 208, 208, -1, 208, 208, 208, -1, -1, -1, -1, -1, -1, -1, 208, 208, 208, -1, 208, -1, 208, 208, 208, -1, 208, -1, -1, -1, -1, -1, 208, -1, 208, 208, 208, 208, -1, -1, -1, -1, -1, -1, 208, 208, 208, 208, 208, -1, -1, 208, 208, 208, 208, -1, 208, -1, -1, 208, 208, -1, -1, 208, -1, -1, 208, 208, 208, 208, 208, 208, 208, -1, -1, 208, 208, -1, 208, 208],
    [222, -1, -1, -1, -1, -1, 222, -1, 222, -1, -1, -1, -1, 222, -1, 222, 222, -1, -1, 222, -1, -1, 222, 222, -1, 222, 222, -1, 222, -1, 222, 222, 222, 222, -1, -1, 222, -1, 222, 222, -1, 222, 222, 222, -1, -1, -1, -1, -1, -1, -1, 222, 222, 222, -1, 222, -1, 222, 222, 222, -1, 222, -1, -1, -1, -1, -1, 222, -1, 222, 222, 222, 222, -1, -1, -1, -1, -1, -1, 222, 222, 222, 222, 256, -1, -1, 222, 222, 222, 222, -1, 222, -1, -1, 222, 222, -1, -1, 222, -1, -1, 222, 222, 222, 222, 222, 222, 222, -1, -1, 222, 222, -1, 222, 222],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 300, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 43, -1, -1, -1, -1, -1, -1, -1, -1, -1, 300, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 43, -1, 300, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [67, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 67, -1, -1, -1, 67, -1, -1, -1, -1, -1, -1, 67, -1, 67, -1, 67, 67, -1, -1, -1, -1, 67, -1, -1, 67, -1, 67, -1, 67, -1, -1, -1, -1, -1, -1, -1, 67, 67, 67, -1, 67, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 67, -1, -1, 67, 67, 67, -1, -1, -1, -1, -1, -1, -1, -1, 67, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 67, -1, -1, -1, -1, 67, -1, 67, -1, -1, -1, -1, -1, -1, -1, 67, 67],
    [327, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 327, -1, -1, -1, 327, -1, -1, -1, -1, -1, -1, 327, -1, 327, -1, 327, 327, -1, -1, -1, -1, 327, -1, -1, 327, -1, 327, -1, 327, -1, -1, -1, -1, -1, -1, -1, 327, 327, 327, -1, 327, -1, -1, -1, -1, -1, 416, -1, -1, -1, -1, -1, 327, -1, -1, 327, 327, 327, -1, -1, -1, -1, -1, -1, -1, -1, 327, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 416, -1, -1, -1, -1, -1, 327, -1, -1, -1, -1, 327, -1, 327, -1, -1, -1, -1, -1, 416, -1, 327, 327],
    [-1, -1, 372, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 372, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 372, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 372, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [395, -1, -1, -1, -1, -1, 395, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 395, -1, -1, 395, -1, -1, -1, -1, -1, -1, 395, -1, -1, -1, -1, -1, -1, -1, -1, 395, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 395, 395, 395, -1, -1, -1, -1, -1, -1, -1, -1, -1, 395, 395, -1, -1, 82, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 395, 395, 395, -1, -1, 395, -1, -1, 395, 393, -1, -1, 395, -1, -1, -1, 395, -1, -1, -1, 395, -1, -1, -1, -1, -1, -1, -1, -1],
    [37, -1, -1, -1, -1, -1, -1, -1, -1, -1, 37, -1, -1, -1, -1, 37, -1, -1, -1, 37, -1, -1, -1, -1, -1, -1, 37, -1, 37, -1, 37, 37, -1, -1, -1, -1, 37, -1, -1, 37, -1, 37, -1, 37, -1, -1, -1, -1, -1, -1, -1, 37, 37, 37, -1, 37, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 37, -1, -1, 37, 37, 37, -1, -1, -1, -1, -1, -1, -1, -1, 37, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 352, -1, -1, 37, -1, -1, -1, -1, 37, -1, 37, -1, -1, -1, -1, -1, -1, -1, 37, 37],
    [428, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 428, -1, -1, -1, 428, -1, -1, -1, -1, -1, -1, 428, -1, 428, -1, 428, 428, -1, -1, -1, -1, 428, -1, -1, 428, -1, 428, -1, 428, -1, -1, -1, -1, -1, -1, -1, 428, 428, 428, -1, 428, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 428, -1, -1, 428, 428, 428, -1, -1, -1, -1, -1, -1, -1, -1, 428, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 428, -1, -1, -1, -1, 428, -1, 428, -1, -1, -1, -1, -1, -1, -1, 428, 428],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 254, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 183, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 183, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 96, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [200, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 209, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 149, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 274, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 274, -1, -1, -1, -1, -1, -1, -1, -1, -1, 274, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 274, -1, 274, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 126, -1, -1, -1, -1, -1, -1, -1, -1, 45, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 90, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 90, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 90, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 90, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 291, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 291, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 291, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 291, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 414, -1, -1, -1],
    [312, -1, -1, -1, -1, -1, 312, -1, 312, -1, -1, -1, -1, -1, -1, 312, 312, -1, -1, 312, -1, -1, 312, 312, -1, 312, 312, -1, 312, -1, 312, 312, 312, 312, -1, -1, 312, -1, 312, 312, -1, 312, 312, 312, -1, -1, -1, -1, -1, -1, -1, 312, 312, 312, -1, 312, -1, 312, 312, 312, -1, 312, -1, -1, -1, -1, -1, 312, -1, 312, 312, 312, 312, -1, -1, -1, -1, -1, -1, 312, -1, 312, 312, -1, -1, -1, 312, 312, 312, 312, -1, 312, -1, -1, 312, 312, -1, -1, 312, -1, -1, 312, 312, 312, 312, 312, 312, 312, -1, -1, 312, 312, -1, 312, 312],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 20, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 137, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [294, -1, -1, -1, -1, -1, 294, -1, 294, -1, -1, -1, -1, 294, -1, 294, 294, -1, -1, 294, -1, -1, 294, 294, -1, 294, 294, -1, 294, -1, 294, 294, 294, 294, -1, -1, 294, -1, 294, 294, -1, 294, 294, 294, -1, -1, -1, -1, -1, -1, -1, 294, 294, 294, -1, 294, -1, 294, 294, 294, -1, 294, -1, -1, -1, -1, -1, 294, -1, 294, 294, 294, 294, -1, -1, -1, -1, -1, -1, 294, 294, 294, 294, 92, -1, -1, 294, 294, 294, 294, -1, 294, -1, -1, 294, 294, -1, -1, 294, -1, -1, 294, 294, 294, 294, 294, 294, 294, -1, -1, 294, 294, -1, 294, 294],
    [330, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 330, -1, -1, -1, 330, -1, -1, -1, -1, -1, -1, 330, -1, 330, -1, 330, 330, -1, -1, -1, -1, 330, -1, -1, 330, -1, 330, -1, 330, -1, -1, -1, -1, -1, -1, -1, 330, 330, 330, -1, 330, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 330, -1, -1, 330, 330, 330, -1, -1, -1, -1, -1, -1, -1, -1, 330, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 330, -1, -1, -1, -1, 330, -1, 330, -1, -1, -1, -1, -1, -1, -1, 330, 330],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 202, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [166, -1, -1, -1, -1, -1, -1, -1, -1, -1, 94, -1, -1, -1, -1, 166, -1, -1, -1, 166, -1, -1, -1, -1, -1, -1, 166, -1, 166, -1, 166, 166, -1, -1, -1, -1, 166, -1, -1, 166, -1, 166, -1, 166, -1, -1, -1, -1, -1, -1, -1, 166, 166, 166, -1, 166, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 166, -1, -1, 166, 166, 166, -1, -1, -1, -1, -1, -1, -1, -1, 166, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 166, -1, -1, -1, -1, 166, -1, 166, -1, -1, -1, -1, -1, -1, -1, 166, 166],
    [106, -1, -1, -1, -1, -1, 106, -1, 106, -1, -1, -1, -1, -1, -1, 106, 106, -1, -1, 106, -1, -1, 106, 106, -1, 106, 106, -1, 106, -1, 106, 106, 106, 106, -1, -1, 106, -1, 106, 106, -1, 106, 106, 106, -1, -1, -1, -1, -1, -1, -1, 106, 106, 106, -1, 106, -1, 106, 106, 106, -1, 106, -1, -1, -1, -1, -1, 106, -1, 106, 106, 106, 106, -1, -1, -1, -1, -1, -1, 106, -1, 106, 106, -1, -1, -1, 106, 106, 106, 106, -1, 106, -1, -1, 106, 106, -1, -1, 106, -1, -1, 106, 106, 106, 106, 106, 106, 106, -1, -1, 106, 106, -1, 106, 106],
    [-1, -1, 60, -1, -1, -1, -1, -1, -1, -1, 60, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 60, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 60, -1, -1, -1, -1, -1, -1, -1, -1, -1, 60, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 60, -1, 60, -1, -1, 60, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 255, -1, -1, -1, -1, -1, 238, -1, -1, -1, -1, 194, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 112, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 366, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 89, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 248, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [396, -1, 396, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 396, -1, -1, -1, 396, -1, -1, -1, -1, -1, 396, 396, -1, 396, -1, -1, 396, -1, -1, -1, 396, -1, -1, -1, 396, -1, -1, -1, 396, -1, -1, -1, -1, -1, -1, -1, -1, 396, 396, -1, -1, -1, -1, 396, -1, -1, -1, -1, -1, -1, -1, -1, 396, -1, -1, 396, 396, 396, -1, -1, -1, -1, -1, -1, -1, -1, 396, 307, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 396, -1, -1, 396, -1, -1, -1, -1, 396, -1, -1, -1, -1, -1, -1, -1, -1, -1, 396, 396],
    [135, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 150, -1, -1, -1, 150, -1, -1, -1, -1, -1, -1, 150, -1, 150, -1, -1, 150, -1, -1, -1, -1, -1, -1, -1, 150, -1, -1, -1, 150, -1, -1, -1, -1, -1, -1, -1, -1, 150, 150, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 150, -1, -1, 135, 150, 150, -1, -1, -1, -1, -1, -1, -1, -1, 150, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 135, -1, -1, -1, -1, 150, -1, -1, -1, -1, -1, -1, -1, -1, -1, 150, 150],
    [287, -1, 331, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 287, -1, -1, -1, 287, -1, -1, -1, -1, -1, 331, 287, -1, 287, -1, -1, 287, -1, -1, -1, 331, -1, -1, -1, 287, -1, -1, -1, 287, -1, -1, -1, -1, -1, -1, -1, -1, 287, 287, -1, -1, -1, -1, 331, -1, -1, -1, -1, -1, -1, -1, -1, 287, -1, -1, 287, 287, 287, -1, -1, -1, -1, -1, -1, -1, -1, 287, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 331, -1, -1, 287, -1, -1, -1, -1, 287, -1, -1, -1, -1, -1, -1, -1, -1, -1, 287, 287],
    [151, -1, 151, -1, -1, -1, -1, -1, -1, -1, 151, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 151, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 151, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 151, -1, -1, -1, -1, -1, -1, -1, -1, -1, 151, -1, 151, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 151, -1, 151, -1, -1, 151, -1, -1, 151, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 322, -1, -1, -1, -1, -1, -1, -1, -1, -1, 148, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 392, -1, -1, -1, -1, -1, -1, -1, -1, 199, -1, -1, -1, -1],
    [170, -1, 146, -1, -1, -1, -1, -1, -1, -1, 146, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 146, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 146, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 146, -1, -1, -1, -1, -1, -1, -1, -1, -1, 146, -1, 170, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 146, -1, 146, -1, -1, 146, -1, -1, 170, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 129, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 108, -1, -1, -1, -1, -1, -1, -1, 108, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 108, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 108, -1, -1, -1, -1, -1, -1, -1, -1, -1, 108, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 108, -1, 108, -1, -1, 105, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 111, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 114, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 11, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 342, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, 243, -1, -1, -1, -1, -1, -1, 25, -1, -1, -1, -1, -1, 259, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 389, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 176, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 285, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 167, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [141, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 141, -1, -1, -1, 141, -1, -1, -1, -1, -1, -1, 141, -1, 141, -1, 141, 141, -1, -1, -1, -1, 141, -1, -1, 141, -1, 141, -1, 141, -1, -1, -1, -1, -1, -1, -1, 141, 141, 141, -1, 141, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 141, -1, -1, 141, 141, 141, -1, -1, -1, -1, -1, -1, -1, -1, 141, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 141, -1, -1, -1, -1, 141, -1, 141, -1, -1, -1, -1, -1, -1, -1, 141, 141],
    [252, -1, -1, -1, -1, -1, -1, -1, 91, -1, -1, -1, -1, -1, -1, 409, 155, -1, -1, 103, -1, -1, -1, 297, -1, -1, 292, -1, 378, -1, 379, 4, -1, 346, -1, -1, 2, -1, 1, 201, -1, 184, 213, 145, -1, -1, -1, -1, -1, -1, -1, 57, 24, 233, -1, 204, -1, -1, -1, 356, -1, -1, -1, -1, -1, -1, -1, 299, -1, -1, 3, 10, 55, -1, -1, -1, -1, -1, -1, 235, 163, -1, -1, -1, -1, -1, -1, -1, -1, 240, -1, -1, -1, -1, -1, -1, -1, -1, 34, -1, -1, 415, -1, 382, 326, 35, -1, -1, -1, -1, 338, -1, -1, 246, 8],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 154, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 154, -1, -1, -1, -1, -1, -1, -1, -1, -1, 154, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 154, -1, 154, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 205, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 282, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 340, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 340, -1, -1, -1, -1, -1, -1, -1, -1, -1, 340, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 340, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 340, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 401, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 360, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 22, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, 220, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 144, -1, -1, -1, -1, -1, -1, -1, -1, -1, 58, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 68, 217, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 193, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 158, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 86, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 61, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [403, -1, -1, -1, -1, -1, 136, -1, -1, -1, -1, -1, -1, -1, -1, 403, -1, -1, -1, 403, -1, -1, 136, -1, -1, 136, 403, -1, 403, -1, 403, 403, 136, -1, -1, -1, 403, -1, -1, 403, -1, 403, -1, 403, -1, -1, -1, -1, -1, -1, -1, 403, 403, 403, -1, 403, -1, 136, 136, 136, -1, -1, -1, -1, -1, -1, -1, 403, -1, 136, 403, 403, 403, -1, -1, -1, -1, -1, -1, -1, -1, 403, -1, -1, -1, -1, 136, 136, 136, -1, -1, 136, -1, -1, 136, 136, -1, -1, 403, -1, -1, -1, 136, 403, -1, 403, 136, -1, -1, -1, -1, 273, -1, 403, 403],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 237, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 121, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 275, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 242, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 195, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, 56, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 56, -1, -1, 56, -1, -1, -1, -1, -1, -1, 56, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 56, 56, 56, -1, 212, -1, -1, -1, -1, -1, -1, -1, 56, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 56, 56, 56, -1, -1, 56, -1, -1, 56, 56, -1, -1, -1, -1, -1, -1, 56, -1, -1, -1, 56, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, 15, -1, 283, 268, -1, -1, 51, -1, 49, 168, 384, -1, -1, 83, -1, -1, -1, -1, -1, 359, 6, -1, -1, -1, -1, -1, 164, -1, 410, -1, -1, -1, -1, 84, 28, -1, 244, -1, -1, 413, -1, -1, -1, -1, 374, 101, -1, 295, 104, -1, -1, -1, -1, 64, -1, 323, 427, 324, -1, -1, 306, -1, 97, -1, -1, -1, -1, -1, -1, -1, -1, -1, 265, 88, 119, 262, 344, 124, -1, -1, -1, 301, -1, 232, 406, -1, -1, 335, -1, 18, -1, 81, 72, -1, -1, -1, 122, -1, 405, 249, -1, -1, -1, -1, -1, -1, -1, 293, 110, -1, 260, 216, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 328],
    [272, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 225, -1, -1, -1, 225, -1, -1, -1, -1, -1, -1, 225, -1, 225, -1, 229, 225, -1, -1, -1, -1, 229, -1, -1, 225, -1, 229, -1, 225, -1, -1, -1, -1, -1, -1, -1, 279, 225, 225, -1, 229, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 225, -1, -1, 272, 225, 225, -1, -1, -1, -1, -1, -1, -1, -1, 225, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 272, -1, -1, -1, -1, 225, -1, 229, -1, -1, -1, -1, -1, -1, -1, 225, 225],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 402, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, 31, -1, -1, 19, -1, -1, -1, 31, -1, -1, -1, -1, -1, -1, 31, -1, -1, -1, -1, 19, -1, -1, 19, -1, -1, -1, -1, -1, -1, 19, -1, -1, 31, -1, -1, -1, -1, -1, -1, -1, -1, 19, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 19, 19, 19, -1, 321, -1, -1, -1, -1, -1, -1, -1, 19, -1, -1, -1, 31, -1, -1, -1, 31, 321, -1, -1, -1, -1, -1, -1, -1, 19, 19, 19, -1, 321, 321, 31, -1, 19, 19, -1, -1, -1, 31, -1, -1, 19, -1, -1, -1, 19, -1, -1, -1, -1, 31, -1, -1, -1],
    [143, -1, 147, -1, -1, -1, -1, -1, -1, -1, 147, -1, -1, -1, -1, 143, -1, -1, -1, 143, -1, -1, -1, -1, 147, 147, 143, -1, 143, -1, 143, 143, -1, -1, -1, -1, 143, -1, -1, 143, -1, 143, -1, 143, -1, -1, -1, -1, -1, -1, -1, 143, 143, 143, -1, 143, -1, -1, 147, -1, -1, -1, 147, -1, -1, -1, -1, 143, 147, -1, 143, 143, 143, -1, -1, -1, -1, -1, -1, -1, -1, 143, -1, -1, -1, -1, -1, -1, -1, -1, 147, -1, 147, -1, -1, 147, 147, -1, 143, -1, -1, -1, -1, 143, -1, 143, -1, -1, -1, -1, -1, 147, -1, 143, 143],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 318, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, 383, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 133, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 78, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, 361, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 361, -1, -1, 361, -1, -1, -1, -1, -1, -1, 361, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 361, 361, 361, -1, 361, -1, -1, -1, -1, -1, -1, -1, 361, -1, -1, -1, -1, -1, -1, -1, -1, 361, -1, -1, -1, -1, -1, -1, -1, 361, 361, 361, -1, 361, 361, -1, -1, 361, 361, -1, -1, -1, 361, -1, -1, 361, -1, -1, -1, 361, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 325, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 325, -1, -1, -1, -1, -1, -1, -1, -1, -1, 17, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 325, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 325, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 181, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 386, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 386, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 334, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 334, -1, -1, -1, -1, -1, -1, -1, -1, 334, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 157, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 152, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 210, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 0, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 134, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 314, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 314, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 314, -1, -1, -1],
    [107, -1, -1, -1, -1, -1, 107, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 107, -1, -1, 107, -1, -1, -1, -1, -1, -1, 107, -1, -1, -1, -1, -1, -1, -1, -1, 107, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 107, 107, 107, -1, -1, -1, -1, -1, -1, -1, -1, -1, 107, 107, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 107, 107, 107, -1, -1, 107, -1, -1, 107, 107, -1, -1, 107, -1, -1, -1, 107, -1, -1, -1, 107, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, 63, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 63, -1, -1, 63, -1, -1, -1, -1, -1, -1, 63, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 63, 63, 63, -1, -1, -1, -1, -1, -1, -1, -1, -1, 63, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 63, 63, 63, -1, -1, 63, -1, -1, 63, 63, -1, -1, -1, -1, -1, -1, 63, -1, -1, -1, 63, -1, -1, -1, -1, 63, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, 138, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 138, -1, -1, 138, -1, -1, -1, -1, -1, -1, 138, -1, -1, -1, -1, -1, -1, -1, -1, 120, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 138, 138, 138, -1, -1, -1, -1, -1, -1, -1, -1, -1, 138, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 138, 138, 138, -1, -1, 138, -1, -1, 138, 138, -1, -1, -1, -1, -1, -1, 138, -1, -1, -1, 138, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 161, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [26, -1, -1, -1, -1, -1, 420, -1, 420, -1, -1, -1, -1, -1, -1, 26, 420, -1, -1, 26, -1, -1, 420, 420, -1, 420, 26, -1, 26, -1, 26, 26, 420, 420, -1, -1, 26, -1, 420, 26, -1, 26, 420, 26, -1, -1, -1, -1, -1, -1, -1, 26, 26, 26, -1, 26, -1, 420, 420, 420, -1, 420, -1, -1, -1, -1, -1, 26, -1, 420, 26, 26, 26, -1, -1, -1, -1, -1, -1, 420, -1, 26, -1, -1, -1, -1, 420, 420, 420, 420, -1, 420, -1, -1, 420, 420, -1, -1, 26, -1, -1, 420, 420, 26, 420, 26, 420, 420, -1, -1, 420, 420, -1, 26, 26],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 80, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 354, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, 190, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 190, -1, -1, 190, -1, -1, -1, -1, -1, -1, 190, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 190, 190, 190, -1, 190, -1, -1, -1, -1, -1, -1, -1, 190, -1, -1, -1, -1, -1, -1, -1, -1, 190, -1, -1, -1, -1, -1, -1, -1, 190, 190, 190, -1, 190, 190, -1, -1, 190, 190, -1, -1, -1, 190, -1, -1, 190, -1, -1, -1, 190, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 370, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 14, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 32, -1, -1, -1],
    [75, -1, 75, -1, -1, -1, -1, -1, -1, -1, 75, -1, -1, -1, -1, 75, -1, -1, -1, 75, -1, -1, -1, -1, 75, 75, 75, -1, 75, -1, 75, 75, -1, -1, -1, 75, 75, -1, -1, 75, -1, 75, -1, 75, -1, -1, -1, -1, -1, -1, -1, 75, 75, 75, -1, 75, -1, -1, 75, -1, -1, 308, 75, -1, -1, -1, -1, 75, 75, -1, 75, 75, 75, -1, -1, -1, -1, -1, -1, -1, -1, 75, -1, -1, -1, -1, -1, -1, -1, -1, 75, -1, 75, -1, -1, 75, 75, -1, 75, -1, -1, -1, -1, 75, -1, 75, -1, -1, -1, -1, -1, 75, -1, 75, 75],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 408, -1, -1, -1, -1, 47, -1, -1, -1, 258, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 128, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 286, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 173, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 173, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 62, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, 175, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 175, -1, -1, 175, -1, -1, -1, -1, -1, -1, 175, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 175, 175, 175, -1, 175, -1, -1, -1, -1, -1, -1, -1, 175, -1, -1, -1, -1, -1, -1, -1, -1, 171, -1, -1, -1, -1, -1, -1, -1, 175, 175, 175, -1, 171, 175, -1, -1, 175, 175, -1, -1, -1, 171, -1, -1, 175, -1, -1, -1, 175, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 178, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 315, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 5, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 36, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 36, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 174, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 228, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [206, -1, 206, -1, -1, -1, -1, -1, -1, -1, 206, -1, -1, -1, -1, 206, -1, -1, -1, 206, -1, -1, -1, -1, 206, 206, 206, -1, 206, -1, 206, 206, -1, -1, -1, 206, 206, -1, -1, 206, -1, 206, -1, 206, -1, -1, -1, -1, -1, -1, -1, 206, 206, 206, -1, 206, -1, -1, 206, -1, -1, 426, 206, -1, -1, -1, -1, 206, 206, -1, 206, 206, 206, -1, -1, -1, -1, -1, -1, -1, -1, 206, -1, -1, -1, -1, -1, -1, -1, -1, 206, -1, 206, -1, -1, 206, 206, -1, 206, -1, -1, -1, -1, 206, -1, 206, -1, -1, -1, -1, -1, 206, -1, 206, 206],
    [23, 281, -1, 281, 281, -1, 425, 281, 23, 281, 281, 281, -1, -1, 281, 23, 23, -1, 311, 23, 281, 281, 425, 23, -1, 277, 23, 281, 23, 281, 23, 23, 425, 23, 281, 281, 23, 281, 23, 23, 281, 23, 23, 23, -1, 281, 281, -1, 281, 281, -1, 23, 23, 23, 281, 23, 281, 281, 281, 23, -1, 281, -1, 281, -1, -1, -1, 23, -1, -1, 23, 23, 23, 281, 281, 281, 281, 281, 281, 23, 23, -1, 281, -1, 281, 281, 425, 425, 281, 23, 281, -1, 281, 281, -1, -1, -1, 281, 23, 281, 281, 23, 13, 23, 23, 23, 425, -1, 281, 281, 23, 281, 281, 23, 23],
    [365, -1, 365, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 365, -1, -1, -1, 365, -1, -1, -1, -1, -1, 365, 365, -1, 365, -1, -1, 365, -1, -1, -1, 365, -1, -1, -1, 365, -1, -1, -1, 365, -1, -1, -1, -1, -1, -1, -1, -1, 365, 365, -1, -1, -1, -1, 365, -1, -1, -1, -1, -1, -1, -1, -1, 365, -1, -1, 365, 365, 365, -1, -1, -1, -1, -1, -1, -1, -1, 365, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 365, -1, -1, 365, -1, -1, -1, -1, 365, -1, -1, -1, -1, -1, -1, -1, -1, -1, 365, 365],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 70, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 250, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  ]
  def terminal(self, str):
    return self.str_terminal[str]
  def terminalNames(self):
    return list(self.str_terminal.keys())
  def isTerminal(self, id):
    return 0 <= id <= 114
  def isNonTerminal(self, id):
    return 115 <= id <= 246
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
  def _DIRECT_DECLARATOR_PARAMETER_LIST(self, depth=0, tracer=None):
    rule = self.rule(115)
    tree = ParseTree( NonTerminal(115, self.getAtomString(115)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 363:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PARAMETER_TYPE_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 411:
      tree.astTransform = AstTransformNodeCreator('ParameterList', {'identifiers': 0})
      subtree = self.__GEN33(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN18(self, depth=0, tracer=None):
    rule = self.rule(116)
    tree = ParseTree( NonTerminal(116, self.getAtomString(116)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [78]):
      return tree
    if self.sym == None:
      return tree
    if rule == 191:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DESIGNATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN18(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _PARAMETER_DECLARATION_SUB_SUB(self, depth=0, tracer=None):
    rule = self.rule(117)
    tree = ParseTree( NonTerminal(117, self.getAtomString(117)), tracer )
    tree.list = False
    if self.sym == None:
      return tree
    if rule == 12:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__DIRECT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 214:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN36(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [58, 2, 25]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__DIRECT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _TYPE_SPECIFIER(self, depth=0, tracer=None):
    rule = self.rule(118)
    tree = ParseTree( NonTerminal(118, self.getAtomString(118)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 21:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(43, tracer) # short
      tree.add(t)
      return tree
    elif rule == 38:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(28, tracer) # int
      tree.add(t)
      return tree
    elif rule == 44:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._TYPEDEF_NAME(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 69:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._UNION_SPECIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 116:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(113, tracer) # double
      tree.add(t)
      return tree
    elif rule == 131:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._ENUM_SPECIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 172:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(19, tracer) # long
      tree.add(t)
      return tree
    elif rule == 179:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(15, tracer) # unsigned
      tree.add(t)
      return tree
    elif rule == 188:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(71, tracer) # char
      tree.add(t)
      return tree
    elif rule == 230:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STRUCT_SPECIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 253:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(31, tracer) # imaginary
      tree.add(t)
      return tree
    elif rule == 264:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(39, tracer) # signed
      tree.add(t)
      return tree
    elif rule == 296:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(52, tracer) # bool
      tree.add(t)
      return tree
    elif rule == 329:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(103, tracer) # float
      tree.add(t)
      return tree
    elif rule == 380:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(53, tracer) # complex
      tree.add(t)
      return tree
    elif rule == 400:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(72, tracer) # void
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _EXTERNAL_DECLARATOR(self, depth=0, tracer=None):
    rule = self.rule(119)
    tree = ParseTree( NonTerminal(119, self.getAtomString(119)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 357:
      tree.astTransform = AstTransformNodeCreator('ExternalDeclarator', {'init_declarator': 1})
      t = self.expect(96, tracer) # declarator_hint
      tree.add(t)
      subtree = self.__GEN6(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _EXPRESSION_OPT(self, depth=0, tracer=None):
    rule = self.rule(120)
    tree = ParseTree( NonTerminal(120, self.getAtomString(120)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [10, 111]):
      return tree
    if self.sym == None:
      return tree
    if rule == 54:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [6, 86, 102, 57, 94, 88, 69, 95, 87, 58, 22, 91, 32, 59, 106, 25]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    return tree
  def _POINTER_OPT(self, depth=0, tracer=None):
    rule = self.rule(121)
    tree = ParseTree( NonTerminal(121, self.getAtomString(121)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [58, 90, 68, 2, 92, 10, 25]):
      return tree
    if self.sym == None:
      return tree
    if rule == 52:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._POINTER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _EXTERNAL_PROTOTYPE(self, depth=0, tracer=None):
    rule = self.rule(123)
    tree = ParseTree( NonTerminal(123, self.getAtomString(123)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 397:
      tree.astTransform = AstTransformNodeCreator('FunctionPrototype', {'declaration_list': 2, 'declarator': 1})
      t = self.expect(62, tracer) # function_prototype_hint
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
  def _ENUMERATION_CONSTANT(self, depth=0, tracer=None):
    rule = self.rule(124)
    tree = ParseTree( NonTerminal(124, self.getAtomString(124)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 159:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(25, tracer) # identifier
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _FUNCTION_SPECIFIER(self, depth=0, tracer=None):
    rule = self.rule(125)
    tree = ParseTree( NonTerminal(125, self.getAtomString(125)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 353:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(51, tracer) # inline
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _DIRECT_DECLARATOR_MODIFIER_LIST_OPT(self, depth=0, tracer=None):
    rule = self.rule(126)
    tree = ParseTree( NonTerminal(126, self.getAtomString(126)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [86, 102, 57, 32, 69, 94, 95, 91, 88, 58, 22, 6, 87, 106, 25, 59]):
      return tree
    if self.sym == None:
      return tree
    if rule == 289:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN29(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _DIRECT_DECLARATOR_SIZE(self, depth=0, tracer=None):
    rule = self.rule(127)
    tree = ParseTree( NonTerminal(127, self.getAtomString(127)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 371:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(95, tracer) # asterisk
      tree.add(t)
      return tree
    elif rule == 422:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [6, 86, 102, 57, 94, 88, 69, 95, 87, 58, 22, 91, 32, 59, 106, 25]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _DECLARATOR(self, depth=0, tracer=None):
    rule = self.rule(128)
    tree = ParseTree( NonTerminal(128, self.getAtomString(128)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 280:
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
    elif self.sym.getId() in [58, 2, 25]:
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
  def _DECLARATION_LIST(self, depth=0, tracer=None):
    rule = self.rule(129)
    tree = ParseTree( NonTerminal(129, self.getAtomString(129)), tracer )
    tree.list = False
    if self.sym == None:
      return tree
    if rule == 40:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN7(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN5(self, depth=0, tracer=None):
    rule = self.rule(130)
    tree = ParseTree( NonTerminal(130, self.getAtomString(130)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [61, 111, 92]):
      return tree
    if self.sym == None:
      return tree
    if rule == 215:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DECLARATION_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _ENUMERATOR_ASSIGNMENT(self, depth=0, tracer=None):
    rule = self.rule(131)
    tree = ParseTree( NonTerminal(131, self.getAtomString(131)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [92, 17]):
      return tree
    if self.sym == None:
      return tree
    if rule == 227:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(78, tracer) # assign
      tree.add(t)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _DIRECT_ABSTRACT_DECLARATOR_SUB0(self, depth=0, tracer=None):
    rule = self.rule(132)
    tree = ParseTree( NonTerminal(132, self.getAtomString(132)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 192:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(58, tracer) # lparen
      tree.add(t)
      subtree = self._ABSTRACT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(10, tracer) # rparen
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN9(self, depth=0, tracer=None):
    rule = self.rule(134)
    tree = ParseTree( NonTerminal(134, self.getAtomString(134)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [58, 92, 68, 10, 90]):
      return tree
    if self.sym == None:
      return tree
    if rule == 27:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DIRECT_ABSTRACT_DECLARATOR_SUB0(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN39(self, depth=0, tracer=None):
    rule = self.rule(135)
    tree = ParseTree( NonTerminal(135, self.getAtomString(135)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [82]):
      return tree
    if self.sym == None:
      return tree
    if rule == 221:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._BLOCK_ITEM(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN39(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [6, 86, 102, 57, 94, 88, 69, 95, 87, 58, 22, 91, 32, 59, 106, 25]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._BLOCK_ITEM(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN39(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    return tree
  def _DIRECT_DECLARATOR_MODIFIER(self, depth=0, tracer=None):
    rule = self.rule(136)
    tree = ParseTree( NonTerminal(136, self.getAtomString(136)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 347:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._TYPE_QUALIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 377:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(41, tracer) # static
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN43(self, depth=0, tracer=None):
    rule = self.rule(137)
    tree = ParseTree( NonTerminal(137, self.getAtomString(137)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 73:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__EXPR_SANS_COMMA(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN44(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN29(self, depth=0, tracer=None):
    rule = self.rule(138)
    tree = ParseTree( NonTerminal(138, self.getAtomString(138)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [86, 91, 87, 57, 88, 69, 95, 94, 58, 59, 106, 102, 32, 6, 25, 22]):
      return tree
    if self.sym == None:
      return tree
    if rule == 33:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DIRECT_DECLARATOR_MODIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN29(depth)
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
    if rule == 109:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(61, tracer) # lbrace
      tree.add(t)
      subtree = self.__GEN38(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(82, tracer) # rbrace
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _DIRECT_ABSTRACT_DECLARATOR_SUB1(self, depth=0, tracer=None):
    rule = self.rule(140)
    tree = ParseTree( NonTerminal(140, self.getAtomString(140)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 9:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(90, tracer) # lsquare
      tree.add(t)
      subtree = self._DIRECT_ABSTRACT_DECLARATOR_EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(73, tracer) # rsquare
      tree.add(t)
      return tree
    elif rule == 30:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(58, tracer) # lparen
      tree.add(t)
      subtree = self._DIRECT_ABSTRACT_DECLARATOR_SUB2(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(10, tracer) # rparen
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN30(self, depth=0, tracer=None):
    rule = self.rule(141)
    tree = ParseTree( NonTerminal(141, self.getAtomString(141)), tracer )
    tree.list = 'slist'
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 66:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PARAMETER_DECLARATION(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN31(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _INIT_DECLARATOR(self, depth=0, tracer=None):
    rule = self.rule(142)
    tree = ParseTree( NonTerminal(142, self.getAtomString(142)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 177:
      tree.astTransform = AstTransformNodeCreator('InitDeclarator', {'initializer': 1, 'declarator': 0})
      subtree = self._DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN14(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [58, 2, 25]:
      tree.astTransform = AstTransformNodeCreator('InitDeclarator', {'initializer': 1, 'declarator': 0})
      subtree = self._DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN14(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN6(self, depth=0, tracer=None):
    rule = self.rule(143)
    tree = ParseTree( NonTerminal(143, self.getAtomString(143)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [92, 111]):
      return tree
    if self.sym == None:
      return tree
    if rule == 234:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._INIT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [58, 2, 25]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._INIT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    return tree
  def _PARAMETER_DECLARATION_SUB(self, depth=0, tracer=None):
    rule = self.rule(144)
    tree = ParseTree( NonTerminal(144, self.getAtomString(144)), tracer )
    tree.list = False
    if self.sym == None:
      return tree
    if rule == 93:
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
    elif self.sym.getId() in [58, 2, 25]:
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
  def __GEN41(self, depth=0, tracer=None):
    rule = self.rule(145)
    tree = ParseTree( NonTerminal(145, self.getAtomString(145)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [23, 6, 39, 8, 15, 52, 95, 16, 25, 53, 30, 31, 32, 33, 36, 38, 51, 22, 41, 59, 86, 105, 42, 55, 91, 57, 58, 81, 61, 104, 13, 67, 102, 69, 70, 106, 71, 72, 26, 82, 0, 43, 79, 98, 28, 111, 87, 88, 114, 94, 19, 101, 103, 107, 110, 113, 89]):
      return tree
    if self.sym == None:
      return tree
    if rule == 271:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._ELSE_STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN35(self, depth=0, tracer=None):
    rule = self.rule(146)
    tree = ParseTree( NonTerminal(146, self.getAtomString(146)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [68, 92, 10]):
      return tree
    if self.sym == None:
      return tree
    if rule == 349:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PARAMETER_DECLARATION_SUB(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [58, 2, 25]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PARAMETER_DECLARATION_SUB(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    return tree
  def _STATEMENT(self, depth=0, tracer=None):
    rule = self.rule(147)
    tree = ParseTree( NonTerminal(147, self.getAtomString(147)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 117:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._SELECTION_STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 142:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._EXPRESSION_STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 245:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._LABELED_STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 247:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._ITERATION_STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 269:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._COMPOUND_STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 398:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._JUMP_STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [6, 86, 102, 57, 94, 88, 69, 95, 87, 58, 22, 91, 32, 59, 106, 25]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._EXPRESSION_STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _SIZEOF_BODY(self, depth=0, tracer=None):
    rule = self.rule(148)
    tree = ParseTree( NonTerminal(148, self.getAtomString(148)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 162:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(25, tracer) # identifier
      tree.add(t)
      return tree
    elif rule == 182:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(58, tracer) # lparen
      tree.add(t)
      subtree = self._TYPE_NAME(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(10, tracer) # rparen
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _ABSTRACT_DECLARATOR(self, depth=0, tracer=None):
    rule = self.rule(149)
    tree = ParseTree( NonTerminal(149, self.getAtomString(149)), tracer )
    tree.list = False
    if self.sym == None:
      return tree
    if rule == 74:
      tree.astTransform = AstTransformNodeCreator('AbstractDeclarator', {'direct_abstract_declarator': 1, 'pointer': 1})
      subtree = self._POINTER_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN36(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _TRAILING_COMMA_OPT(self, depth=0, tracer=None):
    rule = self.rule(150)
    tree = ParseTree( NonTerminal(150, self.getAtomString(150)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [82]):
      return tree
    if self.sym == None:
      return tree
    if rule == 224:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(17, tracer) # trailing_comma
      tree.add(t)
      return tree
    return tree
  def _ELSE_IF_STATEMENT_LIST(self, depth=0, tracer=None):
    rule = self.rule(151)
    tree = ParseTree( NonTerminal(151, self.getAtomString(151)), tracer )
    tree.list = False
    if self.sym == None:
      return tree
    if rule == 208:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN42(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN40(self, depth=0, tracer=None):
    rule = self.rule(152)
    tree = ParseTree( NonTerminal(152, self.getAtomString(152)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [23, 6, 39, 8, 80, 52, 95, 16, 25, 53, 30, 31, 32, 33, 36, 38, 51, 22, 41, 59, 86, 105, 42, 55, 91, 57, 58, 81, 61, 104, 13, 67, 102, 69, 70, 106, 71, 72, 26, 82, 0, 43, 79, 15, 98, 28, 111, 87, 88, 114, 94, 19, 101, 103, 107, 110, 113, 89]):
      return tree
    if self.sym == None:
      return tree
    if rule == 256:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._ELSE_IF_STATEMENT_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN10(self, depth=0, tracer=None):
    rule = self.rule(153)
    tree = ParseTree( NonTerminal(153, self.getAtomString(153)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [68, 10, 92]):
      return tree
    if self.sym == None:
      return tree
    if rule == 43:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DIRECT_ABSTRACT_DECLARATOR_SUB1(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN10(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _DECLARATION(self, depth=0, tracer=None):
    rule = self.rule(154)
    tree = ParseTree( NonTerminal(154, self.getAtomString(154)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 67:
      tree.astTransform = AstTransformNodeCreator('Declaration', {'init_declarators': 1, 'declaration_specifiers': 0})
      subtree = self.__GEN1(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN8(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(111, tracer) # semi
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN7(self, depth=0, tracer=None):
    rule = self.rule(155)
    tree = ParseTree( NonTerminal(155, self.getAtomString(155)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [61, 111, 92]):
      return tree
    if self.sym == None:
      return tree
    if rule == 327:
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
  def __GEN12(self, depth=0, tracer=None):
    rule = self.rule(156)
    tree = ParseTree( NonTerminal(156, self.getAtomString(156)), tracer )
    tree.list = 'slist'
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 372:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._INIT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN13(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [58, 2, 25]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._INIT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN13(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _DIRECT_ABSTRACT_DECLARATOR_EXPR(self, depth=0, tracer=None):
    rule = self.rule(157)
    tree = ParseTree( NonTerminal(157, self.getAtomString(157)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [73]):
      return tree
    if self.sym == None:
      return tree
    if rule == 393:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(95, tracer) # asterisk
      tree.add(t)
      return tree
    elif rule == 395:
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
    elif self.sym.getId() in [6, 86, 102, 57, 94, 88, 69, 95, 87, 58, 22, 91, 32, 59, 106, 25]:
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
  def _DIRECT_ABSTRACT_DECLARATOR_SUB2(self, depth=0, tracer=None):
    rule = self.rule(158)
    tree = ParseTree( NonTerminal(158, self.getAtomString(158)), tracer )
    tree.list = False
    if self.sym == None:
      return tree
    if rule == 37:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN11(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 352:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(95, tracer) # asterisk
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _PARAMETER_DECLARATION(self, depth=0, tracer=None):
    rule = self.rule(159)
    tree = ParseTree( NonTerminal(159, self.getAtomString(159)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 428:
      tree.astTransform = AstTransformNodeCreator('ParameterDeclaration', {'sub': 1, 'declaration_specifiers': 0})
      subtree = self.__GEN1(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN35(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN44(self, depth=0, tracer=None):
    rule = self.rule(160)
    tree = ParseTree( NonTerminal(160, self.getAtomString(160)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 254:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(92, tracer) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self.__EXPR_SANS_COMMA(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN44(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN31(self, depth=0, tracer=None):
    rule = self.rule(161)
    tree = ParseTree( NonTerminal(161, self.getAtomString(161)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in [68, 10]):
      return tree
    if self.sym == None:
      return tree
    if rule == 96:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(92, tracer) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self._PARAMETER_DECLARATION(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN31(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _TYPE_QUALIFIER(self, depth=0, tracer=None):
    rule = self.rule(162)
    tree = ParseTree( NonTerminal(162, self.getAtomString(162)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 149:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(98, tracer) # volatile
      tree.add(t)
      return tree
    elif rule == 200:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(0, tracer) # restrict
      tree.add(t)
      return tree
    elif rule == 209:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(70, tracer) # const
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN36(self, depth=0, tracer=None):
    rule = self.rule(163)
    tree = ParseTree( NonTerminal(163, self.getAtomString(163)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [68, 10, 92]):
      return tree
    if self.sym == None:
      return tree
    if rule == 274:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DIRECT_ABSTRACT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _DESIGNATOR(self, depth=0, tracer=None):
    rule = self.rule(164)
    tree = ParseTree( NonTerminal(164, self.getAtomString(164)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 45:
      tree.astTransform = AstTransformNodeCreator('MemberAccess', {'name': 1})
      t = self.expect(99, tracer) # dot
      tree.add(t)
      t = self.expect(25, tracer) # identifier
      tree.add(t)
      return tree
    elif rule == 126:
      tree.astTransform = AstTransformNodeCreator('ArrayAccess', {'index': 1})
      t = self.expect(90, tracer) # lsquare
      tree.add(t)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(73, tracer) # rsquare
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _INIT_DECLARATOR_LIST(self, depth=0, tracer=None):
    rule = self.rule(165)
    tree = ParseTree( NonTerminal(165, self.getAtomString(165)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 90:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN12(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [58, 2, 25]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN12(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN8(self, depth=0, tracer=None):
    rule = self.rule(166)
    tree = ParseTree( NonTerminal(166, self.getAtomString(166)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [111]):
      return tree
    if self.sym == None:
      return tree
    if rule == 291:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._INIT_DECLARATOR_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [58, 2, 25]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._INIT_DECLARATOR_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    return tree
  def _BLOCK_ITEM_LIST(self, depth=0, tracer=None):
    rule = self.rule(167)
    tree = ParseTree( NonTerminal(167, self.getAtomString(167)), tracer )
    tree.list = False
    if self.sym == None:
      return tree
    if rule == 312:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN39(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [6, 86, 102, 57, 94, 88, 69, 95, 87, 58, 22, 91, 32, 59, 106, 25]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN39(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _ELSE_STATEMENT(self, depth=0, tracer=None):
    rule = self.rule(168)
    tree = ParseTree( NonTerminal(168, self.getAtomString(168)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 20:
      tree.astTransform = AstTransformNodeCreator('Else', {'statement': 1})
      t = self.expect(80, tracer) # else
      tree.add(t)
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(13, tracer) # endif
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _ELSE_IF_STATEMENT(self, depth=0, tracer=None):
    rule = self.rule(169)
    tree = ParseTree( NonTerminal(169, self.getAtomString(169)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 137:
      tree.astTransform = AstTransformNodeCreator('ElseIf', {'statement': 4, 'condition': 2})
      t = self.expect(83, tracer) # else_if
      tree.add(t)
      t = self.expect(58, tracer) # lparen
      tree.add(t)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(10, tracer) # rparen
      tree.add(t)
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(13, tracer) # endif
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN42(self, depth=0, tracer=None):
    rule = self.rule(170)
    tree = ParseTree( NonTerminal(170, self.getAtomString(170)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [23, 6, 39, 8, 80, 52, 95, 16, 25, 53, 30, 31, 32, 33, 36, 38, 51, 22, 41, 59, 86, 105, 42, 55, 91, 57, 58, 81, 61, 104, 13, 67, 102, 69, 70, 106, 71, 72, 26, 82, 0, 43, 79, 15, 98, 28, 111, 87, 88, 114, 94, 19, 101, 103, 107, 110, 113, 89]):
      return tree
    if self.sym == None:
      return tree
    if rule == 92:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._ELSE_IF_STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN42(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _PARAMETER_TYPE_LIST(self, depth=0, tracer=None):
    rule = self.rule(171)
    tree = ParseTree( NonTerminal(171, self.getAtomString(171)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 330:
      tree.astTransform = AstTransformNodeCreator('ParameterTypeList', {'parameter_declarations': 0, 'va_args': 1})
      subtree = self.__GEN30(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN32(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN33(self, depth=0, tracer=None):
    rule = self.rule(172)
    tree = ParseTree( NonTerminal(172, self.getAtomString(172)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 202:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._IDENTIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN34(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN11(self, depth=0, tracer=None):
    rule = self.rule(173)
    tree = ParseTree( NonTerminal(173, self.getAtomString(173)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [10]):
      return tree
    if self.sym == None:
      return tree
    if rule == 166:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PARAMETER_TYPE_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN38(self, depth=0, tracer=None):
    rule = self.rule(174)
    tree = ParseTree( NonTerminal(174, self.getAtomString(174)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [82]):
      return tree
    if self.sym == None:
      return tree
    if rule == 106:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._BLOCK_ITEM_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [6, 86, 102, 57, 94, 88, 69, 95, 87, 58, 22, 91, 32, 59, 106, 25]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._BLOCK_ITEM_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    return tree
  def _POINTER(self, depth=0, tracer=None):
    rule = self.rule(175)
    tree = ParseTree( NonTerminal(175, self.getAtomString(175)), tracer )
    tree.list = False
    if self.sym == None:
      return tree
    if rule == 60:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN37(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _STORAGE_CLASS_SPECIFIER(self, depth=0, tracer=None):
    rule = self.rule(176)
    tree = ParseTree( NonTerminal(176, self.getAtomString(176)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 112:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(55, tracer) # register
      tree.add(t)
      return tree
    elif rule == 194:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(41, tracer) # static
      tree.add(t)
      return tree
    elif rule == 238:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(36, tracer) # extern
      tree.add(t)
      return tree
    elif rule == 255:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(30, tracer) # typedef
      tree.add(t)
      return tree
    elif rule == 366:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(105, tracer) # auto
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _EXTERNAL_DECLARATION_SUB_SUB(self, depth=0, tracer=None):
    rule = self.rule(177)
    tree = ParseTree( NonTerminal(177, self.getAtomString(177)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 89:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._EXTERNAL_PROTOTYPE(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 248:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._EXTERNAL_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN20(self, depth=0, tracer=None):
    rule = self.rule(178)
    tree = ParseTree( NonTerminal(178, self.getAtomString(178)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [82]):
      return tree
    if self.sym == None:
      return tree
    if rule == 396:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STRUCT_DECLARATION(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN20(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [58, 2, 25]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STRUCT_DECLARATION(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN20(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    return tree
  def _SPECIFIER_QUALIFIER(self, depth=0, tracer=None):
    rule = self.rule(179)
    tree = ParseTree( NonTerminal(179, self.getAtomString(179)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 135:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._TYPE_QUALIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 150:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._TYPE_SPECIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN21(self, depth=0, tracer=None):
    rule = self.rule(180)
    tree = ParseTree( NonTerminal(180, self.getAtomString(180)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [58, 35, 95, 2, 25]):
      return tree
    if self.sym == None:
      return tree
    if rule == 287:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._SPECIFIER_QUALIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN21(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _TYPE_QUALIFIER_LIST_OPT(self, depth=0, tracer=None):
    rule = self.rule(181)
    tree = ParseTree( NonTerminal(181, self.getAtomString(181)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [58, 41, 90, 68, 25, 2, 92, 10, 95]):
      return tree
    if self.sym == None:
      return tree
    if rule == 151:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN28(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _JUMP_STATEMENT(self, depth=0, tracer=None):
    rule = self.rule(182)
    tree = ParseTree( NonTerminal(182, self.getAtomString(182)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 148:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(89, tracer) # continue
      tree.add(t)
      return tree
    elif rule == 199:
      tree.astTransform = AstTransformNodeCreator('Return', {'expr': 1})
      t = self.expect(110, tracer) # return
      tree.add(t)
      subtree = self._EXPRESSION_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(111, tracer) # semi
      tree.add(t)
      return tree
    elif rule == 322:
      tree.astTransform = AstTransformNodeCreator('Goto', {'name': 1})
      t = self.expect(79, tracer) # goto
      tree.add(t)
      t = self.expect(25, tracer) # identifier
      tree.add(t)
      t = self.expect(111, tracer) # semi
      tree.add(t)
      return tree
    elif rule == 392:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(101, tracer) # break
      tree.add(t)
      t = self.expect(111, tracer) # semi
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN28(self, depth=0, tracer=None):
    rule = self.rule(183)
    tree = ParseTree( NonTerminal(183, self.getAtomString(183)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [41, 58, 10, 92, 95, 90, 68, 2, 25]):
      return tree
    if self.sym == None:
      return tree
    if rule == 170:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._TYPE_QUALIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN28(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _POINTER_SUB(self, depth=0, tracer=None):
    rule = self.rule(184)
    tree = ParseTree( NonTerminal(184, self.getAtomString(184)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 129:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(95, tracer) # asterisk
      tree.add(t)
      subtree = self._TYPE_QUALIFIER_LIST_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN37(self, depth=0, tracer=None):
    rule = self.rule(185)
    tree = ParseTree( NonTerminal(185, self.getAtomString(185)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [58, 90, 68, 2, 92, 10, 25]):
      return tree
    if self.sym == None:
      return tree
    if rule == 105:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._POINTER_SUB(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN37(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN13(self, depth=0, tracer=None):
    rule = self.rule(186)
    tree = ParseTree( NonTerminal(186, self.getAtomString(186)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in [111]):
      return tree
    if self.sym == None:
      return tree
    if rule == 111:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(92, tracer) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self._INIT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN13(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _ENUMERATOR(self, depth=0, tracer=None):
    rule = self.rule(187)
    tree = ParseTree( NonTerminal(187, self.getAtomString(187)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 11:
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
  def __GEN26(self, depth=0, tracer=None):
    rule = self.rule(188)
    tree = ParseTree( NonTerminal(188, self.getAtomString(188)), tracer )
    tree.list = 'slist'
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 342:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._ENUMERATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN27(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _PP(self, depth=0, tracer=None):
    rule = self.rule(189)
    tree = ParseTree( NonTerminal(189, self.getAtomString(189)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 25:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(12, tracer) # defined_separator
      tree.add(t)
      return tree
    elif rule == 243:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(5, tracer) # defined
      tree.add(t)
      return tree
    elif rule == 259:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(18, tracer) # pp_number
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN27(self, depth=0, tracer=None):
    rule = self.rule(190)
    tree = ParseTree( NonTerminal(190, self.getAtomString(190)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in [17]):
      return tree
    if self.sym == None:
      return tree
    if rule == 176:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(92, tracer) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self._ENUMERATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN27(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _TYPE_NAME(self, depth=0, tracer=None):
    rule = self.rule(191)
    tree = ParseTree( NonTerminal(191, self.getAtomString(191)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 167:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(71, tracer) # char
      tree.add(t)
      return tree
    elif rule == 285:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(28, tracer) # int
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN1(self, depth=0, tracer=None):
    rule = self.rule(192)
    tree = ParseTree( NonTerminal(192, self.getAtomString(192)), tracer )
    tree.list = 'mlist'
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 141:
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
  def _KEYWORD(self, depth=0, tracer=None):
    rule = self.rule(193)
    tree = ParseTree( NonTerminal(193, self.getAtomString(193)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 1:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(38, tracer) # for
      tree.add(t)
      return tree
    elif rule == 2:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(36, tracer) # extern
      tree.add(t)
      return tree
    elif rule == 3:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(70, tracer) # const
      tree.add(t)
      return tree
    elif rule == 4:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(31, tracer) # imaginary
      tree.add(t)
      return tree
    elif rule == 8:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(114, tracer) # enum
      tree.add(t)
      return tree
    elif rule == 10:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(71, tracer) # char
      tree.add(t)
      return tree
    elif rule == 24:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(52, tracer) # bool
      tree.add(t)
      return tree
    elif rule == 34:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(98, tracer) # volatile
      tree.add(t)
      return tree
    elif rule == 35:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(105, tracer) # auto
      tree.add(t)
      return tree
    elif rule == 55:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(72, tracer) # void
      tree.add(t)
      return tree
    elif rule == 57:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(51, tracer) # inline
      tree.add(t)
      return tree
    elif rule == 91:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(8, tracer) # default
      tree.add(t)
      return tree
    elif rule == 103:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(19, tracer) # long
      tree.add(t)
      return tree
    elif rule == 145:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(43, tracer) # short
      tree.add(t)
      return tree
    elif rule == 155:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(16, tracer) # switch
      tree.add(t)
      return tree
    elif rule == 163:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(80, tracer) # else
      tree.add(t)
      return tree
    elif rule == 184:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(41, tracer) # static
      tree.add(t)
      return tree
    elif rule == 201:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(39, tracer) # signed
      tree.add(t)
      return tree
    elif rule == 204:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(55, tracer) # register
      tree.add(t)
      return tree
    elif rule == 213:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(42, tracer) # while
      tree.add(t)
      return tree
    elif rule == 233:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(53, tracer) # complex
      tree.add(t)
      return tree
    elif rule == 235:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(79, tracer) # goto
      tree.add(t)
      return tree
    elif rule == 240:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(89, tracer) # continue
      tree.add(t)
      return tree
    elif rule == 246:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(113, tracer) # double
      tree.add(t)
      return tree
    elif rule == 252:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(0, tracer) # restrict
      tree.add(t)
      return tree
    elif rule == 292:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(26, tracer) # union
      tree.add(t)
      return tree
    elif rule == 297:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(23, tracer) # case
      tree.add(t)
      return tree
    elif rule == 299:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(67, tracer) # struct
      tree.add(t)
      return tree
    elif rule == 326:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(104, tracer) # if
      tree.add(t)
      return tree
    elif rule == 338:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(110, tracer) # return
      tree.add(t)
      return tree
    elif rule == 346:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(33, tracer) # do
      tree.add(t)
      return tree
    elif rule == 356:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(59, tracer) # sizeof
      tree.add(t)
      return tree
    elif rule == 378:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(28, tracer) # int
      tree.add(t)
      return tree
    elif rule == 379:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(30, tracer) # typedef
      tree.add(t)
      return tree
    elif rule == 382:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(103, tracer) # float
      tree.add(t)
      return tree
    elif rule == 409:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(15, tracer) # unsigned
      tree.add(t)
      return tree
    elif rule == 415:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(101, tracer) # break
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _DIRECT_ABSTRACT_DECLARATOR(self, depth=0, tracer=None):
    rule = self.rule(194)
    tree = ParseTree( NonTerminal(194, self.getAtomString(194)), tracer )
    tree.list = False
    if self.sym == None:
      return tree
    if rule == 154:
      tree.astTransform = AstTransformNodeCreator('DirectAbstractDeclarator', {'sub': 1, 'abstract_declarator': 0})
      subtree = self.__GEN9(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN10(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN34(self, depth=0, tracer=None):
    rule = self.rule(195)
    tree = ParseTree( NonTerminal(195, self.getAtomString(195)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 205:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(92, tracer) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self._IDENTIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN34(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _VA_ARGS(self, depth=0, tracer=None):
    rule = self.rule(196)
    tree = ParseTree( NonTerminal(196, self.getAtomString(196)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 282:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(68, tracer) # comma_va_args
      tree.add(t)
      t = self.expect(45, tracer) # elipsis
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN22(self, depth=0, tracer=None):
    rule = self.rule(197)
    tree = ParseTree( NonTerminal(197, self.getAtomString(197)), tracer )
    tree.list = 'slist'
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 340:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STRUCT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN23(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [58, 2, 25]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STRUCT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN23(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _DECLARATOR_INITIALIZER(self, depth=0, tracer=None):
    rule = self.rule(198)
    tree = ParseTree( NonTerminal(198, self.getAtomString(198)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 401:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(78, tracer) # assign
      tree.add(t)
      subtree = self._INITIALIZER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _EXTERNAL_DECLARATION(self, depth=0, tracer=None):
    rule = self.rule(199)
    tree = ParseTree( NonTerminal(199, self.getAtomString(199)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 360:
      tree.astTransform = AstTransformNodeCreator('ExternalDeclaration', {'declarations': 2, 'declaration_specifiers': 1})
      t = self.expect(50, tracer) # external_declaration_hint
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
  def __GEN0(self, depth=0, tracer=None):
    rule = self.rule(200)
    tree = ParseTree( NonTerminal(200, self.getAtomString(200)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [-1]):
      return tree
    if self.sym == None:
      return tree
    if rule == 22:
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
  def _CONSTANT(self, depth=0, tracer=None):
    rule = self.rule(201)
    tree = ParseTree( NonTerminal(201, self.getAtomString(201)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 58:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(32, tracer) # decimal_floating_constant
      tree.add(t)
      return tree
    elif rule == 68:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(86, tracer) # character_constant
      tree.add(t)
      return tree
    elif rule == 144:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(22, tracer) # enumeration_constant
      tree.add(t)
      return tree
    elif rule == 193:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(106, tracer) # hexadecimal_floating_constant
      tree.add(t)
      return tree
    elif rule == 217:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(87, tracer) # integer_constant
      tree.add(t)
      return tree
    elif rule == 220:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(6, tracer) # floating_constant
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN32(self, depth=0, tracer=None):
    rule = self.rule(202)
    tree = ParseTree( NonTerminal(202, self.getAtomString(202)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [10]):
      return tree
    if self.sym == None:
      return tree
    if rule == 86:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._VA_ARGS(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _STRUCT_SPECIFIER(self, depth=0, tracer=None):
    rule = self.rule(203)
    tree = ParseTree( NonTerminal(203, self.getAtomString(203)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 61:
      tree.astTransform = AstTransformNodeCreator('Struct', {'definition': 1})
      t = self.expect(67, tracer) # struct
      tree.add(t)
      subtree = self._STRUCT_OR_UNION_SUB(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _FOR_INIT(self, depth=0, tracer=None):
    rule = self.rule(204)
    tree = ParseTree( NonTerminal(204, self.getAtomString(204)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [111]):
      return tree
    if self.sym == None:
      return tree
    if rule == 136:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 403:
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
    elif self.sym.getId() in [6, 86, 102, 57, 94, 88, 69, 95, 87, 58, 22, 91, 32, 59, 106, 25]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    return tree
  def _STRUCT_DECLARATOR_BODY(self, depth=0, tracer=None):
    rule = self.rule(205)
    tree = ParseTree( NonTerminal(205, self.getAtomString(205)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 237:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(35, tracer) # colon
      tree.add(t)
      subtree = self._DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _FOR_COND(self, depth=0, tracer=None):
    rule = self.rule(206)
    tree = ParseTree( NonTerminal(206, self.getAtomString(206)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 121:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(111, tracer) # semi
      tree.add(t)
      subtree = self._EXPRESSION_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _FOR_INCR(self, depth=0, tracer=None):
    rule = self.rule(207)
    tree = ParseTree( NonTerminal(207, self.getAtomString(207)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [10]):
      return tree
    if self.sym == None:
      return tree
    if rule == 242:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(111, tracer) # semi
      tree.add(t)
      subtree = self._EXPRESSION_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _UNION_SPECIFIER(self, depth=0, tracer=None):
    rule = self.rule(208)
    tree = ParseTree( NonTerminal(208, self.getAtomString(208)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 195:
      tree.astTransform = AstTransformNodeCreator('Union', {'definition': 1})
      t = self.expect(26, tracer) # union
      tree.add(t)
      subtree = self._STRUCT_OR_UNION_SUB(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _INITIALIZER(self, depth=0, tracer=None):
    rule = self.rule(209)
    tree = ParseTree( NonTerminal(209, self.getAtomString(209)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 56:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 212:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(61, tracer) # lbrace
      tree.add(t)
      subtree = self.__GEN15(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self._TRAILING_COMMA_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(82, tracer) # rbrace
      tree.add(t)
      return tree
    elif self.sym.getId() in [6, 86, 102, 57, 94, 88, 69, 95, 87, 58, 22, 91, 32, 59, 106, 25]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _PUNCTUATOR(self, depth=0, tracer=None):
    rule = self.rule(210)
    tree = ParseTree( NonTerminal(210, self.getAtomString(210)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 6:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(21, tracer) # addeq
      tree.add(t)
      return tree
    elif rule == 15:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(1, tracer) # tilde
      tree.add(t)
      return tree
    elif rule == 18:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(90, tracer) # lsquare
      tree.add(t)
      return tree
    elif rule == 28:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(35, tracer) # colon
      tree.add(t)
      return tree
    elif rule == 49:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(9, tracer) # exclamation_point
      tree.add(t)
      return tree
    elif rule == 51:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(7, tracer) # rshifteq
      tree.add(t)
      return tree
    elif rule == 64:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(54, tracer) # mod
      tree.add(t)
      return tree
    elif rule == 72:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(93, tracer) # bitxoreq
      tree.add(t)
      return tree
    elif rule == 81:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(92, tracer) # comma
      tree.add(t)
      return tree
    elif rule == 83:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(14, tracer) # subeq
      tree.add(t)
      return tree
    elif rule == 84:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(34, tracer) # gteq
      tree.add(t)
      return tree
    elif rule == 88:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(74, tracer) # bitor
      tree.add(t)
      return tree
    elif rule == 97:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(63, tracer) # lshifteq
      tree.add(t)
      return tree
    elif rule == 101:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(46, tracer) # rshift
      tree.add(t)
      return tree
    elif rule == 104:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(49, tracer) # pound
      tree.add(t)
      return tree
    elif rule == 110:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(109, tracer) # lteq
      tree.add(t)
      return tree
    elif rule == 119:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(75, tracer) # add
      tree.add(t)
      return tree
    elif rule == 122:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(97, tracer) # ampersand
      tree.add(t)
      return tree
    elif rule == 124:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(78, tracer) # assign
      tree.add(t)
      return tree
    elif rule == 164:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(27, tracer) # modeq
      tree.add(t)
      return tree
    elif rule == 168:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(10, tracer) # rparen
      tree.add(t)
      return tree
    elif rule == 216:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(112, tracer) # neq
      tree.add(t)
      return tree
    elif rule == 232:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(84, tracer) # bitoreq
      tree.add(t)
      return tree
    elif rule == 244:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(37, tracer) # gt
      tree.add(t)
      return tree
    elif rule == 249:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(100, tracer) # muleq
      tree.add(t)
      return tree
    elif rule == 260:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(111, tracer) # semi
      tree.add(t)
      return tree
    elif rule == 262:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(76, tracer) # bitandeq
      tree.add(t)
      return tree
    elif rule == 265:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(73, tracer) # rsquare
      tree.add(t)
      return tree
    elif rule == 268:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(4, tracer) # sub
      tree.add(t)
      return tree
    elif rule == 283:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(3, tracer) # arrow
      tree.add(t)
      return tree
    elif rule == 293:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(108, tracer) # bitxor
      tree.add(t)
      return tree
    elif rule == 295:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(48, tracer) # or
      tree.add(t)
      return tree
    elif rule == 301:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(82, tracer) # rbrace
      tree.add(t)
      return tree
    elif rule == 306:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(61, tracer) # lbrace
      tree.add(t)
      return tree
    elif rule == 323:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(56, tracer) # poundpound
      tree.add(t)
      return tree
    elif rule == 324:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(58, tracer) # lparen
      tree.add(t)
      return tree
    elif rule == 335:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(88, tracer) # incr
      tree.add(t)
      return tree
    elif rule == 344:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(77, tracer) # questionmark
      tree.add(t)
      return tree
    elif rule == 359:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(20, tracer) # and
      tree.add(t)
      return tree
    elif rule == 374:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(45, tracer) # elipsis
      tree.add(t)
      return tree
    elif rule == 384:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(11, tracer) # eq
      tree.add(t)
      return tree
    elif rule == 405:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(99, tracer) # dot
      tree.add(t)
      return tree
    elif rule == 406:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(85, tracer) # div
      tree.add(t)
      return tree
    elif rule == 410:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(29, tracer) # lt
      tree.add(t)
      return tree
    elif rule == 413:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(40, tracer) # lshift
      tree.add(t)
      return tree
    elif rule == 427:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(57, tracer) # decr
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _ENUM_SPECIFIER(self, depth=0, tracer=None):
    rule = self.rule(211)
    tree = ParseTree( NonTerminal(211, self.getAtomString(211)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 328:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(114, tracer) # enum
      tree.add(t)
      subtree = self._ENUM_SPECIFIER_SUB(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _DECLARATION_SPECIFIER(self, depth=0, tracer=None):
    rule = self.rule(212)
    tree = ParseTree( NonTerminal(212, self.getAtomString(212)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 225:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._TYPE_SPECIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 229:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STORAGE_CLASS_SPECIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 272:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._TYPE_QUALIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 279:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._FUNCTION_SPECIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _TRANSLATION_UNIT(self, depth=0, tracer=None):
    rule = self.rule(213)
    tree = ParseTree( NonTerminal(213, self.getAtomString(213)), tracer )
    tree.list = False
    if self.sym == None:
      return tree
    if rule == 402:
      tree.astTransform = AstTransformNodeCreator('TranslationUnit', {'external_declarations': 0})
      subtree = self.__GEN0(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN2(self, depth=0, tracer=None):
    rule = self.rule(215)
    tree = ParseTree( NonTerminal(215, self.getAtomString(215)), tracer )
    tree.list = 'mlist'
    if self.sym != None and (self.sym.getId() in [111, 96, 58, 62, 10, 92, 95, 90, 68, 2, 24, 25]):
      return tree
    if self.sym == None:
      return tree
    if rule == 143:
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
  def _TYPEDEF_NAME(self, depth=0, tracer=None):
    rule = self.rule(216)
    tree = ParseTree( NonTerminal(216, self.getAtomString(216)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 318:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(81, tracer) # typedef_identifier
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _LABELED_STATEMENT(self, depth=0, tracer=None):
    rule = self.rule(217)
    tree = ParseTree( NonTerminal(217, self.getAtomString(217)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 78:
      tree.astTransform = AstTransformNodeCreator('Label', {'name': 0, 'statement': 1})
      t = self.expect(107, tracer) # label_hint
      tree.add(t)
      t = self.expect(25, tracer) # identifier
      tree.add(t)
      t = self.expect(35, tracer) # colon
      tree.add(t)
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 133:
      tree.astTransform = AstTransformNodeCreator('Case', {'expr': 1, 'statement': 3})
      t = self.expect(23, tracer) # case
      tree.add(t)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(35, tracer) # colon
      tree.add(t)
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 383:
      tree.astTransform = AstTransformNodeCreator('DefaultCase', {'statement': 2})
      t = self.expect(8, tracer) # default
      tree.add(t)
      t = self.expect(35, tracer) # colon
      tree.add(t)
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _INITIALIZER_LIST_ITEM(self, depth=0, tracer=None):
    rule = self.rule(218)
    tree = ParseTree( NonTerminal(218, self.getAtomString(218)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 361:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN17(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self._INITIALIZER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 369:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(87, tracer) # integer_constant
      tree.add(t)
      return tree
    elif self.sym.getId() in [6, 86, 102, 57, 94, 88, 69, 95, 87, 58, 22, 91, 32, 59, 106, 25]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN17(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self._INITIALIZER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _STRUCT_DECLARATOR(self, depth=0, tracer=None):
    rule = self.rule(219)
    tree = ParseTree( NonTerminal(219, self.getAtomString(219)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 17:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STRUCT_DECLARATOR_BODY(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 325:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN24(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [58, 2, 25]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN24(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN24(self, depth=0, tracer=None):
    rule = self.rule(220)
    tree = ParseTree( NonTerminal(220, self.getAtomString(220)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [92, 111]):
      return tree
    if self.sym == None:
      return tree
    if rule == 181:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STRUCT_DECLARATOR_BODY(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _DESIGNATION(self, depth=0, tracer=None):
    rule = self.rule(221)
    tree = ParseTree( NonTerminal(221, self.getAtomString(221)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 334:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN18(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(78, tracer) # assign
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN16(self, depth=0, tracer=None):
    rule = self.rule(222)
    tree = ParseTree( NonTerminal(222, self.getAtomString(222)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in [17]):
      return tree
    if self.sym == None:
      return tree
    if rule == 152:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(92, tracer) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self._INITIALIZER_LIST_ITEM(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN16(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _STRUCT_OR_UNION_SUB(self, depth=0, tracer=None):
    rule = self.rule(223)
    tree = ParseTree( NonTerminal(223, self.getAtomString(223)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 0:
      tree.astTransform = AstTransformNodeCreator('StructOrUnion', {'body': 0})
      subtree = self._STRUCT_OR_UNION_BODY(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 210:
      tree.astTransform = AstTransformNodeCreator('StructOrUnion', {'body': 1, 'name': 0})
      t = self.expect(25, tracer) # identifier
      tree.add(t)
      subtree = self.__GEN19(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _EXTERNAL_DECLARATION_SUB(self, depth=0, tracer=None):
    rule = self.rule(224)
    tree = ParseTree( NonTerminal(224, self.getAtomString(224)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 134:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._EXTERNAL_FUNCTION(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 314:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN3(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(111, tracer) # semi
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _DIRECT_DECLARATOR_EXPR(self, depth=0, tracer=None):
    rule = self.rule(225)
    tree = ParseTree( NonTerminal(225, self.getAtomString(225)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 107:
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
    elif self.sym.getId() in [6, 86, 102, 57, 94, 88, 69, 95, 87, 58, 22, 91, 32, 59, 106, 25]:
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
  def _EXPRESSION_STATEMENT(self, depth=0, tracer=None):
    rule = self.rule(226)
    tree = ParseTree( NonTerminal(226, self.getAtomString(226)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 63:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._EXPRESSION_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(111, tracer) # semi
      tree.add(t)
      return tree
    elif self.sym.getId() in [6, 86, 102, 57, 94, 88, 69, 95, 87, 58, 22, 91, 32, 59, 106, 25]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._EXPRESSION_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(111, tracer) ) # semi
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _STATIC_OPT(self, depth=0, tracer=None):
    rule = self.rule(227)
    tree = ParseTree( NonTerminal(227, self.getAtomString(227)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [86, 91, 87, 57, 69, 94, 95, 88, 58, 22, 106, 102, 32, 6, 25, 59]):
      return tree
    if self.sym == None:
      return tree
    if rule == 120:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(41, tracer) # static
      tree.add(t)
      return tree
    return tree
  def _EXTERNAL_FUNCTION(self, depth=0, tracer=None):
    rule = self.rule(228)
    tree = ParseTree( NonTerminal(228, self.getAtomString(228)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 161:
      tree.astTransform = AstTransformNodeCreator('FunctionDefinition', {'body': 3, 'declaration_list': 2, 'signature': 1})
      t = self.expect(24, tracer) # function_definition_hint
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
  def _BLOCK_ITEM(self, depth=0, tracer=None):
    rule = self.rule(229)
    tree = ParseTree( NonTerminal(229, self.getAtomString(229)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 26:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DECLARATION(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 420:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [6, 86, 102, 57, 94, 88, 69, 95, 87, 58, 22, 91, 32, 59, 106, 25]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _SELECTION_STATEMENT(self, depth=0, tracer=None):
    rule = self.rule(230)
    tree = ParseTree( NonTerminal(230, self.getAtomString(230)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 80:
      tree.astTransform = AstTransformNodeCreator('Switch', {'expr': 2, 'statment': 4})
      t = self.expect(16, tracer) # switch
      tree.add(t)
      t = self.expect(58, tracer) # lparen
      tree.add(t)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(10, tracer) # rparen
      tree.add(t)
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 354:
      tree.astTransform = AstTransformNodeCreator('If', {'elseif': 6, 'statement': 4, 'condition': 2, 'else': 7})
      t = self.expect(104, tracer) # if
      tree.add(t)
      t = self.expect(58, tracer) # lparen
      tree.add(t)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(10, tracer) # rparen
      tree.add(t)
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(13, tracer) # endif
      tree.add(t)
      subtree = self.__GEN40(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN41(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN15(self, depth=0, tracer=None):
    rule = self.rule(231)
    tree = ParseTree( NonTerminal(231, self.getAtomString(231)), tracer )
    tree.list = 'slist'
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 190:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._INITIALIZER_LIST_ITEM(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN16(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [6, 86, 102, 57, 94, 88, 69, 95, 87, 58, 22, 91, 32, 59, 106, 25]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._INITIALIZER_LIST_ITEM(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN16(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _STRUCT_OR_UNION_BODY(self, depth=0, tracer=None):
    rule = self.rule(232)
    tree = ParseTree( NonTerminal(232, self.getAtomString(232)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 370:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(61, tracer) # lbrace
      tree.add(t)
      subtree = self.__GEN20(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(82, tracer) # rbrace
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN23(self, depth=0, tracer=None):
    rule = self.rule(233)
    tree = ParseTree( NonTerminal(233, self.getAtomString(233)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in [111]):
      return tree
    if self.sym == None:
      return tree
    if rule == 14:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(92, tracer) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self._STRUCT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN23(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN19(self, depth=0, tracer=None):
    rule = self.rule(234)
    tree = ParseTree( NonTerminal(234, self.getAtomString(234)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [55, 96, 51, 81, 62, 10, 72, 15, 19, 67, 70, 71, 36, 52, 26, 0, 43, 90, 53, 35, 98, 28, 30, 31, 114, 24, 92, 95, 58, 39, 103, 105, 68, 25, 2, 111, 113, 41]):
      return tree
    if self.sym == None:
      return tree
    if rule == 308:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STRUCT_OR_UNION_BODY(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _ITERATION_STATEMENT(self, depth=0, tracer=None):
    rule = self.rule(235)
    tree = ParseTree( NonTerminal(235, self.getAtomString(235)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 47:
      tree.astTransform = AstTransformNodeCreator('For', {'init': 2, 'cond': 3, 'incr': 4, 'statement': 6})
      t = self.expect(38, tracer) # for
      tree.add(t)
      t = self.expect(58, tracer) # lparen
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
      t = self.expect(10, tracer) # rparen
      tree.add(t)
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 258:
      tree.astTransform = AstTransformNodeCreator('While', {'expr': 2, 'statement': 4})
      t = self.expect(42, tracer) # while
      tree.add(t)
      t = self.expect(58, tracer) # lparen
      tree.add(t)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(10, tracer) # rparen
      tree.add(t)
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 408:
      tree.astTransform = AstTransformNodeCreator('DoWhile', {'expr': 4, 'statement': 1})
      t = self.expect(33, tracer) # do
      tree.add(t)
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(42, tracer) # while
      tree.add(t)
      t = self.expect(58, tracer) # lparen
      tree.add(t)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(10, tracer) # rparen
      tree.add(t)
      t = self.expect(111, tracer) # semi
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _ENUM_SPECIFIER_SUB(self, depth=0, tracer=None):
    rule = self.rule(236)
    tree = ParseTree( NonTerminal(236, self.getAtomString(236)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 128:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._IDENTIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN25(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 286:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._ENUM_SPECIFIER_BODY(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN3(self, depth=0, tracer=None):
    rule = self.rule(237)
    tree = ParseTree( NonTerminal(237, self.getAtomString(237)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in [111]):
      return tree
    if self.sym == None:
      return tree
    if rule == 173:
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
  def __GEN17(self, depth=0, tracer=None):
    rule = self.rule(238)
    tree = ParseTree( NonTerminal(238, self.getAtomString(238)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [86, 102, 57, 32, 69, 61, 94, 87, 88, 58, 22, 6, 91, 106, 25, 95, 59]):
      return tree
    if self.sym == None:
      return tree
    if rule == 171:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DESIGNATION(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN4(self, depth=0, tracer=None):
    rule = self.rule(239)
    tree = ParseTree( NonTerminal(239, self.getAtomString(239)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in [111]):
      return tree
    if self.sym == None:
      return tree
    if rule == 178:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(92, tracer) # comma
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
  def __GEN14(self, depth=0, tracer=None):
    rule = self.rule(240)
    tree = ParseTree( NonTerminal(240, self.getAtomString(240)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [92, 111]):
      return tree
    if self.sym == None:
      return tree
    if rule == 5:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DECLARATOR_INITIALIZER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _IDENTIFIER(self, depth=0, tracer=None):
    rule = self.rule(241)
    tree = ParseTree( NonTerminal(241, self.getAtomString(241)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 174:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(25, tracer) # identifier
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _ENUM_SPECIFIER_BODY(self, depth=0, tracer=None):
    rule = self.rule(242)
    tree = ParseTree( NonTerminal(242, self.getAtomString(242)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 228:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(61, tracer) # lbrace
      tree.add(t)
      subtree = self.__GEN26(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self._TRAILING_COMMA_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(82, tracer) # rbrace
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN25(self, depth=0, tracer=None):
    rule = self.rule(243)
    tree = ParseTree( NonTerminal(243, self.getAtomString(243)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [55, 96, 51, 81, 62, 10, 72, 15, 19, 67, 70, 71, 36, 52, 26, 0, 43, 90, 53, 35, 98, 28, 30, 31, 114, 24, 92, 95, 58, 39, 103, 105, 68, 25, 2, 111, 113, 41]):
      return tree
    if self.sym == None:
      return tree
    if rule == 426:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._ENUM_SPECIFIER_BODY(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _TOKEN(self, depth=0, tracer=None):
    rule = self.rule(244)
    tree = ParseTree( NonTerminal(244, self.getAtomString(244)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 13:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(102, tracer) # string_literal
      tree.add(t)
      return tree
    elif rule == 23:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._KEYWORD(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 277:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(25, tracer) # identifier
      tree.add(t)
      return tree
    elif rule == 281:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PUNCTUATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 311:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(18, tracer) # pp_number
      tree.add(t)
      return tree
    elif rule == 425:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._CONSTANT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _STRUCT_DECLARATION(self, depth=0, tracer=None):
    rule = self.rule(245)
    tree = ParseTree( NonTerminal(245, self.getAtomString(245)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 365:
      tree.astTransform = AstTransformNodeCreator('StructOrUnionDeclaration', {'specifier_qualifiers': 0, 'declarators': 1})
      subtree = self.__GEN21(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN22(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(111, tracer) # semi
      tree.add(t)
      return tree
    elif self.sym.getId() in [58, 2, 25]:
      tree.astTransform = AstTransformNodeCreator('StructOrUnionDeclaration', {'specifier_qualifiers': 0, 'declarators': 1})
      subtree = self.__GEN21(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN22(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(111, tracer) ) # semi
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _MISC(self, depth=0, tracer=None):
    rule = self.rule(246)
    tree = ParseTree( NonTerminal(246, self.getAtomString(246)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 70:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(13, tracer) # endif
      tree.add(t)
      return tree
    elif rule == 250:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(47, tracer) # universal_character_name
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  infixBp0 = {
    3: 15000,
    4: 11000,
    7: 1000,
    11: 8000,
    14: 1000,
    20: 4000,
    21: 1000,
    27: 1000,
    29: 9000,
    34: 9000,
    37: 9000,
    40: 10000,
    46: 10000,
    48: 3000,
    54: 12000,
    57: 15000,
    58: 15000,
    60: 1000,
    61: 14000,
    63: 1000,
    69: 5000,
    74: 7000,
    75: 11000,
    76: 1000,
    77: 2000,
    78: 1000,
    84: 1000,
    85: 12000,
    88: 15000,
    90: 15000,
    92: 16000,
    93: 1000,
    95: 12000,
    99: 15000,
    100: 1000,
    108: 6000,
    109: 9000,
    112: 8000,
  }
  prefixBp0 = {
    4: 13000,
    57: 13000,
    64: 13000,
    66: 13000,
    69: 13000,
    88: 13000,
    95: 13000,
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
    elif self.sym.getId() in [88]:
      tree.astTransform = AstTransformNodeCreator('PreIncr', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(88, tracer) )
      tree.add( self.__EXPR( self.prefixBp0[88] ) )
      tree.isPrefix = True
    elif self.sym.getId() in [102]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      return self.expect( 102, tracer )
    elif self.sym.getId() in [94]:
      tree.astTransform = AstTransformNodeCreator('TypeInitializion', {'type': 1, 'initializer': 4})
      tree.nudMorphemeCount = 3
      tree.add( self.expect(94, tracer) )
      tree.add( self._TYPE_NAME() )
      tree.add( self.expect(10, tracer) )
    elif self.sym.getId() in [58]:
      tree.astTransform = AstTransformSubstitution(2)
      tree.nudMorphemeCount = 3
      tree.add( self.expect(58, tracer) )
      tree.add( self.__EXPR() )
      tree.add( self.expect(10, tracer) )
    elif self.sym.getId() in [59]:
      tree.astTransform = AstTransformNodeCreator('SizeOf', {'var': 1})
      tree.nudMorphemeCount = 1
      return self.expect( 59, tracer )
    elif self.sym.getId() in [25]:
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      tree.nudMorphemeCount = 1
      return self.expect( 25, tracer )
    elif self.sym.getId() in [87, 106, 32, 22, 6, 86]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      tree.add( self._CONSTANT() )
    elif self.sym.getId() in [57]:
      tree.astTransform = AstTransformNodeCreator('PreDecr', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(57, tracer) )
      tree.add( self.__EXPR( self.prefixBp0[57] ) )
      tree.isPrefix = True
    elif self.sym.getId() in [25]:
      tree.astTransform = AstTransformNodeCreator('ArrayIndex', {'params': 2, 'name': 0})
      tree.nudMorphemeCount = 1
      return self.expect( 25, tracer )
    elif self.sym.getId() in [69]:
      tree.astTransform = AstTransformNodeCreator('AddressOf', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(69, tracer) )
      tree.add( self.__EXPR( self.prefixBp0[69] ) )
      tree.isPrefix = True
    elif self.sym.getId() in [95]:
      tree.astTransform = AstTransformNodeCreator('Dereference', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(95, tracer) )
      tree.add( self.__EXPR( self.prefixBp0[95] ) )
      tree.isPrefix = True
    elif self.sym.getId() in [25]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      return self.expect( 25, tracer )
    return tree
  def led0(self, left, tracer):
    tree = ParseTree( NonTerminal(214, '_expr') )
    if  self.sym.getId() == 100: # 'muleq'
      tree.astTransform = AstTransformNodeCreator('MultiplyAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(100, tracer) )
      modifier = 1
      tree.add( self.__EXPR( self.infixBp0[100] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 75: # 'add'
      tree.astTransform = AstTransformNodeCreator('Add', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(75, tracer) )
      modifier = 0
      tree.add( self.__EXPR( self.infixBp0[75] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 76: # 'bitandeq'
      tree.astTransform = AstTransformNodeCreator('ANDAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(76, tracer) )
      modifier = 1
      tree.add( self.__EXPR( self.infixBp0[76] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 4: # 'sub'
      tree.astTransform = AstTransformNodeCreator('Sub', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(4, tracer) )
      modifier = 0
      tree.add( self.__EXPR( self.infixBp0[4] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 61: # 'lbrace'
      tree.astTransform = AstTransformNodeCreator('TypeInitializion', {'type': 1, 'initializer': 4})
      if left:
        tree.add(left)
      tree.add( self.expect(61, tracer) )
      tree.add( self.__GEN15() )
      tree.add( self._TRAILING_COMMA_OPT() )
      tree.add( self.expect(82, tracer) )
    elif  self.sym.getId() == 90: # 'lsquare'
      tree.astTransform = AstTransformNodeCreator('ArrayIndex', {'params': 2, 'name': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(90, tracer) )
      tree.add( self.__GEN43() )
      tree.add( self.expect(73, tracer) )
    elif  self.sym.getId() == 109: # 'lteq'
      tree.astTransform = AstTransformNodeCreator('LessThanEq', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(109, tracer) )
      modifier = 0
      tree.add( self.__EXPR( self.infixBp0[109] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 37: # 'gt'
      tree.astTransform = AstTransformNodeCreator('GreaterThan', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(37, tracer) )
      modifier = 0
      tree.add( self.__EXPR( self.infixBp0[37] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 34: # 'gteq'
      tree.astTransform = AstTransformNodeCreator('GreaterThanEq', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(34, tracer) )
      modifier = 0
      tree.add( self.__EXPR( self.infixBp0[34] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 84: # 'bitoreq'
      tree.astTransform = AstTransformNodeCreator('ORAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(84, tracer) )
      modifier = 1
      tree.add( self.__EXPR( self.infixBp0[84] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 69: # 'bitand'
      tree.astTransform = AstTransformNodeCreator('BitAND', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(69, tracer) )
      modifier = 0
      tree.add( self.__EXPR( self.infixBp0[69] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 108: # 'bitxor'
      tree.astTransform = AstTransformNodeCreator('BitXOR', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(108, tracer) )
      modifier = 0
      tree.add( self.__EXPR( self.infixBp0[108] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 11: # 'eq'
      tree.astTransform = AstTransformNodeCreator('Equals', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(11, tracer) )
      modifier = 1
      tree.add( self.__EXPR( self.infixBp0[11] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 99: # 'dot'
      tree.astTransform = AstTransformNodeCreator('MemberSelect', {'member': 2, 'object': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(99, tracer) )
      modifier = 0
      tree.add( self.__EXPR( self.infixBp0[99] - modifier ) )
    elif  self.sym.getId() == 14: # 'subeq'
      tree.astTransform = AstTransformNodeCreator('SubtractAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(14, tracer) )
      modifier = 1
      tree.add( self.__EXPR( self.infixBp0[14] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 7: # 'rshifteq'
      tree.astTransform = AstTransformNodeCreator('RightShiftAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(7, tracer) )
      modifier = 1
      tree.add( self.__EXPR( self.infixBp0[7] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 57: # 'decr'
      tree.astTransform = AstTransformNodeCreator('PostDecr', {'var': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(57, tracer) )
    elif  self.sym.getId() == 3: # 'arrow'
      tree.astTransform = AstTransformNodeCreator('DerefMemberSelect', {'member': 2, 'object': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(3, tracer) )
      modifier = 0
      tree.add( self.__EXPR( self.infixBp0[3] - modifier ) )
    elif  self.sym.getId() == 77: # 'questionmark'
      tree.astTransform = AstTransformNodeCreator('TernaryOperator', {'true': 2, 'false': 4, 'cond': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(77, tracer) )
      modifier = 1
      tree.add( self.__EXPR( self.infixBp0[77] - modifier ) )
      tree.add( self.expect(35, tracer) )
      modifier = 1
      tree.add( self.__EXPR( self.infixBp0[77] - modifier ) )
    elif  self.sym.getId() == 88: # 'incr'
      tree.astTransform = AstTransformNodeCreator('PostIncr', {'var': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(88, tracer) )
    elif  self.sym.getId() == 74: # 'bitor'
      tree.astTransform = AstTransformNodeCreator('BitOR', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(74, tracer) )
      modifier = 0
      tree.add( self.__EXPR( self.infixBp0[74] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 46: # 'rshift'
      tree.astTransform = AstTransformNodeCreator('RightShift', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(46, tracer) )
      modifier = 0
      tree.add( self.__EXPR( self.infixBp0[46] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 21: # 'addeq'
      tree.astTransform = AstTransformNodeCreator('AddAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(21, tracer) )
      modifier = 1
      tree.add( self.__EXPR( self.infixBp0[21] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 27: # 'modeq'
      tree.astTransform = AstTransformNodeCreator('ModAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(27, tracer) )
      modifier = 1
      tree.add( self.__EXPR( self.infixBp0[27] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 85: # 'div'
      tree.astTransform = AstTransformNodeCreator('Div', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(85, tracer) )
      modifier = 0
      tree.add( self.__EXPR( self.infixBp0[85] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 78: # 'assign'
      tree.astTransform = AstTransformNodeCreator('Assign', {'var': 0, 'value': 2})
      if left:
        tree.add(left)
      tree.add( self.expect(78, tracer) )
      modifier = 1
      tree.add( self.__EXPR( self.infixBp0[78] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 92: # 'comma'
      tree.astTransform = AstTransformNodeCreator('Comma', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(92, tracer) )
      modifier = 0
      tree.add( self.__EXPR( self.infixBp0[92] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 93: # 'bitxoreq'
      tree.astTransform = AstTransformNodeCreator('XORAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(93, tracer) )
      modifier = 1
      tree.add( self.__EXPR( self.infixBp0[93] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 65: # 'sizeof_separator'
      tree.astTransform = AstTransformNodeCreator('SizeOf', {'var': 1})
      if left:
        tree.add(left)
      tree.add( self.expect(65, tracer) )
      tree.add( self._SIZEOF_BODY() )
    elif  self.sym.getId() == 63: # 'lshifteq'
      tree.astTransform = AstTransformNodeCreator('LeftShiftAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(63, tracer) )
      modifier = 1
      tree.add( self.__EXPR( self.infixBp0[63] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 29: # 'lt'
      tree.astTransform = AstTransformNodeCreator('LessThan', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(29, tracer) )
      modifier = 0
      tree.add( self.__EXPR( self.infixBp0[29] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 40: # 'lshift'
      tree.astTransform = AstTransformNodeCreator('LeftShift', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(40, tracer) )
      modifier = 0
      tree.add( self.__EXPR( self.infixBp0[40] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 60: # 'diveq'
      tree.astTransform = AstTransformNodeCreator('DivideAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(60, tracer) )
      modifier = 1
      tree.add( self.__EXPR( self.infixBp0[60] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 54: # 'mod'
      tree.astTransform = AstTransformNodeCreator('Mod', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(54, tracer) )
      modifier = 0
      tree.add( self.__EXPR( self.infixBp0[54] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 58: # 'lparen'
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(58, tracer) )
      tree.add( self.__GEN43() )
      tree.add( self.expect(10, tracer) )
    elif  self.sym.getId() == 95: # 'asterisk'
      tree.astTransform = AstTransformNodeCreator('Mul', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(95, tracer) )
      modifier = 0
      tree.add( self.__EXPR( self.infixBp0[95] - modifier ) )
      tree.isInfix = True
    return tree
  infixBp1 = {
    3: 15000,
    4: 11000,
    7: 1000,
    11: 8000,
    14: 1000,
    20: 4000,
    21: 1000,
    27: 1000,
    29: 9000,
    34: 9000,
    37: 9000,
    40: 10000,
    46: 10000,
    48: 3000,
    54: 12000,
    57: 15000,
    58: 15000,
    60: 1000,
    61: 14000,
    63: 1000,
    69: 5000,
    74: 7000,
    75: 11000,
    76: 1000,
    77: 2000,
    78: 1000,
    84: 1000,
    85: 12000,
    88: 15000,
    90: 15000,
    93: 1000,
    95: 12000,
    99: 15000,
    100: 1000,
    108: 6000,
    109: 9000,
    112: 8000,
  }
  prefixBp1 = {
    4: 13000,
    57: 13000,
    64: 13000,
    66: 13000,
    69: 13000,
    88: 13000,
    95: 13000,
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
    tree = ParseTree( NonTerminal(133, '_expr_sans_comma') )
    if not self.sym:
      return tree
    if self.sym.getId() in [95]:
      tree.astTransform = AstTransformNodeCreator('Dereference', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(95, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.prefixBp1[95] ) )
      tree.isPrefix = True
    elif self.sym.getId() in [102]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      return self.expect( 102, tracer )
    elif self.sym.getId() in [88]:
      tree.astTransform = AstTransformNodeCreator('PreIncr', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(88, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.prefixBp1[88] ) )
      tree.isPrefix = True
    elif self.sym.getId() in [25]:
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      tree.nudMorphemeCount = 1
      return self.expect( 25, tracer )
    elif self.sym.getId() in [57]:
      tree.astTransform = AstTransformNodeCreator('PreDecr', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(57, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.prefixBp1[57] ) )
      tree.isPrefix = True
    elif self.sym.getId() in [25]:
      tree.astTransform = AstTransformNodeCreator('ArrayIndex', {'params': 2, 'name': 0})
      tree.nudMorphemeCount = 1
      return self.expect( 25, tracer )
    elif self.sym.getId() in [94]:
      tree.astTransform = AstTransformNodeCreator('TypeInitializion', {'type': 1, 'initializer': 4})
      tree.nudMorphemeCount = 3
      tree.add( self.expect(94, tracer) )
      tree.add( self._TYPE_NAME() )
      tree.add( self.expect(10, tracer) )
    elif self.sym.getId() in [59]:
      tree.astTransform = AstTransformNodeCreator('SizeOf', {'var': 1})
      tree.nudMorphemeCount = 1
      return self.expect( 59, tracer )
    elif self.sym.getId() in [87, 106, 32, 22, 6, 86]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      tree.add( self._CONSTANT() )
    elif self.sym.getId() in [69]:
      tree.astTransform = AstTransformNodeCreator('AddressOf', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(69, tracer) )
      tree.add( self.__EXPR_SANS_COMMA( self.prefixBp1[69] ) )
      tree.isPrefix = True
    elif self.sym.getId() in [25]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      return self.expect( 25, tracer )
    elif self.sym.getId() in [58]:
      tree.astTransform = AstTransformSubstitution(2)
      tree.nudMorphemeCount = 3
      tree.add( self.expect(58, tracer) )
      tree.add( self.__EXPR_SANS_COMMA() )
      tree.add( self.expect(10, tracer) )
    return tree
  def led1(self, left, tracer):
    tree = ParseTree( NonTerminal(133, '_expr_sans_comma') )
    if  self.sym.getId() == 74: # 'bitor'
      tree.astTransform = AstTransformNodeCreator('BitOR', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(74, tracer) )
      modifier = 0
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[74] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 7: # 'rshifteq'
      tree.astTransform = AstTransformNodeCreator('RightShiftAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(7, tracer) )
      modifier = 1
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[7] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 11: # 'eq'
      tree.astTransform = AstTransformNodeCreator('Equals', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(11, tracer) )
      modifier = 1
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[11] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 109: # 'lteq'
      tree.astTransform = AstTransformNodeCreator('LessThanEq', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(109, tracer) )
      modifier = 0
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[109] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 76: # 'bitandeq'
      tree.astTransform = AstTransformNodeCreator('ANDAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(76, tracer) )
      modifier = 1
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[76] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 90: # 'lsquare'
      tree.astTransform = AstTransformNodeCreator('ArrayIndex', {'params': 2, 'name': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(90, tracer) )
      tree.add( self.__GEN43() )
      tree.add( self.expect(73, tracer) )
    elif  self.sym.getId() == 108: # 'bitxor'
      tree.astTransform = AstTransformNodeCreator('BitXOR', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(108, tracer) )
      modifier = 0
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[108] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 61: # 'lbrace'
      tree.astTransform = AstTransformNodeCreator('TypeInitializion', {'type': 1, 'initializer': 4})
      if left:
        tree.add(left)
      tree.add( self.expect(61, tracer) )
      tree.add( self.__GEN15() )
      tree.add( self._TRAILING_COMMA_OPT() )
      tree.add( self.expect(82, tracer) )
    elif  self.sym.getId() == 78: # 'assign'
      tree.astTransform = AstTransformNodeCreator('Assign', {'var': 0, 'value': 2})
      if left:
        tree.add(left)
      tree.add( self.expect(78, tracer) )
      modifier = 1
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[78] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 100: # 'muleq'
      tree.astTransform = AstTransformNodeCreator('MultiplyAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(100, tracer) )
      modifier = 1
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[100] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 60: # 'diveq'
      tree.astTransform = AstTransformNodeCreator('DivideAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(60, tracer) )
      modifier = 1
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[60] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 34: # 'gteq'
      tree.astTransform = AstTransformNodeCreator('GreaterThanEq', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(34, tracer) )
      modifier = 0
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[34] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 75: # 'add'
      tree.astTransform = AstTransformNodeCreator('Add', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(75, tracer) )
      modifier = 0
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[75] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 21: # 'addeq'
      tree.astTransform = AstTransformNodeCreator('AddAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(21, tracer) )
      modifier = 1
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[21] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 99: # 'dot'
      tree.astTransform = AstTransformNodeCreator('MemberSelect', {'member': 2, 'object': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(99, tracer) )
      modifier = 0
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[99] - modifier ) )
    elif  self.sym.getId() == 40: # 'lshift'
      tree.astTransform = AstTransformNodeCreator('LeftShift', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(40, tracer) )
      modifier = 0
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[40] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 95: # 'asterisk'
      tree.astTransform = AstTransformNodeCreator('Mul', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(95, tracer) )
      modifier = 0
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[95] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 4: # 'sub'
      tree.astTransform = AstTransformNodeCreator('Sub', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(4, tracer) )
      modifier = 0
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[4] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 84: # 'bitoreq'
      tree.astTransform = AstTransformNodeCreator('ORAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(84, tracer) )
      modifier = 1
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[84] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 14: # 'subeq'
      tree.astTransform = AstTransformNodeCreator('SubtractAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(14, tracer) )
      modifier = 1
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[14] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 3: # 'arrow'
      tree.astTransform = AstTransformNodeCreator('DerefMemberSelect', {'member': 2, 'object': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(3, tracer) )
      modifier = 0
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[3] - modifier ) )
    elif  self.sym.getId() == 46: # 'rshift'
      tree.astTransform = AstTransformNodeCreator('RightShift', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(46, tracer) )
      modifier = 0
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[46] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 85: # 'div'
      tree.astTransform = AstTransformNodeCreator('Div', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(85, tracer) )
      modifier = 0
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[85] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 93: # 'bitxoreq'
      tree.astTransform = AstTransformNodeCreator('XORAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(93, tracer) )
      modifier = 1
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[93] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 29: # 'lt'
      tree.astTransform = AstTransformNodeCreator('LessThan', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(29, tracer) )
      modifier = 0
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[29] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 58: # 'lparen'
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(58, tracer) )
      tree.add( self.__GEN43() )
      tree.add( self.expect(10, tracer) )
    elif  self.sym.getId() == 57: # 'decr'
      tree.astTransform = AstTransformNodeCreator('PostDecr', {'var': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(57, tracer) )
    elif  self.sym.getId() == 63: # 'lshifteq'
      tree.astTransform = AstTransformNodeCreator('LeftShiftAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(63, tracer) )
      modifier = 1
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[63] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 69: # 'bitand'
      tree.astTransform = AstTransformNodeCreator('BitAND', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(69, tracer) )
      modifier = 0
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[69] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 54: # 'mod'
      tree.astTransform = AstTransformNodeCreator('Mod', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(54, tracer) )
      modifier = 0
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[54] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 77: # 'questionmark'
      tree.astTransform = AstTransformNodeCreator('TernaryOperator', {'true': 2, 'false': 4, 'cond': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(77, tracer) )
      modifier = 1
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[77] - modifier ) )
      tree.add( self.expect(35, tracer) )
      modifier = 1
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[77] - modifier ) )
    elif  self.sym.getId() == 88: # 'incr'
      tree.astTransform = AstTransformNodeCreator('PostIncr', {'var': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(88, tracer) )
    elif  self.sym.getId() == 27: # 'modeq'
      tree.astTransform = AstTransformNodeCreator('ModAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(27, tracer) )
      modifier = 1
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[27] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 37: # 'gt'
      tree.astTransform = AstTransformNodeCreator('GreaterThan', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(37, tracer) )
      modifier = 0
      tree.add( self.__EXPR_SANS_COMMA( self.infixBp1[37] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 65: # 'sizeof_separator'
      tree.astTransform = AstTransformNodeCreator('SizeOf', {'var': 1})
      if left:
        tree.add(left)
      tree.add( self.expect(65, tracer) )
      tree.add( self._SIZEOF_BODY() )
    return tree
  infixBp2 = {
    58: 1000,
    90: 1000,
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
    tree = ParseTree( NonTerminal(122, '_direct_declarator') )
    if not self.sym:
      return tree
    if self.sym.getId() in [25]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      return self.expect( 25, tracer )
    elif self.sym.getId() in [58]:
      tree.astTransform = AstTransformSubstitution(1)
      tree.nudMorphemeCount = 3
      tree.add( self.expect(58, tracer) )
      tree.add( self._DECLARATOR() )
      tree.add( self.expect(10, tracer) )
    return tree
  def led2(self, left, tracer):
    tree = ParseTree( NonTerminal(122, '_direct_declarator') )
    if  self.sym.getId() == 58: # 'lparen'
      tree.astTransform = AstTransformNodeCreator('FunctionSignature', {'params': 2, 'declarator': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(58, tracer) )
      tree.add( self._DIRECT_DECLARATOR_PARAMETER_LIST() )
      tree.add( self.expect(10, tracer) )
    elif  self.sym.getId() == 90: # 'lsquare'
      tree.astTransform = AstTransformNodeCreator('Array', {'name': 0, 'size': 2})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(90, tracer) )
      tree.add( self._DIRECT_DECLARATOR_EXPR() )
      tree.add( self.expect(73, tracer) )
    return tree
