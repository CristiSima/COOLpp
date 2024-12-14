from typing import Union
from functools import wraps
from antlr4.Lexer import Token
from ASTVisitor import *
from ASTNode import *
from pathlib import Path


__all__ = [
    "PopulateScopeVisitor"
]

def populate_global_scope(scope: Scope):
    '''parse a minimal AST defining the builtin types and methods
    IO, Int, Bool and String are created with Object as the scope_parent
    '''
    # global is used to avoid searching in local scope 
    Id = DummyClass(globals()["Id"])
    Type = DummyClass(globals()["Type"])
    SelfType = DummyClass(globals()["SelfType"])

    Object = Class(Type("Object"), None, [
        FunctionDefinition(Id("abort"), [], Type("Object"), None), 
        FunctionDefinition(Id("type_name"), [], Type("String"), None), 
        FunctionDefinition(Id("copy"), [], SelfType(), None), 
    ])
    PopulateScopeVisitor.visit(Object, scope)

    PopulateScopeVisitor.visit(Class(Type("IO"), Type("Object"), [
        FunctionDefinition(
            Id("out_string"), [
                FunctionParameter(Id("x"), Type("String")),
            ],
            SelfType(), None
        ), 
        FunctionDefinition(
            Id("out_int"), [
                FunctionParameter(Id("x"), Type("Int")),
            ],
            SelfType(), None
        ), 
        FunctionDefinition(Id("in_string"), [], Type("String"), Type("Object")),
        FunctionDefinition(Id("in_int"), [], Type("Int"), Type("Object")),
    ]), Object, scope)

    PopulateScopeVisitor.visit(Class(Type("Int"), Type("Object"), [
    ]), Object, scope)

    PopulateScopeVisitor.visit(Class(Type("Bool"), Type("Object"), [
    ]), Object, scope)

    PopulateScopeVisitor.visit(Class(Type("String"), Type("Object"), [
        FunctionDefinition(Id("length"), [], Type("Int"), None),
        FunctionDefinition(
            Id("concat"), [
                FunctionParameter(Id("s"), Type("String")),
            ],
            Type("String"), None
        ), 
        FunctionDefinition(
            Id("substr"), [
                FunctionParameter(Id("i"), Type("Int")),
                FunctionParameter(Id("l"), Type("Int")),
            ],
            Type("String"), None
        ), 

    ]), Object, scope)


def sets_scope_parent(function: callable):
    @wraps(function)
    def temp(node: Scope, scope: Scope, *args):
        node.scope_parent = scope
    
        return function(node, scope, *args)

    return temp


class PopulateScopeVisitor(ASTVisitor):
    errors: bool
    def semanticError(token: Token, msg: str):
        token: Token
        filename=Path(token.source[1].fileName).name
        print(f"\"{filename}\", line {token.line}:{token.column+1}, Semantic error: {msg}")
        __class__.errors = True

    @AST_visits(Program)
    def visitProgram(program: Program):
        program: Program
        __class__.errors = False
        populate_global_scope(program)

        for class_ in program.classes:
            __class__.visit(class_, program)

    @AST_visits(Class)
    @sets_scope_parent
    def visitClass(class_: Class, scope: Scope, global_scope: Scope = None):
        class_: Class
        global_scope = global_scope or scope

        if isinstance(class_.name, SelfType):
            return __class__.semanticError(class_.name.token, "Class has illegal name SELF_TYPE")

        if not global_scope.add(class_.name.value, class_):
            return __class__.semanticError(class_.name.token, f"Class {class_.name.value} is redefined")

        class_.add("self", class_)
        class_.add("SELF_TYPE", class_)
        __class__.visit(class_.name, scope)

        __class__.visit(class_.base_class, class_)

        for feature in class_.features:
            __class__.visit(feature, class_)

    @AST_visits(FunctionDefinition)
    @sets_scope_parent
    def visitFunctionDefinition(functionDefinition: FunctionDefinition, scope: Scope):
        functionDefinition: FunctionDefinition

        for parameter in functionDefinition.parameters:
            __class__.visit(parameter, functionDefinition)

        if not scope.add_function(functionDefinition.name.value, functionDefinition):
            return __class__.semanticError(functionDefinition.name.token,
                f"Class {scope.name.value} redefines method {functionDefinition.name.value}"
            )

        __class__.visit(functionDefinition.body, functionDefinition)
        __class__.visit(functionDefinition.return_type, scope)
    
    @AST_visits(FunctionParameter)
    def visitFunctionParameter(functionParameter: FunctionParameter, scope: FunctionDefinition):
        functionParameter: FunctionParameter
        error_msg_base = f"Method {scope.name.value} of class {scope.scope_parent.name.value}"
        
        if functionParameter.name.value == "self":
            return __class__.semanticError(functionParameter.name.token,
                f"{error_msg_base} has formal parameter with illegal name self"
            )
        
        if isinstance(functionParameter.type, SelfType):
            return __class__.semanticError(functionParameter.type.token,
                f"{error_msg_base} has formal parameter {functionParameter.name.value} "
                + f"with illegal type SELF_TYPE"
            )
        
        if not scope.add(functionParameter.name.value, functionParameter):
            return __class__.semanticError(functionParameter.name.token,
                f"{error_msg_base} redefines formal parameter {functionParameter.name.value}"
            )

        __class__.visit(functionParameter.type, scope)

    @AST_visits(AttributeDefinition)
    def visitAttributeDefinition(attributeDefinition: AttributeDefinition, scope: Scope):
        attributeDefinition: AttributeDefinition

        if attributeDefinition.name.value == "self":
            return __class__.semanticError(attributeDefinition.name.token,
                f"Class {scope.name.value} has attribute with illegal name self"
            )
        
        if not scope.add(attributeDefinition.name, attributeDefinition):
            return __class__.semanticError(attributeDefinition.name.token,
                f"Class {scope.name.value} redefines attribute {attributeDefinition.name.value}"
            )

        __class__.visit(attributeDefinition.name, scope)
        __class__.visit(attributeDefinition.type, scope)
        __class__.visit(attributeDefinition.default_value, scope)

    @AST_visits(LetEntry)
    @sets_scope_parent
    def visitLetEntry(let_entry: LetEntry, scope: Scope):
        let_entry: LetEntry
        if let_entry.name.value == "self":
            return __class__.semanticError(let_entry.name.token, "Let variable has illegal name self")
            
        let_entry.add(let_entry.name, let_entry)

        __class__.visit(let_entry.type, scope)
        __class__.visit(let_entry.default_value, scope)

        return True

    @AST_visits(Let)
    def visitLet(let: Let, scope: Scope):
        let: Let

        # let has nested scopes
        last_scope: Scope = scope

        for let_entry in let.entries:
            if __class__.visit(let_entry, last_scope):
                last_scope = let_entry

        __class__.visit(let.body, last_scope)

    @AST_visits(CaseBranch)
    @sets_scope_parent
    def visitCaseBranch(branch: CaseBranch, scope: Scope):
        branch: CaseBranch

        if branch.name.value == "self":
            return __class__.semanticError(branch.name.token,
                "Case variable has illegal name self"
            )
        
        if branch.type.value == "SELF_TYPE":
            return __class__.semanticError(branch.type.token,
                f"Case variable {branch.name.value} has illegal type SELF_TYPE"
            )
         
        branch.add(branch.name, branch)

        __class__.visit(branch.type, branch)
        __class__.visit(branch.expresion, branch)

    @AST_visits(Case)
    def visitCase(case: Case, scope: Scope):
        case: Case
        __class__.visit(case.target, scope)

        for branch in case.cases:
            __class__.visit(branch, scope)

    @AST_visits(If)
    def visitIf(if_: If, scope: Scope):
        __class__.visit(if_.condition, scope)
        __class__.visit(if_.is_true, scope)
        __class__.visit(if_.is_false, scope)

    @AST_visits(While)
    def visitWhile(while_: While, scope: Scope):
        __class__.visit(while_.condition, scope)
        __class__.visit(while_.body, scope)

    @AST_visits(ExplicitCall)
    @AST_visits(ImplicitCall)
    def visitCall(call: Union[ExplicitCall|ImplicitCall], scope: Scope):
        call: Union[ExplicitCall|ImplicitCall]

        if isinstance(call, ExplicitCall):
            __class__.visit(call.target, scope)       
            __class__.visit(call.upcall_target, scope)       

        __class__.visit(call.name, scope)     

        for arg in call.args:
            __class__.visit(arg, scope)

    @AST_visits(Block)
    def visitBlock(block: Block, scope: Scope):
        block: Block

        for expresion in block.expresions:
            __class__.visit(expresion, scope)

    @AST_visits(Assign)
    def visitAssign(assign: Assign, scope: Scope):
        assign: Assign
        assign.containing_scope=scope

        __class__.visit(assign.target, scope)
        __class__.visit(assign.new_value, scope)

    @AST_visits(Arithmetic)
    @AST_visits(Comparison)
    def visitArithmeticOrComparison(expresion: Union[Arithmetic, Comparison], scope: Scope):
        expresion: Union[Arithmetic, Comparison]

        __class__.visit(expresion.elem1, scope)
        __class__.visit(expresion.elem2, scope)

    @AST_visits(Negate)
    @AST_visits(IsVoid)
    @AST_visits(Not)
    @AST_visits(New)
    def visitSingleOperator(target, scope: Scope):
        __class__.visit(target.target, scope)

    @AST_visits(Id)
    @AST_visits(Type)
    def set_containing_scope(node: Union[Id, Type], scope: Scope):
        node.containing_scope = scope
    
    @AST_visits(SelfType)
    def set_containing_scope(node: SelfType, scope: Scope):
        node.containing_scope = scope
        node.used_in = scope["self"].name

    @AST_visits(type(None))
    # static values
    @AST_visits(String)
    @AST_visits(INT)
    @AST_visits(Bool)
    def ignore(node, scope:Scope):
        return