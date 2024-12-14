# Set the path to the ANTLR jar here:
ANTLR=/usr/local/lib/antlr4.jar
# This line might get overwritten by the vmchecker.

TESTS_PATH=./tests/tema1
TESTS_PATH=./tests/tema2
TESTS_PATH=./tests/tema3

# EXTRA_FILES=$(TESTS_PATH)/main.cl

#
# Main rules:
#
# * build - Cmakompiles everything
# * test - Runs the automated tester
# * clean - Deletes binary files and test-output files 
# * run ARGS=<file> - call compiler
#
.PHONY: build run run-lexer test zip clean 

build: cool/lexer/CoolLexer.py cool/parser/CooLParser.py

cool/lexer/CoolLexer.py: cool/lexer/CoolLexer.g4 
	antlr4 -v 4.13.1 -Dlanguage=Python3 cool/lexer/CoolLexer.g4 -o cool/lexer
	cp cool/lexer/CoolLexer.tokens cool/parser/

cool/parser/CoolParser.py: cool/parser/CoolParser.g4 cool/lexer/CoolLexer.py
	antlr4 -v 4.13.1 -Dlanguage=Python3 -listener -visitor -o cool/parser -lib cool/lexer cool/parser/CoolParser.g4 

clean:
	rm -rf cool/.antlr/ cool/parser/.antlr/ cool/lexer/.antlr/
	rm -rf cool/__pycache__  cool/parser/__pycache__  cool/lexer/__pycache__
	rm cool/*/*.interp   cool/lexer/*.py cool/parser/*.py   cool/*/*.tokens
	rm -f $(TESTS_PATH)/*.out out temp

run: build
	python -X utf8 cool/Compiler.py $(ARGS)