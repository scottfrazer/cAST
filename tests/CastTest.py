import unittest, os, subprocess, re
from cast.ppParser import Parser as ppParser
from cast.ppLexer import ppLexer
from cast.cLexer import cLexer
from cast.Ast import AstPrettyPrintable
from cast.PreProcessor import Factory as PreProcessorFactory
from cast.SourceCode import SourceCode, SourceCodeString

directory = 'tests/cases'

class CastTest(unittest.TestCase):

  def __init__(self, arg=None, expected=None, actual=None):
    super().__init__(arg)
    self.__dict__.update(locals())
    self.maxDiff = None

  def test_isCorrect(self):
    self.assertEqual(self.actual, self.expected)

class CastVersusGccTest(unittest.TestCase):

  def __init__(self, arg=None, filepath=None):
    super().__init__(arg)
    self.__dict__.update(locals())
    self.maxDiff = None

  def getCastOutput(self, filepath):
    cPPFactory = PreProcessorFactory()
    cPP = cPPFactory.create([], ['tests/cases'])
    sourcecode = SourceCode(filepath, open(filepath))
    cT, symbols = cPP.process( sourcecode, dict() )
    actualTokens = list(map(mapFuncSimple, list(cT)))
    return '\n'.join(actualTokens)

  def getGccOutput(self, filepath):
    regex = re.compile(r'^\#.*$', re.M)
    null = open('/dev/null', 'w')
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
    self.assertEqual(self.getGccOutput(filepath), self.getCastOutput(filepath), \
        "File %s didn't parse the same in GCC and cAST" % (filepath) )

def mapFunc(x):
  return "%s,%s,%s,%s,%s" % (x.getTerminalStr(), x.getLine(), x.getColumn(), x.getString().replace('\n', '\\n'), x.getResource())

def mapFuncSimple(x):
  return "%s|%s" % (x.getTerminalStr(), x.getString().replace('\n', '\\n'))

def pptok(sourcecode):
  cPPL = ppLexer(sourcecode)
  actualTokens = list(map(mapFunc, list(cPPL)))
  return '\n'.join(actualTokens)

def ppast(sourcecode):
  cPPL = ppLexer(sourcecode)
  ast = ppParser().parse(cPPL).toAst()
  prettyprint = str(AstPrettyPrintable(ast, 'type'))
  return prettyprint

def ctok(sourcecode):
  cPPFactory = PreProcessorFactory()
  cPP = cPPFactory.create([], [directory])
  cT, symbols = cPP.process( sourcecode, dict() )
  actualTokens = list(map(mapFunc, list(cT)))
  return '\n'.join(actualTokens)
  
transformations = [
  ('pptok', pptok),
  ('ppast', ppast),
  ('ctok', ctok)
]

def load_tests(loader, tests, pattern):
  files = list(filter(lambda x: x.endswith('.c'), os.listdir(directory)))
  suite = unittest.TestSuite()
  for path in files:
    suite.addTest(CastVersusGccTest('test_doesCastPreprocessExactlyLikeGccDoes', path))
    for (extension, transformFunction) in transformations:
      expectedPath = os.path.join(directory, path + '.' + extension)
      sourcePath = os.path.join(directory, path)
      sourcecode = SourceCode(path, open(sourcePath))
      actual = transformFunction(sourcecode)
      if not os.path.exists(expectedPath):
        fp = open(expectedPath, 'w')
        fp.write(actual)
        fp.close()
      expected = open(expectedPath).read()
      suite.addTest( CastTest('test_isCorrect', expected, actual) )
  return suite
