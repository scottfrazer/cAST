from types import *
import sys, os, argparse, subprocess, re, logging
from cast.ppLexer import ppLexer
from cast.PreProcessor import Factory as PreProcessorFactory
from cast.ppParser import Parser as ppParser
from cast.ppParser import TokenStream
from cast.Ast import AstPrettyPrintable, ParseTreePrettyPrintable
from cast.SourceCode import SourceCode
from cast.Logger import Factory as LoggerFactory
from cast.cParser import Parser as cParser

def Cli():

  ver = sys.version_info

  # Version 3.2 required for argparse
  if ver.major < 3 or (ver.major == 3 and ver.minor < 2):
    print("Python 3.2+ required. %d.%d.%d installed" %(ver.major, ver.minor, ver.micro))
    sys.exit(-1)

  parser = argparse.ArgumentParser(
              description = 'cAST: C Preprocessor and Parser',
              epilog = '(c) 2011 Scott Frazer')

  commands = dict()
  subparsers = parser.add_subparsers(help='Available actions', dest='command')
  commands['pp'] = subparsers.add_parser('pp', help='Preprocess.')
  commands['pptok'] = subparsers.add_parser('pptok', help='Tokenize C preprocessor.')
  commands['ppast'] = subparsers.add_parser('ppast', help='Parse C preprocessor.')
  commands['ctok'] = subparsers.add_parser('ctok', help='Preprocess and tokenize C code.')
  commands['cparse'] = subparsers.add_parser('cparse', help='Parse C code')
  commands['ast'] = subparsers.add_parser('ast', help='Parse C code and transform parse tree into an AST')
  commands['dev'] = subparsers.add_parser('dev', help='Developers test area.')

  parser.add_argument('source_file',
              metavar = 'SOURCE_FILE',
              nargs = 1,
              help = 'C Source File')
  
  parser.add_argument('-d', '--debug',
              action='store_true',
              help = 'Writes debug information')
  
  parser.add_argument('--skip-includes',
              action='store_true',
              help = 'Don\'t process #include directives')
  
  parser.add_argument('-e', '--encoding',
              help = 'File encoding')

  parser.add_argument('-f', '--format',
              default = 'long',
              help = "'tiny', 'short', 'long' for outputting tokens.")

  parser.add_argument('-I', '--include-path',
              default = '',
              help = "A path containing the list of directories separated by colons.")

  parser.add_argument('-c', '--color',
              action='store_true',
              help = "Colorize output to stdout.")

  parser.add_argument('--highlight',
              help = "Colorize tokens belonging to this AST node.")

  cli = parser.parse_args()
  logger = LoggerFactory().initialize(cli.debug)
  logger.debug('CLI Parameters: %s' % (cli))

  if not os.path.isfile( cli.source_file[0] ) and \
     not os.path.islink( cli.source_file[0] ):
    sys.stderr.write("Error: Source file does not exist\n")
    sys.exit(-1)

  if not len(cli.source_file) or not cli.source_file[0]:
    cSourcePath = open('/dev/stdin')
  else:
    cSourcePath = cli.source_file[0]

  try:
    cSourceFp = open(cSourcePath, encoding='utf-8')
  except UnicodeDecodeError:
    cSourceFp = open(cSourcePath, encoding='iso-8859-1')

  cSourceCode = SourceCode(cSourcePath, cSourceFp)

  target = subprocess.check_output(["gcc", "-dumpmachine"]).decode('ascii').strip()
  include_path_global = ['/usr/include', '/usr/local/include', 'usr/' + target + '/include']
  include_path_global.extend( list(filter(lambda x: x, cli.include_path.split(':'))) )
  include_path_local = [os.path.dirname(os.path.abspath(cSourcePath))]

  cPPFactory = PreProcessorFactory()
  cPP = cPPFactory.create( include_path_global, include_path_local, skipIncludes=cli.skip_includes )

  if cli.command == 'dev':
    from cast.Theme import XTermColorMapper
    xterm = XTermColorMapper()
    converted = xterm.convert(0xff87ff)
    print(converted)

  if cli.command == 'pp':
    try:
      (cT, symbols) = cPP.process(cSourceCode)
      parser = cParser()
      parsetree = parser.parse(TokenStream(cT))
      ast = parsetree.toAst()
      print(cT.toString(ast, highlight=cli.highlight))
    except Exception as e:
      print(e, '\n', e.tracer)
      sys.exit(-1)

  if cli.command == 'pptok':
    for token in ppLexer(cSourceCode):
      print(token.toString(cli.format))

  if cli.command == 'ppast':
    from cast.ppParser import Parser as ppParser
    try:
      cPPLFactory = ppLexerFactory()
      cPPL = cPPLFactory.create()
      cPPL.setSourceCode(cSourceCode)
      parser = ppParser()
      parsetree = parser.parse(cPPL, 'pp_file')
      ast = parsetree.toAst()
      print(AstPrettyPrintable(ast, cli.format))
    except Exception as e:
      print(e, '\n', e.tracer)
      sys.exit(-1)

  if cli.command == 'ctok':
    try:
      cT, symbols = cPP.process( cSourceCode )
      for token in cT:
        print(token.toString(cli.format))
    except Exception as e:
      print(e, '\n', e.tracer)
      sys.exit(-1)

  if cli.command == 'cparse':
    try:
      cT, symbols = cPP.process( cSourceCode )
      parsetree = cParser().parse(TokenStream(cT))
      print(ParseTreePrettyPrintable(parsetree, cli.format, color=cli.color))
    except Exception as e:
      print(e, '\n', e.tracer)
      sys.exit(-1)

  if cli.command == 'ast':
    try:
      cT, symbols = cPP.process( cSourceCode )
      parser = cParser()
      parsetree = parser.parse(TokenStream(cT))
      ast = parsetree.toAst()
      print(AstPrettyPrintable(ast, cli.format, color=cli.color))
    except Exception as e:
      print(e, '\n', e.tracer)
      sys.exit(-1)

if __name__ == '__main__':
    Cli()
