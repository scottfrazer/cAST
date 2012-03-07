import sys, inspect
from cast.ParserCommon import *
def whoami():
  return inspect.stack()[1][3]
def whosdaddy():
  return inspect.stack()[2][3]
def parse( iterator, entry ):
  p = pp_Parser()
  return p.parse(iterator, entry)
class pp_ExpressionParser__expr:
  def __init__(self, parent):
    self.__dict__.update(locals())
    self.infixBp = {
      0: 10000,
      3: 11000,
      4: 12000,
      8: 12000,
      13: 12000,
      24: 2000,
      28: 5000,
      32: 3000,
      35: 1000,
      37: 14000,
      39: 4000,
      40: 7000,
      41: 9000,
      43: 8000,
      44: 6000,
      47: 8000,
      52: 9000,
      55: 15000,
      65: 9000,
      67: 9000,
      70: 10000,
      73: 11000,
    }
    self.prefixBp = {
      8: 13000,
      28: 13000,
      33: 13000,
      62: 13000,
      64: 13000,
      73: 13000,
    }
  def getInfixBp(self, tokenId):
    try:
      return self.infixBp[tokenId]
    except:
      return 0
  def getPrefixBp(self, tokenId):
    try:
      return self.prefixBp[tokenId]
    except:
      return 0
  def getCurrentToken(self):
    return self.parent.tokens.current()
  def expect(self, token):
    return self.parent.expect(token)
  def parse(self, rbp = 0):
    left = self.nud()
    if isinstance(left, ParseTree):
      left.isExpr = True
      left.isNud = True
    while self.getCurrentToken() and rbp < self.getInfixBp(self.getCurrentToken().getId()):
      left = self.led(left)
    if left:
      left.isExpr = True
    return left
  def nud(self):
    tree = ParseTree( NonTerminal(79, '_expr') )
    current = self.getCurrentToken()
    if not current:
      return tree
    elif current.getId() in [63]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      tree.add( self.expect(63) )
    elif current.getId() in [62]:
      tree.astTransform = AstTransformNodeCreator('IsDefined', {'expr': 2})
      tree.nudMorphemeCount = 1
      tree.add( self.expect(62) )
    elif current.getId() in [54]:
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      tree.nudMorphemeCount = 1
      tree.add( self.expect(54) )
    elif current.getId() in [68]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      tree.add( self.expect(68) )
    elif current.getId() in [64]:
      tree.astTransform = AstTransformNodeCreator('Not', {'expr': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(64) )
      tree.add( self.parent.parse__expr( self.getPrefixBp(64) ) )
      tree.isPrefix = True
    elif current.getId() in [54]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      tree.add( self.expect(54) )
    elif current.getId() in [58]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      tree.add( self.expect(58) )
    elif current.getId() in [33]:
      tree.astTransform = AstTransformNodeCreator('BitNOT', {'expr': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(33) )
      tree.add( self.parent.parse__expr( self.getPrefixBp(33) ) )
      tree.isPrefix = True
    elif current.getId() in [55]:
      tree.astTransform = AstTransformSubstitution(1)
      tree.nudMorphemeCount = 3
      tree.add( self.expect(55) )
      tree.add( self.parent.parse__expr() )
      tree.add( self.expect(59) )
    return tree
  def led(self, left):
    tree = ParseTree( NonTerminal(79, '_expr') )
    current = self.getCurrentToken()
    if current.getId() == 4: # 'mod'
      tree.astTransform = AstTransformNodeCreator('Mod', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(4) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(4) - modifier ) )
      return tree
    if current.getId() == 52: # 'lteq'
      tree.astTransform = AstTransformNodeCreator('LessThanEq', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(52) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(52) - modifier ) )
      return tree
    if current.getId() == 67: # 'lt'
      tree.astTransform = AstTransformNodeCreator('LessThan', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(67) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(67) - modifier ) )
      return tree
    if current.getId() == 44: # 'bitxor'
      tree.astTransform = AstTransformNodeCreator('BitXOR', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(44) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(44) - modifier ) )
      return tree
    if current.getId() == 37: # 'defined_separator'
      tree.astTransform = AstTransformNodeCreator('IsDefined', {'expr': 2})
      tree.add(left)
      tree.add( self.expect(37) )
      tree.add( self.parent.parse_defined_identifier() )
      return tree
    if current.getId() == 55: # 'lparen'
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      tree.add(left)
      tree.add( self.expect(55) )
      tree.add( self.parent.parse__gen5() )
      tree.add( self.expect(59) )
      return tree
    if current.getId() == 43: # 'neq'
      tree.astTransform = AstTransformNodeCreator('NotEquals', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(43) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(43) - modifier ) )
      return tree
    if current.getId() == 35: # 'comma'
      tree.astTransform = AstTransformNodeCreator('Comma', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(35) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(35) - modifier ) )
      return tree
    if current.getId() == 70: # 'lshift'
      tree.astTransform = AstTransformNodeCreator('LeftShift', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(70) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(70) - modifier ) )
      return tree
    if current.getId() == 32: # 'or'
      tree.astTransform = AstTransformNodeCreator('Or', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(32) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(32) - modifier ) )
      return tree
    if current.getId() == 13: # 'div'
      tree.astTransform = AstTransformNodeCreator('Div', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(13) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(13) - modifier ) )
      return tree
    if current.getId() == 39: # 'and'
      tree.astTransform = AstTransformNodeCreator('And', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(39) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(39) - modifier ) )
      return tree
    if current.getId() == 8: # 'mul'
      tree.astTransform = AstTransformNodeCreator('Mul', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(8) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(8) - modifier ) )
      return tree
    if current.getId() == 28: # 'bitand'
      tree.astTransform = AstTransformNodeCreator('BitAND', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(28) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(28) - modifier ) )
      return tree
    if current.getId() == 65: # 'gt'
      tree.astTransform = AstTransformNodeCreator('GreaterThan', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(65) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(65) - modifier ) )
      return tree
    if current.getId() == 40: # 'bitor'
      tree.astTransform = AstTransformNodeCreator('BitOR', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(40) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(40) - modifier ) )
      return tree
    if current.getId() == 24: # 'questionmark'
      tree.astTransform = AstTransformNodeCreator('TernaryOperator', {'true': 2, 'false': 4, 'cond': 0})
      tree.isExprNud = True 
      tree.add(left)
      tree.add( self.expect(24) )
      modifier = 1
      tree.add( self.parent.parse__expr( self.getInfixBp(24) - modifier ) )
      tree.add( self.expect(18) )
      modifier = 1
      tree.add( self.parent.parse__expr( self.getInfixBp(24) - modifier ) )
      return tree
    if current.getId() == 41: # 'gteq'
      tree.astTransform = AstTransformNodeCreator('GreaterThanEq', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(41) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(41) - modifier ) )
      return tree
    if current.getId() == 73: # 'sub'
      tree.astTransform = AstTransformNodeCreator('Sub', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(73) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(73) - modifier ) )
      return tree
    if current.getId() == 3: # 'add'
      tree.astTransform = AstTransformNodeCreator('Add', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(3) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(3) - modifier ) )
      return tree
    if current.getId() == 47: # 'eq'
      tree.astTransform = AstTransformNodeCreator('Equals', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(47) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(47) - modifier ) )
      return tree
    if current.getId() == 0: # 'rshift'
      tree.astTransform = AstTransformNodeCreator('RightShift', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(0) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(0) - modifier ) )
      return tree
    return tree
class pp_Parser:
  # Quark - finite string set maps one string to exactly one int, and vice versa
  terminals = {
    0: 'rshift',
    1: 'addeq',
    2: 'ifndef',
    3: 'add',
    4: 'mod',
    5: 'poundpound',
    6: 'modeq',
    7: 'elif',
    8: 'mul',
    9: 'elipsis',
    10: 'pragma',
    11: 'muleq',
    12: 'else',
    13: 'div',
    14: 'csource',
    15: 'diveq',
    16: 'semi',
    17: 'ampersand',
    18: 'colon',
    19: 'incr',
    20: 'assign',
    21: 'define',
    22: 'define_function',
    23: 'decr',
    24: 'questionmark',
    25: 'include',
    26: 'arrow',
    27: 'if',
    28: 'bitand',
    29: 'separator',
    30: 'pound',
    31: 'dot',
    32: 'or',
    33: 'bitnot',
    34: 'header_global',
    35: 'comma',
    36: 'undef',
    37: 'defined_separator',
    38: 'lbrace',
    39: 'and',
    40: 'bitor',
    41: 'gteq',
    42: 'rbrace',
    43: 'neq',
    44: 'bitxor',
    45: 'lsquare',
    46: '_expr',
    47: 'eq',
    48: 'bitoreq',
    49: 'line',
    50: 'rsquare',
    51: 'header_local',
    52: 'lteq',
    53: 'bitxoreq',
    54: 'identifier',
    55: 'lparen',
    56: 'error',
    57: 'bitandeq',
    58: 'pp_number',
    59: 'rparen',
    60: 'warning',
    61: 'lshifteq',
    62: 'defined',
    63: 'character_constant',
    64: 'exclamation_point',
    65: 'gt',
    66: 'rshifteq',
    67: 'lt',
    68: 'string_literal',
    69: 'tilde',
    70: 'lshift',
    71: 'subeq',
    72: 'ifdef',
    73: 'sub',
    74: 'endif',
    'rshift': 0,
    'addeq': 1,
    'ifndef': 2,
    'add': 3,
    'mod': 4,
    'poundpound': 5,
    'modeq': 6,
    'elif': 7,
    'mul': 8,
    'elipsis': 9,
    'pragma': 10,
    'muleq': 11,
    'else': 12,
    'div': 13,
    'csource': 14,
    'diveq': 15,
    'semi': 16,
    'ampersand': 17,
    'colon': 18,
    'incr': 19,
    'assign': 20,
    'define': 21,
    'define_function': 22,
    'decr': 23,
    'questionmark': 24,
    'include': 25,
    'arrow': 26,
    'if': 27,
    'bitand': 28,
    'separator': 29,
    'pound': 30,
    'dot': 31,
    'or': 32,
    'bitnot': 33,
    'header_global': 34,
    'comma': 35,
    'undef': 36,
    'defined_separator': 37,
    'lbrace': 38,
    'and': 39,
    'bitor': 40,
    'gteq': 41,
    'rbrace': 42,
    'neq': 43,
    'bitxor': 44,
    'lsquare': 45,
    '_expr': 46,
    'eq': 47,
    'bitoreq': 48,
    'line': 49,
    'rsquare': 50,
    'header_local': 51,
    'lteq': 52,
    'bitxoreq': 53,
    'identifier': 54,
    'lparen': 55,
    'error': 56,
    'bitandeq': 57,
    'pp_number': 58,
    'rparen': 59,
    'warning': 60,
    'lshifteq': 61,
    'defined': 62,
    'character_constant': 63,
    'exclamation_point': 64,
    'gt': 65,
    'rshifteq': 66,
    'lt': 67,
    'string_literal': 68,
    'tilde': 69,
    'lshift': 70,
    'subeq': 71,
    'ifdef': 72,
    'sub': 73,
    'endif': 74,
  }
  # Quark - finite string set maps one string to exactly one int, and vice versa
  nonterminals = {
    75: '_gen4',
    76: 'pp_directive',
    77: 'pp_nodes',
    78: 'warning_line',
    79: '_expr',
    80: 'error_line',
    81: 'pp_tokens',
    82: 'define_func_param',
    83: 'pp_file',
    84: '_gen2',
    85: 'include_line',
    86: '_gen3',
    87: 'undef_line',
    88: 'defined_identifier',
    89: '_gen5',
    90: 'control_line',
    91: 'elipsis_opt',
    92: 'pp_nodes_list',
    93: '_gen6',
    94: 'line_line',
    95: 'pragma_line',
    96: '_gen0',
    97: 'if_part',
    98: 'elseif_part',
    99: 'define_line',
    100: 'punctuator',
    101: 'if_section',
    102: '_gen1',
    103: 'else_part',
    104: 'include_type',
    105: 'replacement_list',
    '_gen4': 75,
    'pp_directive': 76,
    'pp_nodes': 77,
    'warning_line': 78,
    '_expr': 79,
    'error_line': 80,
    'pp_tokens': 81,
    'define_func_param': 82,
    'pp_file': 83,
    '_gen2': 84,
    'include_line': 85,
    '_gen3': 86,
    'undef_line': 87,
    'defined_identifier': 88,
    '_gen5': 89,
    'control_line': 90,
    'elipsis_opt': 91,
    'pp_nodes_list': 92,
    '_gen6': 93,
    'line_line': 94,
    'pragma_line': 95,
    '_gen0': 96,
    'if_part': 97,
    'elseif_part': 98,
    'define_line': 99,
    'punctuator': 100,
    'if_section': 101,
    '_gen1': 102,
    'else_part': 103,
    'include_type': 104,
    'replacement_list': 105,
  }
  # table[nonterminal][terminal] = rule
  table = [
    [38, 38, -1, 38, 38, 38, 38, -1, 38, 38, -1, 38, -1, 38, -1, 38, 38, 38, 38, 38, 38, -1, -1, 38, 38, -1, 38, -1, 38, 107, 38, 38, 38, 38, 38, 38, -1, 38, 38, 38, 38, 38, 38, 38, 38, 38, -1, 38, 38, -1, 38, 38, 38, 38, 38, 38, -1, 38, 38, 38, -1, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, 38, -1, 38, -1],
    [-1, -1, 127, -1, -1, -1, -1, -1, -1, -1, 69, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 69, 69, -1, -1, 69, -1, 127, -1, -1, -1, -1, -1, -1, -1, -1, 69, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 69, -1, -1, -1, -1, -1, -1, 69, -1, -1, -1, 69, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 127, -1, -1],
    [-1, -1, 65, -1, -1, -1, -1, -1, -1, -1, 65, -1, -1, -1, 15, -1, -1, -1, -1, -1, -1, 65, 65, -1, -1, 65, -1, 65, -1, -1, -1, -1, -1, -1, -1, -1, 65, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 65, -1, -1, -1, -1, -1, -1, 65, -1, -1, -1, 65, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 65, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 90, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 101, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [12, 12, -1, 12, 12, 12, 12, -1, 12, 12, -1, 12, -1, 12, -1, 12, 12, 12, 12, 12, 12, -1, -1, 12, 12, -1, 12, -1, 12, -1, 12, 12, 12, 12, 52, 12, -1, 71, 12, 12, 12, 12, 12, 12, 12, 12, -1, 12, 12, -1, 12, 103, 12, 12, 94, 12, -1, 12, 85, 12, -1, 12, 80, 120, 12, 12, 12, 12, 92, 12, 12, 12, -1, 12, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, 0, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 27, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 78, -1, -1, -1, -1, -1, -1, -1, 78, -1, -1, -1, 78, -1, -1, -1, -1, -1, -1, 78, 78, -1, -1, 78, -1, 78, -1, -1, -1, -1, -1, -1, -1, -1, 78, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 78, -1, -1, -1, -1, -1, -1, 78, -1, -1, -1, 78, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 78, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, 7, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 7, -1, -1, -1, -1, 102, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 99, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 9, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 87, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 140, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 130, 139, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 1, -1, -1, -1, -1, -1, -1, -1, 1, 1, -1, -1, 1, -1, -1, -1, 1, 1, 1, -1, -1, -1, 1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 16, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 39, 39, -1, -1, 68, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 67, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 77, -1, -1, -1, -1, -1, -1, 135, -1, -1, -1, 46, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 18, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 30, -1, -1, -1, -1, 30, -1, -1, 30, -1, 30, -1, 30, -1, -1, -1, -1, -1, -1, 30, 30, -1, -1, 30, -1, 30, -1, -1, -1, -1, -1, -1, -1, -1, 30, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 30, -1, -1, -1, -1, -1, -1, 30, -1, -1, -1, 30, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 30, -1, 30],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 95, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 114, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 83, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 28, -1, -1, -1, -1, 31, -1, -1, 28, -1, 31, -1, 28, -1, -1, -1, -1, -1, -1, 28, 28, -1, -1, 28, -1, 28, -1, -1, -1, -1, -1, -1, -1, -1, 28, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 28, -1, -1, -1, -1, -1, -1, 28, -1, -1, -1, 28, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 28, -1, 31],
    [-1, -1, 82, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 131, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 88, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, 29, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 81, 61, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [8, 10, -1, 17, 22, 116, 25, -1, 74, 34, -1, 84, -1, 121, -1, 132, 136, 63, 91, 51, 110, -1, -1, 119, 20, -1, 2, -1, 11, -1, 47, 133, 24, 32, -1, 129, -1, -1, 35, 93, 50, 111, 124, 56, 54, 70, -1, 122, 75, -1, 79, -1, 58, 89, -1, 41, -1, 106, -1, 113, -1, 62, -1, -1, 125, 126, 128, 115, -1, 137, 76, 117, -1, 3, -1],
    [-1, -1, 13, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 13, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 13, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, 37, -1, -1, -1, -1, 59, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 42, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 55],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 108, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 118, -1, -1, 4, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [5, 5, -1, 5, 5, 5, 5, -1, 5, 5, -1, 5, -1, 5, -1, 5, 5, 5, 5, 5, 5, -1, -1, 5, 5, -1, 5, -1, 5, 5, 5, 5, 5, 5, 5, 5, -1, 5, 5, 5, 5, 5, 5, 5, 5, 5, -1, 5, 5, -1, 5, 5, 5, 5, 5, 5, -1, 5, 5, 5, -1, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, -1, 5, -1],
  ]
  TERMINAL_RSHIFT = 0
  TERMINAL_ADDEQ = 1
  TERMINAL_IFNDEF = 2
  TERMINAL_ADD = 3
  TERMINAL_MOD = 4
  TERMINAL_POUNDPOUND = 5
  TERMINAL_MODEQ = 6
  TERMINAL_ELIF = 7
  TERMINAL_MUL = 8
  TERMINAL_ELIPSIS = 9
  TERMINAL_PRAGMA = 10
  TERMINAL_MULEQ = 11
  TERMINAL_ELSE = 12
  TERMINAL_DIV = 13
  TERMINAL_CSOURCE = 14
  TERMINAL_DIVEQ = 15
  TERMINAL_SEMI = 16
  TERMINAL_AMPERSAND = 17
  TERMINAL_COLON = 18
  TERMINAL_INCR = 19
  TERMINAL_ASSIGN = 20
  TERMINAL_DEFINE = 21
  TERMINAL_DEFINE_FUNCTION = 22
  TERMINAL_DECR = 23
  TERMINAL_QUESTIONMARK = 24
  TERMINAL_INCLUDE = 25
  TERMINAL_ARROW = 26
  TERMINAL_IF = 27
  TERMINAL_BITAND = 28
  TERMINAL_SEPARATOR = 29
  TERMINAL_POUND = 30
  TERMINAL_DOT = 31
  TERMINAL_OR = 32
  TERMINAL_BITNOT = 33
  TERMINAL_HEADER_GLOBAL = 34
  TERMINAL_COMMA = 35
  TERMINAL_UNDEF = 36
  TERMINAL_DEFINED_SEPARATOR = 37
  TERMINAL_LBRACE = 38
  TERMINAL_AND = 39
  TERMINAL_BITOR = 40
  TERMINAL_GTEQ = 41
  TERMINAL_RBRACE = 42
  TERMINAL_NEQ = 43
  TERMINAL_BITXOR = 44
  TERMINAL_LSQUARE = 45
  TERMINAL__EXPR = 46
  TERMINAL_EQ = 47
  TERMINAL_BITOREQ = 48
  TERMINAL_LINE = 49
  TERMINAL_RSQUARE = 50
  TERMINAL_HEADER_LOCAL = 51
  TERMINAL_LTEQ = 52
  TERMINAL_BITXOREQ = 53
  TERMINAL_IDENTIFIER = 54
  TERMINAL_LPAREN = 55
  TERMINAL_ERROR = 56
  TERMINAL_BITANDEQ = 57
  TERMINAL_PP_NUMBER = 58
  TERMINAL_RPAREN = 59
  TERMINAL_WARNING = 60
  TERMINAL_LSHIFTEQ = 61
  TERMINAL_DEFINED = 62
  TERMINAL_CHARACTER_CONSTANT = 63
  TERMINAL_EXCLAMATION_POINT = 64
  TERMINAL_GT = 65
  TERMINAL_RSHIFTEQ = 66
  TERMINAL_LT = 67
  TERMINAL_STRING_LITERAL = 68
  TERMINAL_TILDE = 69
  TERMINAL_LSHIFT = 70
  TERMINAL_SUBEQ = 71
  TERMINAL_IFDEF = 72
  TERMINAL_SUB = 73
  TERMINAL_ENDIF = 74
  def __init__(self, tokens=None):
    self.__dict__.update(locals())
    self.expressionParsers = dict()
  def isTerminal(self, id):
    return 0 <= id <= 74
  def isNonTerminal(self, id):
    return 75 <= id <= 105
  def parse(self, tokens):
    self.tokens = tokens
    self.start = 'PP_FILE'
    tree = self.parse_pp_file()
    if self.tokens.current() != None:
      raise SyntaxError( 'Finished parsing without consuming all tokens.' )
    return tree
  def expect(self, terminalId):
    currentToken = self.tokens.current()
    if not currentToken:
      raise SyntaxError( 'No more tokens.  Expecting %s' % (self.terminals[terminalId]) )
    if currentToken.getId() != terminalId:
      raise SyntaxError( 'Unexpected symbol when parsing %s.  Expected %s, got %s.' %(whosdaddy(), self.terminals[terminalId], currentToken if currentToken else 'None') )
    nextToken = self.tokens.advance()
    if nextToken and not self.isTerminal(nextToken.getId()):
      raise SyntaxError( 'Invalid symbol ID: %d (%s)' % (nextToken.getId(), nextToken) )
    return currentToken
  def parse__gen4(self):
    current = self.tokens.current()
    rule = self.table[0][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(75, self.nonterminals[75]))
    tree.list = 'nlist'
    if current != None and (current.getId() in [29]):
      return tree
    if current == None:
      return tree
    if rule == 38:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_pp_tokens()
      tree.add( subtree )
      subtree = self.parse__gen4()
      tree.add( subtree )
      return tree
    return tree
  def parse_pp_directive(self):
    current = self.tokens.current()
    rule = self.table[1][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(76, self.nonterminals[76]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 69:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_control_line()
      tree.add( subtree )
      return tree
    elif rule == 127:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_if_section()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_pp_nodes(self):
    current = self.tokens.current()
    rule = self.table[2][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(77, self.nonterminals[77]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 15:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(14) # csource
      tree.add(t)
      return tree
    elif rule == 65:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_pp_directive()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_warning_line(self):
    current = self.tokens.current()
    rule = self.table[3][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(78, self.nonterminals[78]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 90:
      tree.astTransform = AstTransformNodeCreator('Warning', {'tokens': 1})
      t = self.expect(60) # warning
      tree.add(t)
      subtree = self.parse__gen4()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_error_line(self):
    current = self.tokens.current()
    rule = self.table[5][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(80, self.nonterminals[80]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 101:
      tree.astTransform = AstTransformNodeCreator('Error', {'tokens': 1})
      t = self.expect(56) # error
      tree.add(t)
      subtree = self.parse__gen4()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_pp_tokens(self):
    current = self.tokens.current()
    rule = self.table[6][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(81, self.nonterminals[81]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 12:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_punctuator()
      tree.add( subtree )
      return tree
    elif rule == 52:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(34) # header_global
      tree.add(t)
      return tree
    elif rule == 71:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(37) # defined_separator
      tree.add(t)
      return tree
    elif rule == 80:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(62) # defined
      tree.add(t)
      return tree
    elif rule == 85:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(58) # pp_number
      tree.add(t)
      return tree
    elif rule == 92:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(68) # string_literal
      tree.add(t)
      return tree
    elif rule == 94:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(54) # identifier
      tree.add(t)
      return tree
    elif rule == 103:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(51) # header_local
      tree.add(t)
      return tree
    elif rule == 120:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(63) # character_constant
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_define_func_param(self):
    current = self.tokens.current()
    rule = self.table[7][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(82, self.nonterminals[82]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 0:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(9) # elipsis
      tree.add(t)
      return tree
    elif rule == 27:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(54) # identifier
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_pp_file(self):
    current = self.tokens.current()
    rule = self.table[8][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(83, self.nonterminals[83]))
    tree.list = False
    if current == None:
      return tree
    if rule == 78:
      tree.astTransform = AstTransformNodeCreator('PPFile', {'nodes': 0})
      subtree = self.parse_pp_nodes_list()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen2(self):
    current = self.tokens.current()
    rule = self.table[9][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(84, self.nonterminals[84]))
    tree.list = 'slist'
    if current != None and (current.getId() in [59]):
      return tree
    if current == None:
      return tree
    if rule == 7:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_define_func_param()
      tree.add( subtree )
      subtree = self.parse__gen3()
      tree.add( subtree )
      return tree
    return tree
  def parse_include_line(self):
    current = self.tokens.current()
    rule = self.table[10][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(85, self.nonterminals[85]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 99:
      tree.astTransform = AstTransformNodeCreator('Include', {'file': 1})
      t = self.expect(25) # include
      tree.add(t)
      subtree = self.parse_include_type()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen3(self):
    current = self.tokens.current()
    rule = self.table[11][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(86, self.nonterminals[86]))
    tree.list = 'slist'
    if current != None and (current.getId() in [59]):
      return tree
    if current == None:
      return tree
    if rule == 9:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(35) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self.parse_define_func_param()
      tree.add( subtree )
      subtree = self.parse__gen3()
      tree.add( subtree )
      return tree
    return tree
  def parse_undef_line(self):
    current = self.tokens.current()
    rule = self.table[12][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(87, self.nonterminals[87]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 140:
      tree.astTransform = AstTransformNodeCreator('Undef', {'ident': 1})
      t = self.expect(36) # undef
      tree.add(t)
      t = self.expect(54) # identifier
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_defined_identifier(self):
    current = self.tokens.current()
    rule = self.table[13][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(88, self.nonterminals[88]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 130:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(54) # identifier
      tree.add(t)
      return tree
    elif rule == 139:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(55) # lparen
      tree.add(t)
      t = self.expect(54) # identifier
      tree.add(t)
      t = self.expect(59) # rparen
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen5(self):
    current = self.tokens.current()
    rule = self.table[14][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(89, self.nonterminals[89]))
    tree.list = 'slist'
    if current != None and (current.getId() in []):
      return tree
    if current == None:
      return tree
    if rule == 1:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__expr()
      tree.add( subtree )
      subtree = self.parse__gen6()
      tree.add( subtree )
      return tree
    return tree
  def parse_control_line(self):
    current = self.tokens.current()
    rule = self.table[15][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(90, self.nonterminals[90]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 16:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_pragma_line()
      tree.add( subtree )
      return tree
    elif rule == 39:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_define_line()
      tree.add( subtree )
      return tree
    elif rule == 46:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_warning_line()
      tree.add( subtree )
      return tree
    elif rule == 67:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_undef_line()
      tree.add( subtree )
      return tree
    elif rule == 68:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_include_line()
      tree.add( subtree )
      return tree
    elif rule == 77:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_line_line()
      tree.add( subtree )
      return tree
    elif rule == 135:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_error_line()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_elipsis_opt(self):
    current = self.tokens.current()
    rule = self.table[16][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(91, self.nonterminals[91]))
    tree.list = False
    if current != None and (current.getId() in []):
      return tree
    if current == None:
      return tree
    if rule == 18:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(35) # comma
      tree.add(t)
      t = self.expect(9) # elipsis
      tree.add(t)
      return tree
    return tree
  def parse_pp_nodes_list(self):
    current = self.tokens.current()
    rule = self.table[17][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(92, self.nonterminals[92]))
    tree.list = False
    if current != None and (current.getId() in [74, 12, 7, -1]):
      return tree
    if current == None:
      return tree
    if rule == 30:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen0()
      tree.add( subtree )
      return tree
    return tree
  def parse__gen6(self):
    current = self.tokens.current()
    rule = self.table[18][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(93, self.nonterminals[93]))
    tree.list = 'slist'
    if current != None and (current.getId() in []):
      return tree
    if current == None:
      return tree
    if rule == 95:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(35) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self.parse__expr()
      tree.add( subtree )
      subtree = self.parse__gen6()
      tree.add( subtree )
      return tree
    return tree
  def parse_line_line(self):
    current = self.tokens.current()
    rule = self.table[19][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(94, self.nonterminals[94]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 114:
      tree.astTransform = AstTransformNodeCreator('Line', {'tokens': 1})
      t = self.expect(49) # line
      tree.add(t)
      subtree = self.parse__gen4()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_pragma_line(self):
    current = self.tokens.current()
    rule = self.table[20][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(95, self.nonterminals[95]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 83:
      tree.astTransform = AstTransformNodeCreator('Pragma', {'tokens': 1})
      t = self.expect(10) # pragma
      tree.add(t)
      subtree = self.parse__gen4()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen0(self):
    current = self.tokens.current()
    rule = self.table[21][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(96, self.nonterminals[96]))
    tree.list = 'tlist'
    if current != None and (current.getId() in [12, 7, -1, 74]):
      return tree
    if current == None:
      return tree
    if rule == 28:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_pp_nodes()
      tree.add( subtree )
      t = self.expect(29) # separator
      tree.add(t)
      subtree = self.parse__gen0()
      tree.add( subtree )
      return tree
    return tree
  def parse_if_part(self):
    current = self.tokens.current()
    rule = self.table[22][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(97, self.nonterminals[97]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 82:
      tree.astTransform = AstTransformNodeCreator('IfNDef', {'nodes': 2, 'ident': 1})
      t = self.expect(2) # ifndef
      tree.add(t)
      t = self.expect(54) # identifier
      tree.add(t)
      subtree = self.parse_pp_nodes_list()
      tree.add( subtree )
      return tree
    elif rule == 88:
      tree.astTransform = AstTransformNodeCreator('IfDef', {'nodes': 2, 'ident': 1})
      t = self.expect(72) # ifdef
      tree.add(t)
      t = self.expect(54) # identifier
      tree.add(t)
      subtree = self.parse_pp_nodes_list()
      tree.add( subtree )
      return tree
    elif rule == 131:
      tree.astTransform = AstTransformNodeCreator('If', {'expr': 1, 'nodes': 2})
      t = self.expect(27) # if
      tree.add(t)
      subtree = self.parse__expr()
      tree.add( subtree )
      subtree = self.parse_pp_nodes_list()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_elseif_part(self):
    current = self.tokens.current()
    rule = self.table[23][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(98, self.nonterminals[98]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 29:
      tree.astTransform = AstTransformNodeCreator('ElseIf', {'expr': 1, 'nodes': 2})
      t = self.expect(7) # elif
      tree.add(t)
      subtree = self.parse__expr()
      tree.add( subtree )
      subtree = self.parse_pp_nodes_list()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_define_line(self):
    current = self.tokens.current()
    rule = self.table[24][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(99, self.nonterminals[99]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 61:
      tree.astTransform = AstTransformNodeCreator('DefineFunction', {'body': 5, 'ident': 1, 'params': 3})
      t = self.expect(22) # define_function
      tree.add(t)
      t = self.expect(54) # identifier
      tree.add(t)
      t = self.expect(55) # lparen
      tree.add(t)
      subtree = self.parse__gen2()
      tree.add( subtree )
      t = self.expect(59) # rparen
      tree.add(t)
      subtree = self.parse_replacement_list()
      tree.add( subtree )
      return tree
    elif rule == 81:
      tree.astTransform = AstTransformNodeCreator('Define', {'body': 2, 'ident': 1})
      t = self.expect(21) # define
      tree.add(t)
      t = self.expect(54) # identifier
      tree.add(t)
      subtree = self.parse_replacement_list()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_punctuator(self):
    current = self.tokens.current()
    rule = self.table[25][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(100, self.nonterminals[100]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 2:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(26) # arrow
      tree.add(t)
      return tree
    elif rule == 3:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(73) # sub
      tree.add(t)
      return tree
    elif rule == 8:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(0) # rshift
      tree.add(t)
      return tree
    elif rule == 10:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(1) # addeq
      tree.add(t)
      return tree
    elif rule == 11:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(28) # bitand
      tree.add(t)
      return tree
    elif rule == 17:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(3) # add
      tree.add(t)
      return tree
    elif rule == 20:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(24) # questionmark
      tree.add(t)
      return tree
    elif rule == 22:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(4) # mod
      tree.add(t)
      return tree
    elif rule == 24:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(32) # or
      tree.add(t)
      return tree
    elif rule == 25:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(6) # modeq
      tree.add(t)
      return tree
    elif rule == 32:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(33) # bitnot
      tree.add(t)
      return tree
    elif rule == 34:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(9) # elipsis
      tree.add(t)
      return tree
    elif rule == 35:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(38) # lbrace
      tree.add(t)
      return tree
    elif rule == 41:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(55) # lparen
      tree.add(t)
      return tree
    elif rule == 47:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(30) # pound
      tree.add(t)
      return tree
    elif rule == 50:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(40) # bitor
      tree.add(t)
      return tree
    elif rule == 51:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(19) # incr
      tree.add(t)
      return tree
    elif rule == 54:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(44) # bitxor
      tree.add(t)
      return tree
    elif rule == 56:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(43) # neq
      tree.add(t)
      return tree
    elif rule == 58:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(52) # lteq
      tree.add(t)
      return tree
    elif rule == 62:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(61) # lshifteq
      tree.add(t)
      return tree
    elif rule == 63:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(17) # ampersand
      tree.add(t)
      return tree
    elif rule == 70:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(45) # lsquare
      tree.add(t)
      return tree
    elif rule == 74:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(8) # mul
      tree.add(t)
      return tree
    elif rule == 75:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(48) # bitoreq
      tree.add(t)
      return tree
    elif rule == 76:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(70) # lshift
      tree.add(t)
      return tree
    elif rule == 79:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(50) # rsquare
      tree.add(t)
      return tree
    elif rule == 84:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(11) # muleq
      tree.add(t)
      return tree
    elif rule == 89:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(53) # bitxoreq
      tree.add(t)
      return tree
    elif rule == 91:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(18) # colon
      tree.add(t)
      return tree
    elif rule == 93:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(39) # and
      tree.add(t)
      return tree
    elif rule == 106:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(57) # bitandeq
      tree.add(t)
      return tree
    elif rule == 110:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(20) # assign
      tree.add(t)
      return tree
    elif rule == 111:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(41) # gteq
      tree.add(t)
      return tree
    elif rule == 113:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(59) # rparen
      tree.add(t)
      return tree
    elif rule == 115:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(67) # lt
      tree.add(t)
      return tree
    elif rule == 116:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(5) # poundpound
      tree.add(t)
      return tree
    elif rule == 117:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(71) # subeq
      tree.add(t)
      return tree
    elif rule == 119:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(23) # decr
      tree.add(t)
      return tree
    elif rule == 121:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(13) # div
      tree.add(t)
      return tree
    elif rule == 122:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(47) # eq
      tree.add(t)
      return tree
    elif rule == 124:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(42) # rbrace
      tree.add(t)
      return tree
    elif rule == 125:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(64) # exclamation_point
      tree.add(t)
      return tree
    elif rule == 126:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(65) # gt
      tree.add(t)
      return tree
    elif rule == 128:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(66) # rshifteq
      tree.add(t)
      return tree
    elif rule == 129:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(35) # comma
      tree.add(t)
      return tree
    elif rule == 132:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(15) # diveq
      tree.add(t)
      return tree
    elif rule == 133:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(31) # dot
      tree.add(t)
      return tree
    elif rule == 136:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(16) # semi
      tree.add(t)
      return tree
    elif rule == 137:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(69) # tilde
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_if_section(self):
    current = self.tokens.current()
    rule = self.table[26][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(101, self.nonterminals[101]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 13:
      tree.astTransform = AstTransformNodeCreator('IfSection', {'elif': 1, 'else': 2, 'if': 0})
      subtree = self.parse_if_part()
      tree.add( subtree )
      subtree = self.parse__gen1()
      tree.add( subtree )
      subtree = self.parse_else_part()
      tree.add( subtree )
      t = self.expect(74) # endif
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen1(self):
    current = self.tokens.current()
    rule = self.table[27][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(102, self.nonterminals[102]))
    tree.list = 'nlist'
    if current != None and (current.getId() in [12]):
      return tree
    if current == None:
      return tree
    if rule == 37:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_elseif_part()
      tree.add( subtree )
      subtree = self.parse__gen1()
      tree.add( subtree )
      return tree
    return tree
  def parse_else_part(self):
    current = self.tokens.current()
    rule = self.table[28][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(103, self.nonterminals[103]))
    tree.list = False
    if current != None and (current.getId() in [74]):
      return tree
    if current == None:
      return tree
    if rule == 42:
      tree.astTransform = AstTransformNodeCreator('Else', {'nodes': 1})
      t = self.expect(12) # else
      tree.add(t)
      subtree = self.parse_pp_nodes_list()
      tree.add( subtree )
      return tree
    return tree
  def parse_include_type(self):
    current = self.tokens.current()
    rule = self.table[29][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(104, self.nonterminals[104]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 4:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(54) # identifier
      tree.add(t)
      return tree
    elif rule == 108:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(34) # header_global
      tree.add(t)
      return tree
    elif rule == 118:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(51) # header_local
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_replacement_list(self):
    current = self.tokens.current()
    rule = self.table[30][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(105, self.nonterminals[105]))
    tree.list = False
    if current != None and (current.getId() in [29]):
      return tree
    if current == None:
      return tree
    if rule == 5:
      tree.astTransform = AstTransformNodeCreator('ReplacementList', {'tokens': 0})
      subtree = self.parse__gen4()
      tree.add( subtree )
      return tree
    return tree
  def parse__expr( self, rbp = 0):
    name = '_expr'
    if name not in self.expressionParsers:
      self.expressionParsers[name] = pp_ExpressionParser__expr(self)
    return self.expressionParsers[name].parse(rbp)
