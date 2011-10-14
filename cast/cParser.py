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
  TERMINAL_DEFINE = 0
  TERMINAL_SIZEOF_SEPARATOR = 1
  TERMINAL_CONTINUE = 105
  TERMINAL_DEFINED = 3
  TERMINAL_ADDEQ = 4
  TERMINAL_DEFINE_FUNCTION = 5
  TERMINAL_NOT = 107
  TERMINAL_MODEQ = 7
  TERMINAL_ASSIGN = 17
  TERMINAL_COMMA_VA_ARGS = 9
  TERMINAL_LSHIFT = 55
  TERMINAL_INTEGER_CONSTANT = 11
  TERMINAL_CSOURCE = 12
  TERMINAL_DIVEQ = 13
  TERMINAL_SUBEQ = 14
  TERMINAL_TYPEDEF_IDENTIFIER = 15
  TERMINAL_LPAREN_CAST = 16
  TERMINAL_DECIMAL_FLOATING_CONSTANT = 8
  TERMINAL_DECR = 82
  TERMINAL_CONST = 19
  TERMINAL__COMPLEX = 58
  TERMINAL_SEPARATOR = 21
  TERMINAL_HEXADECIMAL_FLOATING_CONSTANT = 22
  TERMINAL_QUESTIONMARK = 84
  TERMINAL_POUND = 24
  TERMINAL_VOLATILE = 25
  TERMINAL_BREAK = 113
  TERMINAL_COMMA = 27
  TERMINAL_POUNDPOUND = 28
  TERMINAL_FLOATING_CONSTANT = 29
  TERMINAL_RSHIFT = 60
  TERMINAL_UNIVERSAL_CHARACTER_NAME = 114
  TERMINAL_HEADER_GLOBAL = 32
  TERMINAL_ENUMERATION_CONSTANT = 33
  TERMINAL_HEADER_LOCAL = 35
  TERMINAL_IMAGINARY = 36
  TERMINAL_PRAGMA = 38
  TERMINAL_DEFINED_SEPARATOR = 39
  TERMINAL_INLINE = 40
  TERMINAL_IDENTIFIER = 41
  TERMINAL_INCLUDE = 116
  TERMINAL_ERROR = 43
  TERMINAL_BITAND = 90
  TERMINAL_PP_NUMBER = 45
  TERMINAL__DIRECT_ABSTRACT_DECLARATOR = 46
  TERMINAL__DIRECT_DECLARATOR = 37
  TERMINAL_LPAREN = 118
  TERMINAL_TRAILING_COMMA = 49
  TERMINAL_CHARACTER_CONSTANT = 50
  TERMINAL_UNDEF = 51
  TERMINAL_IF = 52
  TERMINAL_STATIC = 86
  TERMINAL_STRING_LITERAL = 53
  TERMINAL_TILDE = 54
  TERMINAL_LINE = 10
  TERMINAL__IMAGINARY = 56
  TERMINAL_DO = 66
  TERMINAL_IFDEF = 20
  TERMINAL_SUB = 59
  TERMINAL_WHILE = 30
  TERMINAL_TYPEDEF = 61
  TERMINAL_IFNDEF = 62
  TERMINAL_ADD = 63
  TERMINAL_ARROW = 85
  TERMINAL_MOD = 65
  TERMINAL_EXTERN = 57
  TERMINAL__EXPR = 67
  TERMINAL_ELIF = 68
  TERMINAL_MUL = 70
  TERMINAL_ELIPSIS = 71
  TERMINAL_FOR = 72
  TERMINAL_ELSE = 73
  TERMINAL_DIV = 74
  TERMINAL_SEMI = 75
  TERMINAL_AUTO = 64
  TERMINAL_AMPERSAND = 77
  TERMINAL_COLON = 78
  TERMINAL_REGISTER = 79
  TERMINAL_FUNCTION_DEFINITION_HINT = 47
  TERMINAL_BOOL = 81
  TERMINAL_STRUCT = 18
  TERMINAL_LBRACE = 98
  TERMINAL_ASTERISK = 23
  TERMINAL_VOID = 48
  TERMINAL_MULEQ = 34
  TERMINAL_SIZEOF = 87
  TERMINAL_INCR = 88
  TERMINAL_NUMBER = 125
  TERMINAL_FUNCTION_PROTOTYPE_HINT = 44
  TERMINAL_CHAR = 91
  TERMINAL_AND = 99
  TERMINAL_DOT = 93
  TERMINAL_OR = 94
  TERMINAL_BITNOT = 95
  TERMINAL_SHORT = 96
  TERMINAL_RESTRICT = 97
  TERMINAL_ENUM = 83
  TERMINAL_WARNING = 80
  TERMINAL_COMPLEX = 92
  TERMINAL_BITOR = 100
  TERMINAL_INT = 101
  TERMINAL_HEADER_NAME = 117
  TERMINAL_RBRACE = 102
  TERMINAL_NEQ = 103
  TERMINAL_BITXOR = 104
  TERMINAL_LONG = 2
  TERMINAL_GOTO = 106
  TERMINAL_LSQUARE = 6
  TERMINAL_EQ = 108
  TERMINAL_BITOREQ = 109
  TERMINAL_SWITCH = 110
  TERMINAL_FLOAT = 111
  TERMINAL_DEFAULT = 112
  TERMINAL_RSQUARE = 26
  TERMINAL_LTEQ = 31
  TERMINAL_BITXOREQ = 115
  TERMINAL_DOUBLE = 42
  TERMINAL_DECLARATOR_HINT = 76
  TERMINAL_RETURN = 69
  TERMINAL_GTEQ = 119
  TERMINAL_BITANDEQ = 120
  TERMINAL_SIGNED = 121
  TERMINAL_RPAREN = 122
  TERMINAL_LT = 123
  TERMINAL_UNION = 124
  TERMINAL_LSHIFTEQ = 89
  TERMINAL_CASE = 126
  TERMINAL_UNSIGNED = 127
  TERMINAL_EXCLAMATION_POINT = 128
  TERMINAL_ELSE_IF = 129
  TERMINAL_GT = 130
  TERMINAL_RSHIFTEQ = 131
  TERMINAL_ENDIF = 132
  TERMINAL__BOOL = 133
  terminal_str = {
    0: 'define',
    1: 'sizeof_separator',
    105: 'continue',
    3: 'defined',
    4: 'addeq',
    5: 'define_function',
    107: 'not',
    7: 'modeq',
    17: 'assign',
    9: 'comma_va_args',
    55: 'lshift',
    11: 'integer_constant',
    12: 'csource',
    13: 'diveq',
    14: 'subeq',
    15: 'typedef_identifier',
    16: 'lparen_cast',
    8: 'decimal_floating_constant',
    82: 'decr',
    19: 'const',
    58: '_complex',
    21: 'separator',
    22: 'hexadecimal_floating_constant',
    84: 'questionmark',
    24: 'pound',
    25: 'volatile',
    113: 'break',
    27: 'comma',
    28: 'poundpound',
    29: 'floating_constant',
    60: 'rshift',
    114: 'universal_character_name',
    32: 'header_global',
    33: 'enumeration_constant',
    35: 'header_local',
    36: 'imaginary',
    38: 'pragma',
    39: 'defined_separator',
    40: 'inline',
    41: 'identifier',
    116: 'include',
    43: 'error',
    90: 'bitand',
    45: 'pp_number',
    46: '_direct_abstract_declarator',
    37: '_direct_declarator',
    118: 'lparen',
    49: 'trailing_comma',
    50: 'character_constant',
    51: 'undef',
    52: 'if',
    86: 'static',
    53: 'string_literal',
    54: 'tilde',
    10: 'line',
    56: '_imaginary',
    66: 'do',
    20: 'ifdef',
    59: 'sub',
    30: 'while',
    61: 'typedef',
    62: 'ifndef',
    63: 'add',
    85: 'arrow',
    65: 'mod',
    57: 'extern',
    67: '_expr',
    68: 'elif',
    70: 'mul',
    71: 'elipsis',
    72: 'for',
    73: 'else',
    74: 'div',
    75: 'semi',
    64: 'auto',
    77: 'ampersand',
    78: 'colon',
    79: 'register',
    47: 'function_definition_hint',
    81: 'bool',
    18: 'struct',
    98: 'lbrace',
    23: 'asterisk',
    48: 'void',
    34: 'muleq',
    87: 'sizeof',
    88: 'incr',
    125: 'number',
    44: 'function_prototype_hint',
    91: 'char',
    99: 'and',
    93: 'dot',
    94: 'or',
    95: 'bitnot',
    96: 'short',
    97: 'restrict',
    83: 'enum',
    80: 'warning',
    92: 'complex',
    100: 'bitor',
    101: 'int',
    117: 'header_name',
    102: 'rbrace',
    103: 'neq',
    104: 'bitxor',
    2: 'long',
    106: 'goto',
    6: 'lsquare',
    108: 'eq',
    109: 'bitoreq',
    110: 'switch',
    111: 'float',
    112: 'default',
    26: 'rsquare',
    31: 'lteq',
    115: 'bitxoreq',
    42: 'double',
    76: 'declarator_hint',
    69: 'return',
    119: 'gteq',
    120: 'bitandeq',
    121: 'signed',
    122: 'rparen',
    123: 'lt',
    124: 'union',
    89: 'lshifteq',
    126: 'case',
    127: 'unsigned',
    128: 'exclamation_point',
    129: 'else_if',
    130: 'gt',
    131: 'rshifteq',
    132: 'endif',
    133: '_bool',
  }
  nonterminal_str = {
    134: '_gen13',
    135: '_gen14',
    136: 'replacement_list',
    137: 'direct_declarator_parameter_list',
    138: '_direct_abstract_declarator',
    139: 'token',
    140: 'enumeration_constant',
    141: 'enumerator_assignment',
    142: 'terminals',
    143: 'define_func_param',
    144: 'designation',
    145: 'expression_opt',
    146: 'elipsis_opt',
    147: 'include_line',
    148: 'static_opt',
    149: '_gen23',
    150: '_gen15',
    151: 'declarator_initializer',
    152: '_gen18',
    153: 'pp_tokens',
    154: '_gen24',
    155: 'statement',
    156: 'pp_directive',
    157: 'initializer',
    158: 'struct_declaration',
    159: 'pointer',
    160: '_gen0',
    161: 'translation_unit',
    162: 'initializer_list_item',
    163: 'parameter_declaration_sub_sub',
    164: 'declarator',
    165: 'labeled_statement',
    166: 'abstract_declarator',
    167: '_gen21',
    168: 'external_declaration',
    169: '_gen7',
    170: 'pp_nodes',
    171: 'expression_statement',
    172: 'trailing_comma_opt',
    173: 'if_section',
    174: 'defined_identifier',
    175: 'selection_statement',
    176: 'constant',
    177: 'external_function',
    178: 'control_line',
    179: 'jump_statement',
    180: 'sizeof_body',
    181: 'iteration_statement',
    182: 'external_declarator_list',
    183: 'if_part',
    184: 'elseif_part',
    185: '_gen1',
    186: 'external_prototype',
    187: 'pointer_opt',
    188: '_gen36',
    189: 'direct_abstract_declarator_expr',
    190: 'else_part',
    191: 'direct_declarator_expr',
    192: 'declaration_specifier',
    193: '_gen8',
    194: '_gen16',
    195: '_gen9',
    196: '_gen35',
    197: '_gen2',
    198: 'undef_line',
    199: '_expr',
    200: 'struct_declarator',
    201: '_gen17',
    202: '_gen40',
    203: 'block_item_list',
    204: '_gen37',
    205: '_gen3',
    206: 'direct_declarator_modifier',
    207: '_gen30',
    208: 'designator',
    209: 'declaration_list',
    210: '_gen10',
    211: 'declaration',
    212: 'struct_specifier',
    213: 'parameter_declaration',
    214: '_direct_declarator',
    215: 'block_item',
    216: '_gen38',
    217: '_gen5',
    218: '_gen27',
    219: 'compound_statement',
    220: 'for_init',
    221: 'for_cond',
    222: 'else_if_statement_list',
    223: 'type_name',
    224: 'error_line',
    225: 'typedef_name',
    226: '_gen11',
    227: 'pp_nodes_list',
    228: 'punctuator',
    229: 'specifier_qualifier',
    230: '_gen25',
    231: 'struct_or_union_sub',
    232: 'define_line',
    233: 'parameter_type_list_opt',
    234: 'pp_file',
    235: '_gen28',
    236: 'pragma_line',
    237: 'init_declarator_list',
    238: '_gen4',
    239: '_gen31',
    240: '_gen22',
    241: '_gen32',
    242: 'enum_specifier',
    243: '_gen12',
    244: 'struct_or_union_body',
    245: 'direct_declarator_modifier_list_opt',
    246: '_gen20',
    247: 'type_specifier',
    248: 'enum_specifier_sub',
    249: 'else_statement',
    250: 'warning_line',
    251: '_gen6',
    252: 'va_args',
    253: 'direct_declarator_size',
    254: 'identifier',
    255: 'enum_specifier_body',
    256: 'direct_abstract_declarator_opt',
    257: '_gen26',
    258: 'pp',
    259: 'for_incr',
    260: 'storage_class_specifier',
    261: 'line_line',
    262: '_gen39',
    263: 'else_if_statement',
    264: '_gen41',
    265: 'parameter_type_list',
    266: 'include_type',
    267: '_gen34',
    268: 'type_qualifier',
    269: 'enumerator',
    270: '_gen33',
    271: 'struct_declarator_body',
    272: 'function_specifier',
    273: 'union_specifier',
    274: 'init_declarator',
    275: '_gen29',
    276: 'type_qualifier_list_opt',
    277: '_gen19',
    278: 'pointer_sub',
    279: 'keyword',
    280: 'parameter_declaration_sub',
  }
  str_terminal = {
    'define': 0,
    'sizeof_separator': 1,
    'continue': 105,
    'defined': 3,
    'addeq': 4,
    'define_function': 5,
    'not': 107,
    'modeq': 7,
    'assign': 17,
    'comma_va_args': 9,
    'lshift': 55,
    'integer_constant': 11,
    'csource': 12,
    'diveq': 13,
    'subeq': 14,
    'typedef_identifier': 15,
    'lparen_cast': 16,
    'decimal_floating_constant': 8,
    'decr': 82,
    'const': 19,
    '_complex': 58,
    'separator': 21,
    'hexadecimal_floating_constant': 22,
    'questionmark': 84,
    'pound': 24,
    'volatile': 25,
    'break': 113,
    'comma': 27,
    'poundpound': 28,
    'floating_constant': 29,
    'rshift': 60,
    'universal_character_name': 114,
    'header_global': 32,
    'enumeration_constant': 33,
    'header_local': 35,
    'imaginary': 36,
    'pragma': 38,
    'defined_separator': 39,
    'inline': 40,
    'identifier': 41,
    'include': 116,
    'error': 43,
    'bitand': 90,
    'pp_number': 45,
    '_direct_abstract_declarator': 46,
    '_direct_declarator': 37,
    'lparen': 118,
    'trailing_comma': 49,
    'character_constant': 50,
    'undef': 51,
    'if': 52,
    'static': 86,
    'string_literal': 53,
    'tilde': 54,
    'line': 10,
    '_imaginary': 56,
    'do': 66,
    'ifdef': 20,
    'sub': 59,
    'while': 30,
    'typedef': 61,
    'ifndef': 62,
    'add': 63,
    'arrow': 85,
    'mod': 65,
    'extern': 57,
    '_expr': 67,
    'elif': 68,
    'mul': 70,
    'elipsis': 71,
    'for': 72,
    'else': 73,
    'div': 74,
    'semi': 75,
    'auto': 64,
    'ampersand': 77,
    'colon': 78,
    'register': 79,
    'function_definition_hint': 47,
    'bool': 81,
    'struct': 18,
    'lbrace': 98,
    'asterisk': 23,
    'void': 48,
    'muleq': 34,
    'sizeof': 87,
    'incr': 88,
    'number': 125,
    'function_prototype_hint': 44,
    'char': 91,
    'and': 99,
    'dot': 93,
    'or': 94,
    'bitnot': 95,
    'short': 96,
    'restrict': 97,
    'enum': 83,
    'warning': 80,
    'complex': 92,
    'bitor': 100,
    'int': 101,
    'header_name': 117,
    'rbrace': 102,
    'neq': 103,
    'bitxor': 104,
    'long': 2,
    'goto': 106,
    'lsquare': 6,
    'eq': 108,
    'bitoreq': 109,
    'switch': 110,
    'float': 111,
    'default': 112,
    'rsquare': 26,
    'lteq': 31,
    'bitxoreq': 115,
    'double': 42,
    'declarator_hint': 76,
    'return': 69,
    'gteq': 119,
    'bitandeq': 120,
    'signed': 121,
    'rparen': 122,
    'lt': 123,
    'union': 124,
    'lshifteq': 89,
    'case': 126,
    'unsigned': 127,
    'exclamation_point': 128,
    'else_if': 129,
    'gt': 130,
    'rshifteq': 131,
    'endif': 132,
    '_bool': 133,
  }
  str_nonterminal = {
    '_gen13': 134,
    '_gen14': 135,
    'replacement_list': 136,
    'direct_declarator_parameter_list': 137,
    '_direct_abstract_declarator': 138,
    'token': 139,
    'enumeration_constant': 140,
    'enumerator_assignment': 141,
    'terminals': 142,
    'define_func_param': 143,
    'designation': 144,
    'expression_opt': 145,
    'elipsis_opt': 146,
    'include_line': 147,
    'static_opt': 148,
    '_gen23': 149,
    '_gen15': 150,
    'declarator_initializer': 151,
    '_gen18': 152,
    'pp_tokens': 153,
    '_gen24': 154,
    'statement': 155,
    'pp_directive': 156,
    'initializer': 157,
    'struct_declaration': 158,
    'pointer': 159,
    '_gen0': 160,
    'translation_unit': 161,
    'initializer_list_item': 162,
    'parameter_declaration_sub_sub': 163,
    'declarator': 164,
    'labeled_statement': 165,
    'abstract_declarator': 166,
    '_gen21': 167,
    'external_declaration': 168,
    '_gen7': 169,
    'pp_nodes': 170,
    'expression_statement': 171,
    'trailing_comma_opt': 172,
    'if_section': 173,
    'defined_identifier': 174,
    'selection_statement': 175,
    'constant': 176,
    'external_function': 177,
    'control_line': 178,
    'jump_statement': 179,
    'sizeof_body': 180,
    'iteration_statement': 181,
    'external_declarator_list': 182,
    'if_part': 183,
    'elseif_part': 184,
    '_gen1': 185,
    'external_prototype': 186,
    'pointer_opt': 187,
    '_gen36': 188,
    'direct_abstract_declarator_expr': 189,
    'else_part': 190,
    'direct_declarator_expr': 191,
    'declaration_specifier': 192,
    '_gen8': 193,
    '_gen16': 194,
    '_gen9': 195,
    '_gen35': 196,
    '_gen2': 197,
    'undef_line': 198,
    '_expr': 199,
    'struct_declarator': 200,
    '_gen17': 201,
    '_gen40': 202,
    'block_item_list': 203,
    '_gen37': 204,
    '_gen3': 205,
    'direct_declarator_modifier': 206,
    '_gen30': 207,
    'designator': 208,
    'declaration_list': 209,
    '_gen10': 210,
    'declaration': 211,
    'struct_specifier': 212,
    'parameter_declaration': 213,
    '_direct_declarator': 214,
    'block_item': 215,
    '_gen38': 216,
    '_gen5': 217,
    '_gen27': 218,
    'compound_statement': 219,
    'for_init': 220,
    'for_cond': 221,
    'else_if_statement_list': 222,
    'type_name': 223,
    'error_line': 224,
    'typedef_name': 225,
    '_gen11': 226,
    'pp_nodes_list': 227,
    'punctuator': 228,
    'specifier_qualifier': 229,
    '_gen25': 230,
    'struct_or_union_sub': 231,
    'define_line': 232,
    'parameter_type_list_opt': 233,
    'pp_file': 234,
    '_gen28': 235,
    'pragma_line': 236,
    'init_declarator_list': 237,
    '_gen4': 238,
    '_gen31': 239,
    '_gen22': 240,
    '_gen32': 241,
    'enum_specifier': 242,
    '_gen12': 243,
    'struct_or_union_body': 244,
    'direct_declarator_modifier_list_opt': 245,
    '_gen20': 246,
    'type_specifier': 247,
    'enum_specifier_sub': 248,
    'else_statement': 249,
    'warning_line': 250,
    '_gen6': 251,
    'va_args': 252,
    'direct_declarator_size': 253,
    'identifier': 254,
    'enum_specifier_body': 255,
    'direct_abstract_declarator_opt': 256,
    '_gen26': 257,
    'pp': 258,
    'for_incr': 259,
    'storage_class_specifier': 260,
    'line_line': 261,
    '_gen39': 262,
    'else_if_statement': 263,
    '_gen41': 264,
    'parameter_type_list': 265,
    'include_type': 266,
    '_gen34': 267,
    'type_qualifier': 268,
    'enumerator': 269,
    '_gen33': 270,
    'struct_declarator_body': 271,
    'function_specifier': 272,
    'union_specifier': 273,
    'init_declarator': 274,
    '_gen29': 275,
    'type_qualifier_list_opt': 276,
    '_gen19': 277,
    'pointer_sub': 278,
    'keyword': 279,
    'parameter_declaration_sub': 280,
  }
  terminal_count = 134
  nonterminal_count = 147
  parse_table = [
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 5, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 5, -1, -1, -1, 5, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 5, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 9, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 12, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, 337, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 337, -1, -1, 337, 337, -1, -1, -1, -1, -1, 337, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 337, 223, 337, -1, -1, -1, -1, -1, 337, -1, -1, -1, -1, -1, -1, -1, -1, 337, 337, -1, -1, 337, -1, -1, 337, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 337, -1, -1, -1, 337, -1, -1, 337, -1, -1, -1, -1, 337, -1, -1, -1, -1, 337, 337, -1, -1, -1, 337, -1, -1, -1, -1, -1, -1, -1, -1, -1, 337, -1, -1, -1, -1, -1, -1, -1, -1, -1, 337, -1, -1, 337, -1, -1, 337, -1, -1, -1, -1, -1, 337],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, 72, -1, 47, -1, 47, 47, -1, -1, -1, 102, -1, -1, 47, -1, -1, 47, 72, 72, -1, -1, -1, -1, 47, 72, 47, 47, 47, 102, 72, 47, -1, 102, 47, -1, -1, -1, -1, -1, 72, 88, 72, -1, -1, 191, -1, -1, 72, -1, 102, -1, 72, 186, 47, 47, 72, 72, 72, 47, 47, 72, -1, 47, 72, 47, 72, -1, -1, 72, -1, 47, 72, 72, 47, 47, -1, 47, 47, 72, -1, -1, 47, 72, 47, 47, 72, 72, 47, 47, -1, 72, -1, 47, 47, -1, 72, 72, 47, 47, 47, 72, 47, 47, 47, 72, 72, -1, 47, 47, 72, 72, 72, 72, -1, 47, -1, -1, 47, 47, 47, 72, 47, 47, 72, -1, 72, 72, 47, -1, 47, 47, -1, 72],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 180, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 109, -1, -1, -1, -1, -1, -1, -1, -1, -1, 60, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 60, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, 437, -1, 421, -1, 286, 34, 29, -1, -1, 227, -1, 20, 201, -1, -1, 121, 157, 100, -1, -1, 418, -1, 189, 23, 271, 208, 135, -1, 403, 116, -1, -1, 457, -1, 193, -1, -1, -1, 250, 78, 380, -1, -1, -1, -1, -1, 108, -1, 441, -1, 151, 253, 452, 228, -1, 444, -1, 65, 248, 255, -1, 50, 107, 263, 28, -1, -1, 295, -1, 238, 181, 74, 119, 266, -1, -1, 93, 252, -1, 81, 204, 315, 220, 313, 244, 389, 439, 258, 136, 321, 131, 122, 144, -1, 63, 280, 240, 106, 243, 440, 90, 115, 176, 459, 26, 75, 358, 320, 278, 451, 171, 281, 450, 329, -1, 370, 160, 172, 290, 76, 210, 27, 133, 58, 99, 36, 214, -1, 146, 267, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, 367, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 367, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 367, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 399, -1, -1, -1, -1, 399, -1, -1, -1, -1, -1, -1, 399, -1, -1, -1, -1, -1, 399, -1, -1, -1, 399, -1, -1, -1, -1, -1, -1, -1, 399, -1, -1, -1, -1, -1, -1, -1, -1, 399, -1, -1, 399, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 399, -1, -1, -1, -1, -1, -1, -1, 420, -1, -1, -1, -1, -1, -1, 399, -1, -1, -1, -1, 399, 399, -1, 399, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 399, -1, -1, -1, 420, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 126, -1, -1, -1, -1, 126, -1, -1, -1, -1, -1, -1, 126, -1, -1, -1, -1, -1, 126, -1, -1, -1, 126, -1, -1, -1, -1, -1, -1, -1, 126, -1, -1, -1, -1, -1, -1, -1, -1, 126, -1, -1, 126, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 126, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 126, -1, -1, -1, 113, 126, 126, -1, 126, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 126, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 335, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 335, -1, -1, -1, 335, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 335, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 335, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 25, -1, -1, -1, -1, -1, -1, -1, -1, -1, 30, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 30, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 130, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, 400, -1, -1, -1, -1, 64, -1, -1, -1, -1, 64, 400, -1, -1, -1, -1, -1, 64, -1, -1, -1, -1, -1, 64, -1, -1, -1, 64, -1, -1, -1, -1, -1, -1, -1, 64, -1, -1, -1, -1, -1, -1, -1, -1, 64, -1, -1, 64, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 64, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 64, -1, -1, -1, -1, 64, 64, -1, 64, -1, -1, 400, -1, -1, -1, -1, 64, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 64, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 175, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 343, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 153, -1, -1, -1, -1, 153, -1, -1, -1, -1, -1, -1, 153, -1, -1, -1, -1, -1, 153, 234, -1, -1, 153, -1, -1, -1, -1, -1, -1, -1, 153, -1, -1, -1, -1, -1, -1, -1, -1, 153, -1, 39, 153, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 234, 153, -1, 338, -1, -1, 234, -1, -1, 153, -1, -1, -1, -1, -1, -1, 153, -1, -1, -1, -1, 153, 153, -1, 153, -1, -1, -1, -1, -1, -1, -1, 166, -1, -1, -1, -1, -1, -1, 338, 338, -1, -1, -1, 39, -1, 447, 338, -1, -1, -1, -1, 153, -1, -1, -1, -1, -1, -1, -1, 447, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 142, -1, -1, -1, -1, 142, -1, -1, -1, -1, -1, -1, 142, -1, -1, -1, -1, -1, 142, -1, -1, -1, 142, -1, -1, -1, -1, -1, -1, -1, 142, -1, -1, -1, -1, -1, -1, -1, -1, 142, -1, -1, 142, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 142, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 142, -1, -1, -1, -1, 142, 142, -1, 142, -1, -1, -1, -1, -1, -1, -1, 212, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 142, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, 435, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 435, -1, -1, 435, 435, -1, -1, -1, 435, -1, 435, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 435, -1, -1, -1, 435, 435, -1, -1, -1, -1, -1, 435, -1, -1, -1, -1, -1, -1, -1, -1, -1, 435, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 435, -1, -1, -1, -1, 435, -1, -1, -1, -1, -1, -1, -1, 435, -1, -1, -1, -1, 435, 435, -1, -1, -1, 435, -1, -1, -1, -1, -1, -1, -1, -1, -1, 435, -1, -1, -1, -1, -1, -1, 435, -1, -1, 435, -1, -1, 435, -1, -1, 435, -1, -1, -1, -1, -1, 435],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, 264, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 264, -1, -1, -1, 264, -1, -1, -1, -1, -1, -1, -1, -1, -1, 264, -1, -1, -1, 264, -1, -1, -1, -1, 264, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 264, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 446, -1, -1, 446, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 446, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, 289, -1, -1, -1, -1, 165, -1, -1, -1, -1, 289, 289, -1, -1, -1, -1, -1, 289, -1, -1, -1, -1, -1, 289, -1, -1, -1, 289, -1, -1, -1, -1, -1, -1, -1, 289, -1, -1, -1, -1, -1, -1, -1, -1, 289, -1, -1, 289, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 289, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 289, -1, -1, -1, -1, 289, 289, -1, 289, -1, -1, 289, -1, -1, -1, -1, 289, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 289, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, 84, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 84, -1, -1, -1, -1, -1, -1, -1, -1, -1, 372, -1, -1, -1, 372, -1, -1, -1, -1, 84, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 84, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 236, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 236, -1, -1, -1, 236, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 236, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 323, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 52, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 200, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 83, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 83, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 83, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, 287, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 287, -1, -1, 287, 287, -1, -1, -1, 287, -1, 287, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 287, -1, -1, -1, 287, 287, -1, -1, -1, -1, -1, 287, -1, -1, -1, -1, -1, -1, -1, -1, -1, 287, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 287, -1, -1, -1, -1, 287, -1, -1, -1, -1, -1, -1, -1, 287, -1, -1, -1, -1, 287, 287, -1, -1, -1, 287, 285, -1, -1, -1, -1, -1, -1, -1, -1, 287, -1, -1, -1, -1, -1, -1, 287, -1, -1, 287, -1, -1, 287, -1, -1, 287, -1, -1, -1, -1, -1, 287],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 213, -1, -1, 359, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 268, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 125, -1, -1, 125, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 125, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 69, -1, -1, -1, -1, 69, -1, -1, -1, -1, -1, -1, 69, -1, -1, -1, -1, -1, 69, -1, -1, -1, 69, -1, -1, -1, -1, -1, -1, -1, 69, -1, -1, -1, -1, -1, -1, -1, -1, 69, -1, -1, 69, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 69, -1, -1, -1, -1, -1, -1, -1, 69, -1, -1, -1, -1, -1, -1, 69, -1, -1, -1, -1, 69, 69, -1, 69, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 69, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 249, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 221, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 349, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 42, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 218, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 14, -1, -1, -1, 77, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 415, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 230, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 394, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 408, 148, -1, -1, -1, -1, -1, -1, 184, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 395, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 326, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 35, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 445, -1, -1, -1, -1, -1, 61, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 455, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 316, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, 22, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 216, -1, -1, -1, 22, -1, -1, -1, -1, -1, -1, -1, -1, -1, 22, -1, -1, -1, 22, -1, -1, -1, -1, 22, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 22, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, 94, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 375, -1, -1, -1, 94, -1, -1, -1, -1, -1, -1, -1, -1, -1, 94, -1, -1, -1, 94, -1, -1, -1, -1, 94, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 94, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 324, -1, -1, -1, -1, 324, -1, -1, 324, -1, -1, -1, 237, -1, 324, -1, -1, -1, 324, -1, -1, -1, 324, -1, -1, -1, -1, -1, -1, -1, 324, -1, -1, -1, -1, -1, -1, -1, -1, 324, -1, -1, 324, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 324, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 324, -1, -1, -1, 324, 324, 324, -1, 324, -1, -1, -1, -1, -1, -1, 324, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 324, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 232, -1, -1, -1, -1, 232, -1, -1, 232, -1, -1, -1, 232, -1, 232, -1, -1, -1, 232, -1, -1, -1, 232, -1, -1, -1, -1, -1, -1, -1, 232, -1, -1, -1, -1, -1, -1, -1, -1, 232, -1, -1, 232, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 232, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 232, -1, -1, -1, 232, 232, 232, -1, 232, -1, -1, -1, -1, -1, -1, 232, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 232, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, 303, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 303, -1, -1, 303, 373, -1, -1, -1, -1, -1, 373, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 33, -1, 303, -1, -1, -1, -1, -1, 303, -1, -1, -1, -1, -1, -1, -1, -1, 453, 303, -1, -1, 453, -1, -1, 453, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 453, -1, -1, -1, 303, -1, -1, 453, -1, -1, -1, -1, 303, -1, -1, -1, -1, 303, 373, -1, -1, -1, 303, -1, -1, -1, -1, -1, -1, -1, -1, -1, 303, -1, -1, -1, -1, -1, -1, -1, -1, -1, 303, -1, -1, 303, -1, -1, 303, -1, -1, -1, -1, -1, 303],
  [-1, -1, 183, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 183, -1, -1, 183, 183, -1, -1, -1, -1, -1, 183, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 183, -1, 183, -1, -1, -1, -1, -1, 183, -1, -1, -1, -1, -1, -1, -1, -1, 183, 183, -1, -1, 183, -1, -1, 183, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 183, -1, -1, -1, 183, -1, -1, 183, -1, -1, -1, -1, 183, -1, -1, -1, -1, 183, 183, -1, -1, -1, 183, -1, -1, -1, -1, -1, -1, -1, -1, -1, 183, -1, -1, -1, -1, -1, -1, -1, -1, -1, 183, -1, -1, 183, -1, -1, 183, -1, -1, -1, -1, -1, 183],
  [-1, -1, -1, -1, -1, -1, 56, -1, -1, -1, -1, 56, -1, -1, -1, -1, 56, 56, -1, -1, -1, -1, -1, 56, -1, -1, -1, -1, -1, 56, -1, -1, -1, 56, -1, -1, -1, -1, -1, -1, -1, 56, -1, -1, -1, -1, -1, -1, -1, -1, 56, -1, -1, 56, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 56, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 56, -1, -1, -1, -1, 56, 56, -1, 56, -1, -1, 56, -1, -1, -1, -1, 56, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 56, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, 328, -1, -1, -1, -1, -1, -1, 390, -1, -1, -1, -1, -1, 328, -1, -1, 328, 328, -1, -1, -1, 390, -1, 328, -1, 390, -1, -1, -1, -1, -1, -1, -1, -1, -1, 390, -1, -1, 328, 390, 328, -1, -1, -1, 390, -1, 328, -1, -1, -1, -1, -1, -1, -1, -1, 328, 328, -1, -1, 328, -1, -1, 328, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 328, -1, -1, -1, 328, -1, -1, 328, -1, -1, -1, -1, 328, -1, -1, -1, -1, 328, 328, -1, -1, -1, 328, -1, -1, -1, -1, -1, -1, -1, -1, -1, 328, -1, -1, -1, -1, -1, -1, 390, -1, -1, 328, -1, -1, 328, -1, -1, 328, -1, -1, -1, -1, -1, 328],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, 38, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 38, -1, -1, -1, 38, -1, -1, -1, -1, -1, -1, -1, -1, -1, 38, -1, -1, -1, 38, -1, -1, -1, -1, 38, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 38, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 246, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 246, -1, -1, -1, 246, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 272, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 246, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 59, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 62, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, 412, -1, -1, -1, -1, -1, -1, -1, -1, 412, -1, -1, -1, 412, 412, -1, 412, 412, -1, -1, -1, 412, -1, 412, -1, -1, -1, 412, 412, -1, -1, 412, -1, -1, -1, -1, -1, -1, 412, 412, 412, -1, -1, -1, -1, -1, 412, -1, 412, -1, 412, 412, -1, -1, -1, 412, 412, -1, -1, 412, -1, -1, 412, -1, 412, 412, -1, 412, -1, -1, 412, 262, -1, 412, -1, -1, -1, 412, -1, -1, 412, 412, -1, -1, 412, 412, 412, -1, 412, 412, -1, -1, -1, -1, 412, 412, 412, -1, -1, 412, 412, -1, -1, 412, 412, -1, -1, -1, 412, 412, 412, 412, -1, -1, -1, -1, 412, -1, -1, 412, -1, -1, 412, -1, 412, 412, -1, -1, -1, -1, 412, 412],
  [-1, -1, 302, -1, -1, -1, -1, -1, -1, -1, -1, 302, -1, -1, -1, 302, 302, -1, 302, 302, -1, -1, -1, 302, -1, 302, -1, -1, -1, 302, 302, -1, -1, 302, -1, -1, -1, -1, -1, -1, 302, 302, 302, -1, -1, -1, -1, -1, 302, -1, 302, -1, 302, 302, -1, -1, -1, 302, 302, -1, -1, 302, -1, -1, 302, -1, 302, 302, -1, 302, -1, -1, 302, -1, -1, 302, -1, -1, -1, 302, -1, -1, 302, 302, -1, -1, 302, 302, 302, -1, 302, 302, -1, -1, -1, -1, 302, 302, 302, -1, -1, 302, 302, -1, -1, 302, 302, -1, -1, -1, 302, 302, 302, 302, -1, -1, -1, -1, 302, -1, -1, 302, -1, -1, 302, -1, 302, 302, -1, -1, -1, -1, -1, 302],
  [-1, -1, 245, -1, -1, -1, -1, -1, -1, -1, -1, 245, -1, -1, -1, 245, 245, -1, 245, 245, -1, -1, -1, 245, -1, 245, -1, -1, -1, 245, 245, -1, -1, 245, -1, -1, -1, -1, -1, -1, 245, 245, 245, -1, -1, -1, -1, -1, 245, -1, 245, -1, 245, 245, -1, -1, -1, 245, 245, -1, -1, 245, -1, -1, 245, -1, 245, 245, -1, 245, -1, -1, 245, -1, -1, 245, -1, -1, -1, 245, -1, -1, 245, 245, -1, -1, 245, 245, 245, -1, 245, 245, -1, -1, -1, -1, 245, 245, 245, -1, -1, 245, 245, -1, -1, 245, 245, -1, -1, -1, 245, 245, 245, 245, -1, -1, -1, -1, 245, -1, -1, 245, -1, -1, 245, -1, 245, 245, -1, -1, -1, -1, -1, 245],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 46, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 10, -1, -1, -1, -1, -1, 10, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 318, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 10, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 426, -1, -1, -1, -1, 426, -1, -1, 283, -1, -1, -1, 426, -1, 283, -1, -1, -1, 426, -1, -1, -1, 426, -1, -1, -1, -1, -1, -1, -1, 426, -1, -1, -1, -1, -1, -1, -1, -1, 426, -1, -1, 426, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 426, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 426, -1, -1, -1, 283, 426, 426, -1, 426, -1, -1, -1, -1, -1, -1, 283, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 426, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, 43, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 345, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, 361, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 361, -1, -1, 361, 361, -1, -1, -1, -1, -1, 361, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 361, -1, 361, -1, -1, -1, -1, -1, 361, -1, -1, -1, -1, -1, -1, -1, -1, 361, 361, -1, -1, 361, -1, -1, 361, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 361, -1, -1, -1, 361, -1, -1, 361, -1, -1, -1, -1, 361, -1, -1, -1, -1, 361, 361, 361, -1, -1, 361, -1, -1, -1, -1, -1, -1, -1, -1, -1, 361, -1, -1, -1, -1, -1, -1, -1, -1, -1, 361, -1, -1, 361, -1, -1, 361, -1, -1, -1, -1, -1, 361],
  [-1, -1, 308, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 308, -1, -1, 308, 308, -1, -1, -1, -1, -1, 308, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 308, -1, 308, -1, -1, -1, -1, -1, 308, -1, -1, -1, -1, -1, -1, -1, -1, 308, 308, -1, -1, 308, -1, -1, 308, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 308, -1, -1, -1, 308, -1, -1, 308, -1, -1, -1, -1, 308, -1, -1, -1, -1, 308, 308, 308, -1, -1, 308, -1, -1, -1, -1, -1, -1, -1, -1, -1, 308, -1, -1, -1, -1, -1, -1, -1, -1, -1, 308, -1, -1, 308, -1, -1, 308, -1, -1, -1, -1, -1, 308],
  [-1, -1, 110, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 110, -1, -1, 110, 110, -1, -1, -1, -1, -1, 110, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 110, -1, 110, -1, -1, -1, -1, -1, 110, -1, -1, -1, -1, -1, -1, -1, -1, 110, 110, -1, -1, 110, -1, -1, 110, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 110, -1, -1, -1, 110, -1, -1, 110, -1, -1, -1, -1, 110, -1, -1, -1, -1, 110, 110, -1, -1, -1, 110, -1, -1, -1, -1, -1, -1, -1, -1, -1, 110, -1, -1, -1, -1, -1, -1, -1, -1, -1, 110, -1, -1, 110, -1, -1, 110, -1, -1, -1, -1, -1, 110],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 140, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, 197, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 197, -1, -1, 197, 197, -1, -1, -1, -1, -1, 197, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 197, -1, 197, -1, -1, -1, -1, -1, 197, -1, -1, -1, -1, -1, -1, -1, -1, 197, 197, -1, -1, 197, -1, -1, 197, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 197, -1, -1, -1, 197, -1, -1, 197, -1, -1, -1, -1, 197, -1, -1, -1, -1, 197, 197, -1, -1, -1, 197, -1, -1, -1, -1, -1, -1, -1, -1, -1, 197, -1, -1, -1, -1, -1, -1, -1, -1, -1, 197, -1, -1, 197, -1, -1, 197, -1, -1, -1, -1, -1, 197],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, 123, -1, -1, -1, -1, -1, -1, -1, -1, 304, -1, -1, -1, 123, 304, -1, 123, 123, -1, -1, -1, 304, -1, 123, -1, -1, -1, 304, 304, -1, -1, 304, -1, -1, -1, -1, -1, -1, 123, 304, 123, -1, -1, -1, -1, -1, 123, -1, 304, -1, 304, 304, -1, -1, -1, 123, 123, -1, -1, 123, -1, -1, 123, -1, 304, 304, -1, 304, -1, -1, 304, -1, -1, 304, -1, -1, -1, 123, -1, -1, 304, 123, -1, -1, 123, 304, 304, -1, 304, 123, -1, -1, -1, -1, 123, 123, 304, -1, -1, 123, -1, -1, -1, 304, 304, -1, -1, -1, 304, 123, 304, 304, -1, -1, -1, -1, 304, -1, -1, 123, -1, -1, 123, -1, 304, 123, -1, -1, -1, -1, -1, 123],
  [-1, -1, 381, -1, -1, -1, -1, -1, -1, -1, -1, 381, -1, -1, -1, 381, 381, -1, 381, 381, -1, -1, -1, 381, -1, 381, -1, -1, -1, 381, 381, -1, -1, 381, -1, -1, -1, -1, -1, -1, 381, 381, 381, -1, -1, -1, -1, -1, 381, -1, 381, -1, 381, 381, -1, -1, -1, 381, 381, -1, -1, 381, -1, -1, 381, -1, 381, 381, -1, 381, -1, -1, 381, -1, -1, 381, -1, -1, -1, 381, -1, -1, 381, 381, -1, -1, 381, 381, 381, -1, 381, 381, -1, -1, -1, -1, 381, 381, 381, -1, -1, 381, 360, -1, -1, 381, 381, -1, -1, -1, 381, 381, 381, 381, -1, -1, -1, -1, 381, -1, -1, 381, -1, -1, 381, -1, 381, 381, -1, -1, -1, -1, -1, 381],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 430, -1, -1, -1, -1, 430, -1, -1, -1, -1, -1, -1, 430, -1, -1, -1, -1, -1, 430, -1, -1, -1, 430, -1, -1, -1, -1, -1, -1, -1, 430, -1, -1, -1, -1, -1, -1, -1, -1, 430, -1, -1, 430, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 430, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 430, -1, -1, -1, -1, 430, 430, -1, 430, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 430, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 275, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 385, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, 57, -1, -1, -1, -1, -1, -1, -1, -1, 194, -1, -1, -1, 57, 194, -1, 57, 57, -1, -1, -1, 194, -1, 57, -1, -1, -1, 194, -1, -1, -1, 194, -1, -1, -1, -1, -1, -1, 57, 194, 57, -1, -1, -1, -1, -1, 57, -1, 194, -1, -1, 194, -1, -1, -1, 57, 57, -1, -1, 57, -1, -1, 57, -1, -1, 194, -1, -1, -1, -1, -1, -1, -1, 331, -1, -1, -1, 57, -1, -1, 194, 57, -1, -1, 57, 194, 194, -1, 194, 57, -1, -1, -1, -1, 57, 57, -1, -1, -1, 57, -1, -1, -1, -1, -1, -1, -1, -1, -1, 57, -1, -1, -1, -1, -1, -1, 194, -1, -1, 57, -1, -1, 57, -1, -1, 57, -1, -1, -1, -1, -1, 57],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 305, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, 174, -1, -1, -1, -1, -1, -1, -1, -1, 174, -1, -1, -1, 174, 174, -1, 174, 174, -1, -1, -1, 174, -1, 174, -1, -1, -1, 174, 174, -1, -1, 174, -1, -1, -1, -1, -1, -1, 174, 174, 174, -1, -1, -1, -1, -1, 174, -1, 174, -1, 174, 174, -1, -1, -1, 174, 174, -1, -1, 174, -1, -1, 174, -1, 174, 174, -1, 174, -1, -1, 174, 174, -1, 174, -1, -1, -1, 174, -1, -1, 174, 174, -1, -1, 174, 174, 174, -1, 174, 174, -1, -1, -1, -1, 174, 174, 174, -1, -1, 174, 174, -1, -1, 174, 174, -1, -1, -1, 174, 174, 174, 174, -1, -1, -1, -1, 174, -1, -1, 174, -1, -1, 174, -1, 174, 174, -1, 174, -1, -1, 174, 174],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 293, -1, -1, -1, -1, -1, -1, -1, -1, -1, 414, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 401, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 92, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 92, -1, -1, -1, 92, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 376, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 92, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, 19, -1, 291, 179, -1, -1, -1, -1, -1, -1, 350, -1, -1, 13, -1, -1, -1, -1, -1, -1, 150, -1, 282, 31, 442, -1, -1, 206, -1, -1, 233, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 454, 120, -1, -1, -1, 18, 391, -1, -1, 91, -1, 67, -1, -1, -1, -1, -1, 156, -1, -1, 247, 432, -1, 384, 192, -1, -1, -1, 443, -1, 205, 196, -1, -1, 344, 298, -1, -1, -1, 6, 284, -1, -1, -1, 70, 365, 341, -1, 431, 8, 425, -1, -1, -1, 241, 231, -1, -1, -1, -1, -1, 256, -1, -1, 51, 239, 198, -1, 322, 187, -1, -1, -1, -1, 270, -1, 101, 2, -1, -1],
  [-1, -1, 319, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 319, -1, -1, 319, 277, -1, -1, -1, -1, -1, 277, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 319, -1, -1, -1, -1, -1, 319, -1, -1, -1, -1, -1, -1, -1, -1, -1, 319, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 319, -1, -1, -1, -1, -1, -1, -1, 319, -1, -1, -1, -1, 319, 277, -1, -1, -1, 319, -1, -1, -1, -1, -1, -1, -1, -1, -1, 319, -1, -1, -1, -1, -1, -1, -1, -1, -1, 319, -1, -1, 319, -1, -1, 319, -1, -1, -1, -1, -1, 319],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 405, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 405, -1, -1, 207, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 436, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 162, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, 235, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 235, -1, -1, 235, 235, -1, -1, -1, -1, -1, 235, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 235, -1, 235, -1, -1, -1, -1, -1, 235, -1, -1, -1, -1, -1, -1, -1, -1, 235, 235, -1, -1, 235, -1, -1, 235, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 235, -1, -1, -1, 235, -1, -1, 235, -1, -1, -1, -1, 235, -1, -1, -1, -1, 235, 235, -1, -1, -1, 235, -1, -1, -1, -1, -1, -1, -1, -1, -1, 235, -1, -1, -1, -1, -1, -1, -1, -1, -1, 235, -1, -1, 235, -1, -1, 235, -1, -1, -1, -1, -1, 235],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 398, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 202, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 297, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 297, -1, -1, -1, 297, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 297, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, 428, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 428, -1, -1, 428, 428, -1, -1, -1, -1, -1, 428, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 428, -1, 428, -1, -1, -1, -1, -1, 428, -1, -1, -1, -1, -1, -1, -1, -1, 428, 428, -1, -1, 428, -1, -1, 428, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 428, -1, -1, -1, 428, -1, -1, 428, -1, -1, -1, -1, 428, -1, -1, -1, -1, 428, 428, -1, -1, -1, 428, -1, -1, -1, -1, -1, -1, -1, -1, -1, 428, -1, -1, -1, -1, -1, -1, -1, -1, -1, 428, -1, -1, 428, -1, -1, 428, -1, -1, -1, -1, -1, 428],
  [-1, -1, 410, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 410, -1, -1, 410, 410, -1, -1, -1, 158, -1, 410, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 158, -1, -1, -1, 158, 410, -1, -1, -1, -1, -1, 410, -1, -1, -1, -1, -1, -1, -1, -1, -1, 410, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 158, -1, -1, -1, -1, 410, -1, -1, -1, -1, -1, -1, -1, 410, -1, -1, -1, -1, 410, 410, -1, -1, -1, 410, -1, -1, -1, -1, -1, -1, -1, -1, -1, 410, -1, -1, -1, -1, -1, -1, 158, -1, -1, 410, -1, -1, 410, -1, -1, 410, -1, -1, -1, -1, -1, 410],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, 404, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 456, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 346, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, 397, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 397, -1, -1, 397, 397, -1, -1, -1, -1, -1, 397, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 397, -1, 397, -1, -1, -1, -1, -1, 397, -1, -1, -1, -1, -1, -1, -1, -1, 397, 397, -1, -1, 397, -1, -1, 397, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 397, -1, -1, -1, 397, -1, -1, 397, -1, -1, -1, -1, 397, -1, -1, -1, -1, 397, 397, 402, -1, -1, 397, -1, -1, -1, -1, -1, -1, -1, -1, -1, 397, -1, -1, -1, -1, -1, -1, -1, -1, -1, 397, -1, -1, 397, -1, -1, 397, -1, -1, -1, -1, -1, 397],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 141, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 229, -1, -1, -1, -1, 229, -1, -1, 229, -1, -1, -1, 229, -1, 229, -1, -1, -1, 229, -1, -1, -1, 229, -1, -1, -1, -1, -1, -1, -1, 229, -1, -1, -1, -1, -1, -1, -1, -1, 229, -1, -1, 229, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 229, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 229, -1, -1, -1, 229, 229, 229, -1, 229, -1, -1, -1, -1, -1, -1, 229, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 229, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, 164, -1, -1, -1, -1, -1, -1, 164, -1, -1, -1, -1, -1, 164, -1, -1, 164, 164, -1, -1, -1, 164, -1, 164, -1, 164, -1, -1, -1, -1, -1, -1, -1, -1, -1, 164, -1, -1, 164, 164, 164, -1, -1, -1, 164, -1, 164, -1, -1, -1, -1, -1, -1, -1, -1, 164, 164, -1, -1, 164, -1, -1, 164, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 164, 164, -1, -1, -1, 164, -1, -1, 164, -1, -1, -1, -1, 164, -1, -1, -1, -1, 164, 164, 161, -1, -1, 164, -1, -1, -1, -1, -1, -1, -1, -1, -1, 164, -1, -1, -1, -1, -1, -1, 164, -1, -1, 164, -1, -1, 164, -1, -1, 164, -1, -1, -1, -1, -1, 164],
  [-1, -1, 383, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 152, -1, -1, 215, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 163, -1, -1, -1, -1, -1, 217, -1, -1, -1, -1, -1, -1, -1, -1, -1, 438, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 352, -1, -1, -1, -1, -1, -1, -1, 362, -1, -1, -1, -1, 182, -1, -1, -1, -1, 449, -1, -1, -1, -1, -1, -1, -1, -1, -1, 3, -1, -1, -1, -1, -1, -1, -1, -1, -1, 257, -1, -1, 16, -1, -1, 307, -1, -1, -1, -1, -1, 388],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 79, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 317, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 73, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 242, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, 177, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 1, -1, -1, -1, -1, 1, -1, -1, -1, -1, -1, -1, 1, -1, -1, -1, -1, -1, 1, -1, -1, -1, 1, -1, -1, -1, -1, -1, -1, -1, 1, -1, -1, -1, -1, -1, -1, -1, -1, 1, -1, -1, 1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 1, -1, -1, -1, -1, 1, 1, -1, 1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 369, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 104, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, 0, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 0, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 149, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 149, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, 423, -1, -1, -1, -1, -1, -1, 423, -1, -1, -1, -1, -1, 423, -1, -1, 423, 423, -1, -1, -1, 423, -1, 423, -1, 423, -1, -1, -1, -1, -1, -1, -1, -1, -1, 423, -1, -1, 423, 423, 423, -1, -1, -1, 423, -1, 423, -1, -1, -1, -1, -1, -1, -1, -1, 423, 423, -1, -1, 423, -1, -1, 423, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 423, 423, -1, -1, -1, 423, -1, -1, 423, -1, -1, -1, -1, 423, -1, -1, -1, -1, 423, 423, 96, -1, -1, 423, -1, -1, -1, -1, -1, -1, -1, -1, -1, 423, -1, -1, -1, -1, -1, -1, 423, -1, -1, 423, -1, -1, 423, -1, -1, 423, -1, -1, -1, -1, -1, 423],
  [-1, -1, -1, 292, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 407, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 363, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 98, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 21, -1, -1, -1, 226, -1, -1, 366, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 188, -1, -1, -1, -1, -1, -1, 356, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, 393, -1, -1, -1, -1, -1, -1, -1, -1, 393, -1, -1, -1, 393, 393, -1, 393, 393, -1, -1, -1, 393, -1, 393, -1, -1, -1, 393, 393, -1, -1, 393, -1, -1, -1, -1, -1, -1, 393, 393, 393, -1, -1, -1, -1, -1, 393, -1, 393, -1, 393, 393, -1, -1, -1, 393, 393, -1, -1, 393, -1, -1, 393, -1, 393, 393, -1, 393, -1, -1, 393, 393, -1, 393, -1, -1, -1, 393, -1, -1, 393, 393, -1, -1, 393, 393, 393, -1, 393, 393, -1, -1, -1, -1, 393, 393, 393, -1, -1, 393, 393, -1, -1, 393, 393, -1, -1, -1, 393, 393, 393, 393, -1, -1, -1, -1, 393, -1, -1, 393, -1, -1, 393, -1, 393, 393, -1, 393, -1, -1, 393, 393],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 364, -1, -1, -1, -1],
  [-1, -1, 325, -1, -1, -1, -1, -1, -1, -1, -1, 325, -1, -1, -1, 325, 325, -1, 325, 325, -1, -1, -1, 325, -1, 325, -1, -1, -1, 325, 325, -1, -1, 325, -1, -1, -1, -1, -1, -1, 325, 325, 325, -1, -1, -1, -1, -1, 325, -1, 325, -1, 325, 325, -1, -1, -1, 325, 325, -1, -1, 325, -1, -1, 325, -1, 325, 325, -1, 325, -1, -1, 325, 325, -1, 325, -1, -1, -1, 325, -1, -1, 325, 325, -1, -1, 325, 325, 325, -1, 325, 325, -1, -1, -1, -1, 325, 325, 325, -1, -1, 325, 325, -1, -1, 325, 325, -1, -1, -1, 325, 325, 325, 325, -1, -1, -1, -1, 325, -1, -1, 325, -1, -1, 325, -1, 325, 325, -1, 429, -1, -1, 325, 325],
  [-1, -1, 411, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 411, -1, -1, 411, 411, -1, -1, -1, -1, -1, 411, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 411, -1, 411, -1, -1, -1, -1, -1, 411, -1, -1, -1, -1, -1, -1, -1, -1, 411, 411, -1, -1, 411, -1, -1, 411, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 411, -1, -1, -1, 411, -1, -1, 411, -1, -1, -1, -1, 411, -1, -1, -1, -1, 411, 411, -1, -1, -1, 411, -1, -1, -1, -1, -1, -1, -1, -1, -1, 411, -1, -1, -1, -1, -1, -1, -1, -1, -1, 411, -1, -1, 411, -1, -1, 411, -1, -1, -1, -1, -1, 411],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 417, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 71, -1, -1, -1, -1, -1, 143, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 301, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 371, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 294, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 203, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 55, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 348, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 154, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 154, -1, -1, -1, 154, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 154, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, 276, -1, -1, -1, -1, -1, -1, -1, -1, -1, 309, -1, -1, -1, 276, -1, 309, -1, 276, -1, -1, -1, -1, -1, -1, -1, -1, -1, 276, -1, -1, -1, 276, -1, -1, -1, -1, 276, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 276, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 309, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 276, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, 139, -1, -1, -1, -1, -1, -1, -1, -1, -1, 199, -1, -1, -1, 139, -1, 199, -1, 139, -1, -1, -1, -1, -1, -1, -1, -1, -1, 139, -1, -1, -1, 139, -1, -1, -1, -1, 139, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 139, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 199, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 139, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, 311, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 433, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 311, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 261, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, 310, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 7, 340, -1, -1, -1, -1, -1, 138, -1, -1, -1, -1, 351, -1, -1, -1, -1, -1, -1, -1, -1, -1, 274, -1, 155, -1, -1, -1, -1, -1, 334, -1, -1, -1, 265, -1, -1, -1, 173, 386, 306, -1, -1, 178, -1, -1, 260, -1, 45, -1, -1, 379, -1, -1, 355, 378, -1, -1, -1, -1, -1, 357, -1, -1, -1, 254, -1, -1, 336, 416, -1, -1, -1, 86, -1, -1, -1, -1, 387, 333, -1, -1, -1, 299, -1, -1, -1, 342, 37, -1, -1, -1, 124, 330, 195, 368, -1, -1, -1, -1, -1, -1, -1, 409, -1, -1, 48, -1, 273, 353, -1, -1, -1, -1, -1, 419],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, 168, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 168, -1, -1, -1, 168, -1, -1, -1, -1, -1, -1, -1, -1, -1, 168, -1, -1, -1, 168, -1, -1, -1, -1, 168, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 168, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1]
  ]
  def terminal(self, str):
    return self.str_terminal[str]
  def terminalNames(self):
    return list(self.str_terminal.keys())
  def isTerminal(self, id):
    return 0 <= id <= 133
  def isNonTerminal(self, id):
    return 134 <= id <= 280
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
    if self.recorder.awake and self.sym is not None:
      self.recorder.record(self.sym)
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
    return self.parse_table[n - 134][self.sym.getId()]
  def call(self, nt_str):
    return getattr(self, nt_str)()
  def __GEN13(self, depth=0, tracer=None):
    rule = self.rule(134)
    tree = ParseTree( NonTerminal(134, self.getAtomString(134)), tracer )
    tree.list = 'slist'
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 5:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._INIT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN14(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [118, 37, 41]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._INIT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN14(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN14(self, depth=0, tracer=None):
    rule = self.rule(135)
    tree = ParseTree( NonTerminal(135, self.getAtomString(135)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in [75]):
      return tree
    if self.sym == None:
      return tree
    if rule == 9:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(27, tracer) ) # comma
      subtree = self._INIT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN14(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _REPLACEMENT_LIST(self, depth=0, tracer=None):
    rule = self.rule(136)
    tree = ParseTree( NonTerminal(136, self.getAtomString(136)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _DIRECT_DECLARATOR_PARAMETER_LIST(self, depth=0, tracer=None):
    rule = self.rule(137)
    tree = ParseTree( NonTerminal(137, self.getAtomString(137)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 223:
      tree.astTransform = AstTransformNodeCreator('ParameterList', {'identifiers': 0})
      subtree = self.__GEN33(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 337:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PARAMETER_TYPE_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _TOKEN(self, depth=0, tracer=None):
    rule = self.rule(139)
    tree = ParseTree( NonTerminal(139, self.getAtomString(139)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 47:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PUNCTUATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 72:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._KEYWORD(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 88:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(41, tracer) ) # identifier
      return tree
    elif rule == 102:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._CONSTANT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 186:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(53, tracer) ) # string_literal
      return tree
    elif rule == 191:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(45, tracer) ) # pp_number
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _ENUMERATION_CONSTANT(self, depth=0, tracer=None):
    rule = self.rule(140)
    tree = ParseTree( NonTerminal(140, self.getAtomString(140)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 180:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(41, tracer) ) # identifier
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _ENUMERATOR_ASSIGNMENT(self, depth=0, tracer=None):
    rule = self.rule(141)
    tree = ParseTree( NonTerminal(141, self.getAtomString(141)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [49, 27]):
      return tree
    if self.sym == None:
      return tree
    if rule == 109:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(17, tracer) ) # assign
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _TERMINALS(self, depth=0, tracer=None):
    rule = self.rule(142)
    tree = ParseTree( NonTerminal(142, self.getAtomString(142)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 20:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(13, tracer) ) # diveq
      return tree
    elif rule == 23:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(25, tracer) ) # volatile
      return tree
    elif rule == 26:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(106, tracer) ) # goto
      return tree
    elif rule == 27:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(123, tracer) ) # lt
      return tree
    elif rule == 28:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(66, tracer) ) # do
      return tree
    elif rule == 29:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(8, tracer) ) # decimal_floating_constant
      return tree
    elif rule == 34:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(7, tracer) ) # modeq
      return tree
    elif rule == 36:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(127, tracer) ) # unsigned
      return tree
    elif rule == 50:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(63, tracer) ) # add
      return tree
    elif rule == 58:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(125, tracer) ) # number
      return tree
    elif rule == 63:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(96, tracer) ) # short
      return tree
    elif rule == 65:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(59, tracer) ) # sub
      return tree
    elif rule == 74:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(73, tracer) ) # else
      return tree
    elif rule == 75:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(107, tracer) ) # not
      return tree
    elif rule == 76:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(121, tracer) ) # signed
      return tree
    elif rule == 78:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(41, tracer) ) # identifier
      return tree
    elif rule == 81:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(81, tracer) ) # bool
      return tree
    elif rule == 90:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(102, tracer) ) # rbrace
      return tree
    elif rule == 93:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(78, tracer) ) # colon
      return tree
    elif rule == 99:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(126, tracer) ) # case
      return tree
    elif rule == 100:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(19, tracer) ) # const
      return tree
    elif rule == 106:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(99, tracer) ) # and
      return tree
    elif rule == 107:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(64, tracer) ) # auto
      return tree
    elif rule == 108:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(48, tracer) ) # void
      return tree
    elif rule == 115:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(103, tracer) ) # neq
      return tree
    elif rule == 116:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(31, tracer) ) # lteq
      return tree
    elif rule == 119:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(74, tracer) ) # div
      return tree
    elif rule == 121:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(17, tracer) ) # assign
      return tree
    elif rule == 122:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(93, tracer) ) # dot
      return tree
    elif rule == 131:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(92, tracer) ) # complex
      return tree
    elif rule == 133:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(124, tracer) ) # union
      return tree
    elif rule == 135:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(28, tracer) ) # poundpound
      return tree
    elif rule == 136:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(90, tracer) ) # bitand
      return tree
    elif rule == 144:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(94, tracer) ) # or
      return tree
    elif rule == 146:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(130, tracer) ) # gt
      return tree
    elif rule == 151:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(52, tracer) ) # if
      return tree
    elif rule == 157:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(18, tracer) ) # struct
      return tree
    elif rule == 160:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(118, tracer) ) # lparen
      return tree
    elif rule == 171:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(112, tracer) ) # default
      return tree
    elif rule == 172:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(119, tracer) ) # gteq
      return tree
    elif rule == 176:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(104, tracer) ) # bitxor
      return tree
    elif rule == 181:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(72, tracer) ) # for
      return tree
    elif rule == 189:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(24, tracer) ) # pound
      return tree
    elif rule == 193:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(36, tracer) ) # imaginary
      return tree
    elif rule == 201:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(14, tracer) ) # subeq
      return tree
    elif rule == 204:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(82, tracer) ) # decr
      return tree
    elif rule == 208:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(27, tracer) ) # comma
      return tree
    elif rule == 210:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(122, tracer) ) # rparen
      return tree
    elif rule == 214:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(128, tracer) ) # exclamation_point
      return tree
    elif rule == 220:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(84, tracer) ) # questionmark
      return tree
    elif rule == 227:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(11, tracer) ) # integer_constant
      return tree
    elif rule == 228:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(55, tracer) ) # lshift
      return tree
    elif rule == 238:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(71, tracer) ) # elipsis
      return tree
    elif rule == 240:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(98, tracer) ) # lbrace
      return tree
    elif rule == 243:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(100, tracer) ) # bitor
      return tree
    elif rule == 244:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(86, tracer) ) # static
      return tree
    elif rule == 248:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(60, tracer) ) # rshift
      return tree
    elif rule == 250:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(40, tracer) ) # inline
      return tree
    elif rule == 252:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(79, tracer) ) # register
      return tree
    elif rule == 253:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(53, tracer) ) # string_literal
      return tree
    elif rule == 255:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(61, tracer) ) # typedef
      return tree
    elif rule == 258:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(89, tracer) ) # lshifteq
      return tree
    elif rule == 263:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(65, tracer) ) # mod
      return tree
    elif rule == 266:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(75, tracer) ) # semi
      return tree
    elif rule == 267:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(131, tracer) ) # rshifteq
      return tree
    elif rule == 271:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(26, tracer) ) # rsquare
      return tree
    elif rule == 278:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(110, tracer) ) # switch
      return tree
    elif rule == 280:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(97, tracer) ) # restrict
      return tree
    elif rule == 281:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(113, tracer) ) # break
      return tree
    elif rule == 286:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(6, tracer) ) # lsquare
      return tree
    elif rule == 290:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(120, tracer) ) # bitandeq
      return tree
    elif rule == 295:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(69, tracer) ) # return
      return tree
    elif rule == 313:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(85, tracer) ) # arrow
      return tree
    elif rule == 315:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(83, tracer) ) # enum
      return tree
    elif rule == 320:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(109, tracer) ) # bitoreq
      return tree
    elif rule == 321:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(91, tracer) ) # char
      return tree
    elif rule == 329:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(115, tracer) ) # bitxoreq
      return tree
    elif rule == 358:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(108, tracer) ) # eq
      return tree
    elif rule == 370:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(117, tracer) ) # header_name
      return tree
    elif rule == 380:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(42, tracer) ) # double
      return tree
    elif rule == 389:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(87, tracer) ) # sizeof
      return tree
    elif rule == 403:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(30, tracer) ) # while
      return tree
    elif rule == 418:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(22, tracer) ) # hexadecimal_floating_constant
      return tree
    elif rule == 421:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(4, tracer) ) # addeq
      return tree
    elif rule == 437:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(2, tracer) ) # long
      return tree
    elif rule == 439:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(88, tracer) ) # incr
      return tree
    elif rule == 440:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(101, tracer) ) # int
      return tree
    elif rule == 441:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(50, tracer) ) # character_constant
      return tree
    elif rule == 444:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(57, tracer) ) # extern
      return tree
    elif rule == 450:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(114, tracer) ) # universal_character_name
      return tree
    elif rule == 451:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(111, tracer) ) # float
      return tree
    elif rule == 452:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(54, tracer) ) # tilde
      return tree
    elif rule == 457:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(34, tracer) ) # muleq
      return tree
    elif rule == 459:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(105, tracer) ) # continue
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _DEFINE_FUNC_PARAM(self, depth=0, tracer=None):
    rule = self.rule(143)
    tree = ParseTree( NonTerminal(143, self.getAtomString(143)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _DESIGNATION(self, depth=0, tracer=None):
    rule = self.rule(144)
    tree = ParseTree( NonTerminal(144, self.getAtomString(144)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 367:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN19(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(17, tracer) ) # assign
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _EXPRESSION_OPT(self, depth=0, tracer=None):
    rule = self.rule(145)
    tree = ParseTree( NonTerminal(145, self.getAtomString(145)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [75, 122]):
      return tree
    if self.sym == None:
      return tree
    if rule == 399:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [41, 29, 118, 16, 67, 33, 82, 23, 50, 11, 87, 90, 53, 88]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    return tree
  def _ELIPSIS_OPT(self, depth=0, tracer=None):
    rule = self.rule(146)
    tree = ParseTree( NonTerminal(146, self.getAtomString(146)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _INCLUDE_LINE(self, depth=0, tracer=None):
    rule = self.rule(147)
    tree = ParseTree( NonTerminal(147, self.getAtomString(147)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _STATIC_OPT(self, depth=0, tracer=None):
    rule = self.rule(148)
    tree = ParseTree( NonTerminal(148, self.getAtomString(148)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [50, 33, 23, 41, 11, 29, 118, 67, 88, 82, 90, 53, 16, 87]):
      return tree
    if self.sym == None:
      return tree
    if rule == 113:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(86, tracer) ) # static
      return tree
    return tree
  def __GEN23(self, depth=0, tracer=None):
    rule = self.rule(149)
    tree = ParseTree( NonTerminal(149, self.getAtomString(149)), tracer )
    tree.list = 'slist'
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 335:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STRUCT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN24(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [118, 37, 41]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STRUCT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN24(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN15(self, depth=0, tracer=None):
    rule = self.rule(150)
    tree = ParseTree( NonTerminal(150, self.getAtomString(150)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [75, 27]):
      return tree
    if self.sym == None:
      return tree
    if rule == 25:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DECLARATOR_INITIALIZER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _DECLARATOR_INITIALIZER(self, depth=0, tracer=None):
    rule = self.rule(151)
    tree = ParseTree( NonTerminal(151, self.getAtomString(151)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 130:
      tree.astTransform = AstTransformSubstitution(1)
      tree.add( self.expect(17, tracer) ) # assign
      subtree = self._INITIALIZER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN18(self, depth=0, tracer=None):
    rule = self.rule(152)
    tree = ParseTree( NonTerminal(152, self.getAtomString(152)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [41, 98, 29, 67, 82, 33, 118, 23, 50, 11, 87, 88, 90, 53, 16]):
      return tree
    if self.sym == None:
      return tree
    if rule == 400:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DESIGNATION(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _PP_TOKENS(self, depth=0, tracer=None):
    rule = self.rule(153)
    tree = ParseTree( NonTerminal(153, self.getAtomString(153)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN24(self, depth=0, tracer=None):
    rule = self.rule(154)
    tree = ParseTree( NonTerminal(154, self.getAtomString(154)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in [75]):
      return tree
    if self.sym == None:
      return tree
    if rule == 175:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(27, tracer) ) # comma
      subtree = self._STRUCT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN24(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _STATEMENT(self, depth=0, tracer=None):
    rule = self.rule(155)
    tree = ParseTree( NonTerminal(155, self.getAtomString(155)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 39:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._SELECTION_STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 153:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._EXPRESSION_STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 166:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._COMPOUND_STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 234:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._ITERATION_STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 338:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._JUMP_STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 447:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._LABELED_STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [41, 29, 118, 16, 67, 33, 82, 23, 50, 11, 87, 90, 53, 88]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._EXPRESSION_STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _PP_DIRECTIVE(self, depth=0, tracer=None):
    rule = self.rule(156)
    tree = ParseTree( NonTerminal(156, self.getAtomString(156)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _INITIALIZER(self, depth=0, tracer=None):
    rule = self.rule(157)
    tree = ParseTree( NonTerminal(157, self.getAtomString(157)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 142:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 212:
      tree.astTransform = AstTransformSubstitution(1)
      tree.add( self.expect(98, tracer) ) # lbrace
      subtree = self.__GEN16(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self._TRAILING_COMMA_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(102, tracer) ) # rbrace
      return tree
    elif self.sym.getId() in [41, 29, 118, 16, 67, 33, 82, 23, 50, 11, 87, 90, 53, 88]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _STRUCT_DECLARATION(self, depth=0, tracer=None):
    rule = self.rule(158)
    tree = ParseTree( NonTerminal(158, self.getAtomString(158)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 435:
      tree.astTransform = AstTransformNodeCreator('StructOrUnionDeclaration', {'specifier_qualifiers': 0, 'declarators': 1})
      subtree = self.__GEN22(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN23(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(75, tracer) ) # semi
      return tree
    elif self.sym.getId() in [118, 37, 41]:
      tree.astTransform = AstTransformNodeCreator('StructOrUnionDeclaration', {'specifier_qualifiers': 0, 'declarators': 1})
      subtree = self.__GEN22(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN23(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(75, tracer) ) # semi
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _POINTER(self, depth=0, tracer=None):
    rule = self.rule(159)
    tree = ParseTree( NonTerminal(159, self.getAtomString(159)), tracer )
    tree.list = False
    if self.sym == None:
      return tree
    if rule == 264:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN36(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN0(self, depth=0, tracer=None):
    rule = self.rule(160)
    tree = ParseTree( NonTerminal(160, self.getAtomString(160)), tracer )
    tree.list = 'tlist'
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 53:
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
  def _TRANSLATION_UNIT(self, depth=0, tracer=None):
    rule = self.rule(161)
    tree = ParseTree( NonTerminal(161, self.getAtomString(161)), tracer )
    tree.list = False
    if self.sym == None:
      return tree
    if rule == 446:
      tree.astTransform = AstTransformNodeCreator('TranslationUnit', {'external_declarations': 0})
      subtree = self.__GEN7(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _INITIALIZER_LIST_ITEM(self, depth=0, tracer=None):
    rule = self.rule(162)
    tree = ParseTree( NonTerminal(162, self.getAtomString(162)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 165:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(11, tracer) ) # integer_constant
      return tree
    elif rule == 289:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN18(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self._INITIALIZER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [41, 29, 118, 16, 67, 33, 82, 23, 50, 11, 87, 90, 53, 88]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN18(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self._INITIALIZER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _PARAMETER_DECLARATION_SUB_SUB(self, depth=0, tracer=None):
    rule = self.rule(163)
    tree = ParseTree( NonTerminal(163, self.getAtomString(163)), tracer )
    tree.list = False
    if self.sym == None:
      return tree
    if rule == 84:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DIRECT_ABSTRACT_DECLARATOR_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 372:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__DIRECT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [46, -1, 118]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DIRECT_ABSTRACT_DECLARATOR_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    elif self.sym.getId() in [118, 37, 41]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__DIRECT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _DECLARATOR(self, depth=0, tracer=None):
    rule = self.rule(164)
    tree = ParseTree( NonTerminal(164, self.getAtomString(164)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 236:
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
    elif self.sym.getId() in [118, 37, 41]:
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
  def _LABELED_STATEMENT(self, depth=0, tracer=None):
    rule = self.rule(165)
    tree = ParseTree( NonTerminal(165, self.getAtomString(165)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 52:
      tree.astTransform = AstTransformNodeCreator('DefaultCase', {'statement': 2})
      tree.add( self.expect(112, tracer) ) # default
      tree.add( self.expect(78, tracer) ) # colon
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 200:
      tree.astTransform = AstTransformNodeCreator('Case', {'expr': 1, 'statement': 3})
      tree.add( self.expect(126, tracer) ) # case
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(78, tracer) ) # colon
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 323:
      tree.astTransform = AstTransformNodeCreator('Label', {'name': 0, 'statement': 1})
      tree.add( self.expect(41, tracer) ) # identifier
      tree.add( self.expect(78, tracer) ) # colon
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _ABSTRACT_DECLARATOR(self, depth=0, tracer=None):
    rule = self.rule(166)
    tree = ParseTree( NonTerminal(166, self.getAtomString(166)), tracer )
    tree.list = False
    if self.sym == None:
      return tree
    if rule == 83:
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
    elif self.sym.getId() in [46, -1, 118]:
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
  def __GEN21(self, depth=0, tracer=None):
    rule = self.rule(167)
    tree = ParseTree( NonTerminal(167, self.getAtomString(167)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [102]):
      return tree
    if self.sym == None:
      return tree
    if rule == 287:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STRUCT_DECLARATION(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN21(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [118, 37, 41]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STRUCT_DECLARATION(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN21(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    return tree
  def _EXTERNAL_DECLARATION(self, depth=0, tracer=None):
    rule = self.rule(168)
    tree = ParseTree( NonTerminal(168, self.getAtomString(168)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 213:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._EXTERNAL_PROTOTYPE(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 268:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._EXTERNAL_DECLARATOR_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 359:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._EXTERNAL_FUNCTION(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN7(self, depth=0, tracer=None):
    rule = self.rule(169)
    tree = ParseTree( NonTerminal(169, self.getAtomString(169)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [-1]):
      return tree
    if self.sym == None:
      return tree
    if rule == 125:
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
  def _PP_NODES(self, depth=0, tracer=None):
    rule = self.rule(170)
    tree = ParseTree( NonTerminal(170, self.getAtomString(170)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _EXPRESSION_STATEMENT(self, depth=0, tracer=None):
    rule = self.rule(171)
    tree = ParseTree( NonTerminal(171, self.getAtomString(171)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 69:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._EXPRESSION_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(75, tracer) ) # semi
      return tree
    elif self.sym.getId() in [41, 29, 118, 16, 67, 33, 82, 23, 50, 11, 87, 90, 53, 88]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._EXPRESSION_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(75, tracer) ) # semi
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _TRAILING_COMMA_OPT(self, depth=0, tracer=None):
    rule = self.rule(172)
    tree = ParseTree( NonTerminal(172, self.getAtomString(172)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [102]):
      return tree
    if self.sym == None:
      return tree
    if rule == 249:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(49, tracer) ) # trailing_comma
      return tree
    return tree
  def _IF_SECTION(self, depth=0, tracer=None):
    rule = self.rule(173)
    tree = ParseTree( NonTerminal(173, self.getAtomString(173)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _DEFINED_IDENTIFIER(self, depth=0, tracer=None):
    rule = self.rule(174)
    tree = ParseTree( NonTerminal(174, self.getAtomString(174)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _SELECTION_STATEMENT(self, depth=0, tracer=None):
    rule = self.rule(175)
    tree = ParseTree( NonTerminal(175, self.getAtomString(175)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 42:
      tree.astTransform = AstTransformNodeCreator('Switch', {'expr': 2, 'statment': 4})
      tree.add( self.expect(110, tracer) ) # switch
      tree.add( self.expect(118, tracer) ) # lparen
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(122, tracer) ) # rparen
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 349:
      tree.astTransform = AstTransformNodeCreator('If', {'elseif': 6, 'statement': 4, 'condition': 2, 'else': 7})
      tree.add( self.expect(52, tracer) ) # if
      tree.add( self.expect(118, tracer) ) # lparen
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(122, tracer) ) # rparen
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(132, tracer) ) # endif
      subtree = self.__GEN39(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN40(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _CONSTANT(self, depth=0, tracer=None):
    rule = self.rule(176)
    tree = ParseTree( NonTerminal(176, self.getAtomString(176)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 14:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(29, tracer) ) # floating_constant
      return tree
    elif rule == 77:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(33, tracer) ) # enumeration_constant
      return tree
    elif rule == 218:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(11, tracer) ) # integer_constant
      return tree
    elif rule == 415:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(50, tracer) ) # character_constant
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _EXTERNAL_FUNCTION(self, depth=0, tracer=None):
    rule = self.rule(177)
    tree = ParseTree( NonTerminal(177, self.getAtomString(177)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 230:
      tree.astTransform = AstTransformNodeCreator('FunctionDefinition', {'body': 4, 'declaration_list': 3, 'declaration_specifiers': 1, 'signature': 2})
      tree.add( self.expect(47, tracer) ) # function_definition_hint
      subtree = self.__GEN8(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self._DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN10(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self._COMPOUND_STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _CONTROL_LINE(self, depth=0, tracer=None):
    rule = self.rule(178)
    tree = ParseTree( NonTerminal(178, self.getAtomString(178)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _JUMP_STATEMENT(self, depth=0, tracer=None):
    rule = self.rule(179)
    tree = ParseTree( NonTerminal(179, self.getAtomString(179)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 148:
      tree.astTransform = AstTransformNodeCreator('Goto', {'name': 1})
      tree.add( self.expect(106, tracer) ) # goto
      tree.add( self.expect(41, tracer) ) # identifier
      tree.add( self.expect(75, tracer) ) # semi
      return tree
    elif rule == 184:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(113, tracer) ) # break
      tree.add( self.expect(75, tracer) ) # semi
      return tree
    elif rule == 394:
      tree.astTransform = AstTransformNodeCreator('Return', {'expr': 1})
      tree.add( self.expect(69, tracer) ) # return
      subtree = self._EXPRESSION_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(75, tracer) ) # semi
      return tree
    elif rule == 408:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(105, tracer) ) # continue
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _SIZEOF_BODY(self, depth=0, tracer=None):
    rule = self.rule(180)
    tree = ParseTree( NonTerminal(180, self.getAtomString(180)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 326:
      tree.astTransform = AstTransformSubstitution(1)
      tree.add( self.expect(118, tracer) ) # lparen
      subtree = self._TYPE_NAME(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(122, tracer) ) # rparen
      return tree
    elif rule == 395:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(41, tracer) ) # identifier
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _ITERATION_STATEMENT(self, depth=0, tracer=None):
    rule = self.rule(181)
    tree = ParseTree( NonTerminal(181, self.getAtomString(181)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 35:
      tree.astTransform = AstTransformNodeCreator('While', {'expr': 2, 'statement': 4})
      tree.add( self.expect(30, tracer) ) # while
      tree.add( self.expect(118, tracer) ) # lparen
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(122, tracer) ) # rparen
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 61:
      tree.astTransform = AstTransformNodeCreator('For', {'init': 2, 'cond': 3, 'incr': 4})
      tree.add( self.expect(72, tracer) ) # for
      tree.add( self.expect(118, tracer) ) # lparen
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
      tree.add( self.expect(122, tracer) ) # rparen
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 445:
      tree.astTransform = AstTransformNodeCreator('DoWhile', {'expr': 4, 'statement': 1})
      tree.add( self.expect(66, tracer) ) # do
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(30, tracer) ) # while
      tree.add( self.expect(118, tracer) ) # lparen
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(122, tracer) ) # rparen
      tree.add( self.expect(75, tracer) ) # semi
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _EXTERNAL_DECLARATOR_LIST(self, depth=0, tracer=None):
    rule = self.rule(182)
    tree = ParseTree( NonTerminal(182, self.getAtomString(182)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 455:
      tree.astTransform = AstTransformNodeCreator('DeclaratorList', {'declaration_specifiers': 1, 'declarators': 2})
      tree.add( self.expect(76, tracer) ) # declarator_hint
      subtree = self.__GEN8(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN11(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(75, tracer) ) # semi
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _IF_PART(self, depth=0, tracer=None):
    rule = self.rule(183)
    tree = ParseTree( NonTerminal(183, self.getAtomString(183)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _ELSEIF_PART(self, depth=0, tracer=None):
    rule = self.rule(184)
    tree = ParseTree( NonTerminal(184, self.getAtomString(184)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN1(self, depth=0, tracer=None):
    rule = self.rule(185)
    tree = ParseTree( NonTerminal(185, self.getAtomString(185)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 85:
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
  def _EXTERNAL_PROTOTYPE(self, depth=0, tracer=None):
    rule = self.rule(186)
    tree = ParseTree( NonTerminal(186, self.getAtomString(186)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 316:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(44, tracer) ) # function_prototype_hint
      subtree = self.__GEN8(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self._DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN10(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self._COMPOUND_STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _POINTER_OPT(self, depth=0, tracer=None):
    rule = self.rule(187)
    tree = ParseTree( NonTerminal(187, self.getAtomString(187)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [46, 41, 9, 118, 27, 37]):
      return tree
    if self.sym == None:
      return tree
    if rule == 216:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._POINTER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN36(self, depth=0, tracer=None):
    rule = self.rule(188)
    tree = ParseTree( NonTerminal(188, self.getAtomString(188)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [46, 37, 27, 41, 118, 9]):
      return tree
    if self.sym == None:
      return tree
    if rule == 375:
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
  def _DIRECT_ABSTRACT_DECLARATOR_EXPR(self, depth=0, tracer=None):
    rule = self.rule(189)
    tree = ParseTree( NonTerminal(189, self.getAtomString(189)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 237:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(23, tracer) ) # asterisk
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
    elif self.sym.getId() in [41, 29, 118, 16, 67, 33, 82, 23, 50, 11, 87, 90, 53, 88]:
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
  def _ELSE_PART(self, depth=0, tracer=None):
    rule = self.rule(190)
    tree = ParseTree( NonTerminal(190, self.getAtomString(190)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _DIRECT_DECLARATOR_EXPR(self, depth=0, tracer=None):
    rule = self.rule(191)
    tree = ParseTree( NonTerminal(191, self.getAtomString(191)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 232:
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
    elif self.sym.getId() in [41, 29, 118, 16, 67, 33, 82, 23, 50, 11, 87, 90, 53, 88]:
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
  def _DECLARATION_SPECIFIER(self, depth=0, tracer=None):
    rule = self.rule(192)
    tree = ParseTree( NonTerminal(192, self.getAtomString(192)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 33:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._FUNCTION_SPECIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 303:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._TYPE_SPECIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 373:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._TYPE_QUALIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 453:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STORAGE_CLASS_SPECIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN8(self, depth=0, tracer=None):
    rule = self.rule(193)
    tree = ParseTree( NonTerminal(193, self.getAtomString(193)), tracer )
    tree.list = 'mlist'
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 183:
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
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN16(self, depth=0, tracer=None):
    rule = self.rule(194)
    tree = ParseTree( NonTerminal(194, self.getAtomString(194)), tracer )
    tree.list = 'slist'
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 56:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._INITIALIZER_LIST_ITEM(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN17(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [41, 29, 118, 16, 67, 33, 82, 23, 50, 11, 87, 90, 53, 88]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._INITIALIZER_LIST_ITEM(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN17(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN9(self, depth=0, tracer=None):
    rule = self.rule(195)
    tree = ParseTree( NonTerminal(195, self.getAtomString(195)), tracer )
    tree.list = 'mlist'
    if self.sym != None and (self.sym.getId() in [46, 37, 23, 27, 41, 118, 9]):
      return tree
    if self.sym == None:
      return tree
    if rule == 328:
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
  def __GEN35(self, depth=0, tracer=None):
    rule = self.rule(196)
    tree = ParseTree( NonTerminal(196, self.getAtomString(196)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [27, 9]):
      return tree
    if self.sym == None:
      return tree
    if rule == 38:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PARAMETER_DECLARATION_SUB(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [46, -1, 118]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PARAMETER_DECLARATION_SUB(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    elif self.sym.getId() in [118, 37, 41]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PARAMETER_DECLARATION_SUB(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    return tree
  def __GEN2(self, depth=0, tracer=None):
    rule = self.rule(197)
    tree = ParseTree( NonTerminal(197, self.getAtomString(197)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 269:
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
  def _UNDEF_LINE(self, depth=0, tracer=None):
    rule = self.rule(198)
    tree = ParseTree( NonTerminal(198, self.getAtomString(198)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _STRUCT_DECLARATOR(self, depth=0, tracer=None):
    rule = self.rule(200)
    tree = ParseTree( NonTerminal(200, self.getAtomString(200)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 246:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN25(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 272:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STRUCT_DECLARATOR_BODY(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [118, 37, 41]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN25(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN17(self, depth=0, tracer=None):
    rule = self.rule(201)
    tree = ParseTree( NonTerminal(201, self.getAtomString(201)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in [49]):
      return tree
    if self.sym == None:
      return tree
    if rule == 59:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(27, tracer) ) # comma
      subtree = self._INITIALIZER_LIST_ITEM(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN17(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN40(self, depth=0, tracer=None):
    rule = self.rule(202)
    tree = ParseTree( NonTerminal(202, self.getAtomString(202)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [110, 2, 58, 30, 61, 57, 67, 88, 86, 11, 75, 64, 66, 16, 82, 79, 18, 50, 19, 98, 23, 48, 72, 124, 132, 90, 91, 25, 96, 87, 83, 29, 101, 102, 33, 105, 106, 111, 97, 113, 40, 42, 41, 69, 121, 118, 15, 126, 127, 53, 112, 52, 133]):
      return tree
    if self.sym == None:
      return tree
    if rule == 262:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._ELSE_STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _BLOCK_ITEM_LIST(self, depth=0, tracer=None):
    rule = self.rule(203)
    tree = ParseTree( NonTerminal(203, self.getAtomString(203)), tracer )
    tree.list = False
    if self.sym == None:
      return tree
    if rule == 302:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN38(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [41, 29, 118, 16, 67, 33, 82, 23, 50, 11, 87, 90, 53, 88]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN38(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN37(self, depth=0, tracer=None):
    rule = self.rule(204)
    tree = ParseTree( NonTerminal(204, self.getAtomString(204)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [102]):
      return tree
    if self.sym == None:
      return tree
    if rule == 245:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._BLOCK_ITEM_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [41, 29, 118, 16, 67, 33, 82, 23, 50, 11, 87, 90, 53, 88]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._BLOCK_ITEM_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    return tree
  def __GEN3(self, depth=0, tracer=None):
    rule = self.rule(205)
    tree = ParseTree( NonTerminal(205, self.getAtomString(205)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 46:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(27, tracer) ) # comma
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
  def _DIRECT_DECLARATOR_MODIFIER(self, depth=0, tracer=None):
    rule = self.rule(206)
    tree = ParseTree( NonTerminal(206, self.getAtomString(206)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 10:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._TYPE_QUALIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 318:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(86, tracer) ) # static
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN30(self, depth=0, tracer=None):
    rule = self.rule(207)
    tree = ParseTree( NonTerminal(207, self.getAtomString(207)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [53, 33, 23, 50, 41, 29, 118, 67, 88, 82, 90, 11, 16, 87]):
      return tree
    if self.sym == None:
      return tree
    if rule == 283:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DIRECT_DECLARATOR_MODIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN30(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _DESIGNATOR(self, depth=0, tracer=None):
    rule = self.rule(208)
    tree = ParseTree( NonTerminal(208, self.getAtomString(208)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 43:
      tree.astTransform = AstTransformNodeCreator('ArrayAccess', {'index': 1})
      tree.add( self.expect(6, tracer) ) # lsquare
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(26, tracer) ) # rsquare
      return tree
    elif rule == 345:
      tree.astTransform = AstTransformNodeCreator('MemberAccess', {'name': 1})
      tree.add( self.expect(93, tracer) ) # dot
      tree.add( self.expect(41, tracer) ) # identifier
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _DECLARATION_LIST(self, depth=0, tracer=None):
    rule = self.rule(209)
    tree = ParseTree( NonTerminal(209, self.getAtomString(209)), tracer )
    tree.list = False
    if self.sym == None:
      return tree
    if rule == 361:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN12(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN10(self, depth=0, tracer=None):
    rule = self.rule(210)
    tree = ParseTree( NonTerminal(210, self.getAtomString(210)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [98]):
      return tree
    if self.sym == None:
      return tree
    if rule == 308:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DECLARATION_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _DECLARATION(self, depth=0, tracer=None):
    rule = self.rule(211)
    tree = ParseTree( NonTerminal(211, self.getAtomString(211)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 110:
      tree.astTransform = AstTransformNodeCreator('Declaration', {'init_declarators': 1, 'declaration_specifiers': 0})
      subtree = self.__GEN8(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN11(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(75, tracer) ) # semi
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _STRUCT_SPECIFIER(self, depth=0, tracer=None):
    rule = self.rule(212)
    tree = ParseTree( NonTerminal(212, self.getAtomString(212)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 140:
      tree.astTransform = AstTransformNodeCreator('Struct', {'definition': 1})
      tree.add( self.expect(18, tracer) ) # struct
      subtree = self._STRUCT_OR_UNION_SUB(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _PARAMETER_DECLARATION(self, depth=0, tracer=None):
    rule = self.rule(213)
    tree = ParseTree( NonTerminal(213, self.getAtomString(213)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 197:
      tree.astTransform = AstTransformNodeCreator('ParameterDeclaration', {'sub': 1, 'declaration_specifiers': 0})
      subtree = self.__GEN8(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN35(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _BLOCK_ITEM(self, depth=0, tracer=None):
    rule = self.rule(215)
    tree = ParseTree( NonTerminal(215, self.getAtomString(215)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 123:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DECLARATION(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 304:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [41, 29, 118, 16, 67, 33, 82, 23, 50, 11, 87, 90, 53, 88]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN38(self, depth=0, tracer=None):
    rule = self.rule(216)
    tree = ParseTree( NonTerminal(216, self.getAtomString(216)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [102]):
      return tree
    if self.sym == None:
      return tree
    if rule == 381:
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
    elif self.sym.getId() in [41, 29, 118, 16, 67, 33, 82, 23, 50, 11, 87, 90, 53, 88]:
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
  def __GEN5(self, depth=0, tracer=None):
    rule = self.rule(217)
    tree = ParseTree( NonTerminal(217, self.getAtomString(217)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 430:
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
  def __GEN27(self, depth=0, tracer=None):
    rule = self.rule(218)
    tree = ParseTree( NonTerminal(218, self.getAtomString(218)), tracer )
    tree.list = 'slist'
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 275:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._ENUMERATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN28(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _COMPOUND_STATEMENT(self, depth=0, tracer=None):
    rule = self.rule(219)
    tree = ParseTree( NonTerminal(219, self.getAtomString(219)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 385:
      tree.astTransform = AstTransformSubstitution(1)
      tree.add( self.expect(98, tracer) ) # lbrace
      subtree = self.__GEN37(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(102, tracer) ) # rbrace
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _FOR_INIT(self, depth=0, tracer=None):
    rule = self.rule(220)
    tree = ParseTree( NonTerminal(220, self.getAtomString(220)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [75]):
      return tree
    if self.sym == None:
      return tree
    if rule == 57:
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
    elif rule == 194:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [41, 29, 118, 16, 67, 33, 82, 23, 50, 11, 87, 90, 53, 88]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    return tree
  def _FOR_COND(self, depth=0, tracer=None):
    rule = self.rule(221)
    tree = ParseTree( NonTerminal(221, self.getAtomString(221)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 305:
      tree.astTransform = AstTransformSubstitution(1)
      tree.add( self.expect(75, tracer) ) # semi
      subtree = self._EXPRESSION_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _ELSE_IF_STATEMENT_LIST(self, depth=0, tracer=None):
    rule = self.rule(222)
    tree = ParseTree( NonTerminal(222, self.getAtomString(222)), tracer )
    tree.list = False
    if self.sym == None:
      return tree
    if rule == 174:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN41(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _TYPE_NAME(self, depth=0, tracer=None):
    rule = self.rule(223)
    tree = ParseTree( NonTerminal(223, self.getAtomString(223)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 293:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(91, tracer) ) # char
      return tree
    elif rule == 414:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(101, tracer) ) # int
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _ERROR_LINE(self, depth=0, tracer=None):
    rule = self.rule(224)
    tree = ParseTree( NonTerminal(224, self.getAtomString(224)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _TYPEDEF_NAME(self, depth=0, tracer=None):
    rule = self.rule(225)
    tree = ParseTree( NonTerminal(225, self.getAtomString(225)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 401:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(15, tracer) ) # typedef_identifier
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN11(self, depth=0, tracer=None):
    rule = self.rule(226)
    tree = ParseTree( NonTerminal(226, self.getAtomString(226)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [75]):
      return tree
    if self.sym == None:
      return tree
    if rule == 92:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._INIT_DECLARATOR_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [118, 37, 41]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._INIT_DECLARATOR_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    return tree
  def _PP_NODES_LIST(self, depth=0, tracer=None):
    rule = self.rule(227)
    tree = ParseTree( NonTerminal(227, self.getAtomString(227)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _PUNCTUATOR(self, depth=0, tracer=None):
    rule = self.rule(228)
    tree = ParseTree( NonTerminal(228, self.getAtomString(228)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 2:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(131, tracer) ) # rshifteq
      return tree
    elif rule == 6:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(93, tracer) ) # dot
      return tree
    elif rule == 8:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(103, tracer) ) # neq
      return tree
    elif rule == 13:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(17, tracer) ) # assign
      return tree
    elif rule == 18:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(59, tracer) ) # sub
      return tree
    elif rule == 19:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(4, tracer) ) # addeq
      return tree
    elif rule == 31:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(27, tracer) ) # comma
      return tree
    elif rule == 51:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(118, tracer) ) # lparen
      return tree
    elif rule == 67:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(65, tracer) ) # mod
      return tree
    elif rule == 70:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(98, tracer) ) # lbrace
      return tree
    elif rule == 91:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(63, tracer) ) # add
      return tree
    elif rule == 101:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(130, tracer) ) # gt
      return tree
    elif rule == 120:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(55, tracer) ) # lshift
      return tree
    elif rule == 150:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(24, tracer) ) # pound
      return tree
    elif rule == 156:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(71, tracer) ) # elipsis
      return tree
    elif rule == 179:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(7, tracer) ) # modeq
      return tree
    elif rule == 187:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(123, tracer) ) # lt
      return tree
    elif rule == 192:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(78, tracer) ) # colon
      return tree
    elif rule == 196:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(85, tracer) ) # arrow
      return tree
    elif rule == 198:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(120, tracer) ) # bitandeq
      return tree
    elif rule == 205:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(84, tracer) ) # questionmark
      return tree
    elif rule == 206:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(31, tracer) ) # lteq
      return tree
    elif rule == 231:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(109, tracer) ) # bitoreq
      return tree
    elif rule == 233:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(34, tracer) ) # muleq
      return tree
    elif rule == 239:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(119, tracer) ) # gteq
      return tree
    elif rule == 241:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(108, tracer) ) # eq
      return tree
    elif rule == 247:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(74, tracer) ) # div
      return tree
    elif rule == 256:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(115, tracer) ) # bitxoreq
      return tree
    elif rule == 270:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(128, tracer) ) # exclamation_point
      return tree
    elif rule == 282:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(26, tracer) ) # rsquare
      return tree
    elif rule == 284:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(94, tracer) ) # or
      return tree
    elif rule == 291:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(6, tracer) ) # lsquare
      return tree
    elif rule == 298:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(89, tracer) ) # lshifteq
      return tree
    elif rule == 322:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(122, tracer) ) # rparen
      return tree
    elif rule == 341:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(100, tracer) ) # bitor
      return tree
    elif rule == 344:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(88, tracer) ) # incr
      return tree
    elif rule == 350:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(14, tracer) ) # subeq
      return tree
    elif rule == 365:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(99, tracer) ) # and
      return tree
    elif rule == 384:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(77, tracer) ) # ampersand
      return tree
    elif rule == 391:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(60, tracer) ) # rshift
      return tree
    elif rule == 425:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(104, tracer) ) # bitxor
      return tree
    elif rule == 431:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(102, tracer) ) # rbrace
      return tree
    elif rule == 432:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(75, tracer) ) # semi
      return tree
    elif rule == 442:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(28, tracer) ) # poundpound
      return tree
    elif rule == 443:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(82, tracer) ) # decr
      return tree
    elif rule == 454:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(54, tracer) ) # tilde
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _SPECIFIER_QUALIFIER(self, depth=0, tracer=None):
    rule = self.rule(229)
    tree = ParseTree( NonTerminal(229, self.getAtomString(229)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 277:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._TYPE_QUALIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 319:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._TYPE_SPECIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN25(self, depth=0, tracer=None):
    rule = self.rule(230)
    tree = ParseTree( NonTerminal(230, self.getAtomString(230)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [75, 27]):
      return tree
    if self.sym == None:
      return tree
    if rule == 207:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STRUCT_DECLARATOR_BODY(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _STRUCT_OR_UNION_SUB(self, depth=0, tracer=None):
    rule = self.rule(231)
    tree = ParseTree( NonTerminal(231, self.getAtomString(231)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 162:
      tree.astTransform = AstTransformNodeCreator('StructOrUnion', {'body': 0})
      subtree = self._STRUCT_OR_UNION_BODY(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 436:
      tree.astTransform = AstTransformNodeCreator('StructOrUnion', {'body': 1, 'name': 0})
      tree.add( self.expect(41, tracer) ) # identifier
      subtree = self.__GEN20(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _DEFINE_LINE(self, depth=0, tracer=None):
    rule = self.rule(232)
    tree = ParseTree( NonTerminal(232, self.getAtomString(232)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _PARAMETER_TYPE_LIST_OPT(self, depth=0, tracer=None):
    rule = self.rule(233)
    tree = ParseTree( NonTerminal(233, self.getAtomString(233)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 235:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PARAMETER_TYPE_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _PP_FILE(self, depth=0, tracer=None):
    rule = self.rule(234)
    tree = ParseTree( NonTerminal(234, self.getAtomString(234)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN28(self, depth=0, tracer=None):
    rule = self.rule(235)
    tree = ParseTree( NonTerminal(235, self.getAtomString(235)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in [49]):
      return tree
    if self.sym == None:
      return tree
    if rule == 398:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(27, tracer) ) # comma
      subtree = self._ENUMERATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN28(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _PRAGMA_LINE(self, depth=0, tracer=None):
    rule = self.rule(236)
    tree = ParseTree( NonTerminal(236, self.getAtomString(236)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _INIT_DECLARATOR_LIST(self, depth=0, tracer=None):
    rule = self.rule(237)
    tree = ParseTree( NonTerminal(237, self.getAtomString(237)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 297:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN13(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [118, 37, 41]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN13(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN4(self, depth=0, tracer=None):
    rule = self.rule(238)
    tree = ParseTree( NonTerminal(238, self.getAtomString(238)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 112:
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
  def __GEN31(self, depth=0, tracer=None):
    rule = self.rule(239)
    tree = ParseTree( NonTerminal(239, self.getAtomString(239)), tracer )
    tree.list = 'slist'
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 428:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PARAMETER_DECLARATION(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN32(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN22(self, depth=0, tracer=None):
    rule = self.rule(240)
    tree = ParseTree( NonTerminal(240, self.getAtomString(240)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [118, 37, 23, 78, 41]):
      return tree
    if self.sym == None:
      return tree
    if rule == 410:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._SPECIFIER_QUALIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN22(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN32(self, depth=0, tracer=None):
    rule = self.rule(241)
    tree = ParseTree( NonTerminal(241, self.getAtomString(241)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in [9]):
      return tree
    if self.sym == None:
      return tree
    if rule == 456:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(27, tracer) ) # comma
      subtree = self._PARAMETER_DECLARATION(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN32(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _ENUM_SPECIFIER(self, depth=0, tracer=None):
    rule = self.rule(242)
    tree = ParseTree( NonTerminal(242, self.getAtomString(242)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 346:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(83, tracer) ) # enum
      subtree = self._ENUM_SPECIFIER_SUB(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN12(self, depth=0, tracer=None):
    rule = self.rule(243)
    tree = ParseTree( NonTerminal(243, self.getAtomString(243)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [98]):
      return tree
    if self.sym == None:
      return tree
    if rule == 397:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DECLARATION(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN12(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _STRUCT_OR_UNION_BODY(self, depth=0, tracer=None):
    rule = self.rule(244)
    tree = ParseTree( NonTerminal(244, self.getAtomString(244)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 141:
      tree.astTransform = AstTransformSubstitution(1)
      tree.add( self.expect(98, tracer) ) # lbrace
      subtree = self.__GEN21(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(102, tracer) ) # rbrace
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _DIRECT_DECLARATOR_MODIFIER_LIST_OPT(self, depth=0, tracer=None):
    rule = self.rule(245)
    tree = ParseTree( NonTerminal(245, self.getAtomString(245)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [33, 11, 88, 23, 50, 41, 118, 67, 87, 82, 90, 53, 16, 29]):
      return tree
    if self.sym == None:
      return tree
    if rule == 229:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN30(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN20(self, depth=0, tracer=None):
    rule = self.rule(246)
    tree = ParseTree( NonTerminal(246, self.getAtomString(246)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [61, 25, 96, 111, 2, 83, 101, 64, 42, 58, 57, 121, 9, 86, 124, 37, 40, 41, 27, 118, 78, 79, 19, 46, 18, 15, 23, 127, 48, 133, 97, 91]):
      return tree
    if self.sym == None:
      return tree
    if rule == 161:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STRUCT_OR_UNION_BODY(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _TYPE_SPECIFIER(self, depth=0, tracer=None):
    rule = self.rule(247)
    tree = ParseTree( NonTerminal(247, self.getAtomString(247)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 3:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(111, tracer) ) # float
      return tree
    elif rule == 16:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._UNION_SPECIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 152:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._TYPEDEF_NAME(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 163:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(42, tracer) ) # double
      return tree
    elif rule == 182:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(96, tracer) ) # short
      return tree
    elif rule == 215:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._STRUCT_SPECIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 217:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(48, tracer) ) # void
      return tree
    elif rule == 257:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(121, tracer) ) # signed
      return tree
    elif rule == 307:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(127, tracer) ) # unsigned
      return tree
    elif rule == 352:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._ENUM_SPECIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 362:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(91, tracer) ) # char
      return tree
    elif rule == 383:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(2, tracer) ) # long
      return tree
    elif rule == 388:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(133, tracer) ) # _bool
      return tree
    elif rule == 438:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(58, tracer) ) # _complex
      return tree
    elif rule == 449:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(101, tracer) ) # int
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _ENUM_SPECIFIER_SUB(self, depth=0, tracer=None):
    rule = self.rule(248)
    tree = ParseTree( NonTerminal(248, self.getAtomString(248)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 79:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._IDENTIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN26(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 317:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._ENUM_SPECIFIER_BODY(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _ELSE_STATEMENT(self, depth=0, tracer=None):
    rule = self.rule(249)
    tree = ParseTree( NonTerminal(249, self.getAtomString(249)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 73:
      tree.astTransform = AstTransformNodeCreator('Else', {'statement': 1})
      tree.add( self.expect(73, tracer) ) # else
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(132, tracer) ) # endif
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _WARNING_LINE(self, depth=0, tracer=None):
    rule = self.rule(250)
    tree = ParseTree( NonTerminal(250, self.getAtomString(250)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN6(self, depth=0, tracer=None):
    rule = self.rule(251)
    tree = ParseTree( NonTerminal(251, self.getAtomString(251)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 242:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(27, tracer) ) # comma
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
  def _VA_ARGS(self, depth=0, tracer=None):
    rule = self.rule(252)
    tree = ParseTree( NonTerminal(252, self.getAtomString(252)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 177:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(9, tracer) ) # comma_va_args
      tree.add( self.expect(71, tracer) ) # elipsis
      return tree
    return tree
  def _DIRECT_DECLARATOR_SIZE(self, depth=0, tracer=None):
    rule = self.rule(253)
    tree = ParseTree( NonTerminal(253, self.getAtomString(253)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 1:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 314:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(23, tracer) ) # asterisk
      return tree
    elif self.sym.getId() in [41, 29, 118, 16, 67, 33, 82, 23, 50, 11, 87, 90, 53, 88]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _IDENTIFIER(self, depth=0, tracer=None):
    rule = self.rule(254)
    tree = ParseTree( NonTerminal(254, self.getAtomString(254)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 369:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(41, tracer) ) # identifier
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _ENUM_SPECIFIER_BODY(self, depth=0, tracer=None):
    rule = self.rule(255)
    tree = ParseTree( NonTerminal(255, self.getAtomString(255)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 104:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(98, tracer) ) # lbrace
      subtree = self.__GEN27(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self._TRAILING_COMMA_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(102, tracer) ) # rbrace
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _DIRECT_ABSTRACT_DECLARATOR_OPT(self, depth=0, tracer=None):
    rule = self.rule(256)
    tree = ParseTree( NonTerminal(256, self.getAtomString(256)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [27, 9]):
      return tree
    if self.sym == None:
      return tree
    if rule == 149:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__DIRECT_ABSTRACT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [46, -1, 118]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__DIRECT_ABSTRACT_DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    return tree
  def __GEN26(self, depth=0, tracer=None):
    rule = self.rule(257)
    tree = ParseTree( NonTerminal(257, self.getAtomString(257)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [61, 25, 96, 111, 2, 83, 101, 64, 42, 58, 57, 121, 9, 86, 124, 37, 40, 41, 27, 118, 78, 79, 19, 46, 18, 15, 23, 127, 48, 133, 97, 91]):
      return tree
    if self.sym == None:
      return tree
    if rule == 96:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._ENUM_SPECIFIER_BODY(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _PP(self, depth=0, tracer=None):
    rule = self.rule(258)
    tree = ParseTree( NonTerminal(258, self.getAtomString(258)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 292:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(3, tracer) ) # defined
      return tree
    elif rule == 407:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(39, tracer) ) # defined_separator
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _FOR_INCR(self, depth=0, tracer=None):
    rule = self.rule(259)
    tree = ParseTree( NonTerminal(259, self.getAtomString(259)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [122]):
      return tree
    if self.sym == None:
      return tree
    if rule == 363:
      tree.astTransform = AstTransformSubstitution(1)
      tree.add( self.expect(75, tracer) ) # semi
      subtree = self._EXPRESSION_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _STORAGE_CLASS_SPECIFIER(self, depth=0, tracer=None):
    rule = self.rule(260)
    tree = ParseTree( NonTerminal(260, self.getAtomString(260)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 21:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(57, tracer) ) # extern
      return tree
    elif rule == 188:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(79, tracer) ) # register
      return tree
    elif rule == 226:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(61, tracer) ) # typedef
      return tree
    elif rule == 356:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(86, tracer) ) # static
      return tree
    elif rule == 366:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(64, tracer) ) # auto
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _LINE_LINE(self, depth=0, tracer=None):
    rule = self.rule(261)
    tree = ParseTree( NonTerminal(261, self.getAtomString(261)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN39(self, depth=0, tracer=None):
    rule = self.rule(262)
    tree = ParseTree( NonTerminal(262, self.getAtomString(262)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [110, 2, 58, 30, 61, 57, 67, 88, 86, 73, 11, 75, 64, 66, 16, 82, 79, 18, 50, 19, 98, 23, 48, 72, 124, 132, 90, 91, 25, 96, 87, 83, 29, 101, 102, 33, 105, 106, 111, 97, 113, 40, 42, 41, 69, 121, 118, 15, 126, 127, 53, 112, 52, 133]):
      return tree
    if self.sym == None:
      return tree
    if rule == 393:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._ELSE_IF_STATEMENT_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _ELSE_IF_STATEMENT(self, depth=0, tracer=None):
    rule = self.rule(263)
    tree = ParseTree( NonTerminal(263, self.getAtomString(263)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 364:
      tree.astTransform = AstTransformNodeCreator('ElseIf', {'statement': 4, 'condition': 2})
      tree.add( self.expect(129, tracer) ) # else_if
      tree.add( self.expect(118, tracer) ) # lparen
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(122, tracer) ) # rparen
      subtree = self._STATEMENT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(132, tracer) ) # endif
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN41(self, depth=0, tracer=None):
    rule = self.rule(264)
    tree = ParseTree( NonTerminal(264, self.getAtomString(264)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [110, 57, 58, 30, 61, 66, 67, 88, 86, 73, 11, 75, 64, 15, 16, 82, 79, 18, 50, 19, 98, 2, 48, 72, 124, 132, 90, 91, 25, 96, 87, 83, 29, 106, 102, 33, 105, 101, 111, 97, 113, 40, 41, 42, 69, 23, 121, 118, 126, 127, 53, 112, 52, 133]):
      return tree
    if self.sym == None:
      return tree
    if rule == 429:
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
    rule = self.rule(265)
    tree = ParseTree( NonTerminal(265, self.getAtomString(265)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 411:
      tree.astTransform = AstTransformNodeCreator('ParameterTypeList', {'parameter_declarations': 0, 'va_args': 1})
      subtree = self.__GEN31(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self._VA_ARGS(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _INCLUDE_TYPE(self, depth=0, tracer=None):
    rule = self.rule(266)
    tree = ParseTree( NonTerminal(266, self.getAtomString(266)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN34(self, depth=0, tracer=None):
    rule = self.rule(267)
    tree = ParseTree( NonTerminal(267, self.getAtomString(267)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 417:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(27, tracer) ) # comma
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
  def _TYPE_QUALIFIER(self, depth=0, tracer=None):
    rule = self.rule(268)
    tree = ParseTree( NonTerminal(268, self.getAtomString(268)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 71:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(19, tracer) ) # const
      return tree
    elif rule == 143:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(25, tracer) ) # volatile
      return tree
    elif rule == 301:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(97, tracer) ) # restrict
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _ENUMERATOR(self, depth=0, tracer=None):
    rule = self.rule(269)
    tree = ParseTree( NonTerminal(269, self.getAtomString(269)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 371:
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
  def __GEN33(self, depth=0, tracer=None):
    rule = self.rule(270)
    tree = ParseTree( NonTerminal(270, self.getAtomString(270)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 294:
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
  def _STRUCT_DECLARATOR_BODY(self, depth=0, tracer=None):
    rule = self.rule(271)
    tree = ParseTree( NonTerminal(271, self.getAtomString(271)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 203:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(78, tracer) ) # colon
      subtree = self._DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _FUNCTION_SPECIFIER(self, depth=0, tracer=None):
    rule = self.rule(272)
    tree = ParseTree( NonTerminal(272, self.getAtomString(272)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 55:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(40, tracer) ) # inline
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _UNION_SPECIFIER(self, depth=0, tracer=None):
    rule = self.rule(273)
    tree = ParseTree( NonTerminal(273, self.getAtomString(273)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 348:
      tree.astTransform = AstTransformNodeCreator('Union', {'definition': 1})
      tree.add( self.expect(124, tracer) ) # union
      subtree = self._STRUCT_OR_UNION_SUB(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _INIT_DECLARATOR(self, depth=0, tracer=None):
    rule = self.rule(274)
    tree = ParseTree( NonTerminal(274, self.getAtomString(274)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 154:
      tree.astTransform = AstTransformNodeCreator('InitDeclarator', {'initializer': 1, 'declarator': 0})
      subtree = self._DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN15(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [118, 37, 41]:
      tree.astTransform = AstTransformNodeCreator('InitDeclarator', {'initializer': 1, 'declarator': 0})
      subtree = self._DECLARATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN15(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN29(self, depth=0, tracer=None):
    rule = self.rule(275)
    tree = ParseTree( NonTerminal(275, self.getAtomString(275)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [46, 37, 23, 27, 41, 118, 9, 86]):
      return tree
    if self.sym == None:
      return tree
    if rule == 309:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._TYPE_QUALIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN29(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _TYPE_QUALIFIER_LIST_OPT(self, depth=0, tracer=None):
    rule = self.rule(276)
    tree = ParseTree( NonTerminal(276, self.getAtomString(276)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [46, 37, 23, 27, 41, 118, 9, 86]):
      return tree
    if self.sym == None:
      return tree
    if rule == 199:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN29(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN19(self, depth=0, tracer=None):
    rule = self.rule(277)
    tree = ParseTree( NonTerminal(277, self.getAtomString(277)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [17]):
      return tree
    if self.sym == None:
      return tree
    if rule == 311:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DESIGNATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN19(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _POINTER_SUB(self, depth=0, tracer=None):
    rule = self.rule(278)
    tree = ParseTree( NonTerminal(278, self.getAtomString(278)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 261:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(23, tracer) ) # asterisk
      subtree = self._TYPE_QUALIFIER_LIST_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _KEYWORD(self, depth=0, tracer=None):
    rule = self.rule(279)
    tree = ParseTree( NonTerminal(279, self.getAtomString(279)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 7:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(18, tracer) ) # struct
      return tree
    elif rule == 37:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(106, tracer) ) # goto
      return tree
    elif rule == 45:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(66, tracer) ) # do
      return tree
    elif rule == 48:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(124, tracer) ) # union
      return tree
    elif rule == 86:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(91, tracer) ) # char
      return tree
    elif rule == 124:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(110, tracer) ) # switch
      return tree
    elif rule == 138:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(25, tracer) ) # volatile
      return tree
    elif rule == 155:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(42, tracer) ) # double
      return tree
    elif rule == 173:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(56, tracer) ) # _imaginary
      return tree
    elif rule == 178:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(61, tracer) ) # typedef
      return tree
    elif rule == 195:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(112, tracer) ) # default
      return tree
    elif rule == 254:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(83, tracer) ) # enum
      return tree
    elif rule == 260:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(64, tracer) ) # auto
      return tree
    elif rule == 265:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(52, tracer) ) # if
      return tree
    elif rule == 273:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(126, tracer) ) # case
      return tree
    elif rule == 274:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(40, tracer) ) # inline
      return tree
    elif rule == 299:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(101, tracer) ) # int
      return tree
    elif rule == 306:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(58, tracer) ) # _complex
      return tree
    elif rule == 310:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(2, tracer) ) # long
      return tree
    elif rule == 330:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(111, tracer) ) # float
      return tree
    elif rule == 333:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(97, tracer) ) # restrict
      return tree
    elif rule == 334:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(48, tracer) ) # void
      return tree
    elif rule == 336:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(86, tracer) ) # static
      return tree
    elif rule == 340:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(19, tracer) ) # const
      return tree
    elif rule == 342:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(105, tracer) ) # continue
      return tree
    elif rule == 351:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(30, tracer) ) # while
      return tree
    elif rule == 353:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(127, tracer) ) # unsigned
      return tree
    elif rule == 355:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(72, tracer) ) # for
      return tree
    elif rule == 357:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(79, tracer) ) # register
      return tree
    elif rule == 368:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(113, tracer) ) # break
      return tree
    elif rule == 378:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(73, tracer) ) # else
      return tree
    elif rule == 379:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(69, tracer) ) # return
      return tree
    elif rule == 386:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(57, tracer) ) # extern
      return tree
    elif rule == 387:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(96, tracer) ) # short
      return tree
    elif rule == 409:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(121, tracer) ) # signed
      return tree
    elif rule == 416:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(87, tracer) ) # sizeof
      return tree
    elif rule == 419:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(133, tracer) ) # _bool
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _PARAMETER_DECLARATION_SUB(self, depth=0, tracer=None):
    rule = self.rule(280)
    tree = ParseTree( NonTerminal(280, self.getAtomString(280)), tracer )
    tree.list = False
    if self.sym == None:
      return tree
    if rule == 168:
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
    elif self.sym.getId() in [46, -1, 118]:
      tree.astTransform = AstTransformNodeCreator('ParameterSub', {'name_and_size': 1, 'pointer': 0})
      subtree = self._POINTER_OPT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self._PARAMETER_DECLARATION_SUB_SUB(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    elif self.sym.getId() in [118, 37, 41]:
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
  infixBp0 = {
    4: 2000,
    6: 16000,
    7: 2000,
    13: 2000,
    14: 2000,
    17: 2000,
    23: 13000,
    27: 1000,
    31: 10000,
    34: 2000,
    55: 11000,
    59: 12000,
    60: 11000,
    63: 12000,
    65: 13000,
    74: 13000,
    82: 16000,
    84: 3000,
    85: 16000,
    88: 16000,
    89: 2000,
    90: 6000,
    93: 16000,
    94: 4000,
    98: 15000,
    99: 5000,
    100: 8000,
    103: 9000,
    104: 7000,
    108: 9000,
    109: 2000,
    115: 2000,
    118: 16000,
    119: 10000,
    120: 2000,
    123: 10000,
    130: 10000,
    131: 2000,
  }
  prefixBp0 = {
    23: 14000,
    59: 14000,
    82: 14000,
    88: 14000,
    90: 14000,
    95: 14000,
    107: 14000,
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
    tree = ParseTree( NonTerminal(199, '_expr') )
    if not self.sym:
      return tree
    elif self.sym.getId() in [118]:
      tree.astTransform = AstTransformSubstitution(2)
      tree.add( self.expect(118, tracer) )
      tree.add( self.__EXPR() )
      tree.add( self.expect(122, tracer) )
    elif self.sym.getId() in [82]:
      tree.astTransform = AstTransformNodeCreator('PreDecr', {'var': 1})
      tree.add( self.expect(82, tracer) )
      tree.add( self.__EXPR( self.prefixBp0[82] ) )
      tree.isPrefix = True
    elif self.sym.getId() in [41]:
      tree.astTransform = AstTransformNodeCreator('ArrayIndex', {'params': 2, 'name': 0})
      return self.expect( 41, tracer )
    elif self.sym.getId() in [41]:
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      return self.expect( 41, tracer )
    elif self.sym.getId() in [88]:
      tree.astTransform = AstTransformNodeCreator('PreIncr', {'var': 1})
      tree.add( self.expect(88, tracer) )
      tree.add( self.__EXPR( self.prefixBp0[88] ) )
      tree.isPrefix = True
    elif self.sym.getId() in [87]:
      tree.astTransform = AstTransformNodeCreator('SizeOf', {'var': 1})
      return self.expect( 87, tracer )
    elif self.sym.getId() in [50, 33, 11, 29]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self._CONSTANT() )
    elif self.sym.getId() in [53]:
      tree.astTransform = AstTransformSubstitution(0)
      return self.expect( 53, tracer )
    elif self.sym.getId() in [23]:
      tree.astTransform = AstTransformNodeCreator('Dereference', {'var': 1})
      tree.add( self.expect(23, tracer) )
      tree.add( self.__EXPR( self.prefixBp0[23] ) )
      tree.isPrefix = True
    elif self.sym.getId() in [16]:
      tree.astTransform = AstTransformNodeCreator('TypeInitializion', {'type': 1, 'initializer': 4})
      tree.add( self.expect(16, tracer) )
      tree.add( self._TYPE_NAME() )
      tree.add( self.expect(122, tracer) )
    elif self.sym.getId() in [90]:
      tree.astTransform = AstTransformNodeCreator('AddressOf', {'var': 1})
      tree.add( self.expect(90, tracer) )
      tree.add( self.__EXPR( self.prefixBp0[90] ) )
      tree.isPrefix = True
    elif self.sym.getId() in [41]:
      tree.astTransform = AstTransformSubstitution(0)
      return self.expect( 41, tracer )
    return tree
  def led0(self, left, tracer):
    tree = ParseTree( NonTerminal(199, '_expr') )
    if  self.sym.getId() == 93: # 'dot'
      tree.astTransform = AstTransformNodeCreator('MemberSelect', {'member': 2, 'object': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(93, tracer) )
      tree.add( self.__EXPR() )
    elif  self.sym.getId() == 89: # 'lshifteq'
      tree.astTransform = AstTransformNodeCreator('LeftShiftAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(89, tracer) )
      tree.add( self.__EXPR( self.infixBp0[89] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 27: # 'comma'
      tree.astTransform = AstTransformNodeCreator('Comma', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(27, tracer) )
      tree.add( self.__EXPR( self.infixBp0[27] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 115: # 'bitxoreq'
      tree.astTransform = AstTransformNodeCreator('XORAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(115, tracer) )
      tree.add( self.__EXPR( self.infixBp0[115] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 23: # 'asterisk'
      tree.astTransform = AstTransformNodeCreator('Mul', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(23, tracer) )
      tree.add( self.__EXPR( self.infixBp0[23] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 59: # 'sub'
      tree.astTransform = AstTransformNodeCreator('Sub', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(59, tracer) )
      tree.add( self.__EXPR( self.infixBp0[59] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 118: # 'lparen'
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(118, tracer) )
      tree.add( self.__GEN5() )
      tree.add( self.expect(122, tracer) )
    elif  self.sym.getId() == 85: # 'arrow'
      tree.astTransform = AstTransformNodeCreator('DerefMemberSelect', {'member': 2, 'object': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(85, tracer) )
      tree.add( self.__EXPR() )
    elif  self.sym.getId() == 14: # 'subeq'
      tree.astTransform = AstTransformNodeCreator('SubtractAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(14, tracer) )
      tree.add( self.__EXPR( self.infixBp0[14] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 1: # 'sizeof_separator'
      tree.astTransform = AstTransformNodeCreator('SizeOf', {'var': 1})
      if left:
        tree.add(left)
      tree.add( self.expect(1, tracer) )
      tree.add( self._SIZEOF_BODY() )
    elif  self.sym.getId() == 34: # 'muleq'
      tree.astTransform = AstTransformNodeCreator('MultiplyAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(34, tracer) )
      tree.add( self.__EXPR( self.infixBp0[34] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 74: # 'div'
      tree.astTransform = AstTransformNodeCreator('Div', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(74, tracer) )
      tree.add( self.__EXPR( self.infixBp0[74] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 82: # 'decr'
      tree.astTransform = AstTransformNodeCreator('PostDecr', {'var': 0})
      if left:
        tree.add(left)
      return self.expect( 82, tracer )
    elif  self.sym.getId() == 123: # 'lt'
      tree.astTransform = AstTransformNodeCreator('LessThan', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(123, tracer) )
      tree.add( self.__EXPR( self.infixBp0[123] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 55: # 'lshift'
      tree.astTransform = AstTransformNodeCreator('LeftShift', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(55, tracer) )
      tree.add( self.__EXPR( self.infixBp0[55] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 84: # 'questionmark'
      tree.astTransform = AstTransformNodeCreator('TernaryOperator', {'true': 2, 'false': 4, 'cond': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(84, tracer) )
      tree.add( self.__EXPR() )
      tree.add( self.expect(78, tracer) )
      tree.add( self.__EXPR() )
    elif  self.sym.getId() == 60: # 'rshift'
      tree.astTransform = AstTransformNodeCreator('RightShift', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(60, tracer) )
      tree.add( self.__EXPR( self.infixBp0[60] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 6: # 'lsquare'
      tree.astTransform = AstTransformNodeCreator('ArrayIndex', {'params': 2, 'name': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(6, tracer) )
      tree.add( self.__GEN5() )
      tree.add( self.expect(26, tracer) )
    elif  self.sym.getId() == 65: # 'mod'
      tree.astTransform = AstTransformNodeCreator('Mod', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(65, tracer) )
      tree.add( self.__EXPR( self.infixBp0[65] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 130: # 'gt'
      tree.astTransform = AstTransformNodeCreator('GreaterThan', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(130, tracer) )
      tree.add( self.__EXPR( self.infixBp0[130] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 13: # 'diveq'
      tree.astTransform = AstTransformNodeCreator('DivideAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(13, tracer) )
      tree.add( self.__EXPR( self.infixBp0[13] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 90: # 'bitand'
      tree.astTransform = AstTransformNodeCreator('BitAND', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(90, tracer) )
      tree.add( self.__EXPR( self.infixBp0[90] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 131: # 'rshifteq'
      tree.astTransform = AstTransformNodeCreator('RightShiftAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(131, tracer) )
      tree.add( self.__EXPR( self.infixBp0[131] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 108: # 'eq'
      tree.astTransform = AstTransformNodeCreator('Equals', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(108, tracer) )
      tree.add( self.__EXPR( self.infixBp0[108] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 7: # 'modeq'
      tree.astTransform = AstTransformNodeCreator('ModAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(7, tracer) )
      tree.add( self.__EXPR( self.infixBp0[7] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 31: # 'lteq'
      tree.astTransform = AstTransformNodeCreator('LessThanEq', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(31, tracer) )
      tree.add( self.__EXPR( self.infixBp0[31] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 88: # 'incr'
      tree.astTransform = AstTransformNodeCreator('PostIncr', {'var': 0})
      if left:
        tree.add(left)
      return self.expect( 88, tracer )
    elif  self.sym.getId() == 100: # 'bitor'
      tree.astTransform = AstTransformNodeCreator('BitOR', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(100, tracer) )
      tree.add( self.__EXPR( self.infixBp0[100] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 120: # 'bitandeq'
      tree.astTransform = AstTransformNodeCreator('ANDAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(120, tracer) )
      tree.add( self.__EXPR( self.infixBp0[120] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 98: # 'lbrace'
      tree.astTransform = AstTransformNodeCreator('TypeInitializion', {'type': 1, 'initializer': 4})
      if left:
        tree.add(left)
      tree.add( self.expect(98, tracer) )
      tree.add( self.__GEN16() )
      tree.add( self._TRAILING_COMMA_OPT() )
      tree.add( self.expect(102, tracer) )
    elif  self.sym.getId() == 17: # 'assign'
      tree.astTransform = AstTransformNodeCreator('Assign', {'var': 0, 'value': 2})
      if left:
        tree.add(left)
      tree.add( self.expect(17, tracer) )
      tree.add( self.__EXPR( self.infixBp0[17] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 104: # 'bitxor'
      tree.astTransform = AstTransformNodeCreator('BitXOR', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(104, tracer) )
      tree.add( self.__EXPR( self.infixBp0[104] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 119: # 'gteq'
      tree.astTransform = AstTransformNodeCreator('GreaterThanEq', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(119, tracer) )
      tree.add( self.__EXPR( self.infixBp0[119] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 109: # 'bitoreq'
      tree.astTransform = AstTransformNodeCreator('ORAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(109, tracer) )
      tree.add( self.__EXPR( self.infixBp0[109] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 63: # 'add'
      tree.astTransform = AstTransformNodeCreator('Add', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(63, tracer) )
      tree.add( self.__EXPR( self.infixBp0[63] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 4: # 'addeq'
      tree.astTransform = AstTransformNodeCreator('AddAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(4, tracer) )
      tree.add( self.__EXPR( self.infixBp0[4] ) )
      tree.isInfix = True
    return tree
  infixBp1 = {
    6: 1000,
    118: 1000,
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
    tree = ParseTree( NonTerminal(138, '_direct_abstract_declarator') )
    if not self.sym:
      return tree
    if self.sym.getId() in [118]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(118, tracer) )
      tree.add( self._ABSTRACT_DECLARATOR() )
      tree.add( self.expect(122, tracer) )
    elif self.sym.getId() in [46, -1, 118]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self._DIRECT_ABSTRACT_DECLARATOR_OPT() )
    elif self.sym.getId() in [46, -1, 118]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self._DIRECT_ABSTRACT_DECLARATOR_OPT() )
    return tree
  def led1(self, left, tracer):
    tree = ParseTree( NonTerminal(138, '_direct_abstract_declarator') )
    if  self.sym.getId() == 6: # 'lsquare'
      tree.astTransform = AstTransformSubstitution(0)
      if left:
        tree.add(left)
      tree.add( self.expect(6, tracer) )
      tree.add( self._DIRECT_ABSTRACT_DECLARATOR_EXPR() )
      tree.add( self.expect(26, tracer) )
    elif  self.sym.getId() == 118: # 'lparen'
      tree.astTransform = AstTransformSubstitution(0)
      if left:
        tree.add(left)
      tree.add( self.expect(118, tracer) )
      tree.add( self._PARAMETER_TYPE_LIST_OPT() )
      tree.add( self.expect(122, tracer) )
    return tree
  infixBp2 = {
    6: 1000,
    118: 1000,
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
    tree = ParseTree( NonTerminal(214, '_direct_declarator') )
    if not self.sym:
      return tree
    if self.sym.getId() in [41]:
      tree.astTransform = AstTransformSubstitution(0)
      return self.expect( 41, tracer )
    elif self.sym.getId() in [118]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(118, tracer) )
      tree.add( self._DECLARATOR() )
      tree.add( self.expect(122, tracer) )
    return tree
  def led2(self, left, tracer):
    tree = ParseTree( NonTerminal(214, '_direct_declarator') )
    if  self.sym.getId() == 118: # 'lparen'
      tree.astTransform = AstTransformNodeCreator('FunctionSignature', {'params': 2, 'name': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(118, tracer) )
      tree.add( self._DIRECT_DECLARATOR_PARAMETER_LIST() )
      tree.add( self.expect(122, tracer) )
      print(tree, '')
    elif  self.sym.getId() == 6: # 'lsquare'
      tree.astTransform = AstTransformNodeCreator('Array', {'name': 0, 'size': 2})
      if left:
        tree.add(left)
      tree.add( self.expect(6, tracer) )
      tree.add( self._DIRECT_DECLARATOR_EXPR() )
      tree.add( self.expect(26, tracer) )
    return tree
