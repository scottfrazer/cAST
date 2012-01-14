CGRAMMAR=../../../grammars/c.zgr
CPPGRAMMAR=../../../grammars/pp.zgr

all: c cpp

c: c_tokens c_parser_c c_parser_py

cpp: cpp_tokens cpp_parser_c cpp_parser_py

c_tokens:
	cast ctok source.c --format=terminal | python -c "import sys;print(','.join(filter(lambda x:x, sys.stdin.read().split('\n'))))" > make_ctokens

cpp_tokens:
	cast pptok source.c --format=terminal | python -c "import sys;print(','.join(filter(lambda x:x, sys.stdin.read().split('\n'))))" > make_pptokens

cpp_parser_c: $(CPPGRAMMAR) cpp_tokens
	hermes generate $(CPPGRAMMAR) --language=c --tokens=`cat make_pptokens` --add-main
	gcc -o cppparser parser.c -g
	mv parser.c cppparser.c
	mv parser.h cppparser.h

cpp_parser_py: $(CPPGRAMMAR) cpp_tokens
	hermes generate $(CPPGRAMMAR) --language=python --tokens=`cat make_pptokens` --add-main

c_parser_c: $(CGRAMMAR) c_tokens
	hermes generate $(CGRAMMAR) --language=c --tokens=`cat make_ctokens` --add-main
	gcc -o cparser parser.c -g
	mv parser.c cparser.c
	mv parser.h cparser.h

c_parser_py: $(CGRAMMAR) c_tokens
	hermes generate $(CGRAMMAR) --language=python --tokens=`cat make_ctokens` --add-main

clean:
	-rm -rf make_ctokens make_pptokens cparser.c cparser.h cppparser.c cppparser.h cparser cppparser Parser.py hermes.log cast.log *.dSYM
