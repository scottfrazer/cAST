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
  def __init__(self, message):
    self.__dict__.update(locals())
  def __str__(self):
    return self.message
class ExpressionParser__expr:
  def __init__(self, parent):
    self.__dict__.update(locals())
    self.infixBp = {
      3: 3000,
      5: 14000,
      6: 5000,
      9: 9000,
      10: 1000,
      13: 1000,
      20: 1000,
      23: 16000,
      29: 4000,
      30: 8000,
      31: 1000,
      32: 15000,
      33: 1000,
      37: 1000,
      40: 9000,
      47: 1000,
      51: 1000,
      53: 7000,
      57: 12000,
      60: 9000,
      70: 1000,
      72: 9000,
      75: 12000,
      77: 12000,
      82: 15000,
      86: 1000,
      90: 2000,
      92: 15000,
      96: 15000,
      100: 10000,
      101: 15000,
      102: 10000,
      108: 11000,
      109: 8000,
      110: 11000,
      111: 15000,
      113: 1000,
      114: 6000,
    }
    self.prefixBp = {
      6: 13000,
      25: 13000,
      34: 13000,
      75: 13000,
      101: 13000,
      110: 13000,
      111: 13000,
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
    return self.parent.sym
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
    tree = ParseTree( NonTerminal(235, '_expr') )
    current = self.getCurrentToken()
    if not current:
      return tree
    elif current.getId() in [48]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      return self.expect( 48 )
    elif current.getId() in [32]:
      tree.astTransform = AstTransformSubstitution(2)
      tree.nudMorphemeCount = 3
      tree.add( self.expect(32) )
      tree.add( self.parent.parse__expr() )
      tree.add( self.expect(16) )
    elif current.getId() in [74, 67, 46, 65, 35, 58]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      tree.add( self.parent.parse_constant() )
    elif current.getId() in [75]:
      tree.astTransform = AstTransformNodeCreator('Dereference', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(75) )
      tree.add( self.parent.parse__expr( self.getPrefixBp(75) ) )
      tree.isPrefix = True
    elif current.getId() in [101]:
      tree.astTransform = AstTransformNodeCreator('PreDecr', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(101) )
      tree.add( self.parent.parse__expr( self.getPrefixBp(101) ) )
      tree.isPrefix = True
    elif current.getId() in [76]:
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      tree.nudMorphemeCount = 1
      return self.expect( 76 )
    elif current.getId() in [6]:
      tree.astTransform = AstTransformNodeCreator('AddressOf', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(6) )
      tree.add( self.parent.parse__expr( self.getPrefixBp(6) ) )
      tree.isPrefix = True
    elif current.getId() in [93]:
      tree.astTransform = AstTransformNodeCreator('TypeInitializion', {'type': 1, 'initializer': 4})
      tree.nudMorphemeCount = 3
      tree.add( self.expect(93) )
      tree.add( self.parent.parse_type_name() )
      tree.add( self.expect(16) )
    elif current.getId() in [1]:
      tree.astTransform = AstTransformNodeCreator('SizeOf', {'var': 1})
      tree.nudMorphemeCount = 1
      return self.expect( 1 )
    elif current.getId() in [76]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      return self.expect( 76 )
    elif current.getId() in [111]:
      tree.astTransform = AstTransformNodeCreator('PreIncr', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(111) )
      tree.add( self.parent.parse__expr( self.getPrefixBp(111) ) )
      tree.isPrefix = True
    elif current.getId() in [76]:
      tree.astTransform = AstTransformNodeCreator('ArrayIndex', {'params': 2, 'name': 0})
      tree.nudMorphemeCount = 1
      return self.expect( 76 )
    return tree
  def led(self, left):
    tree = ParseTree( NonTerminal(235, '_expr') )
    current = self.getCurrentToken()
    if current.getId() == 23: # 'comma'
      tree.astTransform = AstTransformNodeCreator('Comma', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(23) )
      modifier = 0
      tree.add( self.parent.parse__expr( self.getInfixBp(23) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 31: # 'modeq'
      tree.astTransform = AstTransformNodeCreator('ModAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(31) )
      modifier = 1
      tree.add( self.parent.parse__expr( self.getInfixBp(31) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 32: # 'lparen'
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(32) )
      tree.add( self.parent.parse__gen40() )
      tree.add( self.expect(16) )
    elif current.getId() == 53: # 'bitor'
      tree.astTransform = AstTransformNodeCreator('BitOR', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(53) )
      modifier = 0
      tree.add( self.parent.parse__expr( self.getInfixBp(53) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 50: # 'sizeof_separator'
      tree.astTransform = AstTransformNodeCreator('SizeOf', {'var': 1})
      if left:
        tree.add(left)
      tree.add( self.expect(50) )
      tree.add( self.parent.parse_sizeof_body() )
    elif current.getId() == 109: # 'eq'
      tree.astTransform = AstTransformNodeCreator('Equals', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(109) )
      modifier = 1
      tree.add( self.parent.parse__expr( self.getInfixBp(109) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 10: # 'diveq'
      tree.astTransform = AstTransformNodeCreator('DivideAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(10) )
      modifier = 1
      tree.add( self.parent.parse__expr( self.getInfixBp(10) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 60: # 'gteq'
      tree.astTransform = AstTransformNodeCreator('GreaterThanEq', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(60) )
      modifier = 0
      tree.add( self.parent.parse__expr( self.getInfixBp(60) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 70: # 'bitandeq'
      tree.astTransform = AstTransformNodeCreator('ANDAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(70) )
      modifier = 1
      tree.add( self.parent.parse__expr( self.getInfixBp(70) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 13: # 'bitoreq'
      tree.astTransform = AstTransformNodeCreator('ORAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(13) )
      modifier = 1
      tree.add( self.parent.parse__expr( self.getInfixBp(13) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 111: # 'incr'
      tree.astTransform = AstTransformNodeCreator('PostIncr', {'var': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(111) )
    elif current.getId() == 51: # 'lshifteq'
      tree.astTransform = AstTransformNodeCreator('LeftShiftAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(51) )
      modifier = 1
      tree.add( self.parent.parse__expr( self.getInfixBp(51) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 57: # 'div'
      tree.astTransform = AstTransformNodeCreator('Div', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(57) )
      modifier = 0
      tree.add( self.parent.parse__expr( self.getInfixBp(57) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 113: # 'muleq'
      tree.astTransform = AstTransformNodeCreator('MultiplyAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(113) )
      modifier = 1
      tree.add( self.parent.parse__expr( self.getInfixBp(113) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 6: # 'bitand'
      tree.astTransform = AstTransformNodeCreator('BitAND', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(6) )
      modifier = 0
      tree.add( self.parent.parse__expr( self.getInfixBp(6) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 9: # 'lt'
      tree.astTransform = AstTransformNodeCreator('LessThan', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(9) )
      modifier = 0
      tree.add( self.parent.parse__expr( self.getInfixBp(9) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 72: # 'lteq'
      tree.astTransform = AstTransformNodeCreator('LessThanEq', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(72) )
      modifier = 0
      tree.add( self.parent.parse__expr( self.getInfixBp(72) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 75: # 'asterisk'
      tree.astTransform = AstTransformNodeCreator('Mul', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(75) )
      modifier = 0
      tree.add( self.parent.parse__expr( self.getInfixBp(75) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 110: # 'sub'
      tree.astTransform = AstTransformNodeCreator('Sub', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(110) )
      modifier = 0
      tree.add( self.parent.parse__expr( self.getInfixBp(110) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 77: # 'mod'
      tree.astTransform = AstTransformNodeCreator('Mod', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(77) )
      modifier = 0
      tree.add( self.parent.parse__expr( self.getInfixBp(77) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 5: # 'lbrace'
      tree.astTransform = AstTransformNodeCreator('TypeInitializion', {'type': 1, 'initializer': 4})
      if left:
        tree.add(left)
      tree.add( self.expect(5) )
      tree.add( self.parent.parse__gen12() )
      tree.add( self.parent.parse_trailing_comma_opt() )
      tree.add( self.expect(22) )
    elif current.getId() == 33: # 'addeq'
      tree.astTransform = AstTransformNodeCreator('AddAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(33) )
      modifier = 1
      tree.add( self.parent.parse__expr( self.getInfixBp(33) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 40: # 'gt'
      tree.astTransform = AstTransformNodeCreator('GreaterThan', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(40) )
      modifier = 0
      tree.add( self.parent.parse__expr( self.getInfixBp(40) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 90: # 'questionmark'
      tree.astTransform = AstTransformNodeCreator('TernaryOperator', {'true': 2, 'false': 4, 'cond': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(90) )
      modifier = 1
      tree.add( self.parent.parse__expr( self.getInfixBp(90) - modifier ) )
      tree.add( self.expect(26) )
      modifier = 1
      tree.add( self.parent.parse__expr( self.getInfixBp(90) - modifier ) )
    elif current.getId() == 86: # 'bitxoreq'
      tree.astTransform = AstTransformNodeCreator('XORAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(86) )
      modifier = 1
      tree.add( self.parent.parse__expr( self.getInfixBp(86) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 92: # 'dot'
      tree.astTransform = AstTransformNodeCreator('MemberSelect', {'member': 2, 'object': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(92) )
      modifier = 0
      tree.add( self.parent.parse__expr( self.getInfixBp(92) - modifier ) )
    elif current.getId() == 82: # 'lsquare'
      tree.astTransform = AstTransformNodeCreator('ArrayIndex', {'params': 2, 'name': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(82) )
      tree.add( self.parent.parse__gen40() )
      tree.add( self.expect(68) )
    elif current.getId() == 100: # 'lshift'
      tree.astTransform = AstTransformNodeCreator('LeftShift', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(100) )
      modifier = 0
      tree.add( self.parent.parse__expr( self.getInfixBp(100) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 47: # 'assign'
      tree.astTransform = AstTransformNodeCreator('Assign', {'var': 0, 'value': 2})
      if left:
        tree.add(left)
      tree.add( self.expect(47) )
      modifier = 1
      tree.add( self.parent.parse__expr( self.getInfixBp(47) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 108: # 'add'
      tree.astTransform = AstTransformNodeCreator('Add', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(108) )
      modifier = 0
      tree.add( self.parent.parse__expr( self.getInfixBp(108) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 20: # 'rshifteq'
      tree.astTransform = AstTransformNodeCreator('RightShiftAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(20) )
      modifier = 1
      tree.add( self.parent.parse__expr( self.getInfixBp(20) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 101: # 'decr'
      tree.astTransform = AstTransformNodeCreator('PostDecr', {'var': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(101) )
    elif current.getId() == 96: # 'arrow'
      tree.astTransform = AstTransformNodeCreator('DerefMemberSelect', {'member': 2, 'object': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(96) )
      modifier = 0
      tree.add( self.parent.parse__expr( self.getInfixBp(96) - modifier ) )
    elif current.getId() == 102: # 'rshift'
      tree.astTransform = AstTransformNodeCreator('RightShift', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(102) )
      modifier = 0
      tree.add( self.parent.parse__expr( self.getInfixBp(102) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 37: # 'subeq'
      tree.astTransform = AstTransformNodeCreator('SubtractAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(37) )
      modifier = 1
      tree.add( self.parent.parse__expr( self.getInfixBp(37) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 114: # 'bitxor'
      tree.astTransform = AstTransformNodeCreator('BitXOR', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(114) )
      modifier = 0
      tree.add( self.parent.parse__expr( self.getInfixBp(114) - modifier ) )
      tree.isInfix = True
    return tree
class ExpressionParser__expr_sans_comma:
  def __init__(self, parent):
    self.__dict__.update(locals())
    self.infixBp = {
      3: 3000,
      5: 14000,
      6: 5000,
      9: 9000,
      10: 1000,
      13: 1000,
      20: 1000,
      29: 4000,
      30: 8000,
      31: 1000,
      32: 15000,
      33: 1000,
      37: 1000,
      40: 9000,
      47: 1000,
      51: 1000,
      53: 7000,
      57: 12000,
      60: 9000,
      70: 1000,
      72: 9000,
      75: 12000,
      77: 12000,
      82: 15000,
      86: 1000,
      90: 2000,
      92: 15000,
      96: 15000,
      100: 10000,
      101: 15000,
      102: 10000,
      108: 11000,
      109: 8000,
      110: 11000,
      111: 15000,
      113: 1000,
      114: 6000,
    }
    self.prefixBp = {
      6: 13000,
      25: 13000,
      34: 13000,
      75: 13000,
      101: 13000,
      110: 13000,
      111: 13000,
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
    return self.parent.sym
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
    tree = ParseTree( NonTerminal(116, '_expr_sans_comma') )
    current = self.getCurrentToken()
    if not current:
      return tree
    elif current.getId() in [48]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      return self.expect( 48 )
    elif current.getId() in [76]:
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      tree.nudMorphemeCount = 1
      return self.expect( 76 )
    elif current.getId() in [32]:
      tree.astTransform = AstTransformSubstitution(2)
      tree.nudMorphemeCount = 3
      tree.add( self.expect(32) )
      tree.add( self.parent.parse__expr_sans_comma() )
      tree.add( self.expect(16) )
    elif current.getId() in [101]:
      tree.astTransform = AstTransformNodeCreator('PreDecr', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(101) )
      tree.add( self.parent.parse__expr_sans_comma( self.getPrefixBp(101) ) )
      tree.isPrefix = True
    elif current.getId() in [93]:
      tree.astTransform = AstTransformNodeCreator('TypeInitializion', {'type': 1, 'initializer': 4})
      tree.nudMorphemeCount = 3
      tree.add( self.expect(93) )
      tree.add( self.parent.parse_type_name() )
      tree.add( self.expect(16) )
    elif current.getId() in [74, 67, 46, 65, 35, 58]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      tree.add( self.parent.parse_constant() )
    elif current.getId() in [6]:
      tree.astTransform = AstTransformNodeCreator('AddressOf', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(6) )
      tree.add( self.parent.parse__expr_sans_comma( self.getPrefixBp(6) ) )
      tree.isPrefix = True
    elif current.getId() in [76]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      return self.expect( 76 )
    elif current.getId() in [75]:
      tree.astTransform = AstTransformNodeCreator('Dereference', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(75) )
      tree.add( self.parent.parse__expr_sans_comma( self.getPrefixBp(75) ) )
      tree.isPrefix = True
    elif current.getId() in [1]:
      tree.astTransform = AstTransformNodeCreator('SizeOf', {'var': 1})
      tree.nudMorphemeCount = 1
      return self.expect( 1 )
    elif current.getId() in [111]:
      tree.astTransform = AstTransformNodeCreator('PreIncr', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(111) )
      tree.add( self.parent.parse__expr_sans_comma( self.getPrefixBp(111) ) )
      tree.isPrefix = True
    elif current.getId() in [76]:
      tree.astTransform = AstTransformNodeCreator('ArrayIndex', {'params': 2, 'name': 0})
      tree.nudMorphemeCount = 1
      return self.expect( 76 )
    return tree
  def led(self, left):
    tree = ParseTree( NonTerminal(116, '_expr_sans_comma') )
    current = self.getCurrentToken()
    if current.getId() == 75: # 'asterisk'
      tree.astTransform = AstTransformNodeCreator('Mul', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(75) )
      modifier = 0
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(75) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 110: # 'sub'
      tree.astTransform = AstTransformNodeCreator('Sub', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(110) )
      modifier = 0
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(110) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 37: # 'subeq'
      tree.astTransform = AstTransformNodeCreator('SubtractAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(37) )
      modifier = 1
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(37) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 50: # 'sizeof_separator'
      tree.astTransform = AstTransformNodeCreator('SizeOf', {'var': 1})
      if left:
        tree.add(left)
      tree.add( self.expect(50) )
      tree.add( self.parent.parse_sizeof_body() )
    elif current.getId() == 31: # 'modeq'
      tree.astTransform = AstTransformNodeCreator('ModAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(31) )
      modifier = 1
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(31) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 102: # 'rshift'
      tree.astTransform = AstTransformNodeCreator('RightShift', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(102) )
      modifier = 0
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(102) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 57: # 'div'
      tree.astTransform = AstTransformNodeCreator('Div', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(57) )
      modifier = 0
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(57) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 10: # 'diveq'
      tree.astTransform = AstTransformNodeCreator('DivideAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(10) )
      modifier = 1
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(10) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 9: # 'lt'
      tree.astTransform = AstTransformNodeCreator('LessThan', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(9) )
      modifier = 0
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(9) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 70: # 'bitandeq'
      tree.astTransform = AstTransformNodeCreator('ANDAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(70) )
      modifier = 1
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(70) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 32: # 'lparen'
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(32) )
      tree.add( self.parent.parse__gen40() )
      tree.add( self.expect(16) )
    elif current.getId() == 101: # 'decr'
      tree.astTransform = AstTransformNodeCreator('PostDecr', {'var': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(101) )
    elif current.getId() == 6: # 'bitand'
      tree.astTransform = AstTransformNodeCreator('BitAND', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(6) )
      modifier = 0
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(6) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 77: # 'mod'
      tree.astTransform = AstTransformNodeCreator('Mod', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(77) )
      modifier = 0
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(77) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 40: # 'gt'
      tree.astTransform = AstTransformNodeCreator('GreaterThan', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(40) )
      modifier = 0
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(40) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 82: # 'lsquare'
      tree.astTransform = AstTransformNodeCreator('ArrayIndex', {'params': 2, 'name': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(82) )
      tree.add( self.parent.parse__gen40() )
      tree.add( self.expect(68) )
    elif current.getId() == 111: # 'incr'
      tree.astTransform = AstTransformNodeCreator('PostIncr', {'var': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(111) )
    elif current.getId() == 114: # 'bitxor'
      tree.astTransform = AstTransformNodeCreator('BitXOR', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(114) )
      modifier = 0
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(114) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 53: # 'bitor'
      tree.astTransform = AstTransformNodeCreator('BitOR', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(53) )
      modifier = 0
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(53) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 109: # 'eq'
      tree.astTransform = AstTransformNodeCreator('Equals', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(109) )
      modifier = 1
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(109) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 13: # 'bitoreq'
      tree.astTransform = AstTransformNodeCreator('ORAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(13) )
      modifier = 1
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(13) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 113: # 'muleq'
      tree.astTransform = AstTransformNodeCreator('MultiplyAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(113) )
      modifier = 1
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(113) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 72: # 'lteq'
      tree.astTransform = AstTransformNodeCreator('LessThanEq', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(72) )
      modifier = 0
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(72) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 33: # 'addeq'
      tree.astTransform = AstTransformNodeCreator('AddAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(33) )
      modifier = 1
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(33) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 20: # 'rshifteq'
      tree.astTransform = AstTransformNodeCreator('RightShiftAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(20) )
      modifier = 1
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(20) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 86: # 'bitxoreq'
      tree.astTransform = AstTransformNodeCreator('XORAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(86) )
      modifier = 1
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(86) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 5: # 'lbrace'
      tree.astTransform = AstTransformNodeCreator('TypeInitializion', {'type': 1, 'initializer': 4})
      if left:
        tree.add(left)
      tree.add( self.expect(5) )
      tree.add( self.parent.parse__gen12() )
      tree.add( self.parent.parse_trailing_comma_opt() )
      tree.add( self.expect(22) )
    elif current.getId() == 47: # 'assign'
      tree.astTransform = AstTransformNodeCreator('Assign', {'var': 0, 'value': 2})
      if left:
        tree.add(left)
      tree.add( self.expect(47) )
      modifier = 1
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(47) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 60: # 'gteq'
      tree.astTransform = AstTransformNodeCreator('GreaterThanEq', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(60) )
      modifier = 0
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(60) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 51: # 'lshifteq'
      tree.astTransform = AstTransformNodeCreator('LeftShiftAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(51) )
      modifier = 1
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(51) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 108: # 'add'
      tree.astTransform = AstTransformNodeCreator('Add', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(108) )
      modifier = 0
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(108) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 90: # 'questionmark'
      tree.astTransform = AstTransformNodeCreator('TernaryOperator', {'true': 2, 'false': 4, 'cond': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(90) )
      modifier = 1
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(90) - modifier ) )
      tree.add( self.expect(26) )
      modifier = 1
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(90) - modifier ) )
    elif current.getId() == 92: # 'dot'
      tree.astTransform = AstTransformNodeCreator('MemberSelect', {'member': 2, 'object': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(92) )
      modifier = 0
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(92) - modifier ) )
    elif current.getId() == 100: # 'lshift'
      tree.astTransform = AstTransformNodeCreator('LeftShift', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(100) )
      modifier = 0
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(100) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 96: # 'arrow'
      tree.astTransform = AstTransformNodeCreator('DerefMemberSelect', {'member': 2, 'object': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(96) )
      modifier = 0
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(96) - modifier ) )
    return tree
class ExpressionParser__direct_declarator:
  def __init__(self, parent):
    self.__dict__.update(locals())
    self.infixBp = {
      32: 1000,
      82: 1000,
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
    return self.parent.sym
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
    tree = ParseTree( NonTerminal(157, '_direct_declarator') )
    current = self.getCurrentToken()
    if not current:
      return tree
    elif current.getId() in [32]:
      tree.astTransform = AstTransformSubstitution(1)
      tree.nudMorphemeCount = 3
      tree.add( self.expect(32) )
      tree.add( self.parent.parse_declarator() )
      tree.add( self.expect(16) )
    elif current.getId() in [76]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      return self.expect( 76 )
    return tree
  def led(self, left):
    tree = ParseTree( NonTerminal(157, '_direct_declarator') )
    current = self.getCurrentToken()
    if current.getId() == 32: # 'lparen'
      tree.astTransform = AstTransformNodeCreator('FunctionSignature', {'params': 2, 'declarator': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(32) )
      tree.add( self.parent.parse_direct_declarator_parameter_list() )
      tree.add( self.expect(16) )
    elif current.getId() == 82: # 'lsquare'
      tree.astTransform = AstTransformNodeCreator('Array', {'name': 0, 'size': 2})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(82) )
      tree.add( self.parent.parse_direct_declarator_expr() )
      tree.add( self.expect(68) )
    return tree
class ExpressionParser__direct_abstract_declarator:
  def __init__(self, parent):
    self.__dict__.update(locals())
    self.infixBp = {
      32: 1000,
      82: 1000,
    }
    self.prefixBp = {
      32: 2000,
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
    return self.parent.sym
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
    tree = ParseTree( NonTerminal(243, '_direct_abstract_declarator') )
    current = self.getCurrentToken()
    if not current:
      return tree
    if current.getId() in [32]:
      tree.astTransform = AstTransformSubstitution(1)
      tree.nudMorphemeCount = 3
      tree.add( self.expect(32) )
      tree.add( self.parent.parse_abstract_declarator() )
      tree.add( self.expect(16) )
    elif current.getId() in [32, -1, 112]:
      tree.astTransform = AstTransformNodeCreator('AbstractFunction', {'object': 0, 'params': 2})
      tree.nudMorphemeCount = 1
      tree.add( self.parent.parse_direct_abstract_declarator_opt() )
    elif current.getId() in [32, -1, 112]:
      tree.astTransform = AstTransformNodeCreator('AbstractArray', {'object': 0, 'size': 2})
      tree.nudMorphemeCount = 1
      tree.add( self.parent.parse_direct_abstract_declarator_opt() )
    return tree
  def led(self, left):
    tree = ParseTree( NonTerminal(243, '_direct_abstract_declarator') )
    current = self.getCurrentToken()
    if current.getId() == 82: # 'lsquare'
      tree.astTransform = AstTransformNodeCreator('AbstractArray', {'object': 0, 'size': 2})
      if left:
        tree.add(left)
      tree.add( self.expect(82) )
      tree.add( self.parent.parse_direct_abstract_declarator_expr() )
      tree.add( self.expect(68) )
    elif current.getId() == 32: # 'lparen'
      tree.astTransform = AstTransformNodeCreator('AbstractFunction', {'object': 0, 'params': 2})
      if left:
        tree.add(left)
      tree.add( self.expect(32) )
      tree.add( self.parent.parse__gen42() )
      tree.add( self.expect(16) )
    return tree
class Parser:
  # Quark - finite string set maps one string to exactly one int, and vice versa
  terminals = {
    0: 'while',
    1: 'sizeof',
    2: 'static',
    3: 'or',
    4: 'break',
    5: 'lbrace',
    6: 'bitand',
    7: 'do',
    8: 'semi',
    9: 'lt',
    10: 'diveq',
    11: 'else_if',
    12: 'for',
    13: 'bitoreq',
    14: 'struct',
    15: 'const',
    16: 'rparen',
    17: 'char',
    18: 'poundpound',
    19: 'goto',
    20: 'rshifteq',
    21: 'restrict',
    22: 'rbrace',
    23: 'comma',
    24: 'universal_character_name',
    25: 'bitnot',
    26: 'colon',
    27: 'volatile',
    28: 'int',
    29: 'and',
    30: 'neq',
    31: 'modeq',
    32: 'lparen',
    33: 'addeq',
    34: 'not',
    35: 'integer_constant',
    36: 'endif',
    37: 'subeq',
    38: 'register',
    39: 'inline',
    40: 'gt',
    41: 'union',
    42: 'return',
    43: 'defined',
    44: 'float',
    45: 'ampersand',
    46: 'floating_constant',
    47: 'assign',
    48: 'string_literal',
    49: 'double',
    50: 'sizeof_separator',
    51: 'lshifteq',
    52: 'case',
    53: 'bitor',
    54: 'exclamation_point',
    55: 'long',
    56: 'signed',
    57: 'div',
    58: 'character_constant',
    59: 'typedef_identifier',
    60: 'gteq',
    61: 'default',
    62: 'pound',
    63: 'unsigned',
    64: 'defined_separator',
    65: 'decimal_floating_constant',
    66: 'switch',
    67: 'enumeration_constant',
    68: 'rsquare',
    69: 'label_hint',
    70: 'bitandeq',
    71: 'imaginary',
    72: 'lteq',
    73: 'function_definition_hint',
    74: 'hexadecimal_floating_constant',
    75: 'asterisk',
    76: 'identifier',
    77: 'mod',
    78: '_expr',
    79: 'external_declaration_hint',
    80: '_expr_sans_comma',
    81: 'enum',
    82: 'lsquare',
    83: '_direct_declarator',
    84: 'typedef',
    85: 'short',
    86: 'bitxoreq',
    87: 'declarator_hint',
    88: 'complex',
    89: 'auto',
    90: 'questionmark',
    91: 'comma_va_args',
    92: 'dot',
    93: 'lparen_cast',
    94: 'trailing_comma',
    95: 'extern',
    96: 'arrow',
    97: 'else',
    98: 'void',
    99: 'function_prototype_hint',
    100: 'lshift',
    101: 'decr',
    102: 'rshift',
    103: 'pp_number',
    104: 'continue',
    105: 'elipsis',
    106: 'tilde',
    107: 'bool',
    108: 'add',
    109: 'eq',
    110: 'sub',
    111: 'incr',
    112: '_direct_abstract_declarator',
    113: 'muleq',
    114: 'bitxor',
    115: 'if',
    'while': 0,
    'sizeof': 1,
    'static': 2,
    'or': 3,
    'break': 4,
    'lbrace': 5,
    'bitand': 6,
    'do': 7,
    'semi': 8,
    'lt': 9,
    'diveq': 10,
    'else_if': 11,
    'for': 12,
    'bitoreq': 13,
    'struct': 14,
    'const': 15,
    'rparen': 16,
    'char': 17,
    'poundpound': 18,
    'goto': 19,
    'rshifteq': 20,
    'restrict': 21,
    'rbrace': 22,
    'comma': 23,
    'universal_character_name': 24,
    'bitnot': 25,
    'colon': 26,
    'volatile': 27,
    'int': 28,
    'and': 29,
    'neq': 30,
    'modeq': 31,
    'lparen': 32,
    'addeq': 33,
    'not': 34,
    'integer_constant': 35,
    'endif': 36,
    'subeq': 37,
    'register': 38,
    'inline': 39,
    'gt': 40,
    'union': 41,
    'return': 42,
    'defined': 43,
    'float': 44,
    'ampersand': 45,
    'floating_constant': 46,
    'assign': 47,
    'string_literal': 48,
    'double': 49,
    'sizeof_separator': 50,
    'lshifteq': 51,
    'case': 52,
    'bitor': 53,
    'exclamation_point': 54,
    'long': 55,
    'signed': 56,
    'div': 57,
    'character_constant': 58,
    'typedef_identifier': 59,
    'gteq': 60,
    'default': 61,
    'pound': 62,
    'unsigned': 63,
    'defined_separator': 64,
    'decimal_floating_constant': 65,
    'switch': 66,
    'enumeration_constant': 67,
    'rsquare': 68,
    'label_hint': 69,
    'bitandeq': 70,
    'imaginary': 71,
    'lteq': 72,
    'function_definition_hint': 73,
    'hexadecimal_floating_constant': 74,
    'asterisk': 75,
    'identifier': 76,
    'mod': 77,
    '_expr': 78,
    'external_declaration_hint': 79,
    '_expr_sans_comma': 80,
    'enum': 81,
    'lsquare': 82,
    '_direct_declarator': 83,
    'typedef': 84,
    'short': 85,
    'bitxoreq': 86,
    'declarator_hint': 87,
    'complex': 88,
    'auto': 89,
    'questionmark': 90,
    'comma_va_args': 91,
    'dot': 92,
    'lparen_cast': 93,
    'trailing_comma': 94,
    'extern': 95,
    'arrow': 96,
    'else': 97,
    'void': 98,
    'function_prototype_hint': 99,
    'lshift': 100,
    'decr': 101,
    'rshift': 102,
    'pp_number': 103,
    'continue': 104,
    'elipsis': 105,
    'tilde': 106,
    'bool': 107,
    'add': 108,
    'eq': 109,
    'sub': 110,
    'incr': 111,
    '_direct_abstract_declarator': 112,
    'muleq': 113,
    'bitxor': 114,
    'if': 115,
  }
  # Quark - finite string set maps one string to exactly one int, and vice versa
  nonterminals = {
    116: '_expr_sans_comma',
    117: '_gen23',
    118: 'parameter_declaration_sub',
    119: 'expression_opt',
    120: 'struct_declarator_body',
    121: '_gen12',
    122: '_gen13',
    123: 'enum_specifier',
    124: 'direct_declarator_expr',
    125: '_gen21',
    126: 'for_init',
    127: '_gen8',
    128: 'enum_specifier_sub',
    129: 'for_incr',
    130: 'direct_abstract_declarator_opt',
    131: 'parameter_declaration_sub_sub',
    132: 'trailing_comma_opt',
    133: '_gen16',
    134: 'storage_class_specifier',
    135: 'external_function',
    136: 'designation',
    137: '_gen14',
    138: '_gen33',
    139: '_gen25',
    140: 'else_if_statement_list',
    141: 'pointer_sub',
    142: 'type_qualifier',
    143: 'identifier',
    144: 'enum_specifier_body',
    145: '_gen40',
    146: '_gen22',
    147: '_gen15',
    148: 'initializer_list_item',
    149: 'struct_declaration',
    150: 'parameter_type_list',
    151: 'translation_unit',
    152: '_gen9',
    153: '_gen10',
    154: 'external_declaration',
    155: 'struct_declarator',
    156: '_gen0',
    157: '_direct_declarator',
    158: '_gen29',
    159: 'declaration_list',
    160: 'specifier_qualifier',
    161: '_gen18',
    162: '_gen24',
    163: 'direct_declarator_modifier_list_opt',
    164: 'direct_declarator_size',
    165: 'typedef_name',
    166: '_gen41',
    167: 'declarator_initializer',
    168: '_gen11',
    169: '_gen19',
    170: '_gen20',
    171: '_gen34',
    172: 'direct_declarator_modifier',
    173: 'designator',
    174: '_gen26',
    175: 'enumeration_constant',
    176: 'enumerator_assignment',
    177: 'static_opt',
    178: 'declaration_specifier',
    179: '_gen39',
    180: 'initializer',
    181: 'type_specifier',
    182: 'function_specifier',
    183: 'type_name',
    184: 'init_declarator_list',
    185: 'external_declaration_sub',
    186: '_gen32',
    187: '_gen1',
    188: 'keyword',
    189: 'else_statement',
    190: 'block_item',
    191: '_gen36',
    192: 'struct_or_union_sub',
    193: '_gen2',
    194: 'misc',
    195: '_gen17',
    196: 'constant',
    197: 'external_declaration_sub_sub',
    198: 'statement',
    199: '_gen3',
    200: '_gen4',
    201: 'direct_declarator_parameter_list',
    202: 'punctuator',
    203: 'parameter_declaration',
    204: 'struct_specifier',
    205: '_gen27',
    206: '_gen28',
    207: 'pointer',
    208: 'labeled_statement',
    209: 'sizeof_body',
    210: '_gen42',
    211: 'external_declarator',
    212: 'iteration_statement',
    213: '_gen37',
    214: 'va_args',
    215: 'enumerator',
    216: 'expression_statement',
    217: 'external_prototype',
    218: 'selection_statement',
    219: 'direct_abstract_declarator_expr',
    220: '_gen38',
    221: 'declarator',
    222: 'abstract_declarator',
    223: '_gen5',
    224: 'token',
    225: 'jump_statement',
    226: 'union_specifier',
    227: '_gen30',
    228: '_gen31',
    229: 'pp',
    230: 'init_declarator',
    231: 'type_qualifier_list_opt',
    232: '_gen6',
    233: 'pointer_opt',
    234: 'block_item_list',
    235: '_expr',
    236: '_gen35',
    237: 'struct_or_union_body',
    238: 'compound_statement',
    239: 'declaration',
    240: 'else_if_statement',
    241: '_gen7',
    242: 'for_cond',
    243: '_direct_abstract_declarator',
    '_expr_sans_comma': 116,
    '_gen23': 117,
    'parameter_declaration_sub': 118,
    'expression_opt': 119,
    'struct_declarator_body': 120,
    '_gen12': 121,
    '_gen13': 122,
    'enum_specifier': 123,
    'direct_declarator_expr': 124,
    '_gen21': 125,
    'for_init': 126,
    '_gen8': 127,
    'enum_specifier_sub': 128,
    'for_incr': 129,
    'direct_abstract_declarator_opt': 130,
    'parameter_declaration_sub_sub': 131,
    'trailing_comma_opt': 132,
    '_gen16': 133,
    'storage_class_specifier': 134,
    'external_function': 135,
    'designation': 136,
    '_gen14': 137,
    '_gen33': 138,
    '_gen25': 139,
    'else_if_statement_list': 140,
    'pointer_sub': 141,
    'type_qualifier': 142,
    'identifier': 143,
    'enum_specifier_body': 144,
    '_gen40': 145,
    '_gen22': 146,
    '_gen15': 147,
    'initializer_list_item': 148,
    'struct_declaration': 149,
    'parameter_type_list': 150,
    'translation_unit': 151,
    '_gen9': 152,
    '_gen10': 153,
    'external_declaration': 154,
    'struct_declarator': 155,
    '_gen0': 156,
    '_direct_declarator': 157,
    '_gen29': 158,
    'declaration_list': 159,
    'specifier_qualifier': 160,
    '_gen18': 161,
    '_gen24': 162,
    'direct_declarator_modifier_list_opt': 163,
    'direct_declarator_size': 164,
    'typedef_name': 165,
    '_gen41': 166,
    'declarator_initializer': 167,
    '_gen11': 168,
    '_gen19': 169,
    '_gen20': 170,
    '_gen34': 171,
    'direct_declarator_modifier': 172,
    'designator': 173,
    '_gen26': 174,
    'enumeration_constant': 175,
    'enumerator_assignment': 176,
    'static_opt': 177,
    'declaration_specifier': 178,
    '_gen39': 179,
    'initializer': 180,
    'type_specifier': 181,
    'function_specifier': 182,
    'type_name': 183,
    'init_declarator_list': 184,
    'external_declaration_sub': 185,
    '_gen32': 186,
    '_gen1': 187,
    'keyword': 188,
    'else_statement': 189,
    'block_item': 190,
    '_gen36': 191,
    'struct_or_union_sub': 192,
    '_gen2': 193,
    'misc': 194,
    '_gen17': 195,
    'constant': 196,
    'external_declaration_sub_sub': 197,
    'statement': 198,
    '_gen3': 199,
    '_gen4': 200,
    'direct_declarator_parameter_list': 201,
    'punctuator': 202,
    'parameter_declaration': 203,
    'struct_specifier': 204,
    '_gen27': 205,
    '_gen28': 206,
    'pointer': 207,
    'labeled_statement': 208,
    'sizeof_body': 209,
    '_gen42': 210,
    'external_declarator': 211,
    'iteration_statement': 212,
    '_gen37': 213,
    'va_args': 214,
    'enumerator': 215,
    'expression_statement': 216,
    'external_prototype': 217,
    'selection_statement': 218,
    'direct_abstract_declarator_expr': 219,
    '_gen38': 220,
    'declarator': 221,
    'abstract_declarator': 222,
    '_gen5': 223,
    'token': 224,
    'jump_statement': 225,
    'union_specifier': 226,
    '_gen30': 227,
    '_gen31': 228,
    'pp': 229,
    'init_declarator': 230,
    'type_qualifier_list_opt': 231,
    '_gen6': 232,
    'pointer_opt': 233,
    'block_item_list': 234,
    '_expr': 235,
    '_gen35': 236,
    'struct_or_union_body': 237,
    'compound_statement': 238,
    'declaration': 239,
    'else_if_statement': 240,
    '_gen7': 241,
    'for_cond': 242,
    '_direct_abstract_declarator': 243,
  }
  # table[nonterminal][terminal] = rule
  table = [
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 267, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 282, -1, -1, -1, -1, -1, -1, -1, -1, 282, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 282, 282, -1, -1, -1, -1, -1, -1, 282, -1, -1, -1, -1, -1, -1, -1, 282, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 282, -1, -1, -1],
    [-1, 219, -1, -1, -1, -1, 219, -1, 371, -1, -1, -1, -1, -1, -1, -1, 371, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 219, -1, -1, 219, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 219, -1, 219, -1, -1, -1, -1, -1, -1, -1, -1, -1, 219, -1, -1, -1, -1, -1, -1, 219, -1, 219, -1, -1, -1, -1, -1, -1, 219, 219, 219, -1, 219, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 219, -1, -1, -1, -1, -1, -1, -1, 219, -1, -1, -1, -1, -1, -1, -1, -1, -1, 219, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 46, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, 92, -1, -1, -1, 92, 92, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 92, -1, -1, 92, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 92, 92, 92, -1, -1, -1, -1, -1, -1, -1, -1, -1, 92, -1, -1, -1, -1, -1, -1, 92, -1, 92, -1, -1, -1, -1, -1, -1, 92, 92, 92, -1, -1, -1, 92, -1, 92, -1, -1, -1, -1, -1, -1, -1, -1, -1, 92, 92, -1, -1, -1, -1, -1, -1, -1, 92, -1, -1, -1, -1, -1, -1, -1, -1, -1, 92, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 108, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 123, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 244, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, 56, 56, -1, -1, -1, 56, -1, -1, -1, -1, -1, -1, -1, -1, 56, -1, -1, -1, -1, -1, 56, -1, -1, -1, -1, -1, 56, -1, -1, -1, -1, 56, -1, -1, 56, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 56, -1, 56, -1, -1, -1, -1, -1, -1, -1, -1, -1, 56, -1, -1, -1, -1, -1, -1, 56, -1, 56, -1, -1, -1, -1, -1, -1, 56, 56, 56, -1, 56, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 56, -1, -1, -1, -1, -1, -1, -1, 56, -1, -1, -1, -1, -1, -1, -1, -1, -1, 56, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, 135, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 135, -1, -1, 206, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, 28, 14, -1, -1, -1, 28, -1, 195, -1, -1, -1, -1, -1, 14, 14, -1, 14, -1, -1, -1, 14, -1, -1, -1, -1, -1, 14, 14, -1, -1, -1, 28, -1, -1, 28, -1, -1, 14, 14, -1, 14, -1, -1, 14, -1, 28, -1, 28, 14, -1, -1, -1, -1, -1, 14, 14, -1, 28, 14, -1, -1, -1, 14, -1, 28, -1, 28, -1, -1, -1, 14, -1, -1, 28, 28, 28, -1, 28, -1, -1, 14, -1, -1, 14, 14, -1, -1, 14, 14, -1, -1, -1, 28, -1, 14, -1, -1, 14, -1, -1, 28, -1, -1, -1, -1, -1, 14, -1, -1, -1, 28, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, 22, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 395, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 395, 395, -1, -1, -1, -1, -1, -1, 395, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, 196, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 346, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, 248, -1, -1, -1, -1, -1, -1, -1, 129, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 336, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 336, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 375, -1, -1, -1, -1, -1, -1, -1, -1, 316, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 316, -1, -1, -1, -1, -1, -1, 316, -1, -1, -1, -1, -1, -1, -1, 375, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 375, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 312, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 390, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 122, -1, -1, 35, -1, -1, 122, -1, -1, -1, -1, -1, 122, 122, -1, 122, -1, -1, -1, 122, -1, 122, -1, -1, 122, 122, 122, -1, -1, -1, 122, -1, -1, -1, -1, -1, 122, 122, -1, 122, -1, -1, 122, -1, -1, -1, -1, 122, -1, -1, -1, -1, -1, 122, 122, -1, -1, 122, -1, -1, -1, 122, -1, -1, -1, -1, -1, -1, -1, 122, -1, 122, -1, 122, 122, -1, -1, -1, -1, 122, -1, 122, 122, 122, -1, 122, 122, 122, -1, 122, -1, -1, -1, 122, -1, -1, 122, 122, -1, -1, -1, -1, -1, -1, -1, 122, -1, -1, -1, -1, 122, -1, -1, -1],
    [-1, -1, 74, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 292, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 247, -1, -1, -1, -1, 175, -1, -1, -1, -1, -1, 298, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 285, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 80, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 80, -1, -1, -1, -1, -1, -1, -1, -1, -1, 80, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, 112, -1, -1, -1, 112, 112, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 112, -1, -1, 112, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 112, 208, 112, -1, -1, -1, -1, -1, -1, -1, -1, -1, 112, -1, -1, -1, -1, -1, -1, 112, -1, 112, -1, -1, -1, -1, -1, -1, 112, 112, 112, -1, -1, -1, 112, -1, 208, -1, -1, -1, -1, -1, -1, -1, -1, -1, 208, 112, -1, -1, -1, -1, -1, -1, -1, 112, -1, -1, -1, -1, -1, -1, -1, -1, -1, 112, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 37, -1, -1, -1, -1, -1, -1, -1, -1, 37, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 37, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 37, -1, -1, -1],
    [-1, -1, 43, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 38, -1, -1, -1, -1, -1, 38, -1, 43, -1, -1, -1, 38, -1, -1, -1, -1, 43, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 43, 43, -1, -1, -1, -1, -1, -1, 43, -1, -1, -1, -1, -1, -1, -1, 43, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 43, -1, -1, -1],
    [393, 393, 393, -1, 393, 393, 393, 393, 393, -1, -1, 393, 393, -1, 393, 393, -1, 393, -1, 393, -1, 393, 393, -1, -1, -1, -1, 393, 393, -1, -1, -1, 393, -1, -1, 393, 393, -1, 393, 393, -1, 393, 393, -1, 393, -1, 393, -1, 393, 393, -1, -1, 393, -1, -1, 393, 393, -1, 393, 393, -1, 393, -1, 393, -1, 393, 393, 393, -1, 393, -1, 393, -1, -1, 393, 393, 393, -1, 393, -1, -1, 393, -1, -1, 393, 393, -1, -1, 393, 393, -1, -1, -1, 393, -1, 393, -1, 393, 393, -1, -1, 393, -1, -1, 393, -1, -1, 393, -1, -1, -1, 393, -1, -1, -1, 393],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 242, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 325, -1, -1, -1, -1, -1, 27, -1, -1, -1, -1, -1, 194, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 85, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, 189, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, 98, -1, -1, -1, -1, 98, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 98, -1, -1, 98, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 98, -1, 98, -1, -1, -1, -1, -1, -1, -1, -1, -1, 98, -1, -1, -1, -1, -1, -1, 98, -1, 98, -1, -1, -1, -1, -1, -1, 98, 98, 98, -1, -1, -1, 98, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 98, -1, -1, -1, -1, -1, -1, -1, 98, -1, -1, -1, -1, -1, -1, -1, -1, -1, 98, -1, -1, -1, -1],
    [-1, -1, 241, -1, -1, 238, -1, -1, 241, -1, -1, -1, -1, -1, 241, 241, -1, 241, -1, -1, -1, 241, -1, 241, -1, -1, 241, 241, 241, -1, -1, -1, 241, -1, -1, -1, -1, -1, 241, 241, -1, 241, -1, -1, 241, -1, -1, -1, -1, 241, -1, -1, -1, -1, -1, 241, 241, -1, -1, 241, -1, -1, -1, 241, -1, -1, -1, -1, -1, -1, -1, 241, -1, 241, -1, 241, 241, -1, -1, -1, -1, 241, -1, 241, 241, 241, -1, 241, 241, 241, -1, 241, -1, -1, -1, 241, -1, -1, 241, 241, -1, -1, -1, -1, -1, -1, -1, 241, -1, -1, -1, -1, 241, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 73, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 383, -1, -1, -1, -1, -1, -1, -1, -1, -1, 383, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, 97, -1, -1, -1, 97, 97, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 97, -1, -1, 97, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 97, 97, 97, -1, -1, -1, -1, -1, -1, -1, -1, -1, 97, -1, -1, -1, -1, -1, -1, 97, -1, 97, -1, -1, -1, -1, -1, -1, 97, 97, 97, -1, -1, -1, 97, -1, 97, -1, -1, -1, -1, -1, -1, -1, -1, -1, 97, 97, -1, -1, -1, -1, -1, -1, -1, 97, -1, -1, -1, -1, -1, -1, -1, -1, -1, 97, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 409, 409, -1, 409, -1, -1, -1, 409, -1, -1, -1, -1, 409, 409, 409, -1, -1, -1, 409, -1, -1, -1, -1, -1, -1, -1, -1, 409, -1, -1, 409, -1, -1, -1, -1, 409, -1, -1, -1, -1, -1, 409, 409, -1, -1, 409, -1, -1, -1, 409, -1, -1, -1, -1, -1, -1, -1, 409, -1, -1, -1, 409, 409, -1, -1, -1, -1, 409, -1, 409, -1, 409, -1, -1, 409, -1, -1, -1, -1, -1, -1, -1, -1, -1, 409, -1, -1, -1, -1, -1, -1, -1, -1, 409, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 20, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 20, 20, -1, 20, -1, -1, -1, 20, -1, -1, -1, -1, -1, 20, 20, -1, -1, -1, -1, -1, -1, -1, -1, -1, 20, 20, -1, 20, -1, -1, 20, -1, -1, -1, -1, 20, -1, -1, -1, -1, -1, 20, 20, -1, -1, 20, -1, -1, -1, 20, -1, -1, -1, -1, -1, -1, -1, 20, -1, -1, -1, -1, -1, -1, -1, -1, -1, 20, -1, -1, 20, 20, -1, -1, 20, 20, -1, -1, -1, -1, -1, 20, -1, -1, 20, -1, -1, -1, -1, -1, -1, -1, -1, 20, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 100, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 65, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 65, 65, -1, -1, -1, -1, -1, -1, 65, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, 71, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 404, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 318, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 351, -1, -1, -1, -1, -1, 19, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 19, 19, -1, -1, -1, -1, -1, -1, 19, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 144, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 164, -1, -1, 164, -1, -1, 164, -1, -1, -1, -1, -1, 164, 164, -1, 164, -1, -1, -1, 164, -1, 164, -1, -1, -1, 164, 164, -1, -1, -1, -1, -1, -1, -1, -1, -1, 164, 164, -1, 164, -1, -1, 164, -1, -1, -1, -1, 164, -1, -1, -1, -1, -1, 164, 164, -1, -1, 164, -1, -1, -1, 164, -1, -1, -1, -1, -1, -1, -1, 164, -1, -1, -1, -1, -1, -1, -1, -1, -1, 164, -1, -1, 164, 164, -1, -1, 164, 164, -1, -1, -1, -1, -1, 164, -1, -1, 164, -1, -1, -1, -1, -1, -1, -1, -1, 164, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 382, 153, -1, 382, -1, -1, -1, 153, -1, -1, -1, -1, -1, 153, 382, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 382, -1, -1, 382, -1, -1, -1, -1, 382, -1, -1, -1, -1, -1, 382, 382, -1, -1, 382, -1, -1, -1, 382, -1, -1, -1, -1, -1, -1, -1, 382, -1, -1, -1, -1, -1, -1, -1, -1, -1, 382, -1, -1, -1, 382, -1, -1, 382, -1, -1, -1, -1, -1, -1, -1, -1, -1, 382, -1, -1, -1, -1, -1, -1, -1, -1, 382, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 75, 75, -1, 75, -1, -1, -1, 75, -1, -1, -1, -1, 44, 75, 75, -1, -1, -1, 44, -1, -1, -1, -1, -1, -1, -1, -1, 75, -1, -1, 75, -1, -1, -1, -1, 75, -1, -1, -1, -1, -1, 75, 75, -1, -1, 75, -1, -1, -1, 75, -1, -1, -1, -1, -1, -1, -1, 75, -1, -1, -1, 44, 44, -1, -1, -1, -1, 75, -1, 44, -1, 75, -1, -1, 75, -1, -1, -1, -1, -1, -1, -1, -1, -1, 75, -1, -1, -1, -1, -1, -1, -1, -1, 75, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 271, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 77, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, 53, 53, -1, -1, -1, 53, -1, -1, -1, -1, -1, -1, -1, -1, 53, -1, -1, -1, -1, -1, 53, -1, -1, -1, -1, -1, 53, -1, -1, -1, -1, 53, -1, -1, 53, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 53, -1, 53, -1, -1, -1, -1, -1, -1, -1, -1, -1, 53, -1, -1, -1, -1, -1, -1, 53, -1, 53, -1, -1, -1, -1, -1, -1, 53, 53, 53, -1, 53, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 53, -1, -1, -1, -1, -1, -1, -1, 53, -1, -1, -1, -1, -1, -1, -1, -1, -1, 53, -1, -1, -1, -1],
    [-1, 251, -1, -1, -1, -1, 251, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 251, -1, -1, 251, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 251, -1, 251, -1, -1, -1, -1, -1, -1, -1, -1, -1, 251, -1, -1, -1, -1, -1, -1, 251, -1, 251, -1, -1, -1, -1, -1, -1, 251, 169, 251, -1, 251, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 251, -1, -1, -1, -1, -1, -1, -1, 251, -1, -1, -1, -1, -1, -1, -1, -1, -1, 251, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 171, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 415, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 257, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, 104, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 104, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 84, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 125, -1, -1, -1, -1, -1, 125, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 125, 125, -1, -1, -1, -1, -1, -1, 125, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, 94, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 118, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 79, -1, -1, -1, -1, -1, -1, -1, -1, 79, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 138, 79, -1, -1, -1, -1, -1, -1, 79, -1, -1, -1, -1, -1, -1, -1, 79, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 79, -1, -1, -1],
    [-1, -1, 417, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 96, -1, -1, -1, -1, -1, 96, -1, -1, -1, -1, -1, 96, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 266, -1, -1, -1, -1, -1, -1, -1, -1, -1, 408, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, 143, 93, -1, -1, -1, 143, -1, -1, -1, -1, -1, -1, -1, -1, 93, -1, -1, -1, -1, -1, 93, -1, -1, -1, -1, -1, 93, -1, -1, -1, -1, 143, -1, -1, 143, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 143, -1, 143, -1, -1, -1, -1, -1, -1, -1, -1, -1, 143, -1, -1, -1, -1, -1, -1, 143, -1, 143, -1, -1, -1, -1, -1, -1, 143, 143, 143, -1, 143, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 143, -1, -1, -1, -1, -1, -1, -1, 143, -1, -1, -1, -1, -1, -1, -1, -1, -1, 143, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 50, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 339, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 183, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 339, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, 174, 57, -1, -1, -1, 174, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 174, -1, -1, 174, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 174, -1, 174, -1, -1, -1, -1, -1, -1, -1, -1, -1, 174, -1, -1, -1, -1, -1, -1, 174, -1, 174, -1, -1, -1, -1, -1, -1, 174, 174, 174, -1, 174, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 174, -1, -1, -1, -1, -1, -1, -1, 174, -1, -1, -1, -1, -1, -1, -1, -1, -1, 174, -1, -1, -1, -1],
    [-1, -1, 54, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 82, 103, -1, 82, -1, -1, -1, 103, -1, -1, -1, -1, -1, 103, 82, -1, -1, -1, -1, -1, -1, -1, -1, -1, 54, 261, -1, 82, -1, -1, 82, -1, -1, -1, -1, 82, -1, -1, -1, -1, -1, 82, 82, -1, -1, 82, -1, -1, -1, 82, -1, -1, -1, -1, -1, -1, -1, 82, -1, -1, -1, -1, -1, -1, -1, -1, -1, 82, -1, -1, 54, 82, -1, -1, 82, 54, -1, -1, -1, -1, -1, 54, -1, -1, 82, -1, -1, -1, -1, -1, -1, -1, -1, 82, -1, -1, -1, -1, -1, -1, -1, -1],
    [380, 380, 380, -1, 380, 380, 380, 380, 380, -1, -1, 406, 380, -1, 380, 380, -1, 380, -1, 380, -1, 380, 380, -1, -1, -1, -1, 380, 380, -1, -1, -1, 380, -1, -1, 380, 380, -1, 380, 380, -1, 380, 380, -1, 380, -1, 380, -1, 380, 380, -1, -1, 380, -1, -1, 380, 380, -1, 380, 380, -1, 380, -1, 380, -1, 380, 380, 380, -1, 380, -1, 380, -1, -1, 380, 380, 380, -1, 380, -1, -1, 380, -1, -1, 380, 380, -1, -1, 380, 380, -1, -1, -1, 380, -1, 380, -1, 380, 380, -1, -1, 380, -1, -1, 380, -1, -1, 380, -1, -1, -1, 380, -1, -1, -1, 380],
    [-1, 152, -1, -1, -1, 24, 152, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 152, -1, -1, 152, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 152, -1, 152, -1, -1, -1, -1, -1, -1, -1, -1, -1, 152, -1, -1, -1, -1, -1, -1, 152, -1, 152, -1, -1, -1, -1, -1, -1, 152, 152, 152, -1, -1, -1, 152, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 152, -1, -1, -1, -1, -1, -1, -1, 152, -1, -1, -1, -1, -1, -1, -1, -1, -1, 152, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 412, -1, -1, 348, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 184, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 237, -1, -1, 179, -1, -1, -1, -1, 331, -1, -1, -1, -1, -1, 176, 78, -1, -1, 170, -1, -1, -1, 355, -1, -1, -1, -1, -1, -1, -1, 357, -1, -1, -1, -1, -1, -1, -1, -1, -1, 422, -1, -1, -1, 32, -1, -1, 51, -1, -1, -1, -1, -1, -1, -1, -1, -1, 304, -1, -1, -1, -1, -1, -1, -1, -1, 126, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 3, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 342, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 345, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 141, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 141, 141, -1, -1, -1, -1, -1, -1, 141, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, 166, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 87, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 166, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 166, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 101, -1, -1, -1, -1, -1, -1, -1, -1, 411, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 411, 411, -1, -1, -1, -1, -1, -1, 411, -1, -1, -1, -1, -1, -1, -1, 101, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 411, -1, -1, -1],
    [-1, -1, 199, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 199, 199, -1, 199, -1, -1, -1, 199, -1, -1, -1, -1, -1, 199, 199, -1, -1, -1, -1, -1, -1, -1, -1, -1, 199, 199, -1, 199, -1, -1, 199, -1, -1, -1, -1, 199, -1, -1, -1, -1, -1, 199, 199, -1, -1, 199, -1, -1, -1, 199, -1, -1, -1, -1, -1, -1, -1, 199, -1, -1, -1, -1, -1, -1, -1, -1, -1, 199, -1, -1, 199, 199, -1, -1, 199, 199, -1, -1, -1, -1, -1, 199, -1, -1, 199, -1, -1, -1, -1, -1, -1, -1, -1, 199, -1, -1, -1, -1, -1, -1, -1, -1],
    [191, 230, 231, -1, 254, -1, -1, 90, -1, -1, -1, -1, 305, -1, 228, 203, -1, 330, -1, 134, -1, 204, -1, -1, -1, -1, -1, 185, 30, -1, -1, -1, -1, -1, -1, -1, -1, -1, 64, 205, -1, 149, 5, -1, 341, -1, -1, -1, -1, 264, -1, -1, 302, -1, -1, 15, 260, -1, -1, -1, -1, 343, -1, 215, -1, -1, 227, -1, -1, -1, -1, 397, -1, -1, -1, -1, -1, -1, -1, -1, -1, 99, -1, -1, 202, 91, -1, -1, 356, 233, -1, -1, -1, -1, -1, 62, -1, 420, 229, -1, -1, -1, -1, -1, 295, -1, -1, 276, -1, -1, -1, -1, -1, -1, -1, 6],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 369, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [324, 324, 187, -1, 324, 324, 324, 324, 324, -1, -1, -1, 324, -1, 187, 187, -1, 187, -1, 324, -1, 187, -1, -1, -1, -1, -1, 187, 187, -1, -1, -1, 324, -1, -1, 324, -1, -1, 187, 187, -1, 187, 324, -1, 187, -1, 324, -1, 324, 187, -1, -1, 324, -1, -1, 187, 187, -1, 324, 187, -1, 324, -1, 187, -1, 324, 324, 324, -1, 324, -1, 187, -1, -1, 324, 324, 324, -1, 324, -1, -1, 187, -1, -1, 187, 187, -1, -1, 187, 187, -1, -1, -1, 324, -1, 187, -1, -1, 187, -1, -1, 324, -1, -1, 324, -1, -1, 187, -1, -1, -1, 324, -1, -1, -1, 324],
    [111, 111, 111, -1, 111, 111, 111, 111, 111, -1, -1, -1, 111, -1, 111, 111, -1, 111, -1, 111, -1, 111, 307, -1, -1, -1, -1, 111, 111, -1, -1, -1, 111, -1, -1, 111, -1, -1, 111, 111, -1, 111, 111, -1, 111, -1, 111, -1, 111, 111, -1, -1, 111, -1, -1, 111, 111, -1, 111, 111, -1, 111, -1, 111, -1, 111, 111, 111, -1, 111, -1, 111, -1, -1, 111, 111, 111, -1, 111, -1, -1, 111, -1, -1, 111, 111, -1, -1, 111, 111, -1, -1, -1, 111, -1, 111, -1, -1, 111, -1, -1, 111, -1, -1, 111, -1, -1, 111, -1, -1, -1, 111, -1, -1, -1, 111],
    [-1, -1, -1, -1, -1, 311, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 224, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 286, -1, -1, -1, -1, -1, 421, -1, -1, -1, -1, -1, 286, 286, -1, 286, -1, -1, -1, 286, -1, 421, -1, -1, -1, 286, 286, -1, -1, -1, 421, -1, -1, -1, -1, -1, 286, 286, -1, 286, -1, -1, 286, -1, -1, -1, -1, 286, -1, -1, -1, -1, -1, 286, 286, -1, -1, 286, -1, -1, -1, 286, -1, -1, -1, -1, -1, -1, -1, 286, -1, 421, -1, 421, 421, -1, -1, -1, -1, 286, -1, 421, 286, 286, -1, 421, 286, 286, -1, 421, -1, -1, -1, 286, -1, -1, 286, 421, -1, -1, -1, -1, -1, -1, -1, 286, -1, -1, -1, -1, 421, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 290, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 218, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 329, 329, -1, 329, -1, -1, -1, 329, 352, -1, -1, -1, 329, 329, 329, -1, -1, -1, 329, -1, -1, -1, -1, -1, -1, -1, -1, 329, -1, -1, 329, -1, -1, -1, -1, 329, -1, -1, -1, -1, -1, 329, 329, -1, -1, 329, -1, -1, -1, 329, -1, -1, -1, -1, -1, -1, -1, 329, -1, -1, -1, 329, 329, -1, -1, -1, -1, 329, -1, 329, -1, 329, -1, -1, 329, -1, -1, -1, -1, -1, -1, -1, -1, -1, 329, -1, -1, -1, -1, -1, -1, -1, -1, 329, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 308, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 151, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 49, -1, -1, -1, -1, -1, -1, 81, -1, 33, -1, -1, -1, -1, -1, -1, 297, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 212, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 12, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [41, 281, -1, -1, 317, 59, 281, 41, 281, -1, -1, -1, 41, -1, -1, -1, -1, -1, -1, 317, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 281, -1, -1, 281, -1, -1, -1, -1, -1, -1, 317, -1, -1, -1, 281, -1, 281, -1, -1, -1, 223, -1, -1, -1, -1, -1, 281, -1, -1, 223, -1, -1, -1, 281, 72, 281, -1, 223, -1, -1, -1, -1, 281, 281, 281, -1, 281, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 281, -1, -1, -1, -1, -1, -1, -1, 281, -1, -1, 317, -1, -1, -1, -1, -1, -1, 281, -1, -1, -1, 72],
    [-1, -1, -1, -1, -1, -1, -1, -1, 366, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 319, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 319, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, 326, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 322, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 173, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 173, 173, -1, 173, -1, -1, -1, 173, -1, -1, -1, -1, -1, 173, 173, -1, -1, -1, -1, -1, -1, -1, -1, -1, 173, 173, -1, 173, -1, -1, 173, -1, -1, -1, -1, 173, -1, -1, -1, -1, -1, 173, 173, -1, -1, 173, -1, -1, -1, 173, -1, -1, -1, -1, -1, -1, -1, 173, -1, -1, -1, -1, 68, -1, -1, -1, -1, 173, -1, -1, 173, 173, -1, -1, 173, 173, -1, -1, -1, -1, -1, 173, -1, -1, 173, -1, -1, -1, -1, -1, -1, -1, -1, 173, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, 309, -1, 370, -1, -1, 235, 18, -1, -1, -1, 314, -1, -1, 182, -1, 225, -1, 363, -1, 332, 284, -1, -1, 392, -1, -1, 258, 335, 384, 365, 368, -1, -1, -1, 272, -1, -1, 350, -1, -1, -1, -1, 88, -1, 107, -1, -1, -1, 193, -1, 315, 163, -1, -1, 172, -1, -1, 83, -1, 60, -1, -1, -1, -1, -1, 23, -1, 198, -1, 220, -1, -1, -1, -1, 273, -1, -1, -1, -1, 328, -1, -1, -1, 410, -1, -1, -1, 10, -1, 52, -1, -1, -1, 323, -1, -1, -1, 333, 31, 403, -1, -1, 39, 55, -1, 278, 42, 156, 222, -1, 114, 287, -1],
    [-1, -1, 216, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 216, 216, -1, 216, -1, -1, -1, 216, -1, -1, -1, -1, -1, 216, 216, -1, -1, -1, -1, -1, -1, -1, -1, -1, 216, 216, -1, 216, -1, -1, 216, -1, -1, -1, -1, 216, -1, -1, -1, -1, -1, 216, 216, -1, -1, 216, -1, -1, -1, 216, -1, -1, -1, -1, -1, -1, -1, 216, -1, -1, -1, -1, -1, -1, -1, -1, -1, 216, -1, -1, 216, 216, -1, -1, 216, 216, -1, -1, -1, -1, -1, 216, -1, -1, 216, -1, -1, -1, -1, -1, -1, -1, -1, 216, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 7, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 131, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 131, 131, -1, 131, -1, -1, -1, 131, -1, -1, -1, -1, -1, 131, 131, -1, -1, -1, -1, -1, -1, -1, -1, -1, 131, 131, -1, 131, -1, -1, 131, -1, -1, -1, -1, 131, -1, -1, -1, -1, -1, 131, 131, -1, -1, 131, -1, -1, -1, 131, -1, -1, -1, -1, -1, -1, -1, 131, -1, -1, -1, -1, -1, -1, -1, -1, -1, 131, -1, -1, 131, 131, -1, -1, 131, 131, -1, -1, -1, -1, -1, 131, -1, -1, 131, -1, -1, -1, -1, -1, -1, -1, -1, 131, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 133, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 36, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 29, -1, -1, -1, -1, -1, -1, -1, -1, 29, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 29, 29, -1, -1, -1, -1, -1, -1, 29, -1, -1, -1, -1, -1, -1, -1, 29, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 29, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 301, -1, -1, -1, -1, -1, -1, -1, -1, 16, -1, -1, -1, -1, -1, -1, -1, 399, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 110, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 154, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 157, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 157, 157, -1, 157, -1, -1, -1, 157, -1, -1, -1, -1, -1, 157, 157, -1, -1, -1, -1, -1, -1, -1, -1, -1, 157, 157, -1, 157, -1, -1, 157, -1, -1, -1, -1, 157, -1, -1, -1, -1, -1, 157, 157, -1, -1, 157, -1, -1, -1, 157, -1, -1, -1, -1, -1, -1, -1, 157, -1, -1, -1, -1, -1, -1, -1, -1, -1, 157, -1, -1, 157, 157, -1, -1, 157, 157, -1, -1, -1, -1, -1, 157, -1, -1, 157, -1, -1, -1, -1, -1, -1, -1, -1, 157, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 70, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [310, -1, -1, -1, -1, -1, -1, 158, -1, -1, -1, -1, 11, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [0, 0, 0, -1, 0, 0, 0, 0, 0, -1, -1, 0, 0, -1, 0, 0, -1, 0, -1, 0, -1, 0, 0, -1, -1, -1, -1, 0, 0, -1, -1, -1, 0, -1, -1, 0, 0, -1, 0, 0, -1, 0, 0, -1, 0, -1, 0, -1, 0, 0, -1, -1, 0, -1, -1, 0, 0, -1, 0, 0, -1, 0, -1, 0, -1, 0, 0, 0, -1, 0, -1, 0, -1, -1, 0, 0, 0, -1, 0, -1, -1, 0, -1, -1, 0, 0, -1, -1, 0, 0, -1, -1, -1, 0, -1, 0, -1, 0, 0, -1, -1, 0, -1, -1, 0, -1, -1, 0, -1, -1, -1, 0, -1, -1, -1, 0],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 119, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 243, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, 95, -1, -1, -1, -1, 95, -1, 95, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 95, -1, -1, 95, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 95, -1, 95, -1, -1, -1, -1, -1, -1, -1, -1, -1, 95, -1, -1, -1, -1, -1, -1, 95, -1, 95, -1, -1, -1, -1, -1, -1, 95, 95, 95, -1, 95, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 95, -1, -1, -1, -1, -1, -1, -1, 95, -1, -1, -1, -1, -1, -1, -1, -1, -1, 95, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 387, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 299, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 21],
    [-1, 250, 250, -1, -1, -1, 250, -1, -1, -1, -1, -1, -1, -1, -1, 250, -1, -1, -1, -1, -1, 250, -1, -1, -1, -1, -1, 250, -1, -1, -1, -1, 250, -1, -1, 250, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 250, -1, 250, -1, -1, -1, -1, -1, -1, -1, -1, -1, 250, -1, -1, -1, -1, -1, -1, 250, -1, 250, -1, -1, -1, -1, -1, -1, 250, 250, 250, -1, 250, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 250, -1, -1, -1, -1, -1, -1, -1, 250, -1, -1, -1, -1, -1, -1, -1, -1, -1, 250, -1, -1, -1, -1],
    [9, 9, 9, -1, 9, 9, 9, 9, 9, -1, -1, -1, 9, -1, 9, 9, -1, 9, -1, 9, -1, 9, 9, -1, -1, -1, -1, 9, 9, -1, -1, -1, 9, -1, -1, 9, 9, -1, 9, 9, -1, 9, 9, -1, 9, -1, 9, -1, 9, 9, -1, -1, 9, -1, -1, 9, 9, -1, 9, 9, -1, 9, -1, 9, -1, 9, 9, 9, -1, 9, -1, 9, -1, -1, 9, 9, 9, -1, 9, -1, -1, 9, -1, -1, 9, 9, -1, -1, 9, 9, -1, -1, -1, 9, -1, 9, -1, 128, 9, -1, -1, 9, -1, -1, 9, -1, -1, 9, -1, -1, -1, 9, -1, -1, -1, 9],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 379, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 379, 379, -1, -1, -1, -1, -1, -1, 379, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 340, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 340, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 340, -1, -1, -1],
    [-1, -1, 364, -1, -1, 105, -1, -1, 105, -1, -1, -1, -1, -1, 364, 364, -1, 364, -1, -1, -1, 364, -1, 105, -1, -1, -1, 364, 364, -1, -1, -1, -1, -1, -1, -1, -1, -1, 364, 364, -1, 364, -1, -1, 364, -1, -1, -1, -1, 364, -1, -1, -1, -1, -1, 364, 364, -1, -1, 364, -1, -1, -1, 364, -1, -1, -1, -1, -1, -1, -1, 364, -1, -1, -1, -1, -1, -1, -1, -1, -1, 364, -1, -1, 364, 364, -1, -1, 364, 364, -1, -1, -1, -1, -1, 364, -1, -1, 364, -1, -1, -1, -1, -1, -1, -1, -1, 364, -1, -1, -1, -1, -1, -1, -1, -1],
    [294, 294, 294, 263, 294, 263, -1, 294, 263, 263, -1, -1, 294, 263, 294, 294, 263, 294, 263, 294, 263, 294, 263, 263, -1, -1, 263, 294, 294, 263, 263, 263, 263, 263, -1, 400, -1, 263, 294, 294, 263, 294, 294, -1, 294, 263, 400, 263, 45, 294, -1, 263, 294, 263, 263, 294, 294, 263, 400, -1, 263, 294, 263, 294, -1, 400, 294, 400, 263, -1, 263, 294, 263, -1, 400, -1, 76, 263, -1, -1, -1, 294, 263, -1, 294, 294, 263, -1, 294, 294, 263, -1, 263, -1, -1, 294, 263, 294, 294, -1, 263, 263, 263, 306, 294, 263, 263, 294, 263, 263, 263, 263, -1, 263, 263, 294],
    [-1, -1, -1, -1, 405, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 358, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 337, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 8, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 259, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 162, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 165, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 394, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 372, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 66, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 270, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 270, 270, -1, -1, -1, -1, -1, -1, 270, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 145, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 145, -1, -1, -1, -1, -1, 145, -1, 145, -1, -1, -1, 145, -1, -1, -1, -1, 145, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 145, 145, -1, -1, -1, -1, -1, -1, 145, -1, -1, -1, -1, -1, -1, -1, 145, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 145, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, 253, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 253, -1, -1, -1, -1, -1, -1, -1, -1, 389, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 389, 389, -1, -1, -1, -1, -1, -1, 389, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 86, -1, -1, -1, -1, -1, -1, -1, -1, 86, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 249, 86, -1, -1, -1, -1, -1, -1, 86, -1, -1, -1, -1, -1, -1, -1, 86, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 86, -1, -1, -1],
    [207, 207, 207, -1, 207, 207, 207, 207, 207, -1, -1, -1, 207, -1, 207, 207, -1, 207, -1, 207, -1, 207, 207, -1, -1, -1, -1, 207, 207, -1, -1, -1, 207, -1, -1, 207, -1, -1, 207, 207, -1, 207, 207, -1, 207, -1, 207, -1, 207, 207, -1, -1, 207, -1, -1, 207, 207, -1, 207, 207, -1, 207, -1, 207, -1, 207, 207, 207, -1, 207, -1, 207, -1, -1, 207, 207, 207, -1, 207, -1, -1, 207, -1, -1, 207, 207, -1, -1, 207, 207, -1, -1, -1, 207, -1, 207, -1, -1, 207, -1, -1, 207, -1, -1, 207, -1, -1, 207, -1, -1, -1, 207, -1, -1, -1, 207],
    [-1, 239, -1, -1, -1, 239, 239, -1, 213, -1, -1, -1, -1, -1, -1, -1, 213, -1, -1, -1, -1, -1, -1, 188, -1, -1, 213, -1, -1, -1, -1, -1, 239, -1, -1, 239, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 239, 239, 239, -1, -1, -1, -1, -1, -1, -1, -1, -1, 239, -1, -1, -1, -1, -1, -1, 239, -1, 239, 213, -1, -1, -1, -1, -1, 239, 239, 239, -1, -1, -1, 239, -1, 239, -1, -1, -1, -1, -1, -1, -1, 213, -1, 213, 239, 213, -1, 213, -1, -1, -1, -1, 213, -1, -1, -1, -1, -1, -1, -1, -1, -1, 213, -1, -1, -1, -1],
    [181, 181, 181, -1, 181, 181, 181, 181, 181, -1, -1, -1, 181, -1, 181, 181, -1, 181, -1, 181, -1, 181, 181, -1, -1, -1, -1, 181, 181, -1, -1, -1, 181, -1, -1, 181, -1, -1, 181, 181, -1, 181, 181, -1, 181, -1, 181, -1, 181, 181, -1, -1, 181, -1, -1, 181, 181, -1, 181, 181, -1, 181, -1, 181, -1, 181, 181, 181, -1, 181, -1, 181, -1, -1, 181, 181, 181, -1, 181, -1, -1, 181, -1, -1, 181, 181, -1, -1, 181, 181, -1, -1, -1, 181, -1, 181, -1, -1, 181, -1, -1, 181, -1, -1, 181, -1, -1, 181, -1, -1, -1, 181, -1, -1, -1, 181],
    [-1, -1, -1, -1, -1, 361, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, 344, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 177, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 177, 177, -1, 177, -1, -1, -1, 177, -1, -1, -1, -1, -1, 177, 177, -1, -1, -1, -1, -1, -1, -1, -1, -1, 177, 177, -1, 177, -1, -1, 177, -1, -1, -1, -1, 177, -1, -1, -1, -1, -1, 177, 177, -1, -1, 177, -1, -1, -1, 177, -1, -1, -1, -1, -1, -1, -1, 177, -1, -1, -1, -1, -1, -1, -1, -1, -1, 177, -1, -1, 177, 177, -1, -1, 177, 177, -1, -1, -1, -1, -1, 177, -1, -1, 177, -1, -1, -1, -1, -1, -1, -1, -1, 177, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 280, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 2, -1, -1, 4, -1, -1, 4, -1, -1, -1, -1, -1, 2, 2, -1, 2, -1, -1, -1, 2, -1, 4, -1, -1, -1, 2, 2, -1, -1, -1, -1, -1, -1, -1, -1, -1, 2, 2, -1, 2, -1, -1, 2, -1, -1, -1, -1, 2, -1, -1, -1, -1, -1, 2, 2, -1, -1, 2, -1, -1, -1, 2, -1, -1, -1, -1, -1, -1, -1, 2, -1, -1, -1, -1, -1, -1, -1, -1, -1, 2, -1, -1, 2, 2, -1, -1, 2, 2, -1, -1, -1, -1, -1, 2, -1, -1, 2, -1, -1, -1, -1, -1, -1, -1, -1, 2, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, 376, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  ]
  TERMINAL_WHILE = 0
  TERMINAL_SIZEOF = 1
  TERMINAL_STATIC = 2
  TERMINAL_OR = 3
  TERMINAL_BREAK = 4
  TERMINAL_LBRACE = 5
  TERMINAL_BITAND = 6
  TERMINAL_DO = 7
  TERMINAL_SEMI = 8
  TERMINAL_LT = 9
  TERMINAL_DIVEQ = 10
  TERMINAL_ELSE_IF = 11
  TERMINAL_FOR = 12
  TERMINAL_BITOREQ = 13
  TERMINAL_STRUCT = 14
  TERMINAL_CONST = 15
  TERMINAL_RPAREN = 16
  TERMINAL_CHAR = 17
  TERMINAL_POUNDPOUND = 18
  TERMINAL_GOTO = 19
  TERMINAL_RSHIFTEQ = 20
  TERMINAL_RESTRICT = 21
  TERMINAL_RBRACE = 22
  TERMINAL_COMMA = 23
  TERMINAL_UNIVERSAL_CHARACTER_NAME = 24
  TERMINAL_BITNOT = 25
  TERMINAL_COLON = 26
  TERMINAL_VOLATILE = 27
  TERMINAL_INT = 28
  TERMINAL_AND = 29
  TERMINAL_NEQ = 30
  TERMINAL_MODEQ = 31
  TERMINAL_LPAREN = 32
  TERMINAL_ADDEQ = 33
  TERMINAL_NOT = 34
  TERMINAL_INTEGER_CONSTANT = 35
  TERMINAL_ENDIF = 36
  TERMINAL_SUBEQ = 37
  TERMINAL_REGISTER = 38
  TERMINAL_INLINE = 39
  TERMINAL_GT = 40
  TERMINAL_UNION = 41
  TERMINAL_RETURN = 42
  TERMINAL_DEFINED = 43
  TERMINAL_FLOAT = 44
  TERMINAL_AMPERSAND = 45
  TERMINAL_FLOATING_CONSTANT = 46
  TERMINAL_ASSIGN = 47
  TERMINAL_STRING_LITERAL = 48
  TERMINAL_DOUBLE = 49
  TERMINAL_SIZEOF_SEPARATOR = 50
  TERMINAL_LSHIFTEQ = 51
  TERMINAL_CASE = 52
  TERMINAL_BITOR = 53
  TERMINAL_EXCLAMATION_POINT = 54
  TERMINAL_LONG = 55
  TERMINAL_SIGNED = 56
  TERMINAL_DIV = 57
  TERMINAL_CHARACTER_CONSTANT = 58
  TERMINAL_TYPEDEF_IDENTIFIER = 59
  TERMINAL_GTEQ = 60
  TERMINAL_DEFAULT = 61
  TERMINAL_POUND = 62
  TERMINAL_UNSIGNED = 63
  TERMINAL_DEFINED_SEPARATOR = 64
  TERMINAL_DECIMAL_FLOATING_CONSTANT = 65
  TERMINAL_SWITCH = 66
  TERMINAL_ENUMERATION_CONSTANT = 67
  TERMINAL_RSQUARE = 68
  TERMINAL_LABEL_HINT = 69
  TERMINAL_BITANDEQ = 70
  TERMINAL_IMAGINARY = 71
  TERMINAL_LTEQ = 72
  TERMINAL_FUNCTION_DEFINITION_HINT = 73
  TERMINAL_HEXADECIMAL_FLOATING_CONSTANT = 74
  TERMINAL_ASTERISK = 75
  TERMINAL_IDENTIFIER = 76
  TERMINAL_MOD = 77
  TERMINAL__EXPR = 78
  TERMINAL_EXTERNAL_DECLARATION_HINT = 79
  TERMINAL__EXPR_SANS_COMMA = 80
  TERMINAL_ENUM = 81
  TERMINAL_LSQUARE = 82
  TERMINAL__DIRECT_DECLARATOR = 83
  TERMINAL_TYPEDEF = 84
  TERMINAL_SHORT = 85
  TERMINAL_BITXOREQ = 86
  TERMINAL_DECLARATOR_HINT = 87
  TERMINAL_COMPLEX = 88
  TERMINAL_AUTO = 89
  TERMINAL_QUESTIONMARK = 90
  TERMINAL_COMMA_VA_ARGS = 91
  TERMINAL_DOT = 92
  TERMINAL_LPAREN_CAST = 93
  TERMINAL_TRAILING_COMMA = 94
  TERMINAL_EXTERN = 95
  TERMINAL_ARROW = 96
  TERMINAL_ELSE = 97
  TERMINAL_VOID = 98
  TERMINAL_FUNCTION_PROTOTYPE_HINT = 99
  TERMINAL_LSHIFT = 100
  TERMINAL_DECR = 101
  TERMINAL_RSHIFT = 102
  TERMINAL_PP_NUMBER = 103
  TERMINAL_CONTINUE = 104
  TERMINAL_ELIPSIS = 105
  TERMINAL_TILDE = 106
  TERMINAL_BOOL = 107
  TERMINAL_ADD = 108
  TERMINAL_EQ = 109
  TERMINAL_SUB = 110
  TERMINAL_INCR = 111
  TERMINAL__DIRECT_ABSTRACT_DECLARATOR = 112
  TERMINAL_MULEQ = 113
  TERMINAL_BITXOR = 114
  TERMINAL_IF = 115
  def __init__(self):
    self.iterator = None
    self.sym = None
    self.expressionParsers = dict()
  def isTerminal(self, id):
    return 0 <= id <= 115
  def isNonTerminal(self, id):
    return 116 <= id <= 243
  def getsym(self):
    try:
      return next( self.iterator )
    except StopIteration:
      return None
  def parse(self, iterator):
    self.iterator = iter(iterator)
    self.sym = self.getsym()
    self.start = 'TRANSLATION_UNIT'
    tree = self.parse_translation_unit()
    if self.sym != None:
      raise SyntaxError( 'Syntax Error: Finished parsing without consuming all tokens.' )
    self.iterator = None
    self.sym = None
    return tree
  def next(self):
    self.sym = self.getsym()
    if self.sym is not None and not self.isTerminal(self.sym.getId()):
      self.sym = None
      raise SyntaxError( 'Invalid symbol ID: %d (%s)' % (self.sym.getId(), self.sym) )
    return self.sym
  def expect(self, s):
    if self.sym and s == self.sym.getId():
      symbol = self.sym
      self.sym = self.next()
      return symbol
    else:
      raise SyntaxError('Unexpected symbol when parsing %s.  Expected %s, got %s.' %(whosdaddy(), self.terminals[s], self.sym if self.sym else 'None'))
  def rule(self, n):
    if self.sym == None: return -1
    return self.table[n - 116][self.sym.getId()]
  def call(self, nt_str):
    return getattr(self, nt_str)()
  def parse__gen23(self, depth=0, tracer=None):
    rule = self.rule(117)
    tree = ParseTree( NonTerminal(117, self.nonterminals[117]))
    tree.list = 'slist'
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 267:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_enumerator()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse__gen24()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse_parameter_declaration_sub(self, depth=0, tracer=None):
    rule = self.rule(118)
    tree = ParseTree( NonTerminal(118, self.nonterminals[118]))
    tree.list = False
    if self.sym == None:
      return tree
    if rule == 282:
      tree.astTransform = AstTransformNodeCreator('ParameterSub', {'name_and_size': 1, 'pointer': 0})
      subtree = self.parse_pointer_opt()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse_parameter_declaration_sub_sub()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [83, 76, 32]:
      tree.astTransform = AstTransformNodeCreator('ParameterSub', {'name_and_size': 1, 'pointer': 0})
      subtree = self.parse_pointer_opt()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse_parameter_declaration_sub_sub()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    elif self.sym.getId() in [32, 112, -1]:
      tree.astTransform = AstTransformNodeCreator('ParameterSub', {'name_and_size': 1, 'pointer': 0})
      subtree = self.parse_pointer_opt()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse_parameter_declaration_sub_sub()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse_expression_opt(self, depth=0, tracer=None):
    rule = self.rule(119)
    tree = ParseTree( NonTerminal(119, self.nonterminals[119]))
    tree.list = False
    if self.sym != None and (self.sym.getId() in [8, 16]):
      return tree
    if self.sym == None:
      return tree
    if rule == 219:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__expr()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [78, 67, 1, 93, 58, 6, 32, 65, 35, 48, 101, 74, 75, 46, 111, 76]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__expr()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    return tree
  def parse_struct_declarator_body(self, depth=0, tracer=None):
    rule = self.rule(120)
    tree = ParseTree( NonTerminal(120, self.nonterminals[120]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 46:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(26) # colon
      tree.add(t)
      subtree = self.parse_declarator()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse__gen12(self, depth=0, tracer=None):
    rule = self.rule(121)
    tree = ParseTree( NonTerminal(121, self.nonterminals[121]))
    tree.list = 'slist'
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 92:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_initializer_list_item()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse__gen13()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [1, 80, 93, 58, 6, 32, 67, 65, 48, 101, 35, 74, 75, 46, 111, 76]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_initializer_list_item()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse__gen13()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse__gen13(self, depth=0, tracer=None):
    rule = self.rule(122)
    tree = ParseTree( NonTerminal(122, self.nonterminals[122]))
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in [94]):
      return tree
    if self.sym == None:
      return tree
    if rule == 108:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(23) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self.parse_initializer_list_item()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse__gen13()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def parse_enum_specifier(self, depth=0, tracer=None):
    rule = self.rule(123)
    tree = ParseTree( NonTerminal(123, self.nonterminals[123]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 244:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(81) # enum
      tree.add(t)
      subtree = self.parse_enum_specifier_sub()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse_direct_declarator_expr(self, depth=0, tracer=None):
    rule = self.rule(124)
    tree = ParseTree( NonTerminal(124, self.nonterminals[124]))
    tree.list = False
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 56:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_direct_declarator_modifier_list_opt()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse_direct_declarator_size()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [78, 67, 1, 93, 58, 6, 32, 65, 35, 48, 101, 74, 75, 46, 111, 76]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_direct_declarator_modifier_list_opt()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse_direct_declarator_size()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    return tree
  def parse__gen21(self, depth=0, tracer=None):
    rule = self.rule(125)
    tree = ParseTree( NonTerminal(125, self.nonterminals[125]))
    tree.list = False
    if self.sym != None and (self.sym.getId() in [23, 8]):
      return tree
    if self.sym == None:
      return tree
    if rule == 206:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_struct_declarator_body()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def parse_for_init(self, depth=0, tracer=None):
    rule = self.rule(126)
    tree = ParseTree( NonTerminal(126, self.nonterminals[126]))
    tree.list = False
    if self.sym != None and (self.sym.getId() in [8]):
      return tree
    if self.sym == None:
      return tree
    if rule == 14:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_declaration()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse_expression_opt()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 28:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__expr()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [78, 67, 1, 93, 58, 6, 32, 65, 35, 48, 101, 74, 75, 46, 111, 76]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__expr()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    return tree
  def parse__gen8(self, depth=0, tracer=None):
    rule = self.rule(127)
    tree = ParseTree( NonTerminal(127, self.nonterminals[127]))
    tree.list = False
    if self.sym != None and (self.sym.getId() in [8]):
      return tree
    if self.sym == None:
      return tree
    if rule == 395:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_init_declarator_list()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [83, 76, 32]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_init_declarator_list()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    return tree
  def parse_enum_specifier_sub(self, depth=0, tracer=None):
    rule = self.rule(128)
    tree = ParseTree( NonTerminal(128, self.nonterminals[128]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 196:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_enum_specifier_body()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 346:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_identifier()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse__gen22()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse_for_incr(self, depth=0, tracer=None):
    rule = self.rule(129)
    tree = ParseTree( NonTerminal(129, self.nonterminals[129]))
    tree.list = False
    if self.sym != None and (self.sym.getId() in [16]):
      return tree
    if self.sym == None:
      return tree
    if rule == 248:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(8) # semi
      tree.add(t)
      subtree = self.parse_expression_opt()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def parse_direct_abstract_declarator_opt(self, depth=0, tracer=None):
    rule = self.rule(130)
    tree = ParseTree( NonTerminal(130, self.nonterminals[130]))
    tree.list = False
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 336:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__direct_abstract_declarator()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [32, 112, -1]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__direct_abstract_declarator()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    return tree
  def parse_parameter_declaration_sub_sub(self, depth=0, tracer=None):
    rule = self.rule(131)
    tree = ParseTree( NonTerminal(131, self.nonterminals[131]))
    tree.list = False
    if self.sym == None:
      return tree
    if rule == 316:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__direct_declarator()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 375:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen33()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [83, 76, 32]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__direct_declarator()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    elif self.sym.getId() in [32, 112, -1]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen33()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse_trailing_comma_opt(self, depth=0, tracer=None):
    rule = self.rule(132)
    tree = ParseTree( NonTerminal(132, self.nonterminals[132]))
    tree.list = False
    if self.sym != None and (self.sym.getId() in [22]):
      return tree
    if self.sym == None:
      return tree
    if rule == 390:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(94) # trailing_comma
      tree.add(t)
      return tree
    return tree
  def parse__gen16(self, depth=0, tracer=None):
    rule = self.rule(133)
    tree = ParseTree( NonTerminal(133, self.nonterminals[133]))
    tree.list = False
    if self.sym != None and (self.sym.getId() in [49, 73, 88, 56, 32, 59, 8, 63, 75, 23, 15, 28, 17, 76, 87, 21, 85, 98, 26, 27, 84, 71, 41, 81, 95, 55, 99, 38, 39, 112, 2, 44, 107, 83, 14, 91, 89]):
      return tree
    if self.sym == None:
      return tree
    if rule == 35:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_struct_or_union_body()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def parse_storage_class_specifier(self, depth=0, tracer=None):
    rule = self.rule(134)
    tree = ParseTree( NonTerminal(134, self.nonterminals[134]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 74:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(2) # static
      tree.add(t)
      return tree
    elif rule == 175:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(89) # auto
      tree.add(t)
      return tree
    elif rule == 247:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(84) # typedef
      tree.add(t)
      return tree
    elif rule == 292:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(38) # register
      tree.add(t)
      return tree
    elif rule == 298:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(95) # extern
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse_external_function(self, depth=0, tracer=None):
    rule = self.rule(135)
    tree = ParseTree( NonTerminal(135, self.nonterminals[135]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 285:
      tree.astTransform = AstTransformNodeCreator('FunctionDefinition', {'body': 3, 'declaration_list': 2, 'signature': 1})
      t = self.expect(73) # function_definition_hint
      tree.add(t)
      subtree = self.parse_declarator()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse__gen5()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse_compound_statement()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse_designation(self, depth=0, tracer=None):
    rule = self.rule(136)
    tree = ParseTree( NonTerminal(136, self.nonterminals[136]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 80:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen15()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(47) # assign
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse__gen14(self, depth=0, tracer=None):
    rule = self.rule(137)
    tree = ParseTree( NonTerminal(137, self.nonterminals[137]))
    tree.list = False
    if self.sym != None and (self.sym.getId() in [1, 80, 93, 5, 58, 6, 32, 67, 65, 48, 101, 35, 74, 75, 46, 111, 76]):
      return tree
    if self.sym == None:
      return tree
    if rule == 208:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_designation()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def parse__gen33(self, depth=0, tracer=None):
    rule = self.rule(138)
    tree = ParseTree( NonTerminal(138, self.nonterminals[138]))
    tree.list = False
    if self.sym != None and (self.sym.getId() in [23, 91]):
      return tree
    if self.sym == None:
      return tree
    if rule == 37:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__direct_abstract_declarator()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [32, 112, -1]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__direct_abstract_declarator()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    return tree
  def parse__gen25(self, depth=0, tracer=None):
    rule = self.rule(139)
    tree = ParseTree( NonTerminal(139, self.nonterminals[139]))
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [23, 2, 32, 112, 75, 83, 91, 76]):
      return tree
    if self.sym == None:
      return tree
    if rule == 38:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_type_qualifier()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse__gen25()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def parse_else_if_statement_list(self, depth=0, tracer=None):
    rule = self.rule(140)
    tree = ParseTree( NonTerminal(140, self.nonterminals[140]))
    tree.list = False
    if self.sym == None:
      return tree
    if rule == 393:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen39()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse_pointer_sub(self, depth=0, tracer=None):
    rule = self.rule(141)
    tree = ParseTree( NonTerminal(141, self.nonterminals[141]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 242:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(75) # asterisk
      tree.add(t)
      subtree = self.parse_type_qualifier_list_opt()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse_type_qualifier(self, depth=0, tracer=None):
    rule = self.rule(142)
    tree = ParseTree( NonTerminal(142, self.nonterminals[142]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 27:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(21) # restrict
      tree.add(t)
      return tree
    elif rule == 194:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(27) # volatile
      tree.add(t)
      return tree
    elif rule == 325:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(15) # const
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse_identifier(self, depth=0, tracer=None):
    rule = self.rule(143)
    tree = ParseTree( NonTerminal(143, self.nonterminals[143]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 85:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(76) # identifier
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse_enum_specifier_body(self, depth=0, tracer=None):
    rule = self.rule(144)
    tree = ParseTree( NonTerminal(144, self.nonterminals[144]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 189:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(5) # lbrace
      tree.add(t)
      subtree = self.parse__gen23()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse_trailing_comma_opt()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(22) # rbrace
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse__gen40(self, depth=0, tracer=None):
    rule = self.rule(145)
    tree = ParseTree( NonTerminal(145, self.nonterminals[145]))
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 98:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__expr_sans_comma()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse__gen41()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def parse__gen22(self, depth=0, tracer=None):
    rule = self.rule(146)
    tree = ParseTree( NonTerminal(146, self.nonterminals[146]))
    tree.list = False
    if self.sym != None and (self.sym.getId() in [49, 73, 88, 56, 32, 59, 8, 63, 75, 23, 15, 28, 17, 76, 87, 21, 85, 98, 26, 27, 84, 71, 41, 81, 95, 55, 99, 38, 39, 112, 2, 44, 107, 83, 14, 91, 89]):
      return tree
    if self.sym == None:
      return tree
    if rule == 238:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_enum_specifier_body()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def parse__gen15(self, depth=0, tracer=None):
    rule = self.rule(147)
    tree = ParseTree( NonTerminal(147, self.nonterminals[147]))
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [47]):
      return tree
    if self.sym == None:
      return tree
    if rule == 383:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_designator()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse__gen15()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def parse_initializer_list_item(self, depth=0, tracer=None):
    rule = self.rule(148)
    tree = ParseTree( NonTerminal(148, self.nonterminals[148]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 97:
      tree.astTransform = AstTransformNodeCreator('Initialization', {'designation': 0, 'initializer': 1})
      subtree = self.parse__gen14()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse_initializer()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 362:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(35) # integer_constant
      tree.add(t)
      return tree
    elif self.sym.getId() in [1, 80, 93, 58, 6, 32, 67, 65, 48, 101, 35, 74, 75, 46, 111, 76]:
      tree.astTransform = AstTransformNodeCreator('Initialization', {'designation': 0, 'initializer': 1})
      subtree = self.parse__gen14()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse_initializer()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse_struct_declaration(self, depth=0, tracer=None):
    rule = self.rule(149)
    tree = ParseTree( NonTerminal(149, self.nonterminals[149]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 409:
      tree.astTransform = AstTransformNodeCreator('StructOrUnionDeclaration', {'specifier_qualifiers': 0, 'declarators': 1})
      subtree = self.parse__gen18()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse__gen19()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(8) # semi
      tree.add(t)
      return tree
    elif self.sym.getId() in [83, 76, 32]:
      tree.astTransform = AstTransformNodeCreator('StructOrUnionDeclaration', {'specifier_qualifiers': 0, 'declarators': 1})
      subtree = self.parse__gen18()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse__gen19()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(8, tracer) ) # semi
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse_parameter_type_list(self, depth=0, tracer=None):
    rule = self.rule(150)
    tree = ParseTree( NonTerminal(150, self.nonterminals[150]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 20:
      tree.astTransform = AstTransformNodeCreator('ParameterTypeList', {'parameter_declarations': 0, 'va_args': 1})
      subtree = self.parse__gen27()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse__gen29()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse_translation_unit(self, depth=0, tracer=None):
    rule = self.rule(151)
    tree = ParseTree( NonTerminal(151, self.nonterminals[151]))
    tree.list = False
    if self.sym == None:
      return tree
    if rule == 100:
      tree.astTransform = AstTransformNodeCreator('TranslationUnit', {'external_declarations': 0})
      subtree = self.parse__gen0()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse__gen9(self, depth=0, tracer=None):
    rule = self.rule(152)
    tree = ParseTree( NonTerminal(152, self.nonterminals[152]))
    tree.list = 'slist'
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 65:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_init_declarator()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse__gen10()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [83, 76, 32]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_init_declarator()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse__gen10()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse__gen10(self, depth=0, tracer=None):
    rule = self.rule(153)
    tree = ParseTree( NonTerminal(153, self.nonterminals[153]))
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in [8]):
      return tree
    if self.sym == None:
      return tree
    if rule == 404:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(23) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self.parse_init_declarator()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse__gen10()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def parse_external_declaration(self, depth=0, tracer=None):
    rule = self.rule(154)
    tree = ParseTree( NonTerminal(154, self.nonterminals[154]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 318:
      tree.astTransform = AstTransformNodeCreator('ExternalDeclaration', {'declarations': 2, 'declaration_specifiers': 1})
      t = self.expect(79) # external_declaration_hint
      tree.add(t)
      subtree = self.parse__gen1()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse_external_declaration_sub()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse_struct_declarator(self, depth=0, tracer=None):
    rule = self.rule(155)
    tree = ParseTree( NonTerminal(155, self.nonterminals[155]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 19:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_declarator()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse__gen21()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 351:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_struct_declarator_body()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [83, 76, 32]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_declarator()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse__gen21()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse__gen0(self, depth=0, tracer=None):
    rule = self.rule(156)
    tree = ParseTree( NonTerminal(156, self.nonterminals[156]))
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [-1]):
      return tree
    if self.sym == None:
      return tree
    if rule == 1:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_external_declaration()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse__gen0()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def parse__gen29(self, depth=0, tracer=None):
    rule = self.rule(158)
    tree = ParseTree( NonTerminal(158, self.nonterminals[158]))
    tree.list = False
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 144:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_va_args()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def parse_declaration_list(self, depth=0, tracer=None):
    rule = self.rule(159)
    tree = ParseTree( NonTerminal(159, self.nonterminals[159]))
    tree.list = False
    if self.sym == None:
      return tree
    if rule == 164:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen7()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse_specifier_qualifier(self, depth=0, tracer=None):
    rule = self.rule(160)
    tree = ParseTree( NonTerminal(160, self.nonterminals[160]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 153:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_type_qualifier()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 382:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_type_specifier()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse__gen18(self, depth=0, tracer=None):
    rule = self.rule(161)
    tree = ParseTree( NonTerminal(161, self.nonterminals[161]))
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [75, 83, 32, 26, 76]):
      return tree
    if self.sym == None:
      return tree
    if rule == 75:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_specifier_qualifier()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse__gen18()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def parse__gen24(self, depth=0, tracer=None):
    rule = self.rule(162)
    tree = ParseTree( NonTerminal(162, self.nonterminals[162]))
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in [94]):
      return tree
    if self.sym == None:
      return tree
    if rule == 271:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(23) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self.parse_enumerator()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse__gen24()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def parse_direct_declarator_modifier_list_opt(self, depth=0, tracer=None):
    rule = self.rule(163)
    tree = ParseTree( NonTerminal(163, self.nonterminals[163]))
    tree.list = False
    if self.sym != None and (self.sym.getId() in [78, 67, 1, 93, 58, 6, 32, 65, 35, 48, 101, 74, 75, 46, 111, 76]):
      return tree
    if self.sym == None:
      return tree
    if rule == 53:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen26()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def parse_direct_declarator_size(self, depth=0, tracer=None):
    rule = self.rule(164)
    tree = ParseTree( NonTerminal(164, self.nonterminals[164]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 169:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(75) # asterisk
      tree.add(t)
      return tree
    elif rule == 251:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__expr()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [78, 67, 1, 93, 58, 6, 32, 65, 35, 48, 101, 74, 75, 46, 111, 76]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__expr()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse_typedef_name(self, depth=0, tracer=None):
    rule = self.rule(165)
    tree = ParseTree( NonTerminal(165, self.nonterminals[165]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 171:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(59) # typedef_identifier
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse__gen41(self, depth=0, tracer=None):
    rule = self.rule(166)
    tree = ParseTree( NonTerminal(166, self.nonterminals[166]))
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 415:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(23) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self.parse__expr_sans_comma()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse__gen41()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def parse_declarator_initializer(self, depth=0, tracer=None):
    rule = self.rule(167)
    tree = ParseTree( NonTerminal(167, self.nonterminals[167]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 257:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(47) # assign
      tree.add(t)
      subtree = self.parse_initializer()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse__gen11(self, depth=0, tracer=None):
    rule = self.rule(168)
    tree = ParseTree( NonTerminal(168, self.nonterminals[168]))
    tree.list = False
    if self.sym != None and (self.sym.getId() in [23, 8]):
      return tree
    if self.sym == None:
      return tree
    if rule == 84:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_declarator_initializer()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def parse__gen19(self, depth=0, tracer=None):
    rule = self.rule(169)
    tree = ParseTree( NonTerminal(169, self.nonterminals[169]))
    tree.list = 'slist'
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 125:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_struct_declarator()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse__gen20()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [83, 76, 32]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_struct_declarator()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse__gen20()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse__gen20(self, depth=0, tracer=None):
    rule = self.rule(170)
    tree = ParseTree( NonTerminal(170, self.nonterminals[170]))
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in [8]):
      return tree
    if self.sym == None:
      return tree
    if rule == 118:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(23) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self.parse_struct_declarator()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse__gen20()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def parse__gen34(self, depth=0, tracer=None):
    rule = self.rule(171)
    tree = ParseTree( NonTerminal(171, self.nonterminals[171]))
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [23, 112, 83, 32, 91, 76]):
      return tree
    if self.sym == None:
      return tree
    if rule == 138:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_pointer_sub()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse__gen34()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def parse_direct_declarator_modifier(self, depth=0, tracer=None):
    rule = self.rule(172)
    tree = ParseTree( NonTerminal(172, self.nonterminals[172]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 96:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_type_qualifier()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 417:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(2) # static
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse_designator(self, depth=0, tracer=None):
    rule = self.rule(173)
    tree = ParseTree( NonTerminal(173, self.nonterminals[173]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 266:
      tree.astTransform = AstTransformNodeCreator('ArrayAccess', {'index': 1})
      t = self.expect(82) # lsquare
      tree.add(t)
      subtree = self.parse__expr()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(68) # rsquare
      tree.add(t)
      return tree
    elif rule == 408:
      tree.astTransform = AstTransformNodeCreator('MemberAccess', {'name': 1})
      t = self.expect(92) # dot
      tree.add(t)
      t = self.expect(76) # identifier
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse__gen26(self, depth=0, tracer=None):
    rule = self.rule(174)
    tree = ParseTree( NonTerminal(174, self.nonterminals[174]))
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [78, 67, 1, 93, 58, 32, 6, 35, 65, 48, 101, 75, 111, 46, 74, 76]):
      return tree
    if self.sym == None:
      return tree
    if rule == 93:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_direct_declarator_modifier()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse__gen26()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def parse_enumeration_constant(self, depth=0, tracer=None):
    rule = self.rule(175)
    tree = ParseTree( NonTerminal(175, self.nonterminals[175]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 50:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(76) # identifier
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse_enumerator_assignment(self, depth=0, tracer=None):
    rule = self.rule(176)
    tree = ParseTree( NonTerminal(176, self.nonterminals[176]))
    tree.list = False
    if self.sym != None and (self.sym.getId() in [23, 94]):
      return tree
    if self.sym == None:
      return tree
    if rule == 183:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(47) # assign
      tree.add(t)
      subtree = self.parse__expr()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def parse_static_opt(self, depth=0, tracer=None):
    rule = self.rule(177)
    tree = ParseTree( NonTerminal(177, self.nonterminals[177]))
    tree.list = False
    if self.sym != None and (self.sym.getId() in [78, 67, 1, 93, 58, 6, 32, 65, 35, 48, 101, 74, 75, 46, 111, 76]):
      return tree
    if self.sym == None:
      return tree
    if rule == 57:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(2) # static
      tree.add(t)
      return tree
    return tree
  def parse_declaration_specifier(self, depth=0, tracer=None):
    rule = self.rule(178)
    tree = ParseTree( NonTerminal(178, self.nonterminals[178]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 54:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_storage_class_specifier()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 82:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_type_specifier()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 103:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_type_qualifier()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 261:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_function_specifier()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse__gen39(self, depth=0, tracer=None):
    rule = self.rule(179)
    tree = ParseTree( NonTerminal(179, self.nonterminals[179]))
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [0, 1, 69, 38, 32, 7, 8, 98, 12, 75, 14, 15, 17, 41, 21, 6, 85, 36, 27, 28, 115, 81, 55, 35, 5, 39, 76, 44, 46, 48, 49, 78, 67, 22, 19, 56, 58, 59, 104, 63, 65, 4, 107, 74, 42, 52, 61, 84, 71, 88, 93, 95, 97, 101, 2, 66, 111, 89]):
      return tree
    if self.sym == None:
      return tree
    if rule == 406:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_else_if_statement()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse__gen39()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def parse_initializer(self, depth=0, tracer=None):
    rule = self.rule(180)
    tree = ParseTree( NonTerminal(180, self.nonterminals[180]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 24:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(5) # lbrace
      tree.add(t)
      subtree = self.parse__gen12()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse_trailing_comma_opt()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(22) # rbrace
      tree.add(t)
      return tree
    elif rule == 152:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__expr_sans_comma()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [1, 80, 93, 58, 6, 32, 67, 65, 48, 101, 35, 74, 75, 46, 111, 76]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__expr_sans_comma()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse_type_specifier(self, depth=0, tracer=None):
    rule = self.rule(181)
    tree = ParseTree( NonTerminal(181, self.nonterminals[181]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 32:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(85) # short
      tree.add(t)
      return tree
    elif rule == 51:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(88) # complex
      tree.add(t)
      return tree
    elif rule == 78:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(56) # signed
      tree.add(t)
      return tree
    elif rule == 126:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(107) # bool
      tree.add(t)
      return tree
    elif rule == 170:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_typedef_name()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 176:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(55) # long
      tree.add(t)
      return tree
    elif rule == 179:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(44) # float
      tree.add(t)
      return tree
    elif rule == 184:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(28) # int
      tree.add(t)
      return tree
    elif rule == 237:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_union_specifier()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 304:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(98) # void
      tree.add(t)
      return tree
    elif rule == 331:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(49) # double
      tree.add(t)
      return tree
    elif rule == 348:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(17) # char
      tree.add(t)
      return tree
    elif rule == 355:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(63) # unsigned
      tree.add(t)
      return tree
    elif rule == 357:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(71) # imaginary
      tree.add(t)
      return tree
    elif rule == 412:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_struct_specifier()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 422:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_enum_specifier()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse_function_specifier(self, depth=0, tracer=None):
    rule = self.rule(182)
    tree = ParseTree( NonTerminal(182, self.nonterminals[182]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 3:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(39) # inline
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse_type_name(self, depth=0, tracer=None):
    rule = self.rule(183)
    tree = ParseTree( NonTerminal(183, self.nonterminals[183]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 342:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(17) # char
      tree.add(t)
      return tree
    elif rule == 345:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(28) # int
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse_init_declarator_list(self, depth=0, tracer=None):
    rule = self.rule(184)
    tree = ParseTree( NonTerminal(184, self.nonterminals[184]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 141:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen9()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [83, 76, 32]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen9()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse_external_declaration_sub(self, depth=0, tracer=None):
    rule = self.rule(185)
    tree = ParseTree( NonTerminal(185, self.nonterminals[185]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 87:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_external_function()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 166:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen3()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(8) # semi
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse__gen32(self, depth=0, tracer=None):
    rule = self.rule(186)
    tree = ParseTree( NonTerminal(186, self.nonterminals[186]))
    tree.list = False
    if self.sym != None and (self.sym.getId() in [23, 91]):
      return tree
    if self.sym == None:
      return tree
    if rule == 411:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_parameter_declaration_sub()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [83, 76, 32]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_parameter_declaration_sub()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    elif self.sym.getId() in [32, 112, -1]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_parameter_declaration_sub()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    return tree
  def parse__gen1(self, depth=0, tracer=None):
    rule = self.rule(187)
    tree = ParseTree( NonTerminal(187, self.nonterminals[187]))
    tree.list = 'mlist'
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 199:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_declaration_specifier()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse__gen2()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse_keyword(self, depth=0, tracer=None):
    rule = self.rule(188)
    tree = ParseTree( NonTerminal(188, self.nonterminals[188]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 5:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(42) # return
      tree.add(t)
      return tree
    elif rule == 6:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(115) # if
      tree.add(t)
      return tree
    elif rule == 15:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(55) # long
      tree.add(t)
      return tree
    elif rule == 30:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(28) # int
      tree.add(t)
      return tree
    elif rule == 62:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(95) # extern
      tree.add(t)
      return tree
    elif rule == 64:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(38) # register
      tree.add(t)
      return tree
    elif rule == 90:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(7) # do
      tree.add(t)
      return tree
    elif rule == 91:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(85) # short
      tree.add(t)
      return tree
    elif rule == 99:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(81) # enum
      tree.add(t)
      return tree
    elif rule == 134:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(19) # goto
      tree.add(t)
      return tree
    elif rule == 149:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(41) # union
      tree.add(t)
      return tree
    elif rule == 185:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(27) # volatile
      tree.add(t)
      return tree
    elif rule == 191:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(0) # while
      tree.add(t)
      return tree
    elif rule == 202:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(84) # typedef
      tree.add(t)
      return tree
    elif rule == 203:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(15) # const
      tree.add(t)
      return tree
    elif rule == 204:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(21) # restrict
      tree.add(t)
      return tree
    elif rule == 205:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(39) # inline
      tree.add(t)
      return tree
    elif rule == 215:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(63) # unsigned
      tree.add(t)
      return tree
    elif rule == 227:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(66) # switch
      tree.add(t)
      return tree
    elif rule == 228:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(14) # struct
      tree.add(t)
      return tree
    elif rule == 229:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(98) # void
      tree.add(t)
      return tree
    elif rule == 230:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(1) # sizeof
      tree.add(t)
      return tree
    elif rule == 231:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(2) # static
      tree.add(t)
      return tree
    elif rule == 233:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(89) # auto
      tree.add(t)
      return tree
    elif rule == 254:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(4) # break
      tree.add(t)
      return tree
    elif rule == 260:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(56) # signed
      tree.add(t)
      return tree
    elif rule == 264:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(49) # double
      tree.add(t)
      return tree
    elif rule == 276:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(107) # bool
      tree.add(t)
      return tree
    elif rule == 295:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(104) # continue
      tree.add(t)
      return tree
    elif rule == 302:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(52) # case
      tree.add(t)
      return tree
    elif rule == 305:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(12) # for
      tree.add(t)
      return tree
    elif rule == 330:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(17) # char
      tree.add(t)
      return tree
    elif rule == 341:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(44) # float
      tree.add(t)
      return tree
    elif rule == 343:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(61) # default
      tree.add(t)
      return tree
    elif rule == 356:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(88) # complex
      tree.add(t)
      return tree
    elif rule == 397:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(71) # imaginary
      tree.add(t)
      return tree
    elif rule == 420:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(97) # else
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse_else_statement(self, depth=0, tracer=None):
    rule = self.rule(189)
    tree = ParseTree( NonTerminal(189, self.nonterminals[189]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 369:
      tree.astTransform = AstTransformNodeCreator('Else', {'statement': 1})
      t = self.expect(97) # else
      tree.add(t)
      subtree = self.parse_statement()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(36) # endif
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse_block_item(self, depth=0, tracer=None):
    rule = self.rule(190)
    tree = ParseTree( NonTerminal(190, self.nonterminals[190]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 187:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_declaration()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 324:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_statement()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [78, 67, 1, 93, 58, 6, 32, 65, 35, 48, 101, 74, 75, 46, 111, 76]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_statement()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse__gen36(self, depth=0, tracer=None):
    rule = self.rule(191)
    tree = ParseTree( NonTerminal(191, self.nonterminals[191]))
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [22]):
      return tree
    if self.sym == None:
      return tree
    if rule == 111:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_block_item()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse__gen36()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [78, 67, 1, 93, 58, 6, 32, 65, 35, 48, 101, 74, 75, 46, 111, 76]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_block_item()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse__gen36()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    return tree
  def parse_struct_or_union_sub(self, depth=0, tracer=None):
    rule = self.rule(192)
    tree = ParseTree( NonTerminal(192, self.nonterminals[192]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 224:
      tree.astTransform = AstTransformNodeCreator('StructOrUnion', {'body': 1, 'name': 0})
      t = self.expect(76) # identifier
      tree.add(t)
      subtree = self.parse__gen16()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 311:
      tree.astTransform = AstTransformNodeCreator('StructOrUnion', {'body': 0})
      subtree = self.parse_struct_or_union_body()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse__gen2(self, depth=0, tracer=None):
    rule = self.rule(193)
    tree = ParseTree( NonTerminal(193, self.nonterminals[193]))
    tree.list = 'mlist'
    if self.sym != None and (self.sym.getId() in [73, 83, 112, 87, 32, 8, 99, 23, 75, 91, 76]):
      return tree
    if self.sym == None:
      return tree
    if rule == 286:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_declaration_specifier()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse__gen2()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def parse_misc(self, depth=0, tracer=None):
    rule = self.rule(194)
    tree = ParseTree( NonTerminal(194, self.nonterminals[194]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 218:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(36) # endif
      tree.add(t)
      return tree
    elif rule == 290:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(24) # universal_character_name
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse__gen17(self, depth=0, tracer=None):
    rule = self.rule(195)
    tree = ParseTree( NonTerminal(195, self.nonterminals[195]))
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [22]):
      return tree
    if self.sym == None:
      return tree
    if rule == 329:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_struct_declaration()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse__gen17()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [83, 76, 32]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_struct_declaration()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse__gen17()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    return tree
  def parse_constant(self, depth=0, tracer=None):
    rule = self.rule(196)
    tree = ParseTree( NonTerminal(196, self.nonterminals[196]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 33:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(67) # enumeration_constant
      tree.add(t)
      return tree
    elif rule == 49:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(58) # character_constant
      tree.add(t)
      return tree
    elif rule == 81:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(65) # decimal_floating_constant
      tree.add(t)
      return tree
    elif rule == 151:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(46) # floating_constant
      tree.add(t)
      return tree
    elif rule == 297:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(74) # hexadecimal_floating_constant
      tree.add(t)
      return tree
    elif rule == 308:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(35) # integer_constant
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse_external_declaration_sub_sub(self, depth=0, tracer=None):
    rule = self.rule(197)
    tree = ParseTree( NonTerminal(197, self.nonterminals[197]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 12:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_external_prototype()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 212:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_external_declarator()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse_statement(self, depth=0, tracer=None):
    rule = self.rule(198)
    tree = ParseTree( NonTerminal(198, self.nonterminals[198]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 41:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_iteration_statement()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 59:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_compound_statement()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 72:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_selection_statement()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 223:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_labeled_statement()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 281:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_expression_statement()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 317:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_jump_statement()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [78, 67, 1, 93, 58, 6, 32, 65, 35, 48, 101, 74, 75, 46, 111, 76]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_expression_statement()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse__gen3(self, depth=0, tracer=None):
    rule = self.rule(199)
    tree = ParseTree( NonTerminal(199, self.nonterminals[199]))
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in [8]):
      return tree
    if self.sym == None:
      return tree
    if rule == 319:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_external_declaration_sub_sub()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse__gen4()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def parse__gen4(self, depth=0, tracer=None):
    rule = self.rule(200)
    tree = ParseTree( NonTerminal(200, self.nonterminals[200]))
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in [8]):
      return tree
    if self.sym == None:
      return tree
    if rule == 322:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(23) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self.parse_external_declaration_sub_sub()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse__gen4()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def parse_direct_declarator_parameter_list(self, depth=0, tracer=None):
    rule = self.rule(201)
    tree = ParseTree( NonTerminal(201, self.nonterminals[201]))
    tree.list = False
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 68:
      tree.astTransform = AstTransformNodeCreator('ParameterList', {'identifiers': 0})
      subtree = self.parse__gen30()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 173:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_parameter_type_list()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def parse_punctuator(self, depth=0, tracer=None):
    rule = self.rule(202)
    tree = ParseTree( NonTerminal(202, self.nonterminals[202]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 10:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(90) # questionmark
      tree.add(t)
      return tree
    elif rule == 18:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(9) # lt
      tree.add(t)
      return tree
    elif rule == 23:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(68) # rsquare
      tree.add(t)
      return tree
    elif rule == 31:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(101) # decr
      tree.add(t)
      return tree
    elif rule == 39:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(105) # elipsis
      tree.add(t)
      return tree
    elif rule == 42:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(109) # eq
      tree.add(t)
      return tree
    elif rule == 52:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(92) # dot
      tree.add(t)
      return tree
    elif rule == 55:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(106) # tilde
      tree.add(t)
      return tree
    elif rule == 60:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(62) # pound
      tree.add(t)
      return tree
    elif rule == 83:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(60) # gteq
      tree.add(t)
      return tree
    elif rule == 88:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(45) # ampersand
      tree.add(t)
      return tree
    elif rule == 107:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(47) # assign
      tree.add(t)
      return tree
    elif rule == 114:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(113) # muleq
      tree.add(t)
      return tree
    elif rule == 156:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(110) # sub
      tree.add(t)
      return tree
    elif rule == 163:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(54) # exclamation_point
      tree.add(t)
      return tree
    elif rule == 172:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(57) # div
      tree.add(t)
      return tree
    elif rule == 182:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(16) # rparen
      tree.add(t)
      return tree
    elif rule == 193:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(51) # lshifteq
      tree.add(t)
      return tree
    elif rule == 198:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(70) # bitandeq
      tree.add(t)
      return tree
    elif rule == 220:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(72) # lteq
      tree.add(t)
      return tree
    elif rule == 222:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(111) # incr
      tree.add(t)
      return tree
    elif rule == 225:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(18) # poundpound
      tree.add(t)
      return tree
    elif rule == 235:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(8) # semi
      tree.add(t)
      return tree
    elif rule == 258:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(29) # and
      tree.add(t)
      return tree
    elif rule == 272:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(37) # subeq
      tree.add(t)
      return tree
    elif rule == 273:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(77) # mod
      tree.add(t)
      return tree
    elif rule == 278:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(108) # add
      tree.add(t)
      return tree
    elif rule == 284:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(23) # comma
      tree.add(t)
      return tree
    elif rule == 287:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(114) # bitxor
      tree.add(t)
      return tree
    elif rule == 309:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(3) # or
      tree.add(t)
      return tree
    elif rule == 314:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(13) # bitoreq
      tree.add(t)
      return tree
    elif rule == 315:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(53) # bitor
      tree.add(t)
      return tree
    elif rule == 323:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(96) # arrow
      tree.add(t)
      return tree
    elif rule == 328:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(82) # lsquare
      tree.add(t)
      return tree
    elif rule == 332:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(22) # rbrace
      tree.add(t)
      return tree
    elif rule == 333:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(100) # lshift
      tree.add(t)
      return tree
    elif rule == 335:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(30) # neq
      tree.add(t)
      return tree
    elif rule == 350:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(40) # gt
      tree.add(t)
      return tree
    elif rule == 363:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(20) # rshifteq
      tree.add(t)
      return tree
    elif rule == 365:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(32) # lparen
      tree.add(t)
      return tree
    elif rule == 368:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(33) # addeq
      tree.add(t)
      return tree
    elif rule == 370:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(5) # lbrace
      tree.add(t)
      return tree
    elif rule == 384:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(31) # modeq
      tree.add(t)
      return tree
    elif rule == 392:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(26) # colon
      tree.add(t)
      return tree
    elif rule == 403:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(102) # rshift
      tree.add(t)
      return tree
    elif rule == 410:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(86) # bitxoreq
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse_parameter_declaration(self, depth=0, tracer=None):
    rule = self.rule(203)
    tree = ParseTree( NonTerminal(203, self.nonterminals[203]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 216:
      tree.astTransform = AstTransformNodeCreator('ParameterDeclaration', {'sub': 1, 'declaration_specifiers': 0})
      subtree = self.parse__gen1()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse__gen32()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse_struct_specifier(self, depth=0, tracer=None):
    rule = self.rule(204)
    tree = ParseTree( NonTerminal(204, self.nonterminals[204]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 7:
      tree.astTransform = AstTransformNodeCreator('Struct', {'definition': 1})
      t = self.expect(14) # struct
      tree.add(t)
      subtree = self.parse_struct_or_union_sub()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse__gen27(self, depth=0, tracer=None):
    rule = self.rule(205)
    tree = ParseTree( NonTerminal(205, self.nonterminals[205]))
    tree.list = 'slist'
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 131:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_parameter_declaration()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse__gen28()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse__gen28(self, depth=0, tracer=None):
    rule = self.rule(206)
    tree = ParseTree( NonTerminal(206, self.nonterminals[206]))
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in [91]):
      return tree
    if self.sym == None:
      return tree
    if rule == 133:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(23) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self.parse_parameter_declaration()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse__gen28()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def parse_pointer(self, depth=0, tracer=None):
    rule = self.rule(207)
    tree = ParseTree( NonTerminal(207, self.nonterminals[207]))
    tree.list = False
    if self.sym == None:
      return tree
    if rule == 29:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen34()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse_labeled_statement(self, depth=0, tracer=None):
    rule = self.rule(208)
    tree = ParseTree( NonTerminal(208, self.nonterminals[208]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 16:
      tree.astTransform = AstTransformNodeCreator('DefaultCase', {'statement': 2})
      t = self.expect(61) # default
      tree.add(t)
      t = self.expect(26) # colon
      tree.add(t)
      subtree = self.parse_statement()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 301:
      tree.astTransform = AstTransformNodeCreator('Case', {'expr': 1, 'statement': 3})
      t = self.expect(52) # case
      tree.add(t)
      subtree = self.parse__expr()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(26) # colon
      tree.add(t)
      subtree = self.parse_statement()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 399:
      tree.astTransform = AstTransformNodeCreator('Label', {'name': 0, 'statement': 1})
      t = self.expect(69) # label_hint
      tree.add(t)
      t = self.expect(76) # identifier
      tree.add(t)
      t = self.expect(26) # colon
      tree.add(t)
      subtree = self.parse_statement()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse_sizeof_body(self, depth=0, tracer=None):
    rule = self.rule(209)
    tree = ParseTree( NonTerminal(209, self.nonterminals[209]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 110:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(32) # lparen
      tree.add(t)
      subtree = self.parse_type_name()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(16) # rparen
      tree.add(t)
      return tree
    elif rule == 154:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(76) # identifier
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse__gen42(self, depth=0, tracer=None):
    rule = self.rule(210)
    tree = ParseTree( NonTerminal(210, self.nonterminals[210]))
    tree.list = False
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 157:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_parameter_type_list()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def parse_external_declarator(self, depth=0, tracer=None):
    rule = self.rule(211)
    tree = ParseTree( NonTerminal(211, self.nonterminals[211]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 70:
      tree.astTransform = AstTransformNodeCreator('ExternalDeclarator', {'init_declarator': 1})
      t = self.expect(87) # declarator_hint
      tree.add(t)
      subtree = self.parse__gen6()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse_iteration_statement(self, depth=0, tracer=None):
    rule = self.rule(212)
    tree = ParseTree( NonTerminal(212, self.nonterminals[212]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 11:
      tree.astTransform = AstTransformNodeCreator('For', {'init': 2, 'cond': 3, 'incr': 4, 'statement': 6})
      t = self.expect(12) # for
      tree.add(t)
      t = self.expect(32) # lparen
      tree.add(t)
      subtree = self.parse_for_init()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse_for_cond()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse_for_incr()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(16) # rparen
      tree.add(t)
      subtree = self.parse_statement()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 158:
      tree.astTransform = AstTransformNodeCreator('DoWhile', {'expr': 4, 'statement': 1})
      t = self.expect(7) # do
      tree.add(t)
      subtree = self.parse_statement()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(0) # while
      tree.add(t)
      t = self.expect(32) # lparen
      tree.add(t)
      subtree = self.parse__expr()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(16) # rparen
      tree.add(t)
      t = self.expect(8) # semi
      tree.add(t)
      return tree
    elif rule == 310:
      tree.astTransform = AstTransformNodeCreator('While', {'expr': 2, 'statement': 4})
      t = self.expect(0) # while
      tree.add(t)
      t = self.expect(32) # lparen
      tree.add(t)
      subtree = self.parse__expr()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(16) # rparen
      tree.add(t)
      subtree = self.parse_statement()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse__gen37(self, depth=0, tracer=None):
    rule = self.rule(213)
    tree = ParseTree( NonTerminal(213, self.nonterminals[213]))
    tree.list = False
    if self.sym != None and (self.sym.getId() in [0, 1, 69, 38, 32, 7, 8, 98, 12, 75, 14, 15, 17, 41, 21, 6, 85, 36, 27, 28, 115, 81, 55, 35, 5, 39, 76, 44, 46, 48, 49, 78, 67, 22, 19, 56, 58, 59, 104, 63, 65, 4, 107, 74, 42, 52, 61, 84, 71, 88, 93, 95, 97, 101, 2, 66, 111, 89]):
      return tree
    if self.sym == None:
      return tree
    if rule == 0:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_else_if_statement_list()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def parse_va_args(self, depth=0, tracer=None):
    rule = self.rule(214)
    tree = ParseTree( NonTerminal(214, self.nonterminals[214]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 119:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(91) # comma_va_args
      tree.add(t)
      t = self.expect(105) # elipsis
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse_enumerator(self, depth=0, tracer=None):
    rule = self.rule(215)
    tree = ParseTree( NonTerminal(215, self.nonterminals[215]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 243:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_enumeration_constant()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse_enumerator_assignment()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse_expression_statement(self, depth=0, tracer=None):
    rule = self.rule(216)
    tree = ParseTree( NonTerminal(216, self.nonterminals[216]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 95:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_expression_opt()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(8) # semi
      tree.add(t)
      return tree
    elif self.sym.getId() in [78, 67, 1, 93, 58, 6, 32, 65, 35, 48, 101, 74, 75, 46, 111, 76]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_expression_opt()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(8, tracer) ) # semi
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse_external_prototype(self, depth=0, tracer=None):
    rule = self.rule(217)
    tree = ParseTree( NonTerminal(217, self.nonterminals[217]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 387:
      tree.astTransform = AstTransformNodeCreator('FunctionPrototype', {'declaration_list': 2, 'declarator': 1})
      t = self.expect(99) # function_prototype_hint
      tree.add(t)
      subtree = self.parse_declarator()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse__gen5()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse_selection_statement(self, depth=0, tracer=None):
    rule = self.rule(218)
    tree = ParseTree( NonTerminal(218, self.nonterminals[218]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 21:
      tree.astTransform = AstTransformNodeCreator('If', {'elseif': 6, 'statement': 4, 'condition': 2, 'else': 7})
      t = self.expect(115) # if
      tree.add(t)
      t = self.expect(32) # lparen
      tree.add(t)
      subtree = self.parse__expr()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(16) # rparen
      tree.add(t)
      subtree = self.parse_statement()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(36) # endif
      tree.add(t)
      subtree = self.parse__gen37()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse__gen38()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 299:
      tree.astTransform = AstTransformNodeCreator('Switch', {'expr': 2, 'statment': 4})
      t = self.expect(66) # switch
      tree.add(t)
      t = self.expect(32) # lparen
      tree.add(t)
      subtree = self.parse__expr()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(16) # rparen
      tree.add(t)
      subtree = self.parse_statement()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse_direct_abstract_declarator_expr(self, depth=0, tracer=None):
    rule = self.rule(219)
    tree = ParseTree( NonTerminal(219, self.nonterminals[219]))
    tree.list = False
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 250:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_type_qualifier_list_opt()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse_static_opt()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse__expr()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 265:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(75) # asterisk
      tree.add(t)
      return tree
    elif self.sym.getId() in [78, 67, 1, 93, 58, 6, 32, 65, 35, 48, 101, 74, 75, 46, 111, 76]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_type_qualifier_list_opt()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse_static_opt()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse__expr()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    return tree
  def parse__gen38(self, depth=0, tracer=None):
    rule = self.rule(220)
    tree = ParseTree( NonTerminal(220, self.nonterminals[220]))
    tree.list = False
    if self.sym != None and (self.sym.getId() in [0, 1, 69, 38, 32, 7, 8, 98, 12, 75, 14, 15, 17, 41, 21, 6, 85, 55, 27, 28, 115, 81, 36, 35, 5, 39, 76, 44, 46, 48, 49, 78, 67, 22, 19, 56, 58, 59, 104, 63, 65, 4, 107, 74, 42, 52, 61, 84, 71, 88, 93, 95, 101, 2, 66, 111, 89]):
      return tree
    if self.sym == None:
      return tree
    if rule == 128:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_else_statement()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def parse_declarator(self, depth=0, tracer=None):
    rule = self.rule(221)
    tree = ParseTree( NonTerminal(221, self.nonterminals[221]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 379:
      tree.astTransform = AstTransformNodeCreator('Declarator', {'direct_declarator': 1, 'pointer': 0})
      subtree = self.parse_pointer_opt()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse__direct_declarator()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [83, 76, 32]:
      tree.astTransform = AstTransformNodeCreator('Declarator', {'direct_declarator': 1, 'pointer': 0})
      subtree = self.parse_pointer_opt()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse__direct_declarator()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse_abstract_declarator(self, depth=0, tracer=None):
    rule = self.rule(222)
    tree = ParseTree( NonTerminal(222, self.nonterminals[222]))
    tree.list = False
    if self.sym == None:
      return tree
    if rule == 340:
      tree.astTransform = AstTransformNodeCreator('AbstractDeclarator', {'direct_abstract_declarator': 1, 'pointer': 1})
      subtree = self.parse_pointer_opt()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse__direct_abstract_declarator()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [32, 112, -1]:
      tree.astTransform = AstTransformNodeCreator('AbstractDeclarator', {'direct_abstract_declarator': 1, 'pointer': 1})
      subtree = self.parse_pointer_opt()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse__direct_abstract_declarator()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse__gen5(self, depth=0, tracer=None):
    rule = self.rule(223)
    tree = ParseTree( NonTerminal(223, self.nonterminals[223]))
    tree.list = False
    if self.sym != None and (self.sym.getId() in [5, 8, 23]):
      return tree
    if self.sym == None:
      return tree
    if rule == 364:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_declaration_list()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def parse_token(self, depth=0, tracer=None):
    rule = self.rule(224)
    tree = ParseTree( NonTerminal(224, self.nonterminals[224]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 45:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(48) # string_literal
      tree.add(t)
      return tree
    elif rule == 76:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(76) # identifier
      tree.add(t)
      return tree
    elif rule == 263:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_punctuator()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 294:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_keyword()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 306:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(103) # pp_number
      tree.add(t)
      return tree
    elif rule == 400:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_constant()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse_jump_statement(self, depth=0, tracer=None):
    rule = self.rule(225)
    tree = ParseTree( NonTerminal(225, self.nonterminals[225]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 8:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(104) # continue
      tree.add(t)
      return tree
    elif rule == 337:
      tree.astTransform = AstTransformNodeCreator('Return', {'expr': 1})
      t = self.expect(42) # return
      tree.add(t)
      subtree = self.parse_expression_opt()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(8) # semi
      tree.add(t)
      return tree
    elif rule == 358:
      tree.astTransform = AstTransformNodeCreator('Goto', {'name': 1})
      t = self.expect(19) # goto
      tree.add(t)
      t = self.expect(76) # identifier
      tree.add(t)
      t = self.expect(8) # semi
      tree.add(t)
      return tree
    elif rule == 405:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(4) # break
      tree.add(t)
      t = self.expect(8) # semi
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse_union_specifier(self, depth=0, tracer=None):
    rule = self.rule(226)
    tree = ParseTree( NonTerminal(226, self.nonterminals[226]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 259:
      tree.astTransform = AstTransformNodeCreator('Union', {'definition': 1})
      t = self.expect(41) # union
      tree.add(t)
      subtree = self.parse_struct_or_union_sub()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse__gen30(self, depth=0, tracer=None):
    rule = self.rule(227)
    tree = ParseTree( NonTerminal(227, self.nonterminals[227]))
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 162:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_identifier()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse__gen31()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def parse__gen31(self, depth=0, tracer=None):
    rule = self.rule(228)
    tree = ParseTree( NonTerminal(228, self.nonterminals[228]))
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 165:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(23) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self.parse_identifier()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse__gen31()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def parse_pp(self, depth=0, tracer=None):
    rule = self.rule(229)
    tree = ParseTree( NonTerminal(229, self.nonterminals[229]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 66:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(103) # pp_number
      tree.add(t)
      return tree
    elif rule == 372:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(64) # defined_separator
      tree.add(t)
      return tree
    elif rule == 394:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(43) # defined
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse_init_declarator(self, depth=0, tracer=None):
    rule = self.rule(230)
    tree = ParseTree( NonTerminal(230, self.nonterminals[230]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 270:
      tree.astTransform = AstTransformNodeCreator('InitDeclarator', {'initializer': 1, 'declarator': 0})
      subtree = self.parse_declarator()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse__gen11()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [83, 76, 32]:
      tree.astTransform = AstTransformNodeCreator('InitDeclarator', {'initializer': 1, 'declarator': 0})
      subtree = self.parse_declarator()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse__gen11()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse_type_qualifier_list_opt(self, depth=0, tracer=None):
    rule = self.rule(231)
    tree = ParseTree( NonTerminal(231, self.nonterminals[231]))
    tree.list = False
    if self.sym != None and (self.sym.getId() in [23, 2, 112, 75, 83, 32, 91, 76]):
      return tree
    if self.sym == None:
      return tree
    if rule == 145:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen25()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def parse__gen6(self, depth=0, tracer=None):
    rule = self.rule(232)
    tree = ParseTree( NonTerminal(232, self.nonterminals[232]))
    tree.list = False
    if self.sym != None and (self.sym.getId() in [23, 8]):
      return tree
    if self.sym == None:
      return tree
    if rule == 389:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_init_declarator()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [83, 76, 32]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_init_declarator()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    return tree
  def parse_pointer_opt(self, depth=0, tracer=None):
    rule = self.rule(233)
    tree = ParseTree( NonTerminal(233, self.nonterminals[233]))
    tree.list = False
    if self.sym != None and (self.sym.getId() in [83, 91, 23, 76, 32, 112]):
      return tree
    if self.sym == None:
      return tree
    if rule == 249:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_pointer()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def parse_block_item_list(self, depth=0, tracer=None):
    rule = self.rule(234)
    tree = ParseTree( NonTerminal(234, self.nonterminals[234]))
    tree.list = False
    if self.sym == None:
      return tree
    if rule == 207:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen36()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [78, 67, 1, 93, 58, 6, 32, 65, 35, 48, 101, 74, 75, 46, 111, 76]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen36()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse__gen35(self, depth=0, tracer=None):
    rule = self.rule(236)
    tree = ParseTree( NonTerminal(236, self.nonterminals[236]))
    tree.list = False
    if self.sym != None and (self.sym.getId() in [22]):
      return tree
    if self.sym == None:
      return tree
    if rule == 181:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_block_item_list()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif self.sym.getId() in [78, 67, 1, 93, 58, 6, 32, 65, 35, 48, 101, 74, 75, 46, 111, 76]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_block_item_list()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
    return tree
  def parse_struct_or_union_body(self, depth=0, tracer=None):
    rule = self.rule(237)
    tree = ParseTree( NonTerminal(237, self.nonterminals[237]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 361:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(5) # lbrace
      tree.add(t)
      subtree = self.parse__gen17()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(22) # rbrace
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse_compound_statement(self, depth=0, tracer=None):
    rule = self.rule(238)
    tree = ParseTree( NonTerminal(238, self.nonterminals[238]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 344:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(5) # lbrace
      tree.add(t)
      subtree = self.parse__gen35()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(22) # rbrace
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse_declaration(self, depth=0, tracer=None):
    rule = self.rule(239)
    tree = ParseTree( NonTerminal(239, self.nonterminals[239]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 177:
      tree.astTransform = AstTransformNodeCreator('Declaration', {'init_declarators': 1, 'declaration_specifiers': 0})
      subtree = self.parse__gen1()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse__gen8()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(8) # semi
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse_else_if_statement(self, depth=0, tracer=None):
    rule = self.rule(240)
    tree = ParseTree( NonTerminal(240, self.nonterminals[240]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 280:
      tree.astTransform = AstTransformNodeCreator('ElseIf', {'statement': 4, 'condition': 2})
      t = self.expect(11) # else_if
      tree.add(t)
      t = self.expect(32) # lparen
      tree.add(t)
      subtree = self.parse__expr()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(16) # rparen
      tree.add(t)
      subtree = self.parse_statement()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(36) # endif
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse__gen7(self, depth=0, tracer=None):
    rule = self.rule(241)
    tree = ParseTree( NonTerminal(241, self.nonterminals[241]))
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [5, 8, 23]):
      return tree
    if self.sym == None:
      return tree
    if rule == 2:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_declaration()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse__gen7()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def parse_for_cond(self, depth=0, tracer=None):
    rule = self.rule(242)
    tree = ParseTree( NonTerminal(242, self.nonterminals[242]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 376:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(8) # semi
      tree.add(t)
      subtree = self.parse_expression_opt()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
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
