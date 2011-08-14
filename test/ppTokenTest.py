import unittest, os
from CastTest import CastTest
from cast.Token import ppToken

class ppTokenTest(CastTest):

  def __init__(self, filename):
    super(ppTokenTest, self).__init__('test_ppTokens')
    self.__dict__.update(locals())

  def test_ppTokens(self):
    csource = os.path.join('c', self.filename)
    pptokens = os.path.join('c', self.filename + '.pptok')

    if not os.path.isfile(pptokens):
      self.write_pptok(pptokens)

    if os.path.isfile(csource) and os.path.isfile(pptokens):

      fp = open( csource )
      contents = fp.read()
      fp.close()

      fp = open( pptokens )
      expected = list(filter(lambda x: len(x), fp.read().split('\n')))
      fp.close()

      self.assert_pptok( contents, expected )

def load_tests(loader, tests, pattern):
    files = list(filter(lambda x: x.endswith('.c'), os.listdir('c')))
    suite = unittest.TestSuite()
    for filename in files:
      suite.addTest( ppTokenTest(filename) )
    return suite

if __name__ == '__main__':
  unittest.main()
