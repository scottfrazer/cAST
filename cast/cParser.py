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
class Parser:
  def __init__(self):
    self.iterator = None
    self.sym = None
  TERMINAL_UNDEF = 0
  TERMINAL_ARROW = 1
  TERMINAL_SUB = 2
  TERMINAL_STRING_LITERAL = 3
  TERMINAL_HEADER_GLOBAL = 4
  TERMINAL_COMMA = 5
  TERMINAL_DO = 6
  TERMINAL_LINE = 7
  TERMINAL_ENUMERATION_CONSTANT = 8
  TERMINAL_FOR = 9
  TERMINAL_DEFINED_SEPARATOR = 10
  TERMINAL_RSHIFTEQ = 11
  TERMINAL_ELSE_IF = 12
  TERMINAL_TRAILING_COMMA = 13
  TERMINAL_STRUCT = 14
  TERMINAL_FLOATING_CONSTANT = 15
  TERMINAL_TYPEDEF = 16
  TERMINAL_NUMBER = 17
  TERMINAL_RBRACE = 18
  TERMINAL_SIZEOF = 19
  TERMINAL_EXTERN = 20
  TERMINAL_UNION = 21
  TERMINAL_NEQ = 22
  TERMINAL_STATIC = 23
  TERMINAL_SEPARATOR = 24
  TERMINAL_EQUALS = 25
  TERMINAL_SIGNED = 26
  TERMINAL_AUTO = 27
  TERMINAL_DECLARATOR_HINT = 28
  TERMINAL_REGISTER = 29
  TERMINAL_CONTINUE = 30
  TERMINAL_ASTERISK = 31
  TERMINAL_VOID = 32
  TERMINAL_FUNCTION_HINT = 33
  TERMINAL_BREAK = 34
  TERMINAL_CSOURCE = 35
  TERMINAL_DEFINED = 36
  TERMINAL_CHAR = 37
  TERMINAL_ENUM = 38
  TERMINAL_RETURN = 39
  TERMINAL_QUESTIONMARK = 40
  TERMINAL_SHORT = 41
  TERMINAL_LPAREN_CAST = 42
  TERMINAL_GOTO = 43
  TERMINAL_INT = 44
  TERMINAL_IMAGINARY = 45
  TERMINAL_UNSIGNED = 46
  TERMINAL_LONG = 47
  TERMINAL__DIRECT_ABSTRACT_DECLARATOR = 48
  TERMINAL_PRAGMA = 49
  TERMINAL__DIRECT_DECLARATOR = 50
  TERMINAL__IMAGINARY = 51
  TERMINAL_ENDIF = 52
  TERMINAL_NOT = 53
  TERMINAL_CASE = 54
  TERMINAL_DOUBLE = 55
  TERMINAL_IF = 56
  TERMINAL_DEFAULT = 57
  TERMINAL_DEFINE_FUNCTION = 58
  TERMINAL_LSHIFT = 59
  TERMINAL_IDENTIFIER = 60
  TERMINAL_SUBEQ = 61
  TERMINAL_IFDEF = 62
  TERMINAL_GT = 63
  TERMINAL_RSHIFT = 64
  TERMINAL_ADDEQ = 65
  TERMINAL_IFNDEF = 66
  TERMINAL__BOOL = 67
  TERMINAL_MODEQ = 68
  TERMINAL_ADD = 69
  TERMINAL_MOD = 70
  TERMINAL_DEFINE = 71
  TERMINAL__COMPLEX = 72
  TERMINAL__EXPR = 73
  TERMINAL_COMPLEX = 74
  TERMINAL_MULEQ = 75
  TERMINAL_ELSE = 76
  TERMINAL_COMMA_VA_ARGS = 77
  TERMINAL_DIVEQ = 78
  TERMINAL_DIV = 79
  TERMINAL_COLON = 80
  TERMINAL_ASSIGN = 81
  TERMINAL_AMPERSAND = 82
  TERMINAL_ELIF = 83
  TERMINAL_PP_NUMBER = 84
  TERMINAL_BOOL = 85
  TERMINAL_LPAREN = 86
  TERMINAL_POUNDPOUND = 87
  TERMINAL_DECR = 88
  TERMINAL_SIZEOF_SEPARATOR = 89
  TERMINAL_TYPEDEF_IDENTIFIER = 90
  TERMINAL_POUND = 91
  TERMINAL_INCR = 92
  TERMINAL_GTEQ = 93
  TERMINAL_BITNOT = 94
  TERMINAL_CONST = 95
  TERMINAL_DOT = 96
  TERMINAL_OR = 97
  TERMINAL_ELIPSIS = 98
  TERMINAL_TILDE = 99
  TERMINAL_BITOR = 100
  TERMINAL_FLOAT = 101
  TERMINAL_RESTRICT = 102
  TERMINAL_UNIVERSAL_CHARACTER_NAME = 103
  TERMINAL_AND = 104
  TERMINAL_INTEGER_CONSTANT = 105
  TERMINAL_BITXOR = 106
  TERMINAL_VOLATILE = 107
  TERMINAL_HEADER_LOCAL = 108
  TERMINAL_HEADER_NAME = 109
  TERMINAL_EXCLAMATION_POINT = 110
  TERMINAL_BITOREQ = 111
  TERMINAL_BITAND = 112
  TERMINAL_LSQUARE = 113
  TERMINAL_EQ = 114
  TERMINAL_MUL = 115
  TERMINAL_DECIMAL_FLOATING_CONSTANT = 116
  TERMINAL_BITXOREQ = 117
  TERMINAL_RPAREN = 118
  TERMINAL_INCLUDE = 119
  TERMINAL_LTEQ = 120
  TERMINAL_ERROR = 121
  TERMINAL_RSQUARE = 122
  TERMINAL_BITANDEQ = 123
  TERMINAL_HEXADECIMAL_FLOATING_CONSTANT = 124
  TERMINAL_LT = 125
  TERMINAL_SWITCH = 126
  TERMINAL_INLINE = 127
  TERMINAL_WARNING = 128
  TERMINAL_LSHIFTEQ = 129
  TERMINAL_LBRACE = 130
  TERMINAL_CHARACTER_CONSTANT = 131
  TERMINAL_WHILE = 132
  TERMINAL_SEMI = 133
  terminal_str = {
    0: 'undef',
    1: 'arrow',
    2: 'sub',
    3: 'string_literal',
    4: 'header_global',
    5: 'comma',
    6: 'do',
    7: 'line',
    8: 'enumeration_constant',
    9: 'for',
    10: 'defined_separator',
    11: 'rshifteq',
    12: 'else_if',
    13: 'trailing_comma',
    14: 'struct',
    15: 'floating_constant',
    16: 'typedef',
    17: 'number',
    18: 'rbrace',
    19: 'sizeof',
    20: 'extern',
    21: 'union',
    22: 'neq',
    23: 'static',
    24: 'separator',
    25: 'equals',
    26: 'signed',
    27: 'auto',
    28: 'declarator_hint',
    29: 'register',
    30: 'continue',
    31: 'asterisk',
    32: 'void',
    33: 'function_hint',
    34: 'break',
    35: 'csource',
    36: 'defined',
    37: 'char',
    38: 'enum',
    39: 'return',
    40: 'questionmark',
    41: 'short',
    42: 'lparen_cast',
    43: 'goto',
    44: 'int',
    45: 'imaginary',
    46: 'unsigned',
    47: 'long',
    48: '_direct_abstract_declarator',
    49: 'pragma',
    50: '_direct_declarator',
    51: '_imaginary',
    52: 'endif',
    53: 'not',
    54: 'case',
    55: 'double',
    56: 'if',
    57: 'default',
    58: 'define_function',
    59: 'lshift',
    60: 'identifier',
    61: 'subeq',
    62: 'ifdef',
    63: 'gt',
    64: 'rshift',
    65: 'addeq',
    66: 'ifndef',
    67: '_bool',
    68: 'modeq',
    69: 'add',
    70: 'mod',
    71: 'define',
    72: '_complex',
    73: '_expr',
    74: 'complex',
    75: 'muleq',
    76: 'else',
    77: 'comma_va_args',
    78: 'diveq',
    79: 'div',
    80: 'colon',
    81: 'assign',
    82: 'ampersand',
    83: 'elif',
    84: 'pp_number',
    85: 'bool',
    86: 'lparen',
    87: 'poundpound',
    88: 'decr',
    89: 'sizeof_separator',
    90: 'typedef_identifier',
    91: 'pound',
    92: 'incr',
    93: 'gteq',
    94: 'bitnot',
    95: 'const',
    96: 'dot',
    97: 'or',
    98: 'elipsis',
    99: 'tilde',
    100: 'bitor',
    101: 'float',
    102: 'restrict',
    103: 'universal_character_name',
    104: 'and',
    105: 'integer_constant',
    106: 'bitxor',
    107: 'volatile',
    108: 'header_local',
    109: 'header_name',
    110: 'exclamation_point',
    111: 'bitoreq',
    112: 'bitand',
    113: 'lsquare',
    114: 'eq',
    115: 'mul',
    116: 'decimal_floating_constant',
    117: 'bitxoreq',
    118: 'rparen',
    119: 'include',
    120: 'lteq',
    121: 'error',
    122: 'rsquare',
    123: 'bitandeq',
    124: 'hexadecimal_floating_constant',
    125: 'lt',
    126: 'switch',
    127: 'inline',
    128: 'warning',
    129: 'lshifteq',
    130: 'lbrace',
    131: 'character_constant',
    132: 'while',
    133: 'semi',
  }
  nonterminal_str = {
    134: 'type_specifier',
    135: 'external_declaration',
    136: '_gen7',
    137: '_direct_declarator',
    138: 'constant',
    139: 'specifier_qualifier_list',
    140: '_direct_abstract_declarator',
    141: '_gen14',
    142: 'for_cond',
    143: 'type_qualifier_list_opt',
    144: 'sizeof_body',
    145: 'pp_file',
    146: 'elipsis_opt',
    147: '_gen8',
    148: '_gen27',
    149: 'init_declarator',
    150: '_gen9',
    151: '_gen5',
    152: '_gen26',
    153: '_gen6',
    154: 'type_name',
    155: 'typedef_name',
    156: '_gen20',
    157: 'external_declaration_sub',
    158: 'pp_directive',
    159: 'designator',
    160: 'statement',
    161: 'token',
    162: 'else_statement_opt',
    163: 'function_definition',
    164: '_gen0',
    165: 'type_qualifier',
    166: 'initializer',
    167: 'terminals',
    168: 'struct_declarator_body',
    169: 'declarator_initializer',
    170: '_gen25',
    171: 'labeled_statement',
    172: '_gen29',
    173: 'init_declarator_list_opt',
    174: 'declarator',
    175: 'pp',
    176: 'compound_statement',
    177: 'parameter_type_list_opt',
    178: 'parameter_declaration_sub_sub',
    179: 'initializer_list_item',
    180: '_gen13',
    181: '_gen23',
    182: 'error_line',
    183: 'parameter_declaration',
    184: 'pointer_opt',
    185: '_gen10',
    186: 'else_statement',
    187: '_gen28',
    188: 'parameter_declaration_sub',
    189: 'control_line',
    190: 'storage_class_specifier',
    191: '_gen15',
    192: 'enum_specifier_sub',
    193: 'direct_declarator_modifier',
    194: 'if_part',
    195: 'elseif_part',
    196: 'pp_tokens',
    197: '_gen1',
    198: 'jump_statement',
    199: 'direct_declarator_modifier_list_opt',
    200: 'enum_specifier_body',
    201: 'keyword',
    202: 'iteration_statement',
    203: 'designation',
    204: 'direct_declarator_size',
    205: 'struct_declaration',
    206: 'abstract_declarator',
    207: 'pp_nodes',
    208: 'direct_declarator_parameter_list',
    209: '_expr',
    210: '_gen19',
    211: 'va_args',
    212: 'enumerator',
    213: 'for_incr',
    214: 'block_item_list_opt',
    215: 'else_if_statement_opt',
    216: '_gen24',
    217: 'define_func_param',
    218: 'function_specifier',
    219: '_gen31',
    220: '_gen2',
    221: 'pragma_line',
    222: '_gen3',
    223: 'direct_declarator_expr',
    224: 'designation_opt',
    225: 'declaration',
    226: 'struct_declarator',
    227: 'parameter_type_list',
    228: 'enumerator_assignment',
    229: 'struct_or_union_specifier',
    230: 'declaration_specifier',
    231: 'trailing_comma_opt',
    232: '_gen22',
    233: 'enum_specifier',
    234: 'include_line',
    235: 'expression_opt',
    236: 'punctuator',
    237: 'define_line',
    238: 'defined_identifier',
    239: 'struct_or_union',
    240: '_gen12',
    241: 'struct_or_union_sub',
    242: 'for_init',
    243: '_gen21',
    244: 'else_if_statement',
    245: 'identifier',
    246: 'pp_nodes_list',
    247: 'struct_or_union_body',
    248: 'block_item',
    249: 'else_part',
    250: 'warning_line',
    251: 'declaration_list_opt',
    252: 'direct_abstract_declarator_opt',
    253: 'static_opt',
    254: 'undef_line',
    255: 'replacement_list',
    256: '_gen18',
    257: '_gen4',
    258: 'line_line',
    259: 'selection_statement',
    260: 'enumeration_constant',
    261: 'pointer',
    262: 'if_section',
    263: 'direct_abstract_declarator_expr',
    264: '_gen17',
    265: 'include_type',
    266: '_gen16',
    267: 'expression_statement',
    268: 'pointer_sub',
    269: '_gen30',
    270: 'translation_unit',
    271: '_gen11',
  }
  str_terminal = {
    'undef': 0,
    'arrow': 1,
    'sub': 2,
    'string_literal': 3,
    'header_global': 4,
    'comma': 5,
    'do': 6,
    'line': 7,
    'enumeration_constant': 8,
    'for': 9,
    'defined_separator': 10,
    'rshifteq': 11,
    'else_if': 12,
    'trailing_comma': 13,
    'struct': 14,
    'floating_constant': 15,
    'typedef': 16,
    'number': 17,
    'rbrace': 18,
    'sizeof': 19,
    'extern': 20,
    'union': 21,
    'neq': 22,
    'static': 23,
    'separator': 24,
    'equals': 25,
    'signed': 26,
    'auto': 27,
    'declarator_hint': 28,
    'register': 29,
    'continue': 30,
    'asterisk': 31,
    'void': 32,
    'function_hint': 33,
    'break': 34,
    'csource': 35,
    'defined': 36,
    'char': 37,
    'enum': 38,
    'return': 39,
    'questionmark': 40,
    'short': 41,
    'lparen_cast': 42,
    'goto': 43,
    'int': 44,
    'imaginary': 45,
    'unsigned': 46,
    'long': 47,
    '_direct_abstract_declarator': 48,
    'pragma': 49,
    '_direct_declarator': 50,
    '_imaginary': 51,
    'endif': 52,
    'not': 53,
    'case': 54,
    'double': 55,
    'if': 56,
    'default': 57,
    'define_function': 58,
    'lshift': 59,
    'identifier': 60,
    'subeq': 61,
    'ifdef': 62,
    'gt': 63,
    'rshift': 64,
    'addeq': 65,
    'ifndef': 66,
    '_bool': 67,
    'modeq': 68,
    'add': 69,
    'mod': 70,
    'define': 71,
    '_complex': 72,
    '_expr': 73,
    'complex': 74,
    'muleq': 75,
    'else': 76,
    'comma_va_args': 77,
    'diveq': 78,
    'div': 79,
    'colon': 80,
    'assign': 81,
    'ampersand': 82,
    'elif': 83,
    'pp_number': 84,
    'bool': 85,
    'lparen': 86,
    'poundpound': 87,
    'decr': 88,
    'sizeof_separator': 89,
    'typedef_identifier': 90,
    'pound': 91,
    'incr': 92,
    'gteq': 93,
    'bitnot': 94,
    'const': 95,
    'dot': 96,
    'or': 97,
    'elipsis': 98,
    'tilde': 99,
    'bitor': 100,
    'float': 101,
    'restrict': 102,
    'universal_character_name': 103,
    'and': 104,
    'integer_constant': 105,
    'bitxor': 106,
    'volatile': 107,
    'header_local': 108,
    'header_name': 109,
    'exclamation_point': 110,
    'bitoreq': 111,
    'bitand': 112,
    'lsquare': 113,
    'eq': 114,
    'mul': 115,
    'decimal_floating_constant': 116,
    'bitxoreq': 117,
    'rparen': 118,
    'include': 119,
    'lteq': 120,
    'error': 121,
    'rsquare': 122,
    'bitandeq': 123,
    'hexadecimal_floating_constant': 124,
    'lt': 125,
    'switch': 126,
    'inline': 127,
    'warning': 128,
    'lshifteq': 129,
    'lbrace': 130,
    'character_constant': 131,
    'while': 132,
    'semi': 133,
  }
  str_nonterminal = {
    'type_specifier': 134,
    'external_declaration': 135,
    '_gen7': 136,
    '_direct_declarator': 137,
    'constant': 138,
    'specifier_qualifier_list': 139,
    '_direct_abstract_declarator': 140,
    '_gen14': 141,
    'for_cond': 142,
    'type_qualifier_list_opt': 143,
    'sizeof_body': 144,
    'pp_file': 145,
    'elipsis_opt': 146,
    '_gen8': 147,
    '_gen27': 148,
    'init_declarator': 149,
    '_gen9': 150,
    '_gen5': 151,
    '_gen26': 152,
    '_gen6': 153,
    'type_name': 154,
    'typedef_name': 155,
    '_gen20': 156,
    'external_declaration_sub': 157,
    'pp_directive': 158,
    'designator': 159,
    'statement': 160,
    'token': 161,
    'else_statement_opt': 162,
    'function_definition': 163,
    '_gen0': 164,
    'type_qualifier': 165,
    'initializer': 166,
    'terminals': 167,
    'struct_declarator_body': 168,
    'declarator_initializer': 169,
    '_gen25': 170,
    'labeled_statement': 171,
    '_gen29': 172,
    'init_declarator_list_opt': 173,
    'declarator': 174,
    'pp': 175,
    'compound_statement': 176,
    'parameter_type_list_opt': 177,
    'parameter_declaration_sub_sub': 178,
    'initializer_list_item': 179,
    '_gen13': 180,
    '_gen23': 181,
    'error_line': 182,
    'parameter_declaration': 183,
    'pointer_opt': 184,
    '_gen10': 185,
    'else_statement': 186,
    '_gen28': 187,
    'parameter_declaration_sub': 188,
    'control_line': 189,
    'storage_class_specifier': 190,
    '_gen15': 191,
    'enum_specifier_sub': 192,
    'direct_declarator_modifier': 193,
    'if_part': 194,
    'elseif_part': 195,
    'pp_tokens': 196,
    '_gen1': 197,
    'jump_statement': 198,
    'direct_declarator_modifier_list_opt': 199,
    'enum_specifier_body': 200,
    'keyword': 201,
    'iteration_statement': 202,
    'designation': 203,
    'direct_declarator_size': 204,
    'struct_declaration': 205,
    'abstract_declarator': 206,
    'pp_nodes': 207,
    'direct_declarator_parameter_list': 208,
    '_expr': 209,
    '_gen19': 210,
    'va_args': 211,
    'enumerator': 212,
    'for_incr': 213,
    'block_item_list_opt': 214,
    'else_if_statement_opt': 215,
    '_gen24': 216,
    'define_func_param': 217,
    'function_specifier': 218,
    '_gen31': 219,
    '_gen2': 220,
    'pragma_line': 221,
    '_gen3': 222,
    'direct_declarator_expr': 223,
    'designation_opt': 224,
    'declaration': 225,
    'struct_declarator': 226,
    'parameter_type_list': 227,
    'enumerator_assignment': 228,
    'struct_or_union_specifier': 229,
    'declaration_specifier': 230,
    'trailing_comma_opt': 231,
    '_gen22': 232,
    'enum_specifier': 233,
    'include_line': 234,
    'expression_opt': 235,
    'punctuator': 236,
    'define_line': 237,
    'defined_identifier': 238,
    'struct_or_union': 239,
    '_gen12': 240,
    'struct_or_union_sub': 241,
    'for_init': 242,
    '_gen21': 243,
    'else_if_statement': 244,
    'identifier': 245,
    'pp_nodes_list': 246,
    'struct_or_union_body': 247,
    'block_item': 248,
    'else_part': 249,
    'warning_line': 250,
    'declaration_list_opt': 251,
    'direct_abstract_declarator_opt': 252,
    'static_opt': 253,
    'undef_line': 254,
    'replacement_list': 255,
    '_gen18': 256,
    '_gen4': 257,
    'line_line': 258,
    'selection_statement': 259,
    'enumeration_constant': 260,
    'pointer': 261,
    'if_section': 262,
    'direct_abstract_declarator_expr': 263,
    '_gen17': 264,
    'include_type': 265,
    '_gen16': 266,
    'expression_statement': 267,
    'pointer_sub': 268,
    '_gen30': 269,
    'translation_unit': 270,
    '_gen11': 271,
  }
  terminal_count = 134
  nonterminal_count = 138
  parse_table = [
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 86, -1, -1, -1, -1, -1, -1, 86, -1, -1, -1, -1, 396, -1, -1, -1, -1, -1, 252, -1, -1, -1, -1, 241, 74, -1, -1, 268, -1, -1, 344, -1, 343, 152, -1, -1, -1, -1, -1, -1, -1, 378, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 222, -1, -1, -1, -1, 187, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 418, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 185, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 220, -1, 220, -1, -1, -1, 220, 220, -1, 220, -1, -1, 220, 220, -1, 220, -1, -1, 220, -1, -1, -1, -1, 220, 220, -1, -1, 220, -1, -1, 220, -1, 220, 220, -1, -1, -1, -1, -1, -1, -1, 220, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 220, -1, -1, -1, -1, 220, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 220, -1, -1, -1, -1, 220, -1, -1, -1, -1, -1, 220, 220, -1, -1, -1, -1, 220, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 220, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 7, -1, 7, -1, -1, -1, 7, 7, -1, 7, -1, -1, 7, 7, -1, 7, -1, -1, 7, -1, -1, -1, -1, 7, 7, -1, -1, 7, -1, -1, 7, -1, 7, 7, -1, -1, -1, -1, -1, -1, -1, 7, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 7, -1, -1, -1, -1, 7, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 7, -1, -1, -1, -1, 7, -1, -1, -1, -1, -1, 7, 7, -1, -1, -1, -1, 7, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 7, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, 79, -1, -1, -1, -1, -1, -1, 434, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 437, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 289, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 197, -1, -1, -1, -1, -1, -1, 197, -1, -1, -1, -1, 197, -1, -1, -1, -1, -1, 197, -1, -1, -1, -1, 197, 197, -1, -1, 197, -1, -1, 197, -1, 197, 197, -1, -1, -1, -1, -1, -1, -1, 197, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 197, -1, -1, -1, -1, 197, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 197, -1, -1, -1, -1, 402, -1, -1, -1, -1, -1, 197, 402, -1, -1, -1, -1, 402, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, 52, -1, -1, -1, -1, -1, -1, -1, 75, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 115],
    [-1, -1, -1, -1, -1, 11, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 11, -1, -1, -1, -1, -1, -1, -1, 11, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 11, -1, 11, -1, -1, -1, -1, -1, -1, -1, -1, -1, 11, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 11, -1, -1, -1, -1, -1, -1, -1, -1, 11, -1, -1, -1, -1, -1, -1, -1, -1, 11, -1, -1, -1, -1, -1, -1, 11, -1, -1, -1, -1, 11, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 244, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 414, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 25, -1, 25, -1, -1, -1, 25, 25, -1, 25, -1, -1, 25, 25, -1, 25, -1, -1, 25, -1, -1, -1, -1, 25, 25, -1, -1, 25, -1, -1, 25, -1, 25, 25, -1, -1, -1, -1, -1, -1, -1, 25, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 25, -1, -1, -1, -1, 25, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 25, -1, -1, -1, -1, 25, -1, -1, -1, -1, -1, 25, 25, -1, -1, -1, -1, 25, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 25, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 292, -1, 292, -1, -1, -1, 292, 292, -1, 292, -1, -1, 292, 292, -1, 292, -1, -1, 292, -1, -1, -1, -1, 292, 292, -1, -1, 292, -1, -1, 292, -1, 292, 292, -1, -1, -1, -1, -1, -1, -1, 292, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 292, -1, -1, -1, -1, 292, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 292, -1, -1, -1, -1, 292, -1, -1, -1, -1, -1, 292, 292, -1, -1, -1, -1, 292, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 292, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 219, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 219, -1, -1, -1, -1, -1, -1, -1, -1, -1, 219, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 219, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, 31, -1, -1, -1, -1, -1, -1, -1, -1, 28, -1, 28, -1, -1, -1, 28, 28, -1, 28, -1, -1, 28, 28, 31, 28, -1, 31, 28, 31, -1, -1, -1, 28, 28, -1, -1, 28, -1, -1, 28, -1, 28, 28, 31, -1, 31, -1, -1, -1, -1, 28, -1, -1, -1, -1, 31, -1, -1, -1, -1, -1, -1, 28, -1, -1, -1, -1, 28, -1, -1, -1, -1, 31, -1, -1, -1, -1, -1, -1, -1, -1, 31, -1, -1, -1, 28, -1, -1, -1, -1, 28, -1, -1, -1, -1, -1, 28, 28, -1, -1, -1, -1, 28, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 28, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, 248, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 248, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 248, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 248, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 248, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 248, -1, 248, -1, -1, -1, 248, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 248, -1, -1, 248, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, 338, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 338, -1, -1, -1, 231, -1, -1, -1, -1, -1, -1, -1, 338, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 338, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 338, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 338, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 338, -1, 338, -1, -1, -1, 338, -1, -1, 231, -1, -1, -1, -1, -1, -1, 231, -1, -1, -1, -1, 231, -1, -1, -1, -1, 338, -1, -1, 338, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, 249, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 83, -1, -1, -1, -1, -1, -1, 365, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 107, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 239, -1, -1, -1, -1, -1, -1, 239, -1, -1, -1, -1, 239, -1, -1, -1, -1, 254, 239, -1, -1, -1, -1, 239, 239, -1, -1, 239, -1, -1, 239, -1, 239, 239, -1, -1, 254, -1, -1, -1, -1, 239, -1, -1, -1, -1, 254, -1, -1, -1, -1, -1, -1, 239, -1, -1, -1, -1, 239, -1, -1, -1, -1, -1, -1, -1, 254, -1, -1, -1, -1, -1, 254, -1, -1, -1, 239, -1, -1, -1, -1, 239, -1, -1, -1, -1, -1, 239, 239, -1, -1, -1, -1, 239, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 21, -1, -1, -1, -1, 10, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 43, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 159, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, 22, -1, -1, 3, -1, -1, 3, -1, -1, -1, -1, -1, -1, -1, -1, -1, 22, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 144, -1, -1, -1, 144, -1, -1, -1, -1, 144, -1, -1, 22, 144, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 157, -1, 58, 157, -1, -1, 22, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 22, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 22, -1, 22, -1, -1, -1, 22, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 22, -1, -1, 22, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 58, -1, -1, -1, 100, -1, 3, 22],
    [-1, 367, 367, 416, -1, 367, 149, -1, 32, 149, -1, 367, -1, -1, 149, 32, 149, -1, 367, 149, 149, 149, 367, 149, -1, -1, 149, 149, -1, 149, 149, -1, 149, -1, 149, -1, -1, 149, 149, 149, 367, 149, -1, 149, 149, -1, 149, 149, -1, -1, -1, 149, -1, -1, 149, 149, 149, 149, -1, 367, 210, 367, -1, 367, 367, 367, -1, 149, 367, 367, 367, -1, 149, -1, -1, 367, 149, -1, -1, 367, 367, 367, 367, -1, 89, -1, 367, 367, 367, -1, -1, 367, 367, 367, -1, 149, 367, 367, 367, 367, 367, 149, 149, -1, 367, 32, 367, 149, -1, -1, 367, 367, -1, 367, 367, 367, -1, 367, 367, -1, 367, -1, 367, 367, -1, 367, 149, 149, -1, 367, 367, 32, 149, 367],
    [-1, -1, -1, 240, -1, -1, 240, -1, -1, 240, -1, -1, -1, -1, 240, -1, 240, -1, 240, 240, 240, 240, -1, 240, -1, -1, 240, 240, -1, 240, 240, -1, 240, -1, 240, -1, -1, 240, 240, 240, -1, 240, 240, 240, 240, -1, 240, 240, -1, -1, -1, -1, 240, -1, 240, 240, 240, 240, -1, -1, 240, -1, -1, -1, -1, -1, -1, 240, -1, -1, -1, -1, 240, 240, -1, -1, 225, -1, -1, -1, -1, -1, -1, -1, -1, -1, 240, -1, 240, -1, 240, -1, 240, -1, -1, 240, -1, -1, -1, -1, -1, 240, 240, -1, -1, -1, -1, 240, -1, -1, -1, -1, 240, -1, -1, 240, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 240, 240, -1, -1, 240, -1, 240, 240],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 320, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 320, -1, -1, -1, -1, -1, -1, -1, -1, -1, 320, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 320, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 300, -1, -1, -1, -1, -1, -1, 196, -1, -1, -1, -1, 276, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, 177, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 177, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 177, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 177, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 177, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 177, -1, 177, -1, -1, -1, 177, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 177, -1, -1, 177, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 383, -1, -1, -1],
    [-1, 205, 399, 176, -1, 206, 264, -1, -1, 201, -1, 323, -1, -1, 20, -1, 394, 99, 326, 84, 4, 238, 340, 310, -1, -1, 279, 221, -1, 47, 200, -1, 161, -1, 267, -1, -1, 140, 208, 34, 68, 294, -1, 283, 398, 324, 374, 389, -1, -1, -1, -1, -1, 126, 121, 397, 433, 128, -1, 387, 73, 420, -1, 163, 336, 361, -1, -1, 256, 313, 319, -1, -1, -1, 114, 190, 375, -1, 8, 207, 335, 362, -1, -1, -1, 442, 45, 95, 135, -1, -1, 191, 385, 92, -1, 345, 179, 167, 265, 448, 236, 199, 354, 113, 393, 357, 35, 17, -1, 353, 325, 53, 278, 314, 195, 286, 341, 270, 15, -1, 143, -1, 388, 255, 44, 419, 390, 275, -1, 439, 218, 369, 87, 261],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 413, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, 56, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 169, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 56],
    [-1, -1, -1, -1, -1, 427, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 427, -1, -1, -1, -1, -1, -1, -1, 427, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 427, -1, 427, -1, -1, -1, -1, -1, -1, -1, -1, -1, 427, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 427, -1, -1, -1, -1, -1, -1, -1, -1, 427, -1, -1, -1, -1, -1, -1, -1, -1, 424, -1, -1, -1, -1, -1, -1, 424, -1, -1, -1, -1, 424, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 96, -1, -1, 136, -1, -1, 54, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 356, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 111, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 111, -1, -1, -1, -1, -1, -1, -1, -1, -1, 111, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 111, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 119, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 119, -1, -1, -1, -1, -1, -1, -1, -1, -1, 119, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 119, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 318, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 431, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 166, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 328, -1, 328, -1, -1, -1, 328, 328, -1, 328, -1, -1, 328, 328, -1, 328, -1, -1, 328, -1, -1, -1, -1, 328, 328, -1, -1, 328, -1, -1, 328, -1, 328, 328, -1, -1, -1, -1, -1, -1, -1, 328, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 328, -1, -1, -1, -1, 328, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 328, -1, -1, -1, -1, 328, -1, -1, -1, -1, -1, 328, 328, -1, -1, -1, -1, 328, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 328, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, 76, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 76, -1, 364, -1, -1, -1, -1, -1, -1, -1, -1, -1, 364, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 76, -1, -1, -1, -1, -1, -1, -1, -1, 76, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, 186, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 186, -1, -1, -1, -1, -1, 186, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 186, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 186, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 186, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 186, -1, 186, -1, -1, -1, 186, -1, -1, -1, 186, -1, -1, -1, -1, -1, -1, -1, -1, 438, -1, -1, -1, -1, -1, -1, 186, 186, -1, 186, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 186, -1, -1, -1],
    [-1, -1, -1, 30, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 30, -1, -1, -1, -1, -1, 30, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 30, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 30, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 30, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 30, -1, 30, -1, -1, -1, 30, -1, -1, -1, 30, -1, -1, -1, -1, -1, -1, -1, -1, 30, -1, -1, -1, -1, -1, -1, 30, 30, -1, 30, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 30, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 257, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 215, -1, 215, -1, -1, -1, 215, 215, -1, 215, -1, -1, 215, 215, -1, 215, -1, -1, 215, -1, -1, -1, -1, 215, 215, -1, -1, 215, -1, -1, 215, -1, 215, 215, -1, -1, -1, -1, -1, -1, -1, 215, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 215, -1, -1, -1, -1, 215, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 215, -1, -1, -1, -1, 215, -1, -1, -1, -1, -1, 215, 215, -1, -1, -1, -1, 215, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 215, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, 368, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 368, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 368, -1, 368, -1, -1, -1, -1, -1, -1, -1, -1, -1, 368, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 368, -1, -1, -1, -1, -1, -1, -1, -1, 368, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 41, -1, 41, -1, -1, -1, 41, 41, -1, 41, -1, -1, 41, 41, -1, 41, -1, -1, 41, -1, -1, -1, -1, 41, 41, -1, -1, 41, -1, -1, 41, -1, 41, 41, -1, -1, -1, -1, -1, -1, -1, 41, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 41, -1, -1, -1, -1, 41, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 41, -1, -1, -1, -1, 41, -1, -1, -1, -1, -1, 41, 41, -1, -1, -1, -1, 41, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 41, -1, -1, 78, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 38, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, 295, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 299, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, 69, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 69, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 69, -1, 69, -1, -1, -1, -1, -1, -1, -1, -1, -1, 69, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 69, -1, -1, -1, -1, -1, -1, -1, -1, 69, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 91, -1, -1, -1, 258, -1, -1, 24, -1, -1, -1, 288, -1, 116, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 223, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 71, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 71, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 277, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 382, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 155, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 315, -1, -1, -1, -1, -1, -1, 315, -1, -1, -1, -1, 315, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 404, -1, -1, -1, 138, -1, -1, -1, -1, 301, -1, -1, -1, 188, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, 72, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 72, -1, -1, -1, 81, -1, -1, -1, -1, -1, -1, -1, 72, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 72, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 72, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 72, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 72, -1, 72, -1, -1, -1, 72, -1, -1, 81, -1, -1, -1, -1, -1, -1, 81, -1, -1, -1, -1, 81, -1, -1, -1, -1, 72, -1, -1, 72, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 184, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, 14, -1, -1, 337, -1, -1, -1, -1, 322, -1, 64, -1, -1, 123, 232, 423, -1, 108, -1, -1, 401, 366, -1, 330, 332, -1, 449, -1, 118, -1, -1, 380, 298, 266, -1, 109, -1, 168, 6, -1, 50, 242, -1, -1, -1, 57, -1, -1, 151, 125, 51, 355, -1, -1, -1, -1, -1, -1, -1, -1, -1, 101, -1, -1, -1, -1, 40, -1, -1, -1, 213, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 194, -1, -1, -1, -1, -1, 12, 445, -1, -1, -1, -1, 1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 410, 66, -1, -1, -1, -1, 173, -1],
    [-1, -1, -1, -1, -1, -1, 171, -1, -1, 146, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 351, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 391, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 391, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 391, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, 287, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 287, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 216, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 287, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 287, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 287, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 287, -1, 287, -1, -1, -1, 287, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 287, -1, -1, 287, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 36, -1, -1, -1, -1, -1, -1, 36, -1, -1, -1, -1, 36, -1, -1, -1, -1, -1, 36, -1, -1, -1, -1, 36, 36, -1, -1, 36, -1, -1, 36, -1, 36, 36, -1, -1, -1, -1, -1, -1, -1, 36, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 36, -1, -1, -1, -1, 36, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 36, -1, -1, -1, -1, 36, -1, -1, -1, -1, -1, 36, 36, -1, -1, -1, -1, 36, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 312, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 312, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 312, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 103, -1, 103, -1, -1, -1, 103, 103, -1, 103, -1, -1, 103, 103, -1, 103, -1, -1, 103, -1, -1, -1, -1, 103, 103, -1, -1, 103, -1, -1, 103, -1, 103, 103, -1, -1, -1, -1, -1, -1, -1, 103, -1, -1, -1, -1, 373, -1, -1, -1, -1, -1, -1, 103, -1, -1, -1, -1, 103, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 103, -1, -1, -1, -1, 103, -1, -1, -1, -1, -1, 103, 103, -1, -1, -1, -1, 103, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 103, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, 235, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 237],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 421, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 272, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 273, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 145],
    [-1, -1, -1, 13, -1, -1, 13, -1, -1, 13, -1, -1, -1, -1, 13, -1, 13, -1, 13, 13, 13, 13, -1, 13, -1, -1, 13, 13, -1, 13, 13, -1, 13, -1, 13, -1, -1, 13, 13, 13, -1, 13, 13, 13, 13, -1, 13, 13, -1, -1, -1, -1, -1, -1, 13, 13, 13, 13, -1, -1, 13, -1, -1, -1, -1, -1, -1, 13, -1, -1, -1, -1, 13, 13, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 13, -1, 13, -1, 13, -1, 13, -1, -1, 13, -1, -1, -1, -1, -1, 13, 13, -1, -1, -1, -1, 13, -1, -1, -1, -1, 13, -1, -1, 13, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 13, 13, -1, -1, 13, -1, 13, 13],
    [-1, -1, -1, 164, -1, -1, 164, -1, -1, 164, -1, -1, 262, -1, 164, -1, 164, -1, 164, 164, 164, 164, -1, 164, -1, -1, 164, 164, -1, 164, 164, -1, 164, -1, 164, -1, -1, 164, 164, 164, -1, 164, 164, 164, 164, -1, 164, 164, -1, -1, -1, -1, 164, -1, 164, 164, 164, 164, -1, -1, 164, -1, -1, -1, -1, -1, -1, 164, -1, -1, -1, -1, 164, 164, -1, -1, 164, -1, -1, -1, -1, -1, -1, -1, -1, -1, 164, -1, 164, -1, 164, -1, 164, -1, -1, 164, -1, -1, -1, -1, -1, 164, 164, -1, -1, -1, -1, 164, -1, -1, -1, -1, 164, -1, -1, 164, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 164, 164, -1, -1, 164, -1, 164, 164],
    [-1, -1, -1, -1, -1, 339, -1, -1, -1, -1, -1, -1, -1, 137, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 174, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, 347, -1, -1, 347, -1, -1, 347, -1, -1, -1, -1, 347, -1, 347, -1, 386, 347, 347, 347, -1, 347, -1, -1, 347, 347, -1, 347, 347, -1, 347, -1, 347, -1, -1, 347, 347, 347, -1, 347, 347, 347, 347, -1, 347, 347, -1, -1, -1, -1, -1, -1, 347, 347, 347, 347, -1, -1, 347, -1, -1, -1, -1, -1, -1, 347, -1, -1, -1, -1, 347, 347, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 347, -1, 347, -1, 347, -1, 347, -1, -1, 347, -1, -1, -1, -1, -1, 347, 347, -1, -1, -1, -1, 347, -1, -1, -1, -1, 347, -1, -1, 347, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 347, 347, -1, -1, 347, -1, 347, 347],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, 134, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, 193, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 193, -1, -1, -1, 193, -1, -1, -1, -1, -1, -1, -1, 193, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 193, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 193, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 193, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 193, -1, 193, -1, -1, -1, 193, -1, -1, 193, -1, -1, -1, -1, -1, -1, 193, -1, -1, -1, -1, 193, -1, -1, -1, -1, 193, -1, -1, 193, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, 412, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 412, -1, -1, -1, -1, -1, 150, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 412, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 412, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 412, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 412, -1, 412, -1, -1, -1, 412, -1, -1, -1, 150, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 412, 150, -1, 412, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 412, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 37, -1, 37, -1, -1, -1, 37, 37, -1, 37, -1, -1, 37, 37, -1, 37, -1, -1, 37, -1, -1, -1, -1, 37, 37, -1, -1, 37, -1, -1, 37, -1, 37, 37, -1, -1, -1, -1, -1, -1, -1, 37, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 37, -1, -1, -1, -1, 37, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 37, -1, -1, -1, -1, 37, -1, -1, -1, -1, -1, 37, 37, -1, -1, -1, -1, 37, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 37, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 67, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 67, -1, -1, -1, -1, -1, -1, -1, -1, -1, 67, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 245, -1, -1, -1, -1, -1, 67, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 129, -1, 129, -1, -1, -1, 129, 129, -1, 129, -1, -1, 129, 129, -1, 129, -1, -1, 129, -1, -1, -1, -1, 129, 129, -1, -1, 129, -1, -1, 129, -1, 129, 129, -1, -1, -1, -1, -1, -1, -1, 129, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 129, -1, -1, -1, -1, 129, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 129, -1, -1, -1, -1, 129, -1, -1, -1, -1, -1, 129, 129, -1, -1, -1, -1, 129, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 129, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, 65, -1, -1, -1, -1, -1, -1, -1, 65, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 281, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 120, -1, -1, -1, -1, -1, -1, 120, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 370, -1, 447, -1, -1, -1, 447, 370, -1, 447, -1, -1, 370, 447, -1, 447, -1, -1, 370, -1, -1, -1, -1, 370, 370, -1, -1, 370, -1, -1, 370, -1, 370, 370, -1, -1, -1, -1, -1, -1, -1, 370, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 370, -1, -1, -1, -1, 370, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 370, -1, -1, -1, -1, 27, -1, -1, -1, -1, -1, 370, 27, -1, -1, -1, -1, 27, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 250, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 253, -1, -1, -1, -1, 436, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, 181, -1, -1, -1, -1, -1, -1, -1, -1, 181, -1, 181, -1, -1, -1, 181, 181, -1, 181, -1, -1, 181, 181, 181, 181, -1, 181, 181, 181, -1, -1, -1, 181, 181, -1, -1, 181, -1, -1, 181, -1, 181, 181, 181, -1, 181, -1, -1, -1, -1, 181, -1, -1, -1, -1, 181, -1, -1, -1, -1, -1, -1, 181, -1, -1, -1, -1, 181, -1, -1, -1, -1, 181, -1, -1, 181, -1, -1, -1, -1, -1, 181, -1, -1, -1, 181, -1, -1, -1, -1, 181, -1, -1, -1, -1, -1, 181, 181, -1, -1, -1, -1, 181, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 181, -1, -1, 309, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 46, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, 233, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 233, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 233, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 233, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 233, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 233, -1, 233, -1, -1, -1, 233, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 233, -1, -1, 233, -1, -1, 360, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 360],
    [-1, 444, 2, -1, -1, 214, -1, -1, -1, -1, -1, 106, -1, -1, -1, -1, -1, -1, 117, -1, -1, -1, 371, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 422, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 16, -1, 127, -1, 406, 39, 229, -1, -1, 142, 122, 49, -1, -1, -1, -1, 305, -1, -1, -1, 61, 132, 293, 297, -1, -1, -1, 175, 384, 317, -1, -1, 77, 243, 321, -1, -1, 93, 33, 331, 98, 291, -1, -1, -1, 379, -1, 425, -1, -1, -1, 269, 392, -1, 139, 228, 102, -1, 428, 189, -1, 363, -1, 97, 23, -1, 302, -1, -1, -1, 94, 90, -1, -1, 80],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 430, -1, -1, -1, -1, -1, -1, 156, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, 246, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 217],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 202, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 359, -1, -1, -1],
    [-1, -1, -1, 415, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 303, -1, 303, -1, -1, 415, 303, 303, -1, 303, -1, -1, 303, 303, -1, 303, -1, -1, 303, -1, -1, -1, -1, 303, 303, -1, -1, 303, 415, -1, 303, -1, 303, 303, -1, -1, -1, -1, -1, -1, -1, 303, -1, -1, -1, -1, 415, -1, -1, -1, -1, -1, -1, 303, -1, -1, -1, -1, 303, 415, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 415, -1, 415, -1, 303, -1, 415, -1, -1, 303, -1, -1, -1, -1, -1, 303, 303, -1, -1, -1, -1, 303, -1, -1, -1, -1, 415, -1, -1, 415, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 303, -1, -1, -1, -1, -1, 342],
    [-1, -1, -1, -1, -1, 282, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 417, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 282],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 234, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 170, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 307, -1, -1, -1],
    [-1, -1, -1, 441, -1, -1, 441, -1, -1, 441, -1, -1, -1, -1, 162, -1, 162, -1, -1, 441, 162, 162, -1, 162, -1, -1, 162, 162, -1, 162, 441, -1, 162, -1, 441, -1, -1, 162, 162, 441, -1, 162, 441, 441, 162, -1, 162, 162, -1, -1, -1, -1, -1, -1, 441, 162, 441, 441, -1, -1, 441, -1, -1, -1, -1, -1, -1, 162, -1, -1, -1, -1, 162, 441, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 441, -1, 441, -1, 162, -1, 441, -1, -1, 162, -1, -1, -1, -1, -1, 162, 162, -1, -1, -1, -1, 162, -1, -1, -1, -1, 441, -1, -1, 441, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 441, 162, -1, -1, 441, -1, 441, 441],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 18, -1, 18, -1, -1, -1, 18, 18, -1, 18, -1, -1, 18, 18, -1, 18, -1, -1, 18, -1, -1, -1, -1, 18, 18, -1, -1, 18, -1, -1, 18, -1, 18, 18, -1, -1, -1, -1, -1, -1, -1, 18, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 18, -1, -1, -1, -1, 18, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 18, -1, -1, -1, -1, 18, -1, -1, -1, -1, -1, 18, 18, -1, -1, -1, -1, 18, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 18, -1, -1, 18, -1, -1, -1],
    [-1, -1, -1, -1, -1, 372, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 60, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 372, -1, -1, -1, -1, -1, -1, -1, -1, 60, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, 104, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 104, -1, -1, -1, 158, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 104, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 104, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 104, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 104, -1, 104, -1, -1, -1, 104, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 104, -1, -1, 104, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 230, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 230, -1, -1, -1, -1, -1, -1, -1, -1, -1, 230, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 230, -1, -1, -1, -1, -1, 230, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 224, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 211, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 352, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, 212, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 212, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 212, -1, 212, -1, -1, -1, -1, -1, -1, -1, -1, -1, 212, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 212, -1, -1, -1, -1, -1, -1, -1, -1, 212, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, 148, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 148, -1, -1, -1, 148, -1, -1, -1, -1, -1, -1, -1, 141, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 148, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 148, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 148, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 148, -1, 148, -1, -1, -1, 148, -1, -1, 148, -1, -1, -1, -1, -1, -1, 148, -1, -1, -1, -1, 148, -1, -1, -1, -1, 148, -1, -1, 148, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 432, -1, -1, -1, 377, -1, -1, 432, -1, -1, -1, -1, 432, -1, -1, -1, -1, -1, 432, -1, -1, -1, -1, 432, 432, -1, -1, 432, -1, -1, 432, -1, 432, 432, -1, -1, -1, -1, -1, -1, -1, 432, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 432, -1, -1, -1, -1, 432, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 432, -1, -1, -1, -1, 432, -1, -1, -1, -1, -1, 432, 432, -1, -1, -1, -1, 432, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, 407, -1, -1, -1, -1, -1, -1, -1, -1, 407, -1, 407, -1, -1, -1, 407, 407, -1, 407, -1, -1, 407, 407, 407, 407, -1, 407, 407, 407, -1, -1, -1, 407, 407, -1, -1, 407, -1, -1, 407, -1, 407, 407, 407, -1, 407, -1, -1, -1, -1, 407, -1, -1, -1, -1, 407, -1, -1, -1, -1, -1, -1, 407, -1, -1, -1, -1, 407, -1, -1, -1, -1, 407, -1, -1, 407, -1, -1, -1, -1, -1, 407, -1, -1, -1, 407, -1, -1, -1, -1, 407, -1, -1, -1, -1, -1, 407, 407, -1, -1, -1, -1, 407, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 407, -1, -1, 403, -1, -1, -1],
    [-1, -1, -1, 29, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 29, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 29, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 29, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 29, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 29, -1, 29, -1, -1, -1, 29, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 29, -1, -1, 29, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 29],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 112, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, 0, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 204, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 0, -1, 0, -1, -1, -1, -1, -1, -1, -1, -1, -1, 0, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 0, -1, -1, -1, -1, -1, -1, -1, -1, 0, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 85, -1, 85, -1, -1, -1, 85, 85, -1, 85, -1, -1, 85, 85, -1, 85, -1, -1, 85, -1, -1, -1, -1, 85, 85, -1, -1, 85, -1, -1, 85, -1, 85, 85, -1, -1, -1, -1, -1, -1, -1, 85, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 85, -1, -1, -1, -1, 85, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 85, -1, -1, -1, -1, 85, -1, -1, -1, -1, -1, 85, 85, -1, -1, -1, -1, 85, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 85, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 182, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 182, -1, -1, -1, -1, -1, -1, -1, -1, -1, 182, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 182, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  ]
  def terminal(self, str):
    return self.str_terminal[str]
  def terminalNames(self):
    return list(self.str_terminal.keys())
  def isTerminal(self, id):
    return 0 <= id <= 133
  def isNonTerminal(self, id):
    return 134 <= id <= 271
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
      raise SyntaxError('Unexpected symbol.  Expected %s, got %s.' %(self.terminal_str[s], self.sym if self.sym else 'None'), tracer)
  def rule(self, n):
    if self.sym == None: return -1
    return self.parse_table[n - 134][self.sym.getId()]
  def call(self, nt_str):
    return getattr(self, nt_str)()
  def _TYPE_SPECIFIER(self, depth=0, tracer=None):
    rule = self.rule(134)
    tree = ParseTree( NonTerminal(134, self.getAtomString(134)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 74:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._ENUM_SPECIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 86:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STRUCT_OR_UNION_SPECIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 152:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(47, tracer) ) # long
      return tree
    elif rule == 185:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(101, tracer) ) # float
      return tree
    elif rule == 187:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(72, tracer) ) # _complex
      return tree
    elif rule == 222:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(67, tracer) ) # _bool
      return tree
    elif rule == 241:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(37, tracer) ) # char
      return tree
    elif rule == 252:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(32, tracer) ) # void
      return tree
    elif rule == 268:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(41, tracer) ) # short
      return tree
    elif rule == 343:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(46, tracer) ) # unsigned
      return tree
    elif rule == 344:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(44, tracer) ) # int
      return tree
    elif rule == 378:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(55, tracer) ) # double
      return tree
    elif rule == 396:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(26, tracer) ) # signed
      return tree
    elif rule == 418:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._TYPEDEF_NAME(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _EXTERNAL_DECLARATION(self, depth=0, tracer=None):
    rule = self.rule(135)
    tree = ParseTree( NonTerminal(135, self.getAtomString(135)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 220:
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
  def __GEN7(self, depth=0, tracer=None):
    rule = self.rule(136)
    tree = ParseTree( NonTerminal(136, self.getAtomString(136)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [-1]):
      return tree
    if self.sym == None:
      return tree
    if rule == 7:
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
  def _CONSTANT(self, depth=0, tracer=None):
    rule = self.rule(138)
    tree = ParseTree( NonTerminal(138, self.getAtomString(138)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 79:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(8, tracer) ) # enumeration_constant
      return tree
    elif rule == 289:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(131, tracer) ) # character_constant
      return tree
    elif rule == 434:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(15, tracer) ) # floating_constant
      return tree
    elif rule == 437:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(105, tracer) ) # integer_constant
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _SPECIFIER_QUALIFIER_LIST(self, depth=0, tracer=None):
    rule = self.rule(139)
    tree = ParseTree( NonTerminal(139, self.getAtomString(139)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 197:
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
    elif rule == 402:
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
  def __GEN14(self, depth=0, tracer=None):
    rule = self.rule(141)
    tree = ParseTree( NonTerminal(141, self.getAtomString(141)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in [13]):
      return tree
    if self.sym == None:
      return tree
    if rule == 52:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(5, tracer) ) # comma
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
  def _FOR_COND(self, depth=0, tracer=None):
    rule = self.rule(142)
    tree = ParseTree( NonTerminal(142, self.getAtomString(142)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 115:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(133, tracer) ) # semi
      subtree = self._EXPRESSION_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _TYPE_QUALIFIER_LIST_OPT(self, depth=0, tracer=None):
    rule = self.rule(143)
    tree = ParseTree( NonTerminal(143, self.getAtomString(143)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [48, 252, 86, 23, 60, 77, 50, 5, 31, 137]):
      return tree
    if self.sym == None:
      return tree
    if rule == 11:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN25(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _SIZEOF_BODY(self, depth=0, tracer=None):
    rule = self.rule(144)
    tree = ParseTree( NonTerminal(144, self.getAtomString(144)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 244:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(60, tracer) ) # identifier
      return tree
    elif rule == 414:
      tree.astTransform = AstTransformSubstitution(1)
      tree.add( self.expect(86, tracer) ) # lparen
      subtree = self._TYPE_NAME(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(118, tracer) ) # rparen
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _PP_FILE(self, depth=0, tracer=None):
    rule = self.rule(145)
    tree = ParseTree( NonTerminal(145, self.getAtomString(145)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _ELIPSIS_OPT(self, depth=0, tracer=None):
    rule = self.rule(146)
    tree = ParseTree( NonTerminal(146, self.getAtomString(146)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def __GEN8(self, depth=0, tracer=None):
    rule = self.rule(147)
    tree = ParseTree( NonTerminal(147, self.getAtomString(147)), tracer )
    tree.list = 'mlist'
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 25:
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
  def __GEN27(self, depth=0, tracer=None):
    rule = self.rule(148)
    tree = ParseTree( NonTerminal(148, self.getAtomString(148)), tracer )
    tree.list = 'slist'
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 292:
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
  def _INIT_DECLARATOR(self, depth=0, tracer=None):
    rule = self.rule(149)
    tree = ParseTree( NonTerminal(149, self.getAtomString(149)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 219:
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
    elif self.sym.getId() in [50, 86, 137, 60]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self._DECLARATOR_INITIALIZER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def __GEN9(self, depth=0, tracer=None):
    rule = self.rule(150)
    tree = ParseTree( NonTerminal(150, self.getAtomString(150)), tracer )
    tree.list = 'mlist'
    if self.sym != None and (self.sym.getId() in [28, 77, 60, 5, 31, 48, 252, 86, 33, 50, 137]):
      return tree
    if self.sym == None:
      return tree
    if rule == 28:
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
  def __GEN5(self, depth=0, tracer=None):
    rule = self.rule(151)
    tree = ParseTree( NonTerminal(151, self.getAtomString(151)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 248:
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
    return tree
  def __GEN26(self, depth=0, tracer=None):
    rule = self.rule(152)
    tree = ParseTree( NonTerminal(152, self.getAtomString(152)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [73, 209, 138, 92, 86, 115, 19, 88, 42, 60, 3, 31, 112]):
      return tree
    if self.sym == None:
      return tree
    if rule == 231:
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
  def __GEN6(self, depth=0, tracer=None):
    rule = self.rule(153)
    tree = ParseTree( NonTerminal(153, self.getAtomString(153)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 249:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(5, tracer) ) # comma
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
  def _TYPE_NAME(self, depth=0, tracer=None):
    rule = self.rule(154)
    tree = ParseTree( NonTerminal(154, self.getAtomString(154)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 83:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(37, tracer) ) # char
      return tree
    elif rule == 365:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(44, tracer) ) # int
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _TYPEDEF_NAME(self, depth=0, tracer=None):
    rule = self.rule(155)
    tree = ParseTree( NonTerminal(155, self.getAtomString(155)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 107:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(90, tracer) ) # typedef_identifier
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def __GEN20(self, depth=0, tracer=None):
    rule = self.rule(156)
    tree = ParseTree( NonTerminal(156, self.getAtomString(156)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [80, 86, 137, 50, 60, 31]):
      return tree
    if self.sym == None:
      return tree
    if rule == 239:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._SPECIFIER_QUALIFIER_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _EXTERNAL_DECLARATION_SUB(self, depth=0, tracer=None):
    rule = self.rule(157)
    tree = ParseTree( NonTerminal(157, self.getAtomString(157)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 10:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(33, tracer) ) # function_hint
      subtree = self._FUNCTION_DEFINITION(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 21:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(28, tracer) ) # declarator_hint
      subtree = self._INIT_DECLARATOR_LIST_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(133, tracer) ) # semi
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _PP_DIRECTIVE(self, depth=0, tracer=None):
    rule = self.rule(158)
    tree = ParseTree( NonTerminal(158, self.getAtomString(158)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _DESIGNATOR(self, depth=0, tracer=None):
    rule = self.rule(159)
    tree = ParseTree( NonTerminal(159, self.getAtomString(159)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 43:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(96, tracer) ) # dot
      tree.add( self.expect(60, tracer) ) # identifier
      return tree
    elif rule == 159:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(113, tracer) ) # lsquare
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(122, tracer) ) # rsquare
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _STATEMENT(self, depth=0, tracer=None):
    rule = self.rule(160)
    tree = ParseTree( NonTerminal(160, self.getAtomString(160)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 3:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._ITERATION_STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 22:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._EXPRESSION_STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 58:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._SELECTION_STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 100:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._COMPOUND_STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 144:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._JUMP_STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 157:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._LABELED_STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [73, 138, 88, 92, 86, 209, 115, 42, 60, 3, 19, 112]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._EXPRESSION_STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _TOKEN(self, depth=0, tracer=None):
    rule = self.rule(161)
    tree = ParseTree( NonTerminal(161, self.getAtomString(161)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 32:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._CONSTANT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 89:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(84, tracer) ) # pp_number
      return tree
    elif rule == 149:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._KEYWORD(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 210:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(60, tracer) ) # identifier
      return tree
    elif rule == 367:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PUNCTUATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 416:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(3, tracer) ) # string_literal
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _ELSE_STATEMENT_OPT(self, depth=0, tracer=None):
    rule = self.rule(162)
    tree = ParseTree( NonTerminal(162, self.getAtomString(162)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [55, 56, 132, 57, 6, 26, 18, 90, 9, 46, 67, 130, 209, 72, 73, 14, 115, 3, 16, 133, 39, 19, 20, 21, 23, 88, 27, 43, 92, 29, 30, 95, 32, 34, 37, 42, 107, 41, 112, 38, 44, 60, 138, 47, 86, 126, 54, 101, 52, 102, 127]):
      return tree
    if self.sym == None:
      return tree
    if rule == 225:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._ELSE_STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(52, tracer) ) # endif
      return tree
    return tree
  def _FUNCTION_DEFINITION(self, depth=0, tracer=None):
    rule = self.rule(163)
    tree = ParseTree( NonTerminal(163, self.getAtomString(163)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 320:
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
    elif self.sym.getId() in [50, 86, 137, 60]:
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
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def __GEN0(self, depth=0, tracer=None):
    rule = self.rule(164)
    tree = ParseTree( NonTerminal(164, self.getAtomString(164)), tracer )
    tree.list = 'tlist'
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 346:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PP_NODES(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(24, tracer) ) # separator
      subtree = self.__GEN0(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _TYPE_QUALIFIER(self, depth=0, tracer=None):
    rule = self.rule(165)
    tree = ParseTree( NonTerminal(165, self.getAtomString(165)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 196:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(102, tracer) ) # restrict
      return tree
    elif rule == 276:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(107, tracer) ) # volatile
      return tree
    elif rule == 300:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(95, tracer) ) # const
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _INITIALIZER(self, depth=0, tracer=None):
    rule = self.rule(166)
    tree = ParseTree( NonTerminal(166, self.getAtomString(166)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 177:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 383:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(130, tracer) ) # lbrace
      subtree = self.__GEN13(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self._TRAILING_COMMA_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(18, tracer) ) # rbrace
      return tree
    elif self.sym.getId() in [73, 138, 88, 92, 86, 209, 115, 42, 60, 3, 19, 112]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _TERMINALS(self, depth=0, tracer=None):
    rule = self.rule(167)
    tree = ParseTree( NonTerminal(167, self.getAtomString(167)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 4:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(20, tracer) ) # extern
      return tree
    elif rule == 8:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(78, tracer) ) # diveq
      return tree
    elif rule == 15:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(118, tracer) ) # rparen
      return tree
    elif rule == 17:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(107, tracer) ) # volatile
      return tree
    elif rule == 20:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(14, tracer) ) # struct
      return tree
    elif rule == 34:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(39, tracer) ) # return
      return tree
    elif rule == 35:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(106, tracer) ) # bitxor
      return tree
    elif rule == 44:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(124, tracer) ) # hexadecimal_floating_constant
      return tree
    elif rule == 45:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(86, tracer) ) # lparen
      return tree
    elif rule == 47:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(29, tracer) ) # register
      return tree
    elif rule == 53:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(111, tracer) ) # bitoreq
      return tree
    elif rule == 68:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(40, tracer) ) # questionmark
      return tree
    elif rule == 73:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(60, tracer) ) # identifier
      return tree
    elif rule == 84:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(19, tracer) ) # sizeof
      return tree
    elif rule == 87:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(132, tracer) ) # while
      return tree
    elif rule == 92:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(93, tracer) ) # gteq
      return tree
    elif rule == 95:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(87, tracer) ) # poundpound
      return tree
    elif rule == 99:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(17, tracer) ) # number
      return tree
    elif rule == 113:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(103, tracer) ) # universal_character_name
      return tree
    elif rule == 114:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(74, tracer) ) # complex
      return tree
    elif rule == 121:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(54, tracer) ) # case
      return tree
    elif rule == 126:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(53, tracer) ) # not
      return tree
    elif rule == 128:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(57, tracer) ) # default
      return tree
    elif rule == 135:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(88, tracer) ) # decr
      return tree
    elif rule == 140:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(37, tracer) ) # char
      return tree
    elif rule == 143:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(120, tracer) ) # lteq
      return tree
    elif rule == 161:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(32, tracer) ) # void
      return tree
    elif rule == 163:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(63, tracer) ) # gt
      return tree
    elif rule == 167:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(97, tracer) ) # or
      return tree
    elif rule == 176:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(3, tracer) ) # string_literal
      return tree
    elif rule == 179:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(96, tracer) ) # dot
      return tree
    elif rule == 190:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(75, tracer) ) # muleq
      return tree
    elif rule == 191:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(91, tracer) ) # pound
      return tree
    elif rule == 195:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(114, tracer) ) # eq
      return tree
    elif rule == 199:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(101, tracer) ) # float
      return tree
    elif rule == 200:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(30, tracer) ) # continue
      return tree
    elif rule == 201:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(9, tracer) ) # for
      return tree
    elif rule == 205:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(1, tracer) ) # arrow
      return tree
    elif rule == 206:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(5, tracer) ) # comma
      return tree
    elif rule == 207:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(79, tracer) ) # div
      return tree
    elif rule == 208:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(38, tracer) ) # enum
      return tree
    elif rule == 218:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(130, tracer) ) # lbrace
      return tree
    elif rule == 221:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(27, tracer) ) # auto
      return tree
    elif rule == 236:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(100, tracer) ) # bitor
      return tree
    elif rule == 238:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(21, tracer) ) # union
      return tree
    elif rule == 255:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(123, tracer) ) # bitandeq
      return tree
    elif rule == 256:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(68, tracer) ) # modeq
      return tree
    elif rule == 261:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(133, tracer) ) # semi
      return tree
    elif rule == 264:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(6, tracer) ) # do
      return tree
    elif rule == 265:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(98, tracer) ) # elipsis
      return tree
    elif rule == 267:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(34, tracer) ) # break
      return tree
    elif rule == 270:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(117, tracer) ) # bitxoreq
      return tree
    elif rule == 275:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(127, tracer) ) # inline
      return tree
    elif rule == 278:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(112, tracer) ) # bitand
      return tree
    elif rule == 279:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(26, tracer) ) # signed
      return tree
    elif rule == 283:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(43, tracer) ) # goto
      return tree
    elif rule == 286:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(115, tracer) ) # mul
      return tree
    elif rule == 294:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(41, tracer) ) # short
      return tree
    elif rule == 310:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(23, tracer) ) # static
      return tree
    elif rule == 313:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(69, tracer) ) # add
      return tree
    elif rule == 314:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(113, tracer) ) # lsquare
      return tree
    elif rule == 319:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(70, tracer) ) # mod
      return tree
    elif rule == 323:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(11, tracer) ) # rshifteq
      return tree
    elif rule == 324:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(45, tracer) ) # imaginary
      return tree
    elif rule == 325:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(110, tracer) ) # exclamation_point
      return tree
    elif rule == 326:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(18, tracer) ) # rbrace
      return tree
    elif rule == 335:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(80, tracer) ) # colon
      return tree
    elif rule == 336:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(64, tracer) ) # rshift
      return tree
    elif rule == 340:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(22, tracer) ) # neq
      return tree
    elif rule == 341:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(116, tracer) ) # decimal_floating_constant
      return tree
    elif rule == 345:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(95, tracer) ) # const
      return tree
    elif rule == 353:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(109, tracer) ) # header_name
      return tree
    elif rule == 354:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(102, tracer) ) # restrict
      return tree
    elif rule == 357:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(105, tracer) ) # integer_constant
      return tree
    elif rule == 361:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(65, tracer) ) # addeq
      return tree
    elif rule == 362:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(81, tracer) ) # assign
      return tree
    elif rule == 369:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(131, tracer) ) # character_constant
      return tree
    elif rule == 374:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(46, tracer) ) # unsigned
      return tree
    elif rule == 375:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(76, tracer) ) # else
      return tree
    elif rule == 385:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(92, tracer) ) # incr
      return tree
    elif rule == 387:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(59, tracer) ) # lshift
      return tree
    elif rule == 388:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(122, tracer) ) # rsquare
      return tree
    elif rule == 389:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(47, tracer) ) # long
      return tree
    elif rule == 390:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(126, tracer) ) # switch
      return tree
    elif rule == 393:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(104, tracer) ) # and
      return tree
    elif rule == 394:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(16, tracer) ) # typedef
      return tree
    elif rule == 397:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(55, tracer) ) # double
      return tree
    elif rule == 398:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(44, tracer) ) # int
      return tree
    elif rule == 399:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(2, tracer) ) # sub
      return tree
    elif rule == 419:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(125, tracer) ) # lt
      return tree
    elif rule == 420:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(61, tracer) ) # subeq
      return tree
    elif rule == 433:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(56, tracer) ) # if
      return tree
    elif rule == 439:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(129, tracer) ) # lshifteq
      return tree
    elif rule == 442:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(85, tracer) ) # bool
      return tree
    elif rule == 448:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(99, tracer) ) # tilde
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _STRUCT_DECLARATOR_BODY(self, depth=0, tracer=None):
    rule = self.rule(168)
    tree = ParseTree( NonTerminal(168, self.getAtomString(168)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 413:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(80, tracer) ) # colon
      subtree = self._DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _DECLARATOR_INITIALIZER(self, depth=0, tracer=None):
    rule = self.rule(169)
    tree = ParseTree( NonTerminal(169, self.getAtomString(169)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [5, 133]):
      return tree
    if self.sym == None:
      return tree
    if rule == 169:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(25, tracer) ) # equals
      subtree = self._INITIALIZER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN25(self, depth=0, tracer=None):
    rule = self.rule(170)
    tree = ParseTree( NonTerminal(170, self.getAtomString(170)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [48, 252, 86, 50, 23, 77, 60, 5, 31, 137]):
      return tree
    if self.sym == None:
      return tree
    if rule == 424:
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
  def _LABELED_STATEMENT(self, depth=0, tracer=None):
    rule = self.rule(171)
    tree = ParseTree( NonTerminal(171, self.getAtomString(171)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 54:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(60, tracer) ) # identifier
      tree.add( self.expect(80, tracer) ) # colon
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 96:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(54, tracer) ) # case
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(80, tracer) ) # colon
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 136:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(57, tracer) ) # default
      tree.add( self.expect(80, tracer) ) # colon
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def __GEN29(self, depth=0, tracer=None):
    rule = self.rule(172)
    tree = ParseTree( NonTerminal(172, self.getAtomString(172)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 356:
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
  def _INIT_DECLARATOR_LIST_OPT(self, depth=0, tracer=None):
    rule = self.rule(173)
    tree = ParseTree( NonTerminal(173, self.getAtomString(173)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 111:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN11(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [50, 86, 137, 60]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN11(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _DECLARATOR(self, depth=0, tracer=None):
    rule = self.rule(174)
    tree = ParseTree( NonTerminal(174, self.getAtomString(174)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 119:
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
    elif self.sym.getId() in [50, 86, 137, 60]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._POINTER_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__DIRECT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _PP(self, depth=0, tracer=None):
    rule = self.rule(175)
    tree = ParseTree( NonTerminal(175, self.getAtomString(175)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 318:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(10, tracer) ) # defined_separator
      return tree
    elif rule == 431:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(36, tracer) ) # defined
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _COMPOUND_STATEMENT(self, depth=0, tracer=None):
    rule = self.rule(176)
    tree = ParseTree( NonTerminal(176, self.getAtomString(176)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 166:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(130, tracer) ) # lbrace
      subtree = self._BLOCK_ITEM_LIST_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(18, tracer) ) # rbrace
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _PARAMETER_TYPE_LIST_OPT(self, depth=0, tracer=None):
    rule = self.rule(177)
    tree = ParseTree( NonTerminal(177, self.getAtomString(177)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 328:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PARAMETER_TYPE_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _PARAMETER_DECLARATION_SUB_SUB(self, depth=0, tracer=None):
    rule = self.rule(178)
    tree = ParseTree( NonTerminal(178, self.getAtomString(178)), tracer )
    tree.list = False
    if self.sym == None:
      return tree
    if rule == 76:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DIRECT_ABSTRACT_DECLARATOR_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 364:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__DIRECT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [86, 48, 252]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DIRECT_ABSTRACT_DECLARATOR_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    elif self.sym.getId() in [50, 86, 137, 60]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__DIRECT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _INITIALIZER_LIST_ITEM(self, depth=0, tracer=None):
    rule = self.rule(179)
    tree = ParseTree( NonTerminal(179, self.getAtomString(179)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 186:
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
    elif rule == 438:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(105, tracer) ) # integer_constant
      return tree
    elif self.sym.getId() in [73, 138, 88, 92, 86, 209, 115, 42, 60, 3, 19, 112]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DESIGNATION_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self._INITIALIZER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def __GEN13(self, depth=0, tracer=None):
    rule = self.rule(180)
    tree = ParseTree( NonTerminal(180, self.getAtomString(180)), tracer )
    tree.list = 'slist'
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 30:
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
    elif self.sym.getId() in [73, 138, 88, 92, 86, 209, 115, 42, 60, 3, 19, 112]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._INITIALIZER_LIST_ITEM(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN14(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def __GEN23(self, depth=0, tracer=None):
    rule = self.rule(181)
    tree = ParseTree( NonTerminal(181, self.getAtomString(181)), tracer )
    tree.list = 'slist'
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 257:
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
  def _ERROR_LINE(self, depth=0, tracer=None):
    rule = self.rule(182)
    tree = ParseTree( NonTerminal(182, self.getAtomString(182)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _PARAMETER_DECLARATION(self, depth=0, tracer=None):
    rule = self.rule(183)
    tree = ParseTree( NonTerminal(183, self.getAtomString(183)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 215:
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
  def _POINTER_OPT(self, depth=0, tracer=None):
    rule = self.rule(184)
    tree = ParseTree( NonTerminal(184, self.getAtomString(184)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [48, 86, 252, 60, 77, 50, 5, 137]):
      return tree
    if self.sym == None:
      return tree
    if rule == 368:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._POINTER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN10(self, depth=0, tracer=None):
    rule = self.rule(185)
    tree = ParseTree( NonTerminal(185, self.getAtomString(185)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [130]):
      return tree
    if self.sym == None:
      return tree
    if rule == 41:
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
  def _ELSE_STATEMENT(self, depth=0, tracer=None):
    rule = self.rule(186)
    tree = ParseTree( NonTerminal(186, self.getAtomString(186)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 38:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(76, tracer) ) # else
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def __GEN28(self, depth=0, tracer=None):
    rule = self.rule(187)
    tree = ParseTree( NonTerminal(187, self.getAtomString(187)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in [77]):
      return tree
    if self.sym == None:
      return tree
    if rule == 295:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(5, tracer) ) # comma
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
  def _PARAMETER_DECLARATION_SUB(self, depth=0, tracer=None):
    rule = self.rule(188)
    tree = ParseTree( NonTerminal(188, self.getAtomString(188)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [5, 77]):
      return tree
    if self.sym == None:
      return tree
    if rule == 69:
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
    elif self.sym.getId() in [86, 48, 252]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._POINTER_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self._PARAMETER_DECLARATION_SUB_SUB(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    elif self.sym.getId() in [50, 86, 137, 60]:
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
  def _CONTROL_LINE(self, depth=0, tracer=None):
    rule = self.rule(189)
    tree = ParseTree( NonTerminal(189, self.getAtomString(189)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _STORAGE_CLASS_SPECIFIER(self, depth=0, tracer=None):
    rule = self.rule(190)
    tree = ParseTree( NonTerminal(190, self.getAtomString(190)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 24:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(23, tracer) ) # static
      return tree
    elif rule == 91:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(16, tracer) ) # typedef
      return tree
    elif rule == 116:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(29, tracer) ) # register
      return tree
    elif rule == 258:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(20, tracer) ) # extern
      return tree
    elif rule == 288:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(27, tracer) ) # auto
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def __GEN15(self, depth=0, tracer=None):
    rule = self.rule(191)
    tree = ParseTree( NonTerminal(191, self.getAtomString(191)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [25]):
      return tree
    if self.sym == None:
      return tree
    if rule == 71:
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
  def _ENUM_SPECIFIER_SUB(self, depth=0, tracer=None):
    rule = self.rule(192)
    tree = ParseTree( NonTerminal(192, self.getAtomString(192)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 277:
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
    elif rule == 382:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._ENUM_SPECIFIER_BODY(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _DIRECT_DECLARATOR_MODIFIER(self, depth=0, tracer=None):
    rule = self.rule(193)
    tree = ParseTree( NonTerminal(193, self.getAtomString(193)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 155:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(23, tracer) ) # static
      return tree
    elif rule == 315:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._TYPE_QUALIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _IF_PART(self, depth=0, tracer=None):
    rule = self.rule(194)
    tree = ParseTree( NonTerminal(194, self.getAtomString(194)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _ELSEIF_PART(self, depth=0, tracer=None):
    rule = self.rule(195)
    tree = ParseTree( NonTerminal(195, self.getAtomString(195)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _PP_TOKENS(self, depth=0, tracer=None):
    rule = self.rule(196)
    tree = ParseTree( NonTerminal(196, self.getAtomString(196)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def __GEN1(self, depth=0, tracer=None):
    rule = self.rule(197)
    tree = ParseTree( NonTerminal(197, self.getAtomString(197)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 133:
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
  def _JUMP_STATEMENT(self, depth=0, tracer=None):
    rule = self.rule(198)
    tree = ParseTree( NonTerminal(198, self.getAtomString(198)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 138:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(34, tracer) ) # break
      tree.add( self.expect(133, tracer) ) # semi
      return tree
    elif rule == 188:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(43, tracer) ) # goto
      tree.add( self.expect(60, tracer) ) # identifier
      tree.add( self.expect(133, tracer) ) # semi
      return tree
    elif rule == 301:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(39, tracer) ) # return
      subtree = self._EXPRESSION_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(133, tracer) ) # semi
      return tree
    elif rule == 404:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(30, tracer) ) # continue
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _DIRECT_DECLARATOR_MODIFIER_LIST_OPT(self, depth=0, tracer=None):
    rule = self.rule(199)
    tree = ParseTree( NonTerminal(199, self.getAtomString(199)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [73, 138, 115, 88, 86, 92, 19, 209, 42, 60, 3, 31, 112]):
      return tree
    if self.sym == None:
      return tree
    if rule == 81:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN26(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _ENUM_SPECIFIER_BODY(self, depth=0, tracer=None):
    rule = self.rule(200)
    tree = ParseTree( NonTerminal(200, self.getAtomString(200)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 184:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(130, tracer) ) # lbrace
      subtree = self.__GEN23(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self._TRAILING_COMMA_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(18, tracer) ) # rbrace
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _KEYWORD(self, depth=0, tracer=None):
    rule = self.rule(201)
    tree = ParseTree( NonTerminal(201, self.getAtomString(201)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 1:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(107, tracer) ) # volatile
      return tree
    elif rule == 6:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(44, tracer) ) # int
      return tree
    elif rule == 12:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(101, tracer) ) # float
      return tree
    elif rule == 14:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(6, tracer) ) # do
      return tree
    elif rule == 40:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(72, tracer) ) # _complex
      return tree
    elif rule == 50:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(46, tracer) ) # unsigned
      return tree
    elif rule == 51:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(56, tracer) ) # if
      return tree
    elif rule == 57:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(51, tracer) ) # _imaginary
      return tree
    elif rule == 64:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(16, tracer) ) # typedef
      return tree
    elif rule == 66:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(127, tracer) ) # inline
      return tree
    elif rule == 101:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(67, tracer) ) # _bool
      return tree
    elif rule == 108:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(23, tracer) ) # static
      return tree
    elif rule == 109:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(41, tracer) ) # short
      return tree
    elif rule == 118:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(34, tracer) ) # break
      return tree
    elif rule == 123:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(19, tracer) ) # sizeof
      return tree
    elif rule == 125:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(55, tracer) ) # double
      return tree
    elif rule == 151:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(54, tracer) ) # case
      return tree
    elif rule == 168:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(43, tracer) ) # goto
      return tree
    elif rule == 173:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(132, tracer) ) # while
      return tree
    elif rule == 194:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(95, tracer) ) # const
      return tree
    elif rule == 213:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(76, tracer) ) # else
      return tree
    elif rule == 232:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(20, tracer) ) # extern
      return tree
    elif rule == 242:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(47, tracer) ) # long
      return tree
    elif rule == 266:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(39, tracer) ) # return
      return tree
    elif rule == 298:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(38, tracer) ) # enum
      return tree
    elif rule == 322:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(14, tracer) ) # struct
      return tree
    elif rule == 330:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(29, tracer) ) # register
      return tree
    elif rule == 332:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(30, tracer) ) # continue
      return tree
    elif rule == 337:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(9, tracer) ) # for
      return tree
    elif rule == 355:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(57, tracer) ) # default
      return tree
    elif rule == 366:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(27, tracer) ) # auto
      return tree
    elif rule == 380:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(37, tracer) ) # char
      return tree
    elif rule == 401:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(26, tracer) ) # signed
      return tree
    elif rule == 410:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(126, tracer) ) # switch
      return tree
    elif rule == 423:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(21, tracer) ) # union
      return tree
    elif rule == 445:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(102, tracer) ) # restrict
      return tree
    elif rule == 449:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(32, tracer) ) # void
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _ITERATION_STATEMENT(self, depth=0, tracer=None):
    rule = self.rule(202)
    tree = ParseTree( NonTerminal(202, self.getAtomString(202)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 146:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(9, tracer) ) # for
      tree.add( self.expect(86, tracer) ) # lparen
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
      tree.add( self.expect(118, tracer) ) # rparen
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 171:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(6, tracer) ) # do
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(132, tracer) ) # while
      tree.add( self.expect(86, tracer) ) # lparen
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(118, tracer) ) # rparen
      tree.add( self.expect(133, tracer) ) # semi
      return tree
    elif rule == 351:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(132, tracer) ) # while
      tree.add( self.expect(86, tracer) ) # lparen
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(118, tracer) ) # rparen
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _DESIGNATION(self, depth=0, tracer=None):
    rule = self.rule(203)
    tree = ParseTree( NonTerminal(203, self.getAtomString(203)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 391:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN15(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(25, tracer) ) # equals
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _DIRECT_DECLARATOR_SIZE(self, depth=0, tracer=None):
    rule = self.rule(204)
    tree = ParseTree( NonTerminal(204, self.getAtomString(204)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 216:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(31, tracer) ) # asterisk
      return tree
    elif rule == 287:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [73, 138, 88, 92, 86, 209, 115, 42, 60, 3, 19, 112]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _STRUCT_DECLARATION(self, depth=0, tracer=None):
    rule = self.rule(205)
    tree = ParseTree( NonTerminal(205, self.getAtomString(205)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 36:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._SPECIFIER_QUALIFIER_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN18(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(133, tracer) ) # semi
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _ABSTRACT_DECLARATOR(self, depth=0, tracer=None):
    rule = self.rule(206)
    tree = ParseTree( NonTerminal(206, self.getAtomString(206)), tracer )
    tree.list = False
    if self.sym == None:
      return tree
    if rule == 312:
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
    elif self.sym.getId() in [86, 48, 252]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._POINTER_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self._DIRECT_ABSTRACT_DECLARATOR_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _PP_NODES(self, depth=0, tracer=None):
    rule = self.rule(207)
    tree = ParseTree( NonTerminal(207, self.getAtomString(207)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _DIRECT_DECLARATOR_PARAMETER_LIST(self, depth=0, tracer=None):
    rule = self.rule(208)
    tree = ParseTree( NonTerminal(208, self.getAtomString(208)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 103:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PARAMETER_TYPE_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 373:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN29(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN19(self, depth=0, tracer=None):
    rule = self.rule(210)
    tree = ParseTree( NonTerminal(210, self.getAtomString(210)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in [133]):
      return tree
    if self.sym == None:
      return tree
    if rule == 235:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(5, tracer) ) # comma
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
  def _VA_ARGS(self, depth=0, tracer=None):
    rule = self.rule(211)
    tree = ParseTree( NonTerminal(211, self.getAtomString(211)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 421:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(77, tracer) ) # comma_va_args
      tree.add( self.expect(98, tracer) ) # elipsis
      return tree
    return tree
  def _ENUMERATOR(self, depth=0, tracer=None):
    rule = self.rule(212)
    tree = ParseTree( NonTerminal(212, self.getAtomString(212)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 272:
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
  def _FOR_INCR(self, depth=0, tracer=None):
    rule = self.rule(213)
    tree = ParseTree( NonTerminal(213, self.getAtomString(213)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [118]):
      return tree
    if self.sym == None:
      return tree
    if rule == 145:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(133, tracer) ) # semi
      subtree = self._EXPRESSION_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _BLOCK_ITEM_LIST_OPT(self, depth=0, tracer=None):
    rule = self.rule(214)
    tree = ParseTree( NonTerminal(214, self.getAtomString(214)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [18]):
      return tree
    if self.sym == None:
      return tree
    if rule == 13:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN31(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [73, 138, 88, 92, 86, 209, 115, 42, 60, 3, 19, 112]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN31(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    return tree
  def _ELSE_IF_STATEMENT_OPT(self, depth=0, tracer=None):
    rule = self.rule(215)
    tree = ParseTree( NonTerminal(215, self.getAtomString(215)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [55, 56, 132, 57, 6, 26, 18, 90, 9, 46, 67, 130, 209, 72, 73, 14, 76, 3, 16, 133, 39, 19, 20, 21, 23, 88, 27, 43, 92, 29, 30, 95, 32, 34, 37, 42, 107, 41, 112, 38, 115, 44, 60, 138, 47, 86, 126, 54, 101, 52, 102, 127]):
      return tree
    if self.sym == None:
      return tree
    if rule == 262:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._ELSE_IF_STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(52, tracer) ) # endif
      return tree
    return tree
  def __GEN24(self, depth=0, tracer=None):
    rule = self.rule(216)
    tree = ParseTree( NonTerminal(216, self.getAtomString(216)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in [13]):
      return tree
    if self.sym == None:
      return tree
    if rule == 339:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(5, tracer) ) # comma
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
  def _DEFINE_FUNC_PARAM(self, depth=0, tracer=None):
    rule = self.rule(217)
    tree = ParseTree( NonTerminal(217, self.getAtomString(217)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _FUNCTION_SPECIFIER(self, depth=0, tracer=None):
    rule = self.rule(218)
    tree = ParseTree( NonTerminal(218, self.getAtomString(218)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 174:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(127, tracer) ) # inline
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def __GEN31(self, depth=0, tracer=None):
    rule = self.rule(219)
    tree = ParseTree( NonTerminal(219, self.getAtomString(219)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [18]):
      return tree
    if self.sym == None:
      return tree
    if rule == 347:
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
    elif self.sym.getId() in [73, 138, 88, 92, 86, 209, 115, 42, 60, 3, 19, 112]:
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
  def __GEN2(self, depth=0, tracer=None):
    rule = self.rule(220)
    tree = ParseTree( NonTerminal(220, self.getAtomString(220)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 131:
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
  def _PRAGMA_LINE(self, depth=0, tracer=None):
    rule = self.rule(221)
    tree = ParseTree( NonTerminal(221, self.getAtomString(221)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def __GEN3(self, depth=0, tracer=None):
    rule = self.rule(222)
    tree = ParseTree( NonTerminal(222, self.getAtomString(222)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 134:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(5, tracer) ) # comma
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
  def _DIRECT_DECLARATOR_EXPR(self, depth=0, tracer=None):
    rule = self.rule(223)
    tree = ParseTree( NonTerminal(223, self.getAtomString(223)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 193:
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
    elif self.sym.getId() in [73, 138, 88, 92, 86, 209, 115, 42, 60, 3, 19, 112]:
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
  def _DESIGNATION_OPT(self, depth=0, tracer=None):
    rule = self.rule(224)
    tree = ParseTree( NonTerminal(224, self.getAtomString(224)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [73, 138, 115, 88, 130, 42, 92, 209, 86, 60, 3, 19, 112]):
      return tree
    if self.sym == None:
      return tree
    if rule == 150:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DESIGNATION(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _DECLARATION(self, depth=0, tracer=None):
    rule = self.rule(225)
    tree = ParseTree( NonTerminal(225, self.getAtomString(225)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 37:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN8(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self._INIT_DECLARATOR_LIST_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(133, tracer) ) # semi
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _STRUCT_DECLARATOR(self, depth=0, tracer=None):
    rule = self.rule(226)
    tree = ParseTree( NonTerminal(226, self.getAtomString(226)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 67:
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
    elif rule == 245:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STRUCT_DECLARATOR_BODY(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [50, 86, 137, 60]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN21(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _PARAMETER_TYPE_LIST(self, depth=0, tracer=None):
    rule = self.rule(227)
    tree = ParseTree( NonTerminal(227, self.getAtomString(227)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 129:
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
  def _ENUMERATOR_ASSIGNMENT(self, depth=0, tracer=None):
    rule = self.rule(228)
    tree = ParseTree( NonTerminal(228, self.getAtomString(228)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [5, 13]):
      return tree
    if self.sym == None:
      return tree
    if rule == 281:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(81, tracer) ) # assign
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _STRUCT_OR_UNION_SPECIFIER(self, depth=0, tracer=None):
    rule = self.rule(229)
    tree = ParseTree( NonTerminal(229, self.getAtomString(229)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 120:
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
  def _DECLARATION_SPECIFIER(self, depth=0, tracer=None):
    rule = self.rule(230)
    tree = ParseTree( NonTerminal(230, self.getAtomString(230)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 27:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._TYPE_QUALIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 250:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._FUNCTION_SPECIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 370:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._TYPE_SPECIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 447:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STORAGE_CLASS_SPECIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _TRAILING_COMMA_OPT(self, depth=0, tracer=None):
    rule = self.rule(231)
    tree = ParseTree( NonTerminal(231, self.getAtomString(231)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [18]):
      return tree
    if self.sym == None:
      return tree
    if rule == 253:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(13, tracer) ) # trailing_comma
      return tree
    return tree
  def __GEN22(self, depth=0, tracer=None):
    rule = self.rule(232)
    tree = ParseTree( NonTerminal(232, self.getAtomString(232)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [27, 55, 21, 26, 95, 90, 5, 101, 31, 28, 32, 46, 23, 102, 37, 67, 107, 252, 41, 72, 47, 38, 16, 77, 60, 44, 48, 20, 80, 29, 50, 14, 33, 86, 127, 137]):
      return tree
    if self.sym == None:
      return tree
    if rule == 309:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._ENUM_SPECIFIER_BODY(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _ENUM_SPECIFIER(self, depth=0, tracer=None):
    rule = self.rule(233)
    tree = ParseTree( NonTerminal(233, self.getAtomString(233)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 46:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(38, tracer) ) # enum
      subtree = self._ENUM_SPECIFIER_SUB(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _INCLUDE_LINE(self, depth=0, tracer=None):
    rule = self.rule(234)
    tree = ParseTree( NonTerminal(234, self.getAtomString(234)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _EXPRESSION_OPT(self, depth=0, tracer=None):
    rule = self.rule(235)
    tree = ParseTree( NonTerminal(235, self.getAtomString(235)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [118, 133]):
      return tree
    if self.sym == None:
      return tree
    if rule == 233:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [73, 138, 88, 92, 86, 209, 115, 42, 60, 3, 19, 112]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    return tree
  def _PUNCTUATOR(self, depth=0, tracer=None):
    rule = self.rule(236)
    tree = ParseTree( NonTerminal(236, self.getAtomString(236)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 2:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(2, tracer) ) # sub
      return tree
    elif rule == 16:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(59, tracer) ) # lshift
      return tree
    elif rule == 23:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(123, tracer) ) # bitandeq
      return tree
    elif rule == 33:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(97, tracer) ) # or
      return tree
    elif rule == 39:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(64, tracer) ) # rshift
      return tree
    elif rule == 49:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(70, tracer) ) # mod
      return tree
    elif rule == 61:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(79, tracer) ) # div
      return tree
    elif rule == 77:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(91, tracer) ) # pound
      return tree
    elif rule == 80:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(133, tracer) ) # semi
      return tree
    elif rule == 90:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(130, tracer) ) # lbrace
      return tree
    elif rule == 93:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(96, tracer) ) # dot
      return tree
    elif rule == 94:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(129, tracer) ) # lshifteq
      return tree
    elif rule == 97:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(122, tracer) ) # rsquare
      return tree
    elif rule == 98:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(99, tracer) ) # tilde
      return tree
    elif rule == 102:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(115, tracer) ) # mul
      return tree
    elif rule == 106:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(11, tracer) ) # rshifteq
      return tree
    elif rule == 117:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(18, tracer) ) # rbrace
      return tree
    elif rule == 122:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(69, tracer) ) # add
      return tree
    elif rule == 127:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(61, tracer) ) # subeq
      return tree
    elif rule == 132:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(80, tracer) ) # colon
      return tree
    elif rule == 139:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(113, tracer) ) # lsquare
      return tree
    elif rule == 142:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(68, tracer) ) # modeq
      return tree
    elif rule == 175:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(86, tracer) ) # lparen
      return tree
    elif rule == 189:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(118, tracer) ) # rparen
      return tree
    elif rule == 214:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(5, tracer) ) # comma
      return tree
    elif rule == 228:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(114, tracer) ) # eq
      return tree
    elif rule == 229:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(65, tracer) ) # addeq
      return tree
    elif rule == 243:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(92, tracer) ) # incr
      return tree
    elif rule == 269:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(110, tracer) ) # exclamation_point
      return tree
    elif rule == 291:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(100, tracer) ) # bitor
      return tree
    elif rule == 293:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(81, tracer) ) # assign
      return tree
    elif rule == 297:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(82, tracer) ) # ampersand
      return tree
    elif rule == 302:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(125, tracer) ) # lt
      return tree
    elif rule == 305:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(75, tracer) ) # muleq
      return tree
    elif rule == 317:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(88, tracer) ) # decr
      return tree
    elif rule == 321:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(93, tracer) ) # gteq
      return tree
    elif rule == 331:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(98, tracer) ) # elipsis
      return tree
    elif rule == 363:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(120, tracer) ) # lteq
      return tree
    elif rule == 371:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(22, tracer) ) # neq
      return tree
    elif rule == 379:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(104, tracer) ) # and
      return tree
    elif rule == 384:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(87, tracer) ) # poundpound
      return tree
    elif rule == 392:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(111, tracer) ) # bitoreq
      return tree
    elif rule == 406:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(63, tracer) ) # gt
      return tree
    elif rule == 422:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(40, tracer) ) # questionmark
      return tree
    elif rule == 425:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(106, tracer) ) # bitxor
      return tree
    elif rule == 428:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(117, tracer) ) # bitxoreq
      return tree
    elif rule == 444:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(1, tracer) ) # arrow
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _DEFINE_LINE(self, depth=0, tracer=None):
    rule = self.rule(237)
    tree = ParseTree( NonTerminal(237, self.getAtomString(237)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _DEFINED_IDENTIFIER(self, depth=0, tracer=None):
    rule = self.rule(238)
    tree = ParseTree( NonTerminal(238, self.getAtomString(238)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _STRUCT_OR_UNION(self, depth=0, tracer=None):
    rule = self.rule(239)
    tree = ParseTree( NonTerminal(239, self.getAtomString(239)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 156:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(21, tracer) ) # union
      return tree
    elif rule == 430:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(14, tracer) ) # struct
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def __GEN12(self, depth=0, tracer=None):
    rule = self.rule(240)
    tree = ParseTree( NonTerminal(240, self.getAtomString(240)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in [133]):
      return tree
    if self.sym == None:
      return tree
    if rule == 246:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(5, tracer) ) # comma
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
  def _STRUCT_OR_UNION_SUB(self, depth=0, tracer=None):
    rule = self.rule(241)
    tree = ParseTree( NonTerminal(241, self.getAtomString(241)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 202:
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
    elif rule == 359:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STRUCT_OR_UNION_BODY(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _FOR_INIT(self, depth=0, tracer=None):
    rule = self.rule(242)
    tree = ParseTree( NonTerminal(242, self.getAtomString(242)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [133]):
      return tree
    if self.sym == None:
      return tree
    if rule == 303:
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
    elif rule == 415:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [73, 138, 88, 92, 86, 209, 115, 42, 60, 3, 19, 112]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    return tree
  def __GEN21(self, depth=0, tracer=None):
    rule = self.rule(243)
    tree = ParseTree( NonTerminal(243, self.getAtomString(243)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [5, 133]):
      return tree
    if self.sym == None:
      return tree
    if rule == 417:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STRUCT_DECLARATOR_BODY(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _ELSE_IF_STATEMENT(self, depth=0, tracer=None):
    rule = self.rule(244)
    tree = ParseTree( NonTerminal(244, self.getAtomString(244)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 234:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(12, tracer) ) # else_if
      tree.add( self.expect(86, tracer) ) # lparen
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(118, tracer) ) # rparen
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _IDENTIFIER(self, depth=0, tracer=None):
    rule = self.rule(245)
    tree = ParseTree( NonTerminal(245, self.getAtomString(245)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 170:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(60, tracer) ) # identifier
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _PP_NODES_LIST(self, depth=0, tracer=None):
    rule = self.rule(246)
    tree = ParseTree( NonTerminal(246, self.getAtomString(246)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _STRUCT_OR_UNION_BODY(self, depth=0, tracer=None):
    rule = self.rule(247)
    tree = ParseTree( NonTerminal(247, self.getAtomString(247)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 307:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(130, tracer) ) # lbrace
      subtree = self.__GEN17(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(18, tracer) ) # rbrace
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _BLOCK_ITEM(self, depth=0, tracer=None):
    rule = self.rule(248)
    tree = ParseTree( NonTerminal(248, self.getAtomString(248)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 162:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DECLARATION(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 441:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [73, 138, 88, 92, 86, 209, 115, 42, 60, 3, 19, 112]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _ELSE_PART(self, depth=0, tracer=None):
    rule = self.rule(249)
    tree = ParseTree( NonTerminal(249, self.getAtomString(249)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _WARNING_LINE(self, depth=0, tracer=None):
    rule = self.rule(250)
    tree = ParseTree( NonTerminal(250, self.getAtomString(250)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _DECLARATION_LIST_OPT(self, depth=0, tracer=None):
    rule = self.rule(251)
    tree = ParseTree( NonTerminal(251, self.getAtomString(251)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [130]):
      return tree
    if self.sym == None:
      return tree
    if rule == 18:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN10(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _DIRECT_ABSTRACT_DECLARATOR_OPT(self, depth=0, tracer=None):
    rule = self.rule(252)
    tree = ParseTree( NonTerminal(252, self.getAtomString(252)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [5, 77]):
      return tree
    if self.sym == None:
      return tree
    if rule == 60:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__DIRECT_ABSTRACT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [86, 48, 252]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__DIRECT_ABSTRACT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    return tree
  def _STATIC_OPT(self, depth=0, tracer=None):
    rule = self.rule(253)
    tree = ParseTree( NonTerminal(253, self.getAtomString(253)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [73, 209, 138, 88, 86, 115, 92, 42, 60, 3, 19, 112]):
      return tree
    if self.sym == None:
      return tree
    if rule == 158:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(23, tracer) ) # static
      return tree
    return tree
  def _UNDEF_LINE(self, depth=0, tracer=None):
    rule = self.rule(254)
    tree = ParseTree( NonTerminal(254, self.getAtomString(254)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _REPLACEMENT_LIST(self, depth=0, tracer=None):
    rule = self.rule(255)
    tree = ParseTree( NonTerminal(255, self.getAtomString(255)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def __GEN18(self, depth=0, tracer=None):
    rule = self.rule(256)
    tree = ParseTree( NonTerminal(256, self.getAtomString(256)), tracer )
    tree.list = 'slist'
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 230:
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
    elif self.sym.getId() in [50, 86, 137, 60]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STRUCT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN19(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def __GEN4(self, depth=0, tracer=None):
    rule = self.rule(257)
    tree = ParseTree( NonTerminal(257, self.getAtomString(257)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 203:
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
  def _LINE_LINE(self, depth=0, tracer=None):
    rule = self.rule(258)
    tree = ParseTree( NonTerminal(258, self.getAtomString(258)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _SELECTION_STATEMENT(self, depth=0, tracer=None):
    rule = self.rule(259)
    tree = ParseTree( NonTerminal(259, self.getAtomString(259)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 211:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(126, tracer) ) # switch
      tree.add( self.expect(86, tracer) ) # lparen
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(118, tracer) ) # rparen
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 224:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(56, tracer) ) # if
      tree.add( self.expect(86, tracer) ) # lparen
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(118, tracer) ) # rparen
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(52, tracer) ) # endif
      subtree = self._ELSE_IF_STATEMENT_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self._ELSE_STATEMENT_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _ENUMERATION_CONSTANT(self, depth=0, tracer=None):
    rule = self.rule(260)
    tree = ParseTree( NonTerminal(260, self.getAtomString(260)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 352:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(60, tracer) ) # identifier
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _POINTER(self, depth=0, tracer=None):
    rule = self.rule(261)
    tree = ParseTree( NonTerminal(261, self.getAtomString(261)), tracer )
    tree.list = False
    if self.sym == None:
      return tree
    if rule == 212:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN30(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _IF_SECTION(self, depth=0, tracer=None):
    rule = self.rule(262)
    tree = ParseTree( NonTerminal(262, self.getAtomString(262)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _DIRECT_ABSTRACT_DECLARATOR_EXPR(self, depth=0, tracer=None):
    rule = self.rule(263)
    tree = ParseTree( NonTerminal(263, self.getAtomString(263)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 141:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(31, tracer) ) # asterisk
      return tree
    elif rule == 148:
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
    elif self.sym.getId() in [73, 138, 88, 92, 86, 209, 115, 42, 60, 3, 19, 112]:
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
  def __GEN17(self, depth=0, tracer=None):
    rule = self.rule(264)
    tree = ParseTree( NonTerminal(264, self.getAtomString(264)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [18]):
      return tree
    if self.sym == None:
      return tree
    if rule == 432:
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
  def _INCLUDE_TYPE(self, depth=0, tracer=None):
    rule = self.rule(265)
    tree = ParseTree( NonTerminal(265, self.getAtomString(265)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def __GEN16(self, depth=0, tracer=None):
    rule = self.rule(266)
    tree = ParseTree( NonTerminal(266, self.getAtomString(266)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [27, 55, 21, 26, 95, 90, 5, 101, 31, 28, 32, 46, 23, 102, 37, 67, 107, 252, 41, 72, 47, 38, 16, 77, 60, 44, 48, 20, 80, 29, 50, 14, 33, 86, 127, 137]):
      return tree
    if self.sym == None:
      return tree
    if rule == 403:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STRUCT_OR_UNION_BODY(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _EXPRESSION_STATEMENT(self, depth=0, tracer=None):
    rule = self.rule(267)
    tree = ParseTree( NonTerminal(267, self.getAtomString(267)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 29:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._EXPRESSION_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(133, tracer) ) # semi
      return tree
    elif self.sym.getId() in [73, 138, 88, 92, 86, 209, 115, 42, 60, 3, 19, 112]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._EXPRESSION_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(133, tracer) ) # semi
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _POINTER_SUB(self, depth=0, tracer=None):
    rule = self.rule(268)
    tree = ParseTree( NonTerminal(268, self.getAtomString(268)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 112:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(31, tracer) ) # asterisk
      subtree = self._TYPE_QUALIFIER_LIST_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def __GEN30(self, depth=0, tracer=None):
    rule = self.rule(269)
    tree = ParseTree( NonTerminal(269, self.getAtomString(269)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [48, 86, 252, 60, 77, 50, 5, 137]):
      return tree
    if self.sym == None:
      return tree
    if rule == 204:
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
  def _TRANSLATION_UNIT(self, depth=0, tracer=None):
    rule = self.rule(270)
    tree = ParseTree( NonTerminal(270, self.getAtomString(270)), tracer )
    tree.list = False
    if self.sym == None:
      return tree
    if rule == 85:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN7(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def __GEN11(self, depth=0, tracer=None):
    rule = self.rule(271)
    tree = ParseTree( NonTerminal(271, self.getAtomString(271)), tracer )
    tree.list = 'slist'
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 182:
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
    elif self.sym.getId() in [50, 86, 137, 60]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._INIT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN12(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol', tracer)
  infixBp0 = {
    1: 16000,
    2: 12000,
    5: 1000,
    11: 2000,
    22: 9000,
    40: 3000,
    59: 11000,
    61: 2000,
    63: 10000,
    64: 11000,
    65: 2000,
    68: 2000,
    69: 12000,
    70: 13000,
    75: 2000,
    78: 2000,
    79: 13000,
    81: 2000,
    86: 16000,
    88: 16000,
    92: 16000,
    93: 10000,
    96: 16000,
    97: 4000,
    100: 8000,
    104: 5000,
    106: 7000,
    111: 2000,
    112: 6000,
    113: 16000,
    114: 9000,
    115: 13000,
    117: 2000,
    120: 10000,
    123: 2000,
    125: 10000,
    129: 2000,
    130: 15000,
  }
  prefixBp0 = {
    2: 14000,
    53: 14000,
    88: 14000,
    92: 14000,
    94: 14000,
    112: 14000,
    115: 14000,
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
    if self.sym.getId() == 112: # 'bitand'
      tree.astTransform = AstTransformNodeCreator('AddressOf', {'var': 1})
      tree.add( self.expect(112, tracer) )
      tree.add( self.__EXPR( self.prefixBp0[112] ) )
      tree.isPrefix = True
    elif self.sym.getId() == 209: # _expr
      tree.astTransform = AstTransformNodeCreator('PostDecr', {'var': 0})
      return self.expect( 209, tracer )
    elif self.sym.getId() == 60: # 'identifier'
      tree.astTransform = AstTransformNodeCreator('ArrayIndex', {'params': 2, 'name': 0})
      return self.expect( 60, tracer )
    elif self.sym.getId() == 86: # 'lparen'
      tree.astTransform = AstTransformSubstitution(2)
      tree.add( self.expect(86, tracer) )
      tree.add( self.__EXPR() )
      tree.add( self.expect(118, tracer) )
    elif self.sym.getId() == 92: # 'incr'
      tree.astTransform = AstTransformNodeCreator('PreIncr', {'var': 1})
      tree.add( self.expect(92, tracer) )
      tree.add( self.__EXPR( self.prefixBp0[92] ) )
      tree.isPrefix = True
    elif self.sym.getId() == 19: # 'sizeof'
      tree.astTransform = AstTransformNodeCreator('SizeOf', {'var': 1})
      return self.expect( 19, tracer )
    elif self.sym.getId() == 88: # 'decr'
      tree.astTransform = AstTransformNodeCreator('PreDecr', {'var': 1})
      tree.add( self.expect(88, tracer) )
      tree.add( self.__EXPR( self.prefixBp0[88] ) )
      tree.isPrefix = True
    elif self.sym.getId() == 3: # 'string_literal'
      tree.astTransform = AstTransformSubstitution(0)
      return self.expect( 3, tracer )
    elif self.sym.getId() == 138: # constant
      tree.astTransform = AstTransformSubstitution(0)
      return self.expect( 138, tracer )
    elif self.sym.getId() == 115: # 'mul'
      tree.astTransform = AstTransformNodeCreator('Dereference', {'var': 1})
      tree.add( self.expect(115, tracer) )
      tree.add( self.__EXPR( self.prefixBp0[115] ) )
      tree.isPrefix = True
    elif self.sym.getId() == 42: # 'lparen_cast'
      tree.astTransform = AstTransformNodeCreator('TypeInitializion', {'type': 1, 'initializer': 4})
      tree.add( self.expect(42, tracer) )
      tree.add( self._TYPE_NAME() )
      tree.add( self.expect(118, tracer) )
    return tree
  def led0(self, left, tracer):
    tree = ParseTree( NonTerminal(209, '_expr') )
    if  self.sym.getId() == 115: # 'mul'
      tree.astTransform = AstTransformNodeCreator('Mul', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(115, tracer) )
      tree.add( self.__EXPR( self.infixBp0[115] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 2: # 'sub'
      tree.astTransform = AstTransformNodeCreator('Sub', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(2, tracer) )
      tree.add( self.__EXPR( self.infixBp0[2] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 86: # 'lparen'
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(86, tracer) )
      tree.add( self.__GEN5() )
      tree.add( self.expect(118, tracer) )
    elif  self.sym.getId() == 129: # 'lshifteq'
      tree.astTransform = AstTransformNodeCreator('LeftShiftAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(129, tracer) )
      tree.add( self.__EXPR( self.infixBp0[129] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 68: # 'modeq'
      tree.astTransform = AstTransformNodeCreator('ModAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(68, tracer) )
      tree.add( self.__EXPR( self.infixBp0[68] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 89: # 'sizeof_separator'
      tree.astTransform = AstTransformNodeCreator('SizeOf', {'var': 1})
      if left:
        tree.add(left)
      tree.add( self.expect(89, tracer) )
      tree.add( self._SIZEOF_BODY() )
    elif  self.sym.getId() == 59: # 'lshift'
      tree.astTransform = AstTransformNodeCreator('LeftShift', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(59, tracer) )
      tree.add( self.__EXPR( self.infixBp0[59] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 79: # 'div'
      tree.astTransform = AstTransformNodeCreator('Div', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(79, tracer) )
      tree.add( self.__EXPR( self.infixBp0[79] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 125: # 'lt'
      tree.astTransform = AstTransformNodeCreator('LessThan', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(125, tracer) )
      tree.add( self.__EXPR( self.infixBp0[125] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 40: # 'questionmark'
      tree.astTransform = AstTransformNodeCreator('TernaryOperator', {'true': 2, 'false': 4, 'cond': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(40, tracer) )
      tree.add( self.__EXPR() )
      tree.add( self.expect(80, tracer) )
      tree.add( self.__EXPR() )
    elif  self.sym.getId() == 88: # 'decr'
      tree.astTransform = AstTransformNodeCreator('PostDecr', {'var': 0})
      if left:
        tree.add(left)
      return self.expect( 88, tracer )
    elif  self.sym.getId() == 64: # 'rshift'
      tree.astTransform = AstTransformNodeCreator('RightShift', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(64, tracer) )
      tree.add( self.__EXPR( self.infixBp0[64] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 100: # 'bitor'
      tree.astTransform = AstTransformNodeCreator('BitOR', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(100, tracer) )
      tree.add( self.__EXPR( self.infixBp0[100] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 130: # 'lbrace'
      tree.astTransform = AstTransformNodeCreator('TypeInitializion', {'type': 1, 'initializer': 4})
      if left:
        tree.add(left)
      tree.add( self.expect(130, tracer) )
      tree.add( self.__GEN13() )
      tree.add( self._TRAILING_COMMA_OPT() )
      tree.add( self.expect(18, tracer) )
    elif  self.sym.getId() == 70: # 'mod'
      tree.astTransform = AstTransformNodeCreator('Mod', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(70, tracer) )
      tree.add( self.__EXPR( self.infixBp0[70] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 123: # 'bitandeq'
      tree.astTransform = AstTransformNodeCreator('ANDAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(123, tracer) )
      tree.add( self.__EXPR( self.infixBp0[123] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 63: # 'gt'
      tree.astTransform = AstTransformNodeCreator('GreaterThan', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(63, tracer) )
      tree.add( self.__EXPR( self.infixBp0[63] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 113: # 'lsquare'
      tree.astTransform = AstTransformNodeCreator('ArrayIndex', {'params': 2, 'name': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(113, tracer) )
      tree.add( self.__GEN5() )
      tree.add( self.expect(122, tracer) )
    elif  self.sym.getId() == 92: # 'incr'
      tree.astTransform = AstTransformNodeCreator('PostIncr', {'var': 0})
      if left:
        tree.add(left)
      return self.expect( 92, tracer )
    elif  self.sym.getId() == 78: # 'diveq'
      tree.astTransform = AstTransformNodeCreator('DivideAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(78, tracer) )
      tree.add( self.__EXPR( self.infixBp0[78] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 112: # 'bitand'
      tree.astTransform = AstTransformNodeCreator('BitAND', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(112, tracer) )
      tree.add( self.__EXPR( self.infixBp0[112] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 111: # 'bitoreq'
      tree.astTransform = AstTransformNodeCreator('ORAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(111, tracer) )
      tree.add( self.__EXPR( self.infixBp0[111] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 114: # 'eq'
      tree.astTransform = AstTransformNodeCreator('Equals', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(114, tracer) )
      tree.add( self.__EXPR( self.infixBp0[114] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 65: # 'addeq'
      tree.astTransform = AstTransformNodeCreator('AddAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(65, tracer) )
      tree.add( self.__EXPR( self.infixBp0[65] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 120: # 'lteq'
      tree.astTransform = AstTransformNodeCreator('LessThanEq', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(120, tracer) )
      tree.add( self.__EXPR( self.infixBp0[120] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 117: # 'bitxoreq'
      tree.astTransform = AstTransformNodeCreator('XORAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(117, tracer) )
      tree.add( self.__EXPR( self.infixBp0[117] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 61: # 'subeq'
      tree.astTransform = AstTransformNodeCreator('SubtractAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(61, tracer) )
      tree.add( self.__EXPR( self.infixBp0[61] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 81: # 'assign'
      tree.astTransform = AstTransformNodeCreator('Assign', {'var': 0, 'value': 2})
      if left:
        tree.add(left)
      tree.add( self.expect(81, tracer) )
      tree.add( self.__EXPR( self.infixBp0[81] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 1: # 'arrow'
      tree.astTransform = AstTransformNodeCreator('DerefMemberSelect', {'member': 2, 'object': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(1, tracer) )
      tree.add( self.__EXPR() )
    elif  self.sym.getId() == 93: # 'gteq'
      tree.astTransform = AstTransformNodeCreator('GreaterThanEq', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(93, tracer) )
      tree.add( self.__EXPR( self.infixBp0[93] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 69: # 'add'
      tree.astTransform = AstTransformNodeCreator('Add', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(69, tracer) )
      tree.add( self.__EXPR( self.infixBp0[69] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 75: # 'muleq'
      tree.astTransform = AstTransformNodeCreator('MultiplyAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(75, tracer) )
      tree.add( self.__EXPR( self.infixBp0[75] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 96: # 'dot'
      tree.astTransform = AstTransformNodeCreator('MemberSelect', {'member': 2, 'object': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(96, tracer) )
      tree.add( self.__EXPR() )
    elif  self.sym.getId() == 11: # 'rshifteq'
      tree.astTransform = AstTransformNodeCreator('RightShiftAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(11, tracer) )
      tree.add( self.__EXPR( self.infixBp0[11] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 5: # 'comma'
      tree.astTransform = AstTransformNodeCreator('Comma', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(5, tracer) )
      tree.add( self.__EXPR( self.infixBp0[5] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 106: # 'bitxor'
      tree.astTransform = AstTransformNodeCreator('BitXOR', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(106, tracer) )
      tree.add( self.__EXPR( self.infixBp0[106] ) )
      tree.isInfix = True
    return tree
  infixBp1 = {
    86: 1000,
    113: 1000,
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
    tree = ParseTree( NonTerminal(140, '_direct_abstract_declarator') )
    if self.sym.getId() == 252: # direct_abstract_declarator_opt
      tree.astTransform = AstTransformSubstitution(0)
      return self.expect( 252, tracer )
    elif self.sym.getId() == 86: # 'lparen'
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(86, tracer) )
      tree.add( self._ABSTRACT_DECLARATOR() )
      tree.add( self.expect(118, tracer) )
    return tree
  def led1(self, left, tracer):
    tree = ParseTree( NonTerminal(140, '_direct_abstract_declarator') )
    if  self.sym.getId() == 113: # 'lsquare'
      tree.astTransform = AstTransformSubstitution(0)
      if left:
        tree.add(left)
      tree.add( self.expect(113, tracer) )
      tree.add( self._DIRECT_ABSTRACT_DECLARATOR_EXPR() )
      tree.add( self.expect(122, tracer) )
    elif  self.sym.getId() == 86: # 'lparen'
      tree.astTransform = AstTransformSubstitution(0)
      if left:
        tree.add(left)
      tree.add( self.expect(86, tracer) )
      tree.add( self._PARAMETER_TYPE_LIST_OPT() )
      tree.add( self.expect(118, tracer) )
    return tree
  infixBp2 = {
    86: 1000,
    113: 1000,
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
    if self.sym.getId() == 60: # 'identifier'
      tree.astTransform = AstTransformSubstitution(0)
      return self.expect( 60, tracer )
    elif self.sym.getId() == 137: # _direct_declarator
      tree.astTransform = AstTransformSubstitution(0)
      return self.expect( 137, tracer )
    elif self.sym.getId() == 86: # 'lparen'
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(86, tracer) )
      tree.add( self._DECLARATOR() )
      tree.add( self.expect(118, tracer) )
    return tree
  def led2(self, left, tracer):
    tree = ParseTree( NonTerminal(137, '_direct_declarator') )
    if  self.sym.getId() == 86: # 'lparen'
      tree.astTransform = AstTransformSubstitution(0)
      if left:
        tree.add(left)
      tree.add( self.expect(86, tracer) )
      tree.add( self._DIRECT_DECLARATOR_PARAMETER_LIST() )
      tree.add( self.expect(118, tracer) )
    elif  self.sym.getId() == 113: # 'lsquare'
      tree.astTransform = AstTransformSubstitution(0)
      if left:
        tree.add(left)
      tree.add( self.expect(113, tracer) )
      tree.add( self._DIRECT_DECLARATOR_EXPR() )
      tree.add( self.expect(122, tracer) )
    return tree
