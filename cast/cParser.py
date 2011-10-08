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
  TERMINAL__BOOL = 124
  TERMINAL__COMPLEX = 129
  TERMINAL__IMAGINARY = 34
  TERMINAL_ADD = 67
  TERMINAL_ADDEQ = 7
  TERMINAL_AMPERSAND = 19
  TERMINAL_AND = 99
  TERMINAL_ARROW = 25
  TERMINAL_ASSIGN = 18
  TERMINAL_ASTERISK = 2
  TERMINAL_AUTO = 70
  TERMINAL_BITAND = 92
  TERMINAL_BITANDEQ = 122
  TERMINAL_BITNOT = 96
  TERMINAL_BITOR = 100
  TERMINAL_BITOREQ = 114
  TERMINAL_BITXOR = 68
  TERMINAL_BITXOREQ = 60
  TERMINAL_BOOL = 9
  TERMINAL_BREAK = 20
  TERMINAL_CASE = 104
  TERMINAL_CHAR = 30
  TERMINAL_CHARACTER_CONSTANT = 49
  TERMINAL_COLON = 82
  TERMINAL_COMMA = 29
  TERMINAL_COMMA_VA_ARGS = 1
  TERMINAL_COMPLEX = 11
  TERMINAL_CONST = 130
  TERMINAL_CONTINUE = 16
  TERMINAL_CSOURCE = 13
  TERMINAL_DECIMAL_FLOATING_CONSTANT = 64
  TERMINAL_DECLARATOR_HINT = 91
  TERMINAL_DECR = 87
  TERMINAL_DEFAULT = 32
  TERMINAL_DEFINE = 54
  TERMINAL_DEFINE_FUNCTION = 62
  TERMINAL_DEFINED = 15
  TERMINAL_DEFINED_SEPARATOR = 105
  TERMINAL_DIV = 75
  TERMINAL_DIVEQ = 94
  TERMINAL_DO = 37
  TERMINAL_DOT = 31
  TERMINAL_DOUBLE = 106
  TERMINAL_ELIF = 66
  TERMINAL_ELIPSIS = 73
  TERMINAL_ELSE = 90
  TERMINAL_ELSE_IF = 85
  TERMINAL_ENDIF = 47
  TERMINAL_ENUM = 28
  TERMINAL_ENUMERATION_CONSTANT = 83
  TERMINAL_EQ = 109
  TERMINAL_EQUALS = 76
  TERMINAL_ERROR = 113
  TERMINAL_EXCLAMATION_POINT = 5
  TERMINAL_EXTERN = 86
  TERMINAL_FLOAT = 101
  TERMINAL_FLOATING_CONSTANT = 8
  TERMINAL_FOR = 117
  TERMINAL_FUNCTION_HINT = 80
  TERMINAL_GOTO = 12
  TERMINAL_GT = 55
  TERMINAL_GTEQ = 79
  TERMINAL_HEADER_GLOBAL = 110
  TERMINAL_HEADER_LOCAL = 6
  TERMINAL_HEADER_NAME = 26
  TERMINAL_HEXADECIMAL_FLOATING_CONSTANT = 84
  TERMINAL_IDENTIFIER = 121
  TERMINAL_IF = 52
  TERMINAL_IFDEF = 120
  TERMINAL_IFNDEF = 108
  TERMINAL_IMAGINARY = 27
  TERMINAL_INCLUDE = 111
  TERMINAL_INCR = 63
  TERMINAL_INLINE = 123
  TERMINAL_INT = 93
  TERMINAL_INTEGER_CONSTANT = 115
  TERMINAL_LBRACE = 33
  TERMINAL_LINE = 58
  TERMINAL_LONG = 97
  TERMINAL_LPAREN = 46
  TERMINAL_LPAREN_CAST = 35
  TERMINAL_LSHIFT = 61
  TERMINAL_LSHIFTEQ = 128
  TERMINAL_LSQUARE = 40
  TERMINAL_LT = 126
  TERMINAL_LTEQ = 116
  TERMINAL_MOD = 69
  TERMINAL_MODEQ = 10
  TERMINAL_MUL = 72
  TERMINAL_MULEQ = 14
  TERMINAL_NEQ = 103
  TERMINAL_NOT = 24
  TERMINAL_NUMBER = 98
  TERMINAL_OR = 95
  TERMINAL_POUND = 50
  TERMINAL_POUNDPOUND = 22
  TERMINAL_PP_NUMBER = 44
  TERMINAL_PRAGMA = 107
  TERMINAL_QUESTIONMARK = 88
  TERMINAL_RBRACE = 36
  TERMINAL_REGISTER = 74
  TERMINAL_RESTRICT = 81
  TERMINAL_RETURN = 23
  TERMINAL_RPAREN = 51
  TERMINAL_RSHIFT = 65
  TERMINAL_RSHIFTEQ = 0
  TERMINAL_RSQUARE = 48
  TERMINAL_SEMI = 77
  TERMINAL_SEPARATOR = 21
  TERMINAL_SHORT = 89
  TERMINAL_SIGNED = 112
  TERMINAL_SIZEOF = 3
  TERMINAL_SIZEOF_SEPARATOR = 42
  TERMINAL_STATIC = 57
  TERMINAL_STRING_LITERAL = 53
  TERMINAL_STRUCT = 38
  TERMINAL_SUB = 45
  TERMINAL_SUBEQ = 4
  TERMINAL_SWITCH = 127
  TERMINAL_TILDE = 59
  TERMINAL_TRAILING_COMMA = 102
  TERMINAL_TYPEDEF = 56
  TERMINAL_TYPEDEF_IDENTIFIER = 71
  TERMINAL_UNDEF = 125
  TERMINAL_UNION = 41
  TERMINAL_UNIVERSAL_CHARACTER_NAME = 43
  TERMINAL_UNSIGNED = 118
  TERMINAL_VOID = 78
  TERMINAL_VOLATILE = 39
  TERMINAL_WARNING = 119
  TERMINAL_WHILE = 17
  terminal_str = {
    124: '_bool',
    129: '_complex',
    34: '_imaginary',
    67: 'add',
    7: 'addeq',
    19: 'ampersand',
    99: 'and',
    25: 'arrow',
    18: 'assign',
    2: 'asterisk',
    70: 'auto',
    92: 'bitand',
    122: 'bitandeq',
    96: 'bitnot',
    100: 'bitor',
    114: 'bitoreq',
    68: 'bitxor',
    60: 'bitxoreq',
    9: 'bool',
    20: 'break',
    104: 'case',
    30: 'char',
    49: 'character_constant',
    82: 'colon',
    29: 'comma',
    1: 'comma_va_args',
    11: 'complex',
    130: 'const',
    16: 'continue',
    13: 'csource',
    64: 'decimal_floating_constant',
    91: 'declarator_hint',
    87: 'decr',
    32: 'default',
    54: 'define',
    62: 'define_function',
    15: 'defined',
    105: 'defined_separator',
    75: 'div',
    94: 'diveq',
    37: 'do',
    31: 'dot',
    106: 'double',
    66: 'elif',
    73: 'elipsis',
    90: 'else',
    85: 'else_if',
    47: 'endif',
    28: 'enum',
    83: 'enumeration_constant',
    109: 'eq',
    76: 'equals',
    113: 'error',
    5: 'exclamation_point',
    86: 'extern',
    101: 'float',
    8: 'floating_constant',
    117: 'for',
    80: 'function_hint',
    12: 'goto',
    55: 'gt',
    79: 'gteq',
    110: 'header_global',
    6: 'header_local',
    26: 'header_name',
    84: 'hexadecimal_floating_constant',
    121: 'identifier',
    52: 'if',
    120: 'ifdef',
    108: 'ifndef',
    27: 'imaginary',
    111: 'include',
    63: 'incr',
    123: 'inline',
    93: 'int',
    115: 'integer_constant',
    33: 'lbrace',
    58: 'line',
    97: 'long',
    46: 'lparen',
    35: 'lparen_cast',
    61: 'lshift',
    128: 'lshifteq',
    40: 'lsquare',
    126: 'lt',
    116: 'lteq',
    69: 'mod',
    10: 'modeq',
    72: 'mul',
    14: 'muleq',
    103: 'neq',
    24: 'not',
    98: 'number',
    95: 'or',
    50: 'pound',
    22: 'poundpound',
    44: 'pp_number',
    107: 'pragma',
    88: 'questionmark',
    36: 'rbrace',
    74: 'register',
    81: 'restrict',
    23: 'return',
    51: 'rparen',
    65: 'rshift',
    0: 'rshifteq',
    48: 'rsquare',
    77: 'semi',
    21: 'separator',
    89: 'short',
    112: 'signed',
    3: 'sizeof',
    42: 'sizeof_separator',
    57: 'static',
    53: 'string_literal',
    38: 'struct',
    45: 'sub',
    4: 'subeq',
    127: 'switch',
    59: 'tilde',
    102: 'trailing_comma',
    56: 'typedef',
    71: 'typedef_identifier',
    125: 'undef',
    41: 'union',
    43: 'universal_character_name',
    118: 'unsigned',
    78: 'void',
    39: 'volatile',
    119: 'warning',
    17: 'while',
  }
  nonterminal_str = {
    186: '_direct_abstract_declarator',
    254: '_direct_declarator',
    194: '_expr',
    155: '_gen0',
    176: '_gen1',
    168: '_gen10',
    180: '_gen11',
    257: '_gen12',
    222: '_gen13',
    200: '_gen14',
    147: '_gen15',
    153: '_gen16',
    230: '_gen17',
    154: '_gen18',
    187: '_gen19',
    203: '_gen2',
    134: '_gen20',
    262: '_gen21',
    167: '_gen22',
    181: '_gen23',
    182: '_gen24',
    232: '_gen25',
    196: '_gen26',
    225: '_gen27',
    226: '_gen28',
    255: '_gen29',
    205: '_gen3',
    189: '_gen30',
    261: '_gen31',
    236: '_gen4',
    207: '_gen5',
    233: '_gen6',
    253: '_gen7',
    249: '_gen8',
    266: '_gen9',
    190: 'abstract_declarator',
    260: 'block_item',
    256: 'block_item_list_opt',
    152: 'compound_statement',
    156: 'constant',
    141: 'control_line',
    188: 'declaration',
    160: 'declaration_list_opt',
    263: 'declaration_specifier',
    150: 'declarator',
    195: 'declarator_initializer',
    202: 'define_func_param',
    158: 'define_line',
    223: 'defined_identifier',
    245: 'designation',
    246: 'designation_opt',
    250: 'designator',
    243: 'direct_abstract_declarator_expr',
    163: 'direct_abstract_declarator_opt',
    132: 'direct_declarator_expr',
    267: 'direct_declarator_modifier',
    258: 'direct_declarator_modifier_list_opt',
    240: 'direct_declarator_parameter_list',
    212: 'direct_declarator_size',
    142: 'elipsis_opt',
    216: 'else_if_statement',
    210: 'else_if_statement_opt',
    185: 'else_part',
    201: 'else_statement',
    211: 'else_statement_opt',
    175: 'elseif_part',
    139: 'enum_specifier',
    166: 'enum_specifier_body',
    161: 'enum_specifier_sub',
    197: 'enumeration_constant',
    179: 'enumerator',
    198: 'enumerator_assignment',
    234: 'error_line',
    192: 'expression_opt',
    227: 'expression_statement',
    251: 'external_declaration',
    136: 'external_declaration_sub',
    259: 'for_cond',
    218: 'for_incr',
    206: 'for_init',
    248: 'function_definition',
    131: 'function_specifier',
    151: 'identifier',
    174: 'if_part',
    208: 'if_section',
    217: 'include_line',
    178: 'include_type',
    191: 'init_declarator',
    149: 'init_declarator_list_opt',
    209: 'initializer',
    220: 'initializer_list_item',
    235: 'iteration_statement',
    239: 'jump_statement',
    252: 'keyword',
    215: 'labeled_statement',
    247: 'line_line',
    221: 'parameter_declaration',
    144: 'parameter_declaration_sub',
    148: 'parameter_declaration_sub_sub',
    213: 'parameter_type_list',
    219: 'parameter_type_list_opt',
    162: 'pointer',
    172: 'pointer_opt',
    169: 'pointer_sub',
    135: 'pp',
    268: 'pp_directive',
    140: 'pp_file',
    165: 'pp_nodes',
    145: 'pp_nodes_list',
    157: 'pp_tokens',
    228: 'pragma_line',
    224: 'punctuator',
    146: 'replacement_list',
    229: 'selection_statement',
    231: 'sizeof_body',
    199: 'specifier_qualifier_list',
    184: 'statement',
    138: 'static_opt',
    170: 'storage_class_specifier',
    164: 'struct_declaration',
    183: 'struct_declarator',
    241: 'struct_declarator_body',
    242: 'struct_or_union',
    143: 'struct_or_union_body',
    133: 'struct_or_union_specifier',
    137: 'struct_or_union_sub',
    159: 'terminals',
    193: 'token',
    214: 'trailing_comma_opt',
    244: 'translation_unit',
    171: 'type_name',
    177: 'type_qualifier',
    264: 'type_qualifier_list_opt',
    173: 'type_specifier',
    204: 'typedef_name',
    265: 'undef_line',
    237: 'va_args',
    238: 'warning_line',
  }
  str_terminal = {
    '_bool': 124,
    '_complex': 129,
    '_imaginary': 34,
    'add': 67,
    'addeq': 7,
    'ampersand': 19,
    'and': 99,
    'arrow': 25,
    'assign': 18,
    'asterisk': 2,
    'auto': 70,
    'bitand': 92,
    'bitandeq': 122,
    'bitnot': 96,
    'bitor': 100,
    'bitoreq': 114,
    'bitxor': 68,
    'bitxoreq': 60,
    'bool': 9,
    'break': 20,
    'case': 104,
    'char': 30,
    'character_constant': 49,
    'colon': 82,
    'comma': 29,
    'comma_va_args': 1,
    'complex': 11,
    'const': 130,
    'continue': 16,
    'csource': 13,
    'decimal_floating_constant': 64,
    'declarator_hint': 91,
    'decr': 87,
    'default': 32,
    'define': 54,
    'define_function': 62,
    'defined': 15,
    'defined_separator': 105,
    'div': 75,
    'diveq': 94,
    'do': 37,
    'dot': 31,
    'double': 106,
    'elif': 66,
    'elipsis': 73,
    'else': 90,
    'else_if': 85,
    'endif': 47,
    'enum': 28,
    'enumeration_constant': 83,
    'eq': 109,
    'equals': 76,
    'error': 113,
    'exclamation_point': 5,
    'extern': 86,
    'float': 101,
    'floating_constant': 8,
    'for': 117,
    'function_hint': 80,
    'goto': 12,
    'gt': 55,
    'gteq': 79,
    'header_global': 110,
    'header_local': 6,
    'header_name': 26,
    'hexadecimal_floating_constant': 84,
    'identifier': 121,
    'if': 52,
    'ifdef': 120,
    'ifndef': 108,
    'imaginary': 27,
    'include': 111,
    'incr': 63,
    'inline': 123,
    'int': 93,
    'integer_constant': 115,
    'lbrace': 33,
    'line': 58,
    'long': 97,
    'lparen': 46,
    'lparen_cast': 35,
    'lshift': 61,
    'lshifteq': 128,
    'lsquare': 40,
    'lt': 126,
    'lteq': 116,
    'mod': 69,
    'modeq': 10,
    'mul': 72,
    'muleq': 14,
    'neq': 103,
    'not': 24,
    'number': 98,
    'or': 95,
    'pound': 50,
    'poundpound': 22,
    'pp_number': 44,
    'pragma': 107,
    'questionmark': 88,
    'rbrace': 36,
    'register': 74,
    'restrict': 81,
    'return': 23,
    'rparen': 51,
    'rshift': 65,
    'rshifteq': 0,
    'rsquare': 48,
    'semi': 77,
    'separator': 21,
    'short': 89,
    'signed': 112,
    'sizeof': 3,
    'sizeof_separator': 42,
    'static': 57,
    'string_literal': 53,
    'struct': 38,
    'sub': 45,
    'subeq': 4,
    'switch': 127,
    'tilde': 59,
    'trailing_comma': 102,
    'typedef': 56,
    'typedef_identifier': 71,
    'undef': 125,
    'union': 41,
    'universal_character_name': 43,
    'unsigned': 118,
    'void': 78,
    'volatile': 39,
    'warning': 119,
    'while': 17,
  }
  str_nonterminal = {
    '_direct_abstract_declarator': 186,
    '_direct_declarator': 254,
    '_expr': 194,
    '_gen0': 155,
    '_gen1': 176,
    '_gen10': 168,
    '_gen11': 180,
    '_gen12': 257,
    '_gen13': 222,
    '_gen14': 200,
    '_gen15': 147,
    '_gen16': 153,
    '_gen17': 230,
    '_gen18': 154,
    '_gen19': 187,
    '_gen2': 203,
    '_gen20': 134,
    '_gen21': 262,
    '_gen22': 167,
    '_gen23': 181,
    '_gen24': 182,
    '_gen25': 232,
    '_gen26': 196,
    '_gen27': 225,
    '_gen28': 226,
    '_gen29': 255,
    '_gen3': 205,
    '_gen30': 189,
    '_gen31': 261,
    '_gen4': 236,
    '_gen5': 207,
    '_gen6': 233,
    '_gen7': 253,
    '_gen8': 249,
    '_gen9': 266,
    'abstract_declarator': 190,
    'block_item': 260,
    'block_item_list_opt': 256,
    'compound_statement': 152,
    'constant': 156,
    'control_line': 141,
    'declaration': 188,
    'declaration_list_opt': 160,
    'declaration_specifier': 263,
    'declarator': 150,
    'declarator_initializer': 195,
    'define_func_param': 202,
    'define_line': 158,
    'defined_identifier': 223,
    'designation': 245,
    'designation_opt': 246,
    'designator': 250,
    'direct_abstract_declarator_expr': 243,
    'direct_abstract_declarator_opt': 163,
    'direct_declarator_expr': 132,
    'direct_declarator_modifier': 267,
    'direct_declarator_modifier_list_opt': 258,
    'direct_declarator_parameter_list': 240,
    'direct_declarator_size': 212,
    'elipsis_opt': 142,
    'else_if_statement': 216,
    'else_if_statement_opt': 210,
    'else_part': 185,
    'else_statement': 201,
    'else_statement_opt': 211,
    'elseif_part': 175,
    'enum_specifier': 139,
    'enum_specifier_body': 166,
    'enum_specifier_sub': 161,
    'enumeration_constant': 197,
    'enumerator': 179,
    'enumerator_assignment': 198,
    'error_line': 234,
    'expression_opt': 192,
    'expression_statement': 227,
    'external_declaration': 251,
    'external_declaration_sub': 136,
    'for_cond': 259,
    'for_incr': 218,
    'for_init': 206,
    'function_definition': 248,
    'function_specifier': 131,
    'identifier': 151,
    'if_part': 174,
    'if_section': 208,
    'include_line': 217,
    'include_type': 178,
    'init_declarator': 191,
    'init_declarator_list_opt': 149,
    'initializer': 209,
    'initializer_list_item': 220,
    'iteration_statement': 235,
    'jump_statement': 239,
    'keyword': 252,
    'labeled_statement': 215,
    'line_line': 247,
    'parameter_declaration': 221,
    'parameter_declaration_sub': 144,
    'parameter_declaration_sub_sub': 148,
    'parameter_type_list': 213,
    'parameter_type_list_opt': 219,
    'pointer': 162,
    'pointer_opt': 172,
    'pointer_sub': 169,
    'pp': 135,
    'pp_directive': 268,
    'pp_file': 140,
    'pp_nodes': 165,
    'pp_nodes_list': 145,
    'pp_tokens': 157,
    'pragma_line': 228,
    'punctuator': 224,
    'replacement_list': 146,
    'selection_statement': 229,
    'sizeof_body': 231,
    'specifier_qualifier_list': 199,
    'statement': 184,
    'static_opt': 138,
    'storage_class_specifier': 170,
    'struct_declaration': 164,
    'struct_declarator': 183,
    'struct_declarator_body': 241,
    'struct_or_union': 242,
    'struct_or_union_body': 143,
    'struct_or_union_specifier': 133,
    'struct_or_union_sub': 137,
    'terminals': 159,
    'token': 193,
    'trailing_comma_opt': 214,
    'translation_unit': 244,
    'type_name': 171,
    'type_qualifier': 177,
    'type_qualifier_list_opt': 264,
    'type_specifier': 173,
    'typedef_name': 204,
    'undef_line': 265,
    'va_args': 237,
    'warning_line': 238,
  }
  terminal_count = 131
  nonterminal_count = 138
  parse_table = [
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 16, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, 5, 5, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 5, -1, -1, -1, 5, -1, -1, -1, -1, -1, -1, 5, -1, -1, -1, -1, -1, -1, 5, -1, -1, -1, 5, -1, -1, -1, -1, -1, 5, -1, -1, -1, -1, -1, -1, -1, -1, 5, -1, -1, -1, -1, -1, -1, -1, -1, 5, -1, -1, -1, -1, -1, 5, -1, -1, -1, -1, 5, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 5, -1, -1, -1, -1, -1, -1, -1, -1, 5],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 313, -1, -1, 313, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, 225, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 70, -1, 70, -1, -1, -1, -1, -1, -1, -1, 70, 70, -1, 70, -1, -1, -1, -1, 225, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 70, -1, -1, -1, -1, -1, -1, 70, -1, -1, 70, 225, -1, -1, -1, -1, -1, -1, 70, -1, -1, -1, 70, -1, -1, -1, 70, -1, -1, -1, 70, -1, -1, -1, -1, 70, -1, -1, -1, -1, -1, 70, -1, -1, -1, -1, -1, 70, -1, -1, 225, -1, -1, 70, -1, -1, -1, -1, 70, 70],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 102, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 431, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 163, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 338, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 69, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 11, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, 398, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 398, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 398, -1, -1, -1, -1, -1, -1, 398, -1, -1, -1, 13, -1, -1, -1, -1, -1, 398, -1, -1, -1, -1, -1, -1, -1, -1, 398, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 398, -1, -1, -1, -1, 398, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 398, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 25, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 302, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, 228, 228, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 228, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 228, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 228, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 191, -1, -1, -1, -1, -1, -1, -1, -1, 191, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 194, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, 348, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 348, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 22, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 22, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, 432, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 432, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 432, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, 77, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 77, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 77, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 402, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 59, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, 282, 282, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 282, 282, 282, -1, -1, 265, -1, -1, -1, -1, 282, 282, -1, 282, -1, -1, -1, -1, 282, -1, -1, -1, -1, -1, -1, -1, -1, -1, 282, 282, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 282, 282, -1, -1, 282, -1, -1, -1, 282, -1, 282, 282, 282, -1, -1, -1, 282, -1, -1, 282, -1, 282, -1, 282, -1, -1, -1, 282, -1, -1, -1, 282, -1, -1, -1, -1, 282, -1, -1, -1, -1, -1, 282, -1, -1, -1, -1, -1, 282, -1, -1, 282, -1, 282, 282, -1, -1, -1, -1, 282, 282],
  [-1, -1, 162, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 162, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 162, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 162, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, 192, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 185, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 209, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 180, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [155, -1, -1, 40, 298, 365, -1, 32, -1, 286, 200, 354, 94, -1, 417, -1, 328, 412, 112, -1, 234, -1, 301, 239, 37, 176, 387, 190, 345, 203, 358, 351, 137, 314, -1, -1, 121, 291, 71, 182, 254, 117, -1, 219, -1, 14, 248, -1, 423, 304, 43, 395, 397, 424, -1, 139, 150, 429, -1, 82, 21, 368, -1, 317, 8, 224, -1, 35, 75, 92, 147, -1, 447, 120, 271, 74, -1, 78, 321, 55, -1, 72, 269, -1, 446, -1, 441, 135, 362, 132, 231, -1, 26, 325, 278, 105, -1, 350, 6, 4, 42, 206, -1, 157, 411, -1, 380, -1, -1, 84, -1, -1, 413, -1, 443, 385, 114, 161, 138, -1, -1, 98, 280, 30, -1, -1, 433, 123, 136, -1, 370],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 296, -1, 296, -1, -1, 116, -1, -1, -1, -1, 296, 296, -1, 296, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 296, 296, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 296, 296, -1, -1, 296, -1, -1, -1, 296, -1, -1, 296, -1, -1, -1, -1, 296, -1, -1, 296, -1, -1, -1, 296, -1, -1, -1, 296, -1, -1, -1, 296, -1, -1, -1, -1, 296, -1, -1, -1, -1, -1, 296, -1, -1, -1, -1, -1, 296, -1, -1, -1, -1, 296, 296, -1, -1, -1, -1, 296, 296],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 409, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 242, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, 146, 146, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 146, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 146, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 146, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, 406, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 406, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 327, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 81, -1, 81, -1, -1, -1, -1, -1, -1, -1, 81, 81, -1, 81, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 81, -1, -1, -1, -1, -1, -1, 81, -1, -1, 81, -1, -1, -1, -1, -1, -1, -1, 81, -1, -1, -1, 81, -1, -1, -1, 81, -1, -1, -1, 81, -1, -1, -1, -1, 81, -1, -1, -1, -1, -1, 81, -1, -1, -1, -1, -1, 81, -1, -1, -1, -1, -1, 81, -1, -1, -1, -1, 81, 81],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 110, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, 288, 288, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 288, 288, 288, -1, -1, 283, -1, -1, -1, -1, 288, 288, -1, 288, -1, -1, -1, -1, 288, -1, -1, -1, -1, -1, -1, -1, -1, -1, 288, 288, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 288, 288, -1, -1, 288, -1, -1, -1, 288, -1, 288, 288, 288, -1, -1, -1, 288, -1, -1, 288, -1, 288, -1, 288, -1, -1, -1, 288, -1, -1, -1, 288, -1, -1, -1, -1, 288, -1, -1, -1, -1, -1, 288, -1, -1, -1, -1, -1, 288, -1, -1, 288, -1, 288, 288, -1, -1, -1, -1, 288, 288],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 29, -1, 29, -1, -1, 270, -1, -1, -1, -1, 29, 29, -1, 29, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 29, 29, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 29, 29, -1, -1, 29, -1, -1, -1, 29, -1, -1, 29, -1, -1, -1, -1, 29, -1, -1, 29, -1, -1, -1, 29, -1, -1, -1, 29, -1, -1, -1, 29, -1, -1, -1, -1, 29, -1, -1, -1, -1, -1, 29, -1, -1, -1, -1, -1, 29, -1, -1, -1, -1, 29, 29, -1, -1, -1, -1, 29, 29],
  [-1, -1, 436, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 113, 404, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 330, -1, -1, -1, 336, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 414, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 426, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 54, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, 213, 213, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 213, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 213, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 213, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 62, -1, 378, -1, -1, -1, -1, -1, -1, -1, 24, -1, -1, 24, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 80, -1, -1, -1, -1, -1, -1, 12, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 391, -1, -1, -1, 410, -1, -1, -1, 156, -1, -1, -1, 103, -1, -1, -1, -1, 342, -1, -1, -1, -1, -1, 50, -1, -1, -1, -1, -1, 160, -1, -1, -1, -1, -1, 86, -1, -1, -1, -1, 343, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 93, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 20, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 19],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 236, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, 101, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 101, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 101, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 312, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 316, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 235, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, 241, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 241, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 274, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 241, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, 106, -1, -1, -1, -1, -1, -1, -1, -1, 95, -1, -1, -1, 95, 337, -1, -1, 95, -1, -1, 95, -1, -1, -1, -1, -1, -1, -1, -1, 297, 3, -1, 106, -1, 337, -1, -1, -1, -1, -1, -1, -1, -1, 106, -1, -1, -1, -1, -1, 218, 106, -1, -1, -1, -1, -1, -1, -1, -1, -1, 106, -1, -1, -1, -1, -1, -1, -1, -1, 106, -1, -1, -1, -1, 106, -1, -1, -1, -1, -1, -1, -1, -1, -1, 106, -1, -1, -1, -1, 106, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 297, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 337, -1, -1, -1, 106, -1, -1, -1, -1, -1, 218, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 295, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 405, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 386, -1, 386, -1, -1, -1, -1, -1, -1, -1, 386, 386, -1, 386, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 386, 386, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 386, 386, -1, -1, 386, -1, -1, -1, 386, -1, -1, 386, -1, -1, -1, -1, 386, -1, -1, 386, -1, -1, -1, 386, -1, -1, -1, 386, -1, -1, -1, 386, -1, -1, -1, -1, 386, -1, -1, -1, -1, -1, 386, -1, -1, -1, -1, -1, 386, -1, -1, -1, -1, 386, 386, -1, -1, -1, -1, 386, 386],
  [-1, 169, 290, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 169, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 169, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 169, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, 279, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 279, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, 401, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 401, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 401, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, 285, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 285, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 285, -1, -1, -1, -1, 383, -1, 285, -1, -1, -1, -1, -1, -1, -1, -1, -1, 285, -1, -1, -1, -1, -1, -1, -1, -1, 285, -1, -1, -1, -1, 383, -1, -1, -1, -1, -1, -1, -1, -1, -1, 285, -1, -1, -1, -1, 285, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 285, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [220, -1, -1, 119, 220, 220, -1, 220, 133, -1, 220, -1, 119, -1, 220, -1, 119, 119, 220, 220, 119, -1, 220, 119, -1, 220, -1, -1, 119, 220, 119, 220, 119, 220, 119, -1, 220, 119, 119, 119, 220, 119, -1, -1, 174, 220, 220, -1, 220, 133, 220, 220, 119, 58, -1, 220, 119, 119, -1, 220, 220, 220, -1, 220, -1, 220, -1, 220, 220, 220, 119, -1, 220, 220, 119, 220, -1, 220, 119, 220, -1, 119, 220, 133, -1, -1, 119, 220, 220, 119, 119, -1, -1, 119, -1, 220, -1, 119, -1, 220, 220, 119, -1, 220, 119, -1, 119, -1, -1, 220, -1, -1, 119, -1, 220, 133, 220, 119, 119, -1, -1, 115, 220, 119, 119, -1, 220, 119, 220, 119, 119],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 27, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 415, 27, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, 247, 247, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 247, -1, -1, -1, 334, -1, -1, -1, -1, -1, -1, 247, -1, -1, -1, -1, -1, -1, 247, -1, -1, -1, 334, -1, -1, -1, -1, -1, 247, -1, -1, -1, -1, -1, -1, -1, -1, 247, -1, -1, -1, -1, -1, -1, -1, -1, 334, -1, -1, -1, -1, -1, 247, -1, -1, -1, -1, 247, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 247, -1, -1, -1, -1, -1, -1, -1, -1, 334],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 60, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 361, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 331, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 331, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 158, -1, 158, -1, -1, -1, -1, -1, -1, -1, 158, 375, -1, 158, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 158, -1, -1, -1, -1, -1, -1, 158, -1, -1, 375, -1, -1, -1, -1, -1, -1, -1, 158, -1, -1, -1, 158, -1, -1, -1, 158, -1, -1, -1, 158, -1, -1, -1, -1, 158, -1, -1, -1, -1, -1, 158, -1, -1, -1, -1, -1, 158, -1, -1, -1, -1, -1, 158, -1, -1, -1, -1, 158, 375],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 152, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 418, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 64, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 262, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 367, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, 1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 363, -1, 363, -1, -1, -1, -1, 1, -1, -1, 363, 363, -1, 363, -1, -1, -1, -1, 1, -1, -1, -1, -1, -1, -1, 1, -1, -1, 363, 363, -1, -1, -1, -1, -1, 1, -1, -1, -1, -1, -1, -1, 363, 363, 1, -1, 363, -1, -1, 28, 363, -1, -1, 363, -1, -1, -1, -1, 363, 1, -1, 363, -1, -1, 1, 363, -1, -1, -1, 363, -1, -1, -1, 363, -1, -1, -1, -1, 363, -1, -1, -1, -1, -1, 363, -1, -1, -1, -1, -1, 363, -1, -1, 1, -1, 363, 363, -1, -1, -1, -1, 363, 363],
  [-1, -1, -1, 408, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 408, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 408, -1, -1, -1, -1, -1, -1, 408, -1, -1, -1, -1, -1, -1, -1, -1, -1, 408, -1, -1, -1, -1, -1, -1, -1, -1, 408, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 408, -1, -1, -1, -1, 408, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 408, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, 333, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 366, -1, 333, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 333, -1, -1, -1, -1, -1, -1, 333, -1, -1, -1, -1, -1, -1, -1, -1, -1, 333, -1, -1, -1, -1, -1, -1, -1, -1, 333, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 333, -1, -1, -1, -1, 333, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 333, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, 439, -1, -1, -1, -1, -1, -1, -1, -1, 439, -1, -1, -1, 439, 439, -1, -1, 439, -1, -1, 439, -1, -1, -1, -1, 439, -1, 439, -1, 439, 439, -1, 439, 439, 439, 439, 439, -1, 439, -1, -1, -1, -1, 439, 439, -1, -1, -1, -1, 439, 439, -1, -1, 439, 439, -1, -1, -1, -1, -1, 439, -1, -1, -1, -1, -1, -1, 439, 439, 439, -1, 439, -1, -1, 439, 439, -1, -1, 439, -1, -1, -1, 186, 439, 439, -1, 439, 439, -1, 439, 439, -1, -1, -1, 439, -1, -1, -1, 439, -1, -1, 439, -1, 439, -1, -1, -1, -1, -1, 439, -1, -1, -1, -1, 439, 439, -1, -1, 439, -1, 439, 439, -1, -1, 439, -1, 439, 439],
  [-1, -1, -1, 183, -1, -1, -1, -1, -1, -1, -1, -1, 183, -1, -1, -1, 183, 183, -1, -1, 183, -1, -1, 183, -1, -1, -1, -1, 183, -1, 183, -1, 183, 183, -1, 183, 183, 183, 183, 183, -1, 183, -1, -1, -1, -1, 183, 183, -1, -1, -1, -1, 183, 183, -1, -1, 183, 183, -1, -1, -1, -1, -1, 183, -1, -1, -1, -1, -1, -1, 183, 183, 183, -1, 183, -1, -1, 183, 183, -1, -1, 183, -1, -1, -1, -1, 183, 183, -1, 183, 435, -1, 183, 183, -1, -1, -1, 183, -1, -1, -1, 183, -1, -1, 183, -1, 183, -1, -1, -1, -1, -1, 183, -1, -1, -1, -1, 183, 183, -1, -1, 183, -1, 183, 183, -1, -1, 183, -1, 183, 183],
  [-1, -1, 197, 195, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 195, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 195, -1, -1, -1, -1, -1, -1, 195, -1, -1, -1, -1, -1, -1, -1, -1, -1, 195, -1, -1, -1, -1, -1, -1, -1, -1, 195, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 195, -1, -1, -1, -1, 195, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 195, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 263, -1, 263, -1, -1, -1, -1, -1, -1, -1, 263, 263, -1, 263, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 263, 263, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 263, 263, -1, -1, 263, -1, -1, -1, 263, -1, -1, 263, -1, -1, -1, -1, 263, -1, -1, 263, -1, -1, -1, 263, -1, -1, -1, 263, -1, -1, -1, 263, -1, -1, -1, -1, 263, -1, -1, -1, -1, -1, 263, -1, -1, -1, -1, -1, 263, -1, -1, -1, -1, 263, 263, -1, -1, -1, -1, 263, 263],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 427, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 172, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 388, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 392, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 256, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 372, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 353, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 68, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 289, -1, 289, -1, -1, -1, -1, -1, -1, -1, 289, 289, -1, 289, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 289, 289, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 289, 289, -1, -1, 289, -1, -1, -1, 289, -1, -1, 289, -1, -1, -1, -1, 289, -1, -1, 289, -1, -1, -1, 289, -1, -1, -1, 289, -1, -1, -1, 289, -1, -1, -1, -1, 289, -1, -1, -1, -1, -1, 289, -1, -1, -1, -1, -1, 289, -1, -1, -1, -1, 289, 289, -1, -1, -1, -1, 289, 289],
  [-1, -1, -1, 166, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 166, -1, 166, -1, 166, -1, -1, -1, -1, 166, -1, -1, -1, -1, -1, 166, -1, -1, -1, -1, -1, -1, 166, -1, -1, -1, -1, -1, -1, -1, -1, -1, 166, -1, -1, -1, -1, -1, -1, -1, -1, 166, -1, -1, -1, 166, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 166, -1, -1, -1, -1, 166, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 83, -1, -1, -1, -1, -1, 166, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 198, -1, 198, -1, -1, -1, -1, -1, -1, -1, 198, 198, -1, 198, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 198, 198, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 198, 198, -1, -1, 198, -1, -1, -1, 198, -1, -1, 198, -1, -1, -1, -1, 198, -1, -1, 198, -1, -1, -1, 198, -1, -1, -1, 198, -1, -1, -1, 198, -1, -1, -1, -1, 198, -1, -1, -1, -1, -1, 198, -1, -1, -1, -1, -1, 198, -1, -1, -1, -1, 198, 198, -1, -1, -1, -1, 198, 198],
  [-1, -1, -1, 76, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 76, -1, 76, -1, 76, -1, -1, -1, -1, 76, -1, -1, -1, -1, -1, 76, -1, -1, -1, -1, -1, -1, 76, -1, -1, -1, -1, -1, -1, -1, -1, -1, 76, -1, -1, -1, -1, -1, -1, -1, -1, 76, -1, -1, -1, 76, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 76, -1, -1, -1, -1, 76, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 76, -1, -1, -1, -1, -1, 76, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [255, -1, -1, -1, 128, 39, -1, 310, -1, -1, 17, -1, -1, -1, 449, -1, -1, -1, 420, 272, -1, -1, 305, -1, -1, 45, -1, -1, -1, 227, -1, 419, -1, 18, -1, -1, 210, -1, -1, -1, 34, -1, -1, -1, -1, 173, 107, -1, 56, -1, 273, 165, -1, -1, -1, 315, -1, -1, -1, 131, 215, 349, -1, 0, -1, 109, -1, 292, 67, 332, -1, -1, 212, 196, -1, 223, -1, 243, -1, 97, -1, -1, 264, -1, -1, -1, -1, 306, 341, -1, -1, -1, -1, -1, -1, 175, -1, -1, -1, 181, 217, -1, -1, 394, -1, -1, -1, -1, -1, 445, -1, -1, -1, -1, 258, -1, 448, -1, -1, -1, -1, -1, 189, -1, -1, -1, 96, -1, 259, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 384, -1, 384, -1, -1, -1, -1, -1, -1, -1, 384, 384, -1, 384, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 384, 384, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 384, 384, -1, -1, 384, -1, -1, -1, 384, -1, -1, 384, -1, -1, -1, -1, 384, -1, -1, 384, -1, -1, -1, 384, -1, -1, -1, 384, -1, -1, -1, 384, -1, -1, -1, -1, 384, -1, -1, -1, -1, -1, 384, -1, -1, -1, -1, -1, 384, -1, -1, -1, -1, 384, 384, -1, -1, -1, -1, 384, 384],
  [-1, 347, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 233, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, 141, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 141, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 141, -1, -1, -1, -1, -1, -1, 141, -1, -1, -1, -1, -1, -1, -1, -1, -1, 141, -1, -1, -1, -1, -1, -1, -1, -1, 141, -1, -1, -1, -1, 141, -1, -1, -1, -1, -1, -1, -1, -1, -1, 141, -1, -1, -1, -1, 141, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 141, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 170, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 323, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 63, -1, 63, -1, -1, -1, -1, -1, 66, -1, 63, 63, -1, 63, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 63, -1, -1, -1, -1, -1, -1, 63, -1, -1, 63, -1, -1, -1, -1, -1, -1, -1, 63, -1, -1, -1, 63, -1, -1, -1, 63, -1, -1, -1, 63, -1, -1, -1, -1, 63, -1, -1, -1, -1, -1, 63, -1, -1, -1, -1, -1, 63, -1, -1, -1, -1, -1, 63, -1, -1, -1, -1, 63, 63],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 251, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 171, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, 154, 154, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 154, -1, -1, -1, -1, -1, -1, -1, -1, -1, 134, -1, -1, -1, -1, -1, -1, 154, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 154, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 134, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 154, -1, -1, -1, -1, -1, -1, -1, -1, 134],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 389, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 357, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 382, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 124, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, 201, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 381, -1, -1, -1, 232, -1, -1, -1, 38, -1, -1, 246, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 371, -1, 371, -1, -1, -1, -1, -1, -1, -1, 371, 371, -1, 371, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 371, 371, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 371, 371, -1, -1, 371, -1, -1, -1, 371, -1, -1, 371, -1, -1, -1, -1, 371, -1, -1, 371, -1, -1, -1, 371, -1, -1, -1, 371, -1, -1, -1, 371, -1, -1, -1, -1, 371, -1, -1, -1, -1, -1, 371, -1, -1, -1, -1, -1, 371, -1, -1, 434, -1, 371, 371, -1, -1, -1, -1, 371, 371],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 276, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 129, -1, -1, 142, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, 240, 324, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 324, -1, -1, -1, 324, -1, -1, -1, -1, -1, -1, 324, -1, -1, -1, -1, -1, -1, 324, -1, -1, -1, 324, -1, -1, -1, -1, -1, 324, -1, -1, -1, -1, -1, -1, -1, -1, 324, -1, -1, -1, -1, -1, -1, -1, -1, 324, -1, -1, -1, -1, -1, 324, -1, -1, -1, -1, 324, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 324, -1, -1, -1, -1, -1, -1, -1, -1, 324],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 421, -1, 421, -1, -1, -1, -1, -1, -1, -1, 421, 421, -1, 421, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 421, 421, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 421, 421, -1, -1, 421, -1, -1, -1, 421, -1, -1, 421, -1, -1, -1, -1, 421, -1, -1, 421, -1, -1, -1, 421, -1, -1, -1, 421, -1, -1, -1, 421, -1, -1, -1, -1, 421, -1, -1, -1, -1, -1, 421, -1, -1, -1, -1, -1, 421, -1, -1, -1, -1, 421, 421, -1, -1, -1, -1, 421, 421],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 403, -1, -1, -1, -1, -1, -1, -1, -1, 403, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 403, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, 87, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 149, -1, 87, -1, 87, -1, -1, -1, -1, 149, -1, -1, -1, -1, -1, 87, -1, -1, -1, -1, -1, -1, 87, -1, -1, -1, -1, -1, -1, -1, -1, -1, 87, -1, -1, -1, -1, -1, -1, -1, -1, 87, -1, -1, -1, 149, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 87, -1, -1, -1, -1, 87, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 87, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, 230, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 230, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 230, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 284, -1, 284, -1, -1, -1, -1, -1, -1, -1, 284, 284, -1, 284, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 284, 284, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 284, 284, -1, -1, 284, -1, -1, -1, 284, -1, -1, 284, -1, -1, -1, -1, 284, -1, -1, 284, -1, -1, -1, 284, -1, -1, -1, 284, -1, -1, -1, 284, -1, -1, -1, -1, 284, -1, -1, -1, -1, -1, 284, -1, -1, -1, -1, -1, 284, -1, -1, -1, -1, 284, 284, -1, -1, -1, -1, 284, 284],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 214, -1, -1, -1, -1, -1, -1, -1, -1, 48, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 88, -1, 88, -1, -1, -1, -1, -1, -1, -1, 88, 88, -1, 88, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 88, 88, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 88, 88, -1, -1, 88, -1, -1, -1, 88, -1, -1, 88, -1, -1, -1, -1, 88, -1, -1, 88, -1, -1, -1, 88, -1, -1, -1, 88, -1, -1, -1, 88, -1, -1, -1, -1, 88, -1, -1, -1, -1, -1, 88, -1, -1, -1, -1, -1, 88, -1, -1, -1, -1, 88, 88, -1, -1, -1, -1, 88, 88],
  [-1, -1, -1, 311, -1, -1, -1, -1, -1, -1, -1, -1, 148, -1, -1, -1, 425, 127, -1, -1, 204, -1, -1, 287, -1, -1, -1, -1, 373, -1, 244, -1, 299, -1, 65, -1, -1, 320, 208, 168, -1, 221, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 61, -1, -1, -1, 47, 151, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 193, -1, -1, -1, 90, -1, -1, -1, 261, -1, -1, 199, -1, -1, -1, -1, 188, -1, -1, 444, 355, -1, -1, 293, -1, -1, -1, 229, -1, -1, -1, 339, -1, -1, 438, -1, 275, -1, -1, -1, -1, -1, 335, -1, -1, -1, -1, 15, 159, -1, -1, -1, -1, 178, 407, -1, -1, 2, -1, 340, 253],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 329, -1, 329, -1, -1, -1, -1, -1, -1, -1, 329, 329, -1, 329, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 329, 329, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 329, 329, -1, -1, 329, -1, -1, -1, 329, -1, -1, 329, -1, -1, -1, -1, 329, -1, -1, 329, -1, -1, -1, 329, -1, -1, -1, 329, -1, -1, -1, 329, -1, -1, -1, -1, 329, -1, -1, -1, -1, -1, 329, -1, -1, -1, -1, -1, 329, -1, -1, -1, -1, 329, 329, -1, -1, -1, -1, 329, 329],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 7, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, 376, -1, -1, -1, -1, -1, -1, -1, -1, 376, -1, -1, -1, 376, 376, -1, -1, 376, -1, -1, 376, -1, -1, -1, -1, 376, -1, 376, -1, 376, 376, -1, 376, 36, 376, 376, 376, -1, 376, -1, -1, -1, -1, 376, -1, -1, -1, -1, -1, 376, 376, -1, -1, 376, 376, -1, -1, -1, -1, -1, 376, -1, -1, -1, -1, -1, -1, 376, 376, 376, -1, 376, -1, -1, 376, 376, -1, -1, 376, -1, -1, -1, -1, 376, 376, -1, 376, -1, -1, 376, 376, -1, -1, -1, 376, -1, -1, -1, 376, -1, -1, 376, -1, 376, -1, -1, -1, -1, -1, 376, -1, -1, -1, -1, 376, 376, -1, -1, 376, -1, 376, 376, -1, -1, 376, -1, 376, 376],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 104, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 268, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, 130, 130, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 130, -1, -1, -1, 130, -1, -1, -1, -1, -1, -1, 130, -1, -1, -1, -1, -1, -1, 130, -1, -1, -1, 130, -1, -1, -1, -1, -1, 130, -1, -1, -1, -1, -1, -1, -1, -1, 130, -1, -1, -1, -1, -1, -1, -1, -1, 130, -1, -1, -1, -1, -1, 130, -1, -1, -1, -1, 130, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 130, -1, -1, -1, -1, -1, -1, -1, -1, 130],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 352, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, 85, -1, -1, -1, -1, -1, -1, -1, -1, 85, -1, -1, -1, 85, 85, -1, -1, 85, -1, -1, 85, -1, -1, -1, -1, 145, -1, 145, -1, 85, 85, -1, 85, -1, 85, 145, 145, -1, 145, -1, -1, -1, -1, 85, -1, -1, -1, -1, -1, 85, 85, -1, -1, 145, 145, -1, -1, -1, -1, -1, 85, -1, -1, -1, -1, -1, -1, 145, 145, 85, -1, 145, -1, -1, 85, 145, -1, -1, 145, -1, -1, -1, -1, 145, 85, -1, 145, -1, -1, 85, 145, -1, -1, -1, 145, -1, -1, -1, 145, -1, -1, 85, -1, 145, -1, -1, -1, -1, -1, 145, -1, -1, -1, -1, 85, 145, -1, -1, 85, -1, 145, 145, -1, -1, 85, -1, 145, 145],
  [-1, -1, -1, 400, -1, -1, -1, -1, -1, -1, -1, -1, 400, -1, -1, -1, 400, 400, -1, -1, 400, -1, -1, 400, -1, -1, -1, -1, 400, -1, 400, -1, 400, 400, -1, 400, 428, 400, 400, 400, -1, 400, -1, -1, -1, -1, 400, -1, -1, -1, -1, -1, 400, 400, -1, -1, 400, 400, -1, -1, -1, -1, -1, 400, -1, -1, -1, -1, -1, -1, 400, 400, 400, -1, 400, -1, -1, 400, 400, -1, -1, 400, -1, -1, -1, -1, 400, 400, -1, 400, -1, -1, 400, 400, -1, -1, -1, 400, -1, -1, -1, 400, -1, -1, 400, -1, 400, -1, -1, -1, -1, -1, 400, -1, -1, -1, -1, 400, 400, -1, -1, 400, -1, 400, 400, -1, -1, 400, -1, 400, 400],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 257, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 257, -1, -1, -1, -1, 252, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 399, -1, 399, -1, -1, -1, -1, -1, -1, -1, 399, 179, -1, 399, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 430, 430, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 430, 399, -1, -1, 430, -1, -1, -1, 399, -1, -1, 179, -1, -1, -1, -1, 430, -1, -1, 399, -1, -1, -1, 399, -1, -1, -1, 399, -1, -1, -1, 399, -1, -1, -1, -1, 399, -1, -1, -1, -1, -1, 399, -1, -1, -1, -1, -1, 399, -1, -1, -1, -1, 374, 399, -1, -1, -1, -1, 399, 179],
  [-1, 91, 91, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 91, -1, -1, -1, -1, -1, -1, -1, -1, -1, 202, -1, -1, -1, -1, -1, -1, 91, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 91, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 202, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 91, -1, -1, -1, -1, -1, -1, -1, -1, 202],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, 52, 52, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 396, 52, 396, -1, -1, -1, -1, -1, -1, -1, 396, 396, -1, 396, -1, -1, -1, -1, 52, -1, -1, -1, -1, -1, -1, -1, -1, -1, 396, 396, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 396, 396, -1, -1, 396, -1, -1, -1, 396, -1, 52, 396, -1, -1, -1, -1, 396, -1, -1, 396, -1, 52, -1, 396, -1, -1, -1, 396, -1, -1, -1, 396, -1, -1, -1, -1, 396, -1, -1, -1, -1, -1, 396, -1, -1, -1, -1, -1, 396, -1, -1, 52, -1, 396, 396, -1, -1, -1, -1, 396, 396],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 122, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 143, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 122, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 122],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1]
  ]
  def terminal(self, str):
    return self.str_terminal[str]
  def terminalNames(self):
    return list(self.str_terminal.keys())
  def isTerminal(self, id):
    return 0 <= id <= 130
  def isNonTerminal(self, id):
    return 131 <= id <= 268
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
    self.start = entry.upper()
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
    return self.parse_table[n - 131][self.sym.getId()]
  def call(self, nt_str):
    return getattr(self, nt_str)()
  def __DIRECT_ABSTRACT_DECLARATOR(self, depth = 0):
    rule = self.rule(186)
    if depth is not False:
      tracer = DebugTracer("__DIRECT_ABSTRACT_DECLARATOR", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(186, self.getAtomString(186)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def __DIRECT_DECLARATOR(self, depth = 0):
    rule = self.rule(254)
    if depth is not False:
      tracer = DebugTracer("__DIRECT_DECLARATOR", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(254, self.getAtomString(254)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def __GEN0(self, depth = 0):
    rule = self.rule(155)
    if depth is not False:
      tracer = DebugTracer("__GEN0", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(155, self.getAtomString(155)), tracer )
    tree.list = 'tlist'
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 266:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PP_NODES(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(21, tracer) ) # separator
      subtree = self.__GEN0(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN1(self, depth = 0):
    rule = self.rule(176)
    if depth is not False:
      tracer = DebugTracer("__GEN1", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(176, self.getAtomString(176)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 303:
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
  def __GEN10(self, depth = 0):
    rule = self.rule(168)
    if depth is not False:
      tracer = DebugTracer("__GEN10", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(168, self.getAtomString(168)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [33]):
      return tree
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 29:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DECLARATION(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN10(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN11(self, depth = 0):
    rule = self.rule(180)
    if depth is not False:
      tracer = DebugTracer("__GEN11", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(180, self.getAtomString(180)), tracer )
    tree.list = 'slist'
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 101:
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
    else:
      try:
        if not self.recorder.awake:
          self.recorder.wake()
        self.recorder.record(self.sym)
        tree.astTransform = AstTransformSubstitution(0)
        subtree = self._INIT_DECLARATOR(depth)
        tree.add( subtree )
        if tracer and isinstance(subtree, ParseTree):
          tracer.add( subtree.tracer )
        subtree = self.__GEN12(depth)
        tree.add( subtree )
        if tracer and isinstance(subtree, ParseTree):
          tracer.add( subtree.tracer )
      except SyntaxError as e:
        if self.recorder.awake:
          self.recorder.sleep()
          self.rewind(self.recorder)
        raise e
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def __GEN12(self, depth = 0):
    rule = self.rule(257)
    if depth is not False:
      tracer = DebugTracer("__GEN12", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(257, self.getAtomString(257)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in [77]):
      return tree
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 104:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(29, tracer) ) # comma
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
  def __GEN13(self, depth = 0):
    rule = self.rule(222)
    if depth is not False:
      tracer = DebugTracer("__GEN13", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(222, self.getAtomString(222)), tracer )
    tree.list = 'slist'
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 76:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._INITIALIZER_LIST_ITEM(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN14(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    else:
      try:
        if not self.recorder.awake:
          self.recorder.wake()
        self.recorder.record(self.sym)
        tree.astTransform = AstTransformSubstitution(0)
        subtree = self._INITIALIZER_LIST_ITEM(depth)
        tree.add( subtree )
        if tracer and isinstance(subtree, ParseTree):
          tracer.add( subtree.tracer )
        subtree = self.__GEN14(depth)
        tree.add( subtree )
        if tracer and isinstance(subtree, ParseTree):
          tracer.add( subtree.tracer )
      except SyntaxError as e:
        if self.recorder.awake:
          self.recorder.sleep()
          self.rewind(self.recorder)
        raise e
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def __GEN14(self, depth = 0):
    rule = self.rule(200)
    if depth is not False:
      tracer = DebugTracer("__GEN14", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(200, self.getAtomString(200)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in [102]):
      return tree
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 152:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(29, tracer) ) # comma
      subtree = self._INITIALIZER_LIST_ITEM(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN14(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN15(self, depth = 0):
    rule = self.rule(147)
    if depth is not False:
      tracer = DebugTracer("__GEN15", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(147, self.getAtomString(147)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [76]):
      return tree
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 191:
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
  def __GEN16(self, depth = 0):
    rule = self.rule(153)
    if depth is not False:
      tracer = DebugTracer("__GEN16", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(153, self.getAtomString(153)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [28, 91, 56, 57, 1, 93, -1, 112, 86, 254, 80, 97, 38, 129, 70, 163, 71, 41, 74, 101, 29, 130, 123, 2, 124, 78, 121, 46, 81, 82, 30, 106, 39, 118, 89]):
      return tree
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 265:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STRUCT_OR_UNION_BODY(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN17(self, depth = 0):
    rule = self.rule(230)
    if depth is not False:
      tracer = DebugTracer("__GEN17", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(230, self.getAtomString(230)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [36]):
      return tree
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 63:
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
    return tree
  def __GEN18(self, depth = 0):
    rule = self.rule(154)
    if depth is not False:
      tracer = DebugTracer("__GEN18", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(154, self.getAtomString(154)), tracer )
    tree.list = 'slist'
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 162:
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
    else:
      try:
        if not self.recorder.awake:
          self.recorder.wake()
        self.recorder.record(self.sym)
        tree.astTransform = AstTransformSubstitution(0)
        subtree = self._STRUCT_DECLARATOR(depth)
        tree.add( subtree )
        if tracer and isinstance(subtree, ParseTree):
          tracer.add( subtree.tracer )
        subtree = self.__GEN19(depth)
        tree.add( subtree )
        if tracer and isinstance(subtree, ParseTree):
          tracer.add( subtree.tracer )
      except SyntaxError as e:
        if self.recorder.awake:
          self.recorder.sleep()
          self.rewind(self.recorder)
        raise e
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def __GEN19(self, depth = 0):
    rule = self.rule(187)
    if depth is not False:
      tracer = DebugTracer("__GEN19", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(187, self.getAtomString(187)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in [77]):
      return tree
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 295:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(29, tracer) ) # comma
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
  def __GEN2(self, depth = 0):
    rule = self.rule(203)
    if depth is not False:
      tracer = DebugTracer("__GEN2", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(203, self.getAtomString(203)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 346:
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
  def __GEN20(self, depth = 0):
    rule = self.rule(134)
    if depth is not False:
      tracer = DebugTracer("__GEN20", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(134, self.getAtomString(134)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [46, 121, 82, 254, 2, -1]):
      return tree
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 70:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._SPECIFIER_QUALIFIER_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN21(self, depth = 0):
    rule = self.rule(262)
    if depth is not False:
      tracer = DebugTracer("__GEN21", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(262, self.getAtomString(262)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [77, 29]):
      return tree
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 252:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STRUCT_DECLARATOR_BODY(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN22(self, depth = 0):
    rule = self.rule(167)
    if depth is not False:
      tracer = DebugTracer("__GEN22", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(167, self.getAtomString(167)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [28, 71, 56, 80, 1, 74, 2, -1, 254, 86, 57, 97, 89, 38, 70, 91, 30, 41, 112, 93, 29, 130, 123, 101, 124, 78, 81, 46, 121, 82, 163, 106, 39, 118, 129]):
      return tree
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 283:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._ENUM_SPECIFIER_BODY(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN23(self, depth = 0):
    rule = self.rule(181)
    if depth is not False:
      tracer = DebugTracer("__GEN23", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(181, self.getAtomString(181)), tracer )
    tree.list = 'slist'
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 312:
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
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def __GEN24(self, depth = 0):
    rule = self.rule(182)
    if depth is not False:
      tracer = DebugTracer("__GEN24", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(182, self.getAtomString(182)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in [102]):
      return tree
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 316:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(29, tracer) ) # comma
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
  def __GEN25(self, depth = 0):
    rule = self.rule(232)
    if depth is not False:
      tracer = DebugTracer("__GEN25", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(232, self.getAtomString(232)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [46, 121, 254, 29, 1, 57, 2, -1, 163]):
      return tree
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 134:
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
  def __GEN26(self, depth = 0):
    rule = self.rule(196)
    if depth is not False:
      tracer = DebugTracer("__GEN26", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(196, self.getAtomString(196)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [46, 3, 121, 72, 92, 2, 35, 87, 194, -1, 53, 156, 63]):
      return tree
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 334:
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
  def __GEN27(self, depth = 0):
    rule = self.rule(225)
    if depth is not False:
      tracer = DebugTracer("__GEN27", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(225, self.getAtomString(225)), tracer )
    tree.list = 'slist'
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 384:
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
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def __GEN28(self, depth = 0):
    rule = self.rule(226)
    if depth is not False:
      tracer = DebugTracer("__GEN28", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(226, self.getAtomString(226)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in [1]):
      return tree
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 233:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(29, tracer) ) # comma
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
  def __GEN29(self, depth = 0):
    rule = self.rule(255)
    if depth is not False:
      tracer = DebugTracer("__GEN29", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(255, self.getAtomString(255)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 7:
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
  def __GEN3(self, depth = 0):
    rule = self.rule(205)
    if depth is not False:
      tracer = DebugTracer("__GEN3", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(205, self.getAtomString(205)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 367:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(29, tracer) ) # comma
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
  def __GEN30(self, depth = 0):
    rule = self.rule(189)
    if depth is not False:
      tracer = DebugTracer("__GEN30", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(189, self.getAtomString(189)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [46, 121, 29, 163, 1, -1, 254]):
      return tree
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 290:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._POINTER_SUB(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN30(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN31(self, depth = 0):
    rule = self.rule(261)
    if depth is not False:
      tracer = DebugTracer("__GEN31", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(261, self.getAtomString(261)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [36]):
      return tree
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 400:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._BLOCK_ITEM(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN31(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    else:
      try:
        if not self.recorder.awake:
          self.recorder.wake()
        self.recorder.record(self.sym)
        tree.astTransform = AstTransformSubstitution(0)
        subtree = self._BLOCK_ITEM(depth)
        tree.add( subtree )
        if tracer and isinstance(subtree, ParseTree):
          tracer.add( subtree.tracer )
        subtree = self.__GEN31(depth)
        tree.add( subtree )
        if tracer and isinstance(subtree, ParseTree):
          tracer.add( subtree.tracer )
      except SyntaxError as e:
        if self.recorder.awake:
          self.recorder.sleep()
          self.rewind(self.recorder)
        raise e
      return tree
    return tree
  def __GEN4(self, depth = 0):
    rule = self.rule(236)
    if depth is not False:
      tracer = DebugTracer("__GEN4", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(236, self.getAtomString(236)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 164:
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
    rule = self.rule(207)
    if depth is not False:
      tracer = DebugTracer("__GEN5", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(207, self.getAtomString(207)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 408:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN6(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    else:
      try:
        if not self.recorder.awake:
          self.recorder.wake()
        self.recorder.record(self.sym)
        tree.astTransform = AstTransformSubstitution(0)
        subtree = self.__EXPR(depth)
        tree.add( subtree )
        if tracer and isinstance(subtree, ParseTree):
          tracer.add( subtree.tracer )
        subtree = self.__GEN6(depth)
        tree.add( subtree )
        if tracer and isinstance(subtree, ParseTree):
          tracer.add( subtree.tracer )
      except SyntaxError as e:
        if self.recorder.awake:
          self.recorder.sleep()
          self.rewind(self.recorder)
        raise e
      return tree
    return tree
  def __GEN6(self, depth = 0):
    rule = self.rule(233)
    if depth is not False:
      tracer = DebugTracer("__GEN6", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(233, self.getAtomString(233)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 389:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(29, tracer) ) # comma
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN6(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN7(self, depth = 0):
    rule = self.rule(253)
    if depth is not False:
      tracer = DebugTracer("__GEN7", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(253, self.getAtomString(253)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 329:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._EXTERNAL_DECLARATION(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN7(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN8(self, depth = 0):
    rule = self.rule(249)
    if depth is not False:
      tracer = DebugTracer("__GEN8", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(249, self.getAtomString(249)), tracer )
    tree.list = 'mlist'
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 284:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DECLARATION_SPECIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN9(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def __GEN9(self, depth = 0):
    rule = self.rule(266)
    if depth is not False:
      tracer = DebugTracer("__GEN9", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(266, self.getAtomString(266)), tracer )
    tree.list = 'mlist'
    if self.sym != None and (self.sym.getId() in [91, 121, 46, 29, 80, 1, 2, -1, 254, 163]):
      return tree
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 396:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DECLARATION_SPECIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN9(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _ABSTRACT_DECLARATOR(self, depth = 0):
    rule = self.rule(190)
    if depth is not False:
      tracer = DebugTracer("_ABSTRACT_DECLARATOR", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(190, self.getAtomString(190)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 279:
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
    else:
      try:
        if not self.recorder.awake:
          self.recorder.wake()
        self.recorder.record(self.sym)
        tree.astTransform = AstTransformSubstitution(0)
        subtree = self._POINTER_OPT(depth)
        tree.add( subtree )
        if tracer and isinstance(subtree, ParseTree):
          tracer.add( subtree.tracer )
        subtree = self._DIRECT_ABSTRACT_DECLARATOR_OPT(depth)
        tree.add( subtree )
        if tracer and isinstance(subtree, ParseTree):
          tracer.add( subtree.tracer )
      except SyntaxError as e:
        if self.recorder.awake:
          self.recorder.sleep()
          self.rewind(self.recorder)
        raise e
      return tree
    return tree
  def _BLOCK_ITEM(self, depth = 0):
    rule = self.rule(260)
    if depth is not False:
      tracer = DebugTracer("_BLOCK_ITEM", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(260, self.getAtomString(260)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 85:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 145:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DECLARATION(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    else:
      try:
        if not self.recorder.awake:
          self.recorder.wake()
        self.recorder.record(self.sym)
        tree.astTransform = AstTransformSubstitution(0)
        subtree = self._STATEMENT(depth)
        tree.add( subtree )
        if tracer and isinstance(subtree, ParseTree):
          tracer.add( subtree.tracer )
      except SyntaxError as e:
        if self.recorder.awake:
          self.recorder.sleep()
          self.rewind(self.recorder)
        raise e
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _BLOCK_ITEM_LIST_OPT(self, depth = 0):
    rule = self.rule(256)
    if depth is not False:
      tracer = DebugTracer("_BLOCK_ITEM_LIST_OPT", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(256, self.getAtomString(256)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [36]):
      return tree
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 376:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN31(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    else:
      try:
        if not self.recorder.awake:
          self.recorder.wake()
        self.recorder.record(self.sym)
        tree.astTransform = AstTransformSubstitution(0)
        subtree = self.__GEN31(depth)
        tree.add( subtree )
        if tracer and isinstance(subtree, ParseTree):
          tracer.add( subtree.tracer )
      except SyntaxError as e:
        if self.recorder.awake:
          self.recorder.sleep()
          self.rewind(self.recorder)
        raise e
      return tree
    return tree
  def _COMPOUND_STATEMENT(self, depth = 0):
    rule = self.rule(152)
    if depth is not False:
      tracer = DebugTracer("_COMPOUND_STATEMENT", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(152, self.getAtomString(152)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 59:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(33, tracer) ) # lbrace
      subtree = self._BLOCK_ITEM_LIST_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(36, tracer) ) # rbrace
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _CONSTANT(self, depth = 0):
    rule = self.rule(156)
    if depth is not False:
      tracer = DebugTracer("_CONSTANT", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(156, self.getAtomString(156)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 180:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(115, tracer) ) # integer_constant
      return tree
    elif rule == 185:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(49, tracer) ) # character_constant
      return tree
    elif rule == 192:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(8, tracer) ) # floating_constant
      return tree
    elif rule == 209:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(83, tracer) ) # enumeration_constant
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _CONTROL_LINE(self, depth = 0):
    rule = self.rule(141)
    if depth is not False:
      tracer = DebugTracer("_CONTROL_LINE", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(141, self.getAtomString(141)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _DECLARATION(self, depth = 0):
    rule = self.rule(188)
    if depth is not False:
      tracer = DebugTracer("_DECLARATION", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(188, self.getAtomString(188)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 386:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN8(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self._INIT_DECLARATOR_LIST_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(77, tracer) ) # semi
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _DECLARATION_LIST_OPT(self, depth = 0):
    rule = self.rule(160)
    if depth is not False:
      tracer = DebugTracer("_DECLARATION_LIST_OPT", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(160, self.getAtomString(160)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [33]):
      return tree
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 296:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN10(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _DECLARATION_SPECIFIER(self, depth = 0):
    rule = self.rule(263)
    if depth is not False:
      tracer = DebugTracer("_DECLARATION_SPECIFIER", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(263, self.getAtomString(263)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 179:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._TYPE_QUALIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 374:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._FUNCTION_SPECIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 399:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._TYPE_SPECIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 430:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STORAGE_CLASS_SPECIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _DECLARATOR(self, depth = 0):
    rule = self.rule(150)
    if depth is not False:
      tracer = DebugTracer("_DECLARATOR", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(150, self.getAtomString(150)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 77:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._POINTER_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__DIRECT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    else:
      try:
        if not self.recorder.awake:
          self.recorder.wake()
        self.recorder.record(self.sym)
        tree.astTransform = AstTransformSubstitution(0)
        subtree = self._POINTER_OPT(depth)
        tree.add( subtree )
        if tracer and isinstance(subtree, ParseTree):
          tracer.add( subtree.tracer )
        subtree = self.__DIRECT_DECLARATOR(depth)
        tree.add( subtree )
        if tracer and isinstance(subtree, ParseTree):
          tracer.add( subtree.tracer )
      except SyntaxError as e:
        if self.recorder.awake:
          self.recorder.sleep()
          self.rewind(self.recorder)
        raise e
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _DECLARATOR_INITIALIZER(self, depth = 0):
    rule = self.rule(195)
    if depth is not False:
      tracer = DebugTracer("_DECLARATOR_INITIALIZER", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(195, self.getAtomString(195)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [77, 29]):
      return tree
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 415:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(76, tracer) ) # equals
      subtree = self._INITIALIZER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _DEFINE_FUNC_PARAM(self, depth = 0):
    rule = self.rule(202)
    if depth is not False:
      tracer = DebugTracer("_DEFINE_FUNC_PARAM", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(202, self.getAtomString(202)), tracer )
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
    rule = self.rule(223)
    if depth is not False:
      tracer = DebugTracer("_DEFINED_IDENTIFIER", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(223, self.getAtomString(223)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _DESIGNATION(self, depth = 0):
    rule = self.rule(245)
    if depth is not False:
      tracer = DebugTracer("_DESIGNATION", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(245, self.getAtomString(245)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 403:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN15(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(76, tracer) ) # equals
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _DESIGNATION_OPT(self, depth = 0):
    rule = self.rule(246)
    if depth is not False:
      tracer = DebugTracer("_DESIGNATION_OPT", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(246, self.getAtomString(246)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [33, 121, 46, -1, 92, 63, 156, 87, 3, 194, 53, 35, 72]):
      return tree
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 149:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DESIGNATION(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _DESIGNATOR(self, depth = 0):
    rule = self.rule(250)
    if depth is not False:
      tracer = DebugTracer("_DESIGNATOR", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(250, self.getAtomString(250)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 48:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(40, tracer) ) # lsquare
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(48, tracer) ) # rsquare
      return tree
    elif rule == 214:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(31, tracer) ) # dot
      tree.add( self.expect(121, tracer) ) # identifier
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _DIRECT_ABSTRACT_DECLARATOR_EXPR(self, depth = 0):
    rule = self.rule(243)
    if depth is not False:
      tracer = DebugTracer("_DIRECT_ABSTRACT_DECLARATOR_EXPR", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(243, self.getAtomString(243)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 240:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(2, tracer) ) # asterisk
      return tree
    elif rule == 324:
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
    else:
      try:
        if not self.recorder.awake:
          self.recorder.wake()
        self.recorder.record(self.sym)
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
      except SyntaxError as e:
        if self.recorder.awake:
          self.recorder.sleep()
          self.rewind(self.recorder)
        raise e
      return tree
    return tree
  def _DIRECT_ABSTRACT_DECLARATOR_OPT(self, depth = 0):
    rule = self.rule(163)
    if depth is not False:
      tracer = DebugTracer("_DIRECT_ABSTRACT_DECLARATOR_OPT", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(163, self.getAtomString(163)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [1, 29]):
      return tree
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 327:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__DIRECT_ABSTRACT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    else:
      try:
        if not self.recorder.awake:
          self.recorder.wake()
        self.recorder.record(self.sym)
        tree.astTransform = AstTransformSubstitution(0)
        subtree = self.__DIRECT_ABSTRACT_DECLARATOR(depth)
        tree.add( subtree )
        if tracer and isinstance(subtree, ParseTree):
          tracer.add( subtree.tracer )
      except SyntaxError as e:
        if self.recorder.awake:
          self.recorder.sleep()
          self.rewind(self.recorder)
        raise e
      return tree
    return tree
  def _DIRECT_DECLARATOR_EXPR(self, depth = 0):
    rule = self.rule(132)
    if depth is not False:
      tracer = DebugTracer("_DIRECT_DECLARATOR_EXPR", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(132, self.getAtomString(132)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 5:
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
    else:
      try:
        if not self.recorder.awake:
          self.recorder.wake()
        self.recorder.record(self.sym)
        tree.astTransform = AstTransformSubstitution(0)
        subtree = self._DIRECT_DECLARATOR_MODIFIER_LIST_OPT(depth)
        tree.add( subtree )
        if tracer and isinstance(subtree, ParseTree):
          tracer.add( subtree.tracer )
        subtree = self._DIRECT_DECLARATOR_SIZE(depth)
        tree.add( subtree )
        if tracer and isinstance(subtree, ParseTree):
          tracer.add( subtree.tracer )
      except SyntaxError as e:
        if self.recorder.awake:
          self.recorder.sleep()
          self.rewind(self.recorder)
        raise e
      return tree
    return tree
  def _DIRECT_DECLARATOR_MODIFIER(self, depth = 0):
    rule = self.rule(267)
    if depth is not False:
      tracer = DebugTracer("_DIRECT_DECLARATOR_MODIFIER", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(267, self.getAtomString(267)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 122:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._TYPE_QUALIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 143:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(57, tracer) ) # static
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _DIRECT_DECLARATOR_MODIFIER_LIST_OPT(self, depth = 0):
    rule = self.rule(258)
    if depth is not False:
      tracer = DebugTracer("_DIRECT_DECLARATOR_MODIFIER_LIST_OPT", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(258, self.getAtomString(258)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [46, 121, -1, 92, 63, 2, 156, 87, 194, 3, 53, 35, 72]):
      return tree
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 130:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN26(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _DIRECT_DECLARATOR_PARAMETER_LIST(self, depth = 0):
    rule = self.rule(240)
    if depth is not False:
      tracer = DebugTracer("_DIRECT_DECLARATOR_PARAMETER_LIST", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(240, self.getAtomString(240)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 371:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PARAMETER_TYPE_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 434:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN29(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _DIRECT_DECLARATOR_SIZE(self, depth = 0):
    rule = self.rule(212)
    if depth is not False:
      tracer = DebugTracer("_DIRECT_DECLARATOR_SIZE", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(212, self.getAtomString(212)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 195:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 197:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(2, tracer) ) # asterisk
      return tree
    else:
      try:
        if not self.recorder.awake:
          self.recorder.wake()
        self.recorder.record(self.sym)
        tree.astTransform = AstTransformSubstitution(0)
        subtree = self.__EXPR(depth)
        tree.add( subtree )
        if tracer and isinstance(subtree, ParseTree):
          tracer.add( subtree.tracer )
      except SyntaxError as e:
        if self.recorder.awake:
          self.recorder.sleep()
          self.rewind(self.recorder)
        raise e
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _ELIPSIS_OPT(self, depth = 0):
    rule = self.rule(142)
    if depth is not False:
      tracer = DebugTracer("_ELIPSIS_OPT", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(142, self.getAtomString(142)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _ELSE_IF_STATEMENT(self, depth = 0):
    rule = self.rule(216)
    if depth is not False:
      tracer = DebugTracer("_ELSE_IF_STATEMENT", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(216, self.getAtomString(216)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 372:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(85, tracer) ) # else_if
      tree.add( self.expect(46, tracer) ) # lparen
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(51, tracer) ) # rparen
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _ELSE_IF_STATEMENT_OPT(self, depth = 0):
    rule = self.rule(210)
    if depth is not False:
      tracer = DebugTracer("_ELSE_IF_STATEMENT_OPT", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(210, self.getAtomString(210)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [63, 12, 92, 35, 56, 101, 52, -1, 3, 112, 86, 28, 33, 127, 57, 106, 97, 36, 117, 41, 38, 129, 70, 87, 71, 72, 37, 32, 74, 93, 16, 130, 104, 124, 77, 121, 156, 78, 20, 46, 47, 81, 123, 30, 90, 17, 39, 194, 118, 53, 89, 23]):
      return tree
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 186:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._ELSE_IF_STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(47, tracer) ) # endif
      return tree
    return tree
  def _ELSE_PART(self, depth = 0):
    rule = self.rule(185)
    if depth is not False:
      tracer = DebugTracer("_ELSE_PART", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(185, self.getAtomString(185)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _ELSE_STATEMENT(self, depth = 0):
    rule = self.rule(201)
    if depth is not False:
      tracer = DebugTracer("_ELSE_STATEMENT", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(201, self.getAtomString(201)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 64:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(90, tracer) ) # else
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _ELSE_STATEMENT_OPT(self, depth = 0):
    rule = self.rule(211)
    if depth is not False:
      tracer = DebugTracer("_ELSE_STATEMENT_OPT", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(211, self.getAtomString(211)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [63, 12, 92, 35, 56, 101, 52, -1, 3, 112, 86, 28, 33, 127, 57, 106, 97, 36, 117, 41, 38, 129, 70, 87, 71, 72, 37, 32, 74, 93, 16, 130, 104, 124, 77, 121, 78, 20, 46, 47, 81, 123, 30, 156, 17, 39, 194, 118, 53, 89, 23]):
      return tree
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 435:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._ELSE_STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(47, tracer) ) # endif
      return tree
    return tree
  def _ELSEIF_PART(self, depth = 0):
    rule = self.rule(175)
    if depth is not False:
      tracer = DebugTracer("_ELSEIF_PART", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(175, self.getAtomString(175)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _ENUM_SPECIFIER(self, depth = 0):
    rule = self.rule(139)
    if depth is not False:
      tracer = DebugTracer("_ENUM_SPECIFIER", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(139, self.getAtomString(139)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 25:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(28, tracer) ) # enum
      subtree = self._ENUM_SPECIFIER_SUB(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _ENUM_SPECIFIER_BODY(self, depth = 0):
    rule = self.rule(166)
    if depth is not False:
      tracer = DebugTracer("_ENUM_SPECIFIER_BODY", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(166, self.getAtomString(166)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 110:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(33, tracer) ) # lbrace
      subtree = self.__GEN23(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self._TRAILING_COMMA_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(36, tracer) ) # rbrace
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _ENUM_SPECIFIER_SUB(self, depth = 0):
    rule = self.rule(161)
    if depth is not False:
      tracer = DebugTracer("_ENUM_SPECIFIER_SUB", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(161, self.getAtomString(161)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 242:
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
    elif rule == 409:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._ENUM_SPECIFIER_BODY(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _ENUMERATION_CONSTANT(self, depth = 0):
    rule = self.rule(197)
    if depth is not False:
      tracer = DebugTracer("_ENUMERATION_CONSTANT", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(197, self.getAtomString(197)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 60:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(121, tracer) ) # identifier
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _ENUMERATOR(self, depth = 0):
    rule = self.rule(179)
    if depth is not False:
      tracer = DebugTracer("_ENUMERATOR", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(179, self.getAtomString(179)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 236:
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
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _ENUMERATOR_ASSIGNMENT(self, depth = 0):
    rule = self.rule(198)
    if depth is not False:
      tracer = DebugTracer("_ENUMERATOR_ASSIGNMENT", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(198, self.getAtomString(198)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [102, 29]):
      return tree
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 361:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(18, tracer) ) # assign
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _ERROR_LINE(self, depth = 0):
    rule = self.rule(234)
    if depth is not False:
      tracer = DebugTracer("_ERROR_LINE", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(234, self.getAtomString(234)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _EXPRESSION_OPT(self, depth = 0):
    rule = self.rule(192)
    if depth is not False:
      tracer = DebugTracer("_EXPRESSION_OPT", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(192, self.getAtomString(192)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [77, 51]):
      return tree
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 285:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    else:
      try:
        if not self.recorder.awake:
          self.recorder.wake()
        self.recorder.record(self.sym)
        tree.astTransform = AstTransformSubstitution(0)
        subtree = self.__EXPR(depth)
        tree.add( subtree )
        if tracer and isinstance(subtree, ParseTree):
          tracer.add( subtree.tracer )
      except SyntaxError as e:
        if self.recorder.awake:
          self.recorder.sleep()
          self.rewind(self.recorder)
        raise e
      return tree
    return tree
  def _EXPRESSION_STATEMENT(self, depth = 0):
    rule = self.rule(227)
    if depth is not False:
      tracer = DebugTracer("_EXPRESSION_STATEMENT", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(227, self.getAtomString(227)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 141:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._EXPRESSION_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(77, tracer) ) # semi
      return tree
    else:
      try:
        if not self.recorder.awake:
          self.recorder.wake()
        self.recorder.record(self.sym)
        tree.astTransform = AstTransformSubstitution(0)
        subtree = self._EXPRESSION_OPT(depth)
        tree.add( subtree )
        if tracer and isinstance(subtree, ParseTree):
          tracer.add( subtree.tracer )
        tree.add( self.expect(77, tracer) ) # semi
      except SyntaxError as e:
        if self.recorder.awake:
          self.recorder.sleep()
          self.rewind(self.recorder)
        raise e
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _EXTERNAL_DECLARATION(self, depth = 0):
    rule = self.rule(251)
    if depth is not False:
      tracer = DebugTracer("_EXTERNAL_DECLARATION", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(251, self.getAtomString(251)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 88:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN8(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self._EXTERNAL_DECLARATION_SUB(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _EXTERNAL_DECLARATION_SUB(self, depth = 0):
    rule = self.rule(136)
    if depth is not False:
      tracer = DebugTracer("_EXTERNAL_DECLARATION_SUB", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(136, self.getAtomString(136)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 163:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(80, tracer) ) # function_hint
      subtree = self._FUNCTION_DEFINITION(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 338:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(91, tracer) ) # declarator_hint
      subtree = self._INIT_DECLARATOR_LIST_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(77, tracer) ) # semi
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _FOR_COND(self, depth = 0):
    rule = self.rule(259)
    if depth is not False:
      tracer = DebugTracer("_FOR_COND", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(259, self.getAtomString(259)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 352:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(77, tracer) ) # semi
      subtree = self._EXPRESSION_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _FOR_INCR(self, depth = 0):
    rule = self.rule(218)
    if depth is not False:
      tracer = DebugTracer("_FOR_INCR", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(218, self.getAtomString(218)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [51]):
      return tree
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 68:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(77, tracer) ) # semi
      subtree = self._EXPRESSION_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _FOR_INIT(self, depth = 0):
    rule = self.rule(206)
    if depth is not False:
      tracer = DebugTracer("_FOR_INIT", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(206, self.getAtomString(206)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [77]):
      return tree
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 1:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 363:
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
    else:
      try:
        if not self.recorder.awake:
          self.recorder.wake()
        self.recorder.record(self.sym)
        tree.astTransform = AstTransformSubstitution(0)
        subtree = self.__EXPR(depth)
        tree.add( subtree )
        if tracer and isinstance(subtree, ParseTree):
          tracer.add( subtree.tracer )
      except SyntaxError as e:
        if self.recorder.awake:
          self.recorder.sleep()
          self.rewind(self.recorder)
        raise e
      return tree
    return tree
  def _FUNCTION_DEFINITION(self, depth = 0):
    rule = self.rule(248)
    if depth is not False:
      tracer = DebugTracer("_FUNCTION_DEFINITION", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(248, self.getAtomString(248)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 230:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self._DECLARATION_LIST_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self._COMPOUND_STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    else:
      try:
        if not self.recorder.awake:
          self.recorder.wake()
        self.recorder.record(self.sym)
        tree.astTransform = AstTransformSubstitution(0)
        subtree = self._DECLARATOR(depth)
        tree.add( subtree )
        if tracer and isinstance(subtree, ParseTree):
          tracer.add( subtree.tracer )
        subtree = self._DECLARATION_LIST_OPT(depth)
        tree.add( subtree )
        if tracer and isinstance(subtree, ParseTree):
          tracer.add( subtree.tracer )
        subtree = self._COMPOUND_STATEMENT(depth)
        tree.add( subtree )
        if tracer and isinstance(subtree, ParseTree):
          tracer.add( subtree.tracer )
      except SyntaxError as e:
        if self.recorder.awake:
          self.recorder.sleep()
          self.rewind(self.recorder)
        raise e
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _FUNCTION_SPECIFIER(self, depth = 0):
    rule = self.rule(131)
    if depth is not False:
      tracer = DebugTracer("_FUNCTION_SPECIFIER", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(131, self.getAtomString(131)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 16:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(123, tracer) ) # inline
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _IDENTIFIER(self, depth = 0):
    rule = self.rule(151)
    if depth is not False:
      tracer = DebugTracer("_IDENTIFIER", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(151, self.getAtomString(151)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 402:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(121, tracer) ) # identifier
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _IF_PART(self, depth = 0):
    rule = self.rule(174)
    if depth is not False:
      tracer = DebugTracer("_IF_PART", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(174, self.getAtomString(174)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _IF_SECTION(self, depth = 0):
    rule = self.rule(208)
    if depth is not False:
      tracer = DebugTracer("_IF_SECTION", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(208, self.getAtomString(208)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _INCLUDE_LINE(self, depth = 0):
    rule = self.rule(217)
    if depth is not False:
      tracer = DebugTracer("_INCLUDE_LINE", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(217, self.getAtomString(217)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _INCLUDE_TYPE(self, depth = 0):
    rule = self.rule(178)
    if depth is not False:
      tracer = DebugTracer("_INCLUDE_TYPE", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(178, self.getAtomString(178)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _INIT_DECLARATOR(self, depth = 0):
    rule = self.rule(191)
    if depth is not False:
      tracer = DebugTracer("_INIT_DECLARATOR", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(191, self.getAtomString(191)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 401:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self._DECLARATOR_INITIALIZER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    else:
      try:
        if not self.recorder.awake:
          self.recorder.wake()
        self.recorder.record(self.sym)
        tree.astTransform = AstTransformSubstitution(0)
        subtree = self._DECLARATOR(depth)
        tree.add( subtree )
        if tracer and isinstance(subtree, ParseTree):
          tracer.add( subtree.tracer )
        subtree = self._DECLARATOR_INITIALIZER(depth)
        tree.add( subtree )
        if tracer and isinstance(subtree, ParseTree):
          tracer.add( subtree.tracer )
      except SyntaxError as e:
        if self.recorder.awake:
          self.recorder.sleep()
          self.rewind(self.recorder)
        raise e
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _INIT_DECLARATOR_LIST_OPT(self, depth = 0):
    rule = self.rule(149)
    if depth is not False:
      tracer = DebugTracer("_INIT_DECLARATOR_LIST_OPT", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(149, self.getAtomString(149)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 432:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN11(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    else:
      try:
        if not self.recorder.awake:
          self.recorder.wake()
        self.recorder.record(self.sym)
        tree.astTransform = AstTransformSubstitution(0)
        subtree = self.__GEN11(depth)
        tree.add( subtree )
        if tracer and isinstance(subtree, ParseTree):
          tracer.add( subtree.tracer )
      except SyntaxError as e:
        if self.recorder.awake:
          self.recorder.sleep()
          self.rewind(self.recorder)
        raise e
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _INITIALIZER(self, depth = 0):
    rule = self.rule(209)
    if depth is not False:
      tracer = DebugTracer("_INITIALIZER", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(209, self.getAtomString(209)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 333:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 366:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(33, tracer) ) # lbrace
      subtree = self.__GEN13(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self._TRAILING_COMMA_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(36, tracer) ) # rbrace
      return tree
    else:
      try:
        if not self.recorder.awake:
          self.recorder.wake()
        self.recorder.record(self.sym)
        tree.astTransform = AstTransformSubstitution(0)
        subtree = self.__EXPR(depth)
        tree.add( subtree )
        if tracer and isinstance(subtree, ParseTree):
          tracer.add( subtree.tracer )
      except SyntaxError as e:
        if self.recorder.awake:
          self.recorder.sleep()
          self.rewind(self.recorder)
        raise e
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _INITIALIZER_LIST_ITEM(self, depth = 0):
    rule = self.rule(220)
    if depth is not False:
      tracer = DebugTracer("_INITIALIZER_LIST_ITEM", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(220, self.getAtomString(220)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 83:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(115, tracer) ) # integer_constant
      return tree
    elif rule == 166:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DESIGNATION_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self._INITIALIZER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    else:
      try:
        if not self.recorder.awake:
          self.recorder.wake()
        self.recorder.record(self.sym)
        tree.astTransform = AstTransformSubstitution(0)
        subtree = self._DESIGNATION_OPT(depth)
        tree.add( subtree )
        if tracer and isinstance(subtree, ParseTree):
          tracer.add( subtree.tracer )
        subtree = self._INITIALIZER(depth)
        tree.add( subtree )
        if tracer and isinstance(subtree, ParseTree):
          tracer.add( subtree.tracer )
      except SyntaxError as e:
        if self.recorder.awake:
          self.recorder.sleep()
          self.rewind(self.recorder)
        raise e
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _ITERATION_STATEMENT(self, depth = 0):
    rule = self.rule(235)
    if depth is not False:
      tracer = DebugTracer("_ITERATION_STATEMENT", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(235, self.getAtomString(235)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 124:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(117, tracer) ) # for
      tree.add( self.expect(46, tracer) ) # lparen
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
      tree.add( self.expect(51, tracer) ) # rparen
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 357:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(17, tracer) ) # while
      tree.add( self.expect(46, tracer) ) # lparen
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(51, tracer) ) # rparen
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 382:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(37, tracer) ) # do
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(17, tracer) ) # while
      tree.add( self.expect(46, tracer) ) # lparen
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(51, tracer) ) # rparen
      tree.add( self.expect(77, tracer) ) # semi
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _JUMP_STATEMENT(self, depth = 0):
    rule = self.rule(239)
    if depth is not False:
      tracer = DebugTracer("_JUMP_STATEMENT", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(239, self.getAtomString(239)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 38:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(20, tracer) ) # break
      tree.add( self.expect(77, tracer) ) # semi
      return tree
    elif rule == 232:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(16, tracer) ) # continue
      return tree
    elif rule == 246:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(23, tracer) ) # return
      subtree = self._EXPRESSION_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(77, tracer) ) # semi
      return tree
    elif rule == 381:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(12, tracer) ) # goto
      tree.add( self.expect(121, tracer) ) # identifier
      tree.add( self.expect(77, tracer) ) # semi
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _KEYWORD(self, depth = 0):
    rule = self.rule(252)
    if depth is not False:
      tracer = DebugTracer("_KEYWORD", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(252, self.getAtomString(252)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 2:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(127, tracer) ) # switch
      return tree
    elif rule == 15:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(117, tracer) ) # for
      return tree
    elif rule == 47:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(56, tracer) ) # typedef
      return tree
    elif rule == 61:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(52, tracer) ) # if
      return tree
    elif rule == 65:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(34, tracer) ) # _imaginary
      return tree
    elif rule == 90:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(74, tracer) ) # register
      return tree
    elif rule == 127:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(17, tracer) ) # while
      return tree
    elif rule == 148:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(12, tracer) ) # goto
      return tree
    elif rule == 151:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(57, tracer) ) # static
      return tree
    elif rule == 159:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(118, tracer) ) # unsigned
      return tree
    elif rule == 168:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(39, tracer) ) # volatile
      return tree
    elif rule == 178:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(123, tracer) ) # inline
      return tree
    elif rule == 188:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(86, tracer) ) # extern
      return tree
    elif rule == 193:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(70, tracer) ) # auto
      return tree
    elif rule == 199:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(81, tracer) ) # restrict
      return tree
    elif rule == 204:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(20, tracer) ) # break
      return tree
    elif rule == 208:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(38, tracer) ) # struct
      return tree
    elif rule == 221:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(41, tracer) ) # union
      return tree
    elif rule == 229:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(97, tracer) ) # long
      return tree
    elif rule == 244:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(30, tracer) ) # char
      return tree
    elif rule == 253:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(130, tracer) ) # const
      return tree
    elif rule == 261:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(78, tracer) ) # void
      return tree
    elif rule == 275:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(106, tracer) ) # double
      return tree
    elif rule == 287:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(23, tracer) ) # return
      return tree
    elif rule == 293:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(93, tracer) ) # int
      return tree
    elif rule == 299:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(32, tracer) ) # default
      return tree
    elif rule == 311:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(3, tracer) ) # sizeof
      return tree
    elif rule == 320:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(37, tracer) ) # do
      return tree
    elif rule == 335:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(112, tracer) ) # signed
      return tree
    elif rule == 339:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(101, tracer) ) # float
      return tree
    elif rule == 340:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(129, tracer) ) # _complex
      return tree
    elif rule == 355:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(90, tracer) ) # else
      return tree
    elif rule == 373:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(28, tracer) ) # enum
      return tree
    elif rule == 407:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(124, tracer) ) # _bool
      return tree
    elif rule == 425:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(16, tracer) ) # continue
      return tree
    elif rule == 438:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(104, tracer) ) # case
      return tree
    elif rule == 444:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(89, tracer) ) # short
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _LABELED_STATEMENT(self, depth = 0):
    rule = self.rule(215)
    if depth is not False:
      tracer = DebugTracer("_LABELED_STATEMENT", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(215, self.getAtomString(215)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 256:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(121, tracer) ) # identifier
      tree.add( self.expect(82, tracer) ) # colon
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 388:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(32, tracer) ) # default
      tree.add( self.expect(82, tracer) ) # colon
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 392:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(104, tracer) ) # case
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(82, tracer) ) # colon
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _LINE_LINE(self, depth = 0):
    rule = self.rule(247)
    if depth is not False:
      tracer = DebugTracer("_LINE_LINE", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(247, self.getAtomString(247)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _PARAMETER_DECLARATION(self, depth = 0):
    rule = self.rule(221)
    if depth is not False:
      tracer = DebugTracer("_PARAMETER_DECLARATION", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(221, self.getAtomString(221)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 198:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN8(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self._PARAMETER_DECLARATION_SUB(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _PARAMETER_DECLARATION_SUB(self, depth = 0):
    rule = self.rule(144)
    if depth is not False:
      tracer = DebugTracer("_PARAMETER_DECLARATION_SUB", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(144, self.getAtomString(144)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [1, 29]):
      return tree
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 228:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._POINTER_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self._PARAMETER_DECLARATION_SUB_SUB(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    else:
      try:
        if not self.recorder.awake:
          self.recorder.wake()
        self.recorder.record(self.sym)
        tree.astTransform = AstTransformSubstitution(0)
        subtree = self._POINTER_OPT(depth)
        tree.add( subtree )
        if tracer and isinstance(subtree, ParseTree):
          tracer.add( subtree.tracer )
        subtree = self._PARAMETER_DECLARATION_SUB_SUB(depth)
        tree.add( subtree )
        if tracer and isinstance(subtree, ParseTree):
          tracer.add( subtree.tracer )
      except SyntaxError as e:
        if self.recorder.awake:
          self.recorder.sleep()
          self.rewind(self.recorder)
        raise e
      return tree
    return tree
  def _PARAMETER_DECLARATION_SUB_SUB(self, depth = 0):
    rule = self.rule(148)
    if depth is not False:
      tracer = DebugTracer("_PARAMETER_DECLARATION_SUB_SUB", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(148, self.getAtomString(148)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [1, 29]):
      return tree
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 22:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__DIRECT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 348:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DIRECT_ABSTRACT_DECLARATOR_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    else:
      try:
        if not self.recorder.awake:
          self.recorder.wake()
        self.recorder.record(self.sym)
        tree.astTransform = AstTransformSubstitution(0)
        subtree = self._DIRECT_ABSTRACT_DECLARATOR_OPT(depth)
        tree.add( subtree )
        if tracer and isinstance(subtree, ParseTree):
          tracer.add( subtree.tracer )
      except SyntaxError as e:
        if self.recorder.awake:
          self.recorder.sleep()
          self.rewind(self.recorder)
        raise e
      return tree
    return tree
  def _PARAMETER_TYPE_LIST(self, depth = 0):
    rule = self.rule(213)
    if depth is not False:
      tracer = DebugTracer("_PARAMETER_TYPE_LIST", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(213, self.getAtomString(213)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 263:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN27(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self._VA_ARGS(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _PARAMETER_TYPE_LIST_OPT(self, depth = 0):
    rule = self.rule(219)
    if depth is not False:
      tracer = DebugTracer("_PARAMETER_TYPE_LIST_OPT", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(219, self.getAtomString(219)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 289:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PARAMETER_TYPE_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _POINTER(self, depth = 0):
    rule = self.rule(162)
    if depth is not False:
      tracer = DebugTracer("_POINTER", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(162, self.getAtomString(162)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [46, 121, 29, 163, 1, -1, 254]):
      return tree
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 146:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN30(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _POINTER_OPT(self, depth = 0):
    rule = self.rule(172)
    if depth is not False:
      tracer = DebugTracer("_POINTER_OPT", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(172, self.getAtomString(172)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [46, 121, 29, 163, 1, -1, 254]):
      return tree
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 213:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._POINTER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _POINTER_SUB(self, depth = 0):
    rule = self.rule(169)
    if depth is not False:
      tracer = DebugTracer("_POINTER_SUB", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(169, self.getAtomString(169)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 436:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(2, tracer) ) # asterisk
      subtree = self._TYPE_QUALIFIER_LIST_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _PP(self, depth = 0):
    rule = self.rule(135)
    if depth is not False:
      tracer = DebugTracer("_PP", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(135, self.getAtomString(135)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 102:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(15, tracer) ) # defined
      return tree
    elif rule == 431:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(105, tracer) ) # defined_separator
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _PP_DIRECTIVE(self, depth = 0):
    rule = self.rule(268)
    if depth is not False:
      tracer = DebugTracer("_PP_DIRECTIVE", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(268, self.getAtomString(268)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _PP_FILE(self, depth = 0):
    rule = self.rule(140)
    if depth is not False:
      tracer = DebugTracer("_PP_FILE", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(140, self.getAtomString(140)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _PP_NODES(self, depth = 0):
    rule = self.rule(165)
    if depth is not False:
      tracer = DebugTracer("_PP_NODES", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(165, self.getAtomString(165)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _PP_NODES_LIST(self, depth = 0):
    rule = self.rule(145)
    if depth is not False:
      tracer = DebugTracer("_PP_NODES_LIST", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(145, self.getAtomString(145)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _PP_TOKENS(self, depth = 0):
    rule = self.rule(157)
    if depth is not False:
      tracer = DebugTracer("_PP_TOKENS", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(157, self.getAtomString(157)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _PRAGMA_LINE(self, depth = 0):
    rule = self.rule(228)
    if depth is not False:
      tracer = DebugTracer("_PRAGMA_LINE", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(228, self.getAtomString(228)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _PUNCTUATOR(self, depth = 0):
    rule = self.rule(224)
    if depth is not False:
      tracer = DebugTracer("_PUNCTUATOR", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(224, self.getAtomString(224)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 0:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(63, tracer) ) # incr
      return tree
    elif rule == 17:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(10, tracer) ) # modeq
      return tree
    elif rule == 18:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(33, tracer) ) # lbrace
      return tree
    elif rule == 34:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(40, tracer) ) # lsquare
      return tree
    elif rule == 39:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(5, tracer) ) # exclamation_point
      return tree
    elif rule == 45:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(25, tracer) ) # arrow
      return tree
    elif rule == 56:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(48, tracer) ) # rsquare
      return tree
    elif rule == 67:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(68, tracer) ) # bitxor
      return tree
    elif rule == 96:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(126, tracer) ) # lt
      return tree
    elif rule == 97:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(79, tracer) ) # gteq
      return tree
    elif rule == 107:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(46, tracer) ) # lparen
      return tree
    elif rule == 109:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(65, tracer) ) # rshift
      return tree
    elif rule == 128:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(4, tracer) ) # subeq
      return tree
    elif rule == 131:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(59, tracer) ) # tilde
      return tree
    elif rule == 165:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(51, tracer) ) # rparen
      return tree
    elif rule == 173:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(45, tracer) ) # sub
      return tree
    elif rule == 175:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(95, tracer) ) # or
      return tree
    elif rule == 181:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(99, tracer) ) # and
      return tree
    elif rule == 189:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(122, tracer) ) # bitandeq
      return tree
    elif rule == 196:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(73, tracer) ) # elipsis
      return tree
    elif rule == 210:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(36, tracer) ) # rbrace
      return tree
    elif rule == 212:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(72, tracer) ) # mul
      return tree
    elif rule == 215:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(60, tracer) ) # bitxoreq
      return tree
    elif rule == 217:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(100, tracer) ) # bitor
      return tree
    elif rule == 223:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(75, tracer) ) # div
      return tree
    elif rule == 227:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(29, tracer) ) # comma
      return tree
    elif rule == 243:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(77, tracer) ) # semi
      return tree
    elif rule == 255:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(0, tracer) ) # rshifteq
      return tree
    elif rule == 258:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(114, tracer) ) # bitoreq
      return tree
    elif rule == 259:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(128, tracer) ) # lshifteq
      return tree
    elif rule == 264:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(82, tracer) ) # colon
      return tree
    elif rule == 272:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(19, tracer) ) # ampersand
      return tree
    elif rule == 273:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(50, tracer) ) # pound
      return tree
    elif rule == 292:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(67, tracer) ) # add
      return tree
    elif rule == 305:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(22, tracer) ) # poundpound
      return tree
    elif rule == 306:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(87, tracer) ) # decr
      return tree
    elif rule == 310:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(7, tracer) ) # addeq
      return tree
    elif rule == 315:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(55, tracer) ) # gt
      return tree
    elif rule == 332:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(69, tracer) ) # mod
      return tree
    elif rule == 341:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(88, tracer) ) # questionmark
      return tree
    elif rule == 349:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(61, tracer) ) # lshift
      return tree
    elif rule == 394:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(103, tracer) ) # neq
      return tree
    elif rule == 419:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(31, tracer) ) # dot
      return tree
    elif rule == 420:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(18, tracer) ) # assign
      return tree
    elif rule == 445:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(109, tracer) ) # eq
      return tree
    elif rule == 448:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(116, tracer) ) # lteq
      return tree
    elif rule == 449:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(14, tracer) ) # muleq
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _REPLACEMENT_LIST(self, depth = 0):
    rule = self.rule(146)
    if depth is not False:
      tracer = DebugTracer("_REPLACEMENT_LIST", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(146, self.getAtomString(146)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _SELECTION_STATEMENT(self, depth = 0):
    rule = self.rule(229)
    if depth is not False:
      tracer = DebugTracer("_SELECTION_STATEMENT", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(229, self.getAtomString(229)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 170:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(52, tracer) ) # if
      tree.add( self.expect(46, tracer) ) # lparen
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(51, tracer) ) # rparen
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(47, tracer) ) # endif
      subtree = self._ELSE_IF_STATEMENT_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self._ELSE_STATEMENT_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 323:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(127, tracer) ) # switch
      tree.add( self.expect(46, tracer) ) # lparen
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(51, tracer) ) # rparen
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _SIZEOF_BODY(self, depth = 0):
    rule = self.rule(231)
    if depth is not False:
      tracer = DebugTracer("_SIZEOF_BODY", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(231, self.getAtomString(231)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 171:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(121, tracer) ) # identifier
      return tree
    elif rule == 251:
      tree.astTransform = AstTransformSubstitution(1)
      tree.add( self.expect(46, tracer) ) # lparen
      subtree = self._TYPE_NAME(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(51, tracer) ) # rparen
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _SPECIFIER_QUALIFIER_LIST(self, depth = 0):
    rule = self.rule(199)
    if depth is not False:
      tracer = DebugTracer("_SPECIFIER_QUALIFIER_LIST", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(199, self.getAtomString(199)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 158:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._TYPE_SPECIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN20(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 375:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._TYPE_QUALIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN20(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _STATEMENT(self, depth = 0):
    rule = self.rule(184)
    if depth is not False:
      tracer = DebugTracer("_STATEMENT", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(184, self.getAtomString(184)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 3:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._COMPOUND_STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 95:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._JUMP_STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 106:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._EXPRESSION_STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 218:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._SELECTION_STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 297:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._LABELED_STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 337:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._ITERATION_STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    else:
      try:
        if not self.recorder.awake:
          self.recorder.wake()
        self.recorder.record(self.sym)
        tree.astTransform = AstTransformSubstitution(0)
        subtree = self._EXPRESSION_STATEMENT(depth)
        tree.add( subtree )
        if tracer and isinstance(subtree, ParseTree):
          tracer.add( subtree.tracer )
      except SyntaxError as e:
        if self.recorder.awake:
          self.recorder.sleep()
          self.rewind(self.recorder)
        raise e
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _STATIC_OPT(self, depth = 0):
    rule = self.rule(138)
    if depth is not False:
      tracer = DebugTracer("_STATIC_OPT", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(138, self.getAtomString(138)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [46, 121, -1, 92, 63, 156, 87, 3, 194, 53, 35, 72]):
      return tree
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 13:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(57, tracer) ) # static
      return tree
    return tree
  def _STORAGE_CLASS_SPECIFIER(self, depth = 0):
    rule = self.rule(170)
    if depth is not False:
      tracer = DebugTracer("_STORAGE_CLASS_SPECIFIER", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(170, self.getAtomString(170)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 113:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(56, tracer) ) # typedef
      return tree
    elif rule == 330:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(70, tracer) ) # auto
      return tree
    elif rule == 336:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(74, tracer) ) # register
      return tree
    elif rule == 404:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(57, tracer) ) # static
      return tree
    elif rule == 414:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(86, tracer) ) # extern
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _STRUCT_DECLARATION(self, depth = 0):
    rule = self.rule(164)
    if depth is not False:
      tracer = DebugTracer("_STRUCT_DECLARATION", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(164, self.getAtomString(164)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 81:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._SPECIFIER_QUALIFIER_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN18(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(77, tracer) ) # semi
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _STRUCT_DECLARATOR(self, depth = 0):
    rule = self.rule(183)
    if depth is not False:
      tracer = DebugTracer("_STRUCT_DECLARATOR", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(183, self.getAtomString(183)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 241:
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
    elif rule == 274:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STRUCT_DECLARATOR_BODY(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    else:
      try:
        if not self.recorder.awake:
          self.recorder.wake()
        self.recorder.record(self.sym)
        tree.astTransform = AstTransformSubstitution(0)
        subtree = self._DECLARATOR(depth)
        tree.add( subtree )
        if tracer and isinstance(subtree, ParseTree):
          tracer.add( subtree.tracer )
        subtree = self.__GEN21(depth)
        tree.add( subtree )
        if tracer and isinstance(subtree, ParseTree):
          tracer.add( subtree.tracer )
      except SyntaxError as e:
        if self.recorder.awake:
          self.recorder.sleep()
          self.rewind(self.recorder)
        raise e
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _STRUCT_DECLARATOR_BODY(self, depth = 0):
    rule = self.rule(241)
    if depth is not False:
      tracer = DebugTracer("_STRUCT_DECLARATOR_BODY", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(241, self.getAtomString(241)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 276:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(82, tracer) ) # colon
      subtree = self._DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _STRUCT_OR_UNION(self, depth = 0):
    rule = self.rule(242)
    if depth is not False:
      tracer = DebugTracer("_STRUCT_OR_UNION", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(242, self.getAtomString(242)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 129:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(38, tracer) ) # struct
      return tree
    elif rule == 142:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(41, tracer) ) # union
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _STRUCT_OR_UNION_BODY(self, depth = 0):
    rule = self.rule(143)
    if depth is not False:
      tracer = DebugTracer("_STRUCT_OR_UNION_BODY", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(143, self.getAtomString(143)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 302:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(33, tracer) ) # lbrace
      subtree = self.__GEN17(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(36, tracer) ) # rbrace
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _STRUCT_OR_UNION_SPECIFIER(self, depth = 0):
    rule = self.rule(133)
    if depth is not False:
      tracer = DebugTracer("_STRUCT_OR_UNION_SPECIFIER", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(133, self.getAtomString(133)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 313:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STRUCT_OR_UNION(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self._STRUCT_OR_UNION_SUB(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _STRUCT_OR_UNION_SUB(self, depth = 0):
    rule = self.rule(137)
    if depth is not False:
      tracer = DebugTracer("_STRUCT_OR_UNION_SUB", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(137, self.getAtomString(137)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 11:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._IDENTIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN16(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 69:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STRUCT_OR_UNION_BODY(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _TERMINALS(self, depth = 0):
    rule = self.rule(159)
    if depth is not False:
      tracer = DebugTracer("_TERMINALS", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(159, self.getAtomString(159)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 4:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(99, tracer) ) # and
      return tree
    elif rule == 6:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(98, tracer) ) # number
      return tree
    elif rule == 8:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(64, tracer) ) # decimal_floating_constant
      return tree
    elif rule == 14:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(45, tracer) ) # sub
      return tree
    elif rule == 21:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(60, tracer) ) # bitxoreq
      return tree
    elif rule == 26:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(92, tracer) ) # bitand
      return tree
    elif rule == 30:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(123, tracer) ) # inline
      return tree
    elif rule == 32:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(7, tracer) ) # addeq
      return tree
    elif rule == 35:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(67, tracer) ) # add
      return tree
    elif rule == 37:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(24, tracer) ) # not
      return tree
    elif rule == 40:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(3, tracer) ) # sizeof
      return tree
    elif rule == 42:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(100, tracer) ) # bitor
      return tree
    elif rule == 43:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(50, tracer) ) # pound
      return tree
    elif rule == 55:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(79, tracer) ) # gteq
      return tree
    elif rule == 71:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(38, tracer) ) # struct
      return tree
    elif rule == 72:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(81, tracer) ) # restrict
      return tree
    elif rule == 74:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(75, tracer) ) # div
      return tree
    elif rule == 75:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(68, tracer) ) # bitxor
      return tree
    elif rule == 78:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(77, tracer) ) # semi
      return tree
    elif rule == 82:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(59, tracer) ) # tilde
      return tree
    elif rule == 84:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(109, tracer) ) # eq
      return tree
    elif rule == 92:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(69, tracer) ) # mod
      return tree
    elif rule == 94:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(12, tracer) ) # goto
      return tree
    elif rule == 98:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(121, tracer) ) # identifier
      return tree
    elif rule == 105:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(95, tracer) ) # or
      return tree
    elif rule == 112:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(18, tracer) ) # assign
      return tree
    elif rule == 114:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(116, tracer) ) # lteq
      return tree
    elif rule == 117:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(41, tracer) ) # union
      return tree
    elif rule == 120:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(73, tracer) ) # elipsis
      return tree
    elif rule == 121:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(36, tracer) ) # rbrace
      return tree
    elif rule == 123:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(127, tracer) ) # switch
      return tree
    elif rule == 132:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(89, tracer) ) # short
      return tree
    elif rule == 135:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(87, tracer) ) # decr
      return tree
    elif rule == 136:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(128, tracer) ) # lshifteq
      return tree
    elif rule == 137:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(32, tracer) ) # default
      return tree
    elif rule == 138:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(118, tracer) ) # unsigned
      return tree
    elif rule == 139:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(55, tracer) ) # gt
      return tree
    elif rule == 147:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(70, tracer) ) # auto
      return tree
    elif rule == 150:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(56, tracer) ) # typedef
      return tree
    elif rule == 155:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(0, tracer) ) # rshifteq
      return tree
    elif rule == 157:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(103, tracer) ) # neq
      return tree
    elif rule == 161:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(117, tracer) ) # for
      return tree
    elif rule == 176:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(25, tracer) ) # arrow
      return tree
    elif rule == 182:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(39, tracer) ) # volatile
      return tree
    elif rule == 190:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(27, tracer) ) # imaginary
      return tree
    elif rule == 200:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(10, tracer) ) # modeq
      return tree
    elif rule == 203:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(29, tracer) ) # comma
      return tree
    elif rule == 206:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(101, tracer) ) # float
      return tree
    elif rule == 219:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(43, tracer) ) # universal_character_name
      return tree
    elif rule == 224:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(65, tracer) ) # rshift
      return tree
    elif rule == 231:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(90, tracer) ) # else
      return tree
    elif rule == 234:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(20, tracer) ) # break
      return tree
    elif rule == 239:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(23, tracer) ) # return
      return tree
    elif rule == 248:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(46, tracer) ) # lparen
      return tree
    elif rule == 254:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(40, tracer) ) # lsquare
      return tree
    elif rule == 269:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(82, tracer) ) # colon
      return tree
    elif rule == 271:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(74, tracer) ) # register
      return tree
    elif rule == 278:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(94, tracer) ) # diveq
      return tree
    elif rule == 280:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(122, tracer) ) # bitandeq
      return tree
    elif rule == 286:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(9, tracer) ) # bool
      return tree
    elif rule == 291:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(37, tracer) ) # do
      return tree
    elif rule == 298:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(4, tracer) ) # subeq
      return tree
    elif rule == 301:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(22, tracer) ) # poundpound
      return tree
    elif rule == 304:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(49, tracer) ) # character_constant
      return tree
    elif rule == 314:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(33, tracer) ) # lbrace
      return tree
    elif rule == 317:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(63, tracer) ) # incr
      return tree
    elif rule == 321:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(78, tracer) ) # void
      return tree
    elif rule == 325:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(93, tracer) ) # int
      return tree
    elif rule == 328:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(16, tracer) ) # continue
      return tree
    elif rule == 345:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(28, tracer) ) # enum
      return tree
    elif rule == 350:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(97, tracer) ) # long
      return tree
    elif rule == 351:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(31, tracer) ) # dot
      return tree
    elif rule == 354:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(11, tracer) ) # complex
      return tree
    elif rule == 358:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(30, tracer) ) # char
      return tree
    elif rule == 362:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(88, tracer) ) # questionmark
      return tree
    elif rule == 365:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(5, tracer) ) # exclamation_point
      return tree
    elif rule == 368:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(61, tracer) ) # lshift
      return tree
    elif rule == 370:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(130, tracer) ) # const
      return tree
    elif rule == 380:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(106, tracer) ) # double
      return tree
    elif rule == 385:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(115, tracer) ) # integer_constant
      return tree
    elif rule == 387:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(26, tracer) ) # header_name
      return tree
    elif rule == 395:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(51, tracer) ) # rparen
      return tree
    elif rule == 397:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(52, tracer) ) # if
      return tree
    elif rule == 411:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(104, tracer) ) # case
      return tree
    elif rule == 412:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(17, tracer) ) # while
      return tree
    elif rule == 413:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(112, tracer) ) # signed
      return tree
    elif rule == 417:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(14, tracer) ) # muleq
      return tree
    elif rule == 423:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(48, tracer) ) # rsquare
      return tree
    elif rule == 424:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(53, tracer) ) # string_literal
      return tree
    elif rule == 429:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(57, tracer) ) # static
      return tree
    elif rule == 433:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(126, tracer) ) # lt
      return tree
    elif rule == 441:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(86, tracer) ) # extern
      return tree
    elif rule == 443:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(114, tracer) ) # bitoreq
      return tree
    elif rule == 446:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(84, tracer) ) # hexadecimal_floating_constant
      return tree
    elif rule == 447:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(72, tracer) ) # mul
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _TOKEN(self, depth = 0):
    rule = self.rule(193)
    if depth is not False:
      tracer = DebugTracer("_TOKEN", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(193, self.getAtomString(193)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 58:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(53, tracer) ) # string_literal
      return tree
    elif rule == 115:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(121, tracer) ) # identifier
      return tree
    elif rule == 119:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._KEYWORD(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 133:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._CONSTANT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 174:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(44, tracer) ) # pp_number
      return tree
    elif rule == 220:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PUNCTUATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _TRAILING_COMMA_OPT(self, depth = 0):
    rule = self.rule(214)
    if depth is not False:
      tracer = DebugTracer("_TRAILING_COMMA_OPT", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(214, self.getAtomString(214)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [36]):
      return tree
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 172:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(102, tracer) ) # trailing_comma
      return tree
    return tree
  def _TRANSLATION_UNIT(self, depth = 0):
    rule = self.rule(244)
    if depth is not False:
      tracer = DebugTracer("_TRANSLATION_UNIT", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(244, self.getAtomString(244)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 421:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN7(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _TYPE_NAME(self, depth = 0):
    rule = self.rule(171)
    if depth is not False:
      tracer = DebugTracer("_TYPE_NAME", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(171, self.getAtomString(171)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 54:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(93, tracer) ) # int
      return tree
    elif rule == 426:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(30, tracer) ) # char
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _TYPE_QUALIFIER(self, depth = 0):
    rule = self.rule(177)
    if depth is not False:
      tracer = DebugTracer("_TYPE_QUALIFIER", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(177, self.getAtomString(177)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 19:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(130, tracer) ) # const
      return tree
    elif rule == 20:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(81, tracer) ) # restrict
      return tree
    elif rule == 93:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(39, tracer) ) # volatile
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _TYPE_QUALIFIER_LIST_OPT(self, depth = 0):
    rule = self.rule(264)
    if depth is not False:
      tracer = DebugTracer("_TYPE_QUALIFIER_LIST_OPT", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(264, self.getAtomString(264)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [46, 121, 29, 57, 1, -1, 2, 254, 163]):
      return tree
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 202:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN25(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _TYPE_SPECIFIER(self, depth = 0):
    rule = self.rule(173)
    if depth is not False:
      tracer = DebugTracer("_TYPE_SPECIFIER", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(173, self.getAtomString(173)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 12:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(78, tracer) ) # void
      return tree
    elif rule == 24:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STRUCT_OR_UNION_SPECIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 50:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(112, tracer) ) # signed
      return tree
    elif rule == 62:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._ENUM_SPECIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 80:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._TYPEDEF_NAME(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 86:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(124, tracer) ) # _bool
      return tree
    elif rule == 103:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(101, tracer) ) # float
      return tree
    elif rule == 156:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(97, tracer) ) # long
      return tree
    elif rule == 160:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(118, tracer) ) # unsigned
      return tree
    elif rule == 342:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(106, tracer) ) # double
      return tree
    elif rule == 343:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(129, tracer) ) # _complex
      return tree
    elif rule == 378:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(30, tracer) ) # char
      return tree
    elif rule == 391:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(89, tracer) ) # short
      return tree
    elif rule == 410:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(93, tracer) ) # int
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _TYPEDEF_NAME(self, depth = 0):
    rule = self.rule(204)
    if depth is not False:
      tracer = DebugTracer("_TYPEDEF_NAME", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(204, self.getAtomString(204)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 262:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(71, tracer) ) # typedef_identifier
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _UNDEF_LINE(self, depth = 0):
    rule = self.rule(265)
    if depth is not False:
      tracer = DebugTracer("_UNDEF_LINE", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(265, self.getAtomString(265)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _VA_ARGS(self, depth = 0):
    rule = self.rule(237)
    if depth is not False:
      tracer = DebugTracer("_VA_ARGS", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(237, self.getAtomString(237)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 201:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(1, tracer) ) # comma_va_args
      tree.add( self.expect(73, tracer) ) # elipsis
      return tree
    return tree
  def _WARNING_LINE(self, depth = 0):
    rule = self.rule(238)
    if depth is not False:
      tracer = DebugTracer("_WARNING_LINE", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(238, self.getAtomString(238)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  infixBp0 = {
    0: 2000,
    4: 2000,
    7: 2000,
    10: 2000,
    14: 2000,
    18: 2000,
    25: 16000,
    29: 1000,
    31: 16000,
    33: 15000,
    40: 16000,
    45: 12000,
    46: 16000,
    55: 10000,
    60: 2000,
    61: 11000,
    63: 16000,
    65: 11000,
    67: 12000,
    68: 7000,
    69: 13000,
    72: 13000,
    75: 13000,
    79: 10000,
    87: 16000,
    88: 3000,
    92: 6000,
    94: 2000,
    95: 4000,
    99: 5000,
    100: 8000,
    103: 9000,
    109: 9000,
    114: 2000,
    116: 10000,
    122: 2000,
    126: 10000,
    128: 2000,
  }
  prefixBp0 = {
    24: 14000,
    45: 14000,
    63: 14000,
    72: 14000,
    87: 14000,
    92: 14000,
    96: 14000,
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
    tree = ParseTree( NonTerminal(194, '_expr') )
    if self.sym.getId() == 156: # constant
      tree.astTransform = AstTransformSubstitution(0)
      return self.expect( 156, tracer )
    elif self.sym.getId() == 194: # _expr
      tree.astTransform = AstTransformNodeCreator('PostIncr', {'var': 0})
      return self.expect( 194, tracer )
    elif self.sym.getId() == 121: # 'identifier'
      tree.astTransform = AstTransformNodeCreator('ArrayIndex', {'params': 2, 'name': 0})
      return self.expect( 121, tracer )
    elif self.sym.getId() == 46: # 'lparen'
      tree.astTransform = AstTransformSubstitution(2)
      tree.add( self.expect(46, tracer) )
      tree.add( self.__EXPR() )
      tree.add( self.expect(51, tracer) )
    elif self.sym.getId() == 72: # 'mul'
      tree.astTransform = AstTransformNodeCreator('Dereference', {'var': 1})
      tree.add( self.expect(72, tracer) )
      tree.add( self.__EXPR( self.prefixBp0[72] ) )
      tree.isPrefix = True
    elif self.sym.getId() == 87: # 'decr'
      tree.astTransform = AstTransformNodeCreator('PreDecr', {'var': 1})
      tree.add( self.expect(87, tracer) )
      tree.add( self.__EXPR( self.prefixBp0[87] ) )
      tree.isPrefix = True
    elif self.sym.getId() == 35: # 'lparen_cast'
      tree.astTransform = AstTransformNodeCreator('TypeInitializion', {'type': 1, 'initializer': 4})
      tree.add( self.expect(35, tracer) )
      tree.add( self._TYPE_NAME() )
      tree.add( self.expect(51, tracer) )
    elif self.sym.getId() == 63: # 'incr'
      tree.astTransform = AstTransformNodeCreator('PreIncr', {'var': 1})
      tree.add( self.expect(63, tracer) )
      tree.add( self.__EXPR( self.prefixBp0[63] ) )
      tree.isPrefix = True
    elif self.sym.getId() == 3: # 'sizeof'
      tree.astTransform = AstTransformNodeCreator('SizeOf', {'var': 1})
      return self.expect( 3, tracer )
    elif self.sym.getId() == 92: # 'bitand'
      tree.astTransform = AstTransformNodeCreator('AddressOf', {'var': 1})
      tree.add( self.expect(92, tracer) )
      tree.add( self.__EXPR( self.prefixBp0[92] ) )
      tree.isPrefix = True
    elif self.sym.getId() == 53: # 'string_literal'
      tree.astTransform = AstTransformSubstitution(0)
      return self.expect( 53, tracer )
    return tree
  def led0(self, left, tracer):
    tree = ParseTree( NonTerminal(194, '_expr') )
    if  self.sym.getId() == 69: # 'mod'
      tree.astTransform = AstTransformNodeCreator('Mod', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(69, tracer) )
      tree.add( self.__EXPR( self.infixBp0[69] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 10: # 'modeq'
      tree.astTransform = AstTransformNodeCreator('ModAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(10, tracer) )
      tree.add( self.__EXPR( self.infixBp0[10] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 55: # 'gt'
      tree.astTransform = AstTransformNodeCreator('GreaterThan', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(55, tracer) )
      tree.add( self.__EXPR( self.infixBp0[55] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 100: # 'bitor'
      tree.astTransform = AstTransformNodeCreator('BitOR', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(100, tracer) )
      tree.add( self.__EXPR( self.infixBp0[100] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 63: # 'incr'
      tree.astTransform = AstTransformNodeCreator('PostIncr', {'var': 0})
      if left:
        tree.add(left)
      return self.expect( 63, tracer )
    elif  self.sym.getId() == 92: # 'bitand'
      tree.astTransform = AstTransformNodeCreator('BitAND', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(92, tracer) )
      tree.add( self.__EXPR( self.infixBp0[92] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 122: # 'bitandeq'
      tree.astTransform = AstTransformNodeCreator('ANDAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(122, tracer) )
      tree.add( self.__EXPR( self.infixBp0[122] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 109: # 'eq'
      tree.astTransform = AstTransformNodeCreator('Equals', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(109, tracer) )
      tree.add( self.__EXPR( self.infixBp0[109] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 68: # 'bitxor'
      tree.astTransform = AstTransformNodeCreator('BitXOR', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(68, tracer) )
      tree.add( self.__EXPR( self.infixBp0[68] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 116: # 'lteq'
      tree.astTransform = AstTransformNodeCreator('LessThanEq', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(116, tracer) )
      tree.add( self.__EXPR( self.infixBp0[116] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 40: # 'lsquare'
      tree.astTransform = AstTransformNodeCreator('ArrayIndex', {'params': 2, 'name': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(40, tracer) )
      tree.add( self.__GEN5() )
      tree.add( self.expect(48, tracer) )
    elif  self.sym.getId() == 114: # 'bitoreq'
      tree.astTransform = AstTransformNodeCreator('ORAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(114, tracer) )
      tree.add( self.__EXPR( self.infixBp0[114] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 14: # 'muleq'
      tree.astTransform = AstTransformNodeCreator('MultiplyAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(14, tracer) )
      tree.add( self.__EXPR( self.infixBp0[14] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 7: # 'addeq'
      tree.astTransform = AstTransformNodeCreator('AddAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(7, tracer) )
      tree.add( self.__EXPR( self.infixBp0[7] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 33: # 'lbrace'
      tree.astTransform = AstTransformNodeCreator('TypeInitializion', {'type': 1, 'initializer': 4})
      if left:
        tree.add(left)
      tree.add( self.expect(33, tracer) )
      tree.add( self.__GEN13() )
      tree.add( self._TRAILING_COMMA_OPT() )
      tree.add( self.expect(36, tracer) )
    elif  self.sym.getId() == 18: # 'assign'
      tree.astTransform = AstTransformNodeCreator('Assign', {'var': 0, 'value': 2})
      if left:
        tree.add(left)
      tree.add( self.expect(18, tracer) )
      tree.add( self.__EXPR( self.infixBp0[18] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 60: # 'bitxoreq'
      tree.astTransform = AstTransformNodeCreator('XORAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(60, tracer) )
      tree.add( self.__EXPR( self.infixBp0[60] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 79: # 'gteq'
      tree.astTransform = AstTransformNodeCreator('GreaterThanEq', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(79, tracer) )
      tree.add( self.__EXPR( self.infixBp0[79] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 4: # 'subeq'
      tree.astTransform = AstTransformNodeCreator('SubtractAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(4, tracer) )
      tree.add( self.__EXPR( self.infixBp0[4] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 67: # 'add'
      tree.astTransform = AstTransformNodeCreator('Add', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(67, tracer) )
      tree.add( self.__EXPR( self.infixBp0[67] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 42: # 'sizeof_separator'
      tree.astTransform = AstTransformNodeCreator('SizeOf', {'var': 1})
      if left:
        tree.add(left)
      tree.add( self.expect(42, tracer) )
      tree.add( self._SIZEOF_BODY() )
    elif  self.sym.getId() == 31: # 'dot'
      tree.astTransform = AstTransformNodeCreator('MemberSelect', {'member': 2, 'object': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(31, tracer) )
      tree.add( self.__EXPR() )
    elif  self.sym.getId() == 29: # 'comma'
      tree.astTransform = AstTransformNodeCreator('Comma', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(29, tracer) )
      tree.add( self.__EXPR( self.infixBp0[29] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 72: # 'mul'
      tree.astTransform = AstTransformNodeCreator('Mul', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(72, tracer) )
      tree.add( self.__EXPR( self.infixBp0[72] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 0: # 'rshifteq'
      tree.astTransform = AstTransformNodeCreator('RightShiftAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(0, tracer) )
      tree.add( self.__EXPR( self.infixBp0[0] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 45: # 'sub'
      tree.astTransform = AstTransformNodeCreator('Sub', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(45, tracer) )
      tree.add( self.__EXPR( self.infixBp0[45] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 46: # 'lparen'
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(46, tracer) )
      tree.add( self.__GEN5() )
      tree.add( self.expect(51, tracer) )
    elif  self.sym.getId() == 25: # 'arrow'
      tree.astTransform = AstTransformNodeCreator('DerefMemberSelect', {'member': 2, 'object': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(25, tracer) )
      tree.add( self.__EXPR() )
    elif  self.sym.getId() == 61: # 'lshift'
      tree.astTransform = AstTransformNodeCreator('LeftShift', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(61, tracer) )
      tree.add( self.__EXPR( self.infixBp0[61] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 75: # 'div'
      tree.astTransform = AstTransformNodeCreator('Div', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(75, tracer) )
      tree.add( self.__EXPR( self.infixBp0[75] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 126: # 'lt'
      tree.astTransform = AstTransformNodeCreator('LessThan', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(126, tracer) )
      tree.add( self.__EXPR( self.infixBp0[126] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 128: # 'lshifteq'
      tree.astTransform = AstTransformNodeCreator('LeftShiftAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(128, tracer) )
      tree.add( self.__EXPR( self.infixBp0[128] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 88: # 'questionmark'
      tree.astTransform = AstTransformNodeCreator('TernaryOperator', {'true': 2, 'false': 4, 'cond': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(88, tracer) )
      tree.add( self.__EXPR() )
      tree.add( self.expect(82, tracer) )
      tree.add( self.__EXPR() )
    elif  self.sym.getId() == 94: # 'diveq'
      tree.astTransform = AstTransformNodeCreator('DivideAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(94, tracer) )
      tree.add( self.__EXPR( self.infixBp0[94] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 87: # 'decr'
      tree.astTransform = AstTransformNodeCreator('PostDecr', {'var': 0})
      if left:
        tree.add(left)
      return self.expect( 87, tracer )
    elif  self.sym.getId() == 65: # 'rshift'
      tree.astTransform = AstTransformNodeCreator('RightShift', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(65, tracer) )
      tree.add( self.__EXPR( self.infixBp0[65] ) )
      tree.isInfix = True
    return tree
  infixBp1 = {
    40: 1000,
    46: 1000,
  }
  prefixBp1 = {
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
    tree = ParseTree( NonTerminal(186, '_direct_abstract_declarator') )
    if self.sym.getId() == 163: # direct_abstract_declarator_opt
      tree.astTransform = AstTransformSubstitution(0)
      return self.expect( 163, tracer )
    elif self.sym.getId() == 46: # 'lparen'
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(46, tracer) )
      tree.add( self._ABSTRACT_DECLARATOR() )
      tree.add( self.expect(51, tracer) )
    return tree
  def led1(self, left, tracer):
    tree = ParseTree( NonTerminal(186, '_direct_abstract_declarator') )
    if  self.sym.getId() == 40: # 'lsquare'
      tree.astTransform = AstTransformSubstitution(0)
      if left:
        tree.add(left)
      tree.add( self.expect(40, tracer) )
      tree.add( self._DIRECT_ABSTRACT_DECLARATOR_EXPR() )
      tree.add( self.expect(48, tracer) )
    elif  self.sym.getId() == 46: # 'lparen'
      tree.astTransform = AstTransformSubstitution(0)
      if left:
        tree.add(left)
      tree.add( self.expect(46, tracer) )
      tree.add( self._PARAMETER_TYPE_LIST_OPT() )
      tree.add( self.expect(51, tracer) )
    return tree
  infixBp2 = {
    40: 1000,
    46: 1000,
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
    tree = ParseTree( NonTerminal(254, '_direct_declarator') )
    if self.sym.getId() == 254: # _direct_declarator
      tree.astTransform = AstTransformSubstitution(0)
      return self.expect( 254, tracer )
    elif self.sym.getId() == 121: # 'identifier'
      tree.astTransform = AstTransformSubstitution(0)
      return self.expect( 121, tracer )
    elif self.sym.getId() == 46: # 'lparen'
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(46, tracer) )
      tree.add( self._DECLARATOR() )
      tree.add( self.expect(51, tracer) )
    return tree
  def led2(self, left, tracer):
    tree = ParseTree( NonTerminal(254, '_direct_declarator') )
    if  self.sym.getId() == 40: # 'lsquare'
      tree.astTransform = AstTransformSubstitution(0)
      if left:
        tree.add(left)
      tree.add( self.expect(40, tracer) )
      tree.add( self._DIRECT_DECLARATOR_EXPR() )
      tree.add( self.expect(48, tracer) )
    elif  self.sym.getId() == 46: # 'lparen'
      tree.astTransform = AstTransformSubstitution(0)
      if left:
        tree.add(left)
      tree.add( self.expect(46, tracer) )
      tree.add( self._DIRECT_DECLARATOR_PARAMETER_LIST() )
      tree.add( self.expect(51, tracer) )
    return tree
