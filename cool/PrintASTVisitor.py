from functools import wraps
from ASTVisitor import *
from ASTNode import *
__all__ = [
    "PrintASTVisitor"
]

old_print=print
indentation=0
spacer="  "

def indent(n=1):
    global indentation
    indentation+=n

def print(arg, *, indent=None):
    global indentation
    old_print(spacer*indentation+str(arg))

    if indent == "++" or indent == 1:
        indentation+=1
    elif indent == "--" or indent == -1:
        indentation-=1

def unindent_at_end(function):
    @wraps(function)
    def temp(*args):
        function(*args)
        indent(-1)
    return temp

class PrintASTVisitor(ASTVisitor):
    
    @AST_visits(Program)
    @unindent_at_end
    def visitProgram(program: Program):
        print("program", indent=1)
        for class_ in program.classes:
            __class__.visit(class_)
    
    @AST_visits(Class)
    @unindent_at_end
    def visitClass(class_: Class):
        print("class", indent=1)
        print(class_.name.value)
        if class_.base_class:
            print(class_.base_class.value)
        for feature in class_.features:
            __class__.visit(feature)
    
    @AST_visits(AttributeDefinition)
    @unindent_at_end
    def visitAttributeDefinition(attr: AttributeDefinition):
        print("attribute", indent=1)
        print(attr.name.value)
        print(attr.type.value)
        if attr.default_value:
            __class__.visit(attr.default_value)

    @AST_visits(FunctionDefinition)
    @unindent_at_end
    def visitFunctionDefinition(func: FunctionDefinition):
        print("method", indent=1)
        print(func.name.value)

        for parameter in func.parameters:
            print("formal", indent=1)
            print(parameter.name.value)
            print(parameter.type.value, indent=-1)

        print(func.return_type.value)
        __class__.visit(func.body)

    @AST_visits(ImplicitCall)
    @unindent_at_end
    def visitImplicitCall(call: ImplicitCall):
        print("implicit dispatch", indent=1)
        print(call.name.value)
        for arg in call.args:
            __class__.visit(arg)

    @AST_visits(ExplicitCall)
    @unindent_at_end
    def visitExplicitCall(call: ExplicitCall):
        print(".", indent=1)
        __class__.visit(call.target)
        if call.upcall_target:
            print(call.upcall_target.value)
        print(call.name.value)
        for arg in call.args:
            __class__.visit(arg)

    @AST_visits(If)
    @unindent_at_end
    def visitIf(if_: If):
        print("if", indent=1)
        __class__.visit(if_.condition)
        __class__.visit(if_.is_true)
        __class__.visit(if_.is_false)

    @AST_visits(While)
    @unindent_at_end
    def visitWhile(while_: While):
        print("while", indent=1)
        __class__.visit(while_.condition)
        __class__.visit(while_.body)

    @AST_visits(Block)
    @unindent_at_end
    def visitBlock(block: Block):
        print("block", indent=1)
        for expr in block.expresions:
            __class__.visit(expr)

    @AST_visits(Let)
    @unindent_at_end
    def visitLet(let: Let):
        let: Let
        print("let", indent=1)
        for entry in let.entries:
            print("local", indent=1)
            print(entry.name.value)
            print(entry.type.value)
            __class__.visit(entry.default_value)
            indent(-1)
            
        __class__.visit(let.body)

    @AST_visits(Case)
    @unindent_at_end
    def visitCase(case: Case):
        case: Case
        print("case", indent=1)
        __class__.visit(case.target)
        for case_branch in case.cases:
            print("case branch", indent=1)
            print(case_branch.name.value)
            print(case_branch.type.value)
            __class__.visit(case_branch.expresion)
            indent(-1)

    @AST_visits(Arithmetic)
    @unindent_at_end
    def visitArithmetic(arithmetic: Arithmetic):
        print(arithmetic.operator, indent=1)
        __class__.visit(arithmetic.elem1)
        __class__.visit(arithmetic.elem2)

    @AST_visits(Comparison)
    @unindent_at_end
    def visitComparison(comparison: Comparison):
        print(comparison.operator, indent=1)
        __class__.visit(comparison.elem1)
        __class__.visit(comparison.elem2)
    
    @AST_visits(Negate)
    @unindent_at_end
    def visitNegate(negate: Negate):
        print("~", indent=1)
        __class__.visit(negate.target)
    
    @AST_visits(Not)
    @unindent_at_end
    def visitNot(not_: Not):
        print("not", indent=1)
        __class__.visit(not_.target)
    
    @AST_visits(New)
    @unindent_at_end
    def visitNew(new: New):
        print("new", indent=1)
        __class__.visit(new.target)
    
    @AST_visits(Negate)
    @unindent_at_end
    def visitNegate(negate: Negate):
        print("~", indent=1)
        __class__.visit(negate.target)
    
    @AST_visits(IsVoid)
    @unindent_at_end
    def visitIsVoid(is_void: IsVoid):
        print("isvoid", indent=1)
        __class__.visit(is_void.target)

    @AST_visits(Assign)
    @unindent_at_end
    def visitAssign(assign: Assign):
        print("<-", indent=1)
        print(assign.target.value)
        __class__.visit(assign.new_value)
    
    @AST_visits(INT)
    @AST_visits(Id)
    @AST_visits(String)
    @AST_visits(Type)
    @AST_visits(SelfType)
    def printValue(target):
        print(target.value)

    @AST_visits(Bool)
    def printValue(target):
        print(str(target.value).lower())
    
    @AST_visits(type(None))
    def ignore(_):
        pass