import sys

try:
  from hermes.GrammarCodeGenerator import TemplateWriter
  from hermes.GrammarCodeGenerator import FactoryFactory as TemplateFactoryFactory
  from hermes.GrammarFileParser import GrammarFileParser, HermesParserFactory
except:
  sys.stderr.write('Hermes is not installed.  Cannot bootstrap.\n')
  sys.exit(-1)

grammars = [
  ('pp', 'grammars/pp.zgr'),
  ('c', 'grammars/c.zgr')
]

cGrammars = []
for name, grammarFile in grammars:
  print('generating parser for grammar %s' % (grammarFile))
  grammarFileParser = GrammarFileParser(HermesParserFactory().create())
  cGrammars.append( grammarFileParser.parse( name, open(grammarFile) ) )

templateFactory = TemplateFactoryFactory().create('python')
templateWriter = TemplateWriter(templateFactory)
templateWriter.write(cGrammars, 'cast', addMain=False)

import setup
