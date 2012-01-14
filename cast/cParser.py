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
      0: 14000,
      2: 15000,
      9: 1000,
      12: 15000,
      14: 1000,
      16: 9000,
      17: 9000,
      21: 9000,
      22: 16000,
      26: 5000,
      27: 10000,
      31: 2000,
      33: 3000,
      37: 15000,
      38: 1000,
      41: 15000,
      42: 9000,
      51: 1000,
      52: 1000,
      64: 8000,
      66: 1000,
      67: 4000,
      68: 15000,
      70: 1000,
      74: 11000,
      84: 11000,
      89: 15000,
      90: 6000,
      91: 12000,
      95: 1000,
      102: 8000,
      103: 1000,
      106: 10000,
      107: 1000,
      108: 12000,
      109: 1000,
      110: 7000,
      118: 12000,
    }
    self.prefixBp = {
      26: 13000,
      30: 13000,
      41: 13000,
      74: 13000,
      78: 13000,
      89: 13000,
      108: 13000,
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
    tree = ParseTree( NonTerminal(219, '_expr') )
    current = self.getCurrentToken()
    if not current:
      return tree
    if current.getId() in [79]:
      tree.astTransform = AstTransformNodeCreator('ArrayIndex', {'params': 2, 'name': 0})
      tree.nudMorphemeCount = 1
      tree.add( self.expect(79) )
    elif current.getId() in [79]:
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      tree.nudMorphemeCount = 1
      tree.add( self.expect(79) )
    elif current.getId() in [26]:
      tree.astTransform = AstTransformNodeCreator('AddressOf', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(26) )
      tree.add( self.parent.parse__expr( self.getPrefixBp(26) ) )
      tree.isPrefix = True
    elif current.getId() in [79]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      tree.add( self.expect(79) )
    elif current.getId() in [111]:
      tree.astTransform = AstTransformNodeCreator('SizeOf', {'var': 1})
      tree.nudMorphemeCount = 1
      tree.add( self.expect(111) )
    elif current.getId() in [37]:
      tree.astTransform = AstTransformSubstitution(2)
      tree.nudMorphemeCount = 3
      tree.add( self.expect(37) )
      tree.add( self.parent.parse__expr() )
      tree.add( self.expect(39) )
    elif current.getId() in [5]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      tree.add( self.expect(5) )
    elif current.getId() in [73, 34, 55, 62, 40, 48]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      tree.add( self.parent.parse_constant() )
    elif current.getId() in [41]:
      tree.astTransform = AstTransformNodeCreator('PreDecr', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(41) )
      tree.add( self.parent.parse__expr( self.getPrefixBp(41) ) )
      tree.isPrefix = True
    elif current.getId() in [108]:
      tree.astTransform = AstTransformNodeCreator('Dereference', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(108) )
      tree.add( self.parent.parse__expr( self.getPrefixBp(108) ) )
      tree.isPrefix = True
    elif current.getId() in [89]:
      tree.astTransform = AstTransformNodeCreator('PreIncr', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(89) )
      tree.add( self.parent.parse__expr( self.getPrefixBp(89) ) )
      tree.isPrefix = True
    elif current.getId() in [81]:
      tree.astTransform = AstTransformNodeCreator('TypeInitializion', {'type': 1, 'initializer': 4})
      tree.nudMorphemeCount = 3
      tree.add( self.expect(81) )
      tree.add( self.parent.parse_type_name() )
      tree.add( self.expect(39) )
    return tree
  def led(self, left):
    tree = ParseTree( NonTerminal(219, '_expr') )
    current = self.getCurrentToken()
    if current.getId() == 2: # 'lsquare'
      tree.astTransform = AstTransformNodeCreator('ArrayIndex', {'params': 2, 'name': 0})
      tree.add(left)
      tree.add( self.expect(2) )
      tree.add( self.parent.parse__gen43() )
      tree.add( self.expect(61) )
      return tree
    if current.getId() == 90: # 'bitxor'
      tree.astTransform = AstTransformNodeCreator('BitXOR', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(90) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(90) - modifier ) )
      return tree
    if current.getId() == 66: # 'muleq'
      tree.astTransform = AstTransformNodeCreator('MultiplyAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(66) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(66) - modifier ) )
      return tree
    if current.getId() == 74: # 'sub'
      tree.astTransform = AstTransformNodeCreator('Sub', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(74) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(74) - modifier ) )
      return tree
    if current.getId() == 9: # 'bitxoreq'
      tree.astTransform = AstTransformNodeCreator('XORAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(9) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(9) - modifier ) )
      return tree
    if current.getId() == 37: # 'lparen'
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      tree.add(left)
      tree.add( self.expect(37) )
      tree.add( self.parent.parse__gen43() )
      tree.add( self.expect(39) )
      return tree
    if current.getId() == 14: # 'subeq'
      tree.astTransform = AstTransformNodeCreator('SubtractAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(14) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(14) - modifier ) )
      return tree
    if current.getId() == 106: # 'lshift'
      tree.astTransform = AstTransformNodeCreator('LeftShift', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(106) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(106) - modifier ) )
      return tree
    if current.getId() == 91: # 'div'
      tree.astTransform = AstTransformNodeCreator('Div', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(91) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(91) - modifier ) )
      return tree
    if current.getId() == 84: # 'add'
      tree.astTransform = AstTransformNodeCreator('Add', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(84) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(84) - modifier ) )
      return tree
    if current.getId() == 95: # 'assign'
      tree.astTransform = AstTransformNodeCreator('Assign', {'var': 0, 'value': 2})
      tree.add(left)
      tree.add( self.expect(95) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(95) - modifier ) )
      return tree
    if current.getId() == 17: # 'lteq'
      tree.astTransform = AstTransformNodeCreator('LessThanEq', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(17) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(17) - modifier ) )
      return tree
    if current.getId() == 109: # 'bitoreq'
      tree.astTransform = AstTransformNodeCreator('ORAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(109) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(109) - modifier ) )
      return tree
    if current.getId() == 46: # 'sizeof_separator'
      tree.astTransform = AstTransformNodeCreator('SizeOf', {'var': 1})
      tree.add(left)
      tree.add( self.expect(46) )
      tree.add( self.parent.parse_sizeof_body() )
      return tree
    if current.getId() == 42: # 'lt'
      tree.astTransform = AstTransformNodeCreator('LessThan', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(42) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(42) - modifier ) )
      return tree
    if current.getId() == 64: # 'eq'
      tree.astTransform = AstTransformNodeCreator('Equals', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(64) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(64) - modifier ) )
      return tree
    if current.getId() == 51: # 'bitandeq'
      tree.astTransform = AstTransformNodeCreator('ANDAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(51) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(51) - modifier ) )
      return tree
    if current.getId() == 68: # 'dot'
      tree.astTransform = AstTransformNodeCreator('MemberSelect', {'member': 2, 'object': 0})
      tree.isExprNud = True 
      tree.add(left)
      tree.add( self.expect(68) )
      modifier = 0
      tree.add( self.parent.parse__expr( self.getInfixBp(68) - modifier ) )
      return tree
    if current.getId() == 27: # 'rshift'
      tree.astTransform = AstTransformNodeCreator('RightShift', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(27) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(27) - modifier ) )
      return tree
    if current.getId() == 108: # 'asterisk'
      tree.astTransform = AstTransformNodeCreator('Mul', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(108) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(108) - modifier ) )
      return tree
    if current.getId() == 107: # 'addeq'
      tree.astTransform = AstTransformNodeCreator('AddAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(107) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(107) - modifier ) )
      return tree
    if current.getId() == 26: # 'bitand'
      tree.astTransform = AstTransformNodeCreator('BitAND', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(26) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(26) - modifier ) )
      return tree
    if current.getId() == 16: # 'gt'
      tree.astTransform = AstTransformNodeCreator('GreaterThan', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(16) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(16) - modifier ) )
      return tree
    if current.getId() == 89: # 'incr'
      tree.astTransform = AstTransformNodeCreator('PostIncr', {'var': 0})
      tree.isExprNud = True 
      tree.add(left)
      tree.add( self.expect(89) )
      return tree
    if current.getId() == 41: # 'decr'
      tree.astTransform = AstTransformNodeCreator('PostDecr', {'var': 0})
      tree.isExprNud = True 
      tree.add(left)
      tree.add( self.expect(41) )
      return tree
    if current.getId() == 38: # 'diveq'
      tree.astTransform = AstTransformNodeCreator('DivideAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(38) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(38) - modifier ) )
      return tree
    if current.getId() == 31: # 'questionmark'
      tree.astTransform = AstTransformNodeCreator('TernaryOperator', {'true': 2, 'false': 4, 'cond': 0})
      tree.isExprNud = True 
      tree.add(left)
      tree.add( self.expect(31) )
      modifier = 1
      tree.add( self.parent.parse__expr( self.getInfixBp(31) - modifier ) )
      tree.add( self.expect(1) )
      modifier = 1
      tree.add( self.parent.parse__expr( self.getInfixBp(31) - modifier ) )
      return tree
    if current.getId() == 110: # 'bitor'
      tree.astTransform = AstTransformNodeCreator('BitOR', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(110) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(110) - modifier ) )
      return tree
    if current.getId() == 70: # 'lshifteq'
      tree.astTransform = AstTransformNodeCreator('LeftShiftAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(70) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(70) - modifier ) )
      return tree
    if current.getId() == 21: # 'gteq'
      tree.astTransform = AstTransformNodeCreator('GreaterThanEq', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(21) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(21) - modifier ) )
      return tree
    if current.getId() == 103: # 'modeq'
      tree.astTransform = AstTransformNodeCreator('ModAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(103) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(103) - modifier ) )
      return tree
    if current.getId() == 118: # 'mod'
      tree.astTransform = AstTransformNodeCreator('Mod', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(118) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(118) - modifier ) )
      return tree
    if current.getId() == 52: # 'rshifteq'
      tree.astTransform = AstTransformNodeCreator('RightShiftAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(52) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(52) - modifier ) )
      return tree
    if current.getId() == 22: # 'comma'
      tree.astTransform = AstTransformNodeCreator('Comma', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(22) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(22) - modifier ) )
      return tree
    if current.getId() == 0: # 'lbrace'
      tree.astTransform = AstTransformNodeCreator('TypeInitializion', {'type': 1, 'initializer': 4})
      tree.add(left)
      tree.add( self.expect(0) )
      tree.add( self.parent.parse__gen12() )
      tree.add( self.parent.parse_trailing_comma_opt() )
      tree.add( self.expect(92) )
      return tree
    if current.getId() == 12: # 'arrow'
      tree.astTransform = AstTransformNodeCreator('DerefMemberSelect', {'member': 2, 'object': 0})
      tree.isExprNud = True 
      tree.add(left)
      tree.add( self.expect(12) )
      modifier = 0
      tree.add( self.parent.parse__expr( self.getInfixBp(12) - modifier ) )
      return tree
    return tree
class ExpressionParser__expr_sans_comma:
  def __init__(self, parent):
    self.__dict__.update(locals())
    self.infixBp = {
      0: 14000,
      2: 15000,
      9: 1000,
      12: 15000,
      14: 1000,
      16: 9000,
      17: 9000,
      21: 9000,
      26: 5000,
      27: 10000,
      31: 2000,
      33: 3000,
      37: 15000,
      38: 1000,
      41: 15000,
      42: 9000,
      51: 1000,
      52: 1000,
      64: 8000,
      66: 1000,
      67: 4000,
      68: 15000,
      70: 1000,
      74: 11000,
      84: 11000,
      89: 15000,
      90: 6000,
      91: 12000,
      95: 1000,
      102: 8000,
      103: 1000,
      106: 10000,
      107: 1000,
      108: 12000,
      109: 1000,
      110: 7000,
      118: 12000,
    }
    self.prefixBp = {
      26: 13000,
      30: 13000,
      41: 13000,
      74: 13000,
      78: 13000,
      89: 13000,
      108: 13000,
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
    elif current.getId() in [79]:
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      tree.nudMorphemeCount = 1
      tree.add( self.expect(79) )
    elif current.getId() in [41]:
      tree.astTransform = AstTransformNodeCreator('PreDecr', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(41) )
      tree.add( self.parent.parse__expr_sans_comma( self.getPrefixBp(41) ) )
      tree.isPrefix = True
    elif current.getId() in [79]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      tree.add( self.expect(79) )
    elif current.getId() in [73, 34, 55, 62, 40, 48]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      tree.add( self.parent.parse_constant() )
    elif current.getId() in [111]:
      tree.astTransform = AstTransformNodeCreator('SizeOf', {'var': 1})
      tree.nudMorphemeCount = 1
      tree.add( self.expect(111) )
    elif current.getId() in [5]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      tree.add( self.expect(5) )
    elif current.getId() in [26]:
      tree.astTransform = AstTransformNodeCreator('AddressOf', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(26) )
      tree.add( self.parent.parse__expr_sans_comma( self.getPrefixBp(26) ) )
      tree.isPrefix = True
    elif current.getId() in [81]:
      tree.astTransform = AstTransformNodeCreator('TypeInitializion', {'type': 1, 'initializer': 4})
      tree.nudMorphemeCount = 3
      tree.add( self.expect(81) )
      tree.add( self.parent.parse_type_name() )
      tree.add( self.expect(39) )
    elif current.getId() in [37]:
      tree.astTransform = AstTransformSubstitution(2)
      tree.nudMorphemeCount = 3
      tree.add( self.expect(37) )
      tree.add( self.parent.parse__expr_sans_comma() )
      tree.add( self.expect(39) )
    elif current.getId() in [108]:
      tree.astTransform = AstTransformNodeCreator('Dereference', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(108) )
      tree.add( self.parent.parse__expr_sans_comma( self.getPrefixBp(108) ) )
      tree.isPrefix = True
    elif current.getId() in [79]:
      tree.astTransform = AstTransformNodeCreator('ArrayIndex', {'params': 2, 'name': 0})
      tree.nudMorphemeCount = 1
      tree.add( self.expect(79) )
    elif current.getId() in [89]:
      tree.astTransform = AstTransformNodeCreator('PreIncr', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(89) )
      tree.add( self.parent.parse__expr_sans_comma( self.getPrefixBp(89) ) )
      tree.isPrefix = True
    return tree
  def led(self, left):
    tree = ParseTree( NonTerminal(179, '_expr_sans_comma') )
    current = self.getCurrentToken()
    if current.getId() == 74: # 'sub'
      tree.astTransform = AstTransformNodeCreator('Sub', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(74) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(74) - modifier ) )
      return tree
    if current.getId() == 110: # 'bitor'
      tree.astTransform = AstTransformNodeCreator('BitOR', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(110) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(110) - modifier ) )
      return tree
    if current.getId() == 51: # 'bitandeq'
      tree.astTransform = AstTransformNodeCreator('ANDAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(51) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(51) - modifier ) )
      return tree
    if current.getId() == 90: # 'bitxor'
      tree.astTransform = AstTransformNodeCreator('BitXOR', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(90) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(90) - modifier ) )
      return tree
    if current.getId() == 37: # 'lparen'
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      tree.add(left)
      tree.add( self.expect(37) )
      tree.add( self.parent.parse__gen43() )
      tree.add( self.expect(39) )
      return tree
    if current.getId() == 17: # 'lteq'
      tree.astTransform = AstTransformNodeCreator('LessThanEq', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(17) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(17) - modifier ) )
      return tree
    if current.getId() == 42: # 'lt'
      tree.astTransform = AstTransformNodeCreator('LessThan', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(42) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(42) - modifier ) )
      return tree
    if current.getId() == 12: # 'arrow'
      tree.astTransform = AstTransformNodeCreator('DerefMemberSelect', {'member': 2, 'object': 0})
      tree.isExprNud = True 
      tree.add(left)
      tree.add( self.expect(12) )
      modifier = 0
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(12) - modifier ) )
      return tree
    if current.getId() == 46: # 'sizeof_separator'
      tree.astTransform = AstTransformNodeCreator('SizeOf', {'var': 1})
      tree.add(left)
      tree.add( self.expect(46) )
      tree.add( self.parent.parse_sizeof_body() )
      return tree
    if current.getId() == 91: # 'div'
      tree.astTransform = AstTransformNodeCreator('Div', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(91) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(91) - modifier ) )
      return tree
    if current.getId() == 31: # 'questionmark'
      tree.astTransform = AstTransformNodeCreator('TernaryOperator', {'true': 2, 'false': 4, 'cond': 0})
      tree.isExprNud = True 
      tree.add(left)
      tree.add( self.expect(31) )
      modifier = 1
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(31) - modifier ) )
      tree.add( self.expect(1) )
      modifier = 1
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(31) - modifier ) )
      return tree
    if current.getId() == 95: # 'assign'
      tree.astTransform = AstTransformNodeCreator('Assign', {'var': 0, 'value': 2})
      tree.add(left)
      tree.add( self.expect(95) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(95) - modifier ) )
      return tree
    if current.getId() == 109: # 'bitoreq'
      tree.astTransform = AstTransformNodeCreator('ORAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(109) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(109) - modifier ) )
      return tree
    if current.getId() == 66: # 'muleq'
      tree.astTransform = AstTransformNodeCreator('MultiplyAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(66) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(66) - modifier ) )
      return tree
    if current.getId() == 68: # 'dot'
      tree.astTransform = AstTransformNodeCreator('MemberSelect', {'member': 2, 'object': 0})
      tree.isExprNud = True 
      tree.add(left)
      tree.add( self.expect(68) )
      modifier = 0
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(68) - modifier ) )
      return tree
    if current.getId() == 16: # 'gt'
      tree.astTransform = AstTransformNodeCreator('GreaterThan', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(16) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(16) - modifier ) )
      return tree
    if current.getId() == 103: # 'modeq'
      tree.astTransform = AstTransformNodeCreator('ModAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(103) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(103) - modifier ) )
      return tree
    if current.getId() == 21: # 'gteq'
      tree.astTransform = AstTransformNodeCreator('GreaterThanEq', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(21) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(21) - modifier ) )
      return tree
    if current.getId() == 0: # 'lbrace'
      tree.astTransform = AstTransformNodeCreator('TypeInitializion', {'type': 1, 'initializer': 4})
      tree.add(left)
      tree.add( self.expect(0) )
      tree.add( self.parent.parse__gen12() )
      tree.add( self.parent.parse_trailing_comma_opt() )
      tree.add( self.expect(92) )
      return tree
    if current.getId() == 9: # 'bitxoreq'
      tree.astTransform = AstTransformNodeCreator('XORAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(9) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(9) - modifier ) )
      return tree
    if current.getId() == 14: # 'subeq'
      tree.astTransform = AstTransformNodeCreator('SubtractAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(14) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(14) - modifier ) )
      return tree
    if current.getId() == 84: # 'add'
      tree.astTransform = AstTransformNodeCreator('Add', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(84) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(84) - modifier ) )
      return tree
    if current.getId() == 64: # 'eq'
      tree.astTransform = AstTransformNodeCreator('Equals', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(64) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(64) - modifier ) )
      return tree
    if current.getId() == 108: # 'asterisk'
      tree.astTransform = AstTransformNodeCreator('Mul', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(108) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(108) - modifier ) )
      return tree
    if current.getId() == 52: # 'rshifteq'
      tree.astTransform = AstTransformNodeCreator('RightShiftAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(52) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(52) - modifier ) )
      return tree
    if current.getId() == 118: # 'mod'
      tree.astTransform = AstTransformNodeCreator('Mod', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(118) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(118) - modifier ) )
      return tree
    if current.getId() == 2: # 'lsquare'
      tree.astTransform = AstTransformNodeCreator('ArrayIndex', {'params': 2, 'name': 0})
      tree.add(left)
      tree.add( self.expect(2) )
      tree.add( self.parent.parse__gen43() )
      tree.add( self.expect(61) )
      return tree
    if current.getId() == 27: # 'rshift'
      tree.astTransform = AstTransformNodeCreator('RightShift', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(27) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(27) - modifier ) )
      return tree
    if current.getId() == 106: # 'lshift'
      tree.astTransform = AstTransformNodeCreator('LeftShift', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(106) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(106) - modifier ) )
      return tree
    if current.getId() == 26: # 'bitand'
      tree.astTransform = AstTransformNodeCreator('BitAND', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(26) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(26) - modifier ) )
      return tree
    if current.getId() == 107: # 'addeq'
      tree.astTransform = AstTransformNodeCreator('AddAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(107) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(107) - modifier ) )
      return tree
    if current.getId() == 41: # 'decr'
      tree.astTransform = AstTransformNodeCreator('PostDecr', {'var': 0})
      tree.isExprNud = True 
      tree.add(left)
      tree.add( self.expect(41) )
      return tree
    if current.getId() == 70: # 'lshifteq'
      tree.astTransform = AstTransformNodeCreator('LeftShiftAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(70) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(70) - modifier ) )
      return tree
    if current.getId() == 38: # 'diveq'
      tree.astTransform = AstTransformNodeCreator('DivideAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(38) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(38) - modifier ) )
      return tree
    if current.getId() == 89: # 'incr'
      tree.astTransform = AstTransformNodeCreator('PostIncr', {'var': 0})
      tree.isExprNud = True 
      tree.add(left)
      tree.add( self.expect(89) )
      return tree
    return tree
class ExpressionParser__direct_declarator:
  def __init__(self, parent):
    self.__dict__.update(locals())
    self.infixBp = {
      2: 1000,
      37: 1000,
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
    tree = ParseTree( NonTerminal(162, '_direct_declarator') )
    current = self.getCurrentToken()
    if not current:
      return tree
    elif current.getId() in [79]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      tree.add( self.expect(79) )
    elif current.getId() in [37]:
      tree.astTransform = AstTransformSubstitution(1)
      tree.nudMorphemeCount = 3
      tree.add( self.expect(37) )
      tree.add( self.parent.parse_declarator() )
      tree.add( self.expect(39) )
    return tree
  def led(self, left):
    tree = ParseTree( NonTerminal(162, '_direct_declarator') )
    current = self.getCurrentToken()
    if current.getId() == 37: # 'lparen'
      tree.astTransform = AstTransformNodeCreator('FunctionSignature', {'params': 2, 'declarator': 0})
      tree.isExprNud = True 
      tree.add(left)
      tree.add( self.expect(37) )
      tree.add( self.parent.parse_direct_declarator_parameter_list() )
      tree.add( self.expect(39) )
      return tree
    if current.getId() == 2: # 'lsquare'
      tree.astTransform = AstTransformNodeCreator('Array', {'name': 0, 'size': 2})
      tree.isExprNud = True 
      tree.add(left)
      tree.add( self.expect(2) )
      tree.add( self.parent.parse_direct_declarator_expr() )
      tree.add( self.expect(61) )
      return tree
    return tree
class ExpressionParser__direct_abstract_declarator:
  def __init__(self, parent):
    self.__dict__.update(locals())
    self.infixBp = {
      2: 1000,
      37: 1000,
    }
    self.prefixBp = {
      37: 2000,
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
    tree = ParseTree( NonTerminal(238, '_direct_abstract_declarator') )
    current = self.getCurrentToken()
    if not current:
      return tree
    elif current.getId() in [37]:
      tree.astTransform = AstTransformSubstitution(1)
      tree.nudMorphemeCount = 3
      tree.add( self.expect(37) )
      tree.add( self.parent.parse_abstract_declarator() )
      tree.add( self.expect(39) )
    return tree
  def led(self, left):
    tree = ParseTree( NonTerminal(238, '_direct_abstract_declarator') )
    current = self.getCurrentToken()
    if current.getId() == 2: # 'lsquare'
      tree.astTransform = AstTransformNodeCreator('AbstractArray', {'object': '$', 'size': 2})
      tree.isExprNud = True 
      tree.add(left)
      tree.add( self.expect(2) )
      tree.add( self.parent.parse_direct_abstract_declarator_expr() )
      tree.add( self.expect(61) )
      return tree
    if current.getId() == 37: # 'lparen'
      tree.astTransform = AstTransformNodeCreator('AbstractFunction', {'object': '$', 'params': 2})
      tree.isExprNud = True 
      tree.add(left)
      tree.add( self.expect(37) )
      tree.add( self.parent.parse__gen45() )
      tree.add( self.expect(39) )
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
    0: 'lbrace',
    1: 'colon',
    2: 'lsquare',
    3: 'struct',
    4: 'const',
    5: 'string_literal',
    6: 'char',
    7: 'do',
    8: 'abstract_parameter_hint',
    9: 'bitxoreq',
    10: 'restrict',
    11: 'exclamation_point',
    12: 'arrow',
    13: 'elipsis',
    14: 'subeq',
    15: 'imaginary',
    16: 'gt',
    17: 'lteq',
    18: 'variable_length_array',
    19: 'endif',
    20: 'int',
    21: 'gteq',
    22: 'comma',
    23: 'enum',
    24: 'void',
    25: 'short',
    26: 'bitand',
    27: 'rshift',
    28: 'long',
    29: 'pound',
    30: 'bitnot',
    31: 'questionmark',
    32: '_direct_declarator',
    33: 'or',
    34: 'integer_constant',
    35: 'if',
    36: 'float',
    37: 'lparen',
    38: 'diveq',
    39: 'rparen',
    40: 'floating_constant',
    41: 'decr',
    42: 'lt',
    43: 'double',
    44: 'function_definition_hint',
    45: 'bool',
    46: 'sizeof_separator',
    47: 'defined_separator',
    48: 'enumeration_constant',
    49: 'extern',
    50: 'signed',
    51: 'bitandeq',
    52: 'rshifteq',
    53: 'pp_number',
    54: 'auto',
    55: 'character_constant',
    56: 'continue',
    57: 'unsigned',
    58: 'named_parameter_hint',
    59: 'goto',
    60: '_expr',
    61: 'rsquare',
    62: 'decimal_floating_constant',
    63: 'register',
    64: 'eq',
    65: 'poundpound',
    66: 'muleq',
    67: 'and',
    68: 'dot',
    69: 'switch',
    70: 'lshifteq',
    71: 'union',
    72: 'function_prototype_hint',
    73: 'hexadecimal_floating_constant',
    74: 'sub',
    75: 'inline',
    76: 'label_hint',
    77: 'external_declaration_hint',
    78: 'not',
    79: 'identifier',
    80: 'tilde',
    81: 'lparen_cast',
    82: 'complex',
    83: 'volatile',
    84: 'add',
    85: 'defined',
    86: 'return',
    87: 'case',
    88: '_direct_abstract_declarator',
    89: 'incr',
    90: 'bitxor',
    91: 'div',
    92: 'rbrace',
    93: 'universal_character_name',
    94: 'default',
    95: 'assign',
    96: 'else_if',
    97: '_expr_sans_comma',
    98: 'static',
    99: 'for',
    100: 'trailing_comma',
    101: 'ampersand',
    102: 'neq',
    103: 'modeq',
    104: 'else',
    105: 'typedef',
    106: 'lshift',
    107: 'addeq',
    108: 'asterisk',
    109: 'bitoreq',
    110: 'bitor',
    111: 'sizeof',
    112: 'comma_va_args',
    113: 'typedef_identifier',
    114: 'break',
    115: 'declarator_hint',
    116: 'semi',
    117: 'while',
    118: 'mod',
    'lbrace': 0,
    'colon': 1,
    'lsquare': 2,
    'struct': 3,
    'const': 4,
    'string_literal': 5,
    'char': 6,
    'do': 7,
    'abstract_parameter_hint': 8,
    'bitxoreq': 9,
    'restrict': 10,
    'exclamation_point': 11,
    'arrow': 12,
    'elipsis': 13,
    'subeq': 14,
    'imaginary': 15,
    'gt': 16,
    'lteq': 17,
    'variable_length_array': 18,
    'endif': 19,
    'int': 20,
    'gteq': 21,
    'comma': 22,
    'enum': 23,
    'void': 24,
    'short': 25,
    'bitand': 26,
    'rshift': 27,
    'long': 28,
    'pound': 29,
    'bitnot': 30,
    'questionmark': 31,
    '_direct_declarator': 32,
    'or': 33,
    'integer_constant': 34,
    'if': 35,
    'float': 36,
    'lparen': 37,
    'diveq': 38,
    'rparen': 39,
    'floating_constant': 40,
    'decr': 41,
    'lt': 42,
    'double': 43,
    'function_definition_hint': 44,
    'bool': 45,
    'sizeof_separator': 46,
    'defined_separator': 47,
    'enumeration_constant': 48,
    'extern': 49,
    'signed': 50,
    'bitandeq': 51,
    'rshifteq': 52,
    'pp_number': 53,
    'auto': 54,
    'character_constant': 55,
    'continue': 56,
    'unsigned': 57,
    'named_parameter_hint': 58,
    'goto': 59,
    '_expr': 60,
    'rsquare': 61,
    'decimal_floating_constant': 62,
    'register': 63,
    'eq': 64,
    'poundpound': 65,
    'muleq': 66,
    'and': 67,
    'dot': 68,
    'switch': 69,
    'lshifteq': 70,
    'union': 71,
    'function_prototype_hint': 72,
    'hexadecimal_floating_constant': 73,
    'sub': 74,
    'inline': 75,
    'label_hint': 76,
    'external_declaration_hint': 77,
    'not': 78,
    'identifier': 79,
    'tilde': 80,
    'lparen_cast': 81,
    'complex': 82,
    'volatile': 83,
    'add': 84,
    'defined': 85,
    'return': 86,
    'case': 87,
    '_direct_abstract_declarator': 88,
    'incr': 89,
    'bitxor': 90,
    'div': 91,
    'rbrace': 92,
    'universal_character_name': 93,
    'default': 94,
    'assign': 95,
    'else_if': 96,
    '_expr_sans_comma': 97,
    'static': 98,
    'for': 99,
    'trailing_comma': 100,
    'ampersand': 101,
    'neq': 102,
    'modeq': 103,
    'else': 104,
    'typedef': 105,
    'lshift': 106,
    'addeq': 107,
    'asterisk': 108,
    'bitoreq': 109,
    'bitor': 110,
    'sizeof': 111,
    'comma_va_args': 112,
    'typedef_identifier': 113,
    'break': 114,
    'declarator_hint': 115,
    'semi': 116,
    'while': 117,
    'mod': 118,
  }
  # Quark - finite string set maps one string to exactly one int, and vice versa
  nonterminals = {
    119: 'external_declaration_sub_sub',
    120: 'init_declarator_list',
    121: '_gen3',
    122: 'direct_declarator_modifier_list_opt',
    123: '_gen4',
    124: '_gen25',
    125: 'direct_declarator_parameter_list',
    126: 'designator',
    127: 'abstract_parameter_declaration',
    128: 'constant',
    129: '_gen21',
    130: 'for_init',
    131: 'pp',
    132: 'for_cond',
    133: 'storage_class_specifier',
    134: 'function_specifier',
    135: '_gen33',
    136: '_gen16',
    137: 'named_parameter_declaration',
    138: '_gen45',
    139: '_gen28',
    140: 'external_declarator',
    141: '_gen34',
    142: 'type_qualifier',
    143: 'struct_or_union_sub',
    144: 'external_prototype',
    145: 'abstract_declarator',
    146: '_gen17',
    147: 'struct_declaration',
    148: 'va_args',
    149: 'declarator',
    150: 'declaration_list',
    151: '_gen9',
    152: '_gen10',
    153: '_gen30',
    154: '_gen11',
    155: 'pointer',
    156: '_gen26',
    157: 'struct_specifier',
    158: 'specifier_qualifier',
    159: '_gen18',
    160: 'translation_unit',
    161: '_gen35',
    162: '_direct_declarator',
    163: 'init_declarator',
    164: '_gen6',
    165: 'struct_declarator',
    166: '_gen5',
    167: '_gen19',
    168: '_gen20',
    169: 'direct_declarator_size',
    170: 'pointer_sub',
    171: '_gen36',
    172: '_gen37',
    173: 'typedef_name',
    174: 'initializer',
    175: 'direct_declarator_modifier',
    176: 'union_specifier',
    177: 'declaration',
    178: '_gen7',
    179: '_expr_sans_comma',
    180: '_gen27',
    181: 'selection_statement',
    182: 'initializer_list_item',
    183: 'expression_opt',
    184: 'type_qualifier_list_opt',
    185: 'direct_abstract_declarator_expr',
    186: 'keyword',
    187: 'block_item',
    188: '_gen0',
    189: '_gen39',
    190: '_gen22',
    191: 'for_incr',
    192: 'block_item_list',
    193: 'trailing_comma_opt',
    194: 'statement',
    195: 'struct_or_union_body',
    196: 'designation',
    197: '_gen14',
    198: 'compound_statement',
    199: 'parameter_type_list',
    200: 'type_name',
    201: 'enum_specifier_sub',
    202: 'sizeof_body',
    203: 'enum_specifier',
    204: '_gen31',
    205: '_gen43',
    206: 'iteration_statement',
    207: 'identifier',
    208: 'static_opt',
    209: 'enum_specifier_body',
    210: '_gen44',
    211: '_gen15',
    212: 'else_if_statement_list',
    213: '_gen40',
    214: 'expression_statement',
    215: 'parameter_declaration',
    216: 'type_specifier',
    217: 'else_statement',
    218: '_gen41',
    219: '_expr',
    220: 'enumerator',
    221: '_gen23',
    222: '_gen24',
    223: 'jump_statement',
    224: '_gen29',
    225: 'else_if_statement',
    226: 'struct_declarator_body',
    227: '_gen42',
    228: 'token',
    229: 'declaration_specifier',
    230: '_gen1',
    231: '_gen2',
    232: '_gen8',
    233: 'enumeration_constant',
    234: '_gen12',
    235: 'enumerator_assignment',
    236: 'declarator_initializer',
    237: '_gen13',
    238: '_direct_abstract_declarator',
    239: 'external_declaration_sub',
    240: 'punctuator',
    241: '_gen38',
    242: '_gen32',
    243: 'external_declaration',
    244: 'labeled_statement',
    245: 'external_function',
    246: 'misc',
    247: 'direct_declarator_expr',
    'external_declaration_sub_sub': 119,
    'init_declarator_list': 120,
    '_gen3': 121,
    'direct_declarator_modifier_list_opt': 122,
    '_gen4': 123,
    '_gen25': 124,
    'direct_declarator_parameter_list': 125,
    'designator': 126,
    'abstract_parameter_declaration': 127,
    'constant': 128,
    '_gen21': 129,
    'for_init': 130,
    'pp': 131,
    'for_cond': 132,
    'storage_class_specifier': 133,
    'function_specifier': 134,
    '_gen33': 135,
    '_gen16': 136,
    'named_parameter_declaration': 137,
    '_gen45': 138,
    '_gen28': 139,
    'external_declarator': 140,
    '_gen34': 141,
    'type_qualifier': 142,
    'struct_or_union_sub': 143,
    'external_prototype': 144,
    'abstract_declarator': 145,
    '_gen17': 146,
    'struct_declaration': 147,
    'va_args': 148,
    'declarator': 149,
    'declaration_list': 150,
    '_gen9': 151,
    '_gen10': 152,
    '_gen30': 153,
    '_gen11': 154,
    'pointer': 155,
    '_gen26': 156,
    'struct_specifier': 157,
    'specifier_qualifier': 158,
    '_gen18': 159,
    'translation_unit': 160,
    '_gen35': 161,
    '_direct_declarator': 162,
    'init_declarator': 163,
    '_gen6': 164,
    'struct_declarator': 165,
    '_gen5': 166,
    '_gen19': 167,
    '_gen20': 168,
    'direct_declarator_size': 169,
    'pointer_sub': 170,
    '_gen36': 171,
    '_gen37': 172,
    'typedef_name': 173,
    'initializer': 174,
    'direct_declarator_modifier': 175,
    'union_specifier': 176,
    'declaration': 177,
    '_gen7': 178,
    '_expr_sans_comma': 179,
    '_gen27': 180,
    'selection_statement': 181,
    'initializer_list_item': 182,
    'expression_opt': 183,
    'type_qualifier_list_opt': 184,
    'direct_abstract_declarator_expr': 185,
    'keyword': 186,
    'block_item': 187,
    '_gen0': 188,
    '_gen39': 189,
    '_gen22': 190,
    'for_incr': 191,
    'block_item_list': 192,
    'trailing_comma_opt': 193,
    'statement': 194,
    'struct_or_union_body': 195,
    'designation': 196,
    '_gen14': 197,
    'compound_statement': 198,
    'parameter_type_list': 199,
    'type_name': 200,
    'enum_specifier_sub': 201,
    'sizeof_body': 202,
    'enum_specifier': 203,
    '_gen31': 204,
    '_gen43': 205,
    'iteration_statement': 206,
    'identifier': 207,
    'static_opt': 208,
    'enum_specifier_body': 209,
    '_gen44': 210,
    '_gen15': 211,
    'else_if_statement_list': 212,
    '_gen40': 213,
    'expression_statement': 214,
    'parameter_declaration': 215,
    'type_specifier': 216,
    'else_statement': 217,
    '_gen41': 218,
    '_expr': 219,
    'enumerator': 220,
    '_gen23': 221,
    '_gen24': 222,
    'jump_statement': 223,
    '_gen29': 224,
    'else_if_statement': 225,
    'struct_declarator_body': 226,
    '_gen42': 227,
    'token': 228,
    'declaration_specifier': 229,
    '_gen1': 230,
    '_gen2': 231,
    '_gen8': 232,
    'enumeration_constant': 233,
    '_gen12': 234,
    'enumerator_assignment': 235,
    'declarator_initializer': 236,
    '_gen13': 237,
    '_direct_abstract_declarator': 238,
    'external_declaration_sub': 239,
    'punctuator': 240,
    '_gen38': 241,
    '_gen32': 242,
    'external_declaration': 243,
    'labeled_statement': 244,
    'external_function': 245,
    'misc': 246,
    'direct_declarator_expr': 247,
  }
  # table[nonterminal][terminal] = rule
  table = [
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 61, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 6, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 198, -1, -1, -1, -1, 198, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 198, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 198, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 7, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 7, 18, -1, -1],
    [-1, -1, -1, -1, 187, 187, -1, -1, -1, -1, 187, -1, -1, -1, -1, -1, -1, -1, 187, -1, -1, -1, -1, -1, -1, -1, 187, -1, -1, -1, -1, -1, -1, -1, 187, -1, -1, 187, -1, -1, 187, 187, -1, -1, -1, -1, -1, -1, 187, -1, -1, -1, -1, -1, -1, 187, -1, -1, -1, -1, 187, -1, 187, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 187, -1, -1, -1, -1, -1, 187, -1, 187, -1, 187, -1, -1, -1, -1, -1, 187, -1, -1, -1, -1, -1, -1, -1, -1, 187, -1, -1, -1, -1, -1, -1, -1, -1, -1, 187, -1, -1, 187, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 10, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 15, -1, -1],
    [-1, -1, -1, -1, 161, -1, -1, -1, -1, -1, 161, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 229, -1, -1, -1, -1, -1, -1, -1, -1, -1, 229, -1, -1, -1, -1, 229, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 229, -1, -1, -1, 161, -1, -1, -1, -1, 229, -1, -1, -1, -1, -1, -1, -1, -1, -1, 229, -1, -1, -1, -1, -1, -1, -1, -1, -1, 229, -1, -1, -1, 229, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, 288, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 288, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 111, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 40, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 366, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, 95, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 133, -1, -1, -1, -1, -1, 145, -1, -1, -1, -1, -1, -1, -1, 267, -1, -1, -1, -1, -1, -1, 101, -1, -1, -1, -1, -1, -1, 424, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 157, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, 12, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 311, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 311, -1, -1],
    [-1, -1, -1, 109, 109, 247, 109, -1, -1, -1, 109, -1, -1, -1, -1, 109, -1, -1, -1, -1, 109, -1, -1, 109, 109, 109, 247, -1, 109, -1, -1, -1, -1, -1, 247, -1, 109, 247, -1, -1, 247, 247, -1, 109, -1, 109, -1, -1, 247, 109, 109, -1, -1, -1, 109, 247, -1, 109, -1, -1, 247, -1, 247, 109, -1, -1, -1, -1, -1, -1, -1, 109, -1, 247, -1, 109, -1, -1, -1, 247, -1, 247, 109, 109, -1, -1, -1, -1, -1, 247, -1, -1, -1, -1, -1, -1, -1, -1, 109, -1, -1, -1, -1, -1, -1, 109, -1, -1, 247, -1, -1, 247, -1, 109, -1, -1, 182, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 59, -1, -1, -1, -1, -1, 128, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 333, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 412, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 100, -1, -1, -1, -1, 402, -1, -1, -1, -1, -1, -1, -1, -1, 334, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 180, -1, -1, -1, -1, -1, -1, 172, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 377, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 225, -1, -1, -1, -1, -1, -1, -1, -1, -1, 220, -1, -1, -1, -1, 220, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 220, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 220, -1, -1, -1, 225, -1, -1, -1, -1, -1, -1],
    [141, 226, -1, 226, 226, -1, 226, -1, -1, -1, 226, -1, -1, -1, -1, 226, -1, -1, -1, -1, 226, -1, 226, 226, 226, 226, -1, -1, 226, -1, -1, -1, 226, -1, -1, -1, 226, 226, -1, -1, -1, -1, -1, 226, 226, 226, -1, -1, -1, 226, 226, -1, -1, -1, 226, -1, -1, 226, -1, -1, -1, -1, -1, 226, -1, -1, -1, -1, -1, -1, -1, 226, 226, -1, -1, 226, -1, -1, -1, 226, -1, -1, 226, 226, -1, -1, -1, -1, 226, -1, -1, -1, -1, -1, -1, -1, -1, -1, 226, -1, -1, -1, -1, -1, -1, 226, -1, -1, 226, -1, -1, -1, 226, 226, -1, 226, 226, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 60, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, 423, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 423, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, 28, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 28, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 419, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 242, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 237, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 237, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 237, -1, -1, -1, 242, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, 149, -1, -1, -1, -1, -1, 375, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 409, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [202, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 85, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 188, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 317, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 317, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 171, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, 239, -1, 239, 239, -1, 239, -1, -1, -1, 239, -1, -1, -1, -1, 239, -1, -1, -1, -1, 239, -1, -1, 239, 239, 239, -1, -1, 239, -1, -1, -1, 239, -1, -1, -1, 239, 239, -1, -1, -1, -1, -1, 239, -1, 239, -1, -1, -1, -1, 239, -1, -1, -1, -1, -1, -1, 239, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 239, -1, -1, -1, -1, -1, -1, -1, 239, -1, -1, 239, 239, -1, -1, -1, -1, -1, -1, -1, -1, 243, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 239, -1, -1, -1, -1, 239, -1, -1, -1, -1, -1],
    [-1, 345, -1, 345, 345, -1, 345, -1, -1, -1, 345, -1, -1, -1, -1, 345, -1, -1, -1, -1, 345, -1, -1, 345, 345, 345, -1, -1, 345, -1, -1, -1, 345, -1, -1, -1, 345, 345, -1, -1, -1, -1, -1, 345, -1, 345, -1, -1, -1, -1, 345, -1, -1, -1, -1, -1, -1, 345, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 345, -1, -1, -1, -1, -1, -1, -1, 345, -1, -1, 345, 345, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 345, -1, -1, -1, -1, 345, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 11, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 121, -1, -1, -1, -1, 121, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 121, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 121, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [272, -1, -1, 272, 272, -1, 272, -1, -1, -1, 272, -1, -1, -1, -1, 272, -1, -1, -1, -1, 272, -1, 272, 272, 272, 272, -1, -1, 272, -1, -1, -1, -1, -1, -1, -1, 272, -1, -1, -1, -1, -1, -1, 272, -1, 272, -1, -1, -1, 272, 272, -1, -1, -1, 272, -1, -1, 272, -1, -1, -1, -1, -1, 272, -1, -1, -1, -1, -1, -1, -1, 272, -1, -1, -1, 272, -1, -1, -1, -1, -1, -1, 272, 272, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 272, -1, -1, -1, -1, -1, -1, 272, -1, -1, -1, -1, -1, -1, -1, 272, -1, -1, 272, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 246, -1, -1, -1, -1, 246, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 246, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 246, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 250, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 255, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 42, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 73, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 269, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 73, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 119, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 257, -1, -1, -1, -1, 257, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 257, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 252, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, 365, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, 358, 14, -1, 358, -1, -1, -1, 14, -1, -1, -1, -1, 358, -1, -1, -1, -1, 358, -1, -1, 358, 358, 358, -1, -1, 358, -1, -1, -1, -1, -1, -1, -1, 358, -1, -1, -1, -1, -1, -1, 358, -1, 358, -1, -1, -1, -1, 358, -1, -1, -1, -1, -1, -1, 358, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 358, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 358, 14, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 358, -1, -1, -1, -1, -1],
    [-1, 303, -1, 258, 258, -1, 258, -1, -1, -1, 258, -1, -1, -1, -1, 258, -1, -1, -1, -1, 258, -1, -1, 258, 258, 258, -1, -1, 258, -1, -1, -1, 303, -1, -1, -1, 258, 303, -1, -1, -1, -1, -1, 258, -1, 258, -1, -1, -1, -1, 258, -1, -1, -1, -1, -1, -1, 258, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 258, -1, -1, -1, -1, -1, -1, -1, 303, -1, -1, 258, 258, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 303, -1, -1, -1, -1, 258, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 150, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 264, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 260, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 260, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 264, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 406, -1, -1, -1, -1, 406, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 406, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 406, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 67, -1, -1, -1, -1, -1, -1, -1, -1, -1, 408, -1, -1, -1, -1, 408, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 408, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 408, -1, -1, -1, -1, -1, -1, -1, 67, -1, -1],
    [-1, 218, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 256, -1, -1, -1, -1, 256, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 256, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 256, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [47, -1, -1, 391, 391, -1, 391, -1, -1, -1, 391, -1, -1, -1, -1, 391, -1, -1, -1, -1, 391, -1, 47, 391, 391, 391, -1, -1, 391, -1, -1, -1, -1, -1, -1, -1, 391, -1, -1, -1, -1, -1, -1, 391, -1, 391, -1, -1, -1, 391, 391, -1, -1, -1, 391, -1, -1, 391, -1, -1, -1, -1, -1, 391, -1, -1, -1, -1, -1, -1, -1, 391, -1, -1, -1, 391, -1, -1, -1, -1, -1, -1, 391, 391, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 391, -1, -1, -1, -1, -1, -1, 391, -1, -1, -1, -1, -1, -1, -1, 391, -1, -1, 47, -1, -1],
    [-1, 271, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 271, -1, -1, -1, -1, 271, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 271, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 271, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 275, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 279, -1, -1],
    [-1, -1, -1, -1, -1, 41, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 126, -1, -1, -1, -1, -1, -1, -1, 41, -1, -1, -1, -1, -1, -1, -1, 41, -1, -1, 41, -1, -1, 41, 41, -1, -1, -1, -1, -1, -1, 41, -1, -1, -1, -1, -1, -1, 41, -1, -1, -1, -1, 41, -1, 41, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 41, -1, -1, -1, -1, -1, 41, -1, 41, -1, -1, -1, -1, -1, -1, -1, 41, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 41, -1, -1, 41, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 390, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 281, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 213, -1, -1, -1, -1, -1, -1, -1, -1, -1, 213, -1, -1, -1, -1, 213, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 213, -1, -1, -1, -1, -1, -1, -1, -1, 213, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 286, -1, -1, -1, 213, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 417, -1, -1, -1, -1, -1],
    [193, -1, -1, -1, -1, 151, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 151, -1, -1, -1, -1, -1, -1, -1, 151, -1, -1, 151, -1, -1, 151, 151, -1, -1, -1, -1, -1, -1, 151, -1, -1, -1, -1, -1, -1, 151, -1, -1, -1, -1, -1, -1, 151, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 151, -1, -1, -1, -1, -1, 151, -1, 151, -1, -1, -1, -1, -1, -1, -1, 151, -1, -1, -1, -1, -1, -1, -1, 151, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 151, -1, -1, 151, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, 418, -1, -1, -1, -1, -1, 418, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 418, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 181, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 3, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, 43, 43, -1, 43, -1, -1, -1, 43, -1, -1, -1, -1, 43, -1, -1, -1, -1, 43, -1, -1, 43, 43, 43, -1, -1, 43, -1, -1, -1, -1, -1, -1, -1, 43, -1, -1, -1, -1, -1, -1, 43, -1, 43, -1, -1, -1, 43, 43, -1, -1, -1, 43, -1, -1, 43, -1, -1, -1, -1, -1, 43, -1, -1, -1, -1, -1, -1, -1, 43, -1, -1, -1, 43, -1, -1, -1, -1, -1, -1, 43, 43, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 43, -1, -1, -1, -1, -1, -1, 43, -1, -1, -1, -1, -1, -1, -1, 43, -1, -1, -1, -1, -1],
    [89, -1, -1, 87, 87, -1, 87, -1, -1, -1, 87, -1, -1, -1, -1, 87, -1, -1, -1, -1, 87, -1, 89, 87, 87, 87, -1, -1, 87, -1, -1, -1, -1, -1, -1, -1, 87, -1, -1, -1, -1, -1, -1, 87, -1, 87, -1, -1, -1, 87, 87, -1, -1, -1, 87, -1, -1, 87, -1, -1, -1, -1, -1, 87, -1, -1, -1, -1, -1, -1, -1, 87, -1, -1, -1, 87, -1, -1, -1, -1, -1, -1, 87, 87, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 87, -1, -1, -1, -1, -1, -1, 87, -1, -1, -1, -1, -1, -1, -1, 87, -1, -1, 89, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, 177, 293, -1, -1, -1, -1, 177, -1, -1, -1, -1, -1, -1, -1, 293, -1, -1, -1, -1, -1, -1, -1, 293, -1, -1, -1, -1, -1, -1, -1, 293, -1, -1, 293, -1, -1, 293, 293, -1, -1, -1, -1, -1, -1, 293, -1, -1, -1, -1, -1, -1, 293, -1, -1, -1, -1, 293, -1, 293, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 293, -1, -1, -1, -1, -1, 293, -1, 293, -1, 177, -1, -1, -1, -1, -1, 293, -1, -1, -1, -1, -1, -1, -1, -1, 177, -1, -1, -1, -1, -1, -1, -1, -1, -1, 293, -1, -1, 293, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 24, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 158, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [127, -1, 127, -1, -1, 127, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 127, -1, -1, -1, -1, -1, -1, -1, 127, -1, -1, 127, -1, -1, 127, 127, -1, -1, -1, -1, -1, -1, 127, -1, -1, -1, -1, -1, -1, 127, -1, -1, -1, -1, -1, -1, 127, -1, -1, -1, -1, -1, 127, -1, -1, -1, -1, 127, -1, -1, -1, -1, -1, 127, -1, 127, -1, -1, -1, -1, -1, -1, -1, 127, -1, -1, -1, -1, -1, 127, -1, 127, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 127, -1, -1, 127, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, 118, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 118, -1, -1, -1, -1, -1, -1, -1, 118, -1, -1, 118, -1, 315, 118, 118, -1, -1, -1, -1, -1, -1, 118, -1, -1, -1, -1, -1, -1, 118, -1, -1, -1, -1, 118, -1, 118, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 118, -1, -1, -1, -1, -1, 118, -1, 118, -1, -1, -1, -1, -1, -1, -1, 118, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 118, -1, -1, 118, -1, -1, -1, -1, 315, -1, -1],
    [-1, -1, -1, -1, 139, -1, -1, -1, -1, -1, 139, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 139, -1, -1, -1, -1, -1, -1, -1, -1, -1, 139, -1, -1, -1, -1, 139, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 139, -1, -1, -1, 139, -1, -1, -1, -1, 139, -1, -1, -1, -1, -1, -1, -1, -1, -1, 139, -1, -1, -1, -1, -1, -1, -1, -1, -1, 139, -1, -1, -1, 139, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, 115, 115, -1, -1, -1, -1, 115, -1, -1, -1, -1, -1, -1, -1, 214, -1, -1, -1, -1, -1, -1, -1, 115, -1, -1, -1, -1, -1, -1, -1, 115, -1, -1, 115, -1, -1, 115, 115, -1, -1, -1, -1, -1, -1, 115, -1, -1, -1, -1, -1, -1, 115, -1, -1, -1, -1, 115, -1, 115, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 115, -1, -1, -1, -1, -1, 115, -1, 115, -1, 115, -1, -1, -1, -1, -1, 115, -1, -1, -1, -1, -1, -1, -1, -1, 115, -1, -1, -1, -1, -1, -1, -1, -1, -1, 115, -1, -1, 115, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, 71, 88, -1, 36, 381, -1, -1, 79, -1, -1, -1, -1, 205, -1, -1, -1, -1, 63, -1, -1, 93, 32, 175, -1, -1, 44, -1, -1, -1, -1, -1, -1, 25, 384, -1, -1, -1, -1, -1, -1, 190, -1, 414, -1, -1, -1, 2, 168, -1, -1, -1, 159, -1, 399, 75, -1, 5, -1, -1, -1, 236, -1, -1, -1, -1, -1, 8, -1, 298, -1, -1, -1, 46, -1, -1, -1, -1, -1, -1, 45, 230, -1, -1, 148, 266, -1, -1, -1, -1, -1, -1, 160, -1, -1, -1, 253, 29, -1, -1, -1, -1, 64, 82, -1, -1, -1, -1, -1, 359, -1, -1, 176, -1, -1, 69, -1],
    [343, -1, -1, 23, 23, 343, 23, 343, -1, -1, 23, -1, -1, -1, -1, 23, -1, -1, -1, -1, 23, -1, -1, 23, 23, 23, 343, -1, 23, -1, -1, -1, -1, -1, 343, 343, 23, 343, -1, -1, 343, 343, -1, 23, -1, 23, -1, -1, 343, 23, 23, -1, -1, -1, 23, 343, 343, 23, -1, 343, 343, -1, 343, 23, -1, -1, -1, -1, -1, 343, -1, 23, -1, 343, -1, 23, 343, -1, -1, 343, -1, 343, 23, 23, -1, -1, 343, 343, -1, 343, -1, -1, -1, -1, 343, -1, -1, -1, 23, 343, -1, -1, -1, -1, -1, 23, -1, -1, 343, -1, -1, 343, -1, 23, 343, -1, 343, 343, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 129, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [78, -1, -1, 78, 78, 78, 78, 78, -1, -1, 78, -1, -1, -1, -1, 78, -1, -1, -1, -1, 78, -1, -1, 78, 78, 78, 78, -1, 78, -1, -1, -1, -1, -1, 78, 78, 78, 78, -1, -1, 78, 78, -1, 78, -1, 78, -1, -1, 78, 78, 78, -1, -1, -1, 78, 78, 78, 78, -1, 78, 78, -1, 78, 78, -1, -1, -1, -1, -1, 78, -1, 78, -1, 78, -1, 78, 78, -1, -1, 78, -1, 78, 78, 78, -1, -1, 78, 78, -1, 78, -1, -1, 259, -1, 78, -1, -1, -1, 78, 78, -1, -1, -1, -1, -1, 78, -1, -1, 78, -1, -1, 78, -1, 78, 78, -1, 78, 78, -1],
    [351, 354, -1, 354, 354, -1, 354, -1, -1, -1, 354, -1, -1, -1, -1, 354, -1, -1, -1, -1, 354, -1, 354, 354, 354, 354, -1, -1, 354, -1, -1, -1, 354, -1, -1, -1, 354, 354, -1, -1, -1, -1, -1, 354, 354, 354, -1, -1, -1, 354, 354, -1, -1, -1, 354, -1, -1, 354, -1, -1, -1, -1, -1, 354, -1, -1, -1, -1, -1, -1, -1, 354, 354, -1, -1, 354, -1, -1, -1, 354, -1, -1, 354, 354, -1, -1, -1, -1, 354, -1, -1, -1, -1, -1, -1, -1, -1, -1, 354, -1, -1, -1, -1, -1, -1, 354, -1, -1, 354, -1, -1, -1, 354, 354, -1, 354, 354, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 270, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 194, -1, -1],
    [51, -1, -1, 51, 51, 51, 51, 51, -1, -1, 51, -1, -1, -1, -1, 51, -1, -1, -1, -1, 51, -1, -1, 51, 51, 51, 51, -1, 51, -1, -1, -1, -1, -1, 51, 51, 51, 51, -1, -1, 51, 51, -1, 51, -1, 51, -1, -1, 51, 51, 51, -1, -1, -1, 51, 51, 51, 51, -1, 51, 51, -1, 51, 51, -1, -1, -1, -1, -1, 51, -1, 51, -1, 51, -1, 51, 51, -1, -1, 51, -1, 51, 51, 51, -1, -1, 51, 51, -1, 51, -1, -1, 51, -1, 51, -1, -1, -1, 51, 51, -1, -1, -1, -1, -1, 51, -1, -1, 51, -1, -1, 51, -1, 51, 51, -1, 51, 51, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 39, -1, -1, -1, -1, -1, -1, -1, 21, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [30, -1, -1, -1, -1, 195, -1, 197, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 195, -1, -1, -1, -1, -1, -1, -1, 195, 112, -1, 195, -1, -1, 195, 195, -1, -1, -1, -1, -1, -1, 195, -1, -1, -1, -1, -1, -1, 195, 240, -1, -1, 240, 195, -1, 195, -1, -1, -1, -1, -1, -1, 112, -1, -1, -1, 195, -1, -1, 326, -1, -1, 195, -1, 195, -1, -1, -1, -1, 240, 326, -1, 195, -1, -1, -1, -1, 326, -1, -1, -1, -1, 197, -1, -1, -1, -1, -1, -1, -1, -1, 195, -1, -1, 195, -1, -1, 240, -1, 195, 197, -1],
    [114, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 185, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 185, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 185, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [125, -1, 123, -1, -1, 125, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 125, -1, -1, -1, -1, -1, -1, -1, 125, -1, -1, 125, -1, -1, 125, 125, -1, -1, -1, -1, -1, -1, 125, -1, -1, -1, -1, -1, -1, 125, -1, -1, -1, -1, -1, -1, 125, -1, -1, -1, -1, -1, 123, -1, -1, -1, -1, 125, -1, -1, -1, -1, -1, 125, -1, 125, -1, -1, -1, -1, -1, -1, -1, 125, -1, -1, -1, -1, -1, 123, -1, 125, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 125, -1, -1, 125, -1, -1, -1, -1, -1, -1, -1],
    [265, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, 13, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 13, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, 312, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 263, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [191, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 305, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 248, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 16, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 113, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 65, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, 278, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 278, -1, -1, -1, -1, -1, -1, -1, 278, -1, -1, 278, -1, -1, 278, 278, -1, -1, -1, -1, -1, -1, 278, -1, -1, -1, -1, -1, -1, 278, -1, -1, -1, -1, -1, -1, 278, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 278, -1, -1, -1, -1, -1, 278, -1, 278, -1, -1, -1, -1, -1, -1, -1, 278, -1, -1, -1, -1, -1, -1, -1, 278, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 278, -1, -1, 278, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, 216, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 276, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 120, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 372, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, 50, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 50, -1, -1, -1, -1, -1, -1, -1, 50, -1, -1, 50, -1, -1, 50, 50, -1, -1, -1, -1, -1, -1, 50, -1, -1, -1, -1, -1, -1, 50, -1, -1, -1, -1, 50, -1, 50, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 50, -1, -1, -1, -1, -1, 50, -1, 50, -1, -1, -1, -1, -1, -1, -1, 50, -1, -1, -1, -1, -1, -1, -1, -1, 57, -1, -1, -1, -1, -1, -1, -1, -1, -1, 50, -1, -1, 50, -1, -1, -1, -1, -1, -1, -1],
    [153, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 34, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 137, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 137, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 52, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [117, -1, -1, 117, 117, 117, 117, 117, -1, -1, 117, -1, -1, -1, -1, 117, -1, -1, -1, 117, 117, -1, -1, 117, 117, 117, 117, -1, 117, -1, -1, -1, -1, -1, 117, 117, 117, 117, -1, -1, 117, 117, -1, 117, -1, 117, -1, -1, 117, 117, 117, -1, -1, -1, 117, 117, 117, 117, -1, 117, 117, -1, 117, 117, -1, -1, -1, -1, -1, 117, -1, 117, -1, 117, -1, 117, 117, -1, -1, 117, -1, 117, 117, 117, -1, -1, 117, 117, -1, 117, -1, -1, 117, -1, 117, -1, 117, -1, 117, 117, -1, -1, -1, -1, 117, 117, -1, -1, 117, -1, -1, 117, -1, 117, 117, -1, 117, 117, -1],
    [144, -1, -1, 144, 144, 144, 144, 144, -1, -1, 144, -1, -1, -1, -1, 144, -1, -1, -1, 144, 144, -1, -1, 144, 144, 144, 144, -1, 144, -1, -1, -1, -1, -1, 144, 144, 144, 144, -1, -1, 144, 144, -1, 144, -1, 144, -1, -1, 144, 144, 144, -1, -1, -1, 144, 144, 144, 144, -1, 144, 144, -1, 144, 144, -1, -1, -1, -1, -1, 144, -1, 144, -1, 144, -1, 144, 144, -1, -1, 144, -1, 144, 144, 144, -1, -1, 144, 144, -1, 144, -1, -1, 144, -1, 144, -1, 379, -1, 144, 144, -1, -1, -1, -1, 144, 144, -1, -1, 144, -1, -1, 144, -1, 144, 144, -1, 144, 144, -1],
    [-1, -1, -1, -1, -1, 291, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 291, -1, -1, -1, -1, -1, -1, -1, 291, -1, -1, 291, -1, -1, 291, 291, -1, -1, -1, -1, -1, -1, 291, -1, -1, -1, -1, -1, -1, 291, -1, -1, -1, -1, 291, -1, 291, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 291, -1, -1, -1, -1, -1, 291, -1, 291, -1, -1, -1, -1, -1, -1, -1, 291, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 291, -1, -1, 291, -1, -1, -1, -1, 291, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, 179, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 49, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, 371, -1, -1, 309, -1, -1, -1, -1, -1, -1, -1, -1, 116, -1, -1, -1, -1, 91, -1, -1, 376, 364, 362, -1, -1, 370, -1, -1, -1, -1, -1, -1, -1, 154, -1, -1, -1, -1, -1, -1, 211, -1, 234, -1, -1, -1, -1, 200, -1, -1, -1, -1, -1, -1, 122, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 0, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 166, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 280, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 54, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [138, -1, -1, 138, 138, 138, 138, 138, -1, -1, 138, -1, -1, -1, -1, 138, -1, -1, -1, 138, 138, -1, -1, 138, 138, 138, 138, -1, 138, -1, -1, -1, -1, -1, 138, 138, 138, 138, -1, -1, 138, 138, -1, 138, -1, 138, -1, -1, 138, 138, 138, -1, -1, -1, 138, 138, 138, 138, -1, 138, 138, -1, 138, 138, -1, -1, -1, -1, -1, 138, -1, 138, -1, 138, -1, 138, 138, -1, -1, 138, -1, 138, 138, 138, -1, -1, 138, 138, -1, 138, -1, -1, 138, -1, 138, -1, -1, -1, 138, 138, -1, -1, -1, -1, 292, 138, -1, -1, 138, -1, -1, 138, -1, 138, 138, -1, 138, 138, -1],
    [363, 215, 363, -1, -1, 363, -1, -1, -1, -1, -1, -1, 215, -1, -1, -1, -1, -1, -1, -1, -1, -1, 215, -1, -1, -1, 363, -1, -1, -1, -1, 215, -1, -1, 363, -1, -1, 363, -1, 215, 363, 215, -1, -1, -1, -1, -1, -1, 363, -1, -1, -1, -1, -1, -1, 363, -1, -1, -1, -1, -1, 215, 363, -1, -1, -1, -1, -1, 215, -1, -1, -1, -1, 363, -1, -1, -1, -1, -1, 363, -1, 363, -1, -1, -1, -1, -1, -1, -1, 215, -1, -1, -1, -1, -1, 363, -1, 363, -1, -1, 215, -1, -1, -1, -1, -1, -1, -1, 363, -1, -1, 363, -1, -1, -1, -1, 215, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 53, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 382, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 385, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 397, -1, -1, 401, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 282, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 174, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 201, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 33, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 389, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, 22, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [324, -1, -1, 324, 324, 324, 324, 324, -1, -1, 324, -1, -1, -1, -1, 324, -1, -1, -1, 324, 324, -1, -1, 324, 324, 324, 324, -1, 324, -1, -1, -1, -1, -1, 324, 324, 324, 324, -1, -1, 324, 324, -1, 324, -1, 324, -1, -1, 324, 324, 324, -1, -1, -1, 324, 324, 324, 324, -1, 324, 324, -1, 324, 324, -1, -1, -1, -1, -1, 324, -1, 324, -1, 324, -1, 324, 324, -1, -1, 324, -1, 324, 324, 324, -1, -1, 324, 324, -1, 324, -1, -1, 324, -1, 324, -1, 245, -1, 324, 324, -1, -1, -1, -1, 324, 324, -1, -1, 324, -1, -1, 324, -1, 324, 324, -1, 324, 324, -1],
    [398, 398, 398, 415, 415, 346, 415, 415, -1, 398, 415, 398, 398, 398, 398, 415, 398, 398, -1, -1, 415, 398, 398, 415, 415, 415, -1, 398, 415, 398, -1, 398, -1, 398, 294, 415, 415, 398, -1, 398, 294, 398, 398, 415, -1, 415, -1, -1, 294, 415, 415, 398, 398, 26, 415, 294, 415, 415, -1, 415, -1, 398, 294, 415, 398, 398, 398, 398, 398, 415, 398, 415, -1, 294, 398, 415, -1, -1, -1, 31, 398, -1, 415, 415, 398, -1, 415, 415, -1, 398, 398, 398, 398, -1, 415, 398, -1, -1, 415, 415, -1, 398, 398, 398, 415, 415, 398, 398, -1, 398, 398, 415, -1, -1, 415, -1, 398, 415, 398],
    [-1, -1, -1, 203, 146, -1, 203, -1, -1, -1, 146, -1, -1, -1, -1, 203, -1, -1, -1, -1, 203, -1, -1, 203, 203, 203, -1, -1, 203, -1, -1, -1, -1, -1, -1, -1, 203, -1, -1, -1, -1, -1, -1, 203, -1, 203, -1, -1, -1, 81, 203, -1, -1, -1, 81, -1, -1, 203, -1, -1, -1, -1, -1, 81, -1, -1, -1, -1, -1, -1, -1, 203, -1, -1, -1, 232, -1, -1, -1, -1, -1, -1, 203, 146, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 81, -1, -1, -1, -1, -1, -1, 81, -1, -1, -1, -1, -1, -1, -1, 203, -1, -1, -1, -1, -1],
    [-1, -1, -1, 251, 251, -1, 251, -1, -1, -1, 251, -1, -1, -1, -1, 251, -1, -1, -1, -1, 251, -1, -1, 251, 251, 251, -1, -1, 251, -1, -1, -1, -1, -1, -1, -1, 251, -1, -1, -1, -1, -1, -1, 251, -1, 251, -1, -1, -1, 251, 251, -1, -1, -1, 251, -1, -1, 251, -1, -1, -1, -1, -1, 251, -1, -1, -1, -1, -1, -1, -1, 251, -1, -1, -1, 251, -1, -1, -1, -1, -1, -1, 251, 251, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 251, -1, -1, -1, -1, -1, -1, 251, -1, -1, -1, -1, -1, -1, -1, 251, -1, -1, -1, -1, -1],
    [-1, -1, -1, 156, 156, -1, 156, -1, -1, -1, 156, -1, -1, -1, -1, 156, -1, -1, -1, -1, 156, -1, 296, 156, 156, 156, -1, -1, 156, -1, -1, -1, 296, -1, -1, -1, 156, 296, -1, -1, -1, -1, -1, 156, 296, 156, -1, -1, -1, 156, 156, -1, -1, -1, 156, -1, -1, 156, -1, -1, -1, -1, -1, 156, -1, -1, -1, -1, -1, -1, -1, 156, 296, -1, -1, 156, -1, -1, -1, 296, -1, -1, 156, 156, -1, -1, -1, -1, 296, -1, -1, -1, -1, -1, -1, -1, -1, -1, 156, -1, -1, -1, -1, -1, -1, 156, -1, -1, 296, -1, -1, -1, 296, 156, -1, 296, 296, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 207, -1, -1, -1, -1, 207, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 207, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 207, -1, -1, -1, -1, -1, -1, -1, 66, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 421, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [210, -1, 210, -1, -1, 210, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 210, -1, -1, -1, -1, -1, -1, -1, 210, -1, -1, 210, -1, -1, 210, 210, -1, -1, -1, -1, -1, -1, 210, -1, -1, -1, -1, -1, -1, 210, -1, -1, -1, -1, -1, -1, 210, -1, -1, -1, -1, -1, 210, -1, -1, -1, -1, 210, -1, -1, -1, -1, -1, 210, -1, 210, -1, -1, -1, -1, -1, -1, -1, 210, -1, -1, -1, -1, -1, 210, -1, 210, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 210, -1, -1, 210, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 132, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 27, -1, -1, -1, -1, 132, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 340, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 104, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 107, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 96, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 219, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 219, 219, -1, -1],
    [167, 103, 70, -1, -1, -1, -1, -1, -1, 58, -1, 357, 72, 77, 189, -1, 110, 395, -1, -1, -1, 352, 99, -1, -1, -1, -1, 307, -1, 422, -1, 335, -1, 20, -1, -1, -1, 136, -1, 336, -1, 186, 170, -1, -1, -1, -1, -1, -1, -1, -1, 106, 86, -1, -1, -1, -1, -1, -1, -1, -1, 147, -1, -1, 56, 105, 142, 163, 403, -1, 394, -1, -1, -1, 84, -1, -1, -1, -1, -1, 140, -1, -1, -1, 155, -1, -1, -1, -1, 35, 341, 339, 4, -1, -1, 241, -1, -1, -1, -1, -1, 297, 98, 124, -1, -1, 37, 162, -1, 407, 130, -1, -1, -1, -1, -1, 173, -1, 222],
    [411, -1, -1, 411, 411, 411, 411, 411, -1, -1, 411, -1, -1, -1, -1, 411, -1, -1, -1, -1, 411, -1, -1, 411, 411, 411, 411, -1, 411, -1, -1, -1, -1, -1, 411, 411, 411, 411, -1, -1, 411, 411, -1, 411, -1, 411, -1, -1, 411, 411, 411, -1, -1, -1, 411, 411, 411, 411, -1, 411, 411, -1, 411, 411, -1, -1, -1, -1, -1, 411, -1, 411, -1, 411, -1, 411, 411, -1, -1, 411, -1, 411, 411, 411, -1, -1, 411, 411, -1, 411, -1, -1, 254, -1, 411, -1, -1, -1, 411, 411, -1, -1, -1, -1, -1, 411, -1, -1, 411, -1, -1, 411, -1, 411, 411, -1, 411, 411, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 68, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 392, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 224, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 374, -1, -1, -1, -1, -1, -1, 328, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 134, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 80, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 17, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, 183, 183, -1, -1, -1, -1, 183, -1, -1, -1, -1, -1, -1, -1, 183, -1, -1, -1, -1, -1, -1, -1, 183, -1, -1, -1, -1, -1, -1, -1, 183, -1, -1, 183, -1, -1, 183, 183, -1, -1, -1, -1, -1, -1, 183, -1, -1, -1, -1, -1, -1, 183, -1, -1, -1, -1, 183, -1, 183, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 183, -1, -1, -1, -1, -1, 183, -1, 183, -1, 183, -1, -1, -1, -1, -1, 183, -1, -1, -1, -1, -1, -1, -1, -1, 183, -1, -1, -1, -1, -1, -1, -1, -1, -1, 183, -1, -1, 183, -1, -1, -1, -1, -1, -1, -1],
  ]
  TERMINAL_LBRACE = 0
  TERMINAL_COLON = 1
  TERMINAL_LSQUARE = 2
  TERMINAL_STRUCT = 3
  TERMINAL_CONST = 4
  TERMINAL_STRING_LITERAL = 5
  TERMINAL_CHAR = 6
  TERMINAL_DO = 7
  TERMINAL_ABSTRACT_PARAMETER_HINT = 8
  TERMINAL_BITXOREQ = 9
  TERMINAL_RESTRICT = 10
  TERMINAL_EXCLAMATION_POINT = 11
  TERMINAL_ARROW = 12
  TERMINAL_ELIPSIS = 13
  TERMINAL_SUBEQ = 14
  TERMINAL_IMAGINARY = 15
  TERMINAL_GT = 16
  TERMINAL_LTEQ = 17
  TERMINAL_VARIABLE_LENGTH_ARRAY = 18
  TERMINAL_ENDIF = 19
  TERMINAL_INT = 20
  TERMINAL_GTEQ = 21
  TERMINAL_COMMA = 22
  TERMINAL_ENUM = 23
  TERMINAL_VOID = 24
  TERMINAL_SHORT = 25
  TERMINAL_BITAND = 26
  TERMINAL_RSHIFT = 27
  TERMINAL_LONG = 28
  TERMINAL_POUND = 29
  TERMINAL_BITNOT = 30
  TERMINAL_QUESTIONMARK = 31
  TERMINAL__DIRECT_DECLARATOR = 32
  TERMINAL_OR = 33
  TERMINAL_INTEGER_CONSTANT = 34
  TERMINAL_IF = 35
  TERMINAL_FLOAT = 36
  TERMINAL_LPAREN = 37
  TERMINAL_DIVEQ = 38
  TERMINAL_RPAREN = 39
  TERMINAL_FLOATING_CONSTANT = 40
  TERMINAL_DECR = 41
  TERMINAL_LT = 42
  TERMINAL_DOUBLE = 43
  TERMINAL_FUNCTION_DEFINITION_HINT = 44
  TERMINAL_BOOL = 45
  TERMINAL_SIZEOF_SEPARATOR = 46
  TERMINAL_DEFINED_SEPARATOR = 47
  TERMINAL_ENUMERATION_CONSTANT = 48
  TERMINAL_EXTERN = 49
  TERMINAL_SIGNED = 50
  TERMINAL_BITANDEQ = 51
  TERMINAL_RSHIFTEQ = 52
  TERMINAL_PP_NUMBER = 53
  TERMINAL_AUTO = 54
  TERMINAL_CHARACTER_CONSTANT = 55
  TERMINAL_CONTINUE = 56
  TERMINAL_UNSIGNED = 57
  TERMINAL_NAMED_PARAMETER_HINT = 58
  TERMINAL_GOTO = 59
  TERMINAL__EXPR = 60
  TERMINAL_RSQUARE = 61
  TERMINAL_DECIMAL_FLOATING_CONSTANT = 62
  TERMINAL_REGISTER = 63
  TERMINAL_EQ = 64
  TERMINAL_POUNDPOUND = 65
  TERMINAL_MULEQ = 66
  TERMINAL_AND = 67
  TERMINAL_DOT = 68
  TERMINAL_SWITCH = 69
  TERMINAL_LSHIFTEQ = 70
  TERMINAL_UNION = 71
  TERMINAL_FUNCTION_PROTOTYPE_HINT = 72
  TERMINAL_HEXADECIMAL_FLOATING_CONSTANT = 73
  TERMINAL_SUB = 74
  TERMINAL_INLINE = 75
  TERMINAL_LABEL_HINT = 76
  TERMINAL_EXTERNAL_DECLARATION_HINT = 77
  TERMINAL_NOT = 78
  TERMINAL_IDENTIFIER = 79
  TERMINAL_TILDE = 80
  TERMINAL_LPAREN_CAST = 81
  TERMINAL_COMPLEX = 82
  TERMINAL_VOLATILE = 83
  TERMINAL_ADD = 84
  TERMINAL_DEFINED = 85
  TERMINAL_RETURN = 86
  TERMINAL_CASE = 87
  TERMINAL__DIRECT_ABSTRACT_DECLARATOR = 88
  TERMINAL_INCR = 89
  TERMINAL_BITXOR = 90
  TERMINAL_DIV = 91
  TERMINAL_RBRACE = 92
  TERMINAL_UNIVERSAL_CHARACTER_NAME = 93
  TERMINAL_DEFAULT = 94
  TERMINAL_ASSIGN = 95
  TERMINAL_ELSE_IF = 96
  TERMINAL__EXPR_SANS_COMMA = 97
  TERMINAL_STATIC = 98
  TERMINAL_FOR = 99
  TERMINAL_TRAILING_COMMA = 100
  TERMINAL_AMPERSAND = 101
  TERMINAL_NEQ = 102
  TERMINAL_MODEQ = 103
  TERMINAL_ELSE = 104
  TERMINAL_TYPEDEF = 105
  TERMINAL_LSHIFT = 106
  TERMINAL_ADDEQ = 107
  TERMINAL_ASTERISK = 108
  TERMINAL_BITOREQ = 109
  TERMINAL_BITOR = 110
  TERMINAL_SIZEOF = 111
  TERMINAL_COMMA_VA_ARGS = 112
  TERMINAL_TYPEDEF_IDENTIFIER = 113
  TERMINAL_BREAK = 114
  TERMINAL_DECLARATOR_HINT = 115
  TERMINAL_SEMI = 116
  TERMINAL_WHILE = 117
  TERMINAL_MOD = 118
  def __init__(self, tokens=None):
    self.__dict__.update(locals())
    self.expressionParsers = dict()
  def isTerminal(self, id):
    return 0 <= id <= 118
  def isNonTerminal(self, id):
    return 119 <= id <= 247
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
    if rule == 6:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_external_declarator()
      tree.add( subtree )
      return tree
    elif rule == 61:
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
    if rule == 198:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen9()
      tree.add( subtree )
      return tree
    elif current.getId() in [32, 79, 37]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen9()
      tree.add( subtree )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen3(self):
    current = self.tokens.current()
    rule = self.table[2][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(121, self.nonterminals[121]))
    tree.list = 'slist'
    if current != None and (current.getId() in [116]):
      return tree
    if current == None:
      return tree
    if rule == 7:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_external_declaration_sub_sub()
      tree.add( subtree )
      subtree = self.parse__gen4()
      tree.add( subtree )
      return tree
    return tree
  def parse_direct_declarator_modifier_list_opt(self):
    current = self.tokens.current()
    rule = self.table[3][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(122, self.nonterminals[122]))
    tree.list = False
    if current != None and (current.getId() in [60, 48, 34, 62, 37, 79, 73, 41, 55, 108, 18, 40, 81, 26, 5, 111, 89]):
      return tree
    if current == None:
      return tree
    if rule == 187:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen27()
      tree.add( subtree )
      return tree
    return tree
  def parse__gen4(self):
    current = self.tokens.current()
    rule = self.table[4][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(123, self.nonterminals[123]))
    tree.list = 'slist'
    if current != None and (current.getId() in [116]):
      return tree
    if current == None:
      return tree
    if rule == 10:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(22) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self.parse_external_declaration_sub_sub()
      tree.add( subtree )
      subtree = self.parse__gen4()
      tree.add( subtree )
      return tree
    return tree
  def parse__gen25(self):
    current = self.tokens.current()
    rule = self.table[5][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(124, self.nonterminals[124]))
    tree.list = 'nlist'
    if current != None and (current.getId() in [32, 108, 98, 88, 112, 37, 22, 79]):
      return tree
    if current == None:
      return tree
    if rule == 161:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_type_qualifier()
      tree.add( subtree )
      subtree = self.parse__gen25()
      tree.add( subtree )
      return tree
    return tree
  def parse_direct_declarator_parameter_list(self):
    current = self.tokens.current()
    rule = self.table[6][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(125, self.nonterminals[125]))
    tree.list = False
    if current != None and (current.getId() in []):
      return tree
    if current == None:
      return tree
    if rule == 111:
      tree.astTransform = AstTransformNodeCreator('ParameterList', {'identifiers': 0})
      subtree = self.parse__gen31()
      tree.add( subtree )
      return tree
    elif rule == 288:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_parameter_type_list()
      tree.add( subtree )
      return tree
    return tree
  def parse_designator(self):
    current = self.tokens.current()
    rule = self.table[7][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(126, self.nonterminals[126]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 40:
      tree.astTransform = AstTransformNodeCreator('ArrayAccess', {'index': 1})
      t = self.expect(2) # lsquare
      tree.add(t)
      subtree = self.parse__expr()
      tree.add( subtree )
      t = self.expect(61) # rsquare
      tree.add(t)
      return tree
    elif rule == 366:
      tree.astTransform = AstTransformNodeCreator('MemberAccess', {'name': 1})
      t = self.expect(68) # dot
      tree.add(t)
      t = self.expect(79) # identifier
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_abstract_parameter_declaration(self):
    current = self.tokens.current()
    rule = self.table[8][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(127, self.nonterminals[127]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 95:
      tree.astTransform = AstTransformNodeCreator('AbstractParameter', {'declaration_specifiers': 1, 'declarator': 2})
      t = self.expect(8) # abstract_parameter_hint
      tree.add(t)
      subtree = self.parse__gen1()
      tree.add( subtree )
      subtree = self.parse__gen34()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_constant(self):
    current = self.tokens.current()
    rule = self.table[9][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(128, self.nonterminals[128]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 101:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(55) # character_constant
      tree.add(t)
      return tree
    elif rule == 133:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(34) # integer_constant
      tree.add(t)
      return tree
    elif rule == 145:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(40) # floating_constant
      tree.add(t)
      return tree
    elif rule == 157:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(73) # hexadecimal_floating_constant
      tree.add(t)
      return tree
    elif rule == 267:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(48) # enumeration_constant
      tree.add(t)
      return tree
    elif rule == 424:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(62) # decimal_floating_constant
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen21(self):
    current = self.tokens.current()
    rule = self.table[10][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(129, self.nonterminals[129]))
    tree.list = False
    if current != None and (current.getId() in [22, 116]):
      return tree
    if current == None:
      return tree
    if rule == 12:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_struct_declarator_body()
      tree.add( subtree )
      return tree
    return tree
  def parse_for_init(self):
    current = self.tokens.current()
    rule = self.table[11][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(130, self.nonterminals[130]))
    tree.list = False
    if current != None and (current.getId() in [116]):
      return tree
    if current == None:
      return tree
    if rule == 109:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_declaration()
      tree.add( subtree )
      subtree = self.parse_expression_opt()
      tree.add( subtree )
      return tree
    elif rule == 247:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__expr()
      tree.add( subtree )
      return tree
    elif current.getId() in [60, 48, 34, 62, 37, 79, 73, 41, 40, 55, 108, 5, 111, 81, 89, 26]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__expr()
      tree.add( subtree )
    return tree
  def parse_pp(self):
    current = self.tokens.current()
    rule = self.table[12][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(131, self.nonterminals[131]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 59:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(47) # defined_separator
      tree.add(t)
      return tree
    elif rule == 128:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(53) # pp_number
      tree.add(t)
      return tree
    elif rule == 333:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(85) # defined
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_for_cond(self):
    current = self.tokens.current()
    rule = self.table[13][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(132, self.nonterminals[132]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 412:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(116) # semi
      tree.add(t)
      subtree = self.parse_expression_opt()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_storage_class_specifier(self):
    current = self.tokens.current()
    rule = self.table[14][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(133, self.nonterminals[133]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 100:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(49) # extern
      tree.add(t)
      return tree
    elif rule == 172:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(105) # typedef
      tree.add(t)
      return tree
    elif rule == 180:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(98) # static
      tree.add(t)
      return tree
    elif rule == 334:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(63) # register
      tree.add(t)
      return tree
    elif rule == 402:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(54) # auto
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_function_specifier(self):
    current = self.tokens.current()
    rule = self.table[15][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(134, self.nonterminals[134]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 377:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(75) # inline
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen33(self):
    current = self.tokens.current()
    rule = self.table[16][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(135, self.nonterminals[135]))
    tree.list = False
    if current != None and (current.getId() in [22, 112]):
      return tree
    if current == None:
      return tree
    if rule == 220:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_declarator()
      tree.add( subtree )
      return tree
    elif current.getId() in [32, 79, 37]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_declarator()
      tree.add( subtree )
    return tree
  def parse__gen16(self):
    current = self.tokens.current()
    rule = self.table[17][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(136, self.nonterminals[136]))
    tree.list = False
    if current != None and (current.getId() in [57, 50, 3, 4, 105, 6, 71, 115, 10, 82, 112, 1, 83, 79, 15, 22, 23, 49, 28, 72, 25, 32, 98, 88, 36, 37, 54, 43, 44, 45, 108, 63, 75, 113, 116, 24, 20]):
      return tree
    if current == None:
      return tree
    if rule == 141:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_struct_or_union_body()
      tree.add( subtree )
      return tree
    return tree
  def parse_named_parameter_declaration(self):
    current = self.tokens.current()
    rule = self.table[18][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(137, self.nonterminals[137]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 60:
      tree.astTransform = AstTransformNodeCreator('NamedParameter', {'declaration_specifiers': 1, 'declarator': 2})
      t = self.expect(58) # named_parameter_hint
      tree.add(t)
      subtree = self.parse__gen1()
      tree.add( subtree )
      subtree = self.parse__gen33()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen45(self):
    current = self.tokens.current()
    rule = self.table[19][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(138, self.nonterminals[138]))
    tree.list = False
    if current != None and (current.getId() in []):
      return tree
    if current == None:
      return tree
    if rule == 423:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_parameter_type_list()
      tree.add( subtree )
      return tree
    return tree
  def parse__gen28(self):
    current = self.tokens.current()
    rule = self.table[20][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(139, self.nonterminals[139]))
    tree.list = 'slist'
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 28:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_parameter_declaration()
      tree.add( subtree )
      subtree = self.parse__gen29()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_external_declarator(self):
    current = self.tokens.current()
    rule = self.table[21][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(140, self.nonterminals[140]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 419:
      tree.astTransform = AstTransformNodeCreator('ExternalDeclarator', {'init_declarator': 1})
      t = self.expect(115) # declarator_hint
      tree.add(t)
      subtree = self.parse__gen6()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen34(self):
    current = self.tokens.current()
    rule = self.table[22][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(141, self.nonterminals[141]))
    tree.list = False
    if current != None and (current.getId() in [22, 112]):
      return tree
    if current == None:
      return tree
    if rule == 237:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_abstract_declarator()
      tree.add( subtree )
      return tree
    elif current.getId() in [88, 37]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_abstract_declarator()
      tree.add( subtree )
    return tree
  def parse_type_qualifier(self):
    current = self.tokens.current()
    rule = self.table[23][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(142, self.nonterminals[142]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 149:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(4) # const
      tree.add(t)
      return tree
    elif rule == 375:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(10) # restrict
      tree.add(t)
      return tree
    elif rule == 409:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(83) # volatile
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_struct_or_union_sub(self):
    current = self.tokens.current()
    rule = self.table[24][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(143, self.nonterminals[143]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 85:
      tree.astTransform = AstTransformNodeCreator('StructOrUnion', {'body': 1, 'name': 0})
      t = self.expect(79) # identifier
      tree.add(t)
      subtree = self.parse__gen16()
      tree.add( subtree )
      return tree
    elif rule == 202:
      tree.astTransform = AstTransformNodeCreator('StructOrUnion', {'body': 0})
      subtree = self.parse_struct_or_union_body()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_external_prototype(self):
    current = self.tokens.current()
    rule = self.table[25][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(144, self.nonterminals[144]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 188:
      tree.astTransform = AstTransformNodeCreator('FunctionPrototype', {'declaration_list': 2, 'declarator': 1})
      t = self.expect(72) # function_prototype_hint
      tree.add(t)
      subtree = self.parse_declarator()
      tree.add( subtree )
      subtree = self.parse__gen5()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_abstract_declarator(self):
    current = self.tokens.current()
    rule = self.table[26][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(145, self.nonterminals[145]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 171:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_pointer()
      tree.add( subtree )
      subtree = self.parse__gen35()
      tree.add( subtree )
      return tree
    elif rule == 317:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__direct_abstract_declarator()
      tree.add( subtree )
      return tree
    elif current.getId() in [88, 37]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__direct_abstract_declarator()
      tree.add( subtree )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen17(self):
    current = self.tokens.current()
    rule = self.table[27][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(146, self.nonterminals[146]))
    tree.list = 'nlist'
    if current != None and (current.getId() in [92]):
      return tree
    if current == None:
      return tree
    if rule == 239:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_struct_declaration()
      tree.add( subtree )
      subtree = self.parse__gen17()
      tree.add( subtree )
      return tree
    elif current.getId() in [32, 79, 37]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_struct_declaration()
      tree.add( subtree )
      subtree = self.parse__gen17()
      tree.add( subtree )
    return tree
  def parse_struct_declaration(self):
    current = self.tokens.current()
    rule = self.table[28][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(147, self.nonterminals[147]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 345:
      tree.astTransform = AstTransformNodeCreator('StructOrUnionDeclaration', {'specifier_qualifiers': 0, 'declarators': 1})
      subtree = self.parse__gen18()
      tree.add( subtree )
      subtree = self.parse__gen19()
      tree.add( subtree )
      t = self.expect(116) # semi
      tree.add(t)
      return tree
    elif current.getId() in [32, 79, 37]:
      tree.astTransform = AstTransformNodeCreator('StructOrUnionDeclaration', {'specifier_qualifiers': 0, 'declarators': 1})
      subtree = self.parse__gen18()
      tree.add( subtree )
      subtree = self.parse__gen19()
      tree.add( subtree )
      tree.add( self.expect(116) ) # semi
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_va_args(self):
    current = self.tokens.current()
    rule = self.table[29][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(148, self.nonterminals[148]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 11:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(112) # comma_va_args
      tree.add(t)
      t = self.expect(13) # elipsis
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_declarator(self):
    current = self.tokens.current()
    rule = self.table[30][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(149, self.nonterminals[149]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 121:
      tree.astTransform = AstTransformNodeCreator('Declarator', {'direct_declarator': 1, 'pointer': 0})
      subtree = self.parse__gen26()
      tree.add( subtree )
      subtree = self.parse__direct_declarator()
      tree.add( subtree )
      return tree
    elif current.getId() in [32, 79, 37]:
      tree.astTransform = AstTransformNodeCreator('Declarator', {'direct_declarator': 1, 'pointer': 0})
      subtree = self.parse__gen26()
      tree.add( subtree )
      subtree = self.parse__direct_declarator()
      tree.add( subtree )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_declaration_list(self):
    current = self.tokens.current()
    rule = self.table[31][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(150, self.nonterminals[150]))
    tree.list = False
    if current == None:
      return tree
    if rule == 272:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen7()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen9(self):
    current = self.tokens.current()
    rule = self.table[32][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(151, self.nonterminals[151]))
    tree.list = 'slist'
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 246:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_init_declarator()
      tree.add( subtree )
      subtree = self.parse__gen10()
      tree.add( subtree )
      return tree
    elif current.getId() in [32, 79, 37]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_init_declarator()
      tree.add( subtree )
      subtree = self.parse__gen10()
      tree.add( subtree )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen10(self):
    current = self.tokens.current()
    rule = self.table[33][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(152, self.nonterminals[152]))
    tree.list = 'slist'
    if current != None and (current.getId() in [116]):
      return tree
    if current == None:
      return tree
    if rule == 250:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(22) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self.parse_init_declarator()
      tree.add( subtree )
      subtree = self.parse__gen10()
      tree.add( subtree )
      return tree
    return tree
  def parse__gen30(self):
    current = self.tokens.current()
    rule = self.table[34][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(153, self.nonterminals[153]))
    tree.list = False
    if current != None and (current.getId() in []):
      return tree
    if current == None:
      return tree
    if rule == 42:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_va_args()
      tree.add( subtree )
      return tree
    return tree
  def parse__gen11(self):
    current = self.tokens.current()
    rule = self.table[35][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(154, self.nonterminals[154]))
    tree.list = False
    if current != None and (current.getId() in [22, 116]):
      return tree
    if current == None:
      return tree
    if rule == 269:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_declarator_initializer()
      tree.add( subtree )
      return tree
    return tree
  def parse_pointer(self):
    current = self.tokens.current()
    rule = self.table[36][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(155, self.nonterminals[155]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 119:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen36()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen26(self):
    current = self.tokens.current()
    rule = self.table[37][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(156, self.nonterminals[156]))
    tree.list = False
    if current != None and (current.getId() in [32, 79, 37]):
      return tree
    if current == None:
      return tree
    if rule == 252:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_pointer()
      tree.add( subtree )
      return tree
    return tree
  def parse_struct_specifier(self):
    current = self.tokens.current()
    rule = self.table[38][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(157, self.nonterminals[157]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 365:
      tree.astTransform = AstTransformNodeCreator('Struct', {'definition': 1})
      t = self.expect(3) # struct
      tree.add(t)
      subtree = self.parse_struct_or_union_sub()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_specifier_qualifier(self):
    current = self.tokens.current()
    rule = self.table[39][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(158, self.nonterminals[158]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 14:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_type_qualifier()
      tree.add( subtree )
      return tree
    elif rule == 358:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_type_specifier()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen18(self):
    current = self.tokens.current()
    rule = self.table[40][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(159, self.nonterminals[159]))
    tree.list = 'nlist'
    if current != None and (current.getId() in [37, 32, 108, 1, 79]):
      return tree
    if current == None:
      return tree
    if rule == 258:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_specifier_qualifier()
      tree.add( subtree )
      subtree = self.parse__gen18()
      tree.add( subtree )
      return tree
    return tree
  def parse_translation_unit(self):
    current = self.tokens.current()
    rule = self.table[41][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(160, self.nonterminals[160]))
    tree.list = False
    if current == None:
      return tree
    if rule == 150:
      tree.astTransform = AstTransformNodeCreator('TranslationUnit', {'external_declarations': 0})
      subtree = self.parse__gen0()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen35(self):
    current = self.tokens.current()
    rule = self.table[42][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(161, self.nonterminals[161]))
    tree.list = False
    if current != None and (current.getId() in [22, 112]):
      return tree
    if current == None:
      return tree
    if rule == 260:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__direct_abstract_declarator()
      tree.add( subtree )
      return tree
    elif current.getId() in [88, 37]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__direct_abstract_declarator()
      tree.add( subtree )
    return tree
  def parse_init_declarator(self):
    current = self.tokens.current()
    rule = self.table[44][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(163, self.nonterminals[163]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 406:
      tree.astTransform = AstTransformNodeCreator('InitDeclarator', {'initializer': 1, 'declarator': 0})
      subtree = self.parse_declarator()
      tree.add( subtree )
      subtree = self.parse__gen11()
      tree.add( subtree )
      return tree
    elif current.getId() in [32, 79, 37]:
      tree.astTransform = AstTransformNodeCreator('InitDeclarator', {'initializer': 1, 'declarator': 0})
      subtree = self.parse_declarator()
      tree.add( subtree )
      subtree = self.parse__gen11()
      tree.add( subtree )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen6(self):
    current = self.tokens.current()
    rule = self.table[45][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(164, self.nonterminals[164]))
    tree.list = False
    if current != None and (current.getId() in [22, 116]):
      return tree
    if current == None:
      return tree
    if rule == 408:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_init_declarator()
      tree.add( subtree )
      return tree
    elif current.getId() in [32, 79, 37]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_init_declarator()
      tree.add( subtree )
    return tree
  def parse_struct_declarator(self):
    current = self.tokens.current()
    rule = self.table[46][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(165, self.nonterminals[165]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 218:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_struct_declarator_body()
      tree.add( subtree )
      return tree
    elif rule == 256:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_declarator()
      tree.add( subtree )
      subtree = self.parse__gen21()
      tree.add( subtree )
      return tree
    elif current.getId() in [32, 79, 37]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_declarator()
      tree.add( subtree )
      subtree = self.parse__gen21()
      tree.add( subtree )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen5(self):
    current = self.tokens.current()
    rule = self.table[47][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(166, self.nonterminals[166]))
    tree.list = False
    if current != None and (current.getId() in [22, 0, 116]):
      return tree
    if current == None:
      return tree
    if rule == 391:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_declaration_list()
      tree.add( subtree )
      return tree
    return tree
  def parse__gen19(self):
    current = self.tokens.current()
    rule = self.table[48][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(167, self.nonterminals[167]))
    tree.list = 'slist'
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 271:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_struct_declarator()
      tree.add( subtree )
      subtree = self.parse__gen20()
      tree.add( subtree )
      return tree
    elif current.getId() in [32, 79, 37]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_struct_declarator()
      tree.add( subtree )
      subtree = self.parse__gen20()
      tree.add( subtree )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen20(self):
    current = self.tokens.current()
    rule = self.table[49][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(168, self.nonterminals[168]))
    tree.list = 'slist'
    if current != None and (current.getId() in [116]):
      return tree
    if current == None:
      return tree
    if rule == 275:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(22) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self.parse_struct_declarator()
      tree.add( subtree )
      subtree = self.parse__gen20()
      tree.add( subtree )
      return tree
    return tree
  def parse_direct_declarator_size(self):
    current = self.tokens.current()
    rule = self.table[50][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(169, self.nonterminals[169]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 41:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__expr()
      tree.add( subtree )
      return tree
    elif rule == 126:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(18) # variable_length_array
      tree.add(t)
      return tree
    elif current.getId() in [60, 48, 34, 62, 37, 79, 73, 41, 40, 55, 108, 5, 111, 81, 89, 26]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__expr()
      tree.add( subtree )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_pointer_sub(self):
    current = self.tokens.current()
    rule = self.table[51][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(170, self.nonterminals[170]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 390:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(108) # asterisk
      tree.add(t)
      subtree = self.parse_type_qualifier_list_opt()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen36(self):
    current = self.tokens.current()
    rule = self.table[52][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(171, self.nonterminals[171]))
    tree.list = 'mlist'
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 281:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_pointer_sub()
      tree.add( subtree )
      subtree = self.parse__gen37()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen37(self):
    current = self.tokens.current()
    rule = self.table[53][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(172, self.nonterminals[172]))
    tree.list = 'mlist'
    if current != None and (current.getId() in [22, 88, 112, 37, 32, 79]):
      return tree
    if current == None:
      return tree
    if rule == 286:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_pointer_sub()
      tree.add( subtree )
      subtree = self.parse__gen37()
      tree.add( subtree )
      return tree
    return tree
  def parse_typedef_name(self):
    current = self.tokens.current()
    rule = self.table[54][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(173, self.nonterminals[173]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 417:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(113) # typedef_identifier
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_initializer(self):
    current = self.tokens.current()
    rule = self.table[55][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(174, self.nonterminals[174]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 151:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__expr_sans_comma()
      tree.add( subtree )
      return tree
    elif rule == 193:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(0) # lbrace
      tree.add(t)
      subtree = self.parse__gen12()
      tree.add( subtree )
      subtree = self.parse_trailing_comma_opt()
      tree.add( subtree )
      t = self.expect(92) # rbrace
      tree.add(t)
      return tree
    elif current.getId() in [97, 48, 34, 62, 37, 79, 73, 41, 40, 55, 108, 5, 26, 81, 89, 111]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__expr_sans_comma()
      tree.add( subtree )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_direct_declarator_modifier(self):
    current = self.tokens.current()
    rule = self.table[56][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(175, self.nonterminals[175]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 181:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(98) # static
      tree.add(t)
      return tree
    elif rule == 418:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_type_qualifier()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_union_specifier(self):
    current = self.tokens.current()
    rule = self.table[57][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(176, self.nonterminals[176]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 3:
      tree.astTransform = AstTransformNodeCreator('Union', {'definition': 1})
      t = self.expect(71) # union
      tree.add(t)
      subtree = self.parse_struct_or_union_sub()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_declaration(self):
    current = self.tokens.current()
    rule = self.table[58][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(177, self.nonterminals[177]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 43:
      tree.astTransform = AstTransformNodeCreator('Declaration', {'init_declarators': 1, 'declaration_specifiers': 0})
      subtree = self.parse__gen1()
      tree.add( subtree )
      subtree = self.parse__gen8()
      tree.add( subtree )
      t = self.expect(116) # semi
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen7(self):
    current = self.tokens.current()
    rule = self.table[59][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(178, self.nonterminals[178]))
    tree.list = 'nlist'
    if current != None and (current.getId() in [22, 0, 116]):
      return tree
    if current == None:
      return tree
    if rule == 87:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_declaration()
      tree.add( subtree )
      subtree = self.parse__gen7()
      tree.add( subtree )
      return tree
    return tree
  def parse__gen27(self):
    current = self.tokens.current()
    rule = self.table[61][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(180, self.nonterminals[180]))
    tree.list = 'nlist'
    if current != None and (current.getId() in [60, 111, 62, 34, 48, 37, 79, 73, 41, 108, 18, 40, 81, 26, 5, 55, 89]):
      return tree
    if current == None:
      return tree
    if rule == 177:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_direct_declarator_modifier()
      tree.add( subtree )
      subtree = self.parse__gen27()
      tree.add( subtree )
      return tree
    return tree
  def parse_selection_statement(self):
    current = self.tokens.current()
    rule = self.table[62][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(181, self.nonterminals[181]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 24:
      tree.astTransform = AstTransformNodeCreator('If', {'elseif': 6, 'statement': 4, 'condition': 2, 'else': 7})
      t = self.expect(35) # if
      tree.add(t)
      t = self.expect(37) # lparen
      tree.add(t)
      subtree = self.parse__expr()
      tree.add( subtree )
      t = self.expect(39) # rparen
      tree.add(t)
      subtree = self.parse_statement()
      tree.add( subtree )
      t = self.expect(19) # endif
      tree.add(t)
      subtree = self.parse__gen40()
      tree.add( subtree )
      subtree = self.parse__gen41()
      tree.add( subtree )
      return tree
    elif rule == 158:
      tree.astTransform = AstTransformNodeCreator('Switch', {'expr': 2, 'statment': 4})
      t = self.expect(69) # switch
      tree.add(t)
      t = self.expect(37) # lparen
      tree.add(t)
      subtree = self.parse__expr()
      tree.add( subtree )
      t = self.expect(39) # rparen
      tree.add(t)
      subtree = self.parse_statement()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_initializer_list_item(self):
    current = self.tokens.current()
    rule = self.table[63][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(182, self.nonterminals[182]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 127:
      tree.astTransform = AstTransformNodeCreator('Initialization', {'designation': 0, 'initializer': 1})
      subtree = self.parse__gen14()
      tree.add( subtree )
      subtree = self.parse_initializer()
      tree.add( subtree )
      return tree
    elif current.getId() in [97, 48, 34, 62, 37, 79, 73, 41, 40, 55, 108, 5, 26, 81, 89, 111]:
      tree.astTransform = AstTransformNodeCreator('Initialization', {'designation': 0, 'initializer': 1})
      subtree = self.parse__gen14()
      tree.add( subtree )
      subtree = self.parse_initializer()
      tree.add( subtree )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_expression_opt(self):
    current = self.tokens.current()
    rule = self.table[64][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(183, self.nonterminals[183]))
    tree.list = False
    if current != None and (current.getId() in [116, 39]):
      return tree
    if current == None:
      return tree
    if rule == 118:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__expr()
      tree.add( subtree )
      return tree
    elif current.getId() in [60, 48, 34, 62, 37, 79, 73, 41, 40, 55, 108, 5, 111, 81, 89, 26]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__expr()
      tree.add( subtree )
    return tree
  def parse_type_qualifier_list_opt(self):
    current = self.tokens.current()
    rule = self.table[65][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(184, self.nonterminals[184]))
    tree.list = False
    if current != None and (current.getId() in [32, 108, 98, 88, 112, 37, 22, 79]):
      return tree
    if current == None:
      return tree
    if rule == 139:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen25()
      tree.add( subtree )
      return tree
    return tree
  def parse_direct_abstract_declarator_expr(self):
    current = self.tokens.current()
    rule = self.table[66][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(185, self.nonterminals[185]))
    tree.list = False
    if current != None and (current.getId() in []):
      return tree
    if current == None:
      return tree
    if rule == 115:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_type_qualifier_list_opt()
      tree.add( subtree )
      subtree = self.parse_static_opt()
      tree.add( subtree )
      subtree = self.parse__expr()
      tree.add( subtree )
      return tree
    elif rule == 214:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(18) # variable_length_array
      tree.add(t)
      return tree
    elif current.getId() in [60, 48, 34, 62, 37, 79, 73, 41, 40, 55, 108, 5, 111, 81, 89, 26]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_type_qualifier_list_opt()
      tree.add( subtree )
      subtree = self.parse_static_opt()
      tree.add( subtree )
      subtree = self.parse__expr()
      tree.add( subtree )
    return tree
  def parse_keyword(self):
    current = self.tokens.current()
    rule = self.table[67][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(186, self.nonterminals[186]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 2:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(49) # extern
      tree.add(t)
      return tree
    elif rule == 5:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(59) # goto
      tree.add(t)
      return tree
    elif rule == 8:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(69) # switch
      tree.add(t)
      return tree
    elif rule == 25:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(35) # if
      tree.add(t)
      return tree
    elif rule == 29:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(99) # for
      tree.add(t)
      return tree
    elif rule == 32:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(24) # void
      tree.add(t)
      return tree
    elif rule == 36:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(6) # char
      tree.add(t)
      return tree
    elif rule == 44:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(28) # long
      tree.add(t)
      return tree
    elif rule == 45:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(82) # complex
      tree.add(t)
      return tree
    elif rule == 46:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(75) # inline
      tree.add(t)
      return tree
    elif rule == 63:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(20) # int
      tree.add(t)
      return tree
    elif rule == 64:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(104) # else
      tree.add(t)
      return tree
    elif rule == 69:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(117) # while
      tree.add(t)
      return tree
    elif rule == 71:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(3) # struct
      tree.add(t)
      return tree
    elif rule == 75:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(57) # unsigned
      tree.add(t)
      return tree
    elif rule == 79:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(10) # restrict
      tree.add(t)
      return tree
    elif rule == 82:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(105) # typedef
      tree.add(t)
      return tree
    elif rule == 88:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(4) # const
      tree.add(t)
      return tree
    elif rule == 93:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(23) # enum
      tree.add(t)
      return tree
    elif rule == 148:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(86) # return
      tree.add(t)
      return tree
    elif rule == 159:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(54) # auto
      tree.add(t)
      return tree
    elif rule == 160:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(94) # default
      tree.add(t)
      return tree
    elif rule == 168:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(50) # signed
      tree.add(t)
      return tree
    elif rule == 175:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(25) # short
      tree.add(t)
      return tree
    elif rule == 176:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(114) # break
      tree.add(t)
      return tree
    elif rule == 190:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(43) # double
      tree.add(t)
      return tree
    elif rule == 205:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(15) # imaginary
      tree.add(t)
      return tree
    elif rule == 230:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(83) # volatile
      tree.add(t)
      return tree
    elif rule == 236:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(63) # register
      tree.add(t)
      return tree
    elif rule == 253:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(98) # static
      tree.add(t)
      return tree
    elif rule == 266:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(87) # case
      tree.add(t)
      return tree
    elif rule == 298:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(71) # union
      tree.add(t)
      return tree
    elif rule == 359:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(111) # sizeof
      tree.add(t)
      return tree
    elif rule == 381:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(7) # do
      tree.add(t)
      return tree
    elif rule == 384:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(36) # float
      tree.add(t)
      return tree
    elif rule == 399:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(56) # continue
      tree.add(t)
      return tree
    elif rule == 414:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(45) # bool
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_block_item(self):
    current = self.tokens.current()
    rule = self.table[68][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(187, self.nonterminals[187]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 23:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_declaration()
      tree.add( subtree )
      return tree
    elif rule == 343:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_statement()
      tree.add( subtree )
      return tree
    elif current.getId() in [60, 48, 34, 62, 37, 79, 73, 41, 40, 55, 108, 5, 111, 81, 89, 26]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_statement()
      tree.add( subtree )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen0(self):
    current = self.tokens.current()
    rule = self.table[69][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(188, self.nonterminals[188]))
    tree.list = 'nlist'
    if current != None and (current.getId() in [-1]):
      return tree
    if current == None:
      return tree
    if rule == 129:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_external_declaration()
      tree.add( subtree )
      subtree = self.parse__gen0()
      tree.add( subtree )
      return tree
    return tree
  def parse__gen39(self):
    current = self.tokens.current()
    rule = self.table[70][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(189, self.nonterminals[189]))
    tree.list = 'nlist'
    if current != None and (current.getId() in [92]):
      return tree
    if current == None:
      return tree
    if rule == 78:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_block_item()
      tree.add( subtree )
      subtree = self.parse__gen39()
      tree.add( subtree )
      return tree
    elif current.getId() in [60, 48, 34, 62, 37, 79, 73, 41, 40, 55, 108, 5, 111, 81, 89, 26]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_block_item()
      tree.add( subtree )
      subtree = self.parse__gen39()
      tree.add( subtree )
    return tree
  def parse__gen22(self):
    current = self.tokens.current()
    rule = self.table[71][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(190, self.nonterminals[190]))
    tree.list = False
    if current != None and (current.getId() in [57, 50, 3, 4, 105, 6, 71, 115, 10, 82, 112, 1, 83, 79, 15, 22, 23, 49, 28, 72, 25, 32, 98, 88, 36, 37, 54, 43, 44, 45, 108, 63, 75, 113, 116, 24, 20]):
      return tree
    if current == None:
      return tree
    if rule == 351:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_enum_specifier_body()
      tree.add( subtree )
      return tree
    return tree
  def parse_for_incr(self):
    current = self.tokens.current()
    rule = self.table[72][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(191, self.nonterminals[191]))
    tree.list = False
    if current != None and (current.getId() in [39]):
      return tree
    if current == None:
      return tree
    if rule == 194:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(116) # semi
      tree.add(t)
      subtree = self.parse_expression_opt()
      tree.add( subtree )
      return tree
    return tree
  def parse_block_item_list(self):
    current = self.tokens.current()
    rule = self.table[73][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(192, self.nonterminals[192]))
    tree.list = False
    if current == None:
      return tree
    if rule == 51:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen39()
      tree.add( subtree )
      return tree
    elif current.getId() in [60, 48, 34, 62, 37, 79, 73, 41, 40, 55, 108, 5, 111, 81, 89, 26]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen39()
      tree.add( subtree )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_trailing_comma_opt(self):
    current = self.tokens.current()
    rule = self.table[74][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(193, self.nonterminals[193]))
    tree.list = False
    if current != None and (current.getId() in [92]):
      return tree
    if current == None:
      return tree
    if rule == 21:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(100) # trailing_comma
      tree.add(t)
      return tree
    return tree
  def parse_statement(self):
    current = self.tokens.current()
    rule = self.table[75][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(194, self.nonterminals[194]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 30:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_compound_statement()
      tree.add( subtree )
      return tree
    elif rule == 112:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_selection_statement()
      tree.add( subtree )
      return tree
    elif rule == 195:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_expression_statement()
      tree.add( subtree )
      return tree
    elif rule == 197:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_iteration_statement()
      tree.add( subtree )
      return tree
    elif rule == 240:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_jump_statement()
      tree.add( subtree )
      return tree
    elif rule == 326:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_labeled_statement()
      tree.add( subtree )
      return tree
    elif current.getId() in [60, 48, 34, 62, 37, 79, 73, 41, 40, 55, 108, 5, 111, 81, 89, 26]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_expression_statement()
      tree.add( subtree )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_struct_or_union_body(self):
    current = self.tokens.current()
    rule = self.table[76][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(195, self.nonterminals[195]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 114:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(0) # lbrace
      tree.add(t)
      subtree = self.parse__gen17()
      tree.add( subtree )
      t = self.expect(92) # rbrace
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_designation(self):
    current = self.tokens.current()
    rule = self.table[77][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(196, self.nonterminals[196]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 185:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen15()
      tree.add( subtree )
      t = self.expect(95) # assign
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen14(self):
    current = self.tokens.current()
    rule = self.table[78][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(197, self.nonterminals[197]))
    tree.list = False
    if current != None and (current.getId() in [97, 34, 48, 62, 5, 37, 79, 73, 41, 40, 55, 108, 0, 26, 81, 89, 111]):
      return tree
    if current == None:
      return tree
    if rule == 123:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_designation()
      tree.add( subtree )
      return tree
    return tree
  def parse_compound_statement(self):
    current = self.tokens.current()
    rule = self.table[79][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(198, self.nonterminals[198]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 265:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(0) # lbrace
      tree.add(t)
      subtree = self.parse__gen38()
      tree.add( subtree )
      t = self.expect(92) # rbrace
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_parameter_type_list(self):
    current = self.tokens.current()
    rule = self.table[80][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(199, self.nonterminals[199]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 13:
      tree.astTransform = AstTransformNodeCreator('ParameterTypeList', {'parameter_declarations': 0, 'va_args': 1})
      subtree = self.parse__gen28()
      tree.add( subtree )
      subtree = self.parse__gen30()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_type_name(self):
    current = self.tokens.current()
    rule = self.table[81][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(200, self.nonterminals[200]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 263:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(20) # int
      tree.add(t)
      return tree
    elif rule == 312:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(6) # char
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_enum_specifier_sub(self):
    current = self.tokens.current()
    rule = self.table[82][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(201, self.nonterminals[201]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 191:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_enum_specifier_body()
      tree.add( subtree )
      return tree
    elif rule == 305:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_identifier()
      tree.add( subtree )
      subtree = self.parse__gen22()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_sizeof_body(self):
    current = self.tokens.current()
    rule = self.table[83][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(202, self.nonterminals[202]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 16:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(79) # identifier
      tree.add(t)
      return tree
    elif rule == 248:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(37) # lparen
      tree.add(t)
      subtree = self.parse_type_name()
      tree.add( subtree )
      t = self.expect(39) # rparen
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_enum_specifier(self):
    current = self.tokens.current()
    rule = self.table[84][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(203, self.nonterminals[203]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 113:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(23) # enum
      tree.add(t)
      subtree = self.parse_enum_specifier_sub()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen31(self):
    current = self.tokens.current()
    rule = self.table[85][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(204, self.nonterminals[204]))
    tree.list = 'slist'
    if current != None and (current.getId() in []):
      return tree
    if current == None:
      return tree
    if rule == 65:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_identifier()
      tree.add( subtree )
      subtree = self.parse__gen32()
      tree.add( subtree )
      return tree
    return tree
  def parse__gen43(self):
    current = self.tokens.current()
    rule = self.table[86][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(205, self.nonterminals[205]))
    tree.list = 'slist'
    if current != None and (current.getId() in []):
      return tree
    if current == None:
      return tree
    if rule == 278:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__expr_sans_comma()
      tree.add( subtree )
      subtree = self.parse__gen44()
      tree.add( subtree )
      return tree
    return tree
  def parse_iteration_statement(self):
    current = self.tokens.current()
    rule = self.table[87][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(206, self.nonterminals[206]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 120:
      tree.astTransform = AstTransformNodeCreator('While', {'expr': 2, 'statement': 4})
      t = self.expect(117) # while
      tree.add(t)
      t = self.expect(37) # lparen
      tree.add(t)
      subtree = self.parse__expr()
      tree.add( subtree )
      t = self.expect(39) # rparen
      tree.add(t)
      subtree = self.parse_statement()
      tree.add( subtree )
      return tree
    elif rule == 216:
      tree.astTransform = AstTransformNodeCreator('DoWhile', {'expr': 4, 'statement': 1})
      t = self.expect(7) # do
      tree.add(t)
      subtree = self.parse_statement()
      tree.add( subtree )
      t = self.expect(117) # while
      tree.add(t)
      t = self.expect(37) # lparen
      tree.add(t)
      subtree = self.parse__expr()
      tree.add( subtree )
      t = self.expect(39) # rparen
      tree.add(t)
      t = self.expect(116) # semi
      tree.add(t)
      return tree
    elif rule == 276:
      tree.astTransform = AstTransformNodeCreator('For', {'init': 2, 'cond': 3, 'incr': 4, 'statement': 6})
      t = self.expect(99) # for
      tree.add(t)
      t = self.expect(37) # lparen
      tree.add(t)
      subtree = self.parse_for_init()
      tree.add( subtree )
      subtree = self.parse_for_cond()
      tree.add( subtree )
      subtree = self.parse_for_incr()
      tree.add( subtree )
      t = self.expect(39) # rparen
      tree.add(t)
      subtree = self.parse_statement()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_identifier(self):
    current = self.tokens.current()
    rule = self.table[88][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(207, self.nonterminals[207]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 372:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(79) # identifier
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_static_opt(self):
    current = self.tokens.current()
    rule = self.table[89][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(208, self.nonterminals[208]))
    tree.list = False
    if current != None and (current.getId() in [60, 34, 62, 37, 79, 73, 41, 40, 55, 108, 48, 26, 81, 89, 5, 111]):
      return tree
    if current == None:
      return tree
    if rule == 57:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(98) # static
      tree.add(t)
      return tree
    return tree
  def parse_enum_specifier_body(self):
    current = self.tokens.current()
    rule = self.table[90][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(209, self.nonterminals[209]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 153:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(0) # lbrace
      tree.add(t)
      subtree = self.parse__gen23()
      tree.add( subtree )
      subtree = self.parse_trailing_comma_opt()
      tree.add( subtree )
      t = self.expect(92) # rbrace
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen44(self):
    current = self.tokens.current()
    rule = self.table[91][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(210, self.nonterminals[210]))
    tree.list = 'slist'
    if current != None and (current.getId() in []):
      return tree
    if current == None:
      return tree
    if rule == 34:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(22) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self.parse__expr_sans_comma()
      tree.add( subtree )
      subtree = self.parse__gen44()
      tree.add( subtree )
      return tree
    return tree
  def parse__gen15(self):
    current = self.tokens.current()
    rule = self.table[92][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(211, self.nonterminals[211]))
    tree.list = 'nlist'
    if current != None and (current.getId() in [95]):
      return tree
    if current == None:
      return tree
    if rule == 137:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_designator()
      tree.add( subtree )
      subtree = self.parse__gen15()
      tree.add( subtree )
      return tree
    return tree
  def parse_else_if_statement_list(self):
    current = self.tokens.current()
    rule = self.table[93][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(212, self.nonterminals[212]))
    tree.list = False
    if current == None:
      return tree
    if rule == 117:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen42()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen40(self):
    current = self.tokens.current()
    rule = self.table[94][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(213, self.nonterminals[213]))
    tree.list = False
    if current != None and (current.getId() in [0, 3, 4, 5, 6, 7, 71, 10, 92, 40, 81, 83, 54, 20, 23, 26, 28, 34, 73, 36, 37, 19, 43, 25, 48, 49, 50, 55, 57, 59, 60, 111, 62, 63, 45, 56, 79, 82, 75, 114, 105, 15, 86, 87, 89, 99, 94, 98, 104, 41, 35, 108, 69, 24, 113, 76, 116, 117]):
      return tree
    if current == None:
      return tree
    if rule == 379:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_else_if_statement_list()
      tree.add( subtree )
      return tree
    return tree
  def parse_expression_statement(self):
    current = self.tokens.current()
    rule = self.table[95][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(214, self.nonterminals[214]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 291:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_expression_opt()
      tree.add( subtree )
      t = self.expect(116) # semi
      tree.add(t)
      return tree
    elif current.getId() in [60, 48, 34, 62, 37, 79, 73, 41, 40, 55, 108, 5, 111, 81, 89, 26]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_expression_opt()
      tree.add( subtree )
      tree.add( self.expect(116) ) # semi
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_parameter_declaration(self):
    current = self.tokens.current()
    rule = self.table[96][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(215, self.nonterminals[215]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 49:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_named_parameter_declaration()
      tree.add( subtree )
      return tree
    elif rule == 179:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_abstract_parameter_declaration()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_type_specifier(self):
    current = self.tokens.current()
    rule = self.table[97][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(216, self.nonterminals[216]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 0:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_union_specifier()
      tree.add( subtree )
      return tree
    elif rule == 91:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(20) # int
      tree.add(t)
      return tree
    elif rule == 116:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(15) # imaginary
      tree.add(t)
      return tree
    elif rule == 122:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(57) # unsigned
      tree.add(t)
      return tree
    elif rule == 154:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(36) # float
      tree.add(t)
      return tree
    elif rule == 166:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(82) # complex
      tree.add(t)
      return tree
    elif rule == 200:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(50) # signed
      tree.add(t)
      return tree
    elif rule == 211:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(43) # double
      tree.add(t)
      return tree
    elif rule == 234:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(45) # bool
      tree.add(t)
      return tree
    elif rule == 280:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_typedef_name()
      tree.add( subtree )
      return tree
    elif rule == 309:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(6) # char
      tree.add(t)
      return tree
    elif rule == 362:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(25) # short
      tree.add(t)
      return tree
    elif rule == 364:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(24) # void
      tree.add(t)
      return tree
    elif rule == 370:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(28) # long
      tree.add(t)
      return tree
    elif rule == 371:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_struct_specifier()
      tree.add( subtree )
      return tree
    elif rule == 376:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_enum_specifier()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_else_statement(self):
    current = self.tokens.current()
    rule = self.table[98][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(217, self.nonterminals[217]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 54:
      tree.astTransform = AstTransformNodeCreator('Else', {'statement': 1})
      t = self.expect(104) # else
      tree.add(t)
      subtree = self.parse_statement()
      tree.add( subtree )
      t = self.expect(19) # endif
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen41(self):
    current = self.tokens.current()
    rule = self.table[99][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(218, self.nonterminals[218]))
    tree.list = False
    if current != None and (current.getId() in [0, 3, 4, 5, 6, 7, 71, 10, 92, 81, 83, 40, 20, 23, 26, 28, 34, 73, 36, 37, 19, 43, 25, 48, 49, 50, 55, 57, 59, 60, 111, 62, 63, 45, 56, 79, 82, 75, 114, 105, 15, 86, 87, 89, 99, 94, 98, 54, 41, 35, 108, 69, 24, 113, 76, 116, 117]):
      return tree
    if current == None:
      return tree
    if rule == 292:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_else_statement()
      tree.add( subtree )
      return tree
    return tree
  def parse_enumerator(self):
    current = self.tokens.current()
    rule = self.table[101][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(220, self.nonterminals[220]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 1:
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
    if rule == 53:
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
    if current != None and (current.getId() in [100]):
      return tree
    if current == None:
      return tree
    if rule == 382:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(22) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self.parse_enumerator()
      tree.add( subtree )
      subtree = self.parse__gen24()
      tree.add( subtree )
      return tree
    return tree
  def parse_jump_statement(self):
    current = self.tokens.current()
    rule = self.table[104][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(223, self.nonterminals[223]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 174:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(114) # break
      tree.add(t)
      t = self.expect(116) # semi
      tree.add(t)
      return tree
    elif rule == 282:
      tree.astTransform = AstTransformNodeCreator('Return', {'expr': 1})
      t = self.expect(86) # return
      tree.add(t)
      subtree = self.parse_expression_opt()
      tree.add( subtree )
      t = self.expect(116) # semi
      tree.add(t)
      return tree
    elif rule == 397:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(56) # continue
      tree.add(t)
      return tree
    elif rule == 401:
      tree.astTransform = AstTransformNodeCreator('Goto', {'name': 1})
      t = self.expect(59) # goto
      tree.add(t)
      t = self.expect(79) # identifier
      tree.add(t)
      t = self.expect(116) # semi
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen29(self):
    current = self.tokens.current()
    rule = self.table[105][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(224, self.nonterminals[224]))
    tree.list = 'slist'
    if current != None and (current.getId() in [112]):
      return tree
    if current == None:
      return tree
    if rule == 201:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(22) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self.parse_parameter_declaration()
      tree.add( subtree )
      subtree = self.parse__gen29()
      tree.add( subtree )
      return tree
    return tree
  def parse_else_if_statement(self):
    current = self.tokens.current()
    rule = self.table[106][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(225, self.nonterminals[225]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 389:
      tree.astTransform = AstTransformNodeCreator('ElseIf', {'statement': 4, 'condition': 2})
      t = self.expect(96) # else_if
      tree.add(t)
      t = self.expect(37) # lparen
      tree.add(t)
      subtree = self.parse__expr()
      tree.add( subtree )
      t = self.expect(39) # rparen
      tree.add(t)
      subtree = self.parse_statement()
      tree.add( subtree )
      t = self.expect(19) # endif
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_struct_declarator_body(self):
    current = self.tokens.current()
    rule = self.table[107][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(226, self.nonterminals[226]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 22:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(1) # colon
      tree.add(t)
      subtree = self.parse_declarator()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen42(self):
    current = self.tokens.current()
    rule = self.table[108][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(227, self.nonterminals[227]))
    tree.list = 'nlist'
    if current != None and (current.getId() in [0, 3, 4, 5, 6, 7, 71, 10, 92, 40, 81, 83, 54, 20, 23, 26, 28, 34, 73, 35, 37, 19, 43, 25, 48, 49, 50, 55, 57, 59, 60, 111, 62, 63, 45, 56, 79, 82, 75, 114, 105, 15, 86, 87, 89, 99, 94, 98, 104, 41, 36, 108, 69, 24, 113, 76, 116, 117]):
      return tree
    if current == None:
      return tree
    if rule == 245:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_else_if_statement()
      tree.add( subtree )
      subtree = self.parse__gen42()
      tree.add( subtree )
      return tree
    return tree
  def parse_token(self):
    current = self.tokens.current()
    rule = self.table[109][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(228, self.nonterminals[228]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 26:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(53) # pp_number
      tree.add(t)
      return tree
    elif rule == 31:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(79) # identifier
      tree.add(t)
      return tree
    elif rule == 294:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_constant()
      tree.add( subtree )
      return tree
    elif rule == 346:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(5) # string_literal
      tree.add(t)
      return tree
    elif rule == 398:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_punctuator()
      tree.add( subtree )
      return tree
    elif rule == 415:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_keyword()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_declaration_specifier(self):
    current = self.tokens.current()
    rule = self.table[110][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(229, self.nonterminals[229]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 81:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_storage_class_specifier()
      tree.add( subtree )
      return tree
    elif rule == 146:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_type_qualifier()
      tree.add( subtree )
      return tree
    elif rule == 203:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_type_specifier()
      tree.add( subtree )
      return tree
    elif rule == 232:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_function_specifier()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen1(self):
    current = self.tokens.current()
    rule = self.table[111][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(230, self.nonterminals[230]))
    tree.list = 'mlist'
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 251:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_declaration_specifier()
      tree.add( subtree )
      subtree = self.parse__gen2()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen2(self):
    current = self.tokens.current()
    rule = self.table[112][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(231, self.nonterminals[231]))
    tree.list = 'mlist'
    if current != None and (current.getId() in [72, 22, 88, 37, 115, 79, 44, 108, 112, 32, 116]):
      return tree
    if current == None:
      return tree
    if rule == 156:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_declaration_specifier()
      tree.add( subtree )
      subtree = self.parse__gen2()
      tree.add( subtree )
      return tree
    return tree
  def parse__gen8(self):
    current = self.tokens.current()
    rule = self.table[113][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(232, self.nonterminals[232]))
    tree.list = False
    if current != None and (current.getId() in [116]):
      return tree
    if current == None:
      return tree
    if rule == 207:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_init_declarator_list()
      tree.add( subtree )
      return tree
    elif current.getId() in [32, 79, 37]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_init_declarator_list()
      tree.add( subtree )
    return tree
  def parse_enumeration_constant(self):
    current = self.tokens.current()
    rule = self.table[114][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(233, self.nonterminals[233]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 421:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(79) # identifier
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen12(self):
    current = self.tokens.current()
    rule = self.table[115][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(234, self.nonterminals[234]))
    tree.list = 'slist'
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 210:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_initializer_list_item()
      tree.add( subtree )
      subtree = self.parse__gen13()
      tree.add( subtree )
      return tree
    elif current.getId() in [97, 48, 34, 62, 37, 79, 73, 41, 40, 55, 108, 5, 26, 81, 89, 111]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_initializer_list_item()
      tree.add( subtree )
      subtree = self.parse__gen13()
      tree.add( subtree )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_enumerator_assignment(self):
    current = self.tokens.current()
    rule = self.table[116][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(235, self.nonterminals[235]))
    tree.list = False
    if current != None and (current.getId() in [22, 100]):
      return tree
    if current == None:
      return tree
    if rule == 27:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(95) # assign
      tree.add(t)
      subtree = self.parse__expr()
      tree.add( subtree )
      return tree
    return tree
  def parse_declarator_initializer(self):
    current = self.tokens.current()
    rule = self.table[117][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(236, self.nonterminals[236]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 340:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(95) # assign
      tree.add(t)
      subtree = self.parse_initializer()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen13(self):
    current = self.tokens.current()
    rule = self.table[118][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(237, self.nonterminals[237]))
    tree.list = 'slist'
    if current != None and (current.getId() in [100]):
      return tree
    if current == None:
      return tree
    if rule == 104:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(22) # comma
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
    rule = self.table[120][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(239, self.nonterminals[239]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 96:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_external_function()
      tree.add( subtree )
      return tree
    elif rule == 219:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen3()
      tree.add( subtree )
      t = self.expect(116) # semi
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_punctuator(self):
    current = self.tokens.current()
    rule = self.table[121][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(240, self.nonterminals[240]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 4:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(92) # rbrace
      tree.add(t)
      return tree
    elif rule == 20:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(33) # or
      tree.add(t)
      return tree
    elif rule == 35:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(89) # incr
      tree.add(t)
      return tree
    elif rule == 37:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(106) # lshift
      tree.add(t)
      return tree
    elif rule == 56:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(64) # eq
      tree.add(t)
      return tree
    elif rule == 58:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(9) # bitxoreq
      tree.add(t)
      return tree
    elif rule == 70:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(2) # lsquare
      tree.add(t)
      return tree
    elif rule == 72:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(12) # arrow
      tree.add(t)
      return tree
    elif rule == 77:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(13) # elipsis
      tree.add(t)
      return tree
    elif rule == 84:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(74) # sub
      tree.add(t)
      return tree
    elif rule == 86:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(52) # rshifteq
      tree.add(t)
      return tree
    elif rule == 98:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(102) # neq
      tree.add(t)
      return tree
    elif rule == 99:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(22) # comma
      tree.add(t)
      return tree
    elif rule == 103:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(1) # colon
      tree.add(t)
      return tree
    elif rule == 105:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(65) # poundpound
      tree.add(t)
      return tree
    elif rule == 106:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(51) # bitandeq
      tree.add(t)
      return tree
    elif rule == 110:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(16) # gt
      tree.add(t)
      return tree
    elif rule == 124:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(103) # modeq
      tree.add(t)
      return tree
    elif rule == 130:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(110) # bitor
      tree.add(t)
      return tree
    elif rule == 136:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(37) # lparen
      tree.add(t)
      return tree
    elif rule == 140:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(80) # tilde
      tree.add(t)
      return tree
    elif rule == 142:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(66) # muleq
      tree.add(t)
      return tree
    elif rule == 147:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(61) # rsquare
      tree.add(t)
      return tree
    elif rule == 155:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(84) # add
      tree.add(t)
      return tree
    elif rule == 162:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(107) # addeq
      tree.add(t)
      return tree
    elif rule == 163:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(67) # and
      tree.add(t)
      return tree
    elif rule == 167:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(0) # lbrace
      tree.add(t)
      return tree
    elif rule == 170:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(42) # lt
      tree.add(t)
      return tree
    elif rule == 173:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(116) # semi
      tree.add(t)
      return tree
    elif rule == 186:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(41) # decr
      tree.add(t)
      return tree
    elif rule == 189:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(14) # subeq
      tree.add(t)
      return tree
    elif rule == 222:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(118) # mod
      tree.add(t)
      return tree
    elif rule == 241:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(95) # assign
      tree.add(t)
      return tree
    elif rule == 297:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(101) # ampersand
      tree.add(t)
      return tree
    elif rule == 307:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(27) # rshift
      tree.add(t)
      return tree
    elif rule == 335:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(31) # questionmark
      tree.add(t)
      return tree
    elif rule == 336:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(39) # rparen
      tree.add(t)
      return tree
    elif rule == 339:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(91) # div
      tree.add(t)
      return tree
    elif rule == 341:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(90) # bitxor
      tree.add(t)
      return tree
    elif rule == 352:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(21) # gteq
      tree.add(t)
      return tree
    elif rule == 357:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(11) # exclamation_point
      tree.add(t)
      return tree
    elif rule == 394:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(70) # lshifteq
      tree.add(t)
      return tree
    elif rule == 395:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(17) # lteq
      tree.add(t)
      return tree
    elif rule == 403:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(68) # dot
      tree.add(t)
      return tree
    elif rule == 407:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(109) # bitoreq
      tree.add(t)
      return tree
    elif rule == 422:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(29) # pound
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen38(self):
    current = self.tokens.current()
    rule = self.table[122][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(241, self.nonterminals[241]))
    tree.list = False
    if current != None and (current.getId() in [92]):
      return tree
    if current == None:
      return tree
    if rule == 411:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_block_item_list()
      tree.add( subtree )
      return tree
    elif current.getId() in [60, 48, 34, 62, 37, 79, 73, 41, 40, 55, 108, 5, 111, 81, 89, 26]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_block_item_list()
      tree.add( subtree )
    return tree
  def parse__gen32(self):
    current = self.tokens.current()
    rule = self.table[123][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(242, self.nonterminals[242]))
    tree.list = 'slist'
    if current != None and (current.getId() in []):
      return tree
    if current == None:
      return tree
    if rule == 68:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(22) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self.parse_identifier()
      tree.add( subtree )
      subtree = self.parse__gen32()
      tree.add( subtree )
      return tree
    return tree
  def parse_external_declaration(self):
    current = self.tokens.current()
    rule = self.table[124][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(243, self.nonterminals[243]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 392:
      tree.astTransform = AstTransformNodeCreator('ExternalDeclaration', {'declarations': 2, 'declaration_specifiers': 1})
      t = self.expect(77) # external_declaration_hint
      tree.add(t)
      subtree = self.parse__gen1()
      tree.add( subtree )
      subtree = self.parse_external_declaration_sub()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_labeled_statement(self):
    current = self.tokens.current()
    rule = self.table[125][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(244, self.nonterminals[244]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 224:
      tree.astTransform = AstTransformNodeCreator('Label', {'name': 0, 'statement': 1})
      t = self.expect(76) # label_hint
      tree.add(t)
      t = self.expect(79) # identifier
      tree.add(t)
      t = self.expect(1) # colon
      tree.add(t)
      subtree = self.parse_statement()
      tree.add( subtree )
      return tree
    elif rule == 328:
      tree.astTransform = AstTransformNodeCreator('DefaultCase', {'statement': 2})
      t = self.expect(94) # default
      tree.add(t)
      t = self.expect(1) # colon
      tree.add(t)
      subtree = self.parse_statement()
      tree.add( subtree )
      return tree
    elif rule == 374:
      tree.astTransform = AstTransformNodeCreator('Case', {'expr': 1, 'statement': 3})
      t = self.expect(87) # case
      tree.add(t)
      subtree = self.parse__expr()
      tree.add( subtree )
      t = self.expect(1) # colon
      tree.add(t)
      subtree = self.parse_statement()
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
    if rule == 134:
      tree.astTransform = AstTransformNodeCreator('FunctionDefinition', {'body': 3, 'declaration_list': 2, 'signature': 1})
      t = self.expect(44) # function_definition_hint
      tree.add(t)
      subtree = self.parse_declarator()
      tree.add( subtree )
      subtree = self.parse__gen5()
      tree.add( subtree )
      subtree = self.parse_compound_statement()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_misc(self):
    current = self.tokens.current()
    rule = self.table[127][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(246, self.nonterminals[246]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 17:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(93) # universal_character_name
      tree.add(t)
      return tree
    elif rule == 80:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(19) # endif
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_direct_declarator_expr(self):
    current = self.tokens.current()
    rule = self.table[128][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(247, self.nonterminals[247]))
    tree.list = False
    if current != None and (current.getId() in []):
      return tree
    if current == None:
      return tree
    if rule == 183:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_direct_declarator_modifier_list_opt()
      tree.add( subtree )
      subtree = self.parse_direct_declarator_size()
      tree.add( subtree )
      return tree
    elif current.getId() in [60, 48, 34, 62, 37, 79, 73, 41, 40, 55, 108, 5, 111, 81, 89, 26]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_direct_declarator_modifier_list_opt()
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
