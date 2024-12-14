lexer grammar CoolLexer;



tokens { ERROR } 

ERROR
    : '*)' {self.text="Unmatched *)" }
    | '"' ~["\u0000EOF]* [\u0000]+ ~["\u0000EOF]* ["\nEOF] {self.mark_error("String contains null character") }
    // | '"' (~[\n"])* (EOF) { print(12355) }
    // | '"' ~[\n"]* (EOF) { self._type,self._text=self.ERROR,"EOF in string constant" }
    // | '"' ('\\\n'|~[\n"])* ('\n') { self.text="Unterminated string constant" }
    ;

// integrated in Compiler.py in class CoolLexer
// as a result of antler's python code gen limitations
// 
// @lexer::members {    
//     def mark_error(self, msg):
//         self.type=self.ERROR
//         self.text=msg
//         return msg
// 
//     def clean_text(self, raw):
// 
//         if len(raw) >= 1024:
//             return mark_error("String constant too long")
//         return raw
// }



IF : [iI][fF];
THEN : [tT][hH][eE][nN];
ELSE : [eE][lL][sS][eE];
FI: [fF][iI];

NEW: [nN][eE][wW];
CLASS: [cC][lL][aA][sS][sS];
INHERITS: [iI][nN][hH][eE][rR][iI][tT][sS];
fragment SELF_TYPE: 'SELF_TYPE';

IN: [iI][nN];
OF: [oO][fF];
ISVOID: [iI][sS][vV][oO][iI][dD];

LET: [lL][eE][tT];
WHILE: [wW][hH][iI][lL][eE];
LOOP: [lL][oO][oO][pP];
POOL: [pP][oO][oO][lL];
CASE: [cC][aA][sS][eE];
ESAC: [eE][sS][aA][cC];

NOT : [nN][oO][tT];
BOOL : 'true' | 'false';

TYPE : 'Int' | 'Bool' | 'IO' | 'Object' | SELF_TYPE | [A-Z](LETTER | '_' | DIGIT)*;

/* Identificator.
 */
fragment LETTER : [a-zA-Z];
ID : [a-z](LETTER | '_' | DIGIT)*;

fragment DIGIT : [0-9];
INT : DIGIT+;

STRING : '"' ('\\"'|'\\\n' | . )*? ('"' {self.text=self.clean_string(self.text)}|'\n' {self.mark_error("Unterminated string constant")} |EOF {self.mark_error("EOF in string constant")} );

SEMI : ';';

COLON : ':';

COMMA : ',';

DOT : '.';

ASSIGN : '<-';

AT : '@';

LPAREN : '(';

RPAREN : ')';

LBRACE : '{';

RBRACE : '}';

NEGATE : '~';

PLUS : '+';

MINUS : '-';

MULT : '*';

DIV : '/';

EQUAL : '=';

LT : '<';

LE : '<=';

ARROW : '=>';

fragment NEW_LINE : '\r'? '\n';

LINE_COMMENT
    : '--' .*? (NEW_LINE | EOF) -> skip
    ;

BLOCK_COMMENT
    : '(*'
      (BLOCK_COMMENT | .)*?
      ('*)' {self.skip()} | EOF {self.type=self.ERROR;self.text="EOF in comment" }) 
    ;

WS
    :   [ \n\f\r\t]+ -> skip
    ; 