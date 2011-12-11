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
  def __init__(self, message):
    self.__dict__.update(locals())
  def __str__(self):
    return self.message
class ExpressionParser__expr:
  def __init__(self, parent):
    self.__dict__.update(locals())
    self.infixBp = {
      1: 1000,
      2: 9000,
      3: 1000,
      10: 5000,
      14: 9000,
      17: 15000,
      18: 1000,
      19: 10000,
      21: 8000,
      23: 15000,
      27: 1000,
      34: 1000,
      42: 11000,
      48: 11000,
      52: 15000,
      53: 2000,
      62: 1000,
      63: 8000,
      65: 1000,
      68: 9000,
      69: 15000,
      77: 12000,
      80: 9000,
      82: 1000,
      83: 12000,
      84: 1000,
      85: 3000,
      87: 14000,
      90: 1000,
      92: 10000,
      98: 1000,
      100: 16000,
      101: 6000,
      102: 7000,
      108: 15000,
      110: 12000,
      114: 15000,
      115: 4000,
    }
    self.prefixBp = {
      10: 13000,
      12: 13000,
      13: 13000,
      23: 13000,
      42: 13000,
      69: 13000,
      110: 13000,
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
    tree = ParseTree( NonTerminal(141, '_expr') )
    current = self.getCurrentToken()
    if not current:
      return tree
    elif current.getId() in [50]:
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      tree.nudMorphemeCount = 1
      tree.add( self.expect(50) )
    elif current.getId() in [50]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      tree.add( self.expect(50) )
    elif current.getId() in [69]:
      tree.astTransform = AstTransformNodeCreator('PreDecr', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(69) )
      tree.add( self.parent.parse__expr( self.getPrefixBp(69) ) )
      tree.isPrefix = True
    elif current.getId() in [110]:
      tree.astTransform = AstTransformNodeCreator('Dereference', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(110) )
      tree.add( self.parent.parse__expr( self.getPrefixBp(110) ) )
      tree.isPrefix = True
    elif current.getId() in [105]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      tree.add( self.expect(105) )
    elif current.getId() in [81, 37, 96, 20, 38, 93]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      tree.add( self.parent.parse_constant() )
    elif current.getId() in [46]:
      tree.astTransform = AstTransformNodeCreator('SizeOf', {'var': 1})
      tree.nudMorphemeCount = 1
      tree.add( self.expect(46) )
    elif current.getId() in [23]:
      tree.astTransform = AstTransformNodeCreator('PreIncr', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(23) )
      tree.add( self.parent.parse__expr( self.getPrefixBp(23) ) )
      tree.isPrefix = True
    elif current.getId() in [50]:
      tree.astTransform = AstTransformNodeCreator('ArrayIndex', {'params': 2, 'name': 0})
      tree.nudMorphemeCount = 1
      tree.add( self.expect(50) )
    elif current.getId() in [52]:
      tree.astTransform = AstTransformSubstitution(2)
      tree.nudMorphemeCount = 3
      tree.add( self.expect(52) )
      tree.add( self.parent.parse__expr() )
      tree.add( self.expect(9) )
    elif current.getId() in [10]:
      tree.astTransform = AstTransformNodeCreator('AddressOf', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(10) )
      tree.add( self.parent.parse__expr( self.getPrefixBp(10) ) )
      tree.isPrefix = True
    elif current.getId() in [60]:
      tree.astTransform = AstTransformNodeCreator('TypeInitializion', {'type': 1, 'initializer': 4})
      tree.nudMorphemeCount = 3
      tree.add( self.expect(60) )
      tree.add( self.parent.parse_type_name() )
      tree.add( self.expect(9) )
    return tree
  def led(self, left):
    tree = ParseTree( NonTerminal(141, '_expr') )
    current = self.getCurrentToken()
    if current.getId() == 102: # 'bitor'
      tree.astTransform = AstTransformNodeCreator('BitOR', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(102) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(102) - modifier ) )
    elif current.getId() == 65: # 'addeq'
      tree.astTransform = AstTransformNodeCreator('AddAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(65) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(65) - modifier ) )
    elif current.getId() == 42: # 'sub'
      tree.astTransform = AstTransformNodeCreator('Sub', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(42) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(42) - modifier ) )
    elif current.getId() == 62: # 'modeq'
      tree.astTransform = AstTransformNodeCreator('ModAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(62) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(62) - modifier ) )
    elif current.getId() == 23: # 'incr'
      tree.astTransform = AstTransformNodeCreator('PostIncr', {'var': 0})
      tree.isExprNud = True
      tree.add(left)
      tree.add( self.expect(23) )
    elif current.getId() == 3: # 'bitoreq'
      tree.astTransform = AstTransformNodeCreator('ORAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(3) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(3) - modifier ) )
    elif current.getId() == 68: # 'gteq'
      tree.astTransform = AstTransformNodeCreator('GreaterThanEq', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(68) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(68) - modifier ) )
    elif current.getId() == 53: # 'questionmark'
      tree.astTransform = AstTransformNodeCreator('TernaryOperator', {'true': 2, 'false': 4, 'cond': 0})
      tree.isExprNud = True
      tree.add(left)
      tree.add( self.expect(53) )
      modifier = 1
      tree.add( self.parent.parse__expr( self.getInfixBp(53) - modifier ) )
      tree.add( self.expect(11) )
      modifier = 1
      tree.add( self.parent.parse__expr( self.getInfixBp(53) - modifier ) )
    elif current.getId() == 87: # 'lbrace'
      tree.astTransform = AstTransformNodeCreator('TypeInitializion', {'type': 1, 'initializer': 4})
      tree.add(left)
      tree.add( self.expect(87) )
      tree.add( self.parent.parse__gen12() )
      tree.add( self.parent.parse_trailing_comma_opt() )
      tree.add( self.expect(71) )
    elif current.getId() == 114: # 'arrow'
      tree.astTransform = AstTransformNodeCreator('DerefMemberSelect', {'member': 2, 'object': 0})
      tree.isExprNud = True
      tree.add(left)
      tree.add( self.expect(114) )
      modifier = 0
      tree.add( self.parent.parse__expr( self.getInfixBp(114) - modifier ) )
    elif current.getId() == 48: # 'add'
      tree.astTransform = AstTransformNodeCreator('Add', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(48) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(48) - modifier ) )
    elif current.getId() == 98: # 'assign'
      tree.astTransform = AstTransformNodeCreator('Assign', {'var': 0, 'value': 2})
      tree.add(left)
      tree.add( self.expect(98) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(98) - modifier ) )
    elif current.getId() == 2: # 'gt'
      tree.astTransform = AstTransformNodeCreator('GreaterThan', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(2) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(2) - modifier ) )
    elif current.getId() == 14: # 'lteq'
      tree.astTransform = AstTransformNodeCreator('LessThanEq', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(14) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(14) - modifier ) )
    elif current.getId() == 29: # 'sizeof_separator'
      tree.astTransform = AstTransformNodeCreator('SizeOf', {'var': 1})
      tree.add(left)
      tree.add( self.expect(29) )
      tree.add( self.parent.parse_sizeof_body() )
    elif current.getId() == 63: # 'eq'
      tree.astTransform = AstTransformNodeCreator('Equals', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(63) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(63) - modifier ) )
    elif current.getId() == 34: # 'subeq'
      tree.astTransform = AstTransformNodeCreator('SubtractAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(34) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(34) - modifier ) )
    elif current.getId() == 90: # 'rshifteq'
      tree.astTransform = AstTransformNodeCreator('RightShiftAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(90) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(90) - modifier ) )
    elif current.getId() == 100: # 'comma'
      tree.astTransform = AstTransformNodeCreator('Comma', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(100) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(100) - modifier ) )
    elif current.getId() == 84: # 'bitxoreq'
      tree.astTransform = AstTransformNodeCreator('XORAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(84) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(84) - modifier ) )
    elif current.getId() == 19: # 'rshift'
      tree.astTransform = AstTransformNodeCreator('RightShift', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(19) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(19) - modifier ) )
    elif current.getId() == 108: # 'dot'
      tree.astTransform = AstTransformNodeCreator('MemberSelect', {'member': 2, 'object': 0})
      tree.isExprNud = True
      tree.add(left)
      tree.add( self.expect(108) )
      modifier = 0
      tree.add( self.parent.parse__expr( self.getInfixBp(108) - modifier ) )
    elif current.getId() == 10: # 'bitand'
      tree.astTransform = AstTransformNodeCreator('BitAND', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(10) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(10) - modifier ) )
    elif current.getId() == 27: # 'diveq'
      tree.astTransform = AstTransformNodeCreator('DivideAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(27) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(27) - modifier ) )
    elif current.getId() == 52: # 'lparen'
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      tree.add(left)
      tree.add( self.expect(52) )
      tree.add( self.parent.parse__gen40() )
      tree.add( self.expect(9) )
    elif current.getId() == 83: # 'div'
      tree.astTransform = AstTransformNodeCreator('Div', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(83) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(83) - modifier ) )
    elif current.getId() == 77: # 'mod'
      tree.astTransform = AstTransformNodeCreator('Mod', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(77) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(77) - modifier ) )
    elif current.getId() == 92: # 'lshift'
      tree.astTransform = AstTransformNodeCreator('LeftShift', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(92) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(92) - modifier ) )
    elif current.getId() == 101: # 'bitxor'
      tree.astTransform = AstTransformNodeCreator('BitXOR', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(101) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(101) - modifier ) )
    elif current.getId() == 18: # 'lshifteq'
      tree.astTransform = AstTransformNodeCreator('LeftShiftAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(18) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(18) - modifier ) )
    elif current.getId() == 82: # 'muleq'
      tree.astTransform = AstTransformNodeCreator('MultiplyAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(82) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(82) - modifier ) )
    elif current.getId() == 69: # 'decr'
      tree.astTransform = AstTransformNodeCreator('PostDecr', {'var': 0})
      tree.isExprNud = True
      tree.add(left)
      tree.add( self.expect(69) )
    elif current.getId() == 80: # 'lt'
      tree.astTransform = AstTransformNodeCreator('LessThan', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(80) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(80) - modifier ) )
    elif current.getId() == 110: # 'asterisk'
      tree.astTransform = AstTransformNodeCreator('Mul', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(110) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(110) - modifier ) )
    elif current.getId() == 17: # 'lsquare'
      tree.astTransform = AstTransformNodeCreator('ArrayIndex', {'params': 2, 'name': 0})
      tree.add(left)
      tree.add( self.expect(17) )
      tree.add( self.parent.parse__gen40() )
      tree.add( self.expect(40) )
    elif current.getId() == 1: # 'bitandeq'
      tree.astTransform = AstTransformNodeCreator('ANDAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(1) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(1) - modifier ) )
    return tree
class ExpressionParser__expr_sans_comma:
  def __init__(self, parent):
    self.__dict__.update(locals())
    self.infixBp = {
      1: 1000,
      2: 9000,
      3: 1000,
      10: 5000,
      14: 9000,
      17: 15000,
      18: 1000,
      19: 10000,
      21: 8000,
      23: 15000,
      27: 1000,
      34: 1000,
      42: 11000,
      48: 11000,
      52: 15000,
      53: 2000,
      62: 1000,
      63: 8000,
      65: 1000,
      68: 9000,
      69: 15000,
      77: 12000,
      80: 9000,
      82: 1000,
      83: 12000,
      84: 1000,
      85: 3000,
      87: 14000,
      90: 1000,
      92: 10000,
      98: 1000,
      101: 6000,
      102: 7000,
      108: 15000,
      110: 12000,
      114: 15000,
      115: 4000,
    }
    self.prefixBp = {
      10: 13000,
      12: 13000,
      13: 13000,
      23: 13000,
      42: 13000,
      69: 13000,
      110: 13000,
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
    tree = ParseTree( NonTerminal(228, '_expr_sans_comma') )
    current = self.getCurrentToken()
    if not current:
      return tree
    elif current.getId() in [50]:
      tree.astTransform = AstTransformNodeCreator('ArrayIndex', {'params': 2, 'name': 0})
      tree.nudMorphemeCount = 1
      tree.add( self.expect(50) )
    elif current.getId() in [50]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      tree.add( self.expect(50) )
    elif current.getId() in [81, 37, 96, 20, 38, 93]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      tree.add( self.parent.parse_constant() )
    elif current.getId() in [110]:
      tree.astTransform = AstTransformNodeCreator('Dereference', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(110) )
      tree.add( self.parent.parse__expr_sans_comma( self.getPrefixBp(110) ) )
      tree.isPrefix = True
    elif current.getId() in [105]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      tree.add( self.expect(105) )
    elif current.getId() in [46]:
      tree.astTransform = AstTransformNodeCreator('SizeOf', {'var': 1})
      tree.nudMorphemeCount = 1
      tree.add( self.expect(46) )
    elif current.getId() in [52]:
      tree.astTransform = AstTransformSubstitution(2)
      tree.nudMorphemeCount = 3
      tree.add( self.expect(52) )
      tree.add( self.parent.parse__expr_sans_comma() )
      tree.add( self.expect(9) )
    elif current.getId() in [60]:
      tree.astTransform = AstTransformNodeCreator('TypeInitializion', {'type': 1, 'initializer': 4})
      tree.nudMorphemeCount = 3
      tree.add( self.expect(60) )
      tree.add( self.parent.parse_type_name() )
      tree.add( self.expect(9) )
    elif current.getId() in [69]:
      tree.astTransform = AstTransformNodeCreator('PreDecr', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(69) )
      tree.add( self.parent.parse__expr_sans_comma( self.getPrefixBp(69) ) )
      tree.isPrefix = True
    elif current.getId() in [50]:
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      tree.nudMorphemeCount = 1
      tree.add( self.expect(50) )
    elif current.getId() in [23]:
      tree.astTransform = AstTransformNodeCreator('PreIncr', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(23) )
      tree.add( self.parent.parse__expr_sans_comma( self.getPrefixBp(23) ) )
      tree.isPrefix = True
    elif current.getId() in [10]:
      tree.astTransform = AstTransformNodeCreator('AddressOf', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(10) )
      tree.add( self.parent.parse__expr_sans_comma( self.getPrefixBp(10) ) )
      tree.isPrefix = True
    return tree
  def led(self, left):
    tree = ParseTree( NonTerminal(228, '_expr_sans_comma') )
    current = self.getCurrentToken()
    if current.getId() == 23: # 'incr'
      tree.astTransform = AstTransformNodeCreator('PostIncr', {'var': 0})
      tree.isExprNud = True
      tree.add(left)
      tree.add( self.expect(23) )
    elif current.getId() == 102: # 'bitor'
      tree.astTransform = AstTransformNodeCreator('BitOR', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(102) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(102) - modifier ) )
    elif current.getId() == 52: # 'lparen'
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      tree.add(left)
      tree.add( self.expect(52) )
      tree.add( self.parent.parse__gen40() )
      tree.add( self.expect(9) )
    elif current.getId() == 63: # 'eq'
      tree.astTransform = AstTransformNodeCreator('Equals', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(63) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(63) - modifier ) )
    elif current.getId() == 19: # 'rshift'
      tree.astTransform = AstTransformNodeCreator('RightShift', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(19) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(19) - modifier ) )
    elif current.getId() == 27: # 'diveq'
      tree.astTransform = AstTransformNodeCreator('DivideAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(27) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(27) - modifier ) )
    elif current.getId() == 14: # 'lteq'
      tree.astTransform = AstTransformNodeCreator('LessThanEq', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(14) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(14) - modifier ) )
    elif current.getId() == 17: # 'lsquare'
      tree.astTransform = AstTransformNodeCreator('ArrayIndex', {'params': 2, 'name': 0})
      tree.add(left)
      tree.add( self.expect(17) )
      tree.add( self.parent.parse__gen40() )
      tree.add( self.expect(40) )
    elif current.getId() == 87: # 'lbrace'
      tree.astTransform = AstTransformNodeCreator('TypeInitializion', {'type': 1, 'initializer': 4})
      tree.add(left)
      tree.add( self.expect(87) )
      tree.add( self.parent.parse__gen12() )
      tree.add( self.parent.parse_trailing_comma_opt() )
      tree.add( self.expect(71) )
    elif current.getId() == 98: # 'assign'
      tree.astTransform = AstTransformNodeCreator('Assign', {'var': 0, 'value': 2})
      tree.add(left)
      tree.add( self.expect(98) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(98) - modifier ) )
    elif current.getId() == 18: # 'lshifteq'
      tree.astTransform = AstTransformNodeCreator('LeftShiftAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(18) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(18) - modifier ) )
    elif current.getId() == 90: # 'rshifteq'
      tree.astTransform = AstTransformNodeCreator('RightShiftAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(90) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(90) - modifier ) )
    elif current.getId() == 62: # 'modeq'
      tree.astTransform = AstTransformNodeCreator('ModAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(62) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(62) - modifier ) )
    elif current.getId() == 68: # 'gteq'
      tree.astTransform = AstTransformNodeCreator('GreaterThanEq', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(68) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(68) - modifier ) )
    elif current.getId() == 48: # 'add'
      tree.astTransform = AstTransformNodeCreator('Add', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(48) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(48) - modifier ) )
    elif current.getId() == 108: # 'dot'
      tree.astTransform = AstTransformNodeCreator('MemberSelect', {'member': 2, 'object': 0})
      tree.isExprNud = True
      tree.add(left)
      tree.add( self.expect(108) )
      modifier = 0
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(108) - modifier ) )
    elif current.getId() == 1: # 'bitandeq'
      tree.astTransform = AstTransformNodeCreator('ANDAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(1) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(1) - modifier ) )
    elif current.getId() == 92: # 'lshift'
      tree.astTransform = AstTransformNodeCreator('LeftShift', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(92) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(92) - modifier ) )
    elif current.getId() == 82: # 'muleq'
      tree.astTransform = AstTransformNodeCreator('MultiplyAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(82) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(82) - modifier ) )
    elif current.getId() == 110: # 'asterisk'
      tree.astTransform = AstTransformNodeCreator('Mul', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(110) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(110) - modifier ) )
    elif current.getId() == 42: # 'sub'
      tree.astTransform = AstTransformNodeCreator('Sub', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(42) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(42) - modifier ) )
    elif current.getId() == 3: # 'bitoreq'
      tree.astTransform = AstTransformNodeCreator('ORAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(3) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(3) - modifier ) )
    elif current.getId() == 114: # 'arrow'
      tree.astTransform = AstTransformNodeCreator('DerefMemberSelect', {'member': 2, 'object': 0})
      tree.isExprNud = True
      tree.add(left)
      tree.add( self.expect(114) )
      modifier = 0
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(114) - modifier ) )
    elif current.getId() == 29: # 'sizeof_separator'
      tree.astTransform = AstTransformNodeCreator('SizeOf', {'var': 1})
      tree.add(left)
      tree.add( self.expect(29) )
      tree.add( self.parent.parse_sizeof_body() )
    elif current.getId() == 84: # 'bitxoreq'
      tree.astTransform = AstTransformNodeCreator('XORAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(84) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(84) - modifier ) )
    elif current.getId() == 101: # 'bitxor'
      tree.astTransform = AstTransformNodeCreator('BitXOR', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(101) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(101) - modifier ) )
    elif current.getId() == 83: # 'div'
      tree.astTransform = AstTransformNodeCreator('Div', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(83) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(83) - modifier ) )
    elif current.getId() == 80: # 'lt'
      tree.astTransform = AstTransformNodeCreator('LessThan', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(80) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(80) - modifier ) )
    elif current.getId() == 69: # 'decr'
      tree.astTransform = AstTransformNodeCreator('PostDecr', {'var': 0})
      tree.isExprNud = True
      tree.add(left)
      tree.add( self.expect(69) )
    elif current.getId() == 65: # 'addeq'
      tree.astTransform = AstTransformNodeCreator('AddAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(65) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(65) - modifier ) )
    elif current.getId() == 10: # 'bitand'
      tree.astTransform = AstTransformNodeCreator('BitAND', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(10) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(10) - modifier ) )
    elif current.getId() == 53: # 'questionmark'
      tree.astTransform = AstTransformNodeCreator('TernaryOperator', {'true': 2, 'false': 4, 'cond': 0})
      tree.isExprNud = True
      tree.add(left)
      tree.add( self.expect(53) )
      modifier = 1
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(53) - modifier ) )
      tree.add( self.expect(11) )
      modifier = 1
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(53) - modifier ) )
    elif current.getId() == 77: # 'mod'
      tree.astTransform = AstTransformNodeCreator('Mod', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(77) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(77) - modifier ) )
    elif current.getId() == 2: # 'gt'
      tree.astTransform = AstTransformNodeCreator('GreaterThan', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(2) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(2) - modifier ) )
    elif current.getId() == 34: # 'subeq'
      tree.astTransform = AstTransformNodeCreator('SubtractAssign', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(34) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(34) - modifier ) )
    return tree
class ExpressionParser__direct_declarator:
  def __init__(self, parent):
    self.__dict__.update(locals())
    self.infixBp = {
      17: 1000,
      52: 1000,
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
    tree = ParseTree( NonTerminal(202, '_direct_declarator') )
    current = self.getCurrentToken()
    if not current:
      return tree
    if current.getId() in [50]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      tree.add( self.expect(50) )
    elif current.getId() in [52]:
      tree.astTransform = AstTransformSubstitution(1)
      tree.nudMorphemeCount = 3
      tree.add( self.expect(52) )
      tree.add( self.parent.parse_declarator() )
      tree.add( self.expect(9) )
    return tree
  def led(self, left):
    tree = ParseTree( NonTerminal(202, '_direct_declarator') )
    current = self.getCurrentToken()
    if current.getId() == 52: # 'lparen'
      tree.astTransform = AstTransformNodeCreator('FunctionSignature', {'params': 2, 'declarator': 0})
      tree.isExprNud = True
      tree.add(left)
      tree.add( self.expect(52) )
      tree.add( self.parent.parse_direct_declarator_parameter_list() )
      tree.add( self.expect(9) )
    elif current.getId() == 17: # 'lsquare'
      tree.astTransform = AstTransformNodeCreator('Array', {'name': 0, 'size': 2})
      tree.isExprNud = True
      tree.add(left)
      tree.add( self.expect(17) )
      tree.add( self.parent.parse_direct_declarator_expr() )
      tree.add( self.expect(40) )
    return tree
class ExpressionParser__direct_abstract_declarator:
  def __init__(self, parent):
    self.__dict__.update(locals())
    self.infixBp = {
      17: 1000,
      52: 1000,
    }
    self.prefixBp = {
      52: 2000,
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
    tree = ParseTree( NonTerminal(163, '_direct_abstract_declarator') )
    current = self.getCurrentToken()
    if not current:
      return tree
    elif current.getId() in [52]:
      tree.astTransform = AstTransformSubstitution(1)
      tree.nudMorphemeCount = 3
      tree.add( self.expect(52) )
      tree.add( self.parent.parse_abstract_declarator() )
      tree.add( self.expect(9) )
    return tree
  def led(self, left):
    tree = ParseTree( NonTerminal(163, '_direct_abstract_declarator') )
    current = self.getCurrentToken()
    if current.getId() == 52: # 'lparen'
      tree.astTransform = AstTransformNodeCreator('AbstractFunction', {'object': 0, 'params': 2})
      tree.add(left)
      tree.add( self.expect(52) )
      tree.add( self.parent.parse__gen42() )
      tree.add( self.expect(9) )
    elif current.getId() == 17: # 'lsquare'
      tree.astTransform = AstTransformNodeCreator('AbstractArray', {'object': 0, 'size': 2})
      tree.add(left)
      tree.add( self.expect(17) )
      tree.add( self.parent.parse_direct_abstract_declarator_expr() )
      tree.add( self.expect(40) )
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
    0: 'while',
    1: 'bitandeq',
    2: 'gt',
    3: 'bitoreq',
    4: 'universal_character_name',
    5: 'int',
    6: 'external_declaration_hint',
    7: 'if',
    8: 'enum',
    9: 'rparen',
    10: 'bitand',
    11: 'colon',
    12: 'not',
    13: 'bitnot',
    14: 'lteq',
    15: 'semi',
    16: 'float',
    17: 'lsquare',
    18: 'lshifteq',
    19: 'rshift',
    20: 'floating_constant',
    21: 'neq',
    22: 'double',
    23: 'incr',
    24: 'function_definition_hint',
    25: 'return',
    26: 'exclamation_point',
    27: 'diveq',
    28: 'typedef',
    29: 'sizeof_separator',
    30: 'poundpound',
    31: 'signed',
    32: 'imaginary',
    33: 'pound',
    34: 'subeq',
    35: 'restrict',
    36: 'tilde',
    37: 'integer_constant',
    38: 'character_constant',
    39: 'unsigned',
    40: 'rsquare',
    41: 'else_if',
    42: 'sub',
    43: '_direct_abstract_declarator',
    44: 'label_hint',
    45: 'bool',
    46: 'sizeof',
    47: 'const',
    48: 'add',
    49: 'break',
    50: 'identifier',
    51: 'case',
    52: 'lparen',
    53: 'questionmark',
    54: 'declarator_hint',
    55: '_expr',
    56: 'defined',
    57: 'char',
    58: '_direct_declarator',
    59: '_expr_sans_comma',
    60: 'lparen_cast',
    61: 'ampersand',
    62: 'modeq',
    63: 'eq',
    64: 'extern',
    65: 'addeq',
    66: 'else',
    67: 'goto',
    68: 'gteq',
    69: 'decr',
    70: 'static',
    71: 'rbrace',
    72: 'volatile',
    73: 'switch',
    74: 'endif',
    75: 'trailing_comma',
    76: 'comma_va_args',
    77: 'mod',
    78: 'elipsis',
    79: 'auto',
    80: 'lt',
    81: 'enumeration_constant',
    82: 'muleq',
    83: 'div',
    84: 'bitxoreq',
    85: 'or',
    86: 'function_prototype_hint',
    87: 'lbrace',
    88: 'register',
    89: 'inline',
    90: 'rshifteq',
    91: 'do',
    92: 'lshift',
    93: 'hexadecimal_floating_constant',
    94: 'default',
    95: 'void',
    96: 'decimal_floating_constant',
    97: 'for',
    98: 'assign',
    99: 'defined_separator',
    100: 'comma',
    101: 'bitxor',
    102: 'bitor',
    103: 'continue',
    104: 'typedef_identifier',
    105: 'string_literal',
    106: 'struct',
    107: 'long',
    108: 'dot',
    109: 'union',
    110: 'asterisk',
    111: 'complex',
    112: 'pp_number',
    113: 'short',
    114: 'arrow',
    115: 'and',
    'while': 0,
    'bitandeq': 1,
    'gt': 2,
    'bitoreq': 3,
    'universal_character_name': 4,
    'int': 5,
    'external_declaration_hint': 6,
    'if': 7,
    'enum': 8,
    'rparen': 9,
    'bitand': 10,
    'colon': 11,
    'not': 12,
    'bitnot': 13,
    'lteq': 14,
    'semi': 15,
    'float': 16,
    'lsquare': 17,
    'lshifteq': 18,
    'rshift': 19,
    'floating_constant': 20,
    'neq': 21,
    'double': 22,
    'incr': 23,
    'function_definition_hint': 24,
    'return': 25,
    'exclamation_point': 26,
    'diveq': 27,
    'typedef': 28,
    'sizeof_separator': 29,
    'poundpound': 30,
    'signed': 31,
    'imaginary': 32,
    'pound': 33,
    'subeq': 34,
    'restrict': 35,
    'tilde': 36,
    'integer_constant': 37,
    'character_constant': 38,
    'unsigned': 39,
    'rsquare': 40,
    'else_if': 41,
    'sub': 42,
    '_direct_abstract_declarator': 43,
    'label_hint': 44,
    'bool': 45,
    'sizeof': 46,
    'const': 47,
    'add': 48,
    'break': 49,
    'identifier': 50,
    'case': 51,
    'lparen': 52,
    'questionmark': 53,
    'declarator_hint': 54,
    '_expr': 55,
    'defined': 56,
    'char': 57,
    '_direct_declarator': 58,
    '_expr_sans_comma': 59,
    'lparen_cast': 60,
    'ampersand': 61,
    'modeq': 62,
    'eq': 63,
    'extern': 64,
    'addeq': 65,
    'else': 66,
    'goto': 67,
    'gteq': 68,
    'decr': 69,
    'static': 70,
    'rbrace': 71,
    'volatile': 72,
    'switch': 73,
    'endif': 74,
    'trailing_comma': 75,
    'comma_va_args': 76,
    'mod': 77,
    'elipsis': 78,
    'auto': 79,
    'lt': 80,
    'enumeration_constant': 81,
    'muleq': 82,
    'div': 83,
    'bitxoreq': 84,
    'or': 85,
    'function_prototype_hint': 86,
    'lbrace': 87,
    'register': 88,
    'inline': 89,
    'rshifteq': 90,
    'do': 91,
    'lshift': 92,
    'hexadecimal_floating_constant': 93,
    'default': 94,
    'void': 95,
    'decimal_floating_constant': 96,
    'for': 97,
    'assign': 98,
    'defined_separator': 99,
    'comma': 100,
    'bitxor': 101,
    'bitor': 102,
    'continue': 103,
    'typedef_identifier': 104,
    'string_literal': 105,
    'struct': 106,
    'long': 107,
    'dot': 108,
    'union': 109,
    'asterisk': 110,
    'complex': 111,
    'pp_number': 112,
    'short': 113,
    'arrow': 114,
    'and': 115,
  }
  # Quark - finite string set maps one string to exactly one int, and vice versa
  nonterminals = {
    116: '_gen27',
    117: '_gen28',
    118: 'designation',
    119: 'labeled_statement',
    120: '_gen33',
    121: 'enum_specifier_sub',
    122: 'external_declarator',
    123: '_gen37',
    124: 'type_qualifier_list_opt',
    125: 'type_qualifier',
    126: '_gen40',
    127: 'pointer_opt',
    128: 'enum_specifier_body',
    129: '_gen22',
    130: 'storage_class_specifier',
    131: '_gen41',
    132: 'else_statement',
    133: '_gen38',
    134: 'declarator',
    135: 'declaration_list',
    136: 'sizeof_body',
    137: '_gen5',
    138: '_gen10',
    139: 'jump_statement',
    140: 'else_if_statement',
    141: '_expr',
    142: 'pointer_sub',
    143: '_gen14',
    144: '_gen23',
    145: '_gen24',
    146: 'enumerator',
    147: '_gen39',
    148: 'init_declarator',
    149: '_gen6',
    150: '_gen30',
    151: '_gen11',
    152: 'initializer_list_item',
    153: 'direct_abstract_declarator_opt',
    154: 'direct_abstract_declarator_expr',
    155: 'type_specifier',
    156: 'enumeration_constant',
    157: 'enumerator_assignment',
    158: 'expression_opt',
    159: 'static_opt',
    160: 'initializer',
    161: 'union_specifier',
    162: 'declaration',
    163: '_direct_abstract_declarator',
    164: '_gen7',
    165: 'enum_specifier',
    166: 'block_item',
    167: '_gen36',
    168: 'else_if_statement_list',
    169: 'parameter_declaration_sub',
    170: '_gen32',
    171: 'typedef_name',
    172: '_gen12',
    173: '_gen13',
    174: 'direct_declarator_expr',
    175: 'init_declarator_list',
    176: 'pp',
    177: 'for_incr',
    178: 'declarator_initializer',
    179: 'struct_specifier',
    180: 'parameter_declaration_sub_sub',
    181: 'trailing_comma_opt',
    182: 'va_args',
    183: '_gen34',
    184: 'struct_or_union_body',
    185: 'expression_statement',
    186: '_gen16',
    187: '_gen25',
    188: 'statement',
    189: '_gen42',
    190: 'external_prototype',
    191: 'misc',
    192: 'abstract_declarator',
    193: 'struct_declaration',
    194: 'designator',
    195: 'parameter_type_list',
    196: 'for_init',
    197: 'translation_unit',
    198: 'function_specifier',
    199: 'external_declaration',
    200: '_gen0',
    201: '_gen8',
    202: '_direct_declarator',
    203: 'struct_or_union_sub',
    204: 'specifier_qualifier',
    205: '_gen1',
    206: '_gen18',
    207: 'selection_statement',
    208: 'direct_declarator_modifier_list_opt',
    209: 'direct_declarator_size',
    210: '_gen31',
    211: '_gen2',
    212: 'struct_declarator',
    213: '_gen19',
    214: '_gen17',
    215: '_gen20',
    216: 'declaration_specifier',
    217: 'direct_declarator_modifier',
    218: '_gen26',
    219: 'block_item_list',
    220: '_gen15',
    221: '_gen35',
    222: 'type_name',
    223: 'for_cond',
    224: 'external_declaration_sub',
    225: 'pointer',
    226: 'keyword',
    227: 'external_function',
    228: '_expr_sans_comma',
    229: 'struct_declarator_body',
    230: 'iteration_statement',
    231: '_gen9',
    232: 'token',
    233: 'constant',
    234: '_gen21',
    235: '_gen3',
    236: '_gen4',
    237: 'external_declaration_sub_sub',
    238: '_gen29',
    239: 'compound_statement',
    240: 'direct_declarator_parameter_list',
    241: 'identifier',
    242: 'punctuator',
    243: 'parameter_declaration',
    '_gen27': 116,
    '_gen28': 117,
    'designation': 118,
    'labeled_statement': 119,
    '_gen33': 120,
    'enum_specifier_sub': 121,
    'external_declarator': 122,
    '_gen37': 123,
    'type_qualifier_list_opt': 124,
    'type_qualifier': 125,
    '_gen40': 126,
    'pointer_opt': 127,
    'enum_specifier_body': 128,
    '_gen22': 129,
    'storage_class_specifier': 130,
    '_gen41': 131,
    'else_statement': 132,
    '_gen38': 133,
    'declarator': 134,
    'declaration_list': 135,
    'sizeof_body': 136,
    '_gen5': 137,
    '_gen10': 138,
    'jump_statement': 139,
    'else_if_statement': 140,
    '_expr': 141,
    'pointer_sub': 142,
    '_gen14': 143,
    '_gen23': 144,
    '_gen24': 145,
    'enumerator': 146,
    '_gen39': 147,
    'init_declarator': 148,
    '_gen6': 149,
    '_gen30': 150,
    '_gen11': 151,
    'initializer_list_item': 152,
    'direct_abstract_declarator_opt': 153,
    'direct_abstract_declarator_expr': 154,
    'type_specifier': 155,
    'enumeration_constant': 156,
    'enumerator_assignment': 157,
    'expression_opt': 158,
    'static_opt': 159,
    'initializer': 160,
    'union_specifier': 161,
    'declaration': 162,
    '_direct_abstract_declarator': 163,
    '_gen7': 164,
    'enum_specifier': 165,
    'block_item': 166,
    '_gen36': 167,
    'else_if_statement_list': 168,
    'parameter_declaration_sub': 169,
    '_gen32': 170,
    'typedef_name': 171,
    '_gen12': 172,
    '_gen13': 173,
    'direct_declarator_expr': 174,
    'init_declarator_list': 175,
    'pp': 176,
    'for_incr': 177,
    'declarator_initializer': 178,
    'struct_specifier': 179,
    'parameter_declaration_sub_sub': 180,
    'trailing_comma_opt': 181,
    'va_args': 182,
    '_gen34': 183,
    'struct_or_union_body': 184,
    'expression_statement': 185,
    '_gen16': 186,
    '_gen25': 187,
    'statement': 188,
    '_gen42': 189,
    'external_prototype': 190,
    'misc': 191,
    'abstract_declarator': 192,
    'struct_declaration': 193,
    'designator': 194,
    'parameter_type_list': 195,
    'for_init': 196,
    'translation_unit': 197,
    'function_specifier': 198,
    'external_declaration': 199,
    '_gen0': 200,
    '_gen8': 201,
    '_direct_declarator': 202,
    'struct_or_union_sub': 203,
    'specifier_qualifier': 204,
    '_gen1': 205,
    '_gen18': 206,
    'selection_statement': 207,
    'direct_declarator_modifier_list_opt': 208,
    'direct_declarator_size': 209,
    '_gen31': 210,
    '_gen2': 211,
    'struct_declarator': 212,
    '_gen19': 213,
    '_gen17': 214,
    '_gen20': 215,
    'declaration_specifier': 216,
    'direct_declarator_modifier': 217,
    '_gen26': 218,
    'block_item_list': 219,
    '_gen15': 220,
    '_gen35': 221,
    'type_name': 222,
    'for_cond': 223,
    'external_declaration_sub': 224,
    'pointer': 225,
    'keyword': 226,
    'external_function': 227,
    '_expr_sans_comma': 228,
    'struct_declarator_body': 229,
    'iteration_statement': 230,
    '_gen9': 231,
    'token': 232,
    'constant': 233,
    '_gen21': 234,
    '_gen3': 235,
    '_gen4': 236,
    'external_declaration_sub_sub': 237,
    '_gen29': 238,
    'compound_statement': 239,
    'direct_declarator_parameter_list': 240,
    'identifier': 241,
    'punctuator': 242,
    'parameter_declaration': 243,
  }
  # table[nonterminal][terminal] = rule
  table = [
    [-1, -1, -1, -1, -1, 4, -1, -1, 4, -1, -1, -1, -1, -1, -1, -1, 4, -1, -1, -1, -1, -1, 4, -1, -1, -1, -1, -1, 4, -1, -1, 4, 4, -1, -1, 4, -1, -1, -1, 4, -1, -1, -1, -1, -1, 4, -1, 4, -1, -1, -1, -1, -1, -1, -1, -1, -1, 4, -1, -1, -1, -1, -1, -1, 4, -1, -1, -1, -1, -1, 4, -1, 4, -1, -1, -1, -1, -1, -1, 4, -1, -1, -1, -1, -1, -1, -1, -1, 4, 4, -1, -1, -1, -1, -1, 4, -1, -1, -1, -1, -1, -1, -1, -1, 4, -1, 4, 4, -1, 4, -1, 4, -1, 4, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 9, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 7, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 362, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 362, -1, -1, -1, -1, -1, -1, -1, -1, -1, 362, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 142, -1, -1, -1, -1, -1, -1, 364, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 55, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 211, -1, -1, -1, -1, -1, -1, -1, -1, 211, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 98, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 98, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 6, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 124, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 34, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [328, -1, -1, -1, -1, 328, -1, 328, 328, -1, 328, -1, -1, -1, -1, 328, 328, -1, -1, -1, 328, -1, 328, 328, -1, 328, -1, -1, 328, -1, -1, 328, 328, -1, -1, 328, -1, 328, 328, 328, -1, 328, -1, -1, 328, 328, 328, 328, -1, 328, 328, 328, 328, -1, -1, 328, -1, 328, -1, -1, 328, -1, -1, -1, 328, -1, 328, 328, -1, 328, 328, 328, 328, 328, 328, -1, -1, -1, -1, 328, -1, 328, -1, -1, -1, -1, -1, 328, 328, 328, -1, 328, -1, 328, 328, 328, 328, 328, -1, -1, -1, -1, -1, 328, 328, 328, 328, 328, -1, 328, 328, 328, -1, 328, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 407, -1, -1, -1, -1, -1, -1, -1, 306, -1, -1, -1, 407, -1, -1, 306, -1, 306, -1, -1, -1, -1, -1, 306, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 306, -1, 407, -1, -1, -1, 306, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 306, -1, -1, -1, -1, -1, -1, -1, -1, -1, 306, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 354, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 418, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 177, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 253, -1, -1, -1, -1, -1, -1, -1, -1, -1, 253, -1, -1, 253, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 253, 253, -1, -1, -1, -1, -1, -1, -1, 253, -1, -1, -1, 253, -1, 253, -1, -1, -1, -1, -1, -1, 253, 253, -1, -1, -1, -1, -1, -1, -1, -1, 253, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 253, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 253, -1, -1, 253, -1, -1, -1, -1, -1, -1, -1, -1, 253, -1, -1, -1, -1, 253, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 280, -1, -1, -1, -1, -1, -1, 280, -1, 280, -1, -1, -1, -1, -1, 280, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 280, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 280, -1, -1, -1, -1, -1, -1, -1, -1, -1, 280, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 23, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, 225, -1, -1, 225, -1, -1, 225, -1, -1, -1, 225, 225, -1, -1, -1, -1, -1, 225, -1, 225, -1, -1, -1, 225, -1, -1, 225, 225, -1, -1, 225, -1, -1, -1, 225, -1, -1, -1, 225, -1, 225, -1, 225, -1, -1, 225, -1, 225, -1, 225, -1, -1, 225, 225, -1, -1, -1, -1, -1, 225, -1, -1, -1, -1, -1, 225, -1, 225, -1, -1, -1, 225, -1, -1, 225, -1, -1, -1, -1, -1, -1, 225, 388, 225, 225, -1, -1, -1, -1, -1, 225, -1, -1, -1, -1, 225, -1, -1, -1, 225, -1, 225, 225, -1, 225, 225, 225, -1, 225, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 102, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 372, -1, -1, -1, -1, -1, 369, -1, -1, -1, -1, -1, -1, -1, -1, 100, -1, -1, -1, -1, -1, -1, -1, -1, 119, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 302, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 305, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [233, -1, -1, -1, -1, 233, -1, 233, 233, -1, 233, -1, -1, -1, -1, 233, 233, -1, -1, -1, 233, -1, 233, 233, -1, 233, -1, -1, 233, -1, -1, 233, 233, -1, -1, 233, -1, 233, 233, 233, -1, -1, -1, -1, 233, 233, 233, 233, -1, 233, 233, 233, 233, -1, -1, 233, -1, 233, -1, -1, 233, -1, -1, -1, 233, -1, 227, 233, -1, 233, 233, 233, 233, 233, 233, -1, -1, -1, -1, 233, -1, 233, -1, -1, -1, -1, -1, 233, 233, 233, -1, 233, -1, 233, 233, 233, 233, 233, -1, -1, -1, -1, -1, 233, 233, 233, 233, 233, -1, 233, 233, 233, -1, 233, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 136, -1, 136, -1, -1, -1, -1, -1, 136, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 136, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, 122, -1, -1, 122, -1, -1, -1, -1, -1, -1, 122, 122, -1, -1, -1, -1, -1, 122, -1, -1, -1, -1, -1, 122, -1, -1, 122, 122, -1, -1, 122, -1, -1, -1, 122, -1, -1, -1, -1, -1, 122, -1, 122, -1, -1, -1, -1, -1, -1, -1, -1, -1, 122, -1, -1, -1, -1, -1, -1, 122, -1, -1, -1, -1, -1, 122, -1, 122, -1, -1, -1, -1, -1, -1, 122, -1, -1, -1, -1, -1, -1, -1, 122, 122, 122, -1, -1, -1, -1, -1, 122, -1, -1, -1, -1, 122, -1, -1, -1, 122, -1, 122, 122, -1, 122, -1, 122, -1, 122, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 197, -1, 178, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, 232, -1, -1, 232, -1, -1, -1, -1, -1, -1, 232, 232, -1, -1, -1, -1, -1, 232, -1, -1, -1, -1, -1, 232, -1, -1, 232, 232, -1, -1, 232, -1, -1, -1, 232, -1, -1, -1, -1, -1, 232, -1, 232, -1, -1, -1, -1, -1, -1, -1, -1, -1, 232, -1, -1, -1, -1, -1, -1, 232, -1, -1, -1, -1, -1, 232, -1, 232, -1, -1, -1, -1, -1, -1, 232, -1, -1, -1, -1, -1, -1, -1, 232, 232, 232, -1, -1, -1, -1, -1, 232, -1, -1, -1, -1, 232, -1, -1, -1, 232, -1, 232, 232, -1, 232, -1, 232, -1, 232, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 242, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 237, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 171, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 271, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 173, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 29, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 335, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, 203, 263, 203, -1, -1, -1, 203, -1, 263, -1, -1, 263, -1, -1, 203, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 263, 263, -1, 203, -1, -1, -1, -1, -1, 263, -1, -1, -1, 263, -1, 263, 203, -1, -1, -1, -1, -1, 263, 263, -1, -1, -1, -1, -1, -1, -1, -1, 203, -1, -1, -1, -1, -1, 203, -1, -1, -1, -1, -1, 263, -1, -1, -1, -1, -1, 263, -1, -1, -1, -1, -1, 263, -1, -1, 263, -1, 263, -1, 190, -1, -1, -1, -1, 263, -1, -1, 203, -1, 263, -1, -1, -1, 203, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 35, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 212, -1, -1, -1, -1, -1, -1, 320, -1, -1, 212, -1, -1, 212, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 212, 212, -1, -1, -1, -1, -1, -1, -1, 212, -1, -1, -1, 212, -1, 212, -1, -1, -1, -1, -1, -1, 212, 212, -1, -1, -1, -1, -1, -1, -1, -1, 212, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 212, -1, -1, -1, -1, -1, 212, -1, -1, -1, -1, -1, 212, -1, -1, 212, -1, 320, -1, -1, -1, -1, -1, -1, 212, -1, -1, 320, -1, 212, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 246, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 252, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 332, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 54, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [397, -1, -1, -1, -1, 397, -1, 397, 397, -1, 397, -1, -1, -1, -1, 397, 397, -1, -1, -1, 397, -1, 397, 397, -1, 397, -1, -1, 397, -1, -1, 397, 397, -1, -1, 397, -1, 397, 397, 397, -1, 315, -1, -1, 397, 397, 397, 397, -1, 397, 397, 397, 397, -1, -1, 397, -1, 397, -1, -1, 397, -1, -1, -1, 397, -1, 397, 397, -1, 397, 397, 397, 397, 397, 397, -1, -1, -1, -1, 397, -1, 397, -1, -1, -1, -1, -1, 397, 397, 397, -1, 397, -1, 397, 397, 397, 397, 397, -1, -1, -1, -1, -1, 397, 397, 397, 397, 397, -1, 397, 397, 397, -1, 397, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 196, -1, 196, -1, -1, -1, -1, -1, 196, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 196, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 256, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 381, -1, 381, -1, -1, -1, -1, -1, 381, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 256, -1, -1, -1, -1, -1, -1, -1, -1, -1, 381, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 39, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 259, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 255, -1, 259, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 185, -1, -1, -1, -1, -1, -1, 185, -1, -1, 185, -1, -1, 185, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 185, 185, -1, -1, -1, -1, -1, -1, -1, 185, -1, -1, -1, 185, -1, 185, -1, -1, -1, -1, -1, -1, 185, 185, -1, -1, -1, -1, -1, -1, -1, -1, 185, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 185, -1, -1, -1, -1, -1, 185, -1, -1, -1, -1, -1, 185, -1, -1, 185, -1, 185, -1, -1, -1, -1, -1, -1, 185, -1, -1, 185, -1, 185, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 161, -1, -1, -1, -1, -1, -1, -1, -1, 161, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 380, -1, -1, -1, -1, -1, -1, -1, -1, -1, 380, -1, -1, 380, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 380, -1, 380, 380, -1, -1, -1, -1, -1, -1, -1, 380, 380, -1, -1, 380, -1, 380, -1, -1, 380, -1, -1, -1, -1, 380, -1, -1, -1, -1, -1, -1, -1, -1, 380, 380, -1, 380, -1, -1, -1, -1, -1, -1, -1, -1, 380, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 380, -1, -1, 380, -1, -1, -1, -1, -1, -1, -1, -1, 380, -1, -1, -1, -1, 86, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, 145, -1, -1, 12, -1, -1, -1, -1, -1, -1, -1, 377, -1, -1, -1, -1, -1, 322, -1, -1, -1, -1, -1, -1, -1, -1, 128, 247, -1, -1, -1, -1, -1, -1, 386, -1, -1, -1, -1, -1, 313, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 120, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 169, -1, -1, -1, -1, -1, -1, -1, -1, 126, -1, 37, 166, -1, 182, -1, 297, -1, 356, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 107, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 96, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 150, -1, 96, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, 26, 174, -1, -1, -1, -1, 26, -1, -1, -1, -1, 174, -1, -1, 174, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 174, 174, -1, -1, -1, -1, -1, -1, -1, 174, -1, -1, -1, 174, -1, 174, -1, -1, 174, -1, -1, -1, -1, 174, -1, -1, -1, -1, -1, -1, -1, -1, 174, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 174, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 174, -1, -1, 174, -1, -1, -1, -1, -1, -1, -1, -1, 174, -1, -1, -1, -1, 174, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 342, -1, -1, -1, -1, -1, -1, -1, -1, -1, 342, -1, -1, 342, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 342, 342, -1, -1, -1, -1, -1, -1, -1, 342, -1, -1, -1, 342, -1, 342, -1, -1, 342, -1, -1, -1, -1, 342, -1, -1, -1, -1, -1, -1, -1, -1, 342, 131, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 342, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 342, -1, -1, 342, -1, -1, -1, -1, -1, -1, -1, -1, 342, -1, -1, -1, -1, 342, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 105, -1, -1, -1, -1, -1, -1, -1, -1, -1, 105, -1, -1, 105, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 105, 105, -1, -1, -1, -1, -1, -1, -1, 105, -1, -1, -1, 105, -1, 105, -1, -1, -1, -1, -1, -1, 105, 105, -1, -1, -1, -1, -1, -1, -1, -1, 105, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 105, -1, -1, -1, -1, -1, 172, -1, -1, -1, -1, -1, 105, -1, -1, 105, -1, -1, -1, -1, -1, -1, -1, -1, 105, -1, -1, -1, -1, 105, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 184, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, 229, -1, -1, 229, -1, -1, -1, -1, -1, -1, -1, 229, -1, -1, -1, -1, -1, 229, -1, -1, -1, -1, -1, 229, -1, -1, 229, 229, -1, -1, 229, -1, -1, -1, 229, -1, -1, -1, -1, -1, 229, -1, 229, -1, -1, -1, -1, -1, -1, -1, -1, -1, 229, -1, -1, -1, -1, -1, -1, 229, -1, -1, -1, -1, -1, 229, -1, 229, -1, -1, -1, -1, -1, -1, 229, -1, -1, -1, -1, -1, -1, -1, -1, 229, 229, -1, -1, -1, -1, -1, 229, -1, -1, -1, -1, -1, -1, -1, -1, 229, -1, 229, 229, -1, 229, -1, 229, -1, 229, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, 411, -1, -1, 411, -1, -1, -1, -1, -1, -1, 325, 411, -1, -1, -1, -1, -1, 411, -1, -1, -1, -1, -1, 411, -1, -1, 411, 411, -1, -1, 411, -1, -1, -1, 411, -1, -1, -1, -1, -1, 411, -1, 411, -1, -1, -1, -1, -1, -1, -1, -1, -1, 411, -1, -1, -1, -1, -1, -1, 411, -1, -1, -1, -1, -1, 411, -1, 411, -1, -1, -1, -1, -1, -1, 411, -1, -1, -1, -1, -1, -1, -1, 325, 411, 411, -1, -1, -1, -1, -1, 411, -1, -1, -1, -1, 325, -1, -1, -1, 411, -1, 411, 411, -1, 411, -1, 411, -1, 411, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, 176, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [285, -1, -1, -1, -1, 165, -1, 285, 165, -1, 285, -1, -1, -1, -1, 285, 165, -1, -1, -1, 285, -1, 165, 285, -1, 285, -1, -1, 165, -1, -1, 165, 165, -1, -1, 165, -1, 285, 285, 165, -1, -1, -1, -1, 285, 165, 285, 165, -1, 285, 285, 285, 285, -1, -1, 285, -1, 165, -1, -1, 285, -1, -1, -1, 165, -1, -1, 285, -1, 285, 165, -1, 165, 285, -1, -1, -1, -1, -1, 165, -1, 285, -1, -1, -1, -1, -1, 285, 165, 165, -1, 285, -1, 285, 285, 165, 285, 285, -1, -1, -1, -1, -1, 285, 165, 285, 165, 165, -1, 165, 285, 165, -1, 165, -1, -1],
    [78, -1, -1, -1, -1, 78, -1, 78, 78, -1, 78, -1, -1, -1, -1, 78, 78, -1, -1, -1, 78, -1, 78, 78, -1, 78, -1, -1, 78, -1, -1, 78, 78, -1, -1, 78, -1, 78, 78, 78, -1, -1, -1, -1, 78, 78, 78, 78, -1, 78, 78, 78, 78, -1, -1, 78, -1, 78, -1, -1, 78, -1, -1, -1, 78, -1, -1, 78, -1, 78, 78, 175, 78, 78, -1, -1, -1, -1, -1, 78, -1, 78, -1, -1, -1, -1, -1, 78, 78, 78, -1, 78, -1, 78, 78, 78, 78, 78, -1, -1, -1, -1, -1, 78, 78, 78, 78, 78, -1, 78, 78, 78, -1, 78, -1, -1],
    [408, -1, -1, -1, -1, 408, -1, 408, 408, -1, 408, -1, -1, -1, -1, 408, 408, -1, -1, -1, 408, -1, 408, 408, -1, 408, -1, -1, 408, -1, -1, 408, 408, -1, -1, 408, -1, 408, 408, 408, -1, 408, -1, -1, 408, 408, 408, 408, -1, 408, 408, 408, 408, -1, -1, 408, -1, 408, -1, -1, 408, -1, -1, -1, 408, -1, 408, 408, -1, 408, 408, 408, 408, 408, 408, -1, -1, -1, -1, 408, -1, 408, -1, -1, -1, -1, -1, 408, 408, 408, -1, 408, -1, 408, 408, 408, 408, 408, -1, -1, -1, -1, -1, 408, 408, 408, 408, 408, -1, 408, 408, 408, -1, 408, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 30, -1, -1, -1, -1, -1, -1, 30, -1, 30, -1, -1, -1, -1, -1, 30, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 30, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 30, -1, -1, -1, -1, -1, -1, -1, -1, -1, 30, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 162, -1, -1, -1, -1, -1, -1, 162, -1, 162, -1, -1, -1, -1, -1, 162, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 83, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 83, -1, -1, -1, -1, -1, -1, -1, -1, -1, 162, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 134, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 50, -1, -1, -1, -1, -1, -1, 50, -1, -1, 50, -1, -1, 50, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 50, 50, -1, -1, -1, -1, -1, -1, -1, 50, -1, -1, -1, 50, -1, 50, -1, -1, -1, -1, -1, -1, 50, 50, -1, -1, -1, -1, -1, -1, -1, -1, 50, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 50, -1, -1, -1, -1, -1, 50, -1, -1, -1, -1, -1, 50, -1, -1, 50, -1, 50, -1, -1, -1, -1, -1, -1, 50, -1, -1, 50, -1, 50, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 295, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 343, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 111, -1, -1, -1, -1, -1, -1, -1, -1, -1, 111, -1, -1, 111, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 111, -1, 111, 111, -1, -1, -1, -1, -1, -1, -1, 111, 111, -1, -1, 111, -1, 111, -1, -1, 111, -1, -1, -1, -1, 111, -1, -1, -1, -1, -1, -1, -1, -1, 111, 111, -1, 111, -1, -1, -1, -1, -1, -1, -1, -1, 111, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 111, -1, -1, 111, -1, -1, -1, -1, -1, -1, -1, -1, 111, -1, -1, -1, -1, 111, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 71, -1, 71, -1, -1, -1, -1, -1, 71, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 71, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 91, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 340, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 153, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, 15, -1, -1, -1, -1, -1, 281, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 77, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 346, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 414, -1, -1, -1, -1, -1, -1, 123, -1, 123, -1, -1, -1, -1, -1, 123, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 414, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 414, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 299, -1, -1, -1, 267, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 400, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 292, -1, -1, -1, -1, -1, -1, 292, -1, 292, -1, -1, -1, -1, -1, 292, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 292, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 292, -1, -1, -1, -1, -1, -1, -1, -1, -1, 245, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 19, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 163, -1, -1, -1, -1, 163, -1, -1, -1, -1, 163, -1, -1, 163, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 163, 163, -1, -1, -1, -1, -1, -1, -1, 163, -1, -1, -1, 163, -1, 163, -1, -1, 163, -1, -1, -1, -1, 163, -1, -1, -1, -1, -1, -1, -1, -1, 163, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 163, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 163, -1, -1, 163, -1, -1, -1, -1, -1, -1, -1, -1, 163, -1, -1, -1, -1, 163, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, 326, -1, -1, 326, -1, -1, 326, -1, -1, -1, 326, 326, -1, -1, -1, -1, -1, 326, -1, 326, -1, -1, -1, 326, -1, -1, 326, 326, -1, -1, 326, -1, -1, -1, 326, -1, -1, -1, 326, -1, 326, -1, 326, -1, -1, 326, -1, 326, -1, 326, -1, -1, 326, 326, -1, -1, -1, -1, -1, 326, -1, -1, -1, -1, -1, 326, -1, 326, -1, -1, -1, 326, -1, -1, 326, -1, -1, -1, -1, -1, -1, 326, 109, 326, 326, -1, -1, -1, -1, -1, 326, -1, -1, -1, -1, 326, -1, -1, -1, 326, -1, 326, 326, -1, 326, 326, 326, -1, 326, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 319, -1, -1, -1, -1, -1, -1, -1, 353, -1, -1, -1, 319, -1, -1, 353, -1, 353, -1, -1, -1, -1, -1, 353, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 353, -1, 319, -1, -1, -1, 353, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 353, -1, -1, -1, -1, -1, -1, -1, -1, -1, 353, -1, -1, -1, -1, -1],
    [363, -1, -1, -1, -1, -1, -1, 85, -1, -1, 10, -1, -1, -1, -1, 10, -1, -1, -1, -1, 10, -1, -1, 10, -1, 116, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 10, 10, -1, -1, -1, -1, -1, 5, -1, 10, -1, -1, 116, 10, 5, 10, -1, -1, 10, -1, -1, -1, -1, 10, -1, -1, -1, -1, -1, -1, 116, -1, 10, -1, -1, -1, 85, -1, -1, -1, -1, -1, -1, -1, 10, -1, -1, -1, -1, -1, 113, -1, -1, -1, 363, -1, 10, 5, -1, 10, 363, -1, -1, -1, -1, -1, 116, -1, 10, -1, -1, -1, -1, 10, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, 290, -1, -1, 290, -1, -1, -1, -1, -1, -1, -1, 290, -1, -1, -1, -1, -1, 290, -1, -1, -1, -1, -1, 290, -1, -1, 290, 290, -1, -1, 290, -1, -1, -1, 290, -1, -1, -1, -1, -1, 290, -1, 290, -1, -1, -1, -1, -1, -1, -1, -1, -1, 290, -1, -1, -1, -1, -1, -1, 290, -1, -1, -1, -1, -1, 290, -1, 290, -1, -1, -1, -1, -1, -1, 290, -1, -1, -1, -1, -1, -1, -1, -1, 290, 290, -1, -1, -1, -1, -1, 290, -1, -1, -1, -1, -1, -1, -1, -1, 290, -1, 290, 290, -1, 290, -1, 290, -1, 290, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 345, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, 254, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 36, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 396, -1, -1, -1, -1, -1, -1, -1, -1, 396, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 396, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, 243, -1, -1, 243, -1, -1, 243, -1, -1, -1, -1, 243, -1, -1, -1, -1, -1, 243, -1, -1, -1, -1, -1, -1, -1, -1, 243, 243, -1, -1, 243, -1, -1, -1, 243, -1, -1, -1, -1, -1, 243, -1, 243, -1, -1, 243, -1, 243, -1, -1, -1, -1, 243, 243, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 243, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 243, -1, -1, -1, -1, -1, -1, -1, -1, 243, -1, 243, 243, -1, 243, 243, 243, -1, 243, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 410, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 2, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, 333, -1, -1, 333, -1, -1, -1, -1, -1, -1, -1, 333, -1, -1, -1, -1, -1, 333, -1, -1, -1, -1, -1, 333, -1, -1, 333, 333, -1, -1, 333, -1, -1, -1, 333, -1, -1, -1, -1, -1, 333, -1, 333, -1, -1, -1, -1, -1, -1, -1, -1, -1, 333, -1, -1, -1, -1, -1, -1, 333, -1, -1, -1, -1, -1, 333, -1, 333, -1, -1, -1, -1, -1, -1, 333, -1, -1, -1, -1, -1, -1, -1, -1, 333, 333, -1, -1, -1, -1, -1, 333, -1, -1, -1, -1, -1, -1, -1, -1, 333, -1, 333, 333, -1, 333, -1, 333, -1, 333, -1, -1],
    [-1, -1, -1, -1, -1, 135, -1, -1, 135, -1, 209, -1, -1, -1, -1, 399, 135, -1, -1, -1, 209, -1, 135, 209, -1, -1, -1, -1, 135, -1, -1, 135, 135, -1, -1, 135, -1, 209, 209, 135, -1, -1, -1, -1, -1, 135, 209, 135, -1, -1, 209, -1, 209, -1, -1, 209, -1, 135, -1, -1, 209, -1, -1, -1, 135, -1, -1, -1, -1, 209, 135, -1, 135, -1, -1, -1, -1, -1, -1, 135, -1, 209, -1, -1, -1, -1, -1, -1, 135, 135, -1, -1, -1, 209, -1, 135, 209, -1, -1, -1, -1, -1, -1, -1, 135, 209, 135, 135, -1, 135, 209, 135, -1, 135, -1, -1],
    [-1, -1, -1, -1, -1, -1, 67, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 75, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, 202, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, 352, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 298, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 409, -1, 409, -1, -1, -1, -1, -1, 409, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 409, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 204, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 32, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, 387, -1, -1, 387, -1, -1, -1, -1, -1, -1, -1, 387, -1, -1, -1, -1, -1, 387, -1, -1, -1, -1, -1, -1, -1, -1, 387, 387, -1, -1, 149, -1, -1, -1, 387, -1, -1, -1, -1, -1, 387, -1, 149, -1, -1, -1, -1, -1, -1, -1, -1, -1, 387, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 149, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 387, -1, -1, -1, -1, -1, -1, -1, -1, 387, -1, 387, 387, -1, 387, -1, 387, -1, 387, -1, -1],
    [-1, -1, -1, -1, -1, 167, -1, -1, 167, -1, -1, -1, -1, -1, -1, -1, 167, -1, -1, -1, -1, -1, 167, -1, -1, -1, -1, -1, 167, -1, -1, 167, 167, -1, -1, 167, -1, -1, -1, 167, -1, -1, -1, -1, -1, 167, -1, 167, -1, -1, -1, -1, -1, -1, -1, -1, -1, 167, -1, -1, -1, -1, -1, -1, 167, -1, -1, -1, -1, -1, 167, -1, 167, -1, -1, -1, -1, -1, -1, 167, -1, -1, -1, -1, -1, -1, -1, -1, 167, 167, -1, -1, -1, -1, -1, 167, -1, -1, -1, -1, -1, -1, -1, -1, 167, -1, 167, 167, -1, 167, -1, 167, -1, 167, -1, -1],
    [-1, -1, -1, -1, -1, 357, -1, -1, 357, -1, -1, 393, -1, -1, -1, -1, 357, -1, -1, -1, -1, -1, 357, -1, -1, -1, -1, -1, -1, -1, -1, 357, 357, -1, -1, 357, -1, -1, -1, 357, -1, -1, -1, -1, -1, 357, -1, 357, -1, -1, 393, -1, 393, -1, -1, -1, -1, 357, 393, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 357, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 357, -1, -1, -1, -1, -1, -1, -1, -1, 357, -1, 357, 357, -1, 357, 393, 357, -1, 357, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, 260, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 64, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 127, -1, -1, -1, -1, -1, -1, -1, -1, -1, 127, -1, -1, 127, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 127, -1, 127, 127, -1, -1, -1, -1, -1, -1, -1, 127, 127, -1, -1, 127, -1, 127, -1, -1, 127, -1, -1, -1, -1, 127, -1, -1, -1, -1, -1, -1, -1, -1, 127, 127, -1, 127, -1, -1, -1, -1, -1, -1, -1, -1, 127, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 127, -1, -1, 127, -1, -1, -1, -1, -1, -1, -1, -1, 127, -1, -1, -1, -1, 127, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 270, -1, -1, -1, -1, -1, -1, -1, -1, -1, 270, -1, -1, 270, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 270, 270, -1, -1, -1, -1, -1, -1, -1, 270, -1, -1, -1, 270, -1, 270, -1, -1, 270, -1, -1, -1, -1, 270, -1, -1, -1, -1, -1, -1, -1, -1, 270, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 270, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 270, -1, -1, 270, -1, -1, -1, -1, -1, -1, -1, -1, 270, -1, -1, -1, -1, 270, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 286, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, 376, -1, -1, 376, -1, -1, -1, -1, -1, -1, 379, 376, -1, -1, -1, -1, -1, 376, -1, 379, -1, -1, -1, 376, -1, -1, 376, 376, -1, -1, 376, -1, -1, -1, 376, -1, -1, -1, 379, -1, 376, -1, 376, -1, -1, 379, -1, 379, -1, 379, -1, -1, 376, 379, -1, -1, -1, -1, -1, 376, -1, -1, -1, -1, -1, 376, -1, 376, -1, -1, -1, 379, -1, -1, 376, -1, -1, -1, -1, -1, -1, 379, -1, 376, 376, -1, -1, -1, -1, -1, 376, -1, -1, -1, -1, 379, -1, -1, -1, 376, -1, 376, 376, -1, 376, 379, 376, -1, 376, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 331, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 201, -1, 201, -1, -1, -1, -1, -1, 201, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 201, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 367, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 367, -1, 367, -1, -1, -1, -1, -1, 367, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 367, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, 337, -1, -1, 337, -1, -1, 337, -1, -1, -1, -1, 337, -1, -1, -1, -1, -1, 337, -1, -1, -1, -1, -1, -1, -1, -1, 337, 337, -1, -1, 337, -1, -1, -1, 337, -1, -1, -1, -1, -1, 337, -1, 337, -1, -1, 337, -1, 337, -1, -1, -1, -1, 337, 337, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 389, 337, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 337, -1, -1, -1, -1, -1, -1, -1, -1, 337, -1, 337, 337, -1, 337, 337, 337, -1, 337, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 373, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 14, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, 94, -1, -1, 94, -1, -1, -1, -1, -1, -1, -1, 94, -1, -1, -1, -1, -1, 94, -1, -1, -1, -1, -1, 139, -1, -1, 94, 94, -1, -1, 348, -1, -1, -1, 94, -1, -1, -1, -1, -1, 94, -1, 348, -1, -1, -1, -1, -1, -1, -1, -1, -1, 94, -1, -1, -1, -1, -1, -1, 139, -1, -1, -1, -1, -1, 139, -1, 348, -1, -1, -1, -1, -1, -1, 139, -1, -1, -1, -1, -1, -1, -1, -1, 139, 278, -1, -1, -1, -1, -1, 94, -1, -1, -1, -1, -1, -1, -1, -1, 94, -1, 94, 94, -1, 94, -1, 94, -1, 94, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 51, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 51, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 251, -1, 51, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 66, -1, -1, -1, -1, -1, -1, -1, -1, -1, 66, -1, -1, 66, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 370, -1, 66, 66, -1, -1, -1, -1, -1, -1, -1, 66, 370, -1, -1, 66, -1, 66, -1, -1, 66, -1, -1, -1, -1, 66, -1, -1, -1, -1, -1, -1, -1, -1, 66, 370, -1, 370, -1, -1, -1, -1, -1, -1, -1, -1, 66, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 66, -1, -1, 66, -1, -1, -1, -1, -1, -1, -1, -1, 66, -1, -1, -1, -1, 66, -1, -1, -1, -1, -1],
    [144, -1, -1, -1, -1, 144, -1, 144, 144, -1, 144, -1, -1, -1, -1, 144, 144, -1, -1, -1, 144, -1, 144, 144, -1, 144, -1, -1, 144, -1, -1, 144, 144, -1, -1, 144, -1, 144, 144, 144, -1, -1, -1, -1, 144, 144, 144, 144, -1, 144, 144, 144, 144, -1, -1, 144, -1, 144, -1, -1, 144, -1, -1, -1, 144, -1, -1, 144, -1, 144, 144, 144, 144, 144, -1, -1, -1, -1, -1, 144, -1, 144, -1, -1, -1, -1, -1, 144, 144, 144, -1, 144, -1, 144, 144, 144, 144, 144, -1, -1, -1, -1, -1, 144, 144, 144, 144, 144, -1, 144, 144, 144, -1, 144, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 223, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 74, -1, -1, -1, -1, -1, -1, -1, -1, -1, 223, -1, -1, -1, -1, -1, -1, -1],
    [60, -1, -1, -1, -1, 60, -1, 60, 60, -1, 60, -1, -1, -1, -1, 60, 60, -1, -1, -1, 60, -1, 60, 60, -1, 60, -1, -1, 60, -1, -1, 60, 60, -1, -1, 60, -1, 60, 60, 60, -1, -1, -1, -1, 60, 60, 60, 60, -1, 60, 60, 60, 60, -1, -1, 60, -1, 60, -1, -1, 60, -1, -1, -1, 60, -1, -1, 60, -1, 60, 60, 3, 60, 60, -1, -1, -1, -1, -1, 60, -1, 60, -1, -1, -1, -1, -1, 60, 60, 60, -1, 60, -1, 60, 60, 60, 60, 60, -1, -1, -1, -1, -1, 60, 60, 60, 60, 60, -1, 60, 60, 60, -1, 60, -1, -1],
    [-1, -1, -1, -1, -1, 218, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 222, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 312, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 147, -1, -1, -1, -1, -1, -1, -1, -1, 307, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 147, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 147, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 205, -1, -1, -1, -1, -1, -1, 205, -1, 205, -1, -1, -1, -1, -1, 205, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 205, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 205, -1, -1, -1, -1, -1, -1, -1, -1, -1, 205, -1, -1, -1, -1, -1],
    [318, -1, -1, -1, -1, 157, -1, 296, 199, -1, -1, -1, -1, -1, -1, -1, 76, -1, -1, -1, -1, -1, 419, -1, -1, 266, -1, -1, 198, -1, -1, 269, 44, -1, -1, 216, -1, -1, -1, 274, -1, -1, -1, -1, -1, 82, 287, 338, -1, 95, -1, 22, -1, -1, -1, -1, -1, 89, -1, -1, -1, -1, -1, -1, 47, -1, 374, 268, -1, -1, 402, -1, 339, 33, -1, -1, -1, -1, -1, 154, -1, -1, -1, -1, -1, -1, -1, -1, 125, 403, -1, 170, -1, -1, 155, 97, -1, 90, -1, -1, -1, -1, -1, 375, -1, -1, 70, 262, -1, 73, -1, 106, -1, 341, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 382, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 13, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [69, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 92, -1, -1, -1, -1, -1, 148, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 208, -1, 208, -1, -1, -1, -1, -1, 208, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 208, -1, -1, -1, -1, -1],
    [334, 384, 384, 384, -1, 334, -1, 334, 334, 384, -1, 384, -1, -1, 384, 384, 334, 384, 384, 384, 368, 384, 334, 384, -1, 334, 384, -1, 334, -1, 384, 334, 334, 384, 384, 334, 384, 368, 368, 334, 384, -1, 384, -1, -1, 334, 334, 334, 384, 334, 231, 334, 384, 384, -1, -1, -1, 334, -1, -1, -1, 384, 384, 384, 334, 384, 334, 334, 384, 384, 334, 384, 334, 334, -1, -1, -1, 384, 384, 334, 384, 368, 384, 384, 384, 384, -1, 384, 334, 334, 384, 334, 384, 368, 334, 334, 368, 334, 384, -1, 384, 384, 384, 334, -1, 378, 334, 334, 384, 334, -1, 334, 347, 334, 384, 384],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 68, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 261, 25, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 80, -1, -1, 112, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 103, -1, -1, -1, 415, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 415, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 158, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 224, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 224, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 8, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 422, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 272, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 294, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 17, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 200, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, 355, -1, -1, 355, -1, -1, -1, -1, -1, -1, -1, 355, -1, -1, -1, -1, -1, 355, -1, -1, -1, -1, -1, 355, -1, -1, 355, 355, -1, -1, 355, -1, -1, -1, 355, -1, -1, -1, -1, -1, 355, -1, 355, -1, -1, 193, -1, -1, -1, -1, -1, -1, 355, -1, -1, -1, -1, -1, -1, 355, -1, -1, -1, -1, -1, 355, -1, 355, -1, -1, -1, -1, -1, -1, 355, -1, -1, -1, -1, -1, -1, -1, -1, 355, 355, -1, -1, -1, -1, -1, 355, -1, -1, -1, -1, -1, -1, -1, -1, 355, -1, 355, 355, -1, 355, -1, 355, -1, 355, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 21, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, 423, 159, 137, -1, -1, -1, -1, -1, 314, -1, 250, -1, -1, 59, 87, -1, 160, 56, 283, -1, 88, -1, 65, -1, -1, 79, -1, -1, -1, 420, -1, -1, 181, 249, -1, 265, -1, -1, -1, 291, -1, 416, -1, -1, -1, -1, -1, 189, -1, -1, -1, 219, 40, -1, -1, -1, -1, -1, -1, -1, 115, 52, 236, -1, 392, -1, -1, 180, 390, -1, 241, -1, -1, -1, -1, -1, 206, 404, -1, 394, -1, 324, 401, 179, 114, -1, 329, -1, -1, 62, -1, 168, -1, -1, -1, -1, -1, 350, -1, 72, 192, 0, -1, -1, -1, -1, -1, 288, -1, -1, -1, -1, -1, 360, 141],
    [-1, -1, -1, -1, -1, 301, -1, -1, 301, -1, -1, -1, -1, -1, -1, -1, 301, -1, -1, -1, -1, -1, 301, -1, -1, -1, -1, -1, 301, -1, -1, 301, 301, -1, -1, 301, -1, -1, -1, 301, -1, -1, -1, -1, -1, 301, -1, 301, -1, -1, -1, -1, -1, -1, -1, -1, -1, 301, -1, -1, -1, -1, -1, -1, 301, -1, -1, -1, -1, -1, 301, -1, 301, -1, -1, -1, -1, -1, -1, 301, -1, -1, -1, -1, -1, -1, -1, -1, 301, 301, -1, -1, -1, -1, -1, 301, -1, -1, -1, -1, -1, -1, -1, -1, 301, -1, 301, 301, -1, 301, -1, 301, -1, 301, -1, -1],
  ]
  TERMINAL_WHILE = 0
  TERMINAL_BITANDEQ = 1
  TERMINAL_GT = 2
  TERMINAL_BITOREQ = 3
  TERMINAL_UNIVERSAL_CHARACTER_NAME = 4
  TERMINAL_INT = 5
  TERMINAL_EXTERNAL_DECLARATION_HINT = 6
  TERMINAL_IF = 7
  TERMINAL_ENUM = 8
  TERMINAL_RPAREN = 9
  TERMINAL_BITAND = 10
  TERMINAL_COLON = 11
  TERMINAL_NOT = 12
  TERMINAL_BITNOT = 13
  TERMINAL_LTEQ = 14
  TERMINAL_SEMI = 15
  TERMINAL_FLOAT = 16
  TERMINAL_LSQUARE = 17
  TERMINAL_LSHIFTEQ = 18
  TERMINAL_RSHIFT = 19
  TERMINAL_FLOATING_CONSTANT = 20
  TERMINAL_NEQ = 21
  TERMINAL_DOUBLE = 22
  TERMINAL_INCR = 23
  TERMINAL_FUNCTION_DEFINITION_HINT = 24
  TERMINAL_RETURN = 25
  TERMINAL_EXCLAMATION_POINT = 26
  TERMINAL_DIVEQ = 27
  TERMINAL_TYPEDEF = 28
  TERMINAL_SIZEOF_SEPARATOR = 29
  TERMINAL_POUNDPOUND = 30
  TERMINAL_SIGNED = 31
  TERMINAL_IMAGINARY = 32
  TERMINAL_POUND = 33
  TERMINAL_SUBEQ = 34
  TERMINAL_RESTRICT = 35
  TERMINAL_TILDE = 36
  TERMINAL_INTEGER_CONSTANT = 37
  TERMINAL_CHARACTER_CONSTANT = 38
  TERMINAL_UNSIGNED = 39
  TERMINAL_RSQUARE = 40
  TERMINAL_ELSE_IF = 41
  TERMINAL_SUB = 42
  TERMINAL__DIRECT_ABSTRACT_DECLARATOR = 43
  TERMINAL_LABEL_HINT = 44
  TERMINAL_BOOL = 45
  TERMINAL_SIZEOF = 46
  TERMINAL_CONST = 47
  TERMINAL_ADD = 48
  TERMINAL_BREAK = 49
  TERMINAL_IDENTIFIER = 50
  TERMINAL_CASE = 51
  TERMINAL_LPAREN = 52
  TERMINAL_QUESTIONMARK = 53
  TERMINAL_DECLARATOR_HINT = 54
  TERMINAL__EXPR = 55
  TERMINAL_DEFINED = 56
  TERMINAL_CHAR = 57
  TERMINAL__DIRECT_DECLARATOR = 58
  TERMINAL__EXPR_SANS_COMMA = 59
  TERMINAL_LPAREN_CAST = 60
  TERMINAL_AMPERSAND = 61
  TERMINAL_MODEQ = 62
  TERMINAL_EQ = 63
  TERMINAL_EXTERN = 64
  TERMINAL_ADDEQ = 65
  TERMINAL_ELSE = 66
  TERMINAL_GOTO = 67
  TERMINAL_GTEQ = 68
  TERMINAL_DECR = 69
  TERMINAL_STATIC = 70
  TERMINAL_RBRACE = 71
  TERMINAL_VOLATILE = 72
  TERMINAL_SWITCH = 73
  TERMINAL_ENDIF = 74
  TERMINAL_TRAILING_COMMA = 75
  TERMINAL_COMMA_VA_ARGS = 76
  TERMINAL_MOD = 77
  TERMINAL_ELIPSIS = 78
  TERMINAL_AUTO = 79
  TERMINAL_LT = 80
  TERMINAL_ENUMERATION_CONSTANT = 81
  TERMINAL_MULEQ = 82
  TERMINAL_DIV = 83
  TERMINAL_BITXOREQ = 84
  TERMINAL_OR = 85
  TERMINAL_FUNCTION_PROTOTYPE_HINT = 86
  TERMINAL_LBRACE = 87
  TERMINAL_REGISTER = 88
  TERMINAL_INLINE = 89
  TERMINAL_RSHIFTEQ = 90
  TERMINAL_DO = 91
  TERMINAL_LSHIFT = 92
  TERMINAL_HEXADECIMAL_FLOATING_CONSTANT = 93
  TERMINAL_DEFAULT = 94
  TERMINAL_VOID = 95
  TERMINAL_DECIMAL_FLOATING_CONSTANT = 96
  TERMINAL_FOR = 97
  TERMINAL_ASSIGN = 98
  TERMINAL_DEFINED_SEPARATOR = 99
  TERMINAL_COMMA = 100
  TERMINAL_BITXOR = 101
  TERMINAL_BITOR = 102
  TERMINAL_CONTINUE = 103
  TERMINAL_TYPEDEF_IDENTIFIER = 104
  TERMINAL_STRING_LITERAL = 105
  TERMINAL_STRUCT = 106
  TERMINAL_LONG = 107
  TERMINAL_DOT = 108
  TERMINAL_UNION = 109
  TERMINAL_ASTERISK = 110
  TERMINAL_COMPLEX = 111
  TERMINAL_PP_NUMBER = 112
  TERMINAL_SHORT = 113
  TERMINAL_ARROW = 114
  TERMINAL_AND = 115
  def __init__(self, tokens=None):
    self.__dict__.update(locals())
    self.expressionParsers = dict()
  def isTerminal(self, id):
    return 0 <= id <= 115
  def isNonTerminal(self, id):
    return 116 <= id <= 243
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
  def parse__gen27(self):
    current = self.tokens.current()
    rule = self.table[0][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(116, self.nonterminals[116]))
    tree.list = 'slist'
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 4:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_parameter_declaration()
      tree.add( subtree )
      subtree = self.parse__gen28()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen28(self):
    current = self.tokens.current()
    rule = self.table[1][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(117, self.nonterminals[117]))
    tree.list = 'slist'
    if current != None and (current.getId() in [76]):
      return tree
    if current == None:
      return tree
    if rule == 7:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(100) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self.parse_parameter_declaration()
      tree.add( subtree )
      subtree = self.parse__gen28()
      tree.add( subtree )
      return tree
    return tree
  def parse_designation(self):
    current = self.tokens.current()
    rule = self.table[2][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(118, self.nonterminals[118]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 362:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen15()
      tree.add( subtree )
      t = self.expect(98) # assign
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_labeled_statement(self):
    current = self.tokens.current()
    rule = self.table[3][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(119, self.nonterminals[119]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 55:
      tree.astTransform = AstTransformNodeCreator('DefaultCase', {'statement': 2})
      t = self.expect(94) # default
      tree.add(t)
      t = self.expect(11) # colon
      tree.add(t)
      subtree = self.parse_statement()
      tree.add( subtree )
      return tree
    elif rule == 142:
      tree.astTransform = AstTransformNodeCreator('Label', {'name': 0, 'statement': 1})
      t = self.expect(44) # label_hint
      tree.add(t)
      t = self.expect(50) # identifier
      tree.add(t)
      t = self.expect(11) # colon
      tree.add(t)
      subtree = self.parse_statement()
      tree.add( subtree )
      return tree
    elif rule == 364:
      tree.astTransform = AstTransformNodeCreator('Case', {'expr': 1, 'statement': 3})
      t = self.expect(51) # case
      tree.add(t)
      subtree = self.parse__expr()
      tree.add( subtree )
      t = self.expect(11) # colon
      tree.add(t)
      subtree = self.parse_statement()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen33(self):
    current = self.tokens.current()
    rule = self.table[4][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(120, self.nonterminals[120]))
    tree.list = False
    if current != None and (current.getId() in [100, 76]):
      return tree
    if current == None:
      return tree
    if rule == 211:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__direct_abstract_declarator()
      tree.add( subtree )
      return tree
    elif current.getId() in [43, 52]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__direct_abstract_declarator()
      tree.add( subtree )
    return tree
  def parse_enum_specifier_sub(self):
    current = self.tokens.current()
    rule = self.table[5][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(121, self.nonterminals[121]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 6:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_identifier()
      tree.add( subtree )
      subtree = self.parse__gen22()
      tree.add( subtree )
      return tree
    elif rule == 124:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_enum_specifier_body()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_external_declarator(self):
    current = self.tokens.current()
    rule = self.table[6][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(122, self.nonterminals[122]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 34:
      tree.astTransform = AstTransformNodeCreator('ExternalDeclarator', {'init_declarator': 1})
      t = self.expect(54) # declarator_hint
      tree.add(t)
      subtree = self.parse__gen6()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen37(self):
    current = self.tokens.current()
    rule = self.table[7][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(123, self.nonterminals[123]))
    tree.list = False
    if current != None and (current.getId() in [72, 5, 7, 8, 74, 96, 16, 94, 20, 22, 105, 67, 81, 10, 31, 103, 37, 38, 39, 50, 44, 45, 46, 49, 25, 111, 52, 55, 28, 32, 60, 64, 66, 69, 70, 73, 107, 93, 23, 88, 79, 0, 87, 89, 91, 15, 71, 95, 97, 106, 47, 104, 57, 51, 109, 110, 35, 113]):
      return tree
    if current == None:
      return tree
    if rule == 328:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_else_if_statement_list()
      tree.add( subtree )
      return tree
    return tree
  def parse_type_qualifier_list_opt(self):
    current = self.tokens.current()
    rule = self.table[8][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(124, self.nonterminals[124]))
    tree.list = False
    if current != None and (current.getId() in [100, 70, 58, 43, 76, 110, 50, 52]):
      return tree
    if current == None:
      return tree
    if rule == 407:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen25()
      tree.add( subtree )
      return tree
    return tree
  def parse_type_qualifier(self):
    current = self.tokens.current()
    rule = self.table[9][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(125, self.nonterminals[125]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 177:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(72) # volatile
      tree.add(t)
      return tree
    elif rule == 354:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(35) # restrict
      tree.add(t)
      return tree
    elif rule == 418:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(47) # const
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen40(self):
    current = self.tokens.current()
    rule = self.table[10][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(126, self.nonterminals[126]))
    tree.list = 'slist'
    if current != None and (current.getId() in []):
      return tree
    if current == None:
      return tree
    if rule == 253:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__expr_sans_comma()
      tree.add( subtree )
      subtree = self.parse__gen41()
      tree.add( subtree )
      return tree
    return tree
  def parse_pointer_opt(self):
    current = self.tokens.current()
    rule = self.table[11][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(127, self.nonterminals[127]))
    tree.list = False
    if current != None and (current.getId() in [100, 76, 43, 50, 58, 52]):
      return tree
    if current == None:
      return tree
    if rule == 280:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_pointer()
      tree.add( subtree )
      return tree
    return tree
  def parse_enum_specifier_body(self):
    current = self.tokens.current()
    rule = self.table[12][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(128, self.nonterminals[128]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 23:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(87) # lbrace
      tree.add(t)
      subtree = self.parse__gen23()
      tree.add( subtree )
      subtree = self.parse_trailing_comma_opt()
      tree.add( subtree )
      t = self.expect(71) # rbrace
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen22(self):
    current = self.tokens.current()
    rule = self.table[13][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(129, self.nonterminals[129]))
    tree.list = False
    if current != None and (current.getId() in [11, 72, 58, 31, 32, 43, 8, 64, 107, 86, 70, 16, 76, 28, 79, 22, 35, 24, 106, 88, 89, 5, 104, 15, 113, 95, 39, 100, 47, 57, 45, 109, 54, 110, 50, 111, 52]):
      return tree
    if current == None:
      return tree
    if rule == 388:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_enum_specifier_body()
      tree.add( subtree )
      return tree
    return tree
  def parse_storage_class_specifier(self):
    current = self.tokens.current()
    rule = self.table[14][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(130, self.nonterminals[130]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 100:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(79) # auto
      tree.add(t)
      return tree
    elif rule == 102:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(28) # typedef
      tree.add(t)
      return tree
    elif rule == 119:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(88) # register
      tree.add(t)
      return tree
    elif rule == 369:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(70) # static
      tree.add(t)
      return tree
    elif rule == 372:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(64) # extern
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen41(self):
    current = self.tokens.current()
    rule = self.table[15][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(131, self.nonterminals[131]))
    tree.list = 'slist'
    if current != None and (current.getId() in []):
      return tree
    if current == None:
      return tree
    if rule == 302:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(100) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self.parse__expr_sans_comma()
      tree.add( subtree )
      subtree = self.parse__gen41()
      tree.add( subtree )
      return tree
    return tree
  def parse_else_statement(self):
    current = self.tokens.current()
    rule = self.table[16][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(132, self.nonterminals[132]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 305:
      tree.astTransform = AstTransformNodeCreator('Else', {'statement': 1})
      t = self.expect(66) # else
      tree.add(t)
      subtree = self.parse_statement()
      tree.add( subtree )
      t = self.expect(74) # endif
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen38(self):
    current = self.tokens.current()
    rule = self.table[17][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(133, self.nonterminals[133]))
    tree.list = False
    if current != None and (current.getId() in [72, 5, 7, 8, 74, 96, 16, 94, 20, 22, 105, 67, 81, 10, 31, 103, 37, 38, 39, 50, 44, 45, 46, 49, 25, 111, 52, 55, 28, 32, 60, 64, 69, 70, 73, 107, 93, 23, 88, 79, 0, 87, 89, 91, 15, 71, 95, 97, 106, 47, 104, 57, 51, 109, 110, 35, 113]):
      return tree
    if current == None:
      return tree
    if rule == 227:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_else_statement()
      tree.add( subtree )
      return tree
    return tree
  def parse_declarator(self):
    current = self.tokens.current()
    rule = self.table[18][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(134, self.nonterminals[134]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 136:
      tree.astTransform = AstTransformNodeCreator('Declarator', {'direct_declarator': 1, 'pointer': 0})
      subtree = self.parse_pointer_opt()
      tree.add( subtree )
      subtree = self.parse__direct_declarator()
      tree.add( subtree )
      return tree
    elif current.getId() in [50, 58, 52]:
      tree.astTransform = AstTransformNodeCreator('Declarator', {'direct_declarator': 1, 'pointer': 0})
      subtree = self.parse_pointer_opt()
      tree.add( subtree )
      subtree = self.parse__direct_declarator()
      tree.add( subtree )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_declaration_list(self):
    current = self.tokens.current()
    rule = self.table[19][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(135, self.nonterminals[135]))
    tree.list = False
    if current == None:
      return tree
    if rule == 122:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen7()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_sizeof_body(self):
    current = self.tokens.current()
    rule = self.table[20][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(136, self.nonterminals[136]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 178:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(52) # lparen
      tree.add(t)
      subtree = self.parse_type_name()
      tree.add( subtree )
      t = self.expect(9) # rparen
      tree.add(t)
      return tree
    elif rule == 197:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(50) # identifier
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen5(self):
    current = self.tokens.current()
    rule = self.table[21][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(137, self.nonterminals[137]))
    tree.list = False
    if current != None and (current.getId() in [87, 15, 100]):
      return tree
    if current == None:
      return tree
    if rule == 232:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_declaration_list()
      tree.add( subtree )
      return tree
    return tree
  def parse__gen10(self):
    current = self.tokens.current()
    rule = self.table[22][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(138, self.nonterminals[138]))
    tree.list = 'slist'
    if current != None and (current.getId() in [15]):
      return tree
    if current == None:
      return tree
    if rule == 237:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(100) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self.parse_init_declarator()
      tree.add( subtree )
      subtree = self.parse__gen10()
      tree.add( subtree )
      return tree
    return tree
  def parse_jump_statement(self):
    current = self.tokens.current()
    rule = self.table[23][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(139, self.nonterminals[139]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 29:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(103) # continue
      tree.add(t)
      return tree
    elif rule == 171:
      tree.astTransform = AstTransformNodeCreator('Return', {'expr': 1})
      t = self.expect(25) # return
      tree.add(t)
      subtree = self.parse_expression_opt()
      tree.add( subtree )
      t = self.expect(15) # semi
      tree.add(t)
      return tree
    elif rule == 173:
      tree.astTransform = AstTransformNodeCreator('Goto', {'name': 1})
      t = self.expect(67) # goto
      tree.add(t)
      t = self.expect(50) # identifier
      tree.add(t)
      t = self.expect(15) # semi
      tree.add(t)
      return tree
    elif rule == 271:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(49) # break
      tree.add(t)
      t = self.expect(15) # semi
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_else_if_statement(self):
    current = self.tokens.current()
    rule = self.table[24][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(140, self.nonterminals[140]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 335:
      tree.astTransform = AstTransformNodeCreator('ElseIf', {'statement': 4, 'condition': 2})
      t = self.expect(41) # else_if
      tree.add(t)
      t = self.expect(52) # lparen
      tree.add(t)
      subtree = self.parse__expr()
      tree.add( subtree )
      t = self.expect(9) # rparen
      tree.add(t)
      subtree = self.parse_statement()
      tree.add( subtree )
      t = self.expect(74) # endif
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_pointer_sub(self):
    current = self.tokens.current()
    rule = self.table[26][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(142, self.nonterminals[142]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 35:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(110) # asterisk
      tree.add(t)
      subtree = self.parse_type_qualifier_list_opt()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen14(self):
    current = self.tokens.current()
    rule = self.table[27][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(143, self.nonterminals[143]))
    tree.list = False
    if current != None and (current.getId() in [87, 59, 60, 52, 37, 38, 10, 69, 105, 93, 23, 110, 50, 20, 46, 81, 96]):
      return tree
    if current == None:
      return tree
    if rule == 320:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_designation()
      tree.add( subtree )
      return tree
    return tree
  def parse__gen23(self):
    current = self.tokens.current()
    rule = self.table[28][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(144, self.nonterminals[144]))
    tree.list = 'slist'
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 246:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_enumerator()
      tree.add( subtree )
      subtree = self.parse__gen24()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen24(self):
    current = self.tokens.current()
    rule = self.table[29][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(145, self.nonterminals[145]))
    tree.list = 'slist'
    if current != None and (current.getId() in [75]):
      return tree
    if current == None:
      return tree
    if rule == 332:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(100) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self.parse_enumerator()
      tree.add( subtree )
      subtree = self.parse__gen24()
      tree.add( subtree )
      return tree
    return tree
  def parse_enumerator(self):
    current = self.tokens.current()
    rule = self.table[30][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(146, self.nonterminals[146]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 54:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_enumeration_constant()
      tree.add( subtree )
      subtree = self.parse_enumerator_assignment()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen39(self):
    current = self.tokens.current()
    rule = self.table[31][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(147, self.nonterminals[147]))
    tree.list = 'nlist'
    if current != None and (current.getId() in [72, 5, 7, 8, 74, 96, 16, 94, 20, 22, 105, 67, 81, 10, 89, 103, 37, 38, 39, 50, 49, 45, 46, 44, 25, 111, 52, 55, 28, 32, 60, 64, 66, 69, 70, 73, 107, 93, 23, 88, 79, 0, 87, 31, 91, 15, 71, 95, 97, 106, 47, 104, 57, 51, 109, 110, 35, 113]):
      return tree
    if current == None:
      return tree
    if rule == 315:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_else_if_statement()
      tree.add( subtree )
      subtree = self.parse__gen39()
      tree.add( subtree )
      return tree
    return tree
  def parse_init_declarator(self):
    current = self.tokens.current()
    rule = self.table[32][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(148, self.nonterminals[148]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 196:
      tree.astTransform = AstTransformNodeCreator('InitDeclarator', {'initializer': 1, 'declarator': 0})
      subtree = self.parse_declarator()
      tree.add( subtree )
      subtree = self.parse__gen11()
      tree.add( subtree )
      return tree
    elif current.getId() in [50, 58, 52]:
      tree.astTransform = AstTransformNodeCreator('InitDeclarator', {'initializer': 1, 'declarator': 0})
      subtree = self.parse_declarator()
      tree.add( subtree )
      subtree = self.parse__gen11()
      tree.add( subtree )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen6(self):
    current = self.tokens.current()
    rule = self.table[33][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(149, self.nonterminals[149]))
    tree.list = False
    if current != None and (current.getId() in [100, 15]):
      return tree
    if current == None:
      return tree
    if rule == 381:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_init_declarator()
      tree.add( subtree )
      return tree
    elif current.getId() in [50, 58, 52]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_init_declarator()
      tree.add( subtree )
    return tree
  def parse__gen30(self):
    current = self.tokens.current()
    rule = self.table[34][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(150, self.nonterminals[150]))
    tree.list = 'slist'
    if current != None and (current.getId() in []):
      return tree
    if current == None:
      return tree
    if rule == 39:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_identifier()
      tree.add( subtree )
      subtree = self.parse__gen31()
      tree.add( subtree )
      return tree
    return tree
  def parse__gen11(self):
    current = self.tokens.current()
    rule = self.table[35][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(151, self.nonterminals[151]))
    tree.list = False
    if current != None and (current.getId() in [100, 15]):
      return tree
    if current == None:
      return tree
    if rule == 255:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_declarator_initializer()
      tree.add( subtree )
      return tree
    return tree
  def parse_initializer_list_item(self):
    current = self.tokens.current()
    rule = self.table[36][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(152, self.nonterminals[152]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 185:
      tree.astTransform = AstTransformNodeCreator('Initialization', {'designation': 0, 'initializer': 1})
      subtree = self.parse__gen14()
      tree.add( subtree )
      subtree = self.parse_initializer()
      tree.add( subtree )
      return tree
    elif rule == 217:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(37) # integer_constant
      tree.add(t)
      return tree
    elif current.getId() in [59, 60, 52, 37, 38, 10, 69, 105, 93, 23, 110, 50, 20, 46, 81, 96]:
      tree.astTransform = AstTransformNodeCreator('Initialization', {'designation': 0, 'initializer': 1})
      subtree = self.parse__gen14()
      tree.add( subtree )
      subtree = self.parse_initializer()
      tree.add( subtree )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_direct_abstract_declarator_opt(self):
    current = self.tokens.current()
    rule = self.table[37][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(153, self.nonterminals[153]))
    tree.list = False
    if current != None and (current.getId() in []):
      return tree
    if current == None:
      return tree
    if rule == 161:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__direct_abstract_declarator()
      tree.add( subtree )
      return tree
    elif current.getId() in [43, 52]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__direct_abstract_declarator()
      tree.add( subtree )
    return tree
  def parse_direct_abstract_declarator_expr(self):
    current = self.tokens.current()
    rule = self.table[38][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(154, self.nonterminals[154]))
    tree.list = False
    if current != None and (current.getId() in []):
      return tree
    if current == None:
      return tree
    if rule == 86:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(110) # asterisk
      tree.add(t)
      return tree
    elif rule == 380:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_type_qualifier_list_opt()
      tree.add( subtree )
      subtree = self.parse_static_opt()
      tree.add( subtree )
      subtree = self.parse__expr()
      tree.add( subtree )
      return tree
    elif current.getId() in [55, 81, 60, 52, 37, 38, 10, 69, 105, 93, 23, 110, 50, 20, 46, 96]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_type_qualifier_list_opt()
      tree.add( subtree )
      subtree = self.parse_static_opt()
      tree.add( subtree )
      subtree = self.parse__expr()
      tree.add( subtree )
    return tree
  def parse_type_specifier(self):
    current = self.tokens.current()
    rule = self.table[39][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(155, self.nonterminals[155]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 12:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_enum_specifier()
      tree.add( subtree )
      return tree
    elif rule == 37:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_struct_specifier()
      tree.add( subtree )
      return tree
    elif rule == 120:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(57) # char
      tree.add(t)
      return tree
    elif rule == 126:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_typedef_name()
      tree.add( subtree )
      return tree
    elif rule == 128:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(31) # signed
      tree.add(t)
      return tree
    elif rule == 145:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(5) # int
      tree.add(t)
      return tree
    elif rule == 166:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(107) # long
      tree.add(t)
      return tree
    elif rule == 169:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(95) # void
      tree.add(t)
      return tree
    elif rule == 182:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_union_specifier()
      tree.add( subtree )
      return tree
    elif rule == 247:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(32) # imaginary
      tree.add(t)
      return tree
    elif rule == 297:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(111) # complex
      tree.add(t)
      return tree
    elif rule == 313:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(45) # bool
      tree.add(t)
      return tree
    elif rule == 322:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(22) # double
      tree.add(t)
      return tree
    elif rule == 356:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(113) # short
      tree.add(t)
      return tree
    elif rule == 377:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(16) # float
      tree.add(t)
      return tree
    elif rule == 386:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(39) # unsigned
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_enumeration_constant(self):
    current = self.tokens.current()
    rule = self.table[40][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(156, self.nonterminals[156]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 107:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(50) # identifier
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_enumerator_assignment(self):
    current = self.tokens.current()
    rule = self.table[41][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(157, self.nonterminals[157]))
    tree.list = False
    if current != None and (current.getId() in [100, 75]):
      return tree
    if current == None:
      return tree
    if rule == 150:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(98) # assign
      tree.add(t)
      subtree = self.parse__expr()
      tree.add( subtree )
      return tree
    return tree
  def parse_expression_opt(self):
    current = self.tokens.current()
    rule = self.table[42][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(158, self.nonterminals[158]))
    tree.list = False
    if current != None and (current.getId() in [9, 15]):
      return tree
    if current == None:
      return tree
    if rule == 174:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__expr()
      tree.add( subtree )
      return tree
    elif current.getId() in [55, 81, 60, 52, 37, 38, 10, 69, 105, 93, 23, 110, 50, 20, 46, 96]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__expr()
      tree.add( subtree )
    return tree
  def parse_static_opt(self):
    current = self.tokens.current()
    rule = self.table[43][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(159, self.nonterminals[159]))
    tree.list = False
    if current != None and (current.getId() in [55, 81, 60, 52, 37, 38, 10, 69, 105, 93, 23, 110, 50, 20, 46, 96]):
      return tree
    if current == None:
      return tree
    if rule == 131:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(70) # static
      tree.add(t)
      return tree
    return tree
  def parse_initializer(self):
    current = self.tokens.current()
    rule = self.table[44][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(160, self.nonterminals[160]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 105:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__expr_sans_comma()
      tree.add( subtree )
      return tree
    elif rule == 172:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(87) # lbrace
      tree.add(t)
      subtree = self.parse__gen12()
      tree.add( subtree )
      subtree = self.parse_trailing_comma_opt()
      tree.add( subtree )
      t = self.expect(71) # rbrace
      tree.add(t)
      return tree
    elif current.getId() in [59, 60, 52, 37, 38, 10, 69, 105, 93, 23, 110, 50, 20, 46, 81, 96]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__expr_sans_comma()
      tree.add( subtree )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_union_specifier(self):
    current = self.tokens.current()
    rule = self.table[45][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(161, self.nonterminals[161]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 184:
      tree.astTransform = AstTransformNodeCreator('Union', {'definition': 1})
      t = self.expect(109) # union
      tree.add(t)
      subtree = self.parse_struct_or_union_sub()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_declaration(self):
    current = self.tokens.current()
    rule = self.table[46][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(162, self.nonterminals[162]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 229:
      tree.astTransform = AstTransformNodeCreator('Declaration', {'init_declarators': 1, 'declaration_specifiers': 0})
      subtree = self.parse__gen1()
      tree.add( subtree )
      subtree = self.parse__gen8()
      tree.add( subtree )
      t = self.expect(15) # semi
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen7(self):
    current = self.tokens.current()
    rule = self.table[48][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(164, self.nonterminals[164]))
    tree.list = 'nlist'
    if current != None and (current.getId() in [87, 15, 100]):
      return tree
    if current == None:
      return tree
    if rule == 411:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_declaration()
      tree.add( subtree )
      subtree = self.parse__gen7()
      tree.add( subtree )
      return tree
    return tree
  def parse_enum_specifier(self):
    current = self.tokens.current()
    rule = self.table[49][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(165, self.nonterminals[165]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 176:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(8) # enum
      tree.add(t)
      subtree = self.parse_enum_specifier_sub()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_block_item(self):
    current = self.tokens.current()
    rule = self.table[50][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(166, self.nonterminals[166]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 165:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_declaration()
      tree.add( subtree )
      return tree
    elif rule == 285:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_statement()
      tree.add( subtree )
      return tree
    elif current.getId() in [55, 81, 60, 52, 37, 38, 10, 69, 105, 93, 23, 110, 50, 20, 46, 96]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_statement()
      tree.add( subtree )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen36(self):
    current = self.tokens.current()
    rule = self.table[51][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(167, self.nonterminals[167]))
    tree.list = 'nlist'
    if current != None and (current.getId() in [71]):
      return tree
    if current == None:
      return tree
    if rule == 78:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_block_item()
      tree.add( subtree )
      subtree = self.parse__gen36()
      tree.add( subtree )
      return tree
    elif current.getId() in [55, 81, 60, 52, 37, 38, 10, 69, 105, 93, 23, 110, 50, 20, 46, 96]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_block_item()
      tree.add( subtree )
      subtree = self.parse__gen36()
      tree.add( subtree )
    return tree
  def parse_else_if_statement_list(self):
    current = self.tokens.current()
    rule = self.table[52][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(168, self.nonterminals[168]))
    tree.list = False
    if current == None:
      return tree
    if rule == 408:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen39()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_parameter_declaration_sub(self):
    current = self.tokens.current()
    rule = self.table[53][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(169, self.nonterminals[169]))
    tree.list = False
    if current == None:
      return tree
    if rule == 30:
      tree.astTransform = AstTransformNodeCreator('ParameterSub', {'name_and_size': 1, 'pointer': 0})
      subtree = self.parse_pointer_opt()
      tree.add( subtree )
      subtree = self.parse_parameter_declaration_sub_sub()
      tree.add( subtree )
      return tree
    elif current.getId() in [50, 58, 52]:
      tree.astTransform = AstTransformNodeCreator('ParameterSub', {'name_and_size': 1, 'pointer': 0})
      subtree = self.parse_pointer_opt()
      tree.add( subtree )
      subtree = self.parse_parameter_declaration_sub_sub()
      tree.add( subtree )
    elif current.getId() in [43, 52]:
      tree.astTransform = AstTransformNodeCreator('ParameterSub', {'name_and_size': 1, 'pointer': 0})
      subtree = self.parse_pointer_opt()
      tree.add( subtree )
      subtree = self.parse_parameter_declaration_sub_sub()
      tree.add( subtree )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen32(self):
    current = self.tokens.current()
    rule = self.table[54][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(170, self.nonterminals[170]))
    tree.list = False
    if current != None and (current.getId() in [100, 76]):
      return tree
    if current == None:
      return tree
    if rule == 162:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_parameter_declaration_sub()
      tree.add( subtree )
      return tree
    elif current.getId() in [50, 58, 52]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_parameter_declaration_sub()
      tree.add( subtree )
    elif current.getId() in [43, 52]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_parameter_declaration_sub()
      tree.add( subtree )
    return tree
  def parse_typedef_name(self):
    current = self.tokens.current()
    rule = self.table[55][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(171, self.nonterminals[171]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 134:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(104) # typedef_identifier
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen12(self):
    current = self.tokens.current()
    rule = self.table[56][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(172, self.nonterminals[172]))
    tree.list = 'slist'
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 50:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_initializer_list_item()
      tree.add( subtree )
      subtree = self.parse__gen13()
      tree.add( subtree )
      return tree
    elif current.getId() in [59, 60, 52, 37, 38, 10, 69, 105, 93, 23, 110, 50, 20, 46, 81, 96]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_initializer_list_item()
      tree.add( subtree )
      subtree = self.parse__gen13()
      tree.add( subtree )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen13(self):
    current = self.tokens.current()
    rule = self.table[57][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(173, self.nonterminals[173]))
    tree.list = 'slist'
    if current != None and (current.getId() in [75]):
      return tree
    if current == None:
      return tree
    if rule == 343:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(100) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self.parse_initializer_list_item()
      tree.add( subtree )
      subtree = self.parse__gen13()
      tree.add( subtree )
      return tree
    return tree
  def parse_direct_declarator_expr(self):
    current = self.tokens.current()
    rule = self.table[58][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(174, self.nonterminals[174]))
    tree.list = False
    if current != None and (current.getId() in []):
      return tree
    if current == None:
      return tree
    if rule == 111:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_direct_declarator_modifier_list_opt()
      tree.add( subtree )
      subtree = self.parse_direct_declarator_size()
      tree.add( subtree )
      return tree
    elif current.getId() in [55, 81, 60, 52, 37, 38, 10, 69, 105, 93, 23, 110, 50, 20, 46, 96]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_direct_declarator_modifier_list_opt()
      tree.add( subtree )
      subtree = self.parse_direct_declarator_size()
      tree.add( subtree )
    return tree
  def parse_init_declarator_list(self):
    current = self.tokens.current()
    rule = self.table[59][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(175, self.nonterminals[175]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 71:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen9()
      tree.add( subtree )
      return tree
    elif current.getId() in [50, 58, 52]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen9()
      tree.add( subtree )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_pp(self):
    current = self.tokens.current()
    rule = self.table[60][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(176, self.nonterminals[176]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 91:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(56) # defined
      tree.add(t)
      return tree
    elif rule == 153:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(112) # pp_number
      tree.add(t)
      return tree
    elif rule == 340:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(99) # defined_separator
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_for_incr(self):
    current = self.tokens.current()
    rule = self.table[61][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(177, self.nonterminals[177]))
    tree.list = False
    if current != None and (current.getId() in [9]):
      return tree
    if current == None:
      return tree
    if rule == 281:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(15) # semi
      tree.add(t)
      subtree = self.parse_expression_opt()
      tree.add( subtree )
      return tree
    return tree
  def parse_declarator_initializer(self):
    current = self.tokens.current()
    rule = self.table[62][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(178, self.nonterminals[178]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 77:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(98) # assign
      tree.add(t)
      subtree = self.parse_initializer()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_struct_specifier(self):
    current = self.tokens.current()
    rule = self.table[63][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(179, self.nonterminals[179]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 346:
      tree.astTransform = AstTransformNodeCreator('Struct', {'definition': 1})
      t = self.expect(106) # struct
      tree.add(t)
      subtree = self.parse_struct_or_union_sub()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_parameter_declaration_sub_sub(self):
    current = self.tokens.current()
    rule = self.table[64][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(180, self.nonterminals[180]))
    tree.list = False
    if current == None:
      return tree
    if rule == 123:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__direct_declarator()
      tree.add( subtree )
      return tree
    elif rule == 414:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen33()
      tree.add( subtree )
      return tree
    elif current.getId() in [50, 58, 52]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__direct_declarator()
      tree.add( subtree )
    elif current.getId() in [43, 52]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen33()
      tree.add( subtree )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_trailing_comma_opt(self):
    current = self.tokens.current()
    rule = self.table[65][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(181, self.nonterminals[181]))
    tree.list = False
    if current != None and (current.getId() in [71]):
      return tree
    if current == None:
      return tree
    if rule == 267:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(75) # trailing_comma
      tree.add(t)
      return tree
    return tree
  def parse_va_args(self):
    current = self.tokens.current()
    rule = self.table[66][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(182, self.nonterminals[182]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 400:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(76) # comma_va_args
      tree.add(t)
      t = self.expect(78) # elipsis
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen34(self):
    current = self.tokens.current()
    rule = self.table[67][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(183, self.nonterminals[183]))
    tree.list = 'nlist'
    if current != None and (current.getId() in [100, 58, 43, 76, 50, 52]):
      return tree
    if current == None:
      return tree
    if rule == 245:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_pointer_sub()
      tree.add( subtree )
      subtree = self.parse__gen34()
      tree.add( subtree )
      return tree
    return tree
  def parse_struct_or_union_body(self):
    current = self.tokens.current()
    rule = self.table[68][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(184, self.nonterminals[184]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 19:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(87) # lbrace
      tree.add(t)
      subtree = self.parse__gen17()
      tree.add( subtree )
      t = self.expect(71) # rbrace
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_expression_statement(self):
    current = self.tokens.current()
    rule = self.table[69][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(185, self.nonterminals[185]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 163:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_expression_opt()
      tree.add( subtree )
      t = self.expect(15) # semi
      tree.add(t)
      return tree
    elif current.getId() in [55, 81, 60, 52, 37, 38, 10, 69, 105, 93, 23, 110, 50, 20, 46, 96]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_expression_opt()
      tree.add( subtree )
      tree.add( self.expect(15) ) # semi
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen16(self):
    current = self.tokens.current()
    rule = self.table[70][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(186, self.nonterminals[186]))
    tree.list = False
    if current != None and (current.getId() in [11, 28, 58, 32, 43, 8, 64, 107, 86, 89, 70, 16, 76, 72, 79, 22, 35, 24, 106, 88, 31, 5, 104, 15, 113, 95, 39, 100, 47, 57, 45, 109, 54, 110, 50, 111, 52]):
      return tree
    if current == None:
      return tree
    if rule == 109:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_struct_or_union_body()
      tree.add( subtree )
      return tree
    return tree
  def parse__gen25(self):
    current = self.tokens.current()
    rule = self.table[71][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(187, self.nonterminals[187]))
    tree.list = 'nlist'
    if current != None and (current.getId() in [100, 70, 58, 43, 76, 110, 50, 52]):
      return tree
    if current == None:
      return tree
    if rule == 319:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_type_qualifier()
      tree.add( subtree )
      subtree = self.parse__gen25()
      tree.add( subtree )
      return tree
    return tree
  def parse_statement(self):
    current = self.tokens.current()
    rule = self.table[72][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(188, self.nonterminals[188]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 5:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_labeled_statement()
      tree.add( subtree )
      return tree
    elif rule == 10:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_expression_statement()
      tree.add( subtree )
      return tree
    elif rule == 85:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_selection_statement()
      tree.add( subtree )
      return tree
    elif rule == 113:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_compound_statement()
      tree.add( subtree )
      return tree
    elif rule == 116:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_jump_statement()
      tree.add( subtree )
      return tree
    elif rule == 363:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_iteration_statement()
      tree.add( subtree )
      return tree
    elif current.getId() in [55, 81, 60, 52, 37, 38, 10, 69, 105, 93, 23, 110, 50, 20, 46, 96]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_expression_statement()
      tree.add( subtree )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen42(self):
    current = self.tokens.current()
    rule = self.table[73][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(189, self.nonterminals[189]))
    tree.list = False
    if current != None and (current.getId() in []):
      return tree
    if current == None:
      return tree
    if rule == 290:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_parameter_type_list()
      tree.add( subtree )
      return tree
    return tree
  def parse_external_prototype(self):
    current = self.tokens.current()
    rule = self.table[74][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(190, self.nonterminals[190]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 345:
      tree.astTransform = AstTransformNodeCreator('FunctionPrototype', {'declaration_list': 2, 'declarator': 1})
      t = self.expect(86) # function_prototype_hint
      tree.add(t)
      subtree = self.parse_declarator()
      tree.add( subtree )
      subtree = self.parse__gen5()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_misc(self):
    current = self.tokens.current()
    rule = self.table[75][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(191, self.nonterminals[191]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 36:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(74) # endif
      tree.add(t)
      return tree
    elif rule == 254:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(4) # universal_character_name
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_abstract_declarator(self):
    current = self.tokens.current()
    rule = self.table[76][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(192, self.nonterminals[192]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 396:
      tree.astTransform = AstTransformNodeCreator('AbstractDeclarator', {'direct_abstract_declarator': 1, 'pointer': 1})
      subtree = self.parse_pointer_opt()
      tree.add( subtree )
      subtree = self.parse__direct_abstract_declarator()
      tree.add( subtree )
      return tree
    elif current.getId() in [43, 52]:
      tree.astTransform = AstTransformNodeCreator('AbstractDeclarator', {'direct_abstract_declarator': 1, 'pointer': 1})
      subtree = self.parse_pointer_opt()
      tree.add( subtree )
      subtree = self.parse__direct_abstract_declarator()
      tree.add( subtree )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_struct_declaration(self):
    current = self.tokens.current()
    rule = self.table[77][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(193, self.nonterminals[193]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 243:
      tree.astTransform = AstTransformNodeCreator('StructOrUnionDeclaration', {'specifier_qualifiers': 0, 'declarators': 1})
      subtree = self.parse__gen18()
      tree.add( subtree )
      subtree = self.parse__gen19()
      tree.add( subtree )
      t = self.expect(15) # semi
      tree.add(t)
      return tree
    elif current.getId() in [50, 58, 52]:
      tree.astTransform = AstTransformNodeCreator('StructOrUnionDeclaration', {'specifier_qualifiers': 0, 'declarators': 1})
      subtree = self.parse__gen18()
      tree.add( subtree )
      subtree = self.parse__gen19()
      tree.add( subtree )
      tree.add( self.expect(15) ) # semi
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_designator(self):
    current = self.tokens.current()
    rule = self.table[78][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(194, self.nonterminals[194]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 2:
      tree.astTransform = AstTransformNodeCreator('MemberAccess', {'name': 1})
      t = self.expect(108) # dot
      tree.add(t)
      t = self.expect(50) # identifier
      tree.add(t)
      return tree
    elif rule == 410:
      tree.astTransform = AstTransformNodeCreator('ArrayAccess', {'index': 1})
      t = self.expect(17) # lsquare
      tree.add(t)
      subtree = self.parse__expr()
      tree.add( subtree )
      t = self.expect(40) # rsquare
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_parameter_type_list(self):
    current = self.tokens.current()
    rule = self.table[79][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(195, self.nonterminals[195]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 333:
      tree.astTransform = AstTransformNodeCreator('ParameterTypeList', {'parameter_declarations': 0, 'va_args': 1})
      subtree = self.parse__gen27()
      tree.add( subtree )
      subtree = self.parse__gen29()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_for_init(self):
    current = self.tokens.current()
    rule = self.table[80][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(196, self.nonterminals[196]))
    tree.list = False
    if current != None and (current.getId() in [15]):
      return tree
    if current == None:
      return tree
    if rule == 135:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_declaration()
      tree.add( subtree )
      subtree = self.parse_expression_opt()
      tree.add( subtree )
      return tree
    elif rule == 209:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__expr()
      tree.add( subtree )
      return tree
    elif current.getId() in [55, 81, 60, 52, 37, 38, 10, 69, 105, 93, 23, 110, 50, 20, 46, 96]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__expr()
      tree.add( subtree )
    return tree
  def parse_translation_unit(self):
    current = self.tokens.current()
    rule = self.table[81][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(197, self.nonterminals[197]))
    tree.list = False
    if current == None:
      return tree
    if rule == 67:
      tree.astTransform = AstTransformNodeCreator('TranslationUnit', {'external_declarations': 0})
      subtree = self.parse__gen0()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_function_specifier(self):
    current = self.tokens.current()
    rule = self.table[82][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(198, self.nonterminals[198]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 75:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(89) # inline
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_external_declaration(self):
    current = self.tokens.current()
    rule = self.table[83][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(199, self.nonterminals[199]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 202:
      tree.astTransform = AstTransformNodeCreator('ExternalDeclaration', {'declarations': 2, 'declaration_specifiers': 1})
      t = self.expect(6) # external_declaration_hint
      tree.add(t)
      subtree = self.parse__gen1()
      tree.add( subtree )
      subtree = self.parse_external_declaration_sub()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen0(self):
    current = self.tokens.current()
    rule = self.table[84][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(200, self.nonterminals[200]))
    tree.list = 'nlist'
    if current != None and (current.getId() in [-1]):
      return tree
    if current == None:
      return tree
    if rule == 352:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_external_declaration()
      tree.add( subtree )
      subtree = self.parse__gen0()
      tree.add( subtree )
      return tree
    return tree
  def parse__gen8(self):
    current = self.tokens.current()
    rule = self.table[85][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(201, self.nonterminals[201]))
    tree.list = False
    if current != None and (current.getId() in [15]):
      return tree
    if current == None:
      return tree
    if rule == 409:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_init_declarator_list()
      tree.add( subtree )
      return tree
    elif current.getId() in [50, 58, 52]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_init_declarator_list()
      tree.add( subtree )
    return tree
  def parse_struct_or_union_sub(self):
    current = self.tokens.current()
    rule = self.table[87][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(203, self.nonterminals[203]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 32:
      tree.astTransform = AstTransformNodeCreator('StructOrUnion', {'body': 0})
      subtree = self.parse_struct_or_union_body()
      tree.add( subtree )
      return tree
    elif rule == 204:
      tree.astTransform = AstTransformNodeCreator('StructOrUnion', {'body': 1, 'name': 0})
      t = self.expect(50) # identifier
      tree.add(t)
      subtree = self.parse__gen16()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_specifier_qualifier(self):
    current = self.tokens.current()
    rule = self.table[88][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(204, self.nonterminals[204]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 149:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_type_qualifier()
      tree.add( subtree )
      return tree
    elif rule == 387:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_type_specifier()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen1(self):
    current = self.tokens.current()
    rule = self.table[89][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(205, self.nonterminals[205]))
    tree.list = 'mlist'
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 167:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_declaration_specifier()
      tree.add( subtree )
      subtree = self.parse__gen2()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen18(self):
    current = self.tokens.current()
    rule = self.table[90][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(206, self.nonterminals[206]))
    tree.list = 'nlist'
    if current != None and (current.getId() in [11, 50, 110, 58, 52]):
      return tree
    if current == None:
      return tree
    if rule == 357:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_specifier_qualifier()
      tree.add( subtree )
      subtree = self.parse__gen18()
      tree.add( subtree )
      return tree
    return tree
  def parse_selection_statement(self):
    current = self.tokens.current()
    rule = self.table[91][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(207, self.nonterminals[207]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 64:
      tree.astTransform = AstTransformNodeCreator('Switch', {'expr': 2, 'statment': 4})
      t = self.expect(73) # switch
      tree.add(t)
      t = self.expect(52) # lparen
      tree.add(t)
      subtree = self.parse__expr()
      tree.add( subtree )
      t = self.expect(9) # rparen
      tree.add(t)
      subtree = self.parse_statement()
      tree.add( subtree )
      return tree
    elif rule == 260:
      tree.astTransform = AstTransformNodeCreator('If', {'elseif': 6, 'statement': 4, 'condition': 2, 'else': 7})
      t = self.expect(7) # if
      tree.add(t)
      t = self.expect(52) # lparen
      tree.add(t)
      subtree = self.parse__expr()
      tree.add( subtree )
      t = self.expect(9) # rparen
      tree.add(t)
      subtree = self.parse_statement()
      tree.add( subtree )
      t = self.expect(74) # endif
      tree.add(t)
      subtree = self.parse__gen37()
      tree.add( subtree )
      subtree = self.parse__gen38()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_direct_declarator_modifier_list_opt(self):
    current = self.tokens.current()
    rule = self.table[92][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(208, self.nonterminals[208]))
    tree.list = False
    if current != None and (current.getId() in [55, 81, 60, 52, 37, 38, 10, 69, 110, 93, 23, 105, 50, 20, 46, 96]):
      return tree
    if current == None:
      return tree
    if rule == 127:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen26()
      tree.add( subtree )
      return tree
    return tree
  def parse_direct_declarator_size(self):
    current = self.tokens.current()
    rule = self.table[93][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(209, self.nonterminals[209]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 270:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__expr()
      tree.add( subtree )
      return tree
    elif rule == 385:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(110) # asterisk
      tree.add(t)
      return tree
    elif current.getId() in [55, 81, 60, 52, 37, 38, 10, 69, 105, 93, 23, 110, 50, 20, 46, 96]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__expr()
      tree.add( subtree )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen31(self):
    current = self.tokens.current()
    rule = self.table[94][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(210, self.nonterminals[210]))
    tree.list = 'slist'
    if current != None and (current.getId() in []):
      return tree
    if current == None:
      return tree
    if rule == 286:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(100) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self.parse_identifier()
      tree.add( subtree )
      subtree = self.parse__gen31()
      tree.add( subtree )
      return tree
    return tree
  def parse__gen2(self):
    current = self.tokens.current()
    rule = self.table[95][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(211, self.nonterminals[211]))
    tree.list = 'mlist'
    if current != None and (current.getId() in [24, 86, 52, 58, 43, 15, 100, 110, 76, 50, 54]):
      return tree
    if current == None:
      return tree
    if rule == 376:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_declaration_specifier()
      tree.add( subtree )
      subtree = self.parse__gen2()
      tree.add( subtree )
      return tree
    return tree
  def parse_struct_declarator(self):
    current = self.tokens.current()
    rule = self.table[96][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(212, self.nonterminals[212]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 201:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_declarator()
      tree.add( subtree )
      subtree = self.parse__gen21()
      tree.add( subtree )
      return tree
    elif rule == 331:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_struct_declarator_body()
      tree.add( subtree )
      return tree
    elif current.getId() in [50, 58, 52]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_declarator()
      tree.add( subtree )
      subtree = self.parse__gen21()
      tree.add( subtree )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen19(self):
    current = self.tokens.current()
    rule = self.table[97][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(213, self.nonterminals[213]))
    tree.list = 'slist'
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 367:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_struct_declarator()
      tree.add( subtree )
      subtree = self.parse__gen20()
      tree.add( subtree )
      return tree
    elif current.getId() in [50, 58, 52]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_struct_declarator()
      tree.add( subtree )
      subtree = self.parse__gen20()
      tree.add( subtree )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen17(self):
    current = self.tokens.current()
    rule = self.table[98][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(214, self.nonterminals[214]))
    tree.list = 'nlist'
    if current != None and (current.getId() in [71]):
      return tree
    if current == None:
      return tree
    if rule == 337:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_struct_declaration()
      tree.add( subtree )
      subtree = self.parse__gen17()
      tree.add( subtree )
      return tree
    elif current.getId() in [50, 58, 52]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_struct_declaration()
      tree.add( subtree )
      subtree = self.parse__gen17()
      tree.add( subtree )
    return tree
  def parse__gen20(self):
    current = self.tokens.current()
    rule = self.table[99][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(215, self.nonterminals[215]))
    tree.list = 'slist'
    if current != None and (current.getId() in [15]):
      return tree
    if current == None:
      return tree
    if rule == 14:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(100) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self.parse_struct_declarator()
      tree.add( subtree )
      subtree = self.parse__gen20()
      tree.add( subtree )
      return tree
    return tree
  def parse_declaration_specifier(self):
    current = self.tokens.current()
    rule = self.table[100][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(216, self.nonterminals[216]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 94:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_type_specifier()
      tree.add( subtree )
      return tree
    elif rule == 139:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_storage_class_specifier()
      tree.add( subtree )
      return tree
    elif rule == 278:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_function_specifier()
      tree.add( subtree )
      return tree
    elif rule == 348:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_type_qualifier()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_direct_declarator_modifier(self):
    current = self.tokens.current()
    rule = self.table[101][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(217, self.nonterminals[217]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 51:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_type_qualifier()
      tree.add( subtree )
      return tree
    elif rule == 251:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(70) # static
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen26(self):
    current = self.tokens.current()
    rule = self.table[102][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(218, self.nonterminals[218]))
    tree.list = 'nlist'
    if current != None and (current.getId() in [55, 81, 60, 52, 50, 38, 10, 69, 110, 46, 23, 105, 37, 20, 93, 96]):
      return tree
    if current == None:
      return tree
    if rule == 370:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_direct_declarator_modifier()
      tree.add( subtree )
      subtree = self.parse__gen26()
      tree.add( subtree )
      return tree
    return tree
  def parse_block_item_list(self):
    current = self.tokens.current()
    rule = self.table[103][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(219, self.nonterminals[219]))
    tree.list = False
    if current == None:
      return tree
    if rule == 144:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen36()
      tree.add( subtree )
      return tree
    elif current.getId() in [55, 81, 60, 52, 37, 38, 10, 69, 105, 93, 23, 110, 50, 20, 46, 96]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen36()
      tree.add( subtree )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen15(self):
    current = self.tokens.current()
    rule = self.table[104][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(220, self.nonterminals[220]))
    tree.list = 'nlist'
    if current != None and (current.getId() in [98]):
      return tree
    if current == None:
      return tree
    if rule == 223:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_designator()
      tree.add( subtree )
      subtree = self.parse__gen15()
      tree.add( subtree )
      return tree
    return tree
  def parse__gen35(self):
    current = self.tokens.current()
    rule = self.table[105][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(221, self.nonterminals[221]))
    tree.list = False
    if current != None and (current.getId() in [71]):
      return tree
    if current == None:
      return tree
    if rule == 60:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_block_item_list()
      tree.add( subtree )
      return tree
    elif current.getId() in [55, 81, 60, 52, 37, 38, 10, 69, 105, 93, 23, 110, 50, 20, 46, 96]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_block_item_list()
      tree.add( subtree )
    return tree
  def parse_type_name(self):
    current = self.tokens.current()
    rule = self.table[106][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(222, self.nonterminals[222]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 218:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(5) # int
      tree.add(t)
      return tree
    elif rule == 222:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(57) # char
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_for_cond(self):
    current = self.tokens.current()
    rule = self.table[107][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(223, self.nonterminals[223]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 312:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(15) # semi
      tree.add(t)
      subtree = self.parse_expression_opt()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_external_declaration_sub(self):
    current = self.tokens.current()
    rule = self.table[108][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(224, self.nonterminals[224]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 147:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen3()
      tree.add( subtree )
      t = self.expect(15) # semi
      tree.add(t)
      return tree
    elif rule == 307:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_external_function()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_pointer(self):
    current = self.tokens.current()
    rule = self.table[109][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(225, self.nonterminals[225]))
    tree.list = False
    if current == None:
      return tree
    if rule == 205:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen34()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_keyword(self):
    current = self.tokens.current()
    rule = self.table[110][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(226, self.nonterminals[226]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 22:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(51) # case
      tree.add(t)
      return tree
    elif rule == 33:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(73) # switch
      tree.add(t)
      return tree
    elif rule == 44:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(32) # imaginary
      tree.add(t)
      return tree
    elif rule == 47:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(64) # extern
      tree.add(t)
      return tree
    elif rule == 70:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(106) # struct
      tree.add(t)
      return tree
    elif rule == 73:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(109) # union
      tree.add(t)
      return tree
    elif rule == 76:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(16) # float
      tree.add(t)
      return tree
    elif rule == 82:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(45) # bool
      tree.add(t)
      return tree
    elif rule == 89:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(57) # char
      tree.add(t)
      return tree
    elif rule == 90:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(97) # for
      tree.add(t)
      return tree
    elif rule == 95:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(49) # break
      tree.add(t)
      return tree
    elif rule == 97:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(95) # void
      tree.add(t)
      return tree
    elif rule == 106:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(111) # complex
      tree.add(t)
      return tree
    elif rule == 125:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(88) # register
      tree.add(t)
      return tree
    elif rule == 154:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(79) # auto
      tree.add(t)
      return tree
    elif rule == 155:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(94) # default
      tree.add(t)
      return tree
    elif rule == 157:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(5) # int
      tree.add(t)
      return tree
    elif rule == 170:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(91) # do
      tree.add(t)
      return tree
    elif rule == 198:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(28) # typedef
      tree.add(t)
      return tree
    elif rule == 199:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(8) # enum
      tree.add(t)
      return tree
    elif rule == 216:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(35) # restrict
      tree.add(t)
      return tree
    elif rule == 262:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(107) # long
      tree.add(t)
      return tree
    elif rule == 266:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(25) # return
      tree.add(t)
      return tree
    elif rule == 268:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(67) # goto
      tree.add(t)
      return tree
    elif rule == 269:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(31) # signed
      tree.add(t)
      return tree
    elif rule == 274:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(39) # unsigned
      tree.add(t)
      return tree
    elif rule == 287:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(46) # sizeof
      tree.add(t)
      return tree
    elif rule == 296:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(7) # if
      tree.add(t)
      return tree
    elif rule == 318:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(0) # while
      tree.add(t)
      return tree
    elif rule == 338:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(47) # const
      tree.add(t)
      return tree
    elif rule == 339:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(72) # volatile
      tree.add(t)
      return tree
    elif rule == 341:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(113) # short
      tree.add(t)
      return tree
    elif rule == 374:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(66) # else
      tree.add(t)
      return tree
    elif rule == 375:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(103) # continue
      tree.add(t)
      return tree
    elif rule == 402:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(70) # static
      tree.add(t)
      return tree
    elif rule == 403:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(89) # inline
      tree.add(t)
      return tree
    elif rule == 419:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(22) # double
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_external_function(self):
    current = self.tokens.current()
    rule = self.table[111][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(227, self.nonterminals[227]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 382:
      tree.astTransform = AstTransformNodeCreator('FunctionDefinition', {'body': 3, 'declaration_list': 2, 'signature': 1})
      t = self.expect(24) # function_definition_hint
      tree.add(t)
      subtree = self.parse_declarator()
      tree.add( subtree )
      subtree = self.parse__gen5()
      tree.add( subtree )
      subtree = self.parse_compound_statement()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_struct_declarator_body(self):
    current = self.tokens.current()
    rule = self.table[113][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(229, self.nonterminals[229]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 13:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(11) # colon
      tree.add(t)
      subtree = self.parse_declarator()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_iteration_statement(self):
    current = self.tokens.current()
    rule = self.table[114][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(230, self.nonterminals[230]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 69:
      tree.astTransform = AstTransformNodeCreator('While', {'expr': 2, 'statement': 4})
      t = self.expect(0) # while
      tree.add(t)
      t = self.expect(52) # lparen
      tree.add(t)
      subtree = self.parse__expr()
      tree.add( subtree )
      t = self.expect(9) # rparen
      tree.add(t)
      subtree = self.parse_statement()
      tree.add( subtree )
      return tree
    elif rule == 92:
      tree.astTransform = AstTransformNodeCreator('DoWhile', {'expr': 4, 'statement': 1})
      t = self.expect(91) # do
      tree.add(t)
      subtree = self.parse_statement()
      tree.add( subtree )
      t = self.expect(0) # while
      tree.add(t)
      t = self.expect(52) # lparen
      tree.add(t)
      subtree = self.parse__expr()
      tree.add( subtree )
      t = self.expect(9) # rparen
      tree.add(t)
      t = self.expect(15) # semi
      tree.add(t)
      return tree
    elif rule == 148:
      tree.astTransform = AstTransformNodeCreator('For', {'init': 2, 'cond': 3, 'incr': 4, 'statement': 6})
      t = self.expect(97) # for
      tree.add(t)
      t = self.expect(52) # lparen
      tree.add(t)
      subtree = self.parse_for_init()
      tree.add( subtree )
      subtree = self.parse_for_cond()
      tree.add( subtree )
      subtree = self.parse_for_incr()
      tree.add( subtree )
      t = self.expect(9) # rparen
      tree.add(t)
      subtree = self.parse_statement()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen9(self):
    current = self.tokens.current()
    rule = self.table[115][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(231, self.nonterminals[231]))
    tree.list = 'slist'
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 208:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_init_declarator()
      tree.add( subtree )
      subtree = self.parse__gen10()
      tree.add( subtree )
      return tree
    elif current.getId() in [50, 58, 52]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_init_declarator()
      tree.add( subtree )
      subtree = self.parse__gen10()
      tree.add( subtree )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_token(self):
    current = self.tokens.current()
    rule = self.table[116][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(232, self.nonterminals[232]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 231:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(50) # identifier
      tree.add(t)
      return tree
    elif rule == 334:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_keyword()
      tree.add( subtree )
      return tree
    elif rule == 347:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(112) # pp_number
      tree.add(t)
      return tree
    elif rule == 368:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_constant()
      tree.add( subtree )
      return tree
    elif rule == 378:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(105) # string_literal
      tree.add(t)
      return tree
    elif rule == 384:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_punctuator()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_constant(self):
    current = self.tokens.current()
    rule = self.table[117][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(233, self.nonterminals[233]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 1:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(81) # enumeration_constant
      tree.add(t)
      return tree
    elif rule == 25:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(38) # character_constant
      tree.add(t)
      return tree
    elif rule == 68:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(20) # floating_constant
      tree.add(t)
      return tree
    elif rule == 80:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(93) # hexadecimal_floating_constant
      tree.add(t)
      return tree
    elif rule == 112:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(96) # decimal_floating_constant
      tree.add(t)
      return tree
    elif rule == 261:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(37) # integer_constant
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen21(self):
    current = self.tokens.current()
    rule = self.table[118][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(234, self.nonterminals[234]))
    tree.list = False
    if current != None and (current.getId() in [100, 15]):
      return tree
    if current == None:
      return tree
    if rule == 103:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_struct_declarator_body()
      tree.add( subtree )
      return tree
    return tree
  def parse__gen3(self):
    current = self.tokens.current()
    rule = self.table[119][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(235, self.nonterminals[235]))
    tree.list = 'slist'
    if current != None and (current.getId() in [15]):
      return tree
    if current == None:
      return tree
    if rule == 224:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_external_declaration_sub_sub()
      tree.add( subtree )
      subtree = self.parse__gen4()
      tree.add( subtree )
      return tree
    return tree
  def parse__gen4(self):
    current = self.tokens.current()
    rule = self.table[120][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(236, self.nonterminals[236]))
    tree.list = 'slist'
    if current != None and (current.getId() in [15]):
      return tree
    if current == None:
      return tree
    if rule == 422:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(100) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self.parse_external_declaration_sub_sub()
      tree.add( subtree )
      subtree = self.parse__gen4()
      tree.add( subtree )
      return tree
    return tree
  def parse_external_declaration_sub_sub(self):
    current = self.tokens.current()
    rule = self.table[121][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(237, self.nonterminals[237]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 272:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_external_declarator()
      tree.add( subtree )
      return tree
    elif rule == 294:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_external_prototype()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen29(self):
    current = self.tokens.current()
    rule = self.table[122][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(238, self.nonterminals[238]))
    tree.list = False
    if current != None and (current.getId() in []):
      return tree
    if current == None:
      return tree
    if rule == 17:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_va_args()
      tree.add( subtree )
      return tree
    return tree
  def parse_compound_statement(self):
    current = self.tokens.current()
    rule = self.table[123][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(239, self.nonterminals[239]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 200:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(87) # lbrace
      tree.add(t)
      subtree = self.parse__gen35()
      tree.add( subtree )
      t = self.expect(71) # rbrace
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_direct_declarator_parameter_list(self):
    current = self.tokens.current()
    rule = self.table[124][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(240, self.nonterminals[240]))
    tree.list = False
    if current != None and (current.getId() in []):
      return tree
    if current == None:
      return tree
    if rule == 193:
      tree.astTransform = AstTransformNodeCreator('ParameterList', {'identifiers': 0})
      subtree = self.parse__gen30()
      tree.add( subtree )
      return tree
    elif rule == 355:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_parameter_type_list()
      tree.add( subtree )
      return tree
    return tree
  def parse_identifier(self):
    current = self.tokens.current()
    rule = self.table[125][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(241, self.nonterminals[241]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 21:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(50) # identifier
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_punctuator(self):
    current = self.tokens.current()
    rule = self.table[126][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(242, self.nonterminals[242]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 0:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(102) # bitor
      tree.add(t)
      return tree
    elif rule == 40:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(53) # questionmark
      tree.add(t)
      return tree
    elif rule == 52:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(62) # modeq
      tree.add(t)
      return tree
    elif rule == 56:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(18) # lshifteq
      tree.add(t)
      return tree
    elif rule == 59:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(14) # lteq
      tree.add(t)
      return tree
    elif rule == 62:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(90) # rshifteq
      tree.add(t)
      return tree
    elif rule == 65:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(23) # incr
      tree.add(t)
      return tree
    elif rule == 72:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(100) # comma
      tree.add(t)
      return tree
    elif rule == 79:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(26) # exclamation_point
      tree.add(t)
      return tree
    elif rule == 87:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(15) # semi
      tree.add(t)
      return tree
    elif rule == 88:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(21) # neq
      tree.add(t)
      return tree
    elif rule == 114:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(85) # or
      tree.add(t)
      return tree
    elif rule == 115:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(61) # ampersand
      tree.add(t)
      return tree
    elif rule == 137:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(3) # bitoreq
      tree.add(t)
      return tree
    elif rule == 141:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(115) # and
      tree.add(t)
      return tree
    elif rule == 159:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(2) # gt
      tree.add(t)
      return tree
    elif rule == 160:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(17) # lsquare
      tree.add(t)
      return tree
    elif rule == 168:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(92) # lshift
      tree.add(t)
      return tree
    elif rule == 179:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(84) # bitxoreq
      tree.add(t)
      return tree
    elif rule == 180:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(68) # gteq
      tree.add(t)
      return tree
    elif rule == 181:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(33) # pound
      tree.add(t)
      return tree
    elif rule == 189:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(48) # add
      tree.add(t)
      return tree
    elif rule == 192:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(101) # bitxor
      tree.add(t)
      return tree
    elif rule == 206:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(77) # mod
      tree.add(t)
      return tree
    elif rule == 219:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(52) # lparen
      tree.add(t)
      return tree
    elif rule == 236:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(63) # eq
      tree.add(t)
      return tree
    elif rule == 241:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(71) # rbrace
      tree.add(t)
      return tree
    elif rule == 249:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(34) # subeq
      tree.add(t)
      return tree
    elif rule == 250:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(11) # colon
      tree.add(t)
      return tree
    elif rule == 265:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(36) # tilde
      tree.add(t)
      return tree
    elif rule == 283:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(19) # rshift
      tree.add(t)
      return tree
    elif rule == 288:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(108) # dot
      tree.add(t)
      return tree
    elif rule == 291:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(40) # rsquare
      tree.add(t)
      return tree
    elif rule == 314:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(9) # rparen
      tree.add(t)
      return tree
    elif rule == 324:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(82) # muleq
      tree.add(t)
      return tree
    elif rule == 329:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(87) # lbrace
      tree.add(t)
      return tree
    elif rule == 350:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(98) # assign
      tree.add(t)
      return tree
    elif rule == 360:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(114) # arrow
      tree.add(t)
      return tree
    elif rule == 390:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(69) # decr
      tree.add(t)
      return tree
    elif rule == 392:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(65) # addeq
      tree.add(t)
      return tree
    elif rule == 394:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(80) # lt
      tree.add(t)
      return tree
    elif rule == 401:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(83) # div
      tree.add(t)
      return tree
    elif rule == 404:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(78) # elipsis
      tree.add(t)
      return tree
    elif rule == 416:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(42) # sub
      tree.add(t)
      return tree
    elif rule == 420:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(30) # poundpound
      tree.add(t)
      return tree
    elif rule == 423:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(1) # bitandeq
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_parameter_declaration(self):
    current = self.tokens.current()
    rule = self.table[127][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(243, self.nonterminals[243]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 301:
      tree.astTransform = AstTransformNodeCreator('ParameterDeclaration', {'sub': 1, 'declaration_specifiers': 0})
      subtree = self.parse__gen1()
      tree.add( subtree )
      subtree = self.parse__gen32()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
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
