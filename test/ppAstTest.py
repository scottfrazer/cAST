import unittest, os
from CastTest import CastTest
from cast.Token import ppToken

class ppAstTest(CastTest):

  def __init__(self, filename):
    super(ppAstTest, self).__init__('test_ppAst')
    self.__dict__.update(locals())

  def test_ppAst(self):
    csource = os.path.join('c', self.filename)
    ppast = os.path.join('c', self.filename + '.ppast')

    if not os.path.isfile(ppast):
      fp = open( csource )
      contents = fp.read()
      fp.close()
      self.write_ppast(ppast, contents)

    if os.path.isfile(csource) and os.path.isfile(ppast):

      fp = open( csource )
      contents = fp.read()
      fp.close()

      fp = open( ppast )
      expected = fp.read()
      fp.close()

      self.assert_ppast( contents, expected )

def load_tests(loader, tests, pattern):
    files = list(filter(lambda x: x.endswith('.c'), os.listdir('c')))
    suite = unittest.TestSuite()
    for filename in files:
      suite.addTest( ppAstTest(filename) )
    return suite

if __name__ == '__main__':
  unittest.main()

