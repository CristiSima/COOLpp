parser grammar CoolParser;

options {
    tokenVocab = CoolLexer;
}





program
    :   class+ EOF 
    ; 

class
    : CLASS class_name=TYPE (INHERITS base_class=TYPE)? LBRACE (features+=feature SEMI)* RBRACE SEMI
    ;

feature
    : function_name=ID  LPAREN ( args+=formal ( COMMA args+=formal)* )? 
                        RPAREN COLON return_type=TYPE LBRACE body=expr RBRACE   # function_definition
    | attribute_name=ID COLON attribute_type=TYPE ( ASSIGN default=expr)?       # attribute_definition
    ;

formal
    : var_name=ID COLON type_name=TYPE
    ;

let_entry
    : var_name=ID COLON var_type=TYPE (ASSIGN default_value=expr)?
    ;

expr
    : target=expr ( AT parent_class=TYPE )? DOT method=ID LPAREN (args+=expr (COMMA args+=expr)* )? RPAREN  # explicit_function_call
    | NEGATE target=expr                                                                                    # negate
    | ISVOID target=expr                                                                                    # isvoid
    | expr1=expr operator=( MULT | DIV ) expr2=expr                                                         # arithm1
    | expr1=expr operator=( PLUS | MINUS ) expr2=expr                                                       # arithm2
    | expr1=expr comparator=( LT | LE | EQUAL ) expr2=expr                                                  # compare
    | NOT target=expr                                                                                       # not
    | target=ID ASSIGN value=expr                                                                           # assignment
    | method=ID LPAREN (args+=expr (COMMA args+=expr)* )? RPAREN                                            # implicit_function_call
    | IF cond=expr THEN if_true=expr ELSE if_false=expr FI                                                  # if
    | WHILE cond=expr LOOP action=expr POOL                                                                 # while
    | LBRACE (expresions+=expr SEMI)+ RBRACE                                                                # block
    | LET entries+=let_entry (COMMA entries+=let_entry )* IN expresion=expr                                 # let
    | CASE target=expr OF (var_names+=ID COLON check_types+=TYPE ARROW actions+=expr SEMI)+ ESAC            # case
    | LPAREN target=expr RPAREN                                                                             # paren
    | NEW class_name=TYPE                                                                                   # new
    | name=ID                                                                                               # id
    | value=INT                                                                                             # int
    | value=STRING                                                                                          # string
    | value=BOOL                                                                                            # bool
    ;