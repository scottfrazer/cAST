import unittest, os, subprocess, re
from cast.ppParser import Parser as ppParser
from cast.cParser import Parser as cParser
from cast.ppLexer import ppLexer
from cast.cLexer import cLexer
from cast.Ast import AstPrettyPrintable, ParseTreePrettyPrintable
from cast.PreProcessor import Factory as PreProcessorFactory
from cast.SourceCode import SourceCode, SourceCodeString

directory = 'test/cases'

class CastTest(unittest.TestCase):

  def __init__(self, path=None, expectedPath=None, actualFunc=None):
    super().__init__()
    self.__dict__.update(locals())
    self.maxDiff = None

  def runTest(self):
    fp = open(self.expectedPath)
    expected = fp.read().rstrip()
    fp.close()
    self.assertEqual(expected, self.actualFunc(), 'failed to match %s (%s)' % (self.path, self.expectedPath))

class CastVersusGccTest(unittest.TestCase):

  def __init__(self, arg=None, filepath=None):
    super().__init__(arg)
    self.__dict__.update(locals())
    self.maxDiff = None

  def getCastOutput(self):
    cPPFactory = PreProcessorFactory()
    cPP = cPPFactory.create([], [self.filepath])
    filepath = os.path.join(self.filepath, 'source.c')
    sourcecode = SourceCode(filepath, open(filepath))
    cT, symbols = cPP.process( sourcecode, dict() )
    actualTokens = list(map(mapFuncSimple, list(cT)))
    return '\n'.join(actualTokens)

  def getGccOutput(self):
    regex = re.compile(r'^\#.*$', re.M)
    null = open('/dev/null', 'w')
    filepath = os.path.join(self.filepath, 'source.c')
    gcc = subprocess.check_output(['gcc', '-std=c99', '-E', filepath], stderr=null)
    null.close()
    gcc = gcc.decode('ascii')
    gcc = regex.sub('', gcc)
    sourcecode = SourceCodeString('<string>', gcc)
    cL = cLexer(sourcecode)
    actualTokens = list(map(mapFuncSimple, list(cL)))
    return '\n'.join(actualTokens)

  def test_doesCastPreprocessExactlyLikeGccDoes(self):
    filepath = os.path.join(directory, self.filepath)
    self.assertEqual(self.getGccOutput(), self.getCastOutput(), \
        "File %s didn't parse the same in GCC and cAST" % (filepath) )

def mapFunc(x):
  return "%s,%s,%s,%s,%s" % (x.getTerminalStr(), x.getLine(), x.getColumn(), x.getString().replace('\n', '\\n'), x.getResource())

def mapFuncSimple(x):
  return "%s|%s" % (x.getTerminalStr(), x.getString().replace('\n', '\\n'))

def pptok(sourcecode, skipIncludes=False):
  cPPL = ppLexer(sourcecode)
  actualTokens = list(map(mapFunc, list(cPPL)))
  return '\n'.join(actualTokens)

def ppparse(sourcecode, skipIncludes=False):
  cPPL = ppLexer(sourcecode)
  parsetree = ppParser().parse(cPPL)
  prettyprint = str(ParseTreePrettyPrintable(parsetree, 'type'))
  return prettyprint

def ppast(sourcecode, skipIncludes=False):
  cPPL = ppLexer(sourcecode)
  ast = ppParser().parse(cPPL).toAst()
  prettyprint = str(AstPrettyPrintable(ast, 'type'))
  return prettyprint

def ctok(sourcecode, skipIncludes=False):
  cPPFactory = PreProcessorFactory()
  cPP = cPPFactory.create([], [os.path.dirname(sourcecode.resource)])
  cT, symbols = cPP.process( sourcecode, dict(), skipIncludes=skipIncludes )
  actualTokens = list(map(mapFunc, list(cT)))
  return '\n'.join(actualTokens)

def cparse(sourcecode, skipIncludes=False):
  cPPFactory = PreProcessorFactory()
  cPP = cPPFactory.create([], [os.path.dirname(sourcecode.resource)])
  cT, symbols = cPP.process( sourcecode, dict(), skipIncludes=skipIncludes )
  parsetree = cParser().parse(cT)
  prettyprint = str(ParseTreePrettyPrintable(parsetree, 'type'))
  return prettyprint

def cast(sourcecode, skipIncludes=False):
  cPPFactory = PreProcessorFactory()
  cPP = cPPFactory.create([], [os.path.dirname(sourcecode.resource)])
  cT, symbols = cPP.process( sourcecode, dict(), skipIncludes=skipIncludes )
  ast = cParser().parse(cT).toAst()
  prettyprint = str(AstPrettyPrintable(ast, 'type'))
  return prettyprint

def preprocessed(sourcecode, skipIncludes=False):
  cPPFactory = PreProcessorFactory()
  cPP = cPPFactory.create([], [os.path.dirname(sourcecode.resource)])
  cT, symbols = cPP.process( sourcecode, dict(), skipIncludes=skipIncludes )
  return cT.toString()
  
transformations = [
  ('pptok', pptok),
  ('ppparse', ppparse),
  ('ppast', ppast),
  ('ctok', ctok),
  ('cparse', cparse),
  ('cast', cast),
  ('preprocessed', preprocessed)
]

def load_tests(loader, tests, pattern):
  testDirectories = os.listdir(directory)
  suite = unittest.TestSuite()
  for path in testDirectories:
    try:
      int(path)
    except ValueError:
      continue
    path = os.path.join(directory, path)
    sourcePath = os.path.join(path, 'source.c')
    sourcecode = SourceCode(sourcePath, open(sourcePath))
    options = []
    if sourcecode.sourceCode[:2] == '//':
      options = sourcecode.sourceCode[2:sourcecode.sourceCode.find('\n')].strip().split(' ')
    skipIncludes = False
    if 'no-includes' in options:
      skipIncludes = True
    if 'no-gcc' not in options:
      suite.addTest(CastVersusGccTest('test_doesCastPreprocessExactlyLikeGccDoes', path))
    for (expected, transformFunction) in transformations:
      expectedPath = os.path.join(path, expected)
      def func(sourcecode, transformFunction, skipIncludes):
        def ret():
          return transformFunction(sourcecode, skipIncludes).rstrip()
        return ret
      actual = transformFunction(sourcecode, skipIncludes).rstrip()
      if not os.path.exists(expectedPath):
        fp = open(expectedPath, 'w')
        fp.write(actual + '\n')
        fp.close()
      suite.addTest( CastTest(path, expectedPath, func(sourcecode,transformFunction, skipIncludes)) )
  return suite
