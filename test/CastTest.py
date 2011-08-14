import unittest
from cast.ppLexer import Factory as ppLexerFactory

def dataProvider(fn_data_provider):
    def test_decorator(fn):
        def repl(self, *args):
            for i in fn_data_provider():
                try:
                    fn(self, *i)
                except AssertionError:
                    print("Assertion error caught with data set ", i)
                    raise
        return repl
    return test_decorator

class CastTest(unittest.TestCase):
  def get_ppLexer(self, sourceString):
    cPPLFactory = ppLexerFactory()
    cPPL = cPPLFactory.create()
    cPPL.setString(sourceString)
    return cPPL

  def assert_pptok(self, sourceString, expectedTokens):
    cPPL = self.get_ppLexer(sourceString)
    mapFunc = lambda x: '%s,%s,%s' % (x.getTerminalStr(), x.getLine(), x.getColumn())
    actualTokens = list(map(mapFunc, list(cPPL)))
    self.assertEqual(actualTokens, expectedTokens)
  
  def write_pptok(self, path, sourceString):
    cPPL = self.get_ppLexer(sourceString)
    mapFunc = lambda x: '%s,%s,%s' % (x.getTerminalStr(), x.getLine(), x.getColumn())
    actualTokens = list(map(mapFunc, list(cPPL)))
    fp = open(path, 'w')
    fp.write('\n'.join(actualTokens))
    fp.close()
