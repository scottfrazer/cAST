import sys

try:
  from hermes.GrammarFileParser import GrammarFileParser, HermesParserFactory
  from hermes.GrammarCodeGenerator import PythonTemplate
except:
  sys.stderr.write('Hermes is not installed.  Cannot bootstrap.\n')
  sys.exit(-1)

grammars = [
  ('cast/ppParser.py', 'grammars/pp.zgr', 'pp_file'),
  ('cast/cParser.py', 'grammars/c.zgr', 'translation_unit')
]

for outFile, grammarFile, start in grammars:
  print('generating grammar %s -> %s' % (grammarFile, outFile))
  grammarFileParser = GrammarFileParser(HermesParserFactory().create())
  grammar = grammarFileParser.parse( open(grammarFile), start )
  template = PythonTemplate()
  code = template.render(grammar)
  fp = open(outFile, 'w')
  fp.write(code)
  fp.close()

import setup
