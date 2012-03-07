import sys, inspect
from cast.ParserCommon import *
def whoami():
  return inspect.stack()[1][3]
def whosdaddy():
  return inspect.stack()[2][3]
def parse( iterator, entry ):
  p = c_Parser()
  return p.parse(iterator, entry)
class c_ExpressionParser__expr:
  def __init__(self, parent):
    self.__dict__.update(locals())
    self.infixBp = {
      0: 1000,
      2: 5000,
      8: 15000,
      11: 12000,
      12: 15000,
      18: 11000,
      19: 15000,
      21: 1000,
      27: 16000,
      30: 1000,
      31: 1000,
      35: 4000,
      39: 2000,
      40: 1000,
      43: 7000,
      45: 8000,
      46: 1000,
      51: 1000,
      52: 12000,
      55: 8000,
      58: 3000,
      59: 1000,
      63: 15000,
      65: 10000,
      66: 15000,
      69: 15000,
      74: 9000,
      75: 6000,
      76: 1000,
      81: 9000,
      84: 1000,
      88: 9000,
      94: 14000,
      101: 10000,
      103: 9000,
      106: 1000,
      107: 11000,
      111: 12000,
    }
    self.prefixBp = {
      2: 13000,
      3: 13000,
      5: 13000,
      12: 13000,
      18: 13000,
      19: 13000,
      52: 13000,
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
    tree = ParseTree( NonTerminal(119, '_expr') )
    current = self.getCurrentToken()
    if not current:
      return tree
    elif current.getId() in [108]:
      tree.astTransform = AstTransformNodeCreator('TypeInitializion', {'type': 1, 'initializer': 4})
      tree.nudMorphemeCount = 3
      tree.add( self.expect(108) )
      tree.add( self.parent.parse_type_name() )
      tree.add( self.expect(1) )
    elif current.getId() in [63]:
      tree.astTransform = AstTransformSubstitution(2)
      tree.nudMorphemeCount = 3
      tree.add( self.expect(63) )
      tree.add( self.parent.parse__expr() )
      tree.add( self.expect(1) )
    elif current.getId() in [52]:
      tree.astTransform = AstTransformNodeCreator('Dereference', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(52) )
      tree.add( self.parent.parse__expr( self.getPrefixBp(52) ) )
      tree.isPrefix = True
    elif current.getId() in [118]:
      tree.astTransform = AstTransformNodeCreator('SizeOf', {'var': 1})
      tree.nudMorphemeCount = 1
      tree.add( self.expect(118) )
    elif current.getId() in [12]:
      tree.astTransform = AstTransformNodeCreator('PreDecr', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(12) )
      tree.add( self.parent.parse__expr( self.getPrefixBp(12) ) )
      tree.isPrefix = True
    elif current.getId() in [19]:
      tree.astTransform = AstTransformNodeCreator('PreIncr', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(19) )
      tree.add( self.parent.parse__expr( self.getPrefixBp(19) ) )
      tree.isPrefix = True
    elif current.getId() in [80]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      tree.add( self.expect(80) )
    elif current.getId() in [2]:
      tree.astTransform = AstTransformNodeCreator('AddressOf', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(2) )
      tree.add( self.parent.parse__expr( self.getPrefixBp(2) ) )
      tree.isPrefix = True
    elif current.getId() in [80]:
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      tree.nudMorphemeCount = 1
      tree.add( self.expect(80) )
    elif current.getId() in [44]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      tree.add( self.expect(44) )
    elif current.getId() in [24, 117, 15, 10, 97, 99]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      tree.add( self.parent.parse_constant() )
    elif current.getId() in [80]:
      tree.astTransform = AstTransformNodeCreator('ArrayIndex', {'params': 2, 'name': 0})
      tree.nudMorphemeCount = 1
      tree.add( self.expect(80) )
    return tree
  def led(self, left):
    tree = ParseTree( NonTerminal(119, '_expr') )
    current = self.getCurrentToken()
    if current.getId() == 76: # 'addeq'
      tree.astTransform = AstTransformNodeCreator('AddAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(76) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(76) - modifier ) )
      return tree
    if current.getId() == 11: # 'mod'
      tree.astTransform = AstTransformNodeCreator('Mod', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(11) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(11) - modifier ) )
      return tree
    if current.getId() == 94: # 'lbrace'
      tree.astTransform = AstTransformNodeCreator('TypeInitializion', {'type': 1, 'initializer': 4})
      tree.add(left)
      tree.add( self.expect(94) )
      tree.add( self.parent.parse__gen12() )
      tree.add( self.parent.parse_trailing_comma_opt() )
      tree.add( self.expect(100) )
      return tree
    if current.getId() == 75: # 'bitxor'
      tree.astTransform = AstTransformNodeCreator('BitXOR', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(75) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(75) - modifier ) )
      return tree
    if current.getId() == 103: # 'gt'
      tree.astTransform = AstTransformNodeCreator('GreaterThan', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(103) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(103) - modifier ) )
      return tree
    if current.getId() == 40: # 'bitxoreq'
      tree.astTransform = AstTransformNodeCreator('XORAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(40) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(40) - modifier ) )
      return tree
    if current.getId() == 8: # 'arrow'
      tree.astTransform = AstTransformNodeCreator('DerefMemberSelect', {'member': 2, 'object': 0})
      tree.isExprNud = True 
      tree.add(left)
      tree.add( self.expect(8) )
      modifier = 0
      tree.add( self.parent.parse__expr( self.getInfixBp(8) - modifier ) )
      return tree
    if current.getId() == 82: # 'sizeof_separator'
      tree.astTransform = AstTransformNodeCreator('SizeOf', {'var': 1})
      tree.add(left)
      tree.add( self.expect(82) )
      tree.add( self.parent.parse_sizeof_body() )
      return tree
    if current.getId() == 88: # 'lt'
      tree.astTransform = AstTransformNodeCreator('LessThan', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(88) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(88) - modifier ) )
      return tree
    if current.getId() == 21: # 'assign'
      tree.astTransform = AstTransformNodeCreator('Assign', {'var': 0, 'value': 2})
      tree.add(left)
      tree.add( self.expect(21) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(21) - modifier ) )
      return tree
    if current.getId() == 39: # 'questionmark'
      tree.astTransform = AstTransformNodeCreator('TernaryOperator', {'true': 2, 'false': 4, 'cond': 0})
      tree.isExprNud = True 
      tree.add(left)
      tree.add( self.expect(39) )
      modifier = 1
      tree.add( self.parent.parse__expr( self.getInfixBp(39) - modifier ) )
      tree.add( self.expect(28) )
      modifier = 1
      tree.add( self.parent.parse__expr( self.getInfixBp(39) - modifier ) )
      return tree
    if current.getId() == 30: # 'subeq'
      tree.astTransform = AstTransformNodeCreator('SubtractAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(30) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(30) - modifier ) )
      return tree
    if current.getId() == 2: # 'bitand'
      tree.astTransform = AstTransformNodeCreator('BitAND', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(2) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(2) - modifier ) )
      return tree
    if current.getId() == 84: # 'modeq'
      tree.astTransform = AstTransformNodeCreator('ModAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(84) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(84) - modifier ) )
      return tree
    if current.getId() == 101: # 'lshift'
      tree.astTransform = AstTransformNodeCreator('LeftShift', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(101) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(101) - modifier ) )
      return tree
    if current.getId() == 31: # 'bitoreq'
      tree.astTransform = AstTransformNodeCreator('ORAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(31) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(31) - modifier ) )
      return tree
    if current.getId() == 106: # 'muleq'
      tree.astTransform = AstTransformNodeCreator('MultiplyAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(106) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(106) - modifier ) )
      return tree
    if current.getId() == 111: # 'div'
      tree.astTransform = AstTransformNodeCreator('Div', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(111) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(111) - modifier ) )
      return tree
    if current.getId() == 27: # 'comma'
      tree.astTransform = AstTransformNodeCreator('Comma', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(27) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(27) - modifier ) )
      return tree
    if current.getId() == 52: # 'asterisk'
      tree.astTransform = AstTransformNodeCreator('Mul', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(52) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(52) - modifier ) )
      return tree
    if current.getId() == 43: # 'bitor'
      tree.astTransform = AstTransformNodeCreator('BitOR', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(43) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(43) - modifier ) )
      return tree
    if current.getId() == 0: # 'diveq'
      tree.astTransform = AstTransformNodeCreator('DivideAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(0) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(0) - modifier ) )
      return tree
    if current.getId() == 107: # 'add'
      tree.astTransform = AstTransformNodeCreator('Add', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(107) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(107) - modifier ) )
      return tree
    if current.getId() == 19: # 'incr'
      tree.astTransform = AstTransformNodeCreator('PostIncr', {'var': 0})
      tree.isExprNud = True 
      tree.add(left)
      tree.add( self.expect(19) )
      return tree
    if current.getId() == 18: # 'sub'
      tree.astTransform = AstTransformNodeCreator('Sub', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(18) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(18) - modifier ) )
      return tree
    if current.getId() == 74: # 'lteq'
      tree.astTransform = AstTransformNodeCreator('LessThanEq', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(74) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(74) - modifier ) )
      return tree
    if current.getId() == 69: # 'dot'
      tree.astTransform = AstTransformNodeCreator('MemberSelect', {'member': 2, 'object': 0})
      tree.isExprNud = True 
      tree.add(left)
      tree.add( self.expect(69) )
      modifier = 0
      tree.add( self.parent.parse__expr( self.getInfixBp(69) - modifier ) )
      return tree
    if current.getId() == 65: # 'rshift'
      tree.astTransform = AstTransformNodeCreator('RightShift', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(65) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(65) - modifier ) )
      return tree
    if current.getId() == 12: # 'decr'
      tree.astTransform = AstTransformNodeCreator('PostDecr', {'var': 0})
      tree.isExprNud = True 
      tree.add(left)
      tree.add( self.expect(12) )
      return tree
    if current.getId() == 45: # 'eq'
      tree.astTransform = AstTransformNodeCreator('Equals', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(45) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(45) - modifier ) )
      return tree
    if current.getId() == 63: # 'lparen'
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      tree.add(left)
      tree.add( self.expect(63) )
      tree.add( self.parent.parse__gen44() )
      tree.add( self.expect(1) )
      return tree
    if current.getId() == 81: # 'gteq'
      tree.astTransform = AstTransformNodeCreator('GreaterThanEq', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(81) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(81) - modifier ) )
      return tree
    if current.getId() == 51: # 'lshifteq'
      tree.astTransform = AstTransformNodeCreator('LeftShiftAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(51) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(51) - modifier ) )
      return tree
    if current.getId() == 46: # 'bitandeq'
      tree.astTransform = AstTransformNodeCreator('ANDAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(46) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(46) - modifier ) )
      return tree
    if current.getId() == 66: # 'lsquare'
      tree.astTransform = AstTransformNodeCreator('ArrayIndex', {'params': 2, 'name': 0})
      tree.add(left)
      tree.add( self.expect(66) )
      tree.add( self.parent.parse__gen44() )
      tree.add( self.expect(77) )
      return tree
    if current.getId() == 59: # 'rshifteq'
      tree.astTransform = AstTransformNodeCreator('RightShiftAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(59) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(59) - modifier ) )
      return tree
    return tree
class c_ExpressionParser__expr_sans_comma:
  def __init__(self, parent):
    self.__dict__.update(locals())
    self.infixBp = {
      0: 1000,
      2: 5000,
      8: 15000,
      11: 12000,
      12: 15000,
      18: 11000,
      19: 15000,
      21: 1000,
      30: 1000,
      31: 1000,
      35: 4000,
      39: 2000,
      40: 1000,
      43: 7000,
      45: 8000,
      46: 1000,
      51: 1000,
      52: 12000,
      55: 8000,
      58: 3000,
      59: 1000,
      63: 15000,
      65: 10000,
      66: 15000,
      69: 15000,
      74: 9000,
      75: 6000,
      76: 1000,
      81: 9000,
      84: 1000,
      88: 9000,
      94: 14000,
      101: 10000,
      103: 9000,
      106: 1000,
      107: 11000,
      111: 12000,
    }
    self.prefixBp = {
      2: 13000,
      3: 13000,
      5: 13000,
      12: 13000,
      18: 13000,
      19: 13000,
      52: 13000,
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
    tree = ParseTree( NonTerminal(185, '_expr_sans_comma') )
    current = self.getCurrentToken()
    if not current:
      return tree
    if current.getId() in [2]:
      tree.astTransform = AstTransformNodeCreator('AddressOf', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(2) )
      tree.add( self.parent.parse__expr_sans_comma( self.getPrefixBp(2) ) )
      tree.isPrefix = True
    elif current.getId() in [44]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      tree.add( self.expect(44) )
    elif current.getId() in [108]:
      tree.astTransform = AstTransformNodeCreator('TypeInitializion', {'type': 1, 'initializer': 4})
      tree.nudMorphemeCount = 3
      tree.add( self.expect(108) )
      tree.add( self.parent.parse_type_name() )
      tree.add( self.expect(1) )
    elif current.getId() in [63]:
      tree.astTransform = AstTransformSubstitution(2)
      tree.nudMorphemeCount = 3
      tree.add( self.expect(63) )
      tree.add( self.parent.parse__expr_sans_comma() )
      tree.add( self.expect(1) )
    elif current.getId() in [52]:
      tree.astTransform = AstTransformNodeCreator('Dereference', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(52) )
      tree.add( self.parent.parse__expr_sans_comma( self.getPrefixBp(52) ) )
      tree.isPrefix = True
    elif current.getId() in [80]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      tree.add( self.expect(80) )
    elif current.getId() in [118]:
      tree.astTransform = AstTransformNodeCreator('SizeOf', {'var': 1})
      tree.nudMorphemeCount = 1
      tree.add( self.expect(118) )
    elif current.getId() in [12]:
      tree.astTransform = AstTransformNodeCreator('PreDecr', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(12) )
      tree.add( self.parent.parse__expr_sans_comma( self.getPrefixBp(12) ) )
      tree.isPrefix = True
    elif current.getId() in [19]:
      tree.astTransform = AstTransformNodeCreator('PreIncr', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(19) )
      tree.add( self.parent.parse__expr_sans_comma( self.getPrefixBp(19) ) )
      tree.isPrefix = True
    elif current.getId() in [80]:
      tree.astTransform = AstTransformNodeCreator('ArrayIndex', {'params': 2, 'name': 0})
      tree.nudMorphemeCount = 1
      tree.add( self.expect(80) )
    elif current.getId() in [24, 117, 15, 10, 97, 99]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      tree.add( self.parent.parse_constant() )
    elif current.getId() in [80]:
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      tree.nudMorphemeCount = 1
      tree.add( self.expect(80) )
    return tree
  def led(self, left):
    tree = ParseTree( NonTerminal(185, '_expr_sans_comma') )
    current = self.getCurrentToken()
    if current.getId() == 103: # 'gt'
      tree.astTransform = AstTransformNodeCreator('GreaterThan', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(103) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(103) - modifier ) )
      return tree
    if current.getId() == 19: # 'incr'
      tree.astTransform = AstTransformNodeCreator('PostIncr', {'var': 0})
      tree.isExprNud = True 
      tree.add(left)
      tree.add( self.expect(19) )
      return tree
    if current.getId() == 40: # 'bitxoreq'
      tree.astTransform = AstTransformNodeCreator('XORAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(40) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(40) - modifier ) )
      return tree
    if current.getId() == 39: # 'questionmark'
      tree.astTransform = AstTransformNodeCreator('TernaryOperator', {'true': 2, 'false': 4, 'cond': 0})
      tree.isExprNud = True 
      tree.add(left)
      tree.add( self.expect(39) )
      modifier = 1
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(39) - modifier ) )
      tree.add( self.expect(28) )
      modifier = 1
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(39) - modifier ) )
      return tree
    if current.getId() == 21: # 'assign'
      tree.astTransform = AstTransformNodeCreator('Assign', {'var': 0, 'value': 2})
      tree.add(left)
      tree.add( self.expect(21) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(21) - modifier ) )
      return tree
    if current.getId() == 30: # 'subeq'
      tree.astTransform = AstTransformNodeCreator('SubtractAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(30) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(30) - modifier ) )
      return tree
    if current.getId() == 107: # 'add'
      tree.astTransform = AstTransformNodeCreator('Add', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(107) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(107) - modifier ) )
      return tree
    if current.getId() == 75: # 'bitxor'
      tree.astTransform = AstTransformNodeCreator('BitXOR', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(75) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(75) - modifier ) )
      return tree
    if current.getId() == 88: # 'lt'
      tree.astTransform = AstTransformNodeCreator('LessThan', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(88) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(88) - modifier ) )
      return tree
    if current.getId() == 94: # 'lbrace'
      tree.astTransform = AstTransformNodeCreator('TypeInitializion', {'type': 1, 'initializer': 4})
      tree.add(left)
      tree.add( self.expect(94) )
      tree.add( self.parent.parse__gen12() )
      tree.add( self.parent.parse_trailing_comma_opt() )
      tree.add( self.expect(100) )
      return tree
    if current.getId() == 51: # 'lshifteq'
      tree.astTransform = AstTransformNodeCreator('LeftShiftAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(51) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(51) - modifier ) )
      return tree
    if current.getId() == 101: # 'lshift'
      tree.astTransform = AstTransformNodeCreator('LeftShift', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(101) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(101) - modifier ) )
      return tree
    if current.getId() == 11: # 'mod'
      tree.astTransform = AstTransformNodeCreator('Mod', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(11) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(11) - modifier ) )
      return tree
    if current.getId() == 0: # 'diveq'
      tree.astTransform = AstTransformNodeCreator('DivideAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(0) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(0) - modifier ) )
      return tree
    if current.getId() == 18: # 'sub'
      tree.astTransform = AstTransformNodeCreator('Sub', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(18) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(18) - modifier ) )
      return tree
    if current.getId() == 2: # 'bitand'
      tree.astTransform = AstTransformNodeCreator('BitAND', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(2) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(2) - modifier ) )
      return tree
    if current.getId() == 82: # 'sizeof_separator'
      tree.astTransform = AstTransformNodeCreator('SizeOf', {'var': 1})
      tree.add(left)
      tree.add( self.expect(82) )
      tree.add( self.parent.parse_sizeof_body() )
      return tree
    if current.getId() == 8: # 'arrow'
      tree.astTransform = AstTransformNodeCreator('DerefMemberSelect', {'member': 2, 'object': 0})
      tree.isExprNud = True 
      tree.add(left)
      tree.add( self.expect(8) )
      modifier = 0
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(8) - modifier ) )
      return tree
    if current.getId() == 106: # 'muleq'
      tree.astTransform = AstTransformNodeCreator('MultiplyAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(106) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(106) - modifier ) )
      return tree
    if current.getId() == 74: # 'lteq'
      tree.astTransform = AstTransformNodeCreator('LessThanEq', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(74) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(74) - modifier ) )
      return tree
    if current.getId() == 12: # 'decr'
      tree.astTransform = AstTransformNodeCreator('PostDecr', {'var': 0})
      tree.isExprNud = True 
      tree.add(left)
      tree.add( self.expect(12) )
      return tree
    if current.getId() == 81: # 'gteq'
      tree.astTransform = AstTransformNodeCreator('GreaterThanEq', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(81) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(81) - modifier ) )
      return tree
    if current.getId() == 66: # 'lsquare'
      tree.astTransform = AstTransformNodeCreator('ArrayIndex', {'params': 2, 'name': 0})
      tree.add(left)
      tree.add( self.expect(66) )
      tree.add( self.parent.parse__gen44() )
      tree.add( self.expect(77) )
      return tree
    if current.getId() == 31: # 'bitoreq'
      tree.astTransform = AstTransformNodeCreator('ORAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(31) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(31) - modifier ) )
      return tree
    if current.getId() == 59: # 'rshifteq'
      tree.astTransform = AstTransformNodeCreator('RightShiftAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(59) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(59) - modifier ) )
      return tree
    if current.getId() == 52: # 'asterisk'
      tree.astTransform = AstTransformNodeCreator('Mul', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(52) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(52) - modifier ) )
      return tree
    if current.getId() == 84: # 'modeq'
      tree.astTransform = AstTransformNodeCreator('ModAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(84) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(84) - modifier ) )
      return tree
    if current.getId() == 43: # 'bitor'
      tree.astTransform = AstTransformNodeCreator('BitOR', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(43) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(43) - modifier ) )
      return tree
    if current.getId() == 45: # 'eq'
      tree.astTransform = AstTransformNodeCreator('Equals', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(45) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(45) - modifier ) )
      return tree
    if current.getId() == 69: # 'dot'
      tree.astTransform = AstTransformNodeCreator('MemberSelect', {'member': 2, 'object': 0})
      tree.isExprNud = True 
      tree.add(left)
      tree.add( self.expect(69) )
      modifier = 0
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(69) - modifier ) )
      return tree
    if current.getId() == 63: # 'lparen'
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      tree.add(left)
      tree.add( self.expect(63) )
      tree.add( self.parent.parse__gen44() )
      tree.add( self.expect(1) )
      return tree
    if current.getId() == 76: # 'addeq'
      tree.astTransform = AstTransformNodeCreator('AddAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(76) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(76) - modifier ) )
      return tree
    if current.getId() == 46: # 'bitandeq'
      tree.astTransform = AstTransformNodeCreator('ANDAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(46) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(46) - modifier ) )
      return tree
    if current.getId() == 65: # 'rshift'
      tree.astTransform = AstTransformNodeCreator('RightShift', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(65) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(65) - modifier ) )
      return tree
    if current.getId() == 111: # 'div'
      tree.astTransform = AstTransformNodeCreator('Div', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(111) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(111) - modifier ) )
      return tree
    return tree
class c_ExpressionParser__direct_declarator:
  def __init__(self, parent):
    self.__dict__.update(locals())
    self.infixBp = {
      63: 1000,
      66: 1000,
    }
    self.prefixBp = {
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
    tree = ParseTree( NonTerminal(247, '_direct_declarator') )
    current = self.getCurrentToken()
    if not current:
      return tree
    elif current.getId() in [80]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      tree.add( self.expect(80) )
    elif current.getId() in [63]:
      tree.astTransform = AstTransformSubstitution(1)
      tree.nudMorphemeCount = 3
      tree.add( self.expect(63) )
      tree.add( self.parent.parse_declarator() )
      tree.add( self.expect(1) )
    return tree
  def led(self, left):
    tree = ParseTree( NonTerminal(247, '_direct_declarator') )
    current = self.getCurrentToken()
    if current.getId() == 66: # 'lsquare'
      tree.astTransform = AstTransformNodeCreator('Array', {'name': 0, 'size': 2})
      tree.isExprNud = True 
      tree.add(left)
      tree.add( self.expect(66) )
      tree.add( self.parent.parse_direct_declarator_expr() )
      tree.add( self.expect(77) )
      return tree
    if current.getId() == 63: # 'lparen'
      tree.astTransform = AstTransformNodeCreator('FunctionSignature', {'params': 2, 'declarator': 0})
      tree.isExprNud = True 
      tree.add(left)
      tree.add( self.expect(63) )
      tree.add( self.parent.parse_direct_declarator_parameter_list() )
      tree.add( self.expect(1) )
      return tree
    return tree
class c_ExpressionParser__direct_abstract_declarator:
  def __init__(self, parent):
    self.__dict__.update(locals())
    self.infixBp = {
      63: 1000,
      66: 1000,
    }
    self.prefixBp = {
      63: 2000,
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
    tree = ParseTree( NonTerminal(228, '_direct_abstract_declarator') )
    current = self.getCurrentToken()
    if not current:
      return tree
    elif current.getId() in [63]:
      tree.astTransform = AstTransformSubstitution(1)
      tree.nudMorphemeCount = 3
      tree.add( self.expect(63) )
      tree.add( self.parent.parse_abstract_declarator() )
      tree.add( self.expect(1) )
    return tree
  def led(self, left):
    tree = ParseTree( NonTerminal(228, '_direct_abstract_declarator') )
    current = self.getCurrentToken()
    if current.getId() == 63: # 'lparen'
      tree.astTransform = AstTransformNodeCreator('AbstractFunction', {'object': '$', 'params': 2})
      tree.isExprNud = True 
      tree.add(left)
      tree.add( self.expect(63) )
      tree.add( self.parent.parse__gen46() )
      tree.add( self.expect(1) )
      return tree
    if current.getId() == 66: # 'lsquare'
      tree.astTransform = AstTransformNodeCreator('AbstractArray', {'object': '$', 'size': 2})
      tree.isExprNud = True 
      tree.add(left)
      tree.add( self.expect(66) )
      tree.add( self.parent.parse_direct_abstract_declarator_expr() )
      tree.add( self.expect(77) )
      return tree
    return tree
class c_Parser:
  # Quark - finite string set maps one string to exactly one int, and vice versa
  terminals = {
    0: 'diveq',
    1: 'rparen',
    2: 'bitand',
    3: 'not',
    4: 'register',
    5: 'bitnot',
    6: 'pound',
    7: 'defined_separator',
    8: 'arrow',
    9: 'if',
    10: 'integer_constant',
    11: 'mod',
    12: 'decr',
    13: 'pp_number',
    14: 'elipsis',
    15: 'floating_constant',
    16: 'continue',
    17: 'comma_va_args',
    18: 'sub',
    19: 'incr',
    20: 'poundpound',
    21: 'assign',
    22: 'union',
    23: 'else_if',
    24: 'enumeration_constant',
    25: '_direct_abstract_declarator',
    26: 'semi',
    27: 'comma',
    28: 'colon',
    29: 'label_hint',
    30: 'subeq',
    31: 'bitoreq',
    32: 'ampersand',
    33: '_expr_sans_comma',
    34: 'inline',
    35: 'and',
    36: 'tilde',
    37: 'enum',
    38: 'struct',
    39: 'questionmark',
    40: 'bitxoreq',
    41: 'long',
    42: 'variable_length_array',
    43: 'bitor',
    44: 'string_literal',
    45: 'eq',
    46: 'bitandeq',
    47: 'restrict',
    48: 'complex',
    49: 'int',
    50: 'const',
    51: 'lshifteq',
    52: 'asterisk',
    53: 'short',
    54: 'typedef_identifier',
    55: 'neq',
    56: 'break',
    57: 'typedef',
    58: 'or',
    59: 'rshifteq',
    60: 'signed',
    61: 'for',
    62: 'float',
    63: 'lparen',
    64: 'abstract_parameter_hint',
    65: 'rshift',
    66: 'lsquare',
    67: 'endif',
    68: 'else',
    69: 'dot',
    70: 'default',
    71: 'function_definition_hint',
    72: 'double',
    73: '_expr',
    74: 'lteq',
    75: 'bitxor',
    76: 'addeq',
    77: 'rsquare',
    78: 'bool',
    79: 'unsigned',
    80: 'identifier',
    81: 'gteq',
    82: 'sizeof_separator',
    83: 'volatile',
    84: 'modeq',
    85: 'while',
    86: 'defined',
    87: 'goto',
    88: 'lt',
    89: '_direct_declarator',
    90: 'static',
    91: 'imaginary',
    92: 'do',
    93: 'declarator_hint',
    94: 'lbrace',
    95: 'named_parameter_hint',
    96: 'void',
    97: 'hexadecimal_floating_constant',
    98: 'extern',
    99: 'decimal_floating_constant',
    100: 'rbrace',
    101: 'lshift',
    102: 'external_declaration_hint',
    103: 'gt',
    104: 'trailing_comma',
    105: 'universal_character_name',
    106: 'muleq',
    107: 'add',
    108: 'lparen_cast',
    109: 'exclamation_point',
    110: 'return',
    111: 'div',
    112: 'case',
    113: 'switch',
    114: 'char',
    115: 'auto',
    116: 'function_prototype_hint',
    117: 'character_constant',
    118: 'sizeof',
    'diveq': 0,
    'rparen': 1,
    'bitand': 2,
    'not': 3,
    'register': 4,
    'bitnot': 5,
    'pound': 6,
    'defined_separator': 7,
    'arrow': 8,
    'if': 9,
    'integer_constant': 10,
    'mod': 11,
    'decr': 12,
    'pp_number': 13,
    'elipsis': 14,
    'floating_constant': 15,
    'continue': 16,
    'comma_va_args': 17,
    'sub': 18,
    'incr': 19,
    'poundpound': 20,
    'assign': 21,
    'union': 22,
    'else_if': 23,
    'enumeration_constant': 24,
    '_direct_abstract_declarator': 25,
    'semi': 26,
    'comma': 27,
    'colon': 28,
    'label_hint': 29,
    'subeq': 30,
    'bitoreq': 31,
    'ampersand': 32,
    '_expr_sans_comma': 33,
    'inline': 34,
    'and': 35,
    'tilde': 36,
    'enum': 37,
    'struct': 38,
    'questionmark': 39,
    'bitxoreq': 40,
    'long': 41,
    'variable_length_array': 42,
    'bitor': 43,
    'string_literal': 44,
    'eq': 45,
    'bitandeq': 46,
    'restrict': 47,
    'complex': 48,
    'int': 49,
    'const': 50,
    'lshifteq': 51,
    'asterisk': 52,
    'short': 53,
    'typedef_identifier': 54,
    'neq': 55,
    'break': 56,
    'typedef': 57,
    'or': 58,
    'rshifteq': 59,
    'signed': 60,
    'for': 61,
    'float': 62,
    'lparen': 63,
    'abstract_parameter_hint': 64,
    'rshift': 65,
    'lsquare': 66,
    'endif': 67,
    'else': 68,
    'dot': 69,
    'default': 70,
    'function_definition_hint': 71,
    'double': 72,
    '_expr': 73,
    'lteq': 74,
    'bitxor': 75,
    'addeq': 76,
    'rsquare': 77,
    'bool': 78,
    'unsigned': 79,
    'identifier': 80,
    'gteq': 81,
    'sizeof_separator': 82,
    'volatile': 83,
    'modeq': 84,
    'while': 85,
    'defined': 86,
    'goto': 87,
    'lt': 88,
    '_direct_declarator': 89,
    'static': 90,
    'imaginary': 91,
    'do': 92,
    'declarator_hint': 93,
    'lbrace': 94,
    'named_parameter_hint': 95,
    'void': 96,
    'hexadecimal_floating_constant': 97,
    'extern': 98,
    'decimal_floating_constant': 99,
    'rbrace': 100,
    'lshift': 101,
    'external_declaration_hint': 102,
    'gt': 103,
    'trailing_comma': 104,
    'universal_character_name': 105,
    'muleq': 106,
    'add': 107,
    'lparen_cast': 108,
    'exclamation_point': 109,
    'return': 110,
    'div': 111,
    'case': 112,
    'switch': 113,
    'char': 114,
    'auto': 115,
    'function_prototype_hint': 116,
    'character_constant': 117,
    'sizeof': 118,
  }
  # Quark - finite string set maps one string to exactly one int, and vice versa
  nonterminals = {
    119: '_expr',
    120: 'struct_declarator_body',
    121: 'direct_declarator_size',
    122: '_gen7',
    123: '_gen44',
    124: '_gen21',
    125: '_gen45',
    126: 'struct_or_union_sub',
    127: 'type_name',
    128: 'for_init',
    129: 'direct_declarator_modifier',
    130: 'keyword',
    131: 'block_item',
    132: 'external_declaration',
    133: 'init_declarator_list',
    134: '_gen8',
    135: 'struct_or_union_body',
    136: 'sizeof_body',
    137: '_gen16',
    138: '_gen28',
    139: 'constant',
    140: '_gen0',
    141: 'enum_specifier_sub',
    142: 'storage_class_specifier',
    143: 'typedef_name',
    144: '_gen18',
    145: 'identifier',
    146: 'enum_specifier_body',
    147: '_gen11',
    148: 'type_specifier',
    149: 'struct_declaration',
    150: 'block_item_list',
    151: '_gen17',
    152: 'declaration',
    153: 'type_qualifier',
    154: 'misc',
    155: 'struct_specifier',
    156: 'function_specifier',
    157: '_gen39',
    158: 'else_if_statement_list',
    159: 'type_qualifier_list_opt',
    160: 'specifier_qualifier',
    161: '_gen9',
    162: '_gen24',
    163: 'translation_unit',
    164: 'else_statement',
    165: '_gen42',
    166: '_gen22',
    167: 'struct_declarator',
    168: '_gen19',
    169: '_gen20',
    170: '_gen10',
    171: 'enumeration_constant',
    172: '_gen15',
    173: 'punctuator',
    174: '_gen43',
    175: '_gen27',
    176: 'external_declarator',
    177: 'else_if_statement',
    178: 'init_declarator',
    179: 'parameter_type_list',
    180: 'initializer',
    181: 'designation',
    182: 'initializer_list_item',
    183: 'external_declaration_sub',
    184: 'declarator_initializer',
    185: '_expr_sans_comma',
    186: 'external_function',
    187: 'expression_opt',
    188: 'direct_abstract_declarator_expr',
    189: 'enumerator_assignment',
    190: '_gen12',
    191: '_gen13',
    192: 'external_declaration_sub_sub',
    193: 'named_parameter_declaration',
    194: '_gen3',
    195: 'designator',
    196: '_gen4',
    197: '_gen14',
    198: 'direct_declarator_parameter_list',
    199: 'abstract_parameter_declaration',
    200: 'trailing_comma_opt',
    201: '_gen25',
    202: 'statement',
    203: 'for_cond',
    204: 'for_incr',
    205: '_gen34',
    206: '_gen46',
    207: 'static_opt',
    208: '_gen41',
    209: 'parameter_declaration',
    210: 'declaration_specifier',
    211: '_gen29',
    212: '_gen30',
    213: 'direct_declarator_expr',
    214: '_gen40',
    215: 'labeled_statement',
    216: 'external_prototype',
    217: 'union_specifier',
    218: 'abstract_declarator',
    219: 'pointer',
    220: '_gen35',
    221: 'va_args',
    222: 'declarator',
    223: 'expression_statement',
    224: 'pointer_sub',
    225: '_gen5',
    226: '_gen26',
    227: 'selection_statement',
    228: '_direct_abstract_declarator',
    229: 'compound_statement',
    230: 'iteration_statement',
    231: '_gen31',
    232: '_gen36',
    233: 'direct_declarator_modifier_list',
    234: 'jump_statement',
    235: 'token',
    236: '_gen38',
    237: '_gen32',
    238: 'declaration_list',
    239: '_gen33',
    240: 'enumerator',
    241: 'pp',
    242: '_gen1',
    243: '_gen2',
    244: '_gen6',
    245: '_gen37',
    246: '_gen23',
    247: '_direct_declarator',
    248: 'enum_specifier',
    '_expr': 119,
    'struct_declarator_body': 120,
    'direct_declarator_size': 121,
    '_gen7': 122,
    '_gen44': 123,
    '_gen21': 124,
    '_gen45': 125,
    'struct_or_union_sub': 126,
    'type_name': 127,
    'for_init': 128,
    'direct_declarator_modifier': 129,
    'keyword': 130,
    'block_item': 131,
    'external_declaration': 132,
    'init_declarator_list': 133,
    '_gen8': 134,
    'struct_or_union_body': 135,
    'sizeof_body': 136,
    '_gen16': 137,
    '_gen28': 138,
    'constant': 139,
    '_gen0': 140,
    'enum_specifier_sub': 141,
    'storage_class_specifier': 142,
    'typedef_name': 143,
    '_gen18': 144,
    'identifier': 145,
    'enum_specifier_body': 146,
    '_gen11': 147,
    'type_specifier': 148,
    'struct_declaration': 149,
    'block_item_list': 150,
    '_gen17': 151,
    'declaration': 152,
    'type_qualifier': 153,
    'misc': 154,
    'struct_specifier': 155,
    'function_specifier': 156,
    '_gen39': 157,
    'else_if_statement_list': 158,
    'type_qualifier_list_opt': 159,
    'specifier_qualifier': 160,
    '_gen9': 161,
    '_gen24': 162,
    'translation_unit': 163,
    'else_statement': 164,
    '_gen42': 165,
    '_gen22': 166,
    'struct_declarator': 167,
    '_gen19': 168,
    '_gen20': 169,
    '_gen10': 170,
    'enumeration_constant': 171,
    '_gen15': 172,
    'punctuator': 173,
    '_gen43': 174,
    '_gen27': 175,
    'external_declarator': 176,
    'else_if_statement': 177,
    'init_declarator': 178,
    'parameter_type_list': 179,
    'initializer': 180,
    'designation': 181,
    'initializer_list_item': 182,
    'external_declaration_sub': 183,
    'declarator_initializer': 184,
    '_expr_sans_comma': 185,
    'external_function': 186,
    'expression_opt': 187,
    'direct_abstract_declarator_expr': 188,
    'enumerator_assignment': 189,
    '_gen12': 190,
    '_gen13': 191,
    'external_declaration_sub_sub': 192,
    'named_parameter_declaration': 193,
    '_gen3': 194,
    'designator': 195,
    '_gen4': 196,
    '_gen14': 197,
    'direct_declarator_parameter_list': 198,
    'abstract_parameter_declaration': 199,
    'trailing_comma_opt': 200,
    '_gen25': 201,
    'statement': 202,
    'for_cond': 203,
    'for_incr': 204,
    '_gen34': 205,
    '_gen46': 206,
    'static_opt': 207,
    '_gen41': 208,
    'parameter_declaration': 209,
    'declaration_specifier': 210,
    '_gen29': 211,
    '_gen30': 212,
    'direct_declarator_expr': 213,
    '_gen40': 214,
    'labeled_statement': 215,
    'external_prototype': 216,
    'union_specifier': 217,
    'abstract_declarator': 218,
    'pointer': 219,
    '_gen35': 220,
    'va_args': 221,
    'declarator': 222,
    'expression_statement': 223,
    'pointer_sub': 224,
    '_gen5': 225,
    '_gen26': 226,
    'selection_statement': 227,
    '_direct_abstract_declarator': 228,
    'compound_statement': 229,
    'iteration_statement': 230,
    '_gen31': 231,
    '_gen36': 232,
    'direct_declarator_modifier_list': 233,
    'jump_statement': 234,
    'token': 235,
    '_gen38': 236,
    '_gen32': 237,
    'declaration_list': 238,
    '_gen33': 239,
    'enumerator': 240,
    'pp': 241,
    '_gen1': 242,
    '_gen2': 243,
    '_gen6': 244,
    '_gen37': 245,
    '_gen23': 246,
    '_direct_declarator': 247,
    'enum_specifier': 248,
  }
  # table[nonterminal][terminal] = rule
  table = [
    [-1, 23, 331, -1, -1, -1, -1, -1, 23, -1, 331, -1, 23, -1, -1, 331, -1, -1, -1, 23, -1, 390, -1, -1, 331, -1, 23, 23, 23, -1, -1, -1, -1, 331, -1, -1, -1, -1, -1, 23, -1, -1, -1, -1, 331, -1, -1, -1, -1, -1, -1, -1, 331, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 331, -1, -1, 390, -1, -1, 23, -1, -1, -1, -1, -1, -1, -1, 23, -1, -1, 331, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 390, -1, -1, 331, -1, 331, -1, -1, -1, -1, 23, -1, -1, -1, 331, -1, -1, -1, -1, -1, -1, -1, -1, 331, 331],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 17, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 360, -1, -1, -1, -1, -1, -1, -1, 360, -1, 360, -1, -1, 360, -1, -1, -1, 360, -1, -1, -1, -1, 360, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 217, -1, 360, -1, -1, -1, -1, -1, -1, -1, 360, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 360, -1, -1, -1, -1, -1, -1, -1, -1, -1, 360, -1, -1, -1, -1, -1, -1, 360, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 360, -1, 360, -1, -1, -1, -1, -1, -1, -1, -1, 360, -1, -1, -1, -1, -1, -1, -1, -1, 360, 360],
    [-1, -1, -1, -1, 183, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 183, -1, -1, -1, 86, 86, -1, -1, -1, -1, -1, -1, 183, -1, -1, 183, 183, -1, -1, 183, -1, -1, -1, -1, -1, 183, 183, 183, 183, -1, -1, 183, 183, -1, -1, 183, -1, -1, 183, -1, 183, -1, -1, -1, -1, -1, -1, -1, -1, -1, 183, -1, -1, -1, -1, -1, 183, 183, -1, -1, -1, 183, -1, -1, -1, -1, -1, -1, 183, 183, -1, -1, 86, -1, 183, -1, 183, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 183, 183, -1, -1, -1],
    [-1, -1, 105, -1, -1, -1, -1, -1, -1, -1, 105, -1, 105, -1, -1, 105, -1, -1, -1, 105, -1, -1, -1, -1, 105, -1, -1, -1, -1, -1, -1, -1, -1, 105, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 105, -1, -1, -1, -1, -1, -1, -1, 105, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 105, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 105, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 105, -1, 105, -1, -1, -1, -1, -1, -1, -1, -1, 105, -1, -1, -1, -1, -1, -1, -1, -1, 105, 105],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 339, 339, 211, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 18, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 7, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 6, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 291, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 359, -1, -1, -1, -1],
    [-1, -1, 132, -1, 187, -1, -1, -1, -1, -1, 132, -1, 132, -1, -1, 132, -1, -1, -1, 132, -1, -1, 187, -1, 132, -1, 14, -1, -1, -1, -1, -1, -1, -1, 187, -1, -1, 187, 187, -1, -1, 187, -1, -1, 132, -1, -1, 187, 187, 187, 187, -1, 132, 187, 187, -1, -1, 187, -1, -1, 187, -1, 187, 132, -1, -1, -1, -1, -1, -1, -1, -1, 187, 132, -1, -1, -1, -1, 187, 187, 132, -1, -1, 187, -1, -1, -1, -1, -1, -1, 187, 187, -1, -1, -1, -1, 187, 132, 187, 132, -1, -1, -1, -1, -1, -1, -1, -1, 132, -1, -1, -1, -1, -1, 187, 187, -1, 132, 132],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 81, -1, -1, 81, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 81, -1, -1, -1, -1, -1, -1, 230, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, 330, -1, -1, -1, -1, 121, -1, -1, -1, -1, -1, -1, 29, -1, -1, -1, -1, -1, 249, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 405, -1, -1, 410, 397, -1, -1, 138, -1, -1, -1, -1, -1, 344, 5, 30, 395, -1, -1, 185, -1, -1, 325, 37, -1, -1, 178, 348, 338, -1, -1, -1, -1, -1, 123, -1, 106, -1, 35, -1, -1, -1, -1, -1, 416, 327, -1, -1, -1, 372, -1, 310, -1, 116, -1, -1, 259, 21, 115, -1, -1, -1, 357, -1, 394, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 2, -1, 413, 219, 136, 314, -1, -1, 34],
    [-1, -1, 55, -1, 46, -1, -1, -1, -1, 55, 55, -1, 55, -1, -1, 55, 55, -1, -1, 55, -1, -1, 46, -1, 55, -1, 55, -1, -1, 55, -1, -1, -1, -1, 46, -1, -1, 46, 46, -1, -1, 46, -1, -1, 55, -1, -1, 46, 46, 46, 46, -1, 55, 46, 46, -1, 55, 46, -1, -1, 46, 55, 46, 55, -1, -1, -1, -1, -1, -1, 55, -1, 46, 55, -1, -1, -1, -1, 46, 46, 55, -1, -1, 46, -1, 55, -1, 55, -1, -1, 46, 46, 55, -1, 55, -1, 46, 55, 46, 55, -1, -1, -1, -1, -1, -1, -1, -1, 55, -1, 55, -1, 55, 55, 46, 46, -1, 55, 55],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 71, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 56, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 56, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 56, -1, -1, -1, -1, -1, -1, -1, -1, 56, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 193, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 373, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 373, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 373, -1, -1, -1, -1, -1, -1, -1, -1, 373, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 296, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 381, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 52, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, 248, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 248, -1, -1, -1, -1, 248, -1, -1, 248, 248, 248, 248, -1, -1, -1, -1, -1, 248, -1, -1, 248, 248, -1, -1, 248, -1, -1, -1, -1, -1, 248, 248, 248, 248, -1, 248, 248, 248, -1, -1, 248, -1, -1, 248, -1, 248, 248, -1, -1, -1, -1, -1, -1, -1, 248, 248, -1, -1, -1, -1, -1, 248, 248, 248, -1, -1, 248, -1, -1, -1, -1, -1, 248, 248, 248, -1, 248, 231, -1, 248, -1, 248, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 248, 248, 248, -1, -1],
    [-1, -1, 108, -1, -1, -1, -1, -1, -1, -1, 108, -1, 108, -1, -1, 108, -1, -1, -1, 108, -1, -1, -1, -1, 108, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 108, -1, 108, -1, -1, 243, -1, -1, 243, -1, 108, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 108, -1, -1, -1, -1, -1, -1, -1, -1, -1, 108, -1, -1, -1, -1, -1, -1, 108, -1, -1, 243, -1, -1, -1, -1, -1, -1, 243, -1, -1, -1, -1, -1, -1, 108, -1, 108, -1, -1, -1, -1, -1, -1, -1, -1, 108, -1, -1, -1, -1, -1, -1, -1, -1, 108, 108],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 294, -1, -1, -1, -1, 358, -1, -1, -1, -1, -1, -1, -1, -1, 68, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 57, -1, 207, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 48, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 396, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 306, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 85, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, 276, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 326, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 84, -1, -1, -1, -1, -1, -1, -1, 356, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 58, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 220, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 262, -1, -1, -1, -1, -1, 266, -1, -1, -1, -1, -1, -1, -1, -1, 262, 262, -1, -1, 262, -1, -1, -1, -1, -1, 262, 262, 262, 262, -1, 266, 262, 262, -1, -1, -1, -1, -1, 262, -1, 262, 266, -1, -1, -1, -1, -1, -1, -1, -1, 262, -1, -1, -1, -1, -1, 262, 262, 266, -1, -1, 262, -1, -1, -1, -1, -1, 266, -1, 262, -1, -1, -1, -1, 262, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 262, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 44, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 12, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 134, -1, -1, -1, -1, 92, 92, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 308, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 375, 153, -1, -1, 75, -1, -1, -1, -1, -1, -1, 150, 316, -1, -1, -1, 96, 16, -1, -1, -1, -1, -1, 301, -1, 346, -1, -1, -1, -1, -1, -1, -1, -1, -1, 198, -1, -1, -1, -1, -1, 305, 206, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 297, -1, -1, -1, -1, 352, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 341, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 36, -1, -1, -1, -1, -1, 36, -1, -1, -1, -1, -1, -1, -1, -1, 36, 36, -1, -1, 36, -1, -1, -1, -1, -1, 36, 36, 36, 36, -1, 36, 36, 36, -1, -1, -1, -1, -1, 36, -1, 36, 36, -1, -1, -1, -1, -1, -1, -1, -1, 36, -1, -1, -1, -1, -1, 36, 36, 36, -1, -1, 36, -1, -1, -1, -1, -1, 36, -1, 36, -1, -1, -1, -1, 36, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 36, -1, -1, -1, -1],
    [-1, -1, 281, -1, 281, -1, -1, -1, -1, 281, 281, -1, 281, -1, -1, 281, 281, -1, -1, 281, -1, -1, 281, -1, 281, -1, 281, -1, -1, 281, -1, -1, -1, -1, 281, -1, -1, 281, 281, -1, -1, 281, -1, -1, 281, -1, -1, 281, 281, 281, 281, -1, 281, 281, 281, -1, 281, 281, -1, -1, 281, 281, 281, 281, -1, -1, -1, -1, -1, -1, 281, -1, 281, 281, -1, -1, -1, -1, 281, 281, 281, -1, -1, 281, -1, 281, -1, 281, -1, -1, 281, 281, 281, -1, 281, -1, 281, 281, 281, 281, 281, -1, -1, -1, -1, -1, -1, -1, 281, -1, 281, -1, 281, 281, 281, 281, -1, 281, 281],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 258, -1, -1, -1, -1, -1, 258, -1, -1, -1, -1, -1, -1, -1, -1, 258, 258, -1, -1, 258, -1, -1, -1, -1, -1, 258, 258, 258, 258, -1, 258, 258, 258, -1, -1, -1, -1, -1, 258, -1, 258, 258, -1, -1, -1, -1, -1, -1, -1, -1, 258, -1, -1, -1, -1, -1, 258, 258, 258, -1, -1, 258, -1, -1, -1, -1, -1, 258, -1, 258, -1, -1, -1, -1, 258, -1, -1, -1, 252, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 258, -1, -1, -1, -1],
    [-1, -1, -1, -1, 412, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 412, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 412, -1, -1, 412, 412, -1, -1, 412, -1, -1, -1, -1, -1, 412, 412, 412, 412, -1, -1, 412, 412, -1, -1, 412, -1, -1, 412, -1, 412, -1, -1, -1, -1, -1, -1, -1, -1, -1, 412, -1, -1, -1, -1, -1, 412, 412, -1, -1, -1, 412, -1, -1, -1, -1, -1, -1, 412, 412, -1, -1, -1, -1, 412, -1, 412, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 412, 412, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 240, -1, -1, 286, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 70, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 315, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 225, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 421, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 275, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 10, -1, 10, -1, -1, -1, -1, 10, 10, -1, 10, -1, -1, 10, 10, -1, -1, 10, -1, -1, 10, -1, 10, -1, 10, -1, -1, 10, -1, -1, -1, -1, 10, -1, -1, 10, 10, -1, -1, 10, -1, -1, 10, -1, -1, 10, 10, 10, 10, -1, 10, 10, 10, -1, 10, 10, -1, -1, 10, 10, 10, 10, -1, -1, -1, -1, -1, -1, 10, -1, 10, 10, -1, -1, -1, -1, 10, 10, 10, -1, -1, 10, -1, 10, -1, 10, -1, -1, 10, 10, 10, -1, 10, -1, 10, 10, 10, 10, 10, -1, -1, -1, -1, -1, -1, -1, 10, -1, 10, -1, 10, 10, 10, 10, -1, 10, 10],
    [-1, -1, 147, -1, 147, -1, -1, -1, -1, 147, 147, -1, 147, -1, -1, 147, 147, -1, -1, 147, -1, -1, 147, 147, 147, -1, 147, -1, -1, 147, -1, -1, -1, -1, 147, -1, -1, 147, 147, -1, -1, 147, -1, -1, 147, -1, -1, 147, 147, 147, 147, -1, 147, 147, 147, -1, 147, 147, -1, -1, 147, 147, 147, 147, -1, -1, -1, 147, 147, -1, 147, -1, 147, 147, -1, -1, -1, -1, 147, 147, 147, -1, -1, 147, -1, 147, -1, 147, -1, -1, 147, 147, 147, -1, 147, -1, 147, 147, 147, 147, 147, -1, -1, -1, -1, -1, -1, -1, 147, -1, 147, -1, 147, 147, 147, 147, -1, 147, 147],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 19, -1, -1, -1, -1, -1, -1, -1, 19, -1, 19, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 19, -1, -1, 19, -1, 19, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 19, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 19, -1, -1, 19, -1, -1, -1, -1, -1, 19, 19, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 273, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 273, 273, -1, -1, 273, -1, -1, -1, -1, -1, 426, 273, 273, 426, -1, -1, 273, 273, -1, -1, -1, -1, -1, 273, -1, 273, -1, -1, -1, -1, -1, -1, -1, -1, -1, 273, -1, -1, -1, -1, -1, 273, 273, -1, -1, -1, 426, -1, -1, -1, -1, -1, -1, -1, 273, -1, -1, -1, -1, 273, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 273, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 67, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 67, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 67, -1, -1, -1, -1, -1, -1, -1, -1, 67, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 267, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 271, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 367, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 419, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 69, -1, 69, -1, -1, -1, -1, 69, 69, -1, 69, -1, -1, 69, 69, -1, -1, 69, -1, -1, 69, -1, 69, -1, 69, -1, -1, 69, -1, -1, -1, -1, 69, -1, -1, 69, 69, -1, -1, 69, -1, -1, 69, -1, -1, 69, 69, 69, 69, -1, 69, 69, 69, -1, 69, 69, -1, -1, 69, 69, 69, 69, -1, -1, -1, 69, 51, -1, 69, -1, 69, 69, -1, -1, -1, -1, 69, 69, 69, -1, -1, 69, -1, 69, -1, 69, -1, -1, 69, 69, 69, -1, 69, -1, 69, 69, 69, 69, 69, -1, -1, -1, -1, -1, -1, -1, 69, -1, 69, -1, 69, 69, 69, 69, -1, 69, 69],
    [-1, -1, -1, -1, 245, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 245, -1, -1, -1, -1, 245, -1, -1, 245, 245, 245, 245, -1, -1, -1, -1, -1, 245, -1, -1, 245, 245, -1, -1, 245, -1, -1, -1, -1, -1, 245, 245, 245, 245, -1, 245, 245, 245, -1, -1, 245, -1, -1, 245, -1, 245, 245, -1, -1, -1, -1, -1, -1, -1, 245, 245, -1, -1, -1, -1, -1, 245, 245, 245, -1, -1, 245, -1, -1, -1, -1, -1, 245, 245, 245, -1, 245, 242, -1, 245, -1, 245, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 245, 245, 245, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 79, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 223, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 223, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 223, -1, -1, -1, -1, -1, -1, -1, -1, 223, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 277, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 277, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 277, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 277, -1, -1, -1, -1, -1, -1, -1, -1, 277, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 284, 107, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 59, 72, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 90, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 274, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 278, -1, -1, 278, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, 128, -1, -1, -1, -1, 241, -1, 40, -1, -1, 269, 261, -1, 189, -1, -1, -1, 391, 28, 370, 374, -1, -1, -1, -1, 152, 162, 312, -1, 354, 288, 177, -1, -1, 250, 270, -1, -1, 366, 287, -1, -1, 65, -1, 77, 53, -1, -1, -1, -1, 130, -1, -1, -1, 22, -1, -1, 199, 25, -1, -1, -1, 415, -1, 145, 292, -1, -1, 64, -1, -1, -1, -1, 208, 32, 300, 362, -1, -1, -1, 201, -1, -1, 244, -1, -1, -1, 329, -1, -1, -1, -1, -1, 411, -1, -1, -1, -1, -1, 114, 192, -1, 1, -1, -1, 47, 214, -1, 251, -1, 157, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 95, -1, 95, -1, -1, -1, -1, 95, 95, -1, 95, -1, -1, 95, 95, -1, -1, 95, -1, -1, 95, 142, 95, -1, 95, -1, -1, 95, -1, -1, -1, -1, 95, -1, -1, 95, 95, -1, -1, 95, -1, -1, 95, -1, -1, 95, 95, 95, 95, -1, 95, 95, 95, -1, 95, 95, -1, -1, 95, 95, 95, 95, -1, -1, -1, 95, 95, -1, 95, -1, 95, 95, -1, -1, -1, -1, 95, 95, 95, -1, -1, 95, -1, 95, -1, 95, -1, -1, 95, 95, 95, -1, 95, -1, 95, 95, 95, 95, 95, -1, -1, -1, -1, -1, -1, -1, 95, -1, 95, -1, 95, 95, 95, 95, -1, 95, 95],
    [-1, -1, 318, -1, -1, -1, -1, -1, -1, -1, 318, -1, 318, -1, -1, 318, -1, -1, -1, 318, -1, -1, -1, -1, 318, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 318, -1, 318, -1, -1, 408, -1, -1, 408, -1, 318, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 318, -1, -1, -1, -1, -1, -1, -1, -1, -1, 318, -1, -1, -1, -1, -1, -1, 318, -1, -1, 408, -1, -1, -1, -1, -1, -1, 408, -1, -1, -1, -1, -1, -1, 318, -1, 318, -1, -1, -1, -1, -1, -1, -1, -1, 318, -1, -1, -1, -1, -1, -1, -1, -1, 318, 318],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 382, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 165, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 137, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 137, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 137, -1, -1, -1, -1, -1, -1, -1, -1, 137, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 236, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 236, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 309, -1, -1, -1, -1, -1, -1, -1, 309, -1, 309, -1, -1, 309, -1, -1, -1, 309, -1, -1, -1, -1, 309, -1, -1, -1, -1, -1, -1, -1, -1, 309, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 309, -1, -1, -1, -1, -1, -1, -1, 309, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 309, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 309, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 317, -1, -1, 309, -1, 309, -1, -1, -1, -1, -1, -1, -1, -1, 309, -1, -1, -1, -1, -1, -1, -1, -1, 309, 309],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 365, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 365, -1, -1, 365, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 126, -1, -1, -1, -1, -1, -1, -1, 126, -1, 126, -1, -1, 126, -1, -1, -1, 126, -1, 126, -1, -1, 126, -1, -1, -1, -1, -1, -1, -1, -1, 126, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 126, -1, -1, -1, -1, -1, -1, -1, 126, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 126, -1, -1, 126, -1, -1, 126, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 126, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 126, -1, -1, 126, -1, 126, -1, -1, -1, -1, -1, -1, -1, -1, 126, -1, -1, -1, -1, -1, -1, -1, -1, 126, 126],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 93, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 298, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 93, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 93, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 158, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 377, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, 39, 227, -1, -1, -1, -1, -1, -1, -1, 227, -1, 227, -1, -1, 227, -1, -1, -1, 227, -1, -1, -1, -1, 227, -1, 39, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 227, -1, -1, -1, -1, -1, -1, -1, 227, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 227, -1, -1, -1, -1, -1, -1, -1, -1, -1, 227, -1, -1, -1, -1, -1, -1, 227, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 227, -1, 227, -1, -1, -1, -1, -1, -1, -1, -1, 227, -1, -1, -1, -1, -1, -1, -1, -1, 227, 227],
    [-1, -1, 49, -1, -1, -1, -1, -1, -1, -1, 49, -1, 49, -1, -1, 49, -1, -1, -1, 49, -1, -1, -1, -1, 49, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 94, -1, 49, -1, -1, 49, -1, -1, 49, -1, 49, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 49, -1, -1, -1, -1, -1, -1, -1, -1, -1, 49, -1, -1, -1, -1, -1, -1, 49, -1, -1, 49, -1, -1, -1, -1, -1, -1, 49, -1, -1, -1, -1, -1, -1, 49, -1, 49, -1, -1, -1, -1, -1, -1, -1, -1, 49, -1, -1, -1, -1, -1, -1, -1, -1, 49, 49],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 41, -1, -1, -1, -1, -1, 43, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 43, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 332, -1, -1, -1, -1, -1, -1, -1, 332, -1, 332, -1, -1, 332, -1, -1, -1, 332, -1, 332, -1, -1, 332, -1, -1, -1, -1, -1, -1, -1, -1, 332, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 332, -1, -1, -1, -1, -1, -1, -1, 332, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 332, -1, -1, 332, -1, -1, 332, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 332, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 332, -1, -1, 332, -1, 332, -1, -1, -1, -1, -1, -1, -1, -1, 332, -1, -1, -1, -1, -1, -1, -1, -1, 332, 332],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 336, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 340, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 202, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 224, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 290, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 355, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 260, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 260, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 334, -1, -1, 13, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 351, 347, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 295, -1, -1, -1, -1, -1, -1, -1, 295, -1, 295, -1, -1, 295, -1, -1, -1, 295, -1, 299, -1, -1, 295, -1, -1, -1, -1, -1, -1, -1, -1, 295, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 295, -1, -1, -1, -1, -1, -1, -1, 295, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 295, -1, -1, 299, -1, -1, 299, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 295, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 295, -1, -1, 295, -1, 295, -1, -1, -1, -1, -1, -1, -1, -1, 295, -1, -1, -1, -1, -1, -1, -1, -1, 295, 295],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 379, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 182, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 379, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 3, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 323, -1, -1, -1, 9, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 194, -1, -1, -1, -1, -1, -1, -1, 194, -1, 194, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 26, -1, -1, 26, -1, 194, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 194, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 194, -1, -1, 26, -1, -1, -1, -1, -1, 194, 194, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 218, -1, -1, -1, -1, -1, -1, 166, 218, -1, 218, -1, -1, 218, 151, -1, -1, 218, -1, -1, -1, -1, 218, -1, 218, -1, -1, 265, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 218, -1, -1, -1, -1, -1, -1, -1, 218, -1, -1, -1, 151, -1, -1, -1, -1, 264, -1, 218, -1, -1, -1, -1, -1, -1, 265, -1, -1, 218, -1, -1, -1, -1, -1, -1, 218, -1, -1, -1, -1, 264, -1, 151, -1, -1, -1, -1, 264, -1, 89, -1, -1, 218, -1, 218, -1, -1, -1, -1, -1, -1, -1, -1, 218, -1, 151, -1, 265, 166, -1, -1, -1, 218, 218],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 172, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, 228, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 179, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 82, -1, -1, -1, -1, -1, -1, -1, -1, -1, 82, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 61, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 61, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 61, -1, -1, -1, -1, -1, -1, -1, -1, 61, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 235, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 235, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 255, -1, -1, -1, -1, -1, -1, -1, 255, -1, 255, -1, -1, 255, -1, -1, -1, 255, -1, -1, -1, -1, 255, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 255, -1, -1, -1, -1, -1, -1, -1, 255, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 255, -1, -1, -1, -1, -1, -1, -1, -1, -1, 255, -1, -1, -1, -1, -1, -1, 255, -1, -1, -1, -1, -1, -1, -1, -1, -1, 209, -1, -1, -1, -1, -1, -1, 255, -1, 255, -1, -1, -1, -1, -1, -1, -1, -1, 255, -1, -1, -1, -1, -1, -1, -1, -1, 255, 255],
    [-1, -1, 234, -1, 234, -1, -1, -1, -1, 234, 234, -1, 234, -1, -1, 234, 234, -1, -1, 234, -1, -1, 234, 234, 234, -1, 234, -1, -1, 234, -1, -1, -1, -1, 234, -1, -1, 234, 234, -1, -1, 234, -1, -1, 234, -1, -1, 234, 234, 234, 234, -1, 234, 234, 234, -1, 234, 234, -1, -1, 234, 234, 234, 234, -1, -1, -1, 234, 234, -1, 234, -1, 234, 234, -1, -1, -1, -1, 234, 234, 234, -1, -1, 234, -1, 234, -1, 234, -1, -1, 234, 234, 234, -1, 234, -1, 234, 234, 234, 234, 234, -1, -1, -1, -1, -1, -1, -1, 234, -1, 234, -1, 234, 234, 234, 234, -1, 234, 234],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 141, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 387, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, 350, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 186, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 24, -1, -1, 186, 186, -1, -1, 186, -1, -1, -1, -1, -1, 167, 186, 186, 167, -1, -1, 186, 186, -1, -1, 350, -1, -1, 186, -1, 186, -1, -1, -1, -1, -1, -1, -1, -1, -1, 186, -1, -1, -1, -1, -1, 186, 186, -1, -1, -1, 167, -1, -1, -1, -1, -1, -1, 350, 186, -1, -1, -1, -1, 186, -1, 350, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 186, 350, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 109, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 109, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 144, -1, -1, -1, -1, -1, -1, -1, -1, -1, 149, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 99, -1, -1, -1, -1, -1, -1, -1, 99, -1, 99, -1, -1, 99, -1, -1, -1, 99, -1, -1, -1, -1, 99, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 99, -1, 99, -1, -1, 99, -1, -1, 99, -1, 99, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 99, -1, -1, -1, -1, -1, -1, -1, -1, -1, 99, -1, -1, -1, -1, -1, -1, 99, -1, -1, 99, -1, -1, -1, -1, -1, -1, 99, -1, -1, -1, -1, -1, -1, 99, -1, 99, -1, -1, -1, -1, -1, -1, -1, -1, 99, -1, -1, -1, -1, -1, -1, -1, -1, 99, 99],
    [-1, -1, 27, -1, 27, -1, -1, -1, -1, 27, 27, -1, 27, -1, -1, 27, 27, -1, -1, 27, -1, -1, 27, -1, 27, -1, 27, -1, -1, 27, -1, -1, -1, -1, 27, -1, -1, 27, 27, -1, -1, 27, -1, -1, 27, -1, -1, 27, 27, 27, 27, -1, 27, 27, 27, -1, 27, 27, -1, -1, 27, 27, 27, 27, -1, -1, -1, -1, -1, -1, 27, -1, 27, 27, -1, -1, -1, -1, 27, 27, 27, -1, -1, 27, -1, 27, -1, 27, -1, -1, 27, 27, 27, -1, 27, -1, 27, 27, 27, 27, 31, -1, -1, -1, -1, -1, -1, -1, 27, -1, 27, -1, 27, 27, 27, 27, -1, 27, 27],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 369, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 8, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 383, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 335, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 424, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 237, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 173, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 237, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 215, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 88, -1, -1, -1, -1, -1, -1, -1, 171, -1, 88, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 171, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 171, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 403, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 122, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 122, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 122, -1, -1, -1, -1, -1, -1, -1, -1, 122, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 285, -1, -1, -1, -1, -1, -1, -1, 285, -1, 285, -1, -1, 285, -1, -1, -1, 285, -1, -1, -1, -1, 285, -1, 285, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 285, -1, -1, -1, -1, -1, -1, -1, 285, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 285, -1, -1, -1, -1, -1, -1, -1, -1, -1, 285, -1, -1, -1, -1, -1, -1, 285, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 285, -1, 285, -1, -1, -1, -1, -1, -1, -1, -1, 285, -1, -1, -1, -1, -1, -1, -1, -1, 285, 285],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 321, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, 302, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 302, -1, -1, -1, 302, 302, -1, -1, -1, -1, -1, -1, 302, -1, -1, 302, 302, -1, -1, 302, -1, -1, -1, -1, -1, 302, 302, 302, 302, -1, -1, 302, 302, -1, -1, 302, -1, -1, 302, -1, 302, -1, -1, -1, -1, -1, -1, -1, -1, -1, 302, -1, -1, -1, -1, -1, 302, 302, -1, -1, -1, 302, -1, -1, -1, -1, -1, -1, 302, 302, -1, -1, 302, -1, 302, -1, 302, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 302, 302, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 385, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 389, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 389, -1, -1, -1, -1, -1, -1, -1, -1, 389, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, 423, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 169, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 175, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 256, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 283, -1, -1, -1, -1, -1, -1, 388, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 159, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 313, -1, -1, -1, -1, -1, -1, -1, 404, -1, 313, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 404, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 272, -1, -1, -1, -1, -1, -1, -1, 272, -1, 272, -1, -1, 272, -1, -1, -1, 272, -1, -1, -1, -1, 272, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 272, -1, 272, -1, -1, 272, -1, -1, 272, -1, 272, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 272, -1, -1, -1, -1, -1, -1, -1, -1, -1, 272, -1, -1, -1, -1, -1, -1, 272, -1, -1, 272, -1, -1, -1, -1, -1, -1, 272, -1, -1, -1, -1, -1, -1, 272, -1, 272, -1, -1, -1, -1, -1, -1, -1, -1, 272, -1, -1, -1, -1, -1, -1, -1, -1, 272, 272],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 118, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 311, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 254, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 156, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, 102, -1, -1, 0, -1, 102, -1, 102, 0, 100, 102, 102, 131, 102, 100, 0, -1, 102, 102, 102, 102, 0, -1, 100, -1, 102, 102, 102, -1, 102, 102, 102, -1, 0, 102, 102, 0, 0, 102, 102, 0, -1, 102, 392, 102, 102, 0, 0, 0, 0, 102, -1, 0, -1, 102, 0, 0, 102, 102, 0, 0, 0, 102, -1, 102, 102, -1, 0, 102, 0, -1, 0, -1, 102, 102, 102, 102, 0, 0, 345, 102, -1, 0, 102, 0, -1, 0, 102, -1, 0, 0, 0, -1, 102, -1, 0, 100, 0, 100, 102, 102, -1, 102, -1, -1, 102, 102, -1, 102, 0, 102, 0, 0, 0, 0, -1, 100, 0],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 353, -1, -1, -1, -1, -1, -1, -1, 353, -1, 353, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 104, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 353, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 353, -1, -1, -1, -1, -1, -1, -1, -1, 353, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 349, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, 280, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 280, -1, -1, -1, 280, 280, -1, -1, -1, -1, -1, -1, 280, -1, -1, 280, 280, -1, -1, 280, -1, -1, -1, -1, -1, 280, 280, 280, 280, -1, -1, 280, 280, -1, -1, 280, -1, -1, 280, -1, 280, -1, -1, -1, -1, -1, -1, -1, -1, -1, 280, -1, -1, -1, -1, -1, 280, 280, -1, -1, -1, 280, -1, -1, -1, -1, -1, -1, 280, 280, -1, -1, 280, -1, 280, -1, 280, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 280, 280, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 184, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 111, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, 364, -1, -1, -1, -1, -1, 247, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 386, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, 140, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 140, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 140, -1, -1, 140, 140, -1, -1, 140, -1, -1, -1, -1, -1, 140, 140, 140, 140, -1, -1, 140, 140, -1, -1, 140, -1, -1, 140, -1, 140, -1, -1, -1, -1, -1, -1, -1, -1, -1, 140, -1, -1, -1, -1, -1, 140, 140, -1, -1, -1, 140, -1, -1, -1, -1, -1, -1, 140, 140, -1, -1, -1, -1, 140, -1, 140, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 140, 140, -1, -1, -1],
    [-1, -1, -1, -1, 303, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 307, -1, -1, -1, -1, 303, -1, -1, 307, 307, 307, -1, -1, -1, -1, -1, -1, 303, -1, -1, 303, 303, -1, -1, 303, -1, -1, -1, -1, -1, 303, 303, 303, 303, -1, 307, 303, 303, -1, -1, 303, -1, -1, 303, -1, 303, 307, -1, -1, -1, -1, -1, -1, -1, 307, 303, -1, -1, -1, -1, -1, 303, 303, 307, -1, -1, 303, -1, -1, -1, -1, -1, 307, 303, 303, -1, 307, -1, -1, 303, -1, 303, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 303, 303, 307, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 361, 361, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 337, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 337, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 337, -1, -1, -1, -1, -1, -1, -1, -1, 337, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 205, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 420, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 20, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  ]
  TERMINAL_DIVEQ = 0
  TERMINAL_RPAREN = 1
  TERMINAL_BITAND = 2
  TERMINAL_NOT = 3
  TERMINAL_REGISTER = 4
  TERMINAL_BITNOT = 5
  TERMINAL_POUND = 6
  TERMINAL_DEFINED_SEPARATOR = 7
  TERMINAL_ARROW = 8
  TERMINAL_IF = 9
  TERMINAL_INTEGER_CONSTANT = 10
  TERMINAL_MOD = 11
  TERMINAL_DECR = 12
  TERMINAL_PP_NUMBER = 13
  TERMINAL_ELIPSIS = 14
  TERMINAL_FLOATING_CONSTANT = 15
  TERMINAL_CONTINUE = 16
  TERMINAL_COMMA_VA_ARGS = 17
  TERMINAL_SUB = 18
  TERMINAL_INCR = 19
  TERMINAL_POUNDPOUND = 20
  TERMINAL_ASSIGN = 21
  TERMINAL_UNION = 22
  TERMINAL_ELSE_IF = 23
  TERMINAL_ENUMERATION_CONSTANT = 24
  TERMINAL__DIRECT_ABSTRACT_DECLARATOR = 25
  TERMINAL_SEMI = 26
  TERMINAL_COMMA = 27
  TERMINAL_COLON = 28
  TERMINAL_LABEL_HINT = 29
  TERMINAL_SUBEQ = 30
  TERMINAL_BITOREQ = 31
  TERMINAL_AMPERSAND = 32
  TERMINAL__EXPR_SANS_COMMA = 33
  TERMINAL_INLINE = 34
  TERMINAL_AND = 35
  TERMINAL_TILDE = 36
  TERMINAL_ENUM = 37
  TERMINAL_STRUCT = 38
  TERMINAL_QUESTIONMARK = 39
  TERMINAL_BITXOREQ = 40
  TERMINAL_LONG = 41
  TERMINAL_VARIABLE_LENGTH_ARRAY = 42
  TERMINAL_BITOR = 43
  TERMINAL_STRING_LITERAL = 44
  TERMINAL_EQ = 45
  TERMINAL_BITANDEQ = 46
  TERMINAL_RESTRICT = 47
  TERMINAL_COMPLEX = 48
  TERMINAL_INT = 49
  TERMINAL_CONST = 50
  TERMINAL_LSHIFTEQ = 51
  TERMINAL_ASTERISK = 52
  TERMINAL_SHORT = 53
  TERMINAL_TYPEDEF_IDENTIFIER = 54
  TERMINAL_NEQ = 55
  TERMINAL_BREAK = 56
  TERMINAL_TYPEDEF = 57
  TERMINAL_OR = 58
  TERMINAL_RSHIFTEQ = 59
  TERMINAL_SIGNED = 60
  TERMINAL_FOR = 61
  TERMINAL_FLOAT = 62
  TERMINAL_LPAREN = 63
  TERMINAL_ABSTRACT_PARAMETER_HINT = 64
  TERMINAL_RSHIFT = 65
  TERMINAL_LSQUARE = 66
  TERMINAL_ENDIF = 67
  TERMINAL_ELSE = 68
  TERMINAL_DOT = 69
  TERMINAL_DEFAULT = 70
  TERMINAL_FUNCTION_DEFINITION_HINT = 71
  TERMINAL_DOUBLE = 72
  TERMINAL__EXPR = 73
  TERMINAL_LTEQ = 74
  TERMINAL_BITXOR = 75
  TERMINAL_ADDEQ = 76
  TERMINAL_RSQUARE = 77
  TERMINAL_BOOL = 78
  TERMINAL_UNSIGNED = 79
  TERMINAL_IDENTIFIER = 80
  TERMINAL_GTEQ = 81
  TERMINAL_SIZEOF_SEPARATOR = 82
  TERMINAL_VOLATILE = 83
  TERMINAL_MODEQ = 84
  TERMINAL_WHILE = 85
  TERMINAL_DEFINED = 86
  TERMINAL_GOTO = 87
  TERMINAL_LT = 88
  TERMINAL__DIRECT_DECLARATOR = 89
  TERMINAL_STATIC = 90
  TERMINAL_IMAGINARY = 91
  TERMINAL_DO = 92
  TERMINAL_DECLARATOR_HINT = 93
  TERMINAL_LBRACE = 94
  TERMINAL_NAMED_PARAMETER_HINT = 95
  TERMINAL_VOID = 96
  TERMINAL_HEXADECIMAL_FLOATING_CONSTANT = 97
  TERMINAL_EXTERN = 98
  TERMINAL_DECIMAL_FLOATING_CONSTANT = 99
  TERMINAL_RBRACE = 100
  TERMINAL_LSHIFT = 101
  TERMINAL_EXTERNAL_DECLARATION_HINT = 102
  TERMINAL_GT = 103
  TERMINAL_TRAILING_COMMA = 104
  TERMINAL_UNIVERSAL_CHARACTER_NAME = 105
  TERMINAL_MULEQ = 106
  TERMINAL_ADD = 107
  TERMINAL_LPAREN_CAST = 108
  TERMINAL_EXCLAMATION_POINT = 109
  TERMINAL_RETURN = 110
  TERMINAL_DIV = 111
  TERMINAL_CASE = 112
  TERMINAL_SWITCH = 113
  TERMINAL_CHAR = 114
  TERMINAL_AUTO = 115
  TERMINAL_FUNCTION_PROTOTYPE_HINT = 116
  TERMINAL_CHARACTER_CONSTANT = 117
  TERMINAL_SIZEOF = 118
  def __init__(self, tokens=None):
    self.__dict__.update(locals())
    self.expressionParsers = dict()
  def isTerminal(self, id):
    return 0 <= id <= 118
  def isNonTerminal(self, id):
    return 119 <= id <= 248
  def parse(self, tokens):
    self.tokens = tokens
    self.start = 'TRANSLATION_UNIT'
    tree = self.parse_translation_unit()
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
  def parse_struct_declarator_body(self):
    current = self.tokens.current()
    rule = self.table[1][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(120, self.nonterminals[120]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 17:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(28) # colon
      tree.add(t)
      subtree = self.parse_declarator()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_direct_declarator_size(self):
    current = self.tokens.current()
    rule = self.table[2][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(121, self.nonterminals[121]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 217:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(42) # variable_length_array
      tree.add(t)
      return tree
    elif rule == 360:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__expr()
      tree.add( subtree )
      return tree
    elif current.getId() in [73, 2, 63, 80, 10, 99, 52, 12, 44, 15, 97, 19, 118, 117, 24, 108]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__expr()
      tree.add( subtree )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen7(self):
    current = self.tokens.current()
    rule = self.table[3][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(122, self.nonterminals[122]))
    tree.list = 'nlist'
    if current != None and (current.getId() in [94, 26, 27]):
      return tree
    if current == None:
      return tree
    if rule == 183:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_declaration()
      tree.add( subtree )
      subtree = self.parse__gen7()
      tree.add( subtree )
      return tree
    return tree
  def parse__gen44(self):
    current = self.tokens.current()
    rule = self.table[4][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(123, self.nonterminals[123]))
    tree.list = 'slist'
    if current != None and (current.getId() in []):
      return tree
    if current == None:
      return tree
    if rule == 105:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__expr_sans_comma()
      tree.add( subtree )
      subtree = self.parse__gen45()
      tree.add( subtree )
      return tree
    return tree
  def parse__gen21(self):
    current = self.tokens.current()
    rule = self.table[5][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(124, self.nonterminals[124]))
    tree.list = False
    if current != None and (current.getId() in [27, 26]):
      return tree
    if current == None:
      return tree
    if rule == 211:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_struct_declarator_body()
      tree.add( subtree )
      return tree
    return tree
  def parse__gen45(self):
    current = self.tokens.current()
    rule = self.table[6][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(125, self.nonterminals[125]))
    tree.list = 'slist'
    if current != None and (current.getId() in []):
      return tree
    if current == None:
      return tree
    if rule == 18:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(27) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self.parse__expr_sans_comma()
      tree.add( subtree )
      subtree = self.parse__gen45()
      tree.add( subtree )
      return tree
    return tree
  def parse_struct_or_union_sub(self):
    current = self.tokens.current()
    rule = self.table[7][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(126, self.nonterminals[126]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 6:
      tree.astTransform = AstTransformNodeCreator('StructOrUnion', {'body': 0})
      subtree = self.parse_struct_or_union_body()
      tree.add( subtree )
      return tree
    elif rule == 7:
      tree.astTransform = AstTransformNodeCreator('StructOrUnion', {'body': 1, 'name': 0})
      t = self.expect(80) # identifier
      tree.add(t)
      subtree = self.parse__gen16()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_type_name(self):
    current = self.tokens.current()
    rule = self.table[8][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(127, self.nonterminals[127]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 291:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(49) # int
      tree.add(t)
      return tree
    elif rule == 359:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(114) # char
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_for_init(self):
    current = self.tokens.current()
    rule = self.table[9][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(128, self.nonterminals[128]))
    tree.list = False
    if current != None and (current.getId() in [26]):
      return tree
    if current == None:
      return tree
    if rule == 132:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__expr()
      tree.add( subtree )
      return tree
    elif rule == 187:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_declaration()
      tree.add( subtree )
      subtree = self.parse_expression_opt()
      tree.add( subtree )
      return tree
    elif current.getId() in [73, 2, 63, 80, 10, 99, 52, 12, 44, 15, 97, 19, 118, 117, 24, 108]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__expr()
      tree.add( subtree )
    return tree
  def parse_direct_declarator_modifier(self):
    current = self.tokens.current()
    rule = self.table[10][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(129, self.nonterminals[129]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 81:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_type_qualifier()
      tree.add( subtree )
      return tree
    elif rule == 230:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(90) # static
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_keyword(self):
    current = self.tokens.current()
    rule = self.table[11][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(130, self.nonterminals[130]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 2:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(110) # return
      tree.add(t)
      return tree
    elif rule == 5:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(48) # complex
      tree.add(t)
      return tree
    elif rule == 21:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(91) # imaginary
      tree.add(t)
      return tree
    elif rule == 29:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(16) # continue
      tree.add(t)
      return tree
    elif rule == 30:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(49) # int
      tree.add(t)
      return tree
    elif rule == 34:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(118) # sizeof
      tree.add(t)
      return tree
    elif rule == 35:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(72) # double
      tree.add(t)
      return tree
    elif rule == 37:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(57) # typedef
      tree.add(t)
      return tree
    elif rule == 106:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(70) # default
      tree.add(t)
      return tree
    elif rule == 115:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(92) # do
      tree.add(t)
      return tree
    elif rule == 116:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(87) # goto
      tree.add(t)
      return tree
    elif rule == 121:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(9) # if
      tree.add(t)
      return tree
    elif rule == 123:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(68) # else
      tree.add(t)
      return tree
    elif rule == 136:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(114) # char
      tree.add(t)
      return tree
    elif rule == 138:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(41) # long
      tree.add(t)
      return tree
    elif rule == 178:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(60) # signed
      tree.add(t)
      return tree
    elif rule == 185:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(53) # short
      tree.add(t)
      return tree
    elif rule == 219:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(113) # switch
      tree.add(t)
      return tree
    elif rule == 249:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(22) # union
      tree.add(t)
      return tree
    elif rule == 259:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(90) # static
      tree.add(t)
      return tree
    elif rule == 310:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(85) # while
      tree.add(t)
      return tree
    elif rule == 314:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(115) # auto
      tree.add(t)
      return tree
    elif rule == 325:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(56) # break
      tree.add(t)
      return tree
    elif rule == 327:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(79) # unsigned
      tree.add(t)
      return tree
    elif rule == 330:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(4) # register
      tree.add(t)
      return tree
    elif rule == 338:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(62) # float
      tree.add(t)
      return tree
    elif rule == 344:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(47) # restrict
      tree.add(t)
      return tree
    elif rule == 348:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(61) # for
      tree.add(t)
      return tree
    elif rule == 357:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(96) # void
      tree.add(t)
      return tree
    elif rule == 372:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(83) # volatile
      tree.add(t)
      return tree
    elif rule == 394:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(98) # extern
      tree.add(t)
      return tree
    elif rule == 395:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(50) # const
      tree.add(t)
      return tree
    elif rule == 397:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(38) # struct
      tree.add(t)
      return tree
    elif rule == 405:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(34) # inline
      tree.add(t)
      return tree
    elif rule == 410:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(37) # enum
      tree.add(t)
      return tree
    elif rule == 413:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(112) # case
      tree.add(t)
      return tree
    elif rule == 416:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(78) # bool
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_block_item(self):
    current = self.tokens.current()
    rule = self.table[12][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(131, self.nonterminals[131]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 46:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_declaration()
      tree.add( subtree )
      return tree
    elif rule == 55:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_statement()
      tree.add( subtree )
      return tree
    elif current.getId() in [73, 2, 63, 80, 10, 99, 52, 12, 44, 15, 97, 19, 118, 117, 24, 108]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_statement()
      tree.add( subtree )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_external_declaration(self):
    current = self.tokens.current()
    rule = self.table[13][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(132, self.nonterminals[132]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 71:
      tree.astTransform = AstTransformNodeCreator('ExternalDeclaration', {'declarations': 2, 'declaration_specifiers': 1})
      t = self.expect(102) # external_declaration_hint
      tree.add(t)
      subtree = self.parse__gen1()
      tree.add( subtree )
      subtree = self.parse_external_declaration_sub()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_init_declarator_list(self):
    current = self.tokens.current()
    rule = self.table[14][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(133, self.nonterminals[133]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 56:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen9()
      tree.add( subtree )
      return tree
    elif current.getId() in [80, 89, 63]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen9()
      tree.add( subtree )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen8(self):
    current = self.tokens.current()
    rule = self.table[15][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(134, self.nonterminals[134]))
    tree.list = False
    if current != None and (current.getId() in [26]):
      return tree
    if current == None:
      return tree
    if rule == 373:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_init_declarator_list()
      tree.add( subtree )
      return tree
    elif current.getId() in [80, 89, 63]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_init_declarator_list()
      tree.add( subtree )
    return tree
  def parse_struct_or_union_body(self):
    current = self.tokens.current()
    rule = self.table[16][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(135, self.nonterminals[135]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 296:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(94) # lbrace
      tree.add(t)
      subtree = self.parse__gen17()
      tree.add( subtree )
      t = self.expect(100) # rbrace
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_sizeof_body(self):
    current = self.tokens.current()
    rule = self.table[17][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(136, self.nonterminals[136]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 52:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(80) # identifier
      tree.add(t)
      return tree
    elif rule == 381:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(63) # lparen
      tree.add(t)
      subtree = self.parse_type_name()
      tree.add( subtree )
      t = self.expect(1) # rparen
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen16(self):
    current = self.tokens.current()
    rule = self.table[18][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(137, self.nonterminals[137]))
    tree.list = False
    if current != None and (current.getId() in [57, 41, 34, 17, 63, 54, 53, 79, 38, 50, 78, 96, 26, 83, 4, 48, 22, 27, 28, 89, 72, 90, 91, 60, 93, 37, 47, 98, 52, 25, 71, 62, 115, 49, 114, 116, 80]):
      return tree
    if current == None:
      return tree
    if rule == 231:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_struct_or_union_body()
      tree.add( subtree )
      return tree
    return tree
  def parse__gen28(self):
    current = self.tokens.current()
    rule = self.table[19][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(138, self.nonterminals[138]))
    tree.list = 'nlist'
    if current != None and (current.getId() in [73, 2, 63, 80, 10, 99, 52, 12, 42, 15, 97, 19, 118, 117, 24, 108, 44]):
      return tree
    if current == None:
      return tree
    if rule == 243:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_direct_declarator_modifier()
      tree.add( subtree )
      subtree = self.parse__gen28()
      tree.add( subtree )
      return tree
    return tree
  def parse_constant(self):
    current = self.tokens.current()
    rule = self.table[20][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(139, self.nonterminals[139]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 48:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(117) # character_constant
      tree.add(t)
      return tree
    elif rule == 57:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(97) # hexadecimal_floating_constant
      tree.add(t)
      return tree
    elif rule == 68:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(24) # enumeration_constant
      tree.add(t)
      return tree
    elif rule == 207:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(99) # decimal_floating_constant
      tree.add(t)
      return tree
    elif rule == 294:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(10) # integer_constant
      tree.add(t)
      return tree
    elif rule == 358:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(15) # floating_constant
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen0(self):
    current = self.tokens.current()
    rule = self.table[21][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(140, self.nonterminals[140]))
    tree.list = 'nlist'
    if current != None and (current.getId() in [-1]):
      return tree
    if current == None:
      return tree
    if rule == 396:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_external_declaration()
      tree.add( subtree )
      subtree = self.parse__gen0()
      tree.add( subtree )
      return tree
    return tree
  def parse_enum_specifier_sub(self):
    current = self.tokens.current()
    rule = self.table[22][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(141, self.nonterminals[141]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 85:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_enum_specifier_body()
      tree.add( subtree )
      return tree
    elif rule == 306:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_identifier()
      tree.add( subtree )
      subtree = self.parse__gen22()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_storage_class_specifier(self):
    current = self.tokens.current()
    rule = self.table[23][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(142, self.nonterminals[142]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 58:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(115) # auto
      tree.add(t)
      return tree
    elif rule == 84:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(90) # static
      tree.add(t)
      return tree
    elif rule == 276:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(4) # register
      tree.add(t)
      return tree
    elif rule == 326:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(57) # typedef
      tree.add(t)
      return tree
    elif rule == 356:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(98) # extern
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_typedef_name(self):
    current = self.tokens.current()
    rule = self.table[24][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(143, self.nonterminals[143]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 220:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(54) # typedef_identifier
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen18(self):
    current = self.tokens.current()
    rule = self.table[25][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(144, self.nonterminals[144]))
    tree.list = 'nlist'
    if current != None and (current.getId() in [80, 28, 89, 63, 52]):
      return tree
    if current == None:
      return tree
    if rule == 262:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_specifier_qualifier()
      tree.add( subtree )
      subtree = self.parse__gen18()
      tree.add( subtree )
      return tree
    return tree
  def parse_identifier(self):
    current = self.tokens.current()
    rule = self.table[26][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(145, self.nonterminals[145]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 44:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(80) # identifier
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_enum_specifier_body(self):
    current = self.tokens.current()
    rule = self.table[27][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(146, self.nonterminals[146]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 12:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(94) # lbrace
      tree.add(t)
      subtree = self.parse__gen23()
      tree.add( subtree )
      subtree = self.parse_trailing_comma_opt()
      tree.add( subtree )
      t = self.expect(100) # rbrace
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen11(self):
    current = self.tokens.current()
    rule = self.table[28][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(147, self.nonterminals[147]))
    tree.list = False
    if current != None and (current.getId() in [27, 26]):
      return tree
    if current == None:
      return tree
    if rule == 134:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_declarator_initializer()
      tree.add( subtree )
      return tree
    return tree
  def parse_type_specifier(self):
    current = self.tokens.current()
    rule = self.table[29][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(148, self.nonterminals[148]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 16:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_typedef_name()
      tree.add( subtree )
      return tree
    elif rule == 75:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(41) # long
      tree.add(t)
      return tree
    elif rule == 96:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(53) # short
      tree.add(t)
      return tree
    elif rule == 150:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(48) # complex
      tree.add(t)
      return tree
    elif rule == 153:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_struct_specifier()
      tree.add( subtree )
      return tree
    elif rule == 198:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(72) # double
      tree.add(t)
      return tree
    elif rule == 206:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(79) # unsigned
      tree.add(t)
      return tree
    elif rule == 297:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(91) # imaginary
      tree.add(t)
      return tree
    elif rule == 301:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(60) # signed
      tree.add(t)
      return tree
    elif rule == 305:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(78) # bool
      tree.add(t)
      return tree
    elif rule == 308:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_union_specifier()
      tree.add( subtree )
      return tree
    elif rule == 316:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(49) # int
      tree.add(t)
      return tree
    elif rule == 341:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(114) # char
      tree.add(t)
      return tree
    elif rule == 346:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(62) # float
      tree.add(t)
      return tree
    elif rule == 352:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(96) # void
      tree.add(t)
      return tree
    elif rule == 375:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_enum_specifier()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_struct_declaration(self):
    current = self.tokens.current()
    rule = self.table[30][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(149, self.nonterminals[149]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 36:
      tree.astTransform = AstTransformNodeCreator('StructOrUnionDeclaration', {'specifier_qualifiers': 0, 'declarators': 1})
      subtree = self.parse__gen18()
      tree.add( subtree )
      subtree = self.parse__gen19()
      tree.add( subtree )
      t = self.expect(26) # semi
      tree.add(t)
      return tree
    elif current.getId() in [80, 89, 63]:
      tree.astTransform = AstTransformNodeCreator('StructOrUnionDeclaration', {'specifier_qualifiers': 0, 'declarators': 1})
      subtree = self.parse__gen18()
      tree.add( subtree )
      subtree = self.parse__gen19()
      tree.add( subtree )
      tree.add( self.expect(26) ) # semi
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_block_item_list(self):
    current = self.tokens.current()
    rule = self.table[31][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(150, self.nonterminals[150]))
    tree.list = False
    if current == None:
      return tree
    if rule == 281:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen40()
      tree.add( subtree )
      return tree
    elif current.getId() in [73, 2, 63, 80, 10, 99, 52, 12, 44, 15, 97, 19, 118, 117, 24, 108]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen40()
      tree.add( subtree )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen17(self):
    current = self.tokens.current()
    rule = self.table[32][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(151, self.nonterminals[151]))
    tree.list = 'nlist'
    if current != None and (current.getId() in [100]):
      return tree
    if current == None:
      return tree
    if rule == 258:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_struct_declaration()
      tree.add( subtree )
      subtree = self.parse__gen17()
      tree.add( subtree )
      return tree
    elif current.getId() in [80, 89, 63]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_struct_declaration()
      tree.add( subtree )
      subtree = self.parse__gen17()
      tree.add( subtree )
    return tree
  def parse_declaration(self):
    current = self.tokens.current()
    rule = self.table[33][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(152, self.nonterminals[152]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 412:
      tree.astTransform = AstTransformNodeCreator('Declaration', {'init_declarators': 1, 'declaration_specifiers': 0})
      subtree = self.parse__gen1()
      tree.add( subtree )
      subtree = self.parse__gen8()
      tree.add( subtree )
      t = self.expect(26) # semi
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_type_qualifier(self):
    current = self.tokens.current()
    rule = self.table[34][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(153, self.nonterminals[153]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 70:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(83) # volatile
      tree.add(t)
      return tree
    elif rule == 240:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(47) # restrict
      tree.add(t)
      return tree
    elif rule == 286:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(50) # const
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_misc(self):
    current = self.tokens.current()
    rule = self.table[35][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(154, self.nonterminals[154]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 225:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(105) # universal_character_name
      tree.add(t)
      return tree
    elif rule == 315:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(67) # endif
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_struct_specifier(self):
    current = self.tokens.current()
    rule = self.table[36][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(155, self.nonterminals[155]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 421:
      tree.astTransform = AstTransformNodeCreator('Struct', {'definition': 1})
      t = self.expect(38) # struct
      tree.add(t)
      subtree = self.parse_struct_or_union_sub()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_function_specifier(self):
    current = self.tokens.current()
    rule = self.table[37][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(156, self.nonterminals[156]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 275:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(34) # inline
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen39(self):
    current = self.tokens.current()
    rule = self.table[38][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(157, self.nonterminals[157]))
    tree.list = False
    if current != None and (current.getId() in [100]):
      return tree
    if current == None:
      return tree
    if rule == 10:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_block_item_list()
      tree.add( subtree )
      return tree
    elif current.getId() in [73, 2, 63, 80, 10, 99, 52, 12, 44, 15, 97, 19, 118, 117, 24, 108]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_block_item_list()
      tree.add( subtree )
    return tree
  def parse_else_if_statement_list(self):
    current = self.tokens.current()
    rule = self.table[39][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(158, self.nonterminals[158]))
    tree.list = False
    if current == None:
      return tree
    if rule == 147:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen43()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_type_qualifier_list_opt(self):
    current = self.tokens.current()
    rule = self.table[40][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(159, self.nonterminals[159]))
    tree.list = False
    if current != None and (current.getId() in [27, 52, 90, 17, 89, 63, 25, 80]):
      return tree
    if current == None:
      return tree
    if rule == 19:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen25()
      tree.add( subtree )
      return tree
    return tree
  def parse_specifier_qualifier(self):
    current = self.tokens.current()
    rule = self.table[41][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(160, self.nonterminals[160]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 273:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_type_specifier()
      tree.add( subtree )
      return tree
    elif rule == 426:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_type_qualifier()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen9(self):
    current = self.tokens.current()
    rule = self.table[42][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(161, self.nonterminals[161]))
    tree.list = 'slist'
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 67:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_init_declarator()
      tree.add( subtree )
      subtree = self.parse__gen10()
      tree.add( subtree )
      return tree
    elif current.getId() in [80, 89, 63]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_init_declarator()
      tree.add( subtree )
      subtree = self.parse__gen10()
      tree.add( subtree )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen24(self):
    current = self.tokens.current()
    rule = self.table[43][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(162, self.nonterminals[162]))
    tree.list = 'slist'
    if current != None and (current.getId() in [104]):
      return tree
    if current == None:
      return tree
    if rule == 267:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(27) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self.parse_enumerator()
      tree.add( subtree )
      subtree = self.parse__gen24()
      tree.add( subtree )
      return tree
    return tree
  def parse_translation_unit(self):
    current = self.tokens.current()
    rule = self.table[44][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(163, self.nonterminals[163]))
    tree.list = False
    if current == None:
      return tree
    if rule == 367:
      tree.astTransform = AstTransformNodeCreator('TranslationUnit', {'external_declarations': 0})
      subtree = self.parse__gen0()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_else_statement(self):
    current = self.tokens.current()
    rule = self.table[45][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(164, self.nonterminals[164]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 419:
      tree.astTransform = AstTransformNodeCreator('Else', {'statement': 1})
      t = self.expect(68) # else
      tree.add(t)
      subtree = self.parse_statement()
      tree.add( subtree )
      t = self.expect(67) # endif
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen42(self):
    current = self.tokens.current()
    rule = self.table[46][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(165, self.nonterminals[165]))
    tree.list = False
    if current != None and (current.getId() in [70, 2, 4, 54, 99, 10, 24, 12, 38, 87, 94, 108, 19, 26, 85, 15, 22, 52, 56, 83, 92, 34, 37, 47, 61, 41, 44, 62, 48, 49, 50, 53, 80, 57, 9, 60, 97, 63, 67, 79, 73, 78, 96, 118, 117, 115, 90, 91, 16, 98, 100, 29, 72, 110, 112, 113, 114]):
      return tree
    if current == None:
      return tree
    if rule == 51:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_else_statement()
      tree.add( subtree )
      return tree
    return tree
  def parse__gen22(self):
    current = self.tokens.current()
    rule = self.table[47][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(166, self.nonterminals[166]))
    tree.list = False
    if current != None and (current.getId() in [57, 41, 34, 17, 63, 54, 53, 79, 38, 50, 78, 96, 26, 83, 4, 48, 22, 27, 28, 89, 72, 90, 91, 60, 93, 37, 47, 98, 52, 25, 71, 62, 115, 49, 114, 116, 80]):
      return tree
    if current == None:
      return tree
    if rule == 242:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_enum_specifier_body()
      tree.add( subtree )
      return tree
    return tree
  def parse_struct_declarator(self):
    current = self.tokens.current()
    rule = self.table[48][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(167, self.nonterminals[167]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 79:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_struct_declarator_body()
      tree.add( subtree )
      return tree
    elif rule == 223:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_declarator()
      tree.add( subtree )
      subtree = self.parse__gen21()
      tree.add( subtree )
      return tree
    elif current.getId() in [80, 89, 63]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_declarator()
      tree.add( subtree )
      subtree = self.parse__gen21()
      tree.add( subtree )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen19(self):
    current = self.tokens.current()
    rule = self.table[49][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(168, self.nonterminals[168]))
    tree.list = 'slist'
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 277:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_struct_declarator()
      tree.add( subtree )
      subtree = self.parse__gen20()
      tree.add( subtree )
      return tree
    elif current.getId() in [80, 89, 63]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_struct_declarator()
      tree.add( subtree )
      subtree = self.parse__gen20()
      tree.add( subtree )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen20(self):
    current = self.tokens.current()
    rule = self.table[50][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(169, self.nonterminals[169]))
    tree.list = 'slist'
    if current != None and (current.getId() in [26]):
      return tree
    if current == None:
      return tree
    if rule == 107:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(27) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self.parse_struct_declarator()
      tree.add( subtree )
      subtree = self.parse__gen20()
      tree.add( subtree )
      return tree
    return tree
  def parse__gen10(self):
    current = self.tokens.current()
    rule = self.table[51][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(170, self.nonterminals[170]))
    tree.list = 'slist'
    if current != None and (current.getId() in [26]):
      return tree
    if current == None:
      return tree
    if rule == 72:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(27) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self.parse_init_declarator()
      tree.add( subtree )
      subtree = self.parse__gen10()
      tree.add( subtree )
      return tree
    return tree
  def parse_enumeration_constant(self):
    current = self.tokens.current()
    rule = self.table[52][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(171, self.nonterminals[171]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 90:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(80) # identifier
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen15(self):
    current = self.tokens.current()
    rule = self.table[53][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(172, self.nonterminals[172]))
    tree.list = 'nlist'
    if current != None and (current.getId() in [21]):
      return tree
    if current == None:
      return tree
    if rule == 278:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_designator()
      tree.add( subtree )
      subtree = self.parse__gen15()
      tree.add( subtree )
      return tree
    return tree
  def parse_punctuator(self):
    current = self.tokens.current()
    rule = self.table[54][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(173, self.nonterminals[173]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 1:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(103) # gt
      tree.add(t)
      return tree
    elif rule == 22:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(55) # neq
      tree.add(t)
      return tree
    elif rule == 25:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(59) # rshifteq
      tree.add(t)
      return tree
    elif rule == 28:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(19) # incr
      tree.add(t)
      return tree
    elif rule == 32:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(75) # bitxor
      tree.add(t)
      return tree
    elif rule == 40:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(8) # arrow
      tree.add(t)
      return tree
    elif rule == 47:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(106) # muleq
      tree.add(t)
      return tree
    elif rule == 53:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(46) # bitandeq
      tree.add(t)
      return tree
    elif rule == 64:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(69) # dot
      tree.add(t)
      return tree
    elif rule == 65:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(43) # bitor
      tree.add(t)
      return tree
    elif rule == 77:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(45) # eq
      tree.add(t)
      return tree
    elif rule == 114:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(100) # rbrace
      tree.add(t)
      return tree
    elif rule == 128:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(1) # rparen
      tree.add(t)
      return tree
    elif rule == 130:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(51) # lshifteq
      tree.add(t)
      return tree
    elif rule == 145:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(65) # rshift
      tree.add(t)
      return tree
    elif rule == 152:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(26) # semi
      tree.add(t)
      return tree
    elif rule == 157:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(111) # div
      tree.add(t)
      return tree
    elif rule == 162:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(27) # comma
      tree.add(t)
      return tree
    elif rule == 177:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(32) # ampersand
      tree.add(t)
      return tree
    elif rule == 189:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(14) # elipsis
      tree.add(t)
      return tree
    elif rule == 192:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(101) # lshift
      tree.add(t)
      return tree
    elif rule == 199:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(58) # or
      tree.add(t)
      return tree
    elif rule == 201:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(81) # gteq
      tree.add(t)
      return tree
    elif rule == 208:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(74) # lteq
      tree.add(t)
      return tree
    elif rule == 214:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(107) # add
      tree.add(t)
      return tree
    elif rule == 241:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(6) # pound
      tree.add(t)
      return tree
    elif rule == 244:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(84) # modeq
      tree.add(t)
      return tree
    elif rule == 250:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(35) # and
      tree.add(t)
      return tree
    elif rule == 251:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(109) # exclamation_point
      tree.add(t)
      return tree
    elif rule == 261:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(12) # decr
      tree.add(t)
      return tree
    elif rule == 269:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(11) # mod
      tree.add(t)
      return tree
    elif rule == 270:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(36) # tilde
      tree.add(t)
      return tree
    elif rule == 287:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(40) # bitxoreq
      tree.add(t)
      return tree
    elif rule == 288:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(31) # bitoreq
      tree.add(t)
      return tree
    elif rule == 292:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(66) # lsquare
      tree.add(t)
      return tree
    elif rule == 300:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(76) # addeq
      tree.add(t)
      return tree
    elif rule == 312:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(28) # colon
      tree.add(t)
      return tree
    elif rule == 329:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(88) # lt
      tree.add(t)
      return tree
    elif rule == 354:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(30) # subeq
      tree.add(t)
      return tree
    elif rule == 362:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(77) # rsquare
      tree.add(t)
      return tree
    elif rule == 366:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(39) # questionmark
      tree.add(t)
      return tree
    elif rule == 370:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(20) # poundpound
      tree.add(t)
      return tree
    elif rule == 374:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(21) # assign
      tree.add(t)
      return tree
    elif rule == 391:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(18) # sub
      tree.add(t)
      return tree
    elif rule == 411:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(94) # lbrace
      tree.add(t)
      return tree
    elif rule == 415:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(63) # lparen
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen43(self):
    current = self.tokens.current()
    rule = self.table[55][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(174, self.nonterminals[174]))
    tree.list = 'nlist'
    if current != None and (current.getId() in [70, 2, 4, 54, 99, 68, 24, 12, 38, 87, 94, 108, 19, 26, 85, 15, 22, 52, 56, 83, 92, 34, 37, 47, 61, 41, 44, 62, 48, 49, 50, 53, 80, 57, 9, 60, 97, 63, 67, 10, 79, 73, 78, 96, 118, 117, 115, 90, 91, 16, 98, 100, 29, 72, 110, 112, 113, 114]):
      return tree
    if current == None:
      return tree
    if rule == 142:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_else_if_statement()
      tree.add( subtree )
      subtree = self.parse__gen43()
      tree.add( subtree )
      return tree
    return tree
  def parse__gen27(self):
    current = self.tokens.current()
    rule = self.table[56][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(175, self.nonterminals[175]))
    tree.list = False
    if current != None and (current.getId() in [73, 2, 63, 52, 80, 10, 99, 44, 12, 42, 15, 97, 19, 118, 117, 24, 108]):
      return tree
    if current == None:
      return tree
    if rule == 408:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_direct_declarator_modifier_list()
      tree.add( subtree )
      return tree
    return tree
  def parse_external_declarator(self):
    current = self.tokens.current()
    rule = self.table[57][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(176, self.nonterminals[176]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 382:
      tree.astTransform = AstTransformNodeCreator('ExternalDeclarator', {'init_declarator': 1})
      t = self.expect(93) # declarator_hint
      tree.add(t)
      subtree = self.parse__gen6()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_else_if_statement(self):
    current = self.tokens.current()
    rule = self.table[58][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(177, self.nonterminals[177]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 165:
      tree.astTransform = AstTransformNodeCreator('ElseIf', {'statement': 4, 'condition': 2})
      t = self.expect(23) # else_if
      tree.add(t)
      t = self.expect(63) # lparen
      tree.add(t)
      subtree = self.parse__expr()
      tree.add( subtree )
      t = self.expect(1) # rparen
      tree.add(t)
      subtree = self.parse_statement()
      tree.add( subtree )
      t = self.expect(67) # endif
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_init_declarator(self):
    current = self.tokens.current()
    rule = self.table[59][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(178, self.nonterminals[178]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 137:
      tree.astTransform = AstTransformNodeCreator('InitDeclarator', {'initializer': 1, 'declarator': 0})
      subtree = self.parse_declarator()
      tree.add( subtree )
      subtree = self.parse__gen11()
      tree.add( subtree )
      return tree
    elif current.getId() in [80, 89, 63]:
      tree.astTransform = AstTransformNodeCreator('InitDeclarator', {'initializer': 1, 'declarator': 0})
      subtree = self.parse_declarator()
      tree.add( subtree )
      subtree = self.parse__gen11()
      tree.add( subtree )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_parameter_type_list(self):
    current = self.tokens.current()
    rule = self.table[60][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(179, self.nonterminals[179]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 236:
      tree.astTransform = AstTransformNodeCreator('ParameterTypeList', {'parameter_declarations': 0, 'va_args': 1})
      subtree = self.parse__gen29()
      tree.add( subtree )
      subtree = self.parse__gen31()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_initializer(self):
    current = self.tokens.current()
    rule = self.table[61][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(180, self.nonterminals[180]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 309:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__expr_sans_comma()
      tree.add( subtree )
      return tree
    elif rule == 317:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(94) # lbrace
      tree.add(t)
      subtree = self.parse__gen12()
      tree.add( subtree )
      subtree = self.parse_trailing_comma_opt()
      tree.add( subtree )
      t = self.expect(100) # rbrace
      tree.add(t)
      return tree
    elif current.getId() in [33, 63, 80, 10, 99, 44, 12, 52, 15, 97, 19, 118, 2, 24, 108, 117]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__expr_sans_comma()
      tree.add( subtree )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_designation(self):
    current = self.tokens.current()
    rule = self.table[62][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(181, self.nonterminals[181]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 365:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen15()
      tree.add( subtree )
      t = self.expect(21) # assign
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_initializer_list_item(self):
    current = self.tokens.current()
    rule = self.table[63][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(182, self.nonterminals[182]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 126:
      tree.astTransform = AstTransformNodeCreator('Initialization', {'designation': 0, 'initializer': 1})
      subtree = self.parse__gen14()
      tree.add( subtree )
      subtree = self.parse_initializer()
      tree.add( subtree )
      return tree
    elif current.getId() in [33, 63, 80, 10, 99, 44, 12, 52, 15, 97, 19, 118, 2, 24, 108, 117]:
      tree.astTransform = AstTransformNodeCreator('Initialization', {'designation': 0, 'initializer': 1})
      subtree = self.parse__gen14()
      tree.add( subtree )
      subtree = self.parse_initializer()
      tree.add( subtree )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_external_declaration_sub(self):
    current = self.tokens.current()
    rule = self.table[64][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(183, self.nonterminals[183]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 93:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen3()
      tree.add( subtree )
      t = self.expect(26) # semi
      tree.add(t)
      return tree
    elif rule == 298:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_external_function()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_declarator_initializer(self):
    current = self.tokens.current()
    rule = self.table[65][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(184, self.nonterminals[184]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 158:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(21) # assign
      tree.add(t)
      subtree = self.parse_initializer()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_external_function(self):
    current = self.tokens.current()
    rule = self.table[67][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(186, self.nonterminals[186]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 377:
      tree.astTransform = AstTransformNodeCreator('FunctionDefinition', {'body': 3, 'declaration_list': 2, 'signature': 1})
      t = self.expect(71) # function_definition_hint
      tree.add(t)
      subtree = self.parse_declarator()
      tree.add( subtree )
      subtree = self.parse__gen5()
      tree.add( subtree )
      subtree = self.parse_compound_statement()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_expression_opt(self):
    current = self.tokens.current()
    rule = self.table[68][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(187, self.nonterminals[187]))
    tree.list = False
    if current != None and (current.getId() in [1, 26]):
      return tree
    if current == None:
      return tree
    if rule == 227:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__expr()
      tree.add( subtree )
      return tree
    elif current.getId() in [73, 2, 63, 80, 10, 99, 52, 12, 44, 15, 97, 19, 118, 117, 24, 108]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__expr()
      tree.add( subtree )
    return tree
  def parse_direct_abstract_declarator_expr(self):
    current = self.tokens.current()
    rule = self.table[69][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(188, self.nonterminals[188]))
    tree.list = False
    if current != None and (current.getId() in []):
      return tree
    if current == None:
      return tree
    if rule == 49:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_type_qualifier_list_opt()
      tree.add( subtree )
      subtree = self.parse_static_opt()
      tree.add( subtree )
      subtree = self.parse__expr()
      tree.add( subtree )
      return tree
    elif rule == 94:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(42) # variable_length_array
      tree.add(t)
      return tree
    elif current.getId() in [73, 2, 63, 80, 10, 99, 52, 12, 44, 15, 97, 19, 118, 117, 24, 108]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_type_qualifier_list_opt()
      tree.add( subtree )
      subtree = self.parse_static_opt()
      tree.add( subtree )
      subtree = self.parse__expr()
      tree.add( subtree )
    return tree
  def parse_enumerator_assignment(self):
    current = self.tokens.current()
    rule = self.table[70][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(189, self.nonterminals[189]))
    tree.list = False
    if current != None and (current.getId() in [27, 104]):
      return tree
    if current == None:
      return tree
    if rule == 41:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(21) # assign
      tree.add(t)
      subtree = self.parse__expr()
      tree.add( subtree )
      return tree
    return tree
  def parse__gen12(self):
    current = self.tokens.current()
    rule = self.table[71][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(190, self.nonterminals[190]))
    tree.list = 'slist'
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 332:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_initializer_list_item()
      tree.add( subtree )
      subtree = self.parse__gen13()
      tree.add( subtree )
      return tree
    elif current.getId() in [33, 63, 80, 10, 99, 44, 12, 52, 15, 97, 19, 118, 2, 24, 108, 117]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_initializer_list_item()
      tree.add( subtree )
      subtree = self.parse__gen13()
      tree.add( subtree )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen13(self):
    current = self.tokens.current()
    rule = self.table[72][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(191, self.nonterminals[191]))
    tree.list = 'slist'
    if current != None and (current.getId() in [104]):
      return tree
    if current == None:
      return tree
    if rule == 336:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(27) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self.parse_initializer_list_item()
      tree.add( subtree )
      subtree = self.parse__gen13()
      tree.add( subtree )
      return tree
    return tree
  def parse_external_declaration_sub_sub(self):
    current = self.tokens.current()
    rule = self.table[73][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(192, self.nonterminals[192]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 202:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_external_declarator()
      tree.add( subtree )
      return tree
    elif rule == 224:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_external_prototype()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_named_parameter_declaration(self):
    current = self.tokens.current()
    rule = self.table[74][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(193, self.nonterminals[193]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 290:
      tree.astTransform = AstTransformNodeCreator('NamedParameter', {'declaration_specifiers': 1, 'declarator': 2})
      t = self.expect(95) # named_parameter_hint
      tree.add(t)
      subtree = self.parse__gen1()
      tree.add( subtree )
      subtree = self.parse__gen34()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen3(self):
    current = self.tokens.current()
    rule = self.table[75][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(194, self.nonterminals[194]))
    tree.list = 'slist'
    if current != None and (current.getId() in [26]):
      return tree
    if current == None:
      return tree
    if rule == 260:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_external_declaration_sub_sub()
      tree.add( subtree )
      subtree = self.parse__gen4()
      tree.add( subtree )
      return tree
    return tree
  def parse_designator(self):
    current = self.tokens.current()
    rule = self.table[76][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(195, self.nonterminals[195]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 13:
      tree.astTransform = AstTransformNodeCreator('MemberAccess', {'name': 1})
      t = self.expect(69) # dot
      tree.add(t)
      t = self.expect(80) # identifier
      tree.add(t)
      return tree
    elif rule == 334:
      tree.astTransform = AstTransformNodeCreator('ArrayAccess', {'index': 1})
      t = self.expect(66) # lsquare
      tree.add(t)
      subtree = self.parse__expr()
      tree.add( subtree )
      t = self.expect(77) # rsquare
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen4(self):
    current = self.tokens.current()
    rule = self.table[77][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(196, self.nonterminals[196]))
    tree.list = 'slist'
    if current != None and (current.getId() in [26]):
      return tree
    if current == None:
      return tree
    if rule == 347:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(27) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self.parse_external_declaration_sub_sub()
      tree.add( subtree )
      subtree = self.parse__gen4()
      tree.add( subtree )
      return tree
    return tree
  def parse__gen14(self):
    current = self.tokens.current()
    rule = self.table[78][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(197, self.nonterminals[197]))
    tree.list = False
    if current != None and (current.getId() in [15, 33, 63, 80, 10, 99, 44, 12, 52, 94, 97, 19, 118, 2, 24, 108, 117]):
      return tree
    if current == None:
      return tree
    if rule == 299:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_designation()
      tree.add( subtree )
      return tree
    return tree
  def parse_direct_declarator_parameter_list(self):
    current = self.tokens.current()
    rule = self.table[79][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(198, self.nonterminals[198]))
    tree.list = False
    if current != None and (current.getId() in []):
      return tree
    if current == None:
      return tree
    if rule == 182:
      tree.astTransform = AstTransformNodeCreator('ParameterList', {'identifiers': 0})
      subtree = self.parse__gen32()
      tree.add( subtree )
      return tree
    elif rule == 379:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_parameter_type_list()
      tree.add( subtree )
      return tree
    return tree
  def parse_abstract_parameter_declaration(self):
    current = self.tokens.current()
    rule = self.table[80][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(199, self.nonterminals[199]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 3:
      tree.astTransform = AstTransformNodeCreator('AbstractParameter', {'declaration_specifiers': 1, 'declarator': 2})
      t = self.expect(64) # abstract_parameter_hint
      tree.add(t)
      subtree = self.parse__gen1()
      tree.add( subtree )
      subtree = self.parse__gen35()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_trailing_comma_opt(self):
    current = self.tokens.current()
    rule = self.table[81][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(200, self.nonterminals[200]))
    tree.list = False
    if current != None and (current.getId() in [100]):
      return tree
    if current == None:
      return tree
    if rule == 9:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(104) # trailing_comma
      tree.add(t)
      return tree
    return tree
  def parse__gen25(self):
    current = self.tokens.current()
    rule = self.table[82][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(201, self.nonterminals[201]))
    tree.list = 'nlist'
    if current != None and (current.getId() in [27, 52, 90, 17, 89, 63, 25, 80]):
      return tree
    if current == None:
      return tree
    if rule == 26:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_type_qualifier()
      tree.add( subtree )
      subtree = self.parse__gen25()
      tree.add( subtree )
      return tree
    return tree
  def parse_statement(self):
    current = self.tokens.current()
    rule = self.table[83][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(202, self.nonterminals[202]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 89:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_compound_statement()
      tree.add( subtree )
      return tree
    elif rule == 151:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_jump_statement()
      tree.add( subtree )
      return tree
    elif rule == 166:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_selection_statement()
      tree.add( subtree )
      return tree
    elif rule == 218:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_expression_statement()
      tree.add( subtree )
      return tree
    elif rule == 264:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_iteration_statement()
      tree.add( subtree )
      return tree
    elif rule == 265:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_labeled_statement()
      tree.add( subtree )
      return tree
    elif current.getId() in [73, 2, 63, 80, 10, 99, 52, 12, 44, 15, 97, 19, 118, 117, 24, 108]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_expression_statement()
      tree.add( subtree )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_for_cond(self):
    current = self.tokens.current()
    rule = self.table[84][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(203, self.nonterminals[203]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 172:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(26) # semi
      tree.add(t)
      subtree = self.parse_expression_opt()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_for_incr(self):
    current = self.tokens.current()
    rule = self.table[85][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(204, self.nonterminals[204]))
    tree.list = False
    if current != None and (current.getId() in [1]):
      return tree
    if current == None:
      return tree
    if rule == 179:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(26) # semi
      tree.add(t)
      subtree = self.parse_expression_opt()
      tree.add( subtree )
      return tree
    return tree
  def parse__gen34(self):
    current = self.tokens.current()
    rule = self.table[86][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(205, self.nonterminals[205]))
    tree.list = False
    if current != None and (current.getId() in [27, 17]):
      return tree
    if current == None:
      return tree
    if rule == 61:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_declarator()
      tree.add( subtree )
      return tree
    elif current.getId() in [80, 89, 63]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_declarator()
      tree.add( subtree )
    return tree
  def parse__gen46(self):
    current = self.tokens.current()
    rule = self.table[87][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(206, self.nonterminals[206]))
    tree.list = False
    if current != None and (current.getId() in []):
      return tree
    if current == None:
      return tree
    if rule == 235:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_parameter_type_list()
      tree.add( subtree )
      return tree
    return tree
  def parse_static_opt(self):
    current = self.tokens.current()
    rule = self.table[88][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(207, self.nonterminals[207]))
    tree.list = False
    if current != None and (current.getId() in [73, 2, 63, 80, 10, 99, 52, 12, 44, 15, 97, 19, 118, 117, 24, 108]):
      return tree
    if current == None:
      return tree
    if rule == 209:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(90) # static
      tree.add(t)
      return tree
    return tree
  def parse__gen41(self):
    current = self.tokens.current()
    rule = self.table[89][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(208, self.nonterminals[208]))
    tree.list = False
    if current != None and (current.getId() in [70, 2, 4, 54, 99, 68, 24, 12, 38, 94, 108, 19, 26, 85, 15, 22, 52, 56, 83, 92, 34, 37, 47, 61, 41, 44, 62, 87, 49, 53, 80, 57, 9, 60, 97, 63, 67, 10, 115, 79, 73, 78, 96, 118, 117, 48, 90, 91, 16, 98, 100, 29, 113, 72, 110, 112, 50, 114]):
      return tree
    if current == None:
      return tree
    if rule == 234:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_else_if_statement_list()
      tree.add( subtree )
      return tree
    return tree
  def parse_parameter_declaration(self):
    current = self.tokens.current()
    rule = self.table[90][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(209, self.nonterminals[209]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 141:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_abstract_parameter_declaration()
      tree.add( subtree )
      return tree
    elif rule == 387:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_named_parameter_declaration()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_declaration_specifier(self):
    current = self.tokens.current()
    rule = self.table[91][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(210, self.nonterminals[210]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 24:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_function_specifier()
      tree.add( subtree )
      return tree
    elif rule == 167:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_type_qualifier()
      tree.add( subtree )
      return tree
    elif rule == 186:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_type_specifier()
      tree.add( subtree )
      return tree
    elif rule == 350:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_storage_class_specifier()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen29(self):
    current = self.tokens.current()
    rule = self.table[92][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(211, self.nonterminals[211]))
    tree.list = 'slist'
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 109:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_parameter_declaration()
      tree.add( subtree )
      subtree = self.parse__gen30()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen30(self):
    current = self.tokens.current()
    rule = self.table[93][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(212, self.nonterminals[212]))
    tree.list = 'slist'
    if current != None and (current.getId() in [17]):
      return tree
    if current == None:
      return tree
    if rule == 149:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(27) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self.parse_parameter_declaration()
      tree.add( subtree )
      subtree = self.parse__gen30()
      tree.add( subtree )
      return tree
    return tree
  def parse_direct_declarator_expr(self):
    current = self.tokens.current()
    rule = self.table[94][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(213, self.nonterminals[213]))
    tree.list = False
    if current != None and (current.getId() in []):
      return tree
    if current == None:
      return tree
    if rule == 99:
      tree.astTransform = AstTransformNodeCreator('DirectDeclaratorExpression', {'modifiers': 0, 'value': 1})
      subtree = self.parse__gen27()
      tree.add( subtree )
      subtree = self.parse_direct_declarator_size()
      tree.add( subtree )
      return tree
    elif current.getId() in [73, 2, 63, 80, 10, 99, 52, 12, 44, 15, 97, 19, 118, 117, 24, 108]:
      tree.astTransform = AstTransformNodeCreator('DirectDeclaratorExpression', {'modifiers': 0, 'value': 1})
      subtree = self.parse__gen27()
      tree.add( subtree )
      subtree = self.parse_direct_declarator_size()
      tree.add( subtree )
    return tree
  def parse__gen40(self):
    current = self.tokens.current()
    rule = self.table[95][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(214, self.nonterminals[214]))
    tree.list = 'nlist'
    if current != None and (current.getId() in [100]):
      return tree
    if current == None:
      return tree
    if rule == 27:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_block_item()
      tree.add( subtree )
      subtree = self.parse__gen40()
      tree.add( subtree )
      return tree
    elif current.getId() in [73, 2, 63, 80, 10, 99, 52, 12, 44, 15, 97, 19, 118, 117, 24, 108]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_block_item()
      tree.add( subtree )
      subtree = self.parse__gen40()
      tree.add( subtree )
    return tree
  def parse_labeled_statement(self):
    current = self.tokens.current()
    rule = self.table[96][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(215, self.nonterminals[215]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 8:
      tree.astTransform = AstTransformNodeCreator('DefaultCase', {'statement': 2})
      t = self.expect(70) # default
      tree.add(t)
      t = self.expect(28) # colon
      tree.add(t)
      subtree = self.parse_statement()
      tree.add( subtree )
      return tree
    elif rule == 369:
      tree.astTransform = AstTransformNodeCreator('Label', {'name': 0, 'statement': 1})
      t = self.expect(29) # label_hint
      tree.add(t)
      t = self.expect(80) # identifier
      tree.add(t)
      t = self.expect(28) # colon
      tree.add(t)
      subtree = self.parse_statement()
      tree.add( subtree )
      return tree
    elif rule == 383:
      tree.astTransform = AstTransformNodeCreator('Case', {'expr': 1, 'statement': 3})
      t = self.expect(112) # case
      tree.add(t)
      subtree = self.parse__expr()
      tree.add( subtree )
      t = self.expect(28) # colon
      tree.add(t)
      subtree = self.parse_statement()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_external_prototype(self):
    current = self.tokens.current()
    rule = self.table[97][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(216, self.nonterminals[216]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 335:
      tree.astTransform = AstTransformNodeCreator('FunctionPrototype', {'declaration_list': 2, 'declarator': 1})
      t = self.expect(116) # function_prototype_hint
      tree.add(t)
      subtree = self.parse_declarator()
      tree.add( subtree )
      subtree = self.parse__gen5()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_union_specifier(self):
    current = self.tokens.current()
    rule = self.table[98][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(217, self.nonterminals[217]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 424:
      tree.astTransform = AstTransformNodeCreator('Union', {'definition': 1})
      t = self.expect(22) # union
      tree.add(t)
      subtree = self.parse_struct_or_union_sub()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_abstract_declarator(self):
    current = self.tokens.current()
    rule = self.table[99][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(218, self.nonterminals[218]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 173:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_pointer()
      tree.add( subtree )
      subtree = self.parse__gen36()
      tree.add( subtree )
      return tree
    elif rule == 237:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__direct_abstract_declarator()
      tree.add( subtree )
      return tree
    elif current.getId() in [25, 63]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__direct_abstract_declarator()
      tree.add( subtree )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_pointer(self):
    current = self.tokens.current()
    rule = self.table[100][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(219, self.nonterminals[219]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 215:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen37()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen35(self):
    current = self.tokens.current()
    rule = self.table[101][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(220, self.nonterminals[220]))
    tree.list = False
    if current != None and (current.getId() in [27, 17]):
      return tree
    if current == None:
      return tree
    if rule == 171:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_abstract_declarator()
      tree.add( subtree )
      return tree
    elif current.getId() in [25, 63]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_abstract_declarator()
      tree.add( subtree )
    return tree
  def parse_va_args(self):
    current = self.tokens.current()
    rule = self.table[102][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(221, self.nonterminals[221]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 403:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(17) # comma_va_args
      tree.add(t)
      t = self.expect(14) # elipsis
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_declarator(self):
    current = self.tokens.current()
    rule = self.table[103][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(222, self.nonterminals[222]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 122:
      tree.astTransform = AstTransformNodeCreator('Declarator', {'direct_declarator': 1, 'pointer': 0})
      subtree = self.parse__gen26()
      tree.add( subtree )
      subtree = self.parse__direct_declarator()
      tree.add( subtree )
      return tree
    elif current.getId() in [80, 89, 63]:
      tree.astTransform = AstTransformNodeCreator('Declarator', {'direct_declarator': 1, 'pointer': 0})
      subtree = self.parse__gen26()
      tree.add( subtree )
      subtree = self.parse__direct_declarator()
      tree.add( subtree )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_expression_statement(self):
    current = self.tokens.current()
    rule = self.table[104][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(223, self.nonterminals[223]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 285:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_expression_opt()
      tree.add( subtree )
      t = self.expect(26) # semi
      tree.add(t)
      return tree
    elif current.getId() in [73, 2, 63, 80, 10, 99, 52, 12, 44, 15, 97, 19, 118, 117, 24, 108]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_expression_opt()
      tree.add( subtree )
      tree.add( self.expect(26) ) # semi
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_pointer_sub(self):
    current = self.tokens.current()
    rule = self.table[105][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(224, self.nonterminals[224]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 321:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(52) # asterisk
      tree.add(t)
      subtree = self.parse_type_qualifier_list_opt()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen5(self):
    current = self.tokens.current()
    rule = self.table[106][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(225, self.nonterminals[225]))
    tree.list = False
    if current != None and (current.getId() in [94, 26, 27]):
      return tree
    if current == None:
      return tree
    if rule == 302:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_declaration_list()
      tree.add( subtree )
      return tree
    return tree
  def parse__gen26(self):
    current = self.tokens.current()
    rule = self.table[107][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(226, self.nonterminals[226]))
    tree.list = False
    if current != None and (current.getId() in [63, 89, 80]):
      return tree
    if current == None:
      return tree
    if rule == 385:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_pointer()
      tree.add( subtree )
      return tree
    return tree
  def parse_selection_statement(self):
    current = self.tokens.current()
    rule = self.table[108][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(227, self.nonterminals[227]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 169:
      tree.astTransform = AstTransformNodeCreator('Switch', {'expr': 2, 'statment': 4})
      t = self.expect(113) # switch
      tree.add(t)
      t = self.expect(63) # lparen
      tree.add(t)
      subtree = self.parse__expr()
      tree.add( subtree )
      t = self.expect(1) # rparen
      tree.add(t)
      subtree = self.parse_statement()
      tree.add( subtree )
      return tree
    elif rule == 423:
      tree.astTransform = AstTransformNodeCreator('If', {'elseif': 6, 'statement': 4, 'condition': 2, 'else': 7})
      t = self.expect(9) # if
      tree.add(t)
      t = self.expect(63) # lparen
      tree.add(t)
      subtree = self.parse__expr()
      tree.add( subtree )
      t = self.expect(1) # rparen
      tree.add(t)
      subtree = self.parse_statement()
      tree.add( subtree )
      t = self.expect(67) # endif
      tree.add(t)
      subtree = self.parse__gen41()
      tree.add( subtree )
      subtree = self.parse__gen42()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_compound_statement(self):
    current = self.tokens.current()
    rule = self.table[110][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(229, self.nonterminals[229]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 175:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(94) # lbrace
      tree.add(t)
      subtree = self.parse__gen39()
      tree.add( subtree )
      t = self.expect(100) # rbrace
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_iteration_statement(self):
    current = self.tokens.current()
    rule = self.table[111][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(230, self.nonterminals[230]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 256:
      tree.astTransform = AstTransformNodeCreator('For', {'init': 2, 'cond': 3, 'incr': 4, 'statement': 6})
      t = self.expect(61) # for
      tree.add(t)
      t = self.expect(63) # lparen
      tree.add(t)
      subtree = self.parse_for_init()
      tree.add( subtree )
      subtree = self.parse_for_cond()
      tree.add( subtree )
      subtree = self.parse_for_incr()
      tree.add( subtree )
      t = self.expect(1) # rparen
      tree.add(t)
      subtree = self.parse_statement()
      tree.add( subtree )
      return tree
    elif rule == 283:
      tree.astTransform = AstTransformNodeCreator('While', {'expr': 2, 'statement': 4})
      t = self.expect(85) # while
      tree.add(t)
      t = self.expect(63) # lparen
      tree.add(t)
      subtree = self.parse__expr()
      tree.add( subtree )
      t = self.expect(1) # rparen
      tree.add(t)
      subtree = self.parse_statement()
      tree.add( subtree )
      return tree
    elif rule == 388:
      tree.astTransform = AstTransformNodeCreator('DoWhile', {'expr': 4, 'statement': 1})
      t = self.expect(92) # do
      tree.add(t)
      subtree = self.parse_statement()
      tree.add( subtree )
      t = self.expect(85) # while
      tree.add(t)
      t = self.expect(63) # lparen
      tree.add(t)
      subtree = self.parse__expr()
      tree.add( subtree )
      t = self.expect(1) # rparen
      tree.add(t)
      t = self.expect(26) # semi
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen31(self):
    current = self.tokens.current()
    rule = self.table[112][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(231, self.nonterminals[231]))
    tree.list = False
    if current != None and (current.getId() in []):
      return tree
    if current == None:
      return tree
    if rule == 159:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_va_args()
      tree.add( subtree )
      return tree
    return tree
  def parse__gen36(self):
    current = self.tokens.current()
    rule = self.table[113][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(232, self.nonterminals[232]))
    tree.list = False
    if current != None and (current.getId() in [27, 17]):
      return tree
    if current == None:
      return tree
    if rule == 404:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__direct_abstract_declarator()
      tree.add( subtree )
      return tree
    elif current.getId() in [25, 63]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__direct_abstract_declarator()
      tree.add( subtree )
    return tree
  def parse_direct_declarator_modifier_list(self):
    current = self.tokens.current()
    rule = self.table[114][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(233, self.nonterminals[233]))
    tree.list = False
    if current != None and (current.getId() in [73, 2, 63, 80, 99, 10, 52, 12, 42, 15, 97, 19, 118, 117, 24, 108, 44]):
      return tree
    if current == None:
      return tree
    if rule == 272:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen28()
      tree.add( subtree )
      return tree
    return tree
  def parse_jump_statement(self):
    current = self.tokens.current()
    rule = self.table[115][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(234, self.nonterminals[234]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 118:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(16) # continue
      tree.add(t)
      return tree
    elif rule == 156:
      tree.astTransform = AstTransformNodeCreator('Return', {'expr': 1})
      t = self.expect(110) # return
      tree.add(t)
      subtree = self.parse_expression_opt()
      tree.add( subtree )
      t = self.expect(26) # semi
      tree.add(t)
      return tree
    elif rule == 254:
      tree.astTransform = AstTransformNodeCreator('Goto', {'name': 1})
      t = self.expect(87) # goto
      tree.add(t)
      t = self.expect(80) # identifier
      tree.add(t)
      t = self.expect(26) # semi
      tree.add(t)
      return tree
    elif rule == 311:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(56) # break
      tree.add(t)
      t = self.expect(26) # semi
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_token(self):
    current = self.tokens.current()
    rule = self.table[116][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(235, self.nonterminals[235]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 0:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_keyword()
      tree.add( subtree )
      return tree
    elif rule == 100:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_constant()
      tree.add( subtree )
      return tree
    elif rule == 102:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_punctuator()
      tree.add( subtree )
      return tree
    elif rule == 131:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(13) # pp_number
      tree.add(t)
      return tree
    elif rule == 345:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(80) # identifier
      tree.add(t)
      return tree
    elif rule == 392:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(44) # string_literal
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen38(self):
    current = self.tokens.current()
    rule = self.table[117][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(236, self.nonterminals[236]))
    tree.list = 'mlist'
    if current != None and (current.getId() in [27, 17, 89, 63, 25, 80]):
      return tree
    if current == None:
      return tree
    if rule == 104:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_pointer_sub()
      tree.add( subtree )
      subtree = self.parse__gen38()
      tree.add( subtree )
      return tree
    return tree
  def parse__gen32(self):
    current = self.tokens.current()
    rule = self.table[118][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(237, self.nonterminals[237]))
    tree.list = 'slist'
    if current != None and (current.getId() in []):
      return tree
    if current == None:
      return tree
    if rule == 349:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_identifier()
      tree.add( subtree )
      subtree = self.parse__gen33()
      tree.add( subtree )
      return tree
    return tree
  def parse_declaration_list(self):
    current = self.tokens.current()
    rule = self.table[119][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(238, self.nonterminals[238]))
    tree.list = False
    if current == None:
      return tree
    if rule == 280:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen7()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen33(self):
    current = self.tokens.current()
    rule = self.table[120][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(239, self.nonterminals[239]))
    tree.list = 'slist'
    if current != None and (current.getId() in []):
      return tree
    if current == None:
      return tree
    if rule == 184:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(27) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self.parse_identifier()
      tree.add( subtree )
      subtree = self.parse__gen33()
      tree.add( subtree )
      return tree
    return tree
  def parse_enumerator(self):
    current = self.tokens.current()
    rule = self.table[121][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(240, self.nonterminals[240]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 111:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_enumeration_constant()
      tree.add( subtree )
      subtree = self.parse_enumerator_assignment()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_pp(self):
    current = self.tokens.current()
    rule = self.table[122][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(241, self.nonterminals[241]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 247:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(13) # pp_number
      tree.add(t)
      return tree
    elif rule == 364:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(7) # defined_separator
      tree.add(t)
      return tree
    elif rule == 386:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(86) # defined
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen1(self):
    current = self.tokens.current()
    rule = self.table[123][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(242, self.nonterminals[242]))
    tree.list = 'mlist'
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 140:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_declaration_specifier()
      tree.add( subtree )
      subtree = self.parse__gen2()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen2(self):
    current = self.tokens.current()
    rule = self.table[124][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(243, self.nonterminals[243]))
    tree.list = 'mlist'
    if current != None and (current.getId() in [27, 52, 89, 25, 116, 63, 17, 93, 26, 71, 80]):
      return tree
    if current == None:
      return tree
    if rule == 303:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_declaration_specifier()
      tree.add( subtree )
      subtree = self.parse__gen2()
      tree.add( subtree )
      return tree
    return tree
  def parse__gen6(self):
    current = self.tokens.current()
    rule = self.table[125][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(244, self.nonterminals[244]))
    tree.list = False
    if current != None and (current.getId() in [27, 26]):
      return tree
    if current == None:
      return tree
    if rule == 337:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_init_declarator()
      tree.add( subtree )
      return tree
    elif current.getId() in [80, 89, 63]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_init_declarator()
      tree.add( subtree )
    return tree
  def parse__gen37(self):
    current = self.tokens.current()
    rule = self.table[126][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(245, self.nonterminals[245]))
    tree.list = 'mlist'
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 205:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_pointer_sub()
      tree.add( subtree )
      subtree = self.parse__gen38()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen23(self):
    current = self.tokens.current()
    rule = self.table[127][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(246, self.nonterminals[246]))
    tree.list = 'slist'
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 420:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_enumerator()
      tree.add( subtree )
      subtree = self.parse__gen24()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_enum_specifier(self):
    current = self.tokens.current()
    rule = self.table[129][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(248, self.nonterminals[248]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 20:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(37) # enum
      tree.add(t)
      subtree = self.parse_enum_specifier_sub()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__expr( self, rbp = 0):
    name = '_expr'
    if name not in self.expressionParsers:
      self.expressionParsers[name] = c_ExpressionParser__expr(self)
    return self.expressionParsers[name].parse(rbp)
  def parse__expr_sans_comma( self, rbp = 0):
    name = '_expr_sans_comma'
    if name not in self.expressionParsers:
      self.expressionParsers[name] = c_ExpressionParser__expr_sans_comma(self)
    return self.expressionParsers[name].parse(rbp)
  def parse__direct_declarator( self, rbp = 0):
    name = '_direct_declarator'
    if name not in self.expressionParsers:
      self.expressionParsers[name] = c_ExpressionParser__direct_declarator(self)
    return self.expressionParsers[name].parse(rbp)
  def parse__direct_abstract_declarator( self, rbp = 0):
    name = '_direct_abstract_declarator'
    if name not in self.expressionParsers:
      self.expressionParsers[name] = c_ExpressionParser__direct_abstract_declarator(self)
    return self.expressionParsers[name].parse(rbp)
