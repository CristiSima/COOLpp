from ASTNode import *
from antlr4 import *
from parser.CoolParser import CoolParser
from parser.CoolParserVisitor import CoolParserVisitor

def getId(token: Token) -> Id:
    return Id(token, str(token.text))
def getInt(token: Token) -> INT:
    return INT(token, int(str(token.text)))
def getString(token: Token) -> String:
    return String(token, str(token.text))
def getBool(token: Token) -> Bool:
    return Bool(token, str(token.text)=="true")
def getType(token: Token) -> Type:
    if str(token.text) == "SELF_TYPE":
        return SelfType(token)
    else:
        return Type(token, str(token.text))

def map_list(func, *args): return list(map(func, *args))

class VistorASTBuilder(CoolParserVisitor):
    def visitProgram(self, ctx:CoolParser.ProgramContext):
        return Program([
            self.visit(class_) for class_ in ctx.class_() 
        ])
    
    def visitClass(self, ctx:CoolParser.ClassContext):
        base_class = None
        if ctx.base_class:
            base_class = getType(ctx.base_class)
        return Class(
            getType(ctx.class_name),
            base_class,
            map_list(self.visit, ctx.features)
        )

    def visitAttribute_definition(self, ctx:CoolParser.Attribute_definitionContext):
        return AttributeDefinition(
            getId(ctx.attribute_name),
            getType(ctx.attribute_type),
            self.visit(ctx.default) if ctx.default else None
        )

    def visitFunction_definition(self, ctx:CoolParser.Function_definitionContext):
        return FunctionDefinition(
            getId(ctx.function_name),
            map_list(self.visitFormal, ctx.args),
            getType(ctx.return_type),
            self.visit(ctx.body)
        )

    def visitFormal(self, ctx:CoolParser.FormalContext):
        return FunctionParameter(
            getId(ctx.var_name),
            getType(ctx.type_name),
        )

    def visitAssignment(self, ctx:CoolParser.AssignmentContext):
        return Assign(
            ctx.ASSIGN(),
            getId(ctx.target),
            self.visit(ctx.value)
        )

    def visitExplicit_function_call(self, ctx:CoolParser.Explicit_function_callContext):
        return ExplicitCall(
            ctx.start,
            self.visit(ctx.target),
            getType(ctx.parent_class) if ctx.parent_class else None,
            getId(ctx.method),
            map_list(self.visit, ctx.args)
        )

    def visitImplicit_function_call(self, ctx:CoolParser.Explicit_function_callContext):
        return ImplicitCall(
            ctx.start,
            getId(ctx.method),
            map_list(self.visit, ctx.args)
        )

    def visitIf(self, ctx:CoolParser.IfContext):
        return If(
            ctx.start,
            self.visit(ctx.cond),
            self.visit(ctx.if_true),
            self.visit(ctx.if_false),
        )

    def visitWhile(self, ctx:CoolParser.WhileContext):
        return While(
            ctx.start,
            self.visit(ctx.cond),
            self.visit(ctx.action)
        )

    def visitBlock(self, ctx:CoolParser.BlockContext):
        return Block(
            ctx.start,
            map_list(self.visit, ctx.expresions)
        )

    def visitLet_entry(self, ctx:CoolParser.Let_entryContext):
        return LetEntry(
            getId(ctx.var_name),
            getType(ctx.var_type),
            self.visit(ctx.default_value) if ctx.default_value else None
        )

    def visitLet(self, ctx:CoolParser.LetContext):
        return Let(
            ctx.start,
            map_list(self.visitLet_entry, ctx.entries),
            self.visit(ctx.expresion)
        )

    def visitCase(self, ctx:CoolParser.CaseContext):
        return Case(
            ctx.start,
            self.visit(ctx.target),
            [ CaseBranch(
                getId(var_name),
                getType(check_type),
                self.visit(action)
            )   for var_name, check_type, action 
                in zip(ctx.var_names, ctx.check_types, ctx.actions) ]
        )

    def visitNew(self, ctx):
        return New(
            ctx.start,
            getType(ctx.class_name)
        )

    def visitIsvoid(self, ctx):
        return IsVoid(
            ctx.start,
            self.visit(ctx.target)
        )

    def visitNegate(self, ctx):
        return Negate(
            ctx.start,
            self.visit(ctx.target)
        )

    def visitArithm1(self, ctx:CoolParser.Arithm1Context):
        return Arithmetic(
            ctx.operator,
            self.visit(ctx.expr1),
            self.visit(ctx.expr2),
            ctx.operator.text
        )

    def visitArithm2(self, ctx:CoolParser.Arithm2Context):
        return Arithmetic(
            ctx.operator,
            self.visit(ctx.expr1),
            self.visit(ctx.expr2),
            ctx.operator.text
        )
        
    def visitCompare(self, ctx:CoolParser.CompareContext):
        return Comparison(
            ctx.comparator,
            self.visit(ctx.expr1),
            self.visit(ctx.expr2),
            ctx.comparator.text
        )

    def visitNot(self, ctx):
        return Not(
            ctx.start,
            self.visit(ctx.target)
        )

    def visitParen(self, ctx):
        return self.visit(ctx.target)

    def visitId(self, ctx:CoolParser.IdContext) -> Id:
        return Id(ctx.name, str(ctx.ID()))
    def visitInt(self, ctx) -> INT:
        return INT(ctx.value, int(str(ctx.INT())))
    def visitString(self, ctx) -> String:
        return String(ctx.value, str(ctx.STRING()))
    def visitBool(self, ctx) -> Bool:
        return Bool(ctx.value, str(ctx.BOOL())=="true")