import sys
import inspect
def whoami():
  return inspect.stack()[1][3]
def whosdaddy():
  return inspect.stack()[2][3]
def parse( iterator, entry ):
  p = Parser()
  return p.parse(iterator, entry)
class Terminal:
  def __init__(self, id):
    self.id=id
    self.str=Parser.terminals[id]
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
  def __init__(self, nonterminal):
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
          elif len(self.children) == 1 and not isinstance(self.children[0], ParseTree) and not isinstance(self.children[0], list):
            return self.children[0]
          else:
            child = self.children[idx]
          parameters[name] = child.toAst()
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
      string = '%s(%s:\n' % ('', parsetree.nonterminal)
      string += ',\n'.join([ \
        '%s  %s' % (indentStr, self._prettyPrint(value, indent + 2)) for value in parsetree.children \
      ])
      string += '\n%s)' % (indentStr)
      return string
    elif isinstance(parsetree, Terminal):
      return parsetree.toString(self.tokenFormat)
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
        return 'None'
      string = '[\n'
      string += ',\n'.join([self._prettyPrint(element, indent + 2) for element in ast])
      string += '\n%s]' % (indentStr)
      return string
    elif isinstance(ast, Terminal):
      return '%s%s' % (indentStr, ast.toString(self.tokenFormat))
    return 'None'
class SyntaxError(Exception):
  def __init__(self, message):
    self.__dict__.update(locals())
  def __str__(self):
    return self.message
class ExpressionParser__expr:
  def __init__(self, parent):
    self.__dict__.update(locals())
    self.infixBp = {
      0: 15000,
      6: 1000,
      7: 2000,
      10: 1000,
      12: 1000,
      14: 9000,
      15: 8000,
      17: 1000,
      21: 8000,
      28: 16000,
      29: 7000,
      32: 12000,
      34: 1000,
      36: 5000,
      40: 9000,
      47: 15000,
      51: 15000,
      54: 15000,
      55: 15000,
      57: 1000,
      59: 14000,
      61: 1000,
      67: 1000,
      80: 15000,
      81: 9000,
      86: 6000,
      87: 4000,
      90: 1000,
      91: 1000,
      92: 12000,
      96: 11000,
      98: 10000,
      101: 11000,
      103: 12000,
      104: 10000,
      106: 1000,
      109: 3000,
      112: 9000,
    }
    self.prefixBp = {
      0: 13000,
      36: 13000,
      38: 13000,
      41: 13000,
      80: 13000,
      92: 13000,
      101: 13000,
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
    tree = ParseTree( NonTerminal(194, '_expr') )
    current = self.getCurrentToken()
    if not current:
      return tree
    if current.getId() in [0]:
      tree.astTransform = AstTransformNodeCreator('PreDecr', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(0) )
      tree.add( self.parent.parse__expr( self.getPrefixBp(0) ) )
      tree.isPrefix = True
    elif current.getId() in [36]:
      tree.astTransform = AstTransformNodeCreator('AddressOf', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(36) )
      tree.add( self.parent.parse__expr( self.getPrefixBp(36) ) )
      tree.isPrefix = True
    elif current.getId() in [115]:
      tree.astTransform = AstTransformNodeCreator('ArrayIndex', {'params': 2, 'name': 0})
      tree.nudMorphemeCount = 1
      tree.add( self.expect(115) )
    elif current.getId() in [82]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      tree.add( self.expect(82) )
    elif current.getId() in [92]:
      tree.astTransform = AstTransformNodeCreator('Dereference', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(92) )
      tree.add( self.parent.parse__expr( self.getPrefixBp(92) ) )
      tree.isPrefix = True
    elif current.getId() in [95]:
      tree.astTransform = AstTransformNodeCreator('TypeInitializion', {'type': 1, 'initializer': 4})
      tree.nudMorphemeCount = 3
      tree.add( self.expect(95) )
      tree.add( self.parent.parse_type_name() )
      tree.add( self.expect(48) )
    elif current.getId() in [18, 74, 49, 58, 84, 99]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      tree.add( self.parent.parse_constant() )
    elif current.getId() in [47]:
      tree.astTransform = AstTransformSubstitution(2)
      tree.nudMorphemeCount = 3
      tree.add( self.expect(47) )
      tree.add( self.parent.parse__expr() )
      tree.add( self.expect(48) )
    elif current.getId() in [115]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      tree.add( self.expect(115) )
    elif current.getId() in [115]:
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      tree.nudMorphemeCount = 1
      tree.add( self.expect(115) )
    elif current.getId() in [64]:
      tree.astTransform = AstTransformNodeCreator('SizeOf', {'var': 1})
      tree.nudMorphemeCount = 1
      tree.add( self.expect(64) )
    elif current.getId() in [80]:
      tree.astTransform = AstTransformNodeCreator('PreIncr', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(80) )
      tree.add( self.parent.parse__expr( self.getPrefixBp(80) ) )
      tree.isPrefix = True
    return tree
  def led(self, left):
    tree = ParseTree( NonTerminal(194, '_expr') )
    current = self.getCurrentToken()
    if current.getId() == 86: # 'bitxor'
      tree.astTransform = AstTransformNodeCreator('BitXOR', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(86) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(86) - modifier ) )
      return tree
    if current.getId() == 106: # 'rshifteq'
      tree.astTransform = AstTransformNodeCreator('RightShiftAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(106) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(106) - modifier ) )
      return tree
    if current.getId() == 80: # 'incr'
      tree.astTransform = AstTransformNodeCreator('PostIncr', {'var': 0})
      tree.isExprNud = True 
      tree.add(left)
      tree.add( self.expect(80) )
      return tree
    if current.getId() == 90: # 'muleq'
      tree.astTransform = AstTransformNodeCreator('MultiplyAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(90) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(90) - modifier ) )
      return tree
    if current.getId() == 28: # 'comma'
      tree.astTransform = AstTransformNodeCreator('Comma', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(28) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(28) - modifier ) )
      return tree
    if current.getId() == 6: # 'subeq'
      tree.astTransform = AstTransformNodeCreator('SubtractAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(6) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(6) - modifier ) )
      return tree
    if current.getId() == 91: # 'assign'
      tree.astTransform = AstTransformNodeCreator('Assign', {'var': 0, 'value': 2})
      tree.add(left)
      tree.add( self.expect(91) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(91) - modifier ) )
      return tree
    if current.getId() == 104: # 'rshift'
      tree.astTransform = AstTransformNodeCreator('RightShift', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(104) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(104) - modifier ) )
      return tree
    if current.getId() == 61: # 'addeq'
      tree.astTransform = AstTransformNodeCreator('AddAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(61) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(61) - modifier ) )
      return tree
    if current.getId() == 55: # 'lsquare'
      tree.astTransform = AstTransformNodeCreator('ArrayIndex', {'params': 2, 'name': 0})
      tree.add(left)
      tree.add( self.expect(55) )
      tree.add( self.parent.parse__gen44() )
      tree.add( self.expect(70) )
      return tree
    if current.getId() == 112: # 'lt'
      tree.astTransform = AstTransformNodeCreator('LessThan', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(112) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(112) - modifier ) )
      return tree
    if current.getId() == 32: # 'mod'
      tree.astTransform = AstTransformNodeCreator('Mod', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(32) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(32) - modifier ) )
      return tree
    if current.getId() == 12: # 'lshifteq'
      tree.astTransform = AstTransformNodeCreator('LeftShiftAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(12) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(12) - modifier ) )
      return tree
    if current.getId() == 34: # 'diveq'
      tree.astTransform = AstTransformNodeCreator('DivideAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(34) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(34) - modifier ) )
      return tree
    if current.getId() == 21: # 'eq'
      tree.astTransform = AstTransformNodeCreator('Equals', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(21) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(21) - modifier ) )
      return tree
    if current.getId() == 10: # 'bitoreq'
      tree.astTransform = AstTransformNodeCreator('ORAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(10) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(10) - modifier ) )
      return tree
    if current.getId() == 17: # 'modeq'
      tree.astTransform = AstTransformNodeCreator('ModAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(17) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(17) - modifier ) )
      return tree
    if current.getId() == 92: # 'asterisk'
      tree.astTransform = AstTransformNodeCreator('Mul', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(92) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(92) - modifier ) )
      return tree
    if current.getId() == 67: # 'bitxoreq'
      tree.astTransform = AstTransformNodeCreator('XORAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(67) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(67) - modifier ) )
      return tree
    if current.getId() == 59: # 'lbrace'
      tree.astTransform = AstTransformNodeCreator('TypeInitializion', {'type': 1, 'initializer': 4})
      tree.add(left)
      tree.add( self.expect(59) )
      tree.add( self.parent.parse__gen12() )
      tree.add( self.parent.parse_trailing_comma_opt() )
      tree.add( self.expect(89) )
      return tree
    if current.getId() == 40: # 'lteq'
      tree.astTransform = AstTransformNodeCreator('LessThanEq', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(40) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(40) - modifier ) )
      return tree
    if current.getId() == 7: # 'questionmark'
      tree.astTransform = AstTransformNodeCreator('TernaryOperator', {'true': 2, 'false': 4, 'cond': 0})
      tree.isExprNud = True 
      tree.add(left)
      tree.add( self.expect(7) )
      modifier = 1
      tree.add( self.parent.parse__expr( self.getInfixBp(7) - modifier ) )
      tree.add( self.expect(114) )
      modifier = 1
      tree.add( self.parent.parse__expr( self.getInfixBp(7) - modifier ) )
      return tree
    if current.getId() == 0: # 'decr'
      tree.astTransform = AstTransformNodeCreator('PostDecr', {'var': 0})
      tree.isExprNud = True 
      tree.add(left)
      tree.add( self.expect(0) )
      return tree
    if current.getId() == 81: # 'gt'
      tree.astTransform = AstTransformNodeCreator('GreaterThan', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(81) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(81) - modifier ) )
      return tree
    if current.getId() == 51: # 'arrow'
      tree.astTransform = AstTransformNodeCreator('DerefMemberSelect', {'member': 2, 'object': 0})
      tree.isExprNud = True 
      tree.add(left)
      tree.add( self.expect(51) )
      modifier = 0
      tree.add( self.parent.parse__expr( self.getInfixBp(51) - modifier ) )
      return tree
    if current.getId() == 36: # 'bitand'
      tree.astTransform = AstTransformNodeCreator('BitAND', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(36) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(36) - modifier ) )
      return tree
    if current.getId() == 47: # 'lparen'
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      tree.add(left)
      tree.add( self.expect(47) )
      tree.add( self.parent.parse__gen44() )
      tree.add( self.expect(48) )
      return tree
    if current.getId() == 9: # 'sizeof_separator'
      tree.astTransform = AstTransformNodeCreator('SizeOf', {'var': 1})
      tree.add(left)
      tree.add( self.expect(9) )
      tree.add( self.parent.parse_sizeof_body() )
      return tree
    if current.getId() == 103: # 'div'
      tree.astTransform = AstTransformNodeCreator('Div', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(103) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(103) - modifier ) )
      return tree
    if current.getId() == 101: # 'sub'
      tree.astTransform = AstTransformNodeCreator('Sub', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(101) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(101) - modifier ) )
      return tree
    if current.getId() == 96: # 'add'
      tree.astTransform = AstTransformNodeCreator('Add', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(96) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(96) - modifier ) )
      return tree
    if current.getId() == 14: # 'gteq'
      tree.astTransform = AstTransformNodeCreator('GreaterThanEq', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(14) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(14) - modifier ) )
      return tree
    if current.getId() == 98: # 'lshift'
      tree.astTransform = AstTransformNodeCreator('LeftShift', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(98) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(98) - modifier ) )
      return tree
    if current.getId() == 57: # 'bitandeq'
      tree.astTransform = AstTransformNodeCreator('ANDAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(57) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(57) - modifier ) )
      return tree
    if current.getId() == 29: # 'bitor'
      tree.astTransform = AstTransformNodeCreator('BitOR', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(29) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(29) - modifier ) )
      return tree
    if current.getId() == 54: # 'dot'
      tree.astTransform = AstTransformNodeCreator('MemberSelect', {'member': 2, 'object': 0})
      tree.isExprNud = True 
      tree.add(left)
      tree.add( self.expect(54) )
      modifier = 0
      tree.add( self.parent.parse__expr( self.getInfixBp(54) - modifier ) )
      return tree
    return tree
class ExpressionParser__expr_sans_comma:
  def __init__(self, parent):
    self.__dict__.update(locals())
    self.infixBp = {
      0: 15000,
      6: 1000,
      7: 2000,
      10: 1000,
      12: 1000,
      14: 9000,
      15: 8000,
      17: 1000,
      21: 8000,
      29: 7000,
      32: 12000,
      34: 1000,
      36: 5000,
      40: 9000,
      47: 15000,
      51: 15000,
      54: 15000,
      55: 15000,
      57: 1000,
      59: 14000,
      61: 1000,
      67: 1000,
      80: 15000,
      81: 9000,
      86: 6000,
      87: 4000,
      90: 1000,
      91: 1000,
      92: 12000,
      96: 11000,
      98: 10000,
      101: 11000,
      103: 12000,
      104: 10000,
      106: 1000,
      109: 3000,
      112: 9000,
    }
    self.prefixBp = {
      0: 13000,
      36: 13000,
      38: 13000,
      41: 13000,
      80: 13000,
      92: 13000,
      101: 13000,
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
    tree = ParseTree( NonTerminal(179, '_expr_sans_comma') )
    current = self.getCurrentToken()
    if not current:
      return tree
    elif current.getId() in [95]:
      tree.astTransform = AstTransformNodeCreator('TypeInitializion', {'type': 1, 'initializer': 4})
      tree.nudMorphemeCount = 3
      tree.add( self.expect(95) )
      tree.add( self.parent.parse_type_name() )
      tree.add( self.expect(48) )
    elif current.getId() in [82]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      tree.add( self.expect(82) )
    elif current.getId() in [64]:
      tree.astTransform = AstTransformNodeCreator('SizeOf', {'var': 1})
      tree.nudMorphemeCount = 1
      tree.add( self.expect(64) )
    elif current.getId() in [92]:
      tree.astTransform = AstTransformNodeCreator('Dereference', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(92) )
      tree.add( self.parent.parse__expr_sans_comma( self.getPrefixBp(92) ) )
      tree.isPrefix = True
    elif current.getId() in [47]:
      tree.astTransform = AstTransformSubstitution(2)
      tree.nudMorphemeCount = 3
      tree.add( self.expect(47) )
      tree.add( self.parent.parse__expr_sans_comma() )
      tree.add( self.expect(48) )
    elif current.getId() in [0]:
      tree.astTransform = AstTransformNodeCreator('PreDecr', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(0) )
      tree.add( self.parent.parse__expr_sans_comma( self.getPrefixBp(0) ) )
      tree.isPrefix = True
    elif current.getId() in [36]:
      tree.astTransform = AstTransformNodeCreator('AddressOf', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(36) )
      tree.add( self.parent.parse__expr_sans_comma( self.getPrefixBp(36) ) )
      tree.isPrefix = True
    elif current.getId() in [18, 74, 49, 58, 84, 99]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      tree.add( self.parent.parse_constant() )
    elif current.getId() in [115]:
      tree.astTransform = AstTransformNodeCreator('ArrayIndex', {'params': 2, 'name': 0})
      tree.nudMorphemeCount = 1
      tree.add( self.expect(115) )
    elif current.getId() in [115]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      tree.add( self.expect(115) )
    elif current.getId() in [80]:
      tree.astTransform = AstTransformNodeCreator('PreIncr', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(80) )
      tree.add( self.parent.parse__expr_sans_comma( self.getPrefixBp(80) ) )
      tree.isPrefix = True
    elif current.getId() in [115]:
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      tree.nudMorphemeCount = 1
      tree.add( self.expect(115) )
    return tree
  def led(self, left):
    tree = ParseTree( NonTerminal(179, '_expr_sans_comma') )
    current = self.getCurrentToken()
    if current.getId() == 103: # 'div'
      tree.astTransform = AstTransformNodeCreator('Div', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(103) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(103) - modifier ) )
      return tree
    if current.getId() == 14: # 'gteq'
      tree.astTransform = AstTransformNodeCreator('GreaterThanEq', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(14) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(14) - modifier ) )
      return tree
    if current.getId() == 106: # 'rshifteq'
      tree.astTransform = AstTransformNodeCreator('RightShiftAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(106) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(106) - modifier ) )
      return tree
    if current.getId() == 104: # 'rshift'
      tree.astTransform = AstTransformNodeCreator('RightShift', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(104) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(104) - modifier ) )
      return tree
    if current.getId() == 51: # 'arrow'
      tree.astTransform = AstTransformNodeCreator('DerefMemberSelect', {'member': 2, 'object': 0})
      tree.isExprNud = True 
      tree.add(left)
      tree.add( self.expect(51) )
      modifier = 0
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(51) - modifier ) )
      return tree
    if current.getId() == 59: # 'lbrace'
      tree.astTransform = AstTransformNodeCreator('TypeInitializion', {'type': 1, 'initializer': 4})
      tree.add(left)
      tree.add( self.expect(59) )
      tree.add( self.parent.parse__gen12() )
      tree.add( self.parent.parse_trailing_comma_opt() )
      tree.add( self.expect(89) )
      return tree
    if current.getId() == 91: # 'assign'
      tree.astTransform = AstTransformNodeCreator('Assign', {'var': 0, 'value': 2})
      tree.add(left)
      tree.add( self.expect(91) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(91) - modifier ) )
      return tree
    if current.getId() == 9: # 'sizeof_separator'
      tree.astTransform = AstTransformNodeCreator('SizeOf', {'var': 1})
      tree.add(left)
      tree.add( self.expect(9) )
      tree.add( self.parent.parse_sizeof_body() )
      return tree
    if current.getId() == 21: # 'eq'
      tree.astTransform = AstTransformNodeCreator('Equals', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(21) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(21) - modifier ) )
      return tree
    if current.getId() == 86: # 'bitxor'
      tree.astTransform = AstTransformNodeCreator('BitXOR', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(86) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(86) - modifier ) )
      return tree
    if current.getId() == 6: # 'subeq'
      tree.astTransform = AstTransformNodeCreator('SubtractAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(6) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(6) - modifier ) )
      return tree
    if current.getId() == 0: # 'decr'
      tree.astTransform = AstTransformNodeCreator('PostDecr', {'var': 0})
      tree.isExprNud = True 
      tree.add(left)
      tree.add( self.expect(0) )
      return tree
    if current.getId() == 80: # 'incr'
      tree.astTransform = AstTransformNodeCreator('PostIncr', {'var': 0})
      tree.isExprNud = True 
      tree.add(left)
      tree.add( self.expect(80) )
      return tree
    if current.getId() == 67: # 'bitxoreq'
      tree.astTransform = AstTransformNodeCreator('XORAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(67) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(67) - modifier ) )
      return tree
    if current.getId() == 7: # 'questionmark'
      tree.astTransform = AstTransformNodeCreator('TernaryOperator', {'true': 2, 'false': 4, 'cond': 0})
      tree.isExprNud = True 
      tree.add(left)
      tree.add( self.expect(7) )
      modifier = 1
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(7) - modifier ) )
      tree.add( self.expect(114) )
      modifier = 1
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(7) - modifier ) )
      return tree
    if current.getId() == 34: # 'diveq'
      tree.astTransform = AstTransformNodeCreator('DivideAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(34) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(34) - modifier ) )
      return tree
    if current.getId() == 96: # 'add'
      tree.astTransform = AstTransformNodeCreator('Add', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(96) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(96) - modifier ) )
      return tree
    if current.getId() == 40: # 'lteq'
      tree.astTransform = AstTransformNodeCreator('LessThanEq', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(40) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(40) - modifier ) )
      return tree
    if current.getId() == 101: # 'sub'
      tree.astTransform = AstTransformNodeCreator('Sub', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(101) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(101) - modifier ) )
      return tree
    if current.getId() == 32: # 'mod'
      tree.astTransform = AstTransformNodeCreator('Mod', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(32) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(32) - modifier ) )
      return tree
    if current.getId() == 17: # 'modeq'
      tree.astTransform = AstTransformNodeCreator('ModAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(17) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(17) - modifier ) )
      return tree
    if current.getId() == 55: # 'lsquare'
      tree.astTransform = AstTransformNodeCreator('ArrayIndex', {'params': 2, 'name': 0})
      tree.add(left)
      tree.add( self.expect(55) )
      tree.add( self.parent.parse__gen44() )
      tree.add( self.expect(70) )
      return tree
    if current.getId() == 98: # 'lshift'
      tree.astTransform = AstTransformNodeCreator('LeftShift', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(98) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(98) - modifier ) )
      return tree
    if current.getId() == 54: # 'dot'
      tree.astTransform = AstTransformNodeCreator('MemberSelect', {'member': 2, 'object': 0})
      tree.isExprNud = True 
      tree.add(left)
      tree.add( self.expect(54) )
      modifier = 0
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(54) - modifier ) )
      return tree
    if current.getId() == 92: # 'asterisk'
      tree.astTransform = AstTransformNodeCreator('Mul', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(92) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(92) - modifier ) )
      return tree
    if current.getId() == 90: # 'muleq'
      tree.astTransform = AstTransformNodeCreator('MultiplyAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(90) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(90) - modifier ) )
      return tree
    if current.getId() == 29: # 'bitor'
      tree.astTransform = AstTransformNodeCreator('BitOR', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(29) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(29) - modifier ) )
      return tree
    if current.getId() == 12: # 'lshifteq'
      tree.astTransform = AstTransformNodeCreator('LeftShiftAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(12) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(12) - modifier ) )
      return tree
    if current.getId() == 36: # 'bitand'
      tree.astTransform = AstTransformNodeCreator('BitAND', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(36) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(36) - modifier ) )
      return tree
    if current.getId() == 112: # 'lt'
      tree.astTransform = AstTransformNodeCreator('LessThan', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(112) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(112) - modifier ) )
      return tree
    if current.getId() == 61: # 'addeq'
      tree.astTransform = AstTransformNodeCreator('AddAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(61) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(61) - modifier ) )
      return tree
    if current.getId() == 47: # 'lparen'
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      tree.add(left)
      tree.add( self.expect(47) )
      tree.add( self.parent.parse__gen44() )
      tree.add( self.expect(48) )
      return tree
    if current.getId() == 57: # 'bitandeq'
      tree.astTransform = AstTransformNodeCreator('ANDAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(57) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(57) - modifier ) )
      return tree
    if current.getId() == 81: # 'gt'
      tree.astTransform = AstTransformNodeCreator('GreaterThan', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(81) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(81) - modifier ) )
      return tree
    if current.getId() == 10: # 'bitoreq'
      tree.astTransform = AstTransformNodeCreator('ORAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(10) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(10) - modifier ) )
      return tree
    return tree
class ExpressionParser__direct_declarator:
  def __init__(self, parent):
    self.__dict__.update(locals())
    self.infixBp = {
      47: 1000,
      55: 1000,
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
    tree = ParseTree( NonTerminal(158, '_direct_declarator') )
    current = self.getCurrentToken()
    if not current:
      return tree
    if current.getId() in [47]:
      tree.astTransform = AstTransformSubstitution(1)
      tree.nudMorphemeCount = 3
      tree.add( self.expect(47) )
      tree.add( self.parent.parse_declarator() )
      tree.add( self.expect(48) )
    elif current.getId() in [115]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      tree.add( self.expect(115) )
    return tree
  def led(self, left):
    tree = ParseTree( NonTerminal(158, '_direct_declarator') )
    current = self.getCurrentToken()
    if current.getId() == 55: # 'lsquare'
      tree.astTransform = AstTransformNodeCreator('Array', {'name': 0, 'size': 2})
      tree.isExprNud = True 
      tree.add(left)
      tree.add( self.expect(55) )
      tree.add( self.parent.parse_direct_declarator_expr() )
      tree.add( self.expect(70) )
      return tree
    if current.getId() == 47: # 'lparen'
      tree.astTransform = AstTransformNodeCreator('FunctionSignature', {'params': 2, 'declarator': 0})
      tree.isExprNud = True 
      tree.add(left)
      tree.add( self.expect(47) )
      tree.add( self.parent.parse_direct_declarator_parameter_list() )
      tree.add( self.expect(48) )
      return tree
    return tree
class ExpressionParser__direct_abstract_declarator:
  def __init__(self, parent):
    self.__dict__.update(locals())
    self.infixBp = {
      47: 1000,
      55: 1000,
    }
    self.prefixBp = {
      47: 2000,
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
    tree = ParseTree( NonTerminal(229, '_direct_abstract_declarator') )
    current = self.getCurrentToken()
    if not current:
      return tree
    if current.getId() in [47]:
      tree.astTransform = AstTransformSubstitution(1)
      tree.nudMorphemeCount = 3
      tree.add( self.expect(47) )
      tree.add( self.parent.parse_abstract_declarator() )
      tree.add( self.expect(48) )
    return tree
  def led(self, left):
    tree = ParseTree( NonTerminal(229, '_direct_abstract_declarator') )
    current = self.getCurrentToken()
    if current.getId() == 55: # 'lsquare'
      tree.astTransform = AstTransformNodeCreator('AbstractArray', {'object': '$', 'size': 2})
      tree.isExprNud = True 
      tree.add(left)
      tree.add( self.expect(55) )
      tree.add( self.parent.parse_direct_abstract_declarator_expr() )
      tree.add( self.expect(70) )
      return tree
    if current.getId() == 47: # 'lparen'
      tree.astTransform = AstTransformNodeCreator('AbstractFunction', {'object': '$', 'params': 2})
      tree.isExprNud = True 
      tree.add(left)
      tree.add( self.expect(47) )
      tree.add( self.parent.parse__gen46() )
      tree.add( self.expect(48) )
      return tree
    return tree
class TokenStream:
  def __init__(self, iterable):
    self.iterable = iter(iterable)
    self.advance()
  def advance(self):
    try:
      self.token = next(self.iterable)
    except StopIteration:
      self.token = None
    return self.token
  def current(self):
    return self.token
class Parser:
  # Quark - finite string set maps one string to exactly one int, and vice versa
  terminals = {
    0: 'decr',
    1: 'unsigned',
    2: 'struct',
    3: 'const',
    4: 'typedef',
    5: 'comma_va_args',
    6: 'subeq',
    7: 'questionmark',
    8: 'restrict',
    9: 'sizeof_separator',
    10: 'bitoreq',
    11: 'else_if',
    12: 'lshifteq',
    13: 'int',
    14: 'gteq',
    15: 'neq',
    16: 'volatile',
    17: 'modeq',
    18: 'character_constant',
    19: 'do',
    20: 'semi',
    21: 'eq',
    22: 'pp_number',
    23: 'poundpound',
    24: 'for',
    25: 'variable_length_array',
    26: 'long',
    27: 'extern',
    28: 'comma',
    29: 'bitor',
    30: 'double',
    31: 'named_parameter_hint',
    32: 'mod',
    33: 'float',
    34: 'diveq',
    35: 'enum',
    36: 'bitand',
    37: 'register',
    38: 'not',
    39: '_expr',
    40: 'lteq',
    41: 'bitnot',
    42: 'function_definition_hint',
    43: 'char',
    44: '_expr_sans_comma',
    45: 'if',
    46: 'universal_character_name',
    47: 'lparen',
    48: 'rparen',
    49: 'integer_constant',
    50: 'endif',
    51: 'arrow',
    52: 'switch',
    53: 'elipsis',
    54: 'dot',
    55: 'lsquare',
    56: 'union',
    57: 'bitandeq',
    58: 'enumeration_constant',
    59: 'lbrace',
    60: 'bool',
    61: 'addeq',
    62: 'inline',
    63: 'declarator_hint',
    64: 'sizeof',
    65: 'static',
    66: 'default',
    67: 'bitxoreq',
    68: 'short',
    69: 'break',
    70: 'rsquare',
    71: 'goto',
    72: '_direct_abstract_declarator',
    73: 'signed',
    74: 'decimal_floating_constant',
    75: 'external_declaration_hint',
    76: 'while',
    77: 'imaginary',
    78: 'complex',
    79: 'defined_separator',
    80: 'incr',
    81: 'gt',
    82: 'string_literal',
    83: 'continue',
    84: 'hexadecimal_floating_constant',
    85: 'abstract_parameter_hint',
    86: 'bitxor',
    87: 'and',
    88: 'function_prototype_hint',
    89: 'rbrace',
    90: 'muleq',
    91: 'assign',
    92: 'asterisk',
    93: '_direct_declarator',
    94: 'pound',
    95: 'lparen_cast',
    96: 'add',
    97: 'defined',
    98: 'lshift',
    99: 'floating_constant',
    100: 'case',
    101: 'sub',
    102: 'auto',
    103: 'div',
    104: 'rshift',
    105: 'trailing_comma',
    106: 'rshifteq',
    107: 'label_hint',
    108: 'exclamation_point',
    109: 'or',
    110: 'tilde',
    111: 'ampersand',
    112: 'lt',
    113: 'typedef_identifier',
    114: 'colon',
    115: 'identifier',
    116: 'else',
    117: 'void',
    118: 'return',
    'decr': 0,
    'unsigned': 1,
    'struct': 2,
    'const': 3,
    'typedef': 4,
    'comma_va_args': 5,
    'subeq': 6,
    'questionmark': 7,
    'restrict': 8,
    'sizeof_separator': 9,
    'bitoreq': 10,
    'else_if': 11,
    'lshifteq': 12,
    'int': 13,
    'gteq': 14,
    'neq': 15,
    'volatile': 16,
    'modeq': 17,
    'character_constant': 18,
    'do': 19,
    'semi': 20,
    'eq': 21,
    'pp_number': 22,
    'poundpound': 23,
    'for': 24,
    'variable_length_array': 25,
    'long': 26,
    'extern': 27,
    'comma': 28,
    'bitor': 29,
    'double': 30,
    'named_parameter_hint': 31,
    'mod': 32,
    'float': 33,
    'diveq': 34,
    'enum': 35,
    'bitand': 36,
    'register': 37,
    'not': 38,
    '_expr': 39,
    'lteq': 40,
    'bitnot': 41,
    'function_definition_hint': 42,
    'char': 43,
    '_expr_sans_comma': 44,
    'if': 45,
    'universal_character_name': 46,
    'lparen': 47,
    'rparen': 48,
    'integer_constant': 49,
    'endif': 50,
    'arrow': 51,
    'switch': 52,
    'elipsis': 53,
    'dot': 54,
    'lsquare': 55,
    'union': 56,
    'bitandeq': 57,
    'enumeration_constant': 58,
    'lbrace': 59,
    'bool': 60,
    'addeq': 61,
    'inline': 62,
    'declarator_hint': 63,
    'sizeof': 64,
    'static': 65,
    'default': 66,
    'bitxoreq': 67,
    'short': 68,
    'break': 69,
    'rsquare': 70,
    'goto': 71,
    '_direct_abstract_declarator': 72,
    'signed': 73,
    'decimal_floating_constant': 74,
    'external_declaration_hint': 75,
    'while': 76,
    'imaginary': 77,
    'complex': 78,
    'defined_separator': 79,
    'incr': 80,
    'gt': 81,
    'string_literal': 82,
    'continue': 83,
    'hexadecimal_floating_constant': 84,
    'abstract_parameter_hint': 85,
    'bitxor': 86,
    'and': 87,
    'function_prototype_hint': 88,
    'rbrace': 89,
    'muleq': 90,
    'assign': 91,
    'asterisk': 92,
    '_direct_declarator': 93,
    'pound': 94,
    'lparen_cast': 95,
    'add': 96,
    'defined': 97,
    'lshift': 98,
    'floating_constant': 99,
    'case': 100,
    'sub': 101,
    'auto': 102,
    'div': 103,
    'rshift': 104,
    'trailing_comma': 105,
    'rshifteq': 106,
    'label_hint': 107,
    'exclamation_point': 108,
    'or': 109,
    'tilde': 110,
    'ampersand': 111,
    'lt': 112,
    'typedef_identifier': 113,
    'colon': 114,
    'identifier': 115,
    'else': 116,
    'void': 117,
    'return': 118,
  }
  # Quark - finite string set maps one string to exactly one int, and vice versa
  nonterminals = {
    119: 'external_declaration_sub_sub',
    120: 'init_declarator_list',
    121: '_gen8',
    122: '_gen20',
    123: '_gen4',
    124: 'designator',
    125: 'keyword',
    126: 'named_parameter_declaration',
    127: 'storage_class_specifier',
    128: 'sizeof_body',
    129: 'struct_or_union_body',
    130: '_gen16',
    131: 'constant',
    132: 'type_specifier',
    133: '_gen1',
    134: 'for_init',
    135: 'external_declarator',
    136: 'for_incr',
    137: 'type_qualifier',
    138: 'struct_or_union_sub',
    139: 'external_prototype',
    140: '_gen46',
    141: 'function_specifier',
    142: 'struct_declaration',
    143: '_gen17',
    144: 'type_name',
    145: 'declarator',
    146: 'declaration_list',
    147: 'enumeration_constant',
    148: '_gen9',
    149: '_gen10',
    150: 'abstract_declarator',
    151: 'pointer',
    152: 'misc',
    153: '_gen26',
    154: '_gen33',
    155: 'specifier_qualifier',
    156: '_gen18',
    157: 'translation_unit',
    158: '_direct_declarator',
    159: 'init_declarator',
    160: '_gen6',
    161: 'struct_declarator',
    162: '_gen5',
    163: '_gen19',
    164: '_gen36',
    165: 'direct_declarator_modifier_list',
    166: '_gen27',
    167: 'token',
    168: '_gen22',
    169: 'struct_specifier',
    170: 'block_item',
    171: 'initializer',
    172: 'direct_declarator_size',
    173: 'expression_statement',
    174: 'union_specifier',
    175: 'pointer_sub',
    176: '_gen7',
    177: 'struct_declarator_body',
    178: '_gen38',
    179: '_expr_sans_comma',
    180: 'direct_declarator_modifier',
    181: '_gen28',
    182: '_gen35',
    183: 'typedef_name',
    184: 'enumerator_assignment',
    185: '_gen12',
    186: 'type_qualifier_list_opt',
    187: 'parameter_type_list',
    188: '_gen21',
    189: '_gen0',
    190: 'direct_abstract_declarator_expr',
    191: 'expression_opt',
    192: '_gen37',
    193: 'trailing_comma_opt',
    194: '_expr',
    195: 'static_opt',
    196: '_gen40',
    197: 'designation',
    198: 'direct_declarator_parameter_list',
    199: 'declaration',
    200: '_gen14',
    201: 'compound_statement',
    202: 'enum_specifier_sub',
    203: 'abstract_parameter_declaration',
    204: 'statement',
    205: 'enum_specifier',
    206: 'identifier',
    207: 'enum_specifier_body',
    208: 'parameter_declaration',
    209: '_gen29',
    210: '_gen30',
    211: '_gen44',
    212: 'labeled_statement',
    213: '_gen25',
    214: '_gen45',
    215: '_gen15',
    216: 'else_if_statement_list',
    217: '_gen41',
    218: '_gen31',
    219: 'punctuator',
    220: 'enumerator',
    221: '_gen23',
    222: '_gen24',
    223: 'else_statement',
    224: 'selection_statement',
    225: '_gen42',
    226: 'for_cond',
    227: 'initializer_list_item',
    228: 'iteration_statement',
    229: '_direct_abstract_declarator',
    230: 'declaration_specifier',
    231: 'jump_statement',
    232: '_gen2',
    233: '_gen3',
    234: '_gen32',
    235: 'else_if_statement',
    236: '_gen43',
    237: 'declarator_initializer',
    238: 'pp',
    239: '_gen34',
    240: 'va_args',
    241: '_gen13',
    242: 'external_declaration_sub',
    243: '_gen11',
    244: 'external_declaration',
    245: 'external_function',
    246: 'block_item_list',
    247: '_gen39',
    248: 'direct_declarator_expr',
    'external_declaration_sub_sub': 119,
    'init_declarator_list': 120,
    '_gen8': 121,
    '_gen20': 122,
    '_gen4': 123,
    'designator': 124,
    'keyword': 125,
    'named_parameter_declaration': 126,
    'storage_class_specifier': 127,
    'sizeof_body': 128,
    'struct_or_union_body': 129,
    '_gen16': 130,
    'constant': 131,
    'type_specifier': 132,
    '_gen1': 133,
    'for_init': 134,
    'external_declarator': 135,
    'for_incr': 136,
    'type_qualifier': 137,
    'struct_or_union_sub': 138,
    'external_prototype': 139,
    '_gen46': 140,
    'function_specifier': 141,
    'struct_declaration': 142,
    '_gen17': 143,
    'type_name': 144,
    'declarator': 145,
    'declaration_list': 146,
    'enumeration_constant': 147,
    '_gen9': 148,
    '_gen10': 149,
    'abstract_declarator': 150,
    'pointer': 151,
    'misc': 152,
    '_gen26': 153,
    '_gen33': 154,
    'specifier_qualifier': 155,
    '_gen18': 156,
    'translation_unit': 157,
    '_direct_declarator': 158,
    'init_declarator': 159,
    '_gen6': 160,
    'struct_declarator': 161,
    '_gen5': 162,
    '_gen19': 163,
    '_gen36': 164,
    'direct_declarator_modifier_list': 165,
    '_gen27': 166,
    'token': 167,
    '_gen22': 168,
    'struct_specifier': 169,
    'block_item': 170,
    'initializer': 171,
    'direct_declarator_size': 172,
    'expression_statement': 173,
    'union_specifier': 174,
    'pointer_sub': 175,
    '_gen7': 176,
    'struct_declarator_body': 177,
    '_gen38': 178,
    '_expr_sans_comma': 179,
    'direct_declarator_modifier': 180,
    '_gen28': 181,
    '_gen35': 182,
    'typedef_name': 183,
    'enumerator_assignment': 184,
    '_gen12': 185,
    'type_qualifier_list_opt': 186,
    'parameter_type_list': 187,
    '_gen21': 188,
    '_gen0': 189,
    'direct_abstract_declarator_expr': 190,
    'expression_opt': 191,
    '_gen37': 192,
    'trailing_comma_opt': 193,
    '_expr': 194,
    'static_opt': 195,
    '_gen40': 196,
    'designation': 197,
    'direct_declarator_parameter_list': 198,
    'declaration': 199,
    '_gen14': 200,
    'compound_statement': 201,
    'enum_specifier_sub': 202,
    'abstract_parameter_declaration': 203,
    'statement': 204,
    'enum_specifier': 205,
    'identifier': 206,
    'enum_specifier_body': 207,
    'parameter_declaration': 208,
    '_gen29': 209,
    '_gen30': 210,
    '_gen44': 211,
    'labeled_statement': 212,
    '_gen25': 213,
    '_gen45': 214,
    '_gen15': 215,
    'else_if_statement_list': 216,
    '_gen41': 217,
    '_gen31': 218,
    'punctuator': 219,
    'enumerator': 220,
    '_gen23': 221,
    '_gen24': 222,
    'else_statement': 223,
    'selection_statement': 224,
    '_gen42': 225,
    'for_cond': 226,
    'initializer_list_item': 227,
    'iteration_statement': 228,
    '_direct_abstract_declarator': 229,
    'declaration_specifier': 230,
    'jump_statement': 231,
    '_gen2': 232,
    '_gen3': 233,
    '_gen32': 234,
    'else_if_statement': 235,
    '_gen43': 236,
    'declarator_initializer': 237,
    'pp': 238,
    '_gen34': 239,
    'va_args': 240,
    '_gen13': 241,
    'external_declaration_sub': 242,
    '_gen11': 243,
    'external_declaration': 244,
    'external_function': 245,
    'block_item_list': 246,
    '_gen39': 247,
    'direct_declarator_expr': 248,
  }
  # table[nonterminal][terminal] = rule
  table = [
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 49, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 388, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 280, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 280, 280, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 280, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 66, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 6, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 6, 6, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 6, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 392, -1, -1, -1, -1, -1, -1, -1, 288, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 93, -1, -1, -1, -1, -1, -1, -1, 217, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 271, 40, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, 233, 35, 378, 67, -1, -1, -1, 152, -1, -1, -1, -1, 109, -1, -1, 336, -1, -1, 342, -1, -1, -1, -1, 162, -1, 61, 37, -1, -1, 13, -1, -1, 18, -1, 410, -1, 71, -1, -1, -1, -1, -1, 175, -1, 30, -1, -1, -1, -1, -1, -1, 26, -1, -1, -1, 164, -1, -1, -1, 325, -1, 126, -1, 246, 220, 376, -1, 411, 231, -1, 296, -1, 341, -1, -1, 318, 182, 381, -1, -1, -1, -1, 241, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 150, -1, 351, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 113, 96, 352],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 70, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, 0, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 78, -1, -1, -1, -1, -1, -1, -1, -1, -1, 358, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 31, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 348, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 75, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 412, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 134, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, 65, 65, 65, 65, 65, -1, -1, 65, -1, -1, -1, -1, 65, -1, -1, 65, -1, -1, -1, 65, -1, -1, -1, -1, -1, 65, 65, 65, -1, 65, -1, -1, 65, -1, 65, -1, 65, -1, -1, -1, -1, 65, 65, -1, -1, -1, 65, -1, -1, -1, -1, -1, -1, -1, -1, 65, -1, -1, 230, 65, -1, 65, 65, -1, 65, -1, -1, 65, -1, -1, -1, 65, 65, -1, -1, -1, 65, 65, -1, -1, -1, -1, -1, -1, -1, -1, -1, 65, -1, -1, -1, 65, 65, -1, -1, -1, -1, -1, -1, -1, -1, 65, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 65, 65, 65, -1, 65, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 397, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 169, -1, -1, -1, -1, -1, -1, -1, -1, 295, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 401, -1, -1, -1, -1, -1, -1, -1, -1, -1, 313, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 353, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, 62, 156, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 133, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 41, -1, -1, -1, 85, -1, -1, 210, -1, 201, -1, -1, -1, -1, -1, -1, -1, 23, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 103, -1, -1, -1, 46, -1, -1, -1, -1, -1, -1, -1, 60, -1, -1, -1, -1, 393, -1, -1, -1, 174, 326, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 422, -1, -1, -1, 149, -1],
    [-1, 399, 399, 399, 399, -1, -1, -1, 399, -1, -1, -1, -1, 399, -1, -1, 399, -1, -1, -1, -1, -1, -1, -1, -1, -1, 399, 399, -1, -1, 399, -1, -1, 399, -1, 399, -1, 399, -1, -1, -1, -1, -1, 399, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 399, -1, -1, -1, 399, -1, 399, -1, -1, 399, -1, -1, 399, -1, -1, -1, -1, 399, -1, -1, -1, 399, 399, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 399, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 399, -1, -1, -1, 399, -1],
    [92, 76, 76, 76, 76, -1, -1, -1, 76, -1, -1, -1, -1, 76, -1, -1, 76, -1, 92, -1, 158, -1, -1, -1, -1, -1, 76, 76, -1, -1, 76, -1, -1, 76, -1, 76, 92, 76, -1, 92, -1, -1, -1, 76, -1, -1, -1, 92, -1, 92, -1, -1, -1, -1, -1, -1, 76, -1, 92, -1, 76, -1, 76, -1, 92, 76, -1, -1, 76, -1, -1, -1, -1, 76, 92, -1, -1, 76, 76, -1, 92, -1, 92, -1, 92, -1, -1, -1, -1, -1, -1, -1, 92, -1, -1, 92, -1, -1, -1, 92, -1, -1, 76, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 76, -1, 92, -1, 76, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 324, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 153, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 183, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, 95, -1, -1, -1, -1, 91, -1, -1, -1, -1, -1, -1, -1, 15, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 68, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 2, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 322, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 235, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 235, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 332, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, 426, 426, 426, -1, -1, -1, -1, 426, -1, -1, -1, -1, 426, -1, -1, 426, -1, -1, -1, -1, -1, -1, -1, -1, -1, 426, -1, -1, -1, 426, -1, -1, 426, -1, 426, -1, -1, -1, -1, -1, -1, -1, 426, -1, -1, -1, 426, -1, -1, -1, -1, -1, -1, -1, -1, 426, -1, -1, -1, 426, -1, -1, -1, -1, -1, -1, -1, 426, -1, -1, -1, -1, 426, -1, -1, -1, 426, 426, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 426, 426, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 426, 426, 426, -1, 426, -1],
    [-1, 254, 254, 254, -1, -1, -1, -1, 254, -1, -1, -1, -1, 254, -1, -1, 254, -1, -1, -1, -1, -1, -1, -1, -1, -1, 254, -1, -1, -1, 254, -1, -1, 254, -1, 254, -1, -1, -1, -1, -1, -1, -1, 254, -1, -1, -1, 254, -1, -1, -1, -1, -1, -1, -1, -1, 254, -1, -1, -1, 254, -1, -1, -1, -1, -1, -1, -1, 254, -1, -1, -1, -1, 254, -1, -1, -1, 254, 254, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 257, -1, -1, 254, 254, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 254, 254, 254, -1, 254, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 269, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 289, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 383, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 383, 383, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 383, -1, -1, -1],
    [-1, 415, 415, 415, 415, -1, -1, -1, 415, -1, -1, -1, -1, 415, -1, -1, 415, -1, -1, -1, 415, -1, -1, -1, -1, -1, 415, 415, 415, -1, 415, -1, -1, 415, -1, 415, -1, 415, -1, -1, -1, -1, -1, 415, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 415, -1, -1, 415, 415, -1, 415, -1, -1, 415, -1, -1, 415, -1, -1, -1, -1, 415, -1, -1, -1, 415, 415, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 415, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 415, -1, -1, -1, 415, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 161, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 307, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 307, 307, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 307, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 52, -1, -1, -1, -1, -1, -1, -1, 47, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 184, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 184, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 54, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 11, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 417, -1, -1, -1, 122, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 272, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 267, 272, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 272, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 335, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, 373, 373, 191, -1, -1, -1, -1, 191, -1, -1, -1, -1, 373, -1, -1, 191, -1, -1, -1, -1, -1, -1, -1, -1, -1, 373, -1, -1, -1, 373, -1, -1, 373, -1, 373, -1, -1, -1, -1, -1, -1, -1, 373, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 373, -1, -1, -1, 373, -1, -1, -1, -1, -1, -1, -1, 373, -1, -1, -1, -1, 373, -1, -1, -1, 373, 373, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 373, -1, -1, -1, 373, -1],
    [-1, 274, 274, 274, -1, -1, -1, -1, 274, -1, -1, -1, -1, 274, -1, -1, 274, -1, -1, -1, -1, -1, -1, -1, -1, -1, 274, -1, -1, -1, 274, -1, -1, 274, -1, 274, -1, -1, -1, -1, -1, -1, -1, 274, -1, -1, -1, 277, -1, -1, -1, -1, -1, -1, -1, -1, 274, -1, -1, -1, 274, -1, -1, -1, -1, -1, -1, -1, 274, -1, -1, -1, -1, 274, -1, -1, -1, 274, 274, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 277, 277, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 274, 277, 277, -1, 274, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 101, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 337, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 337, 337, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 337, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 284, -1, -1, -1, -1, -1, -1, -1, 284, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 281, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 281, 281, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 281, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 199, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 199, 199, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 125, 199, -1, -1, -1],
    [-1, 259, 259, 259, 259, -1, -1, -1, 259, -1, -1, -1, -1, 259, -1, -1, 259, -1, -1, -1, 259, -1, -1, -1, -1, -1, 259, 259, 259, -1, 259, -1, -1, 259, -1, 259, -1, 259, -1, -1, -1, -1, -1, 259, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 259, -1, -1, 259, 259, -1, 259, -1, -1, 259, -1, -1, 259, -1, -1, -1, -1, 259, -1, -1, -1, 259, 259, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 259, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 259, -1, -1, -1, 259, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 178, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 178, 178, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 178, 178, -1, -1, -1],
    [-1, -1, -1, -1, -1, 319, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 319, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 285, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 285, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [56, -1, -1, 386, -1, -1, -1, -1, 386, -1, -1, -1, -1, -1, -1, -1, 386, -1, 56, -1, -1, -1, -1, -1, -1, 56, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 56, -1, -1, 56, -1, -1, -1, -1, -1, -1, -1, 56, -1, 56, -1, -1, -1, -1, -1, -1, -1, -1, 56, -1, -1, -1, -1, -1, 56, 386, -1, -1, -1, -1, -1, -1, -1, -1, 56, -1, -1, -1, -1, -1, 56, -1, 56, -1, 56, -1, -1, -1, -1, -1, -1, -1, 56, -1, -1, 56, -1, -1, -1, 56, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 56, -1, -1, -1],
    [39, -1, -1, 39, -1, -1, -1, -1, 39, -1, -1, -1, -1, -1, -1, -1, 39, -1, 39, -1, -1, -1, -1, -1, -1, 39, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 39, -1, -1, 39, -1, -1, -1, -1, -1, -1, -1, 39, -1, 39, -1, -1, -1, -1, -1, -1, -1, -1, 39, -1, -1, -1, -1, -1, 39, 39, -1, -1, -1, -1, -1, -1, -1, -1, 39, -1, -1, -1, -1, -1, 39, -1, 39, -1, 39, -1, -1, -1, -1, -1, -1, -1, 39, -1, -1, 39, -1, -1, -1, 39, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 39, -1, -1, -1],
    [82, 244, 244, 244, 244, -1, 82, 82, 244, -1, 82, -1, 82, 244, 82, 82, 244, 82, 32, 244, 82, 82, 131, 82, 244, -1, 244, 244, 82, 82, 244, -1, 82, 244, -1, 244, -1, 244, -1, -1, 82, -1, -1, 244, -1, 244, -1, 82, 82, 32, -1, 82, 244, 82, 82, 82, 244, 82, 32, 82, 244, 82, 244, -1, 244, 244, 244, 82, 244, 244, 82, 244, -1, 244, 32, -1, 244, 244, 244, -1, 82, 82, 367, 244, 32, -1, 82, 82, -1, 82, 82, 82, -1, -1, 82, -1, 82, -1, 82, 32, 244, 82, 244, 82, 82, -1, 82, -1, 82, 82, 82, 82, 82, -1, 82, 9, 244, 244, 244],
    [-1, 42, 42, 42, 42, 42, -1, -1, 42, -1, -1, -1, -1, 42, -1, -1, 42, -1, -1, -1, 42, -1, -1, -1, -1, -1, 42, 42, 42, -1, 42, -1, -1, 42, -1, 42, -1, 42, -1, -1, -1, -1, 42, 42, -1, -1, -1, 42, -1, -1, -1, -1, -1, -1, -1, -1, 42, -1, -1, 139, 42, -1, 42, 42, -1, 42, -1, -1, 42, -1, -1, -1, 42, 42, -1, -1, -1, 42, 42, -1, -1, -1, -1, -1, -1, -1, -1, -1, 42, -1, -1, -1, 42, 42, -1, -1, -1, -1, -1, -1, -1, -1, 42, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 42, 42, 42, -1, 42, -1],
    [-1, -1, 423, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [136, 119, 119, 119, 119, -1, -1, -1, 119, -1, -1, -1, -1, 119, -1, -1, 119, -1, 136, 136, 136, -1, -1, -1, 136, -1, 119, 119, -1, -1, 119, -1, -1, 119, -1, 119, 136, 119, -1, 136, -1, -1, -1, 119, -1, 136, -1, 136, -1, 136, -1, -1, 136, -1, -1, -1, 119, -1, 136, 136, 119, -1, 119, -1, 136, 119, 136, -1, 119, 136, -1, 136, -1, 119, 136, -1, 136, 119, 119, -1, 136, -1, 136, 136, 136, -1, -1, -1, -1, -1, -1, -1, 136, -1, -1, 136, -1, -1, -1, 136, 136, -1, 119, -1, -1, -1, -1, 136, -1, -1, -1, -1, -1, 119, -1, 136, -1, 119, 136],
    [389, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 389, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 389, -1, -1, -1, -1, -1, -1, -1, 389, -1, -1, 389, -1, 389, -1, -1, -1, -1, -1, -1, -1, -1, 389, 380, -1, -1, -1, -1, 389, -1, -1, -1, -1, -1, -1, -1, -1, -1, 389, -1, -1, -1, -1, -1, 389, -1, 389, -1, 389, -1, -1, -1, -1, -1, -1, -1, 389, -1, -1, 389, -1, -1, -1, 389, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 389, -1, -1, -1],
    [371, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 371, -1, -1, -1, -1, -1, -1, 188, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 371, -1, -1, 371, -1, -1, -1, -1, -1, -1, -1, 371, -1, 371, -1, -1, -1, -1, -1, -1, -1, -1, 371, -1, -1, -1, -1, -1, 371, -1, -1, -1, -1, -1, -1, -1, -1, -1, 371, -1, -1, -1, -1, -1, 371, -1, 371, -1, 371, -1, -1, -1, -1, -1, -1, -1, 371, -1, -1, 371, -1, -1, -1, 371, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 371, -1, -1, -1],
    [118, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 118, -1, 118, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 118, -1, -1, 118, -1, -1, -1, -1, -1, -1, -1, 118, -1, 118, -1, -1, -1, -1, -1, -1, -1, -1, 118, -1, -1, -1, -1, -1, 118, -1, -1, -1, -1, -1, -1, -1, -1, -1, 118, -1, -1, -1, -1, -1, 118, -1, 118, -1, 118, -1, -1, -1, -1, -1, -1, -1, 118, -1, -1, 118, -1, -1, -1, 118, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 118, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 81, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 21, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, 302, 302, 302, 302, -1, -1, -1, 302, -1, -1, -1, -1, 302, -1, -1, 302, -1, -1, -1, 372, -1, -1, -1, -1, -1, 302, 302, 372, -1, 302, -1, -1, 302, -1, 302, -1, 302, -1, -1, -1, -1, -1, 302, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 302, -1, -1, 372, 302, -1, 302, -1, -1, 302, -1, -1, 302, -1, -1, -1, -1, 302, -1, -1, -1, 302, 302, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 302, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 302, -1, -1, -1, 302, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 370, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, 147, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 147, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 147, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 147, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 306, 147, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 147, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, 53, -1, -1, -1, -1, 53, -1, -1, -1, -1, -1, -1, -1, 53, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 8, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [310, -1, -1, 105, -1, -1, -1, -1, 105, -1, -1, -1, -1, -1, -1, -1, 105, -1, 310, -1, -1, -1, -1, -1, -1, 310, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 310, -1, -1, 310, -1, -1, -1, -1, -1, -1, -1, 310, -1, 310, -1, -1, -1, -1, -1, -1, -1, -1, 310, -1, -1, -1, -1, -1, 310, 105, -1, -1, -1, -1, -1, -1, -1, -1, 310, -1, -1, -1, -1, -1, 310, -1, 310, -1, 310, -1, -1, -1, -1, -1, -1, -1, 310, -1, -1, 310, -1, -1, -1, 310, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 310, -1, -1, -1],
    [-1, -1, -1, -1, -1, 268, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 268, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 27, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 27, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 27, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 159, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 29, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 224, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 29, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [215, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 215, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 215, -1, -1, -1, -1, -1, -1, -1, 215, -1, -1, 215, -1, 215, -1, -1, -1, -1, 215, 215, -1, -1, 215, 215, -1, -1, -1, -1, 215, -1, -1, -1, -1, -1, -1, -1, -1, -1, 215, -1, -1, -1, -1, -1, 215, -1, 215, -1, 215, -1, -1, -1, -1, -1, -1, 215, 215, -1, -1, 215, -1, -1, -1, 215, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 215, -1, -1, -1],
    [-1, -1, -1, 57, -1, 57, -1, -1, 57, -1, -1, -1, -1, -1, -1, -1, 57, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 57, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 57, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 57, -1, -1, -1, -1, -1, -1, 57, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 57, 57, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 57, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 84, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 84, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 106, -1, -1, -1, -1, -1, -1, -1, 106, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 409, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 127, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [59, -1, -1, 59, -1, -1, -1, -1, 59, -1, -1, -1, -1, -1, -1, -1, 59, -1, 59, -1, -1, -1, -1, -1, -1, 192, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 59, -1, -1, 59, -1, -1, -1, -1, -1, -1, -1, 59, -1, 59, -1, -1, -1, -1, -1, -1, -1, -1, 59, -1, -1, -1, -1, -1, 59, 59, -1, -1, -1, -1, -1, -1, -1, -1, 59, -1, -1, -1, -1, -1, 59, -1, 59, -1, 59, -1, -1, -1, -1, -1, -1, -1, 59, -1, -1, 59, -1, -1, -1, 59, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 59, -1, -1, -1],
    [129, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 129, -1, 138, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 129, -1, -1, 129, -1, -1, -1, -1, -1, -1, -1, 129, 138, 129, -1, -1, -1, -1, -1, -1, -1, -1, 129, -1, -1, -1, -1, -1, 129, -1, -1, -1, -1, -1, -1, -1, -1, -1, 129, -1, -1, -1, -1, -1, 129, -1, 129, -1, 129, -1, -1, -1, -1, -1, -1, -1, 129, -1, -1, 129, -1, -1, -1, 129, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 129, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 303, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 137, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 187, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [179, -1, -1, -1, -1, -1, -1, 179, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 384, -1, 179, -1, -1, -1, -1, -1, -1, -1, 98, -1, -1, -1, -1, -1, -1, -1, 384, -1, -1, -1, -1, -1, -1, -1, 384, -1, -1, 384, 179, 384, -1, 179, -1, -1, 179, 406, -1, -1, 384, 406, -1, -1, -1, -1, 384, -1, -1, -1, -1, -1, 179, -1, -1, -1, 384, -1, -1, -1, -1, -1, 179, -1, 384, -1, 384, -1, -1, -1, -1, -1, -1, 406, 384, -1, -1, 384, -1, -1, -1, 384, -1, -1, -1, -1, -1, 179, -1, -1, -1, -1, -1, -1, -1, -1, 179, 384, -1, -1, -1],
    [28, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 28, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 28, -1, -1, 28, -1, -1, -1, -1, -1, -1, -1, 28, -1, 28, -1, -1, -1, -1, -1, -1, -1, -1, 28, -1, -1, -1, -1, -1, 28, 114, -1, -1, -1, -1, -1, -1, -1, -1, 28, -1, -1, -1, -1, -1, 28, -1, 28, -1, 28, -1, -1, -1, -1, -1, -1, -1, 28, -1, -1, 28, -1, -1, -1, 28, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 28, -1, -1, -1],
    [116, 116, 116, 116, 116, -1, -1, -1, 116, -1, -1, -1, -1, 116, -1, -1, 116, -1, 116, 116, 116, -1, -1, -1, 116, -1, 116, 116, -1, -1, 116, -1, -1, 116, -1, 116, 116, 116, -1, 116, -1, -1, -1, 116, -1, 116, -1, 116, -1, 116, -1, -1, 116, -1, -1, -1, 116, -1, 116, 116, 116, -1, 116, -1, 116, 116, 116, -1, 116, 116, -1, 116, -1, 116, 116, -1, 116, 116, 116, -1, 116, -1, 116, 116, 116, -1, -1, -1, -1, 340, -1, -1, 116, -1, -1, 116, -1, -1, -1, 116, 116, -1, 116, -1, -1, -1, -1, 116, -1, -1, -1, -1, -1, 116, -1, 116, -1, 116, 116],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 50, 50, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 50, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 203, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 203, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 16, -1, -1, -1],
    [-1, 424, 424, 424, 424, -1, -1, -1, 424, -1, -1, -1, -1, 424, -1, -1, 424, -1, -1, -1, -1, -1, -1, -1, -1, -1, 424, 424, -1, -1, 424, -1, -1, 424, -1, 424, -1, 424, -1, -1, -1, -1, -1, 424, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 424, -1, -1, -1, 424, -1, 424, -1, -1, 424, -1, -1, 424, -1, -1, -1, -1, 424, -1, -1, -1, 424, 424, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 424, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 424, -1, -1, -1, 424, -1],
    [124, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 124, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 124, -1, -1, -1, -1, -1, -1, -1, 124, -1, -1, 124, -1, 124, -1, -1, -1, -1, 359, 359, -1, -1, 124, 124, -1, -1, -1, -1, 124, -1, -1, -1, -1, -1, -1, -1, -1, -1, 124, -1, -1, -1, -1, -1, 124, -1, 124, -1, 124, -1, -1, -1, -1, -1, -1, 359, 124, -1, -1, 124, -1, -1, -1, 124, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 124, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 34, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 312, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 300, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 112, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [207, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 207, 265, 207, -1, -1, -1, 265, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 207, -1, -1, 207, -1, -1, -1, -1, -1, 314, -1, 207, -1, 207, -1, -1, 314, -1, -1, -1, -1, -1, 207, 413, -1, -1, -1, -1, 207, -1, 176, -1, -1, 292, -1, 292, -1, -1, 207, -1, 265, -1, -1, -1, 207, -1, 207, 292, 207, -1, -1, -1, -1, -1, -1, -1, 207, -1, -1, 207, -1, -1, -1, 207, 176, -1, -1, -1, -1, -1, -1, 176, -1, -1, -1, -1, -1, -1, -1, 207, -1, -1, 292],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 73, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 79, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 421, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 425, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 330, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 142, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 142, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, 97, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 420, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [331, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 331, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 331, -1, -1, -1, -1, -1, -1, -1, 331, -1, -1, 331, -1, 331, -1, -1, -1, -1, -1, -1, -1, -1, 331, -1, -1, -1, -1, -1, 331, -1, -1, -1, -1, -1, -1, -1, -1, -1, 331, -1, -1, -1, -1, -1, 331, -1, 331, -1, 331, -1, -1, -1, -1, -1, -1, -1, 331, -1, -1, 331, -1, -1, -1, 331, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 331, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 69, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 44, -1, -1, -1, -1, -1, -1, 17, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, 234, -1, 237, -1, -1, 234, -1, -1, -1, -1, -1, -1, -1, 234, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 237, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 237, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 237, -1, -1, -1, -1, -1, -1, 237, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 237, 237, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 237, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 100, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 140, 140, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 144, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [72, 72, 72, 72, 72, -1, -1, -1, 72, -1, -1, 72, -1, 72, -1, -1, 72, -1, 72, 72, 72, -1, -1, -1, 72, -1, 72, 72, -1, -1, 72, -1, -1, 72, -1, 72, 72, 72, -1, 72, -1, -1, -1, 72, -1, 72, -1, 72, -1, 72, 72, -1, 72, -1, -1, -1, 72, -1, 72, 72, 72, -1, 72, -1, 72, 72, 72, -1, 72, 72, -1, 72, -1, 72, 72, -1, 72, 72, 72, -1, 72, -1, 72, 72, 72, -1, -1, -1, -1, 72, -1, -1, 72, -1, -1, 72, -1, -1, -1, 72, 72, -1, 72, -1, -1, -1, -1, 72, -1, -1, -1, -1, -1, 72, -1, 72, 72, 72, 72],
    [141, 141, 141, 141, 141, -1, -1, -1, 141, -1, -1, 301, -1, 141, -1, -1, 141, -1, 141, 141, 141, -1, -1, -1, 141, -1, 141, 141, -1, -1, 141, -1, -1, 141, -1, 141, 141, 141, -1, 141, -1, -1, -1, 141, -1, 141, -1, 141, -1, 141, 141, -1, 141, -1, -1, -1, 141, -1, 141, 141, 141, -1, 141, -1, 141, 141, 141, -1, 141, 141, -1, 141, -1, 141, 141, -1, 141, 141, 141, -1, 141, -1, 141, 141, 141, -1, -1, -1, -1, 141, -1, -1, 141, -1, -1, 141, -1, -1, -1, 141, 141, -1, 141, -1, -1, -1, -1, 141, -1, -1, -1, -1, -1, 141, -1, 141, 141, 141, 141],
    [-1, -1, -1, -1, -1, 130, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [22, -1, -1, -1, -1, -1, 334, 48, -1, -1, 362, -1, 108, -1, 228, 45, -1, 154, -1, -1, 418, 107, -1, 171, -1, -1, -1, -1, 51, 36, -1, -1, 168, -1, -1, -1, -1, -1, -1, -1, 355, -1, -1, -1, -1, -1, -1, 321, 329, -1, -1, 143, -1, 327, 204, 323, -1, 94, -1, 400, -1, 10, -1, -1, -1, -1, -1, 148, -1, -1, 87, -1, -1, -1, -1, -1, -1, -1, -1, -1, 43, 196, -1, -1, -1, -1, 83, 344, -1, 24, 317, 181, -1, -1, 155, -1, 363, -1, 102, -1, -1, 339, -1, 391, 115, -1, 12, -1, 304, 157, 395, 117, 248, -1, 202, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 4, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 165, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 276, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 345, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 77, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 189, -1, -1, -1, -1, -1, -1, 419, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [173, 173, 173, 173, 173, -1, -1, -1, 173, -1, -1, -1, -1, 173, -1, -1, 173, -1, 173, 173, 173, -1, -1, -1, 173, -1, 173, 173, -1, -1, 173, -1, -1, 173, -1, 173, 173, 173, -1, 173, -1, -1, -1, 173, -1, 173, -1, 173, -1, 173, 173, -1, 173, -1, -1, -1, 173, -1, 173, 173, 173, -1, 173, -1, 173, 173, 173, -1, 173, 173, -1, 173, -1, 173, 173, -1, 173, 173, 173, -1, 173, -1, 173, 173, 173, -1, -1, -1, -1, 173, -1, -1, 173, -1, -1, 173, -1, -1, -1, 173, 173, -1, 173, -1, -1, -1, -1, 173, -1, -1, -1, -1, -1, 173, -1, 173, 170, 173, 173],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 146, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [128, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 128, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 128, -1, -1, -1, -1, -1, -1, -1, 128, -1, -1, 128, -1, 128, -1, -1, -1, -1, 128, 128, -1, -1, 128, 128, -1, -1, -1, -1, 128, -1, -1, -1, -1, -1, -1, -1, -1, -1, 128, -1, -1, -1, -1, -1, 128, -1, 128, -1, 128, -1, -1, -1, -1, -1, -1, 128, 128, -1, -1, 128, -1, -1, -1, 128, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 128, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 88, -1, -1, -1, -1, 208, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 343, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, 38, 38, 3, 63, -1, -1, -1, 3, -1, -1, -1, -1, 38, -1, -1, 3, -1, -1, -1, -1, -1, -1, -1, -1, -1, 38, 63, -1, -1, 38, -1, -1, 38, -1, 38, -1, 63, -1, -1, -1, -1, -1, 38, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 38, -1, -1, -1, 38, -1, 89, -1, -1, 63, -1, -1, 38, -1, -1, -1, -1, 38, -1, -1, -1, 38, 38, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 63, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 38, -1, -1, -1, 38, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 347, -1, 369, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 320, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 366],
    [-1, 403, 403, 403, 403, 407, -1, -1, 403, -1, -1, -1, -1, 403, -1, -1, 403, -1, -1, -1, 407, -1, -1, -1, -1, -1, 403, 403, 407, -1, 403, -1, -1, 403, -1, 403, -1, 403, -1, -1, -1, -1, 407, 403, -1, -1, -1, 407, -1, -1, -1, -1, -1, -1, -1, -1, 403, -1, -1, -1, 403, -1, 403, 407, -1, 403, -1, -1, 403, -1, -1, -1, 407, 403, -1, -1, -1, 403, 403, -1, -1, -1, -1, -1, -1, -1, -1, -1, 407, -1, -1, -1, 407, 407, -1, -1, -1, -1, -1, -1, -1, -1, 403, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 403, -1, 407, -1, 403, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 226, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 212, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 212, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 286, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 328, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [404, 404, 404, 404, 404, -1, -1, -1, 404, -1, -1, 185, -1, 404, -1, -1, 404, -1, 404, 404, 404, -1, -1, -1, 404, -1, 404, 404, -1, -1, 404, -1, -1, 404, -1, 404, 404, 404, -1, 404, -1, -1, -1, 404, -1, 404, -1, 404, -1, 404, 404, -1, 404, -1, -1, -1, 404, -1, 404, 404, 404, -1, 404, -1, 404, 404, 404, -1, 404, 404, -1, 404, -1, 404, 404, -1, 404, 404, 404, -1, 404, -1, 404, 404, 404, -1, -1, -1, -1, 404, -1, -1, 404, -1, -1, 404, -1, -1, -1, 404, 404, -1, 404, -1, -1, -1, -1, 404, -1, -1, -1, -1, -1, 404, -1, 404, 404, 404, 404],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 354, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 55, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 405, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, 247, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 247, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 242, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 242, 242, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 242, -1, -1, -1],
    [-1, -1, -1, -1, -1, 86, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 5, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 262, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 25, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 19, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 25, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 25, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 123, -1, -1, -1, -1, -1, -1, -1, 123, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 64, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 20, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 205, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [121, 121, 121, 121, 121, -1, -1, -1, 121, -1, -1, -1, -1, 121, -1, -1, 121, -1, 121, 121, 121, -1, -1, -1, 121, -1, 121, 121, -1, -1, 121, -1, -1, 121, -1, 121, 121, 121, -1, 121, -1, -1, -1, 121, -1, 121, -1, 121, -1, 121, -1, -1, 121, -1, -1, -1, 121, -1, 121, 121, 121, -1, 121, -1, 121, 121, 121, -1, 121, 121, -1, 121, -1, 121, 121, -1, 121, 121, 121, -1, 121, -1, 121, 121, 121, -1, -1, -1, -1, 121, -1, -1, 121, -1, -1, 121, -1, -1, -1, 121, 121, -1, 121, -1, -1, -1, -1, 121, -1, -1, -1, -1, -1, 121, -1, 121, -1, 121, 121],
    [99, 99, 99, 99, 99, -1, -1, -1, 99, -1, -1, -1, -1, 99, -1, -1, 99, -1, 99, 99, 99, -1, -1, -1, 99, -1, 99, 99, -1, -1, 99, -1, -1, 99, -1, 99, 99, 99, -1, 99, -1, -1, -1, 99, -1, 99, -1, 99, -1, 99, -1, -1, 99, -1, -1, -1, 99, -1, 99, 99, 99, -1, 99, -1, 99, 99, 99, -1, 99, 99, -1, 99, -1, 99, 99, -1, 99, 99, 99, -1, 99, -1, 99, 99, 99, -1, -1, -1, -1, 99, -1, -1, 99, -1, -1, 99, -1, -1, -1, 99, 99, -1, 99, -1, -1, -1, -1, 99, -1, -1, -1, -1, -1, 99, -1, 99, -1, 99, 99],
    [396, -1, -1, 396, -1, -1, -1, -1, 396, -1, -1, -1, -1, -1, -1, -1, 396, -1, 396, -1, -1, -1, -1, -1, -1, 396, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 396, -1, -1, 396, -1, -1, -1, -1, -1, -1, -1, 396, -1, 396, -1, -1, -1, -1, -1, -1, -1, -1, 396, -1, -1, -1, -1, -1, 396, 396, -1, -1, -1, -1, -1, -1, -1, -1, 396, -1, -1, -1, -1, -1, 396, -1, 396, -1, 396, -1, -1, -1, -1, -1, -1, -1, 396, -1, -1, 396, -1, -1, -1, 396, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 396, -1, -1, -1],
  ]
  TERMINAL_DECR = 0
  TERMINAL_UNSIGNED = 1
  TERMINAL_STRUCT = 2
  TERMINAL_CONST = 3
  TERMINAL_TYPEDEF = 4
  TERMINAL_COMMA_VA_ARGS = 5
  TERMINAL_SUBEQ = 6
  TERMINAL_QUESTIONMARK = 7
  TERMINAL_RESTRICT = 8
  TERMINAL_SIZEOF_SEPARATOR = 9
  TERMINAL_BITOREQ = 10
  TERMINAL_ELSE_IF = 11
  TERMINAL_LSHIFTEQ = 12
  TERMINAL_INT = 13
  TERMINAL_GTEQ = 14
  TERMINAL_NEQ = 15
  TERMINAL_VOLATILE = 16
  TERMINAL_MODEQ = 17
  TERMINAL_CHARACTER_CONSTANT = 18
  TERMINAL_DO = 19
  TERMINAL_SEMI = 20
  TERMINAL_EQ = 21
  TERMINAL_PP_NUMBER = 22
  TERMINAL_POUNDPOUND = 23
  TERMINAL_FOR = 24
  TERMINAL_VARIABLE_LENGTH_ARRAY = 25
  TERMINAL_LONG = 26
  TERMINAL_EXTERN = 27
  TERMINAL_COMMA = 28
  TERMINAL_BITOR = 29
  TERMINAL_DOUBLE = 30
  TERMINAL_NAMED_PARAMETER_HINT = 31
  TERMINAL_MOD = 32
  TERMINAL_FLOAT = 33
  TERMINAL_DIVEQ = 34
  TERMINAL_ENUM = 35
  TERMINAL_BITAND = 36
  TERMINAL_REGISTER = 37
  TERMINAL_NOT = 38
  TERMINAL__EXPR = 39
  TERMINAL_LTEQ = 40
  TERMINAL_BITNOT = 41
  TERMINAL_FUNCTION_DEFINITION_HINT = 42
  TERMINAL_CHAR = 43
  TERMINAL__EXPR_SANS_COMMA = 44
  TERMINAL_IF = 45
  TERMINAL_UNIVERSAL_CHARACTER_NAME = 46
  TERMINAL_LPAREN = 47
  TERMINAL_RPAREN = 48
  TERMINAL_INTEGER_CONSTANT = 49
  TERMINAL_ENDIF = 50
  TERMINAL_ARROW = 51
  TERMINAL_SWITCH = 52
  TERMINAL_ELIPSIS = 53
  TERMINAL_DOT = 54
  TERMINAL_LSQUARE = 55
  TERMINAL_UNION = 56
  TERMINAL_BITANDEQ = 57
  TERMINAL_ENUMERATION_CONSTANT = 58
  TERMINAL_LBRACE = 59
  TERMINAL_BOOL = 60
  TERMINAL_ADDEQ = 61
  TERMINAL_INLINE = 62
  TERMINAL_DECLARATOR_HINT = 63
  TERMINAL_SIZEOF = 64
  TERMINAL_STATIC = 65
  TERMINAL_DEFAULT = 66
  TERMINAL_BITXOREQ = 67
  TERMINAL_SHORT = 68
  TERMINAL_BREAK = 69
  TERMINAL_RSQUARE = 70
  TERMINAL_GOTO = 71
  TERMINAL__DIRECT_ABSTRACT_DECLARATOR = 72
  TERMINAL_SIGNED = 73
  TERMINAL_DECIMAL_FLOATING_CONSTANT = 74
  TERMINAL_EXTERNAL_DECLARATION_HINT = 75
  TERMINAL_WHILE = 76
  TERMINAL_IMAGINARY = 77
  TERMINAL_COMPLEX = 78
  TERMINAL_DEFINED_SEPARATOR = 79
  TERMINAL_INCR = 80
  TERMINAL_GT = 81
  TERMINAL_STRING_LITERAL = 82
  TERMINAL_CONTINUE = 83
  TERMINAL_HEXADECIMAL_FLOATING_CONSTANT = 84
  TERMINAL_ABSTRACT_PARAMETER_HINT = 85
  TERMINAL_BITXOR = 86
  TERMINAL_AND = 87
  TERMINAL_FUNCTION_PROTOTYPE_HINT = 88
  TERMINAL_RBRACE = 89
  TERMINAL_MULEQ = 90
  TERMINAL_ASSIGN = 91
  TERMINAL_ASTERISK = 92
  TERMINAL__DIRECT_DECLARATOR = 93
  TERMINAL_POUND = 94
  TERMINAL_LPAREN_CAST = 95
  TERMINAL_ADD = 96
  TERMINAL_DEFINED = 97
  TERMINAL_LSHIFT = 98
  TERMINAL_FLOATING_CONSTANT = 99
  TERMINAL_CASE = 100
  TERMINAL_SUB = 101
  TERMINAL_AUTO = 102
  TERMINAL_DIV = 103
  TERMINAL_RSHIFT = 104
  TERMINAL_TRAILING_COMMA = 105
  TERMINAL_RSHIFTEQ = 106
  TERMINAL_LABEL_HINT = 107
  TERMINAL_EXCLAMATION_POINT = 108
  TERMINAL_OR = 109
  TERMINAL_TILDE = 110
  TERMINAL_AMPERSAND = 111
  TERMINAL_LT = 112
  TERMINAL_TYPEDEF_IDENTIFIER = 113
  TERMINAL_COLON = 114
  TERMINAL_IDENTIFIER = 115
  TERMINAL_ELSE = 116
  TERMINAL_VOID = 117
  TERMINAL_RETURN = 118
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
  def parse_external_declaration_sub_sub(self):
    current = self.tokens.current()
    rule = self.table[0][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(119, self.nonterminals[119]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 49:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_external_declarator()
      tree.add( subtree )
      return tree
    elif rule == 388:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_external_prototype()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_init_declarator_list(self):
    current = self.tokens.current()
    rule = self.table[1][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(120, self.nonterminals[120]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 280:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen9()
      tree.add( subtree )
      return tree
    elif current.getId() in [47, 93, 115]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen9()
      tree.add( subtree )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen8(self):
    current = self.tokens.current()
    rule = self.table[2][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(121, self.nonterminals[121]))
    tree.list = False
    if current != None and (current.getId() in [20]):
      return tree
    if current == None:
      return tree
    if rule == 6:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_init_declarator_list()
      tree.add( subtree )
      return tree
    elif current.getId() in [47, 93, 115]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_init_declarator_list()
      tree.add( subtree )
    return tree
  def parse__gen20(self):
    current = self.tokens.current()
    rule = self.table[3][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(122, self.nonterminals[122]))
    tree.list = 'slist'
    if current != None and (current.getId() in [20]):
      return tree
    if current == None:
      return tree
    if rule == 288:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(28) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self.parse_struct_declarator()
      tree.add( subtree )
      subtree = self.parse__gen20()
      tree.add( subtree )
      return tree
    return tree
  def parse__gen4(self):
    current = self.tokens.current()
    rule = self.table[4][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(123, self.nonterminals[123]))
    tree.list = 'slist'
    if current != None and (current.getId() in [20]):
      return tree
    if current == None:
      return tree
    if rule == 217:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(28) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self.parse_external_declaration_sub_sub()
      tree.add( subtree )
      subtree = self.parse__gen4()
      tree.add( subtree )
      return tree
    return tree
  def parse_designator(self):
    current = self.tokens.current()
    rule = self.table[5][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(124, self.nonterminals[124]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 40:
      tree.astTransform = AstTransformNodeCreator('ArrayAccess', {'index': 1})
      t = self.expect(55) # lsquare
      tree.add(t)
      subtree = self.parse__expr()
      tree.add( subtree )
      t = self.expect(70) # rsquare
      tree.add(t)
      return tree
    elif rule == 271:
      tree.astTransform = AstTransformNodeCreator('MemberAccess', {'name': 1})
      t = self.expect(54) # dot
      tree.add(t)
      t = self.expect(115) # identifier
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_keyword(self):
    current = self.tokens.current()
    rule = self.table[6][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(125, self.nonterminals[125]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 13:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(30) # double
      tree.add(t)
      return tree
    elif rule == 18:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(33) # float
      tree.add(t)
      return tree
    elif rule == 26:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(52) # switch
      tree.add(t)
      return tree
    elif rule == 30:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(45) # if
      tree.add(t)
      return tree
    elif rule == 35:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(2) # struct
      tree.add(t)
      return tree
    elif rule == 37:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(27) # extern
      tree.add(t)
      return tree
    elif rule == 61:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(26) # long
      tree.add(t)
      return tree
    elif rule == 67:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(4) # typedef
      tree.add(t)
      return tree
    elif rule == 71:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(37) # register
      tree.add(t)
      return tree
    elif rule == 96:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(117) # void
      tree.add(t)
      return tree
    elif rule == 109:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(13) # int
      tree.add(t)
      return tree
    elif rule == 113:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(116) # else
      tree.add(t)
      return tree
    elif rule == 126:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(62) # inline
      tree.add(t)
      return tree
    elif rule == 150:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(100) # case
      tree.add(t)
      return tree
    elif rule == 152:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(8) # restrict
      tree.add(t)
      return tree
    elif rule == 162:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(24) # for
      tree.add(t)
      return tree
    elif rule == 164:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(56) # union
      tree.add(t)
      return tree
    elif rule == 175:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(43) # char
      tree.add(t)
      return tree
    elif rule == 182:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(77) # imaginary
      tree.add(t)
      return tree
    elif rule == 220:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(65) # static
      tree.add(t)
      return tree
    elif rule == 231:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(69) # break
      tree.add(t)
      return tree
    elif rule == 233:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(1) # unsigned
      tree.add(t)
      return tree
    elif rule == 241:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(83) # continue
      tree.add(t)
      return tree
    elif rule == 246:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(64) # sizeof
      tree.add(t)
      return tree
    elif rule == 296:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(71) # goto
      tree.add(t)
      return tree
    elif rule == 318:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(76) # while
      tree.add(t)
      return tree
    elif rule == 325:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(60) # bool
      tree.add(t)
      return tree
    elif rule == 336:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(16) # volatile
      tree.add(t)
      return tree
    elif rule == 341:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(73) # signed
      tree.add(t)
      return tree
    elif rule == 342:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(19) # do
      tree.add(t)
      return tree
    elif rule == 351:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(102) # auto
      tree.add(t)
      return tree
    elif rule == 352:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(118) # return
      tree.add(t)
      return tree
    elif rule == 376:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(66) # default
      tree.add(t)
      return tree
    elif rule == 378:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(3) # const
      tree.add(t)
      return tree
    elif rule == 381:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(78) # complex
      tree.add(t)
      return tree
    elif rule == 410:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(35) # enum
      tree.add(t)
      return tree
    elif rule == 411:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(68) # short
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_named_parameter_declaration(self):
    current = self.tokens.current()
    rule = self.table[7][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(126, self.nonterminals[126]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 70:
      tree.astTransform = AstTransformNodeCreator('NamedParameter', {'declaration_specifiers': 1, 'declarator': 2})
      t = self.expect(31) # named_parameter_hint
      tree.add(t)
      subtree = self.parse__gen1()
      tree.add( subtree )
      subtree = self.parse__gen34()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_storage_class_specifier(self):
    current = self.tokens.current()
    rule = self.table[8][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(127, self.nonterminals[127]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 0:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(4) # typedef
      tree.add(t)
      return tree
    elif rule == 31:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(65) # static
      tree.add(t)
      return tree
    elif rule == 78:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(27) # extern
      tree.add(t)
      return tree
    elif rule == 348:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(102) # auto
      tree.add(t)
      return tree
    elif rule == 358:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(37) # register
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_sizeof_body(self):
    current = self.tokens.current()
    rule = self.table[9][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(128, self.nonterminals[128]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 75:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(47) # lparen
      tree.add(t)
      subtree = self.parse_type_name()
      tree.add( subtree )
      t = self.expect(48) # rparen
      tree.add(t)
      return tree
    elif rule == 412:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(115) # identifier
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_struct_or_union_body(self):
    current = self.tokens.current()
    rule = self.table[10][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(129, self.nonterminals[129]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 134:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(59) # lbrace
      tree.add(t)
      subtree = self.parse__gen17()
      tree.add( subtree )
      t = self.expect(89) # rbrace
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen16(self):
    current = self.tokens.current()
    rule = self.table[11][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(130, self.nonterminals[130]))
    tree.list = False
    if current != None and (current.getId() in [1, 93, 60, 2, 3, 4, 43, 56, 63, 8, 68, 73, 114, 16, 115, 77, 92, 35, 27, 26, 28, 88, 78, 65, 33, 102, 30, 42, 5, 37, 62, 47, 113, 20, 117, 13, 72]):
      return tree
    if current == None:
      return tree
    if rule == 230:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_struct_or_union_body()
      tree.add( subtree )
      return tree
    return tree
  def parse_constant(self):
    current = self.tokens.current()
    rule = self.table[12][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(131, self.nonterminals[131]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 169:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(49) # integer_constant
      tree.add(t)
      return tree
    elif rule == 295:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(58) # enumeration_constant
      tree.add(t)
      return tree
    elif rule == 313:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(84) # hexadecimal_floating_constant
      tree.add(t)
      return tree
    elif rule == 353:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(99) # floating_constant
      tree.add(t)
      return tree
    elif rule == 397:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(18) # character_constant
      tree.add(t)
      return tree
    elif rule == 401:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(74) # decimal_floating_constant
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_type_specifier(self):
    current = self.tokens.current()
    rule = self.table[13][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(132, self.nonterminals[132]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 23:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(43) # char
      tree.add(t)
      return tree
    elif rule == 41:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(26) # long
      tree.add(t)
      return tree
    elif rule == 46:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(60) # bool
      tree.add(t)
      return tree
    elif rule == 60:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(68) # short
      tree.add(t)
      return tree
    elif rule == 62:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(1) # unsigned
      tree.add(t)
      return tree
    elif rule == 85:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(30) # double
      tree.add(t)
      return tree
    elif rule == 103:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_union_specifier()
      tree.add( subtree )
      return tree
    elif rule == 133:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(13) # int
      tree.add(t)
      return tree
    elif rule == 149:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(117) # void
      tree.add(t)
      return tree
    elif rule == 156:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_struct_specifier()
      tree.add( subtree )
      return tree
    elif rule == 174:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(77) # imaginary
      tree.add(t)
      return tree
    elif rule == 201:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_enum_specifier()
      tree.add( subtree )
      return tree
    elif rule == 210:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(33) # float
      tree.add(t)
      return tree
    elif rule == 326:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(78) # complex
      tree.add(t)
      return tree
    elif rule == 393:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(73) # signed
      tree.add(t)
      return tree
    elif rule == 422:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_typedef_name()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen1(self):
    current = self.tokens.current()
    rule = self.table[14][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(133, self.nonterminals[133]))
    tree.list = 'mlist'
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 399:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_declaration_specifier()
      tree.add( subtree )
      subtree = self.parse__gen2()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_for_init(self):
    current = self.tokens.current()
    rule = self.table[15][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(134, self.nonterminals[134]))
    tree.list = False
    if current != None and (current.getId() in [20]):
      return tree
    if current == None:
      return tree
    if rule == 76:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_declaration()
      tree.add( subtree )
      subtree = self.parse_expression_opt()
      tree.add( subtree )
      return tree
    elif rule == 92:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__expr()
      tree.add( subtree )
      return tree
    elif current.getId() in [0, 82, 95, 49, 58, 80, 36, 64, 115, 39, 74, 18, 47, 92, 99, 84]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__expr()
      tree.add( subtree )
    return tree
  def parse_external_declarator(self):
    current = self.tokens.current()
    rule = self.table[16][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(135, self.nonterminals[135]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 324:
      tree.astTransform = AstTransformNodeCreator('ExternalDeclarator', {'init_declarator': 1})
      t = self.expect(63) # declarator_hint
      tree.add(t)
      subtree = self.parse__gen6()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_for_incr(self):
    current = self.tokens.current()
    rule = self.table[17][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(136, self.nonterminals[136]))
    tree.list = False
    if current != None and (current.getId() in [48]):
      return tree
    if current == None:
      return tree
    if rule == 153:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(20) # semi
      tree.add(t)
      subtree = self.parse_expression_opt()
      tree.add( subtree )
      return tree
    return tree
  def parse_type_qualifier(self):
    current = self.tokens.current()
    rule = self.table[18][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(137, self.nonterminals[137]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 15:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(16) # volatile
      tree.add(t)
      return tree
    elif rule == 91:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(8) # restrict
      tree.add(t)
      return tree
    elif rule == 95:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(3) # const
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_struct_or_union_sub(self):
    current = self.tokens.current()
    rule = self.table[19][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(138, self.nonterminals[138]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 2:
      tree.astTransform = AstTransformNodeCreator('StructOrUnion', {'body': 1, 'name': 0})
      t = self.expect(115) # identifier
      tree.add(t)
      subtree = self.parse__gen16()
      tree.add( subtree )
      return tree
    elif rule == 68:
      tree.astTransform = AstTransformNodeCreator('StructOrUnion', {'body': 0})
      subtree = self.parse_struct_or_union_body()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_external_prototype(self):
    current = self.tokens.current()
    rule = self.table[20][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(139, self.nonterminals[139]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 322:
      tree.astTransform = AstTransformNodeCreator('FunctionPrototype', {'declaration_list': 2, 'declarator': 1})
      t = self.expect(88) # function_prototype_hint
      tree.add(t)
      subtree = self.parse_declarator()
      tree.add( subtree )
      subtree = self.parse__gen5()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen46(self):
    current = self.tokens.current()
    rule = self.table[21][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(140, self.nonterminals[140]))
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
  def parse_function_specifier(self):
    current = self.tokens.current()
    rule = self.table[22][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(141, self.nonterminals[141]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 332:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(62) # inline
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_struct_declaration(self):
    current = self.tokens.current()
    rule = self.table[23][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(142, self.nonterminals[142]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 426:
      tree.astTransform = AstTransformNodeCreator('StructOrUnionDeclaration', {'specifier_qualifiers': 0, 'declarators': 1})
      subtree = self.parse__gen18()
      tree.add( subtree )
      subtree = self.parse__gen19()
      tree.add( subtree )
      t = self.expect(20) # semi
      tree.add(t)
      return tree
    elif current.getId() in [47, 93, 115]:
      tree.astTransform = AstTransformNodeCreator('StructOrUnionDeclaration', {'specifier_qualifiers': 0, 'declarators': 1})
      subtree = self.parse__gen18()
      tree.add( subtree )
      subtree = self.parse__gen19()
      tree.add( subtree )
      tree.add( self.expect(20) ) # semi
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen17(self):
    current = self.tokens.current()
    rule = self.table[24][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(143, self.nonterminals[143]))
    tree.list = 'nlist'
    if current != None and (current.getId() in [89]):
      return tree
    if current == None:
      return tree
    if rule == 254:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_struct_declaration()
      tree.add( subtree )
      subtree = self.parse__gen17()
      tree.add( subtree )
      return tree
    elif current.getId() in [47, 93, 115]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_struct_declaration()
      tree.add( subtree )
      subtree = self.parse__gen17()
      tree.add( subtree )
    return tree
  def parse_type_name(self):
    current = self.tokens.current()
    rule = self.table[25][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(144, self.nonterminals[144]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 269:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(13) # int
      tree.add(t)
      return tree
    elif rule == 289:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(43) # char
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_declarator(self):
    current = self.tokens.current()
    rule = self.table[26][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(145, self.nonterminals[145]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 383:
      tree.astTransform = AstTransformNodeCreator('Declarator', {'direct_declarator': 1, 'pointer': 0})
      subtree = self.parse__gen26()
      tree.add( subtree )
      subtree = self.parse__direct_declarator()
      tree.add( subtree )
      return tree
    elif current.getId() in [47, 93, 115]:
      tree.astTransform = AstTransformNodeCreator('Declarator', {'direct_declarator': 1, 'pointer': 0})
      subtree = self.parse__gen26()
      tree.add( subtree )
      subtree = self.parse__direct_declarator()
      tree.add( subtree )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_declaration_list(self):
    current = self.tokens.current()
    rule = self.table[27][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(146, self.nonterminals[146]))
    tree.list = False
    if current == None:
      return tree
    if rule == 415:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen7()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_enumeration_constant(self):
    current = self.tokens.current()
    rule = self.table[28][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(147, self.nonterminals[147]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 161:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(115) # identifier
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen9(self):
    current = self.tokens.current()
    rule = self.table[29][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(148, self.nonterminals[148]))
    tree.list = 'slist'
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 307:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_init_declarator()
      tree.add( subtree )
      subtree = self.parse__gen10()
      tree.add( subtree )
      return tree
    elif current.getId() in [47, 93, 115]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_init_declarator()
      tree.add( subtree )
      subtree = self.parse__gen10()
      tree.add( subtree )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen10(self):
    current = self.tokens.current()
    rule = self.table[30][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(149, self.nonterminals[149]))
    tree.list = 'slist'
    if current != None and (current.getId() in [20]):
      return tree
    if current == None:
      return tree
    if rule == 47:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(28) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self.parse_init_declarator()
      tree.add( subtree )
      subtree = self.parse__gen10()
      tree.add( subtree )
      return tree
    return tree
  def parse_abstract_declarator(self):
    current = self.tokens.current()
    rule = self.table[31][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(150, self.nonterminals[150]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 54:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_pointer()
      tree.add( subtree )
      subtree = self.parse__gen36()
      tree.add( subtree )
      return tree
    elif rule == 184:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__direct_abstract_declarator()
      tree.add( subtree )
      return tree
    elif current.getId() in [72, 47]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__direct_abstract_declarator()
      tree.add( subtree )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_pointer(self):
    current = self.tokens.current()
    rule = self.table[32][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(151, self.nonterminals[151]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 11:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen37()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_misc(self):
    current = self.tokens.current()
    rule = self.table[33][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(152, self.nonterminals[152]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 122:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(50) # endif
      tree.add(t)
      return tree
    elif rule == 417:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(46) # universal_character_name
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen26(self):
    current = self.tokens.current()
    rule = self.table[34][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(153, self.nonterminals[153]))
    tree.list = False
    if current != None and (current.getId() in [47, 93, 115]):
      return tree
    if current == None:
      return tree
    if rule == 267:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_pointer()
      tree.add( subtree )
      return tree
    return tree
  def parse__gen33(self):
    current = self.tokens.current()
    rule = self.table[35][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(154, self.nonterminals[154]))
    tree.list = 'slist'
    if current != None and (current.getId() in []):
      return tree
    if current == None:
      return tree
    if rule == 335:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(28) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self.parse_identifier()
      tree.add( subtree )
      subtree = self.parse__gen33()
      tree.add( subtree )
      return tree
    return tree
  def parse_specifier_qualifier(self):
    current = self.tokens.current()
    rule = self.table[36][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(155, self.nonterminals[155]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 191:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_type_qualifier()
      tree.add( subtree )
      return tree
    elif rule == 373:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_type_specifier()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen18(self):
    current = self.tokens.current()
    rule = self.table[37][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(156, self.nonterminals[156]))
    tree.list = 'nlist'
    if current != None and (current.getId() in [47, 92, 114, 115, 93]):
      return tree
    if current == None:
      return tree
    if rule == 274:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_specifier_qualifier()
      tree.add( subtree )
      subtree = self.parse__gen18()
      tree.add( subtree )
      return tree
    return tree
  def parse_translation_unit(self):
    current = self.tokens.current()
    rule = self.table[38][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(157, self.nonterminals[157]))
    tree.list = False
    if current == None:
      return tree
    if rule == 101:
      tree.astTransform = AstTransformNodeCreator('TranslationUnit', {'external_declarations': 0})
      subtree = self.parse__gen0()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_init_declarator(self):
    current = self.tokens.current()
    rule = self.table[40][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(159, self.nonterminals[159]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 337:
      tree.astTransform = AstTransformNodeCreator('InitDeclarator', {'initializer': 1, 'declarator': 0})
      subtree = self.parse_declarator()
      tree.add( subtree )
      subtree = self.parse__gen11()
      tree.add( subtree )
      return tree
    elif current.getId() in [47, 93, 115]:
      tree.astTransform = AstTransformNodeCreator('InitDeclarator', {'initializer': 1, 'declarator': 0})
      subtree = self.parse_declarator()
      tree.add( subtree )
      subtree = self.parse__gen11()
      tree.add( subtree )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen6(self):
    current = self.tokens.current()
    rule = self.table[41][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(160, self.nonterminals[160]))
    tree.list = False
    if current != None and (current.getId() in [28, 20]):
      return tree
    if current == None:
      return tree
    if rule == 281:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_init_declarator()
      tree.add( subtree )
      return tree
    elif current.getId() in [47, 93, 115]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_init_declarator()
      tree.add( subtree )
    return tree
  def parse_struct_declarator(self):
    current = self.tokens.current()
    rule = self.table[42][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(161, self.nonterminals[161]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 125:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_struct_declarator_body()
      tree.add( subtree )
      return tree
    elif rule == 199:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_declarator()
      tree.add( subtree )
      subtree = self.parse__gen21()
      tree.add( subtree )
      return tree
    elif current.getId() in [47, 93, 115]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_declarator()
      tree.add( subtree )
      subtree = self.parse__gen21()
      tree.add( subtree )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen5(self):
    current = self.tokens.current()
    rule = self.table[43][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(162, self.nonterminals[162]))
    tree.list = False
    if current != None and (current.getId() in [28, 59, 20]):
      return tree
    if current == None:
      return tree
    if rule == 259:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_declaration_list()
      tree.add( subtree )
      return tree
    return tree
  def parse__gen19(self):
    current = self.tokens.current()
    rule = self.table[44][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(163, self.nonterminals[163]))
    tree.list = 'slist'
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 178:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_struct_declarator()
      tree.add( subtree )
      subtree = self.parse__gen20()
      tree.add( subtree )
      return tree
    elif current.getId() in [47, 93, 115]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_struct_declarator()
      tree.add( subtree )
      subtree = self.parse__gen20()
      tree.add( subtree )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen36(self):
    current = self.tokens.current()
    rule = self.table[45][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(164, self.nonterminals[164]))
    tree.list = False
    if current != None and (current.getId() in [28, 5]):
      return tree
    if current == None:
      return tree
    if rule == 285:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__direct_abstract_declarator()
      tree.add( subtree )
      return tree
    elif current.getId() in [72, 47]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__direct_abstract_declarator()
      tree.add( subtree )
    return tree
  def parse_direct_declarator_modifier_list(self):
    current = self.tokens.current()
    rule = self.table[46][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(165, self.nonterminals[165]))
    tree.list = False
    if current != None and (current.getId() in [0, 25, 95, 58, 74, 80, 64, 36, 115, 39, 82, 49, 18, 47, 92, 99, 84]):
      return tree
    if current == None:
      return tree
    if rule == 386:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen28()
      tree.add( subtree )
      return tree
    return tree
  def parse__gen27(self):
    current = self.tokens.current()
    rule = self.table[47][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(166, self.nonterminals[166]))
    tree.list = False
    if current != None and (current.getId() in [0, 25, 92, 95, 49, 80, 36, 64, 115, 39, 82, 74, 18, 47, 58, 99, 84]):
      return tree
    if current == None:
      return tree
    if rule == 39:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_direct_declarator_modifier_list()
      tree.add( subtree )
      return tree
    return tree
  def parse_token(self):
    current = self.tokens.current()
    rule = self.table[48][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(167, self.nonterminals[167]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 9:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(115) # identifier
      tree.add(t)
      return tree
    elif rule == 32:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_constant()
      tree.add( subtree )
      return tree
    elif rule == 82:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_punctuator()
      tree.add( subtree )
      return tree
    elif rule == 131:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(22) # pp_number
      tree.add(t)
      return tree
    elif rule == 244:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_keyword()
      tree.add( subtree )
      return tree
    elif rule == 367:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(82) # string_literal
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen22(self):
    current = self.tokens.current()
    rule = self.table[49][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(168, self.nonterminals[168]))
    tree.list = False
    if current != None and (current.getId() in [1, 93, 60, 2, 3, 4, 43, 56, 63, 8, 68, 73, 114, 16, 115, 77, 92, 35, 27, 26, 28, 88, 78, 65, 33, 102, 30, 42, 5, 37, 62, 47, 113, 20, 117, 13, 72]):
      return tree
    if current == None:
      return tree
    if rule == 139:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_enum_specifier_body()
      tree.add( subtree )
      return tree
    return tree
  def parse_struct_specifier(self):
    current = self.tokens.current()
    rule = self.table[50][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(169, self.nonterminals[169]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 423:
      tree.astTransform = AstTransformNodeCreator('Struct', {'definition': 1})
      t = self.expect(2) # struct
      tree.add(t)
      subtree = self.parse_struct_or_union_sub()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_block_item(self):
    current = self.tokens.current()
    rule = self.table[51][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(170, self.nonterminals[170]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 119:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_declaration()
      tree.add( subtree )
      return tree
    elif rule == 136:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_statement()
      tree.add( subtree )
      return tree
    elif current.getId() in [0, 82, 95, 49, 58, 80, 36, 64, 115, 39, 74, 18, 47, 92, 99, 84]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_statement()
      tree.add( subtree )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_initializer(self):
    current = self.tokens.current()
    rule = self.table[52][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(171, self.nonterminals[171]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 380:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(59) # lbrace
      tree.add(t)
      subtree = self.parse__gen12()
      tree.add( subtree )
      subtree = self.parse_trailing_comma_opt()
      tree.add( subtree )
      t = self.expect(89) # rbrace
      tree.add(t)
      return tree
    elif rule == 389:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__expr_sans_comma()
      tree.add( subtree )
      return tree
    elif current.getId() in [0, 82, 95, 49, 58, 74, 80, 36, 64, 115, 44, 18, 47, 92, 99, 84]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__expr_sans_comma()
      tree.add( subtree )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_direct_declarator_size(self):
    current = self.tokens.current()
    rule = self.table[53][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(172, self.nonterminals[172]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 188:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(25) # variable_length_array
      tree.add(t)
      return tree
    elif rule == 371:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__expr()
      tree.add( subtree )
      return tree
    elif current.getId() in [0, 82, 95, 49, 58, 80, 36, 64, 115, 39, 74, 18, 47, 92, 99, 84]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__expr()
      tree.add( subtree )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_expression_statement(self):
    current = self.tokens.current()
    rule = self.table[54][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(173, self.nonterminals[173]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 118:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_expression_opt()
      tree.add( subtree )
      t = self.expect(20) # semi
      tree.add(t)
      return tree
    elif current.getId() in [0, 82, 95, 49, 58, 80, 36, 64, 115, 39, 74, 18, 47, 92, 99, 84]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_expression_opt()
      tree.add( subtree )
      tree.add( self.expect(20) ) # semi
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_union_specifier(self):
    current = self.tokens.current()
    rule = self.table[55][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(174, self.nonterminals[174]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 81:
      tree.astTransform = AstTransformNodeCreator('Union', {'definition': 1})
      t = self.expect(56) # union
      tree.add(t)
      subtree = self.parse_struct_or_union_sub()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_pointer_sub(self):
    current = self.tokens.current()
    rule = self.table[56][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(175, self.nonterminals[175]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 21:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(92) # asterisk
      tree.add(t)
      subtree = self.parse_type_qualifier_list_opt()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen7(self):
    current = self.tokens.current()
    rule = self.table[57][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(176, self.nonterminals[176]))
    tree.list = 'nlist'
    if current != None and (current.getId() in [28, 59, 20]):
      return tree
    if current == None:
      return tree
    if rule == 302:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_declaration()
      tree.add( subtree )
      subtree = self.parse__gen7()
      tree.add( subtree )
      return tree
    return tree
  def parse_struct_declarator_body(self):
    current = self.tokens.current()
    rule = self.table[58][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(177, self.nonterminals[177]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 370:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(114) # colon
      tree.add(t)
      subtree = self.parse_declarator()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen38(self):
    current = self.tokens.current()
    rule = self.table[59][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(178, self.nonterminals[178]))
    tree.list = 'mlist'
    if current != None and (current.getId() in [72, 28, 93, 47, 5, 115]):
      return tree
    if current == None:
      return tree
    if rule == 306:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_pointer_sub()
      tree.add( subtree )
      subtree = self.parse__gen38()
      tree.add( subtree )
      return tree
    return tree
  def parse_direct_declarator_modifier(self):
    current = self.tokens.current()
    rule = self.table[61][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(180, self.nonterminals[180]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 8:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(65) # static
      tree.add(t)
      return tree
    elif rule == 53:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_type_qualifier()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen28(self):
    current = self.tokens.current()
    rule = self.table[62][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(181, self.nonterminals[181]))
    tree.list = 'nlist'
    if current != None and (current.getId() in [0, 25, 92, 95, 49, 80, 36, 64, 115, 39, 82, 74, 18, 47, 58, 99, 84]):
      return tree
    if current == None:
      return tree
    if rule == 105:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_direct_declarator_modifier()
      tree.add( subtree )
      subtree = self.parse__gen28()
      tree.add( subtree )
      return tree
    return tree
  def parse__gen35(self):
    current = self.tokens.current()
    rule = self.table[63][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(182, self.nonterminals[182]))
    tree.list = False
    if current != None and (current.getId() in [28, 5]):
      return tree
    if current == None:
      return tree
    if rule == 27:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_abstract_declarator()
      tree.add( subtree )
      return tree
    elif current.getId() in [72, 47]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_abstract_declarator()
      tree.add( subtree )
    return tree
  def parse_typedef_name(self):
    current = self.tokens.current()
    rule = self.table[64][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(183, self.nonterminals[183]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 159:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(113) # typedef_identifier
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_enumerator_assignment(self):
    current = self.tokens.current()
    rule = self.table[65][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(184, self.nonterminals[184]))
    tree.list = False
    if current != None and (current.getId() in [28, 105]):
      return tree
    if current == None:
      return tree
    if rule == 224:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(91) # assign
      tree.add(t)
      subtree = self.parse__expr()
      tree.add( subtree )
      return tree
    return tree
  def parse__gen12(self):
    current = self.tokens.current()
    rule = self.table[66][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(185, self.nonterminals[185]))
    tree.list = 'slist'
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 215:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_initializer_list_item()
      tree.add( subtree )
      subtree = self.parse__gen13()
      tree.add( subtree )
      return tree
    elif current.getId() in [0, 82, 95, 49, 58, 74, 80, 36, 64, 115, 44, 18, 47, 92, 99, 84]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_initializer_list_item()
      tree.add( subtree )
      subtree = self.parse__gen13()
      tree.add( subtree )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_type_qualifier_list_opt(self):
    current = self.tokens.current()
    rule = self.table[67][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(186, self.nonterminals[186]))
    tree.list = False
    if current != None and (current.getId() in [72, 92, 65, 93, 5, 47, 28, 115]):
      return tree
    if current == None:
      return tree
    if rule == 57:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen25()
      tree.add( subtree )
      return tree
    return tree
  def parse_parameter_type_list(self):
    current = self.tokens.current()
    rule = self.table[68][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(187, self.nonterminals[187]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 84:
      tree.astTransform = AstTransformNodeCreator('ParameterTypeList', {'parameter_declarations': 0, 'va_args': 1})
      subtree = self.parse__gen29()
      tree.add( subtree )
      subtree = self.parse__gen31()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen21(self):
    current = self.tokens.current()
    rule = self.table[69][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(188, self.nonterminals[188]))
    tree.list = False
    if current != None and (current.getId() in [28, 20]):
      return tree
    if current == None:
      return tree
    if rule == 409:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_struct_declarator_body()
      tree.add( subtree )
      return tree
    return tree
  def parse__gen0(self):
    current = self.tokens.current()
    rule = self.table[70][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(189, self.nonterminals[189]))
    tree.list = 'nlist'
    if current != None and (current.getId() in [-1]):
      return tree
    if current == None:
      return tree
    if rule == 127:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_external_declaration()
      tree.add( subtree )
      subtree = self.parse__gen0()
      tree.add( subtree )
      return tree
    return tree
  def parse_direct_abstract_declarator_expr(self):
    current = self.tokens.current()
    rule = self.table[71][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(190, self.nonterminals[190]))
    tree.list = False
    if current != None and (current.getId() in []):
      return tree
    if current == None:
      return tree
    if rule == 59:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_type_qualifier_list_opt()
      tree.add( subtree )
      subtree = self.parse_static_opt()
      tree.add( subtree )
      subtree = self.parse__expr()
      tree.add( subtree )
      return tree
    elif rule == 192:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(25) # variable_length_array
      tree.add(t)
      return tree
    elif current.getId() in [0, 82, 95, 49, 58, 80, 36, 64, 115, 39, 74, 18, 47, 92, 99, 84]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_type_qualifier_list_opt()
      tree.add( subtree )
      subtree = self.parse_static_opt()
      tree.add( subtree )
      subtree = self.parse__expr()
      tree.add( subtree )
    return tree
  def parse_expression_opt(self):
    current = self.tokens.current()
    rule = self.table[72][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(191, self.nonterminals[191]))
    tree.list = False
    if current != None and (current.getId() in [20, 48]):
      return tree
    if current == None:
      return tree
    if rule == 129:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__expr()
      tree.add( subtree )
      return tree
    elif current.getId() in [0, 82, 95, 49, 58, 80, 36, 64, 115, 39, 74, 18, 47, 92, 99, 84]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__expr()
      tree.add( subtree )
    return tree
  def parse__gen37(self):
    current = self.tokens.current()
    rule = self.table[73][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(192, self.nonterminals[192]))
    tree.list = 'mlist'
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 303:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_pointer_sub()
      tree.add( subtree )
      subtree = self.parse__gen38()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_trailing_comma_opt(self):
    current = self.tokens.current()
    rule = self.table[74][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(193, self.nonterminals[193]))
    tree.list = False
    if current != None and (current.getId() in [89]):
      return tree
    if current == None:
      return tree
    if rule == 187:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(105) # trailing_comma
      tree.add(t)
      return tree
    return tree
  def parse_static_opt(self):
    current = self.tokens.current()
    rule = self.table[76][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(195, self.nonterminals[195]))
    tree.list = False
    if current != None and (current.getId() in [0, 82, 95, 49, 58, 80, 36, 64, 115, 39, 74, 18, 47, 92, 99, 84]):
      return tree
    if current == None:
      return tree
    if rule == 114:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(65) # static
      tree.add(t)
      return tree
    return tree
  def parse__gen40(self):
    current = self.tokens.current()
    rule = self.table[77][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(196, self.nonterminals[196]))
    tree.list = 'nlist'
    if current != None and (current.getId() in [89]):
      return tree
    if current == None:
      return tree
    if rule == 116:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_block_item()
      tree.add( subtree )
      subtree = self.parse__gen40()
      tree.add( subtree )
      return tree
    elif current.getId() in [0, 82, 95, 49, 58, 80, 36, 64, 115, 39, 74, 18, 47, 92, 99, 84]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_block_item()
      tree.add( subtree )
      subtree = self.parse__gen40()
      tree.add( subtree )
    return tree
  def parse_designation(self):
    current = self.tokens.current()
    rule = self.table[78][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(197, self.nonterminals[197]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 50:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen15()
      tree.add( subtree )
      t = self.expect(91) # assign
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_direct_declarator_parameter_list(self):
    current = self.tokens.current()
    rule = self.table[79][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(198, self.nonterminals[198]))
    tree.list = False
    if current != None and (current.getId() in []):
      return tree
    if current == None:
      return tree
    if rule == 16:
      tree.astTransform = AstTransformNodeCreator('ParameterList', {'identifiers': 0})
      subtree = self.parse__gen32()
      tree.add( subtree )
      return tree
    elif rule == 203:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_parameter_type_list()
      tree.add( subtree )
      return tree
    return tree
  def parse_declaration(self):
    current = self.tokens.current()
    rule = self.table[80][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(199, self.nonterminals[199]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 424:
      tree.astTransform = AstTransformNodeCreator('Declaration', {'init_declarators': 1, 'declaration_specifiers': 0})
      subtree = self.parse__gen1()
      tree.add( subtree )
      subtree = self.parse__gen8()
      tree.add( subtree )
      t = self.expect(20) # semi
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen14(self):
    current = self.tokens.current()
    rule = self.table[81][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(200, self.nonterminals[200]))
    tree.list = False
    if current != None and (current.getId() in [0, 82, 95, 49, 58, 74, 80, 36, 64, 115, 44, 59, 18, 47, 92, 99, 84]):
      return tree
    if current == None:
      return tree
    if rule == 359:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_designation()
      tree.add( subtree )
      return tree
    return tree
  def parse_compound_statement(self):
    current = self.tokens.current()
    rule = self.table[82][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(201, self.nonterminals[201]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 34:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(59) # lbrace
      tree.add(t)
      subtree = self.parse__gen39()
      tree.add( subtree )
      t = self.expect(89) # rbrace
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_enum_specifier_sub(self):
    current = self.tokens.current()
    rule = self.table[83][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(202, self.nonterminals[202]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 300:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_identifier()
      tree.add( subtree )
      subtree = self.parse__gen22()
      tree.add( subtree )
      return tree
    elif rule == 312:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_enum_specifier_body()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_abstract_parameter_declaration(self):
    current = self.tokens.current()
    rule = self.table[84][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(203, self.nonterminals[203]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 112:
      tree.astTransform = AstTransformNodeCreator('AbstractParameter', {'declaration_specifiers': 1, 'declarator': 2})
      t = self.expect(85) # abstract_parameter_hint
      tree.add(t)
      subtree = self.parse__gen1()
      tree.add( subtree )
      subtree = self.parse__gen35()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_statement(self):
    current = self.tokens.current()
    rule = self.table[85][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(204, self.nonterminals[204]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 176:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_labeled_statement()
      tree.add( subtree )
      return tree
    elif rule == 207:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_expression_statement()
      tree.add( subtree )
      return tree
    elif rule == 265:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_iteration_statement()
      tree.add( subtree )
      return tree
    elif rule == 292:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_jump_statement()
      tree.add( subtree )
      return tree
    elif rule == 314:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_selection_statement()
      tree.add( subtree )
      return tree
    elif rule == 413:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_compound_statement()
      tree.add( subtree )
      return tree
    elif current.getId() in [0, 82, 95, 49, 58, 80, 36, 64, 115, 39, 74, 18, 47, 92, 99, 84]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_expression_statement()
      tree.add( subtree )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_enum_specifier(self):
    current = self.tokens.current()
    rule = self.table[86][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(205, self.nonterminals[205]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 73:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(35) # enum
      tree.add(t)
      subtree = self.parse_enum_specifier_sub()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_identifier(self):
    current = self.tokens.current()
    rule = self.table[87][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(206, self.nonterminals[206]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 79:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(115) # identifier
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_enum_specifier_body(self):
    current = self.tokens.current()
    rule = self.table[88][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(207, self.nonterminals[207]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 421:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(59) # lbrace
      tree.add(t)
      subtree = self.parse__gen23()
      tree.add( subtree )
      subtree = self.parse_trailing_comma_opt()
      tree.add( subtree )
      t = self.expect(89) # rbrace
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_parameter_declaration(self):
    current = self.tokens.current()
    rule = self.table[89][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(208, self.nonterminals[208]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 330:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_abstract_parameter_declaration()
      tree.add( subtree )
      return tree
    elif rule == 425:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_named_parameter_declaration()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen29(self):
    current = self.tokens.current()
    rule = self.table[90][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(209, self.nonterminals[209]))
    tree.list = 'slist'
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 142:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_parameter_declaration()
      tree.add( subtree )
      subtree = self.parse__gen30()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen30(self):
    current = self.tokens.current()
    rule = self.table[91][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(210, self.nonterminals[210]))
    tree.list = 'slist'
    if current != None and (current.getId() in [5]):
      return tree
    if current == None:
      return tree
    if rule == 420:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(28) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self.parse_parameter_declaration()
      tree.add( subtree )
      subtree = self.parse__gen30()
      tree.add( subtree )
      return tree
    return tree
  def parse__gen44(self):
    current = self.tokens.current()
    rule = self.table[92][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(211, self.nonterminals[211]))
    tree.list = 'slist'
    if current != None and (current.getId() in []):
      return tree
    if current == None:
      return tree
    if rule == 331:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__expr_sans_comma()
      tree.add( subtree )
      subtree = self.parse__gen45()
      tree.add( subtree )
      return tree
    return tree
  def parse_labeled_statement(self):
    current = self.tokens.current()
    rule = self.table[93][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(212, self.nonterminals[212]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 17:
      tree.astTransform = AstTransformNodeCreator('Label', {'name': 0, 'statement': 1})
      t = self.expect(107) # label_hint
      tree.add(t)
      t = self.expect(115) # identifier
      tree.add(t)
      t = self.expect(114) # colon
      tree.add(t)
      subtree = self.parse_statement()
      tree.add( subtree )
      return tree
    elif rule == 44:
      tree.astTransform = AstTransformNodeCreator('Case', {'expr': 1, 'statement': 3})
      t = self.expect(100) # case
      tree.add(t)
      subtree = self.parse__expr()
      tree.add( subtree )
      t = self.expect(114) # colon
      tree.add(t)
      subtree = self.parse_statement()
      tree.add( subtree )
      return tree
    elif rule == 69:
      tree.astTransform = AstTransformNodeCreator('DefaultCase', {'statement': 2})
      t = self.expect(66) # default
      tree.add(t)
      t = self.expect(114) # colon
      tree.add(t)
      subtree = self.parse_statement()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen25(self):
    current = self.tokens.current()
    rule = self.table[94][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(213, self.nonterminals[213]))
    tree.list = 'nlist'
    if current != None and (current.getId() in [72, 92, 65, 93, 5, 47, 28, 115]):
      return tree
    if current == None:
      return tree
    if rule == 234:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_type_qualifier()
      tree.add( subtree )
      subtree = self.parse__gen25()
      tree.add( subtree )
      return tree
    return tree
  def parse__gen45(self):
    current = self.tokens.current()
    rule = self.table[95][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(214, self.nonterminals[214]))
    tree.list = 'slist'
    if current != None and (current.getId() in []):
      return tree
    if current == None:
      return tree
    if rule == 100:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(28) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self.parse__expr_sans_comma()
      tree.add( subtree )
      subtree = self.parse__gen45()
      tree.add( subtree )
      return tree
    return tree
  def parse__gen15(self):
    current = self.tokens.current()
    rule = self.table[96][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(215, self.nonterminals[215]))
    tree.list = 'nlist'
    if current != None and (current.getId() in [91]):
      return tree
    if current == None:
      return tree
    if rule == 140:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_designator()
      tree.add( subtree )
      subtree = self.parse__gen15()
      tree.add( subtree )
      return tree
    return tree
  def parse_else_if_statement_list(self):
    current = self.tokens.current()
    rule = self.table[97][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(216, self.nonterminals[216]))
    tree.list = False
    if current == None:
      return tree
    if rule == 72:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen43()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen41(self):
    current = self.tokens.current()
    rule = self.table[98][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(217, self.nonterminals[217]))
    tree.list = False
    if current != None and (current.getId() in [0, 2, 3, 47, 43, 80, 56, 76, 89, 77, 16, 19, 92, 35, 24, 26, 13, 82, 52, 33, 36, 30, 39, 78, 45, 84, 62, 49, 50, 1, 58, 99, 59, 60, 64, 18, 115, 69, 71, 73, 74, 4, 8, 83, 27, 107, 68, 65, 95, 118, 116, 100, 102, 66, 37, 113, 20, 117]):
      return tree
    if current == None:
      return tree
    if rule == 301:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_else_if_statement_list()
      tree.add( subtree )
      return tree
    return tree
  def parse__gen31(self):
    current = self.tokens.current()
    rule = self.table[99][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(218, self.nonterminals[218]))
    tree.list = False
    if current != None and (current.getId() in []):
      return tree
    if current == None:
      return tree
    if rule == 130:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_va_args()
      tree.add( subtree )
      return tree
    return tree
  def parse_punctuator(self):
    current = self.tokens.current()
    rule = self.table[100][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(219, self.nonterminals[219]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 10:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(61) # addeq
      tree.add(t)
      return tree
    elif rule == 12:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(106) # rshifteq
      tree.add(t)
      return tree
    elif rule == 22:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(0) # decr
      tree.add(t)
      return tree
    elif rule == 24:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(89) # rbrace
      tree.add(t)
      return tree
    elif rule == 36:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(29) # bitor
      tree.add(t)
      return tree
    elif rule == 43:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(80) # incr
      tree.add(t)
      return tree
    elif rule == 45:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(15) # neq
      tree.add(t)
      return tree
    elif rule == 48:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(7) # questionmark
      tree.add(t)
      return tree
    elif rule == 51:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(28) # comma
      tree.add(t)
      return tree
    elif rule == 83:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(86) # bitxor
      tree.add(t)
      return tree
    elif rule == 87:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(70) # rsquare
      tree.add(t)
      return tree
    elif rule == 94:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(57) # bitandeq
      tree.add(t)
      return tree
    elif rule == 102:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(98) # lshift
      tree.add(t)
      return tree
    elif rule == 107:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(21) # eq
      tree.add(t)
      return tree
    elif rule == 108:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(12) # lshifteq
      tree.add(t)
      return tree
    elif rule == 115:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(104) # rshift
      tree.add(t)
      return tree
    elif rule == 117:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(111) # ampersand
      tree.add(t)
      return tree
    elif rule == 143:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(51) # arrow
      tree.add(t)
      return tree
    elif rule == 148:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(67) # bitxoreq
      tree.add(t)
      return tree
    elif rule == 154:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(17) # modeq
      tree.add(t)
      return tree
    elif rule == 155:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(94) # pound
      tree.add(t)
      return tree
    elif rule == 157:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(109) # or
      tree.add(t)
      return tree
    elif rule == 168:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(32) # mod
      tree.add(t)
      return tree
    elif rule == 171:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(23) # poundpound
      tree.add(t)
      return tree
    elif rule == 181:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(91) # assign
      tree.add(t)
      return tree
    elif rule == 196:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(81) # gt
      tree.add(t)
      return tree
    elif rule == 202:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(114) # colon
      tree.add(t)
      return tree
    elif rule == 204:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(54) # dot
      tree.add(t)
      return tree
    elif rule == 228:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(14) # gteq
      tree.add(t)
      return tree
    elif rule == 248:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(112) # lt
      tree.add(t)
      return tree
    elif rule == 304:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(108) # exclamation_point
      tree.add(t)
      return tree
    elif rule == 317:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(90) # muleq
      tree.add(t)
      return tree
    elif rule == 321:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(47) # lparen
      tree.add(t)
      return tree
    elif rule == 323:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(55) # lsquare
      tree.add(t)
      return tree
    elif rule == 327:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(53) # elipsis
      tree.add(t)
      return tree
    elif rule == 329:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(48) # rparen
      tree.add(t)
      return tree
    elif rule == 334:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(6) # subeq
      tree.add(t)
      return tree
    elif rule == 339:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(101) # sub
      tree.add(t)
      return tree
    elif rule == 344:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(87) # and
      tree.add(t)
      return tree
    elif rule == 355:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(40) # lteq
      tree.add(t)
      return tree
    elif rule == 362:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(10) # bitoreq
      tree.add(t)
      return tree
    elif rule == 363:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(96) # add
      tree.add(t)
      return tree
    elif rule == 391:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(103) # div
      tree.add(t)
      return tree
    elif rule == 395:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(110) # tilde
      tree.add(t)
      return tree
    elif rule == 400:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(59) # lbrace
      tree.add(t)
      return tree
    elif rule == 418:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(20) # semi
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_enumerator(self):
    current = self.tokens.current()
    rule = self.table[101][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(220, self.nonterminals[220]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 4:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_enumeration_constant()
      tree.add( subtree )
      subtree = self.parse_enumerator_assignment()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen23(self):
    current = self.tokens.current()
    rule = self.table[102][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(221, self.nonterminals[221]))
    tree.list = 'slist'
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 165:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_enumerator()
      tree.add( subtree )
      subtree = self.parse__gen24()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen24(self):
    current = self.tokens.current()
    rule = self.table[103][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(222, self.nonterminals[222]))
    tree.list = 'slist'
    if current != None and (current.getId() in [105]):
      return tree
    if current == None:
      return tree
    if rule == 276:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(28) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self.parse_enumerator()
      tree.add( subtree )
      subtree = self.parse__gen24()
      tree.add( subtree )
      return tree
    return tree
  def parse_else_statement(self):
    current = self.tokens.current()
    rule = self.table[104][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(223, self.nonterminals[223]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 77:
      tree.astTransform = AstTransformNodeCreator('Else', {'statement': 1})
      t = self.expect(116) # else
      tree.add(t)
      subtree = self.parse_statement()
      tree.add( subtree )
      t = self.expect(50) # endif
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_selection_statement(self):
    current = self.tokens.current()
    rule = self.table[105][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(224, self.nonterminals[224]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 189:
      tree.astTransform = AstTransformNodeCreator('If', {'elseif': 6, 'statement': 4, 'condition': 2, 'else': 7})
      t = self.expect(45) # if
      tree.add(t)
      t = self.expect(47) # lparen
      tree.add(t)
      subtree = self.parse__expr()
      tree.add( subtree )
      t = self.expect(48) # rparen
      tree.add(t)
      subtree = self.parse_statement()
      tree.add( subtree )
      t = self.expect(50) # endif
      tree.add(t)
      subtree = self.parse__gen41()
      tree.add( subtree )
      subtree = self.parse__gen42()
      tree.add( subtree )
      return tree
    elif rule == 419:
      tree.astTransform = AstTransformNodeCreator('Switch', {'expr': 2, 'statment': 4})
      t = self.expect(52) # switch
      tree.add(t)
      t = self.expect(47) # lparen
      tree.add(t)
      subtree = self.parse__expr()
      tree.add( subtree )
      t = self.expect(48) # rparen
      tree.add(t)
      subtree = self.parse_statement()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen42(self):
    current = self.tokens.current()
    rule = self.table[106][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(225, self.nonterminals[225]))
    tree.list = False
    if current != None and (current.getId() in [0, 2, 3, 47, 43, 80, 56, 76, 89, 77, 16, 19, 92, 35, 24, 26, 13, 82, 52, 33, 36, 30, 39, 78, 45, 84, 62, 49, 50, 1, 58, 59, 60, 64, 18, 115, 69, 71, 73, 74, 4, 8, 83, 27, 107, 68, 65, 95, 118, 99, 100, 102, 66, 37, 113, 20, 117]):
      return tree
    if current == None:
      return tree
    if rule == 170:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_else_statement()
      tree.add( subtree )
      return tree
    return tree
  def parse_for_cond(self):
    current = self.tokens.current()
    rule = self.table[107][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(226, self.nonterminals[226]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 146:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(20) # semi
      tree.add(t)
      subtree = self.parse_expression_opt()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_initializer_list_item(self):
    current = self.tokens.current()
    rule = self.table[108][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(227, self.nonterminals[227]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 128:
      tree.astTransform = AstTransformNodeCreator('Initialization', {'designation': 0, 'initializer': 1})
      subtree = self.parse__gen14()
      tree.add( subtree )
      subtree = self.parse_initializer()
      tree.add( subtree )
      return tree
    elif current.getId() in [0, 82, 95, 49, 58, 74, 80, 36, 64, 115, 44, 18, 47, 92, 99, 84]:
      tree.astTransform = AstTransformNodeCreator('Initialization', {'designation': 0, 'initializer': 1})
      subtree = self.parse__gen14()
      tree.add( subtree )
      subtree = self.parse_initializer()
      tree.add( subtree )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_iteration_statement(self):
    current = self.tokens.current()
    rule = self.table[109][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(228, self.nonterminals[228]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 88:
      tree.astTransform = AstTransformNodeCreator('DoWhile', {'expr': 4, 'statement': 1})
      t = self.expect(19) # do
      tree.add(t)
      subtree = self.parse_statement()
      tree.add( subtree )
      t = self.expect(76) # while
      tree.add(t)
      t = self.expect(47) # lparen
      tree.add(t)
      subtree = self.parse__expr()
      tree.add( subtree )
      t = self.expect(48) # rparen
      tree.add(t)
      t = self.expect(20) # semi
      tree.add(t)
      return tree
    elif rule == 208:
      tree.astTransform = AstTransformNodeCreator('For', {'init': 2, 'cond': 3, 'incr': 4, 'statement': 6})
      t = self.expect(24) # for
      tree.add(t)
      t = self.expect(47) # lparen
      tree.add(t)
      subtree = self.parse_for_init()
      tree.add( subtree )
      subtree = self.parse_for_cond()
      tree.add( subtree )
      subtree = self.parse_for_incr()
      tree.add( subtree )
      t = self.expect(48) # rparen
      tree.add(t)
      subtree = self.parse_statement()
      tree.add( subtree )
      return tree
    elif rule == 343:
      tree.astTransform = AstTransformNodeCreator('While', {'expr': 2, 'statement': 4})
      t = self.expect(76) # while
      tree.add(t)
      t = self.expect(47) # lparen
      tree.add(t)
      subtree = self.parse__expr()
      tree.add( subtree )
      t = self.expect(48) # rparen
      tree.add(t)
      subtree = self.parse_statement()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_declaration_specifier(self):
    current = self.tokens.current()
    rule = self.table[111][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(230, self.nonterminals[230]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 3:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_type_qualifier()
      tree.add( subtree )
      return tree
    elif rule == 38:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_type_specifier()
      tree.add( subtree )
      return tree
    elif rule == 63:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_storage_class_specifier()
      tree.add( subtree )
      return tree
    elif rule == 89:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_function_specifier()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_jump_statement(self):
    current = self.tokens.current()
    rule = self.table[112][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(231, self.nonterminals[231]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 320:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(83) # continue
      tree.add(t)
      return tree
    elif rule == 347:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(69) # break
      tree.add(t)
      t = self.expect(20) # semi
      tree.add(t)
      return tree
    elif rule == 366:
      tree.astTransform = AstTransformNodeCreator('Return', {'expr': 1})
      t = self.expect(118) # return
      tree.add(t)
      subtree = self.parse_expression_opt()
      tree.add( subtree )
      t = self.expect(20) # semi
      tree.add(t)
      return tree
    elif rule == 369:
      tree.astTransform = AstTransformNodeCreator('Goto', {'name': 1})
      t = self.expect(71) # goto
      tree.add(t)
      t = self.expect(115) # identifier
      tree.add(t)
      t = self.expect(20) # semi
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen2(self):
    current = self.tokens.current()
    rule = self.table[113][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(232, self.nonterminals[232]))
    tree.list = 'mlist'
    if current != None and (current.getId() in [88, 92, 5, 63, 115, 42, 47, 93, 72, 28, 20]):
      return tree
    if current == None:
      return tree
    if rule == 403:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_declaration_specifier()
      tree.add( subtree )
      subtree = self.parse__gen2()
      tree.add( subtree )
      return tree
    return tree
  def parse__gen3(self):
    current = self.tokens.current()
    rule = self.table[114][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(233, self.nonterminals[233]))
    tree.list = 'slist'
    if current != None and (current.getId() in [20]):
      return tree
    if current == None:
      return tree
    if rule == 212:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_external_declaration_sub_sub()
      tree.add( subtree )
      subtree = self.parse__gen4()
      tree.add( subtree )
      return tree
    return tree
  def parse__gen32(self):
    current = self.tokens.current()
    rule = self.table[115][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(234, self.nonterminals[234]))
    tree.list = 'slist'
    if current != None and (current.getId() in []):
      return tree
    if current == None:
      return tree
    if rule == 286:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_identifier()
      tree.add( subtree )
      subtree = self.parse__gen33()
      tree.add( subtree )
      return tree
    return tree
  def parse_else_if_statement(self):
    current = self.tokens.current()
    rule = self.table[116][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(235, self.nonterminals[235]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 328:
      tree.astTransform = AstTransformNodeCreator('ElseIf', {'statement': 4, 'condition': 2})
      t = self.expect(11) # else_if
      tree.add(t)
      t = self.expect(47) # lparen
      tree.add(t)
      subtree = self.parse__expr()
      tree.add( subtree )
      t = self.expect(48) # rparen
      tree.add(t)
      subtree = self.parse_statement()
      tree.add( subtree )
      t = self.expect(50) # endif
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen43(self):
    current = self.tokens.current()
    rule = self.table[117][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(236, self.nonterminals[236]))
    tree.list = 'nlist'
    if current != None and (current.getId() in [0, 2, 3, 47, 43, 80, 56, 76, 89, 77, 16, 19, 92, 35, 24, 26, 13, 82, 52, 33, 36, 30, 39, 78, 45, 84, 62, 49, 50, 1, 58, 99, 59, 60, 64, 18, 115, 69, 71, 73, 74, 4, 8, 83, 27, 107, 68, 65, 95, 118, 116, 100, 102, 66, 37, 113, 20, 117]):
      return tree
    if current == None:
      return tree
    if rule == 185:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_else_if_statement()
      tree.add( subtree )
      subtree = self.parse__gen43()
      tree.add( subtree )
      return tree
    return tree
  def parse_declarator_initializer(self):
    current = self.tokens.current()
    rule = self.table[118][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(237, self.nonterminals[237]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 354:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(91) # assign
      tree.add(t)
      subtree = self.parse_initializer()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_pp(self):
    current = self.tokens.current()
    rule = self.table[119][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(238, self.nonterminals[238]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 1:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(79) # defined_separator
      tree.add(t)
      return tree
    elif rule == 55:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(22) # pp_number
      tree.add(t)
      return tree
    elif rule == 405:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(97) # defined
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen34(self):
    current = self.tokens.current()
    rule = self.table[120][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(239, self.nonterminals[239]))
    tree.list = False
    if current != None and (current.getId() in [28, 5]):
      return tree
    if current == None:
      return tree
    if rule == 242:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_declarator()
      tree.add( subtree )
      return tree
    elif current.getId() in [47, 93, 115]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_declarator()
      tree.add( subtree )
    return tree
  def parse_va_args(self):
    current = self.tokens.current()
    rule = self.table[121][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(240, self.nonterminals[240]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 86:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(5) # comma_va_args
      tree.add(t)
      t = self.expect(53) # elipsis
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen13(self):
    current = self.tokens.current()
    rule = self.table[122][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(241, self.nonterminals[241]))
    tree.list = 'slist'
    if current != None and (current.getId() in [105]):
      return tree
    if current == None:
      return tree
    if rule == 5:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(28) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self.parse_initializer_list_item()
      tree.add( subtree )
      subtree = self.parse__gen13()
      tree.add( subtree )
      return tree
    return tree
  def parse_external_declaration_sub(self):
    current = self.tokens.current()
    rule = self.table[123][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(242, self.nonterminals[242]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 19:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_external_function()
      tree.add( subtree )
      return tree
    elif rule == 25:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen3()
      tree.add( subtree )
      t = self.expect(20) # semi
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen11(self):
    current = self.tokens.current()
    rule = self.table[124][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(243, self.nonterminals[243]))
    tree.list = False
    if current != None and (current.getId() in [28, 20]):
      return tree
    if current == None:
      return tree
    if rule == 64:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_declarator_initializer()
      tree.add( subtree )
      return tree
    return tree
  def parse_external_declaration(self):
    current = self.tokens.current()
    rule = self.table[125][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(244, self.nonterminals[244]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 20:
      tree.astTransform = AstTransformNodeCreator('ExternalDeclaration', {'declarations': 2, 'declaration_specifiers': 1})
      t = self.expect(75) # external_declaration_hint
      tree.add(t)
      subtree = self.parse__gen1()
      tree.add( subtree )
      subtree = self.parse_external_declaration_sub()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_external_function(self):
    current = self.tokens.current()
    rule = self.table[126][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(245, self.nonterminals[245]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 205:
      tree.astTransform = AstTransformNodeCreator('FunctionDefinition', {'body': 3, 'declaration_list': 2, 'signature': 1})
      t = self.expect(42) # function_definition_hint
      tree.add(t)
      subtree = self.parse_declarator()
      tree.add( subtree )
      subtree = self.parse__gen5()
      tree.add( subtree )
      subtree = self.parse_compound_statement()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_block_item_list(self):
    current = self.tokens.current()
    rule = self.table[127][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(246, self.nonterminals[246]))
    tree.list = False
    if current == None:
      return tree
    if rule == 121:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen40()
      tree.add( subtree )
      return tree
    elif current.getId() in [0, 82, 95, 49, 58, 80, 36, 64, 115, 39, 74, 18, 47, 92, 99, 84]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen40()
      tree.add( subtree )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen39(self):
    current = self.tokens.current()
    rule = self.table[128][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(247, self.nonterminals[247]))
    tree.list = False
    if current != None and (current.getId() in [89]):
      return tree
    if current == None:
      return tree
    if rule == 99:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_block_item_list()
      tree.add( subtree )
      return tree
    elif current.getId() in [0, 82, 95, 49, 58, 80, 36, 64, 115, 39, 74, 18, 47, 92, 99, 84]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_block_item_list()
      tree.add( subtree )
    return tree
  def parse_direct_declarator_expr(self):
    current = self.tokens.current()
    rule = self.table[129][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(248, self.nonterminals[248]))
    tree.list = False
    if current != None and (current.getId() in []):
      return tree
    if current == None:
      return tree
    if rule == 396:
      tree.astTransform = AstTransformNodeCreator('DirectDeclaratorExpression', {'modifiers': 0, 'value': 1})
      subtree = self.parse__gen27()
      tree.add( subtree )
      subtree = self.parse_direct_declarator_size()
      tree.add( subtree )
      return tree
    elif current.getId() in [0, 82, 95, 49, 58, 80, 36, 64, 115, 39, 74, 18, 47, 92, 99, 84]:
      tree.astTransform = AstTransformNodeCreator('DirectDeclaratorExpression', {'modifiers': 0, 'value': 1})
      subtree = self.parse__gen27()
      tree.add( subtree )
      subtree = self.parse_direct_declarator_size()
      tree.add( subtree )
    return tree
  def parse__expr( self, rbp = 0):
    name = '_expr'
    if name not in self.expressionParsers:
      self.expressionParsers[name] = ExpressionParser__expr(self)
    return self.expressionParsers[name].parse(rbp)
  def parse__expr_sans_comma( self, rbp = 0):
    name = '_expr_sans_comma'
    if name not in self.expressionParsers:
      self.expressionParsers[name] = ExpressionParser__expr_sans_comma(self)
    return self.expressionParsers[name].parse(rbp)
  def parse__direct_declarator( self, rbp = 0):
    name = '_direct_declarator'
    if name not in self.expressionParsers:
      self.expressionParsers[name] = ExpressionParser__direct_declarator(self)
    return self.expressionParsers[name].parse(rbp)
  def parse__direct_abstract_declarator( self, rbp = 0):
    name = '_direct_abstract_declarator'
    if name not in self.expressionParsers:
      self.expressionParsers[name] = ExpressionParser__direct_abstract_declarator(self)
    return self.expressionParsers[name].parse(rbp)
