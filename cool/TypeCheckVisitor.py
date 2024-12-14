from typing import Union, Dict, Set, Iterable, Generator
from functools import wraps, reduce, partial
from itertools import tee
from antlr4.Lexer import Token
from ASTVisitor import *
from ASTNode import *
from PopulateScopeVisitor import *
from pathlib import Path

__all__ = [
    "TypeCheckVisitor"
]
AnyType = Union[Type|SelfType]

def get_ancestor(type_: Type) -> Type:
    if not type_.definition.base_class:
        return None
    if not type_.definition.base_class.definition:
        return None

    return type_.definition.base_class

def gen_ancestors(type_: Type) -> Generator[Type, None, None]:
    while type_:
        yield type_
        type_ = get_ancestor(type_)

def get_ancestors(type_: Type) -> Set[Type]:
    # return set(gen_ancestors(type_))
    result: Set = set()

    while type_:
        result.add(type_)
        type_ = get_ancestor(type_)

    return result

def intersect_type(t1: AnyType, t2: AnyType) -> AnyType:
    if isinstance(t1, SelfType) and isinstance(t2, SelfType):
        return t1

    if isinstance(t1, SelfType):
        return get_first_ancestor(t1.used_in, get_ancestors(t2))
    elif isinstance(t2, SelfType):
        return intersect_type(t2, t1)

    return get_first_common_ancestor(t1, t2)

def intersect_types(ts: Iterable[AnyType]) -> AnyType:
    ts = iter(ts)
    return reduce(intersect_type, ts, next(ts))

def get_first_ancestor(target: Type, ancestors: Set[Type]) -> Type:
    for ancestor in gen_ancestors(target):
        if ancestor in ancestors:
            return ancestor

def get_first_common_ancestor(t1: Type, t2:Type) -> Type:
    return get_first_ancestor(t1, get_ancestors(t1) & get_ancestors(t2))

def check_can_cast_to(tested: Union[Class, Type, SelfType], target: Union[Class, Type, SelfType]):
    tested: Union[Type, SelfType] = tested.name if isinstance(tested, Class) else tested
    target: Union[Type, SelfType] = target.name if isinstance(target, Class) else target

    return target == intersect_type(tested, target)


class TypeEvaluationVisitor(ASTVisitor):
    global_scope : Scope

    errors: bool
    def semanticError(token: Token, msg: str):
        token: Token
        filename = Path(token.source[1].fileName).name
        print(f"\"{filename}\", line {token.line}:{token.column+1}, Semantic error: {msg}")
        __class__.errors = True

    @classmethod
    def visit(cls, node: ASTNode, *args, **kwargs):
        result = super().visit(node, *args, **kwargs)
        
        if isinstance(node, Expresion):
            node: Exception
            node.static_type = result
        
        return result

    @AST_visits(LetEntry)
    def visitLetEntry(entry: LetEntry):
        return entry.type

    def checkLetEntry(entry: LetEntry):
        entry: LetEntry

        if entry.name.value == "self":
            return

        if not entry.type.definition:
            # doen't matter, variable isn't checked any more
            del entry[entry.name.value]
            return __class__.semanticError(entry.type.token, 
                f"Let variable {entry.name.value} has undefined type {entry.type.value}"
            )

        default_value_type: Type = __class__.visit(entry.default_value)
        if default_value_type and not check_can_cast_to(default_value_type, entry.type):
            return __class__.semanticError(entry.default_value.token,
                f"Type {default_value_type.value} of initialization expression "
                + f"of identifier {entry.name.value} "
                + f"is incompatible with declared type {entry.type.value}"
            )

    @AST_visits(Let)
    def visitLet(let: Let):
        let: Let
        for entry in let.entries:
            __class__.checkLetEntry(entry)

        return __class__.visit(let.body)


    @AST_visits(CaseBranch)
    def visitCaseBranch(branch: CaseBranch):
        return branch.type

    def checkCaseBranch(branch: CaseBranch, target_type: Type):
        branch: CaseBranch

        if branch.name.value == "self" or branch.type.value == "SELF_TYPE":
            return

        if not branch.type.definition:
            return __class__.semanticError(branch.type.token, 
                f"Case variable {branch.name.value} has undefined type {branch.type.value}"
            )

        return __class__.visit(branch.expresion)

    @AST_visits(Case)
    def visitCase(case: Case):
        case: Case
        target_type = __class__.visit(case.target)

        results = []
        for branch in case.cases:
            if result := __class__.checkCaseBranch(branch, target_type):
                results.append(result)

        return intersect_types(results)

    @AST_visits(If)
    def visitIf(if_: If):
        if_: If
        condition_type = __class__.visit(if_.condition)
        if condition_type and condition_type.value != "Bool":
            __class__.semanticError(if_.condition.token, 
                f"If condition has type {condition_type.value} instead of Bool"
            )
        
        is_true_type = __class__.visit(if_.is_true)
        is_false_type = __class__.visit(if_.is_false)

        return intersect_type(is_true_type, is_false_type)

    @AST_visits(While)
    def visitWhile(while_: While):
        while_: While

        condition_type = __class__.visit(while_.condition)

        if condition_type and condition_type.value != "Bool":
            __class__.semanticError(while_.condition.token, 
                f"While condition has type {condition_type.value} instead of Bool"
            )

        __class__.visit(while_.body)
        return __class__.builtin_type_Object()

    @AST_visits(Block)
    def visitBlock(block: Block):
        block: Block

        last_type: Type
        for expresion in block.expresions:
            last_type = __class__.visit(expresion)

        return last_type


    @AST_visits(Arithmetic)
    def visitArithmeric(arithmetic: Arithmetic):
        arithmetic: Arithmetic
        type1 = __class__.visit(arithmetic.elem1)
        type2 = __class__.visit(arithmetic.elem2)

        if type1 and not type1.value == "Int":
            __class__.semanticError(arithmetic.elem1.token, 
                f"Operand of {arithmetic.operator} has type {type1.value} instead of Int"
            )

        if type2 and not type2.value == "Int":
            __class__.semanticError(arithmetic.elem2.token, 
                f"Operand of {arithmetic.operator} has type {type2.value} instead of Int"
            )
        
        return __class__.visit(INT(...,...))

    @AST_visits(Comparison)
    def visitComparison(comparison: Comparison):
        comparison: Comparison
        type1 = __class__.visit(comparison.elem1)
        type2 = __class__.visit(comparison.elem2)

        if comparison.operator == "=":
            if type1 != type2 \
                    and any(elem_type.value in ["Bool", "String", "Int"] for elem_type in [type1, type2]):
                __class__.semanticError(comparison.token, 
                    f"Cannot compare {type1.value} with {type2.value}"
                )
        else:
            if type1 and not type1.value == "Int":
                __class__.semanticError(comparison.elem1.token, 
                    f"Operand of {comparison.operator} has type {type1.value} instead of Int"
                )

            if type2 and not type2.value == "Int":
                __class__.semanticError(comparison.elem2.token, 
                    f"Operand of {comparison.operator} has type {type2.value} instead of Int"
                )
        
        return __class__.visit(Bool(...,...))

    @AST_visits(IsVoid)
    def visitSingleOperator(operation: IsVoid):
        __class__.visit(operation.target)
        return __class__.visit(Bool(...,...))

    @AST_visits(New)
    def visitSingleOperator(operation: New):
        if isinstance(operation.target, SelfType):
            return operation.target

        if not operation.target.definition:
            return __class__.semanticError(operation.target.token, 
                f"new is used with undefined type {operation.target.value}"
            )

        return operation.target


    @AST_visits(Not)
    def visitSingleOperator(operation: Not):
        operation: Negate
        target_type = __class__.visit(operation.target)
        
        if target_type and not target_type.value == "Bool":
            __class__.semanticError(operation.target.token, 
                f"Operand of not has type {target_type.value} instead of Bool"

            )
        return __class__.visit(Bool(...,...))

    @AST_visits(Negate)
    def visitSingleOperator(operation):
        operation: Negate
        target_type = __class__.visit(operation.target)
        
        if target_type and not target_type.value == "Int":
            __class__.semanticError(operation.target.token, 
                f"Operand of ~ has type {target_type.value} instead of Int"
            )

        return __class__.visit(INT(...,...))

    @AST_visits(ExplicitCall)
    def visitExplicit_function_call(call: ExplicitCall):
        call: ExplicitCall
        og_target_type = target_type = __class__.visit(call.target)

        if not target_type:
            return

        target_type_name = target_type.used_in.value if isinstance(target_type, SelfType) \
                            else target_type.value

        if call.upcall_target:
            if call.upcall_target.value == "SELF_TYPE":
                return __class__.semanticError(call.upcall_target.token, 
                    f"Type of static dispatch cannot be SELF_TYPE"
                )

            if not call.upcall_target.definition:
                return __class__.semanticError(call.upcall_target.token, 
                    f"Type {call.upcall_target.value} of static dispatch is undefined"
                )

            if not check_can_cast_to(target_type, call.upcall_target):
                return __class__.semanticError(call.upcall_target.token, 
                    f"Type {call.upcall_target.value} of static dispatch "
                    + f"is not a superclass of type {target_type_name}"
                )

            target_type = call.upcall_target
            target_type_name = target_type.value

        function_definiion: FunctionDefinition = target_type.definition.get_function(call.name.value)
        
        if not function_definiion:
            return __class__.semanticError(call.name.token, 
                f"Undefined method {call.name.value} in class {target_type_name}"
            )

        if len(function_definiion.parameters) != len(call.args):
            return __class__.semanticError(call.name.token, 
                f"Method {call.name.value} of class {target_type_name} "
                + f"is applied to wrong number of arguments"
            )
        
        for parameter, argument in zip(function_definiion.parameters, call.args):
            argument_type = __class__.visit(argument)

            if argument and not check_can_cast_to(argument_type, parameter.type):
                __class__.semanticError(argument.token, 
                    f"In call to method {call.name.value} of class {target_type_name}, "
                    + f"actual type {argument_type.value} of formal parameter {parameter.name.value} "
                    + f"is incompatible with declared type {parameter.type.value}"
                )
        
        if isinstance(function_definiion.return_type, SelfType):
            return og_target_type

        return function_definiion.return_type


    @AST_visits(ImplicitCall)
    def visitImplicit_function_call(call: ImplicitCall):
        call: ImplicitCall
        self_class: Class = call.name.containing_scope['self']
        function_definiion: FunctionDefinition = call.name.function_definition

        if not function_definiion:
            return __class__.semanticError(call.name.token, 
                f"Undefined method {call.name.value} in class {self_class.name.value}"
            )

        if len(function_definiion.parameters) != len(call.args):
            return __class__.semanticError(call.name.token, 
                f"Method {call.name.value} of class {self_class.name.value} "
                + f"is applied to wrong number of arguments"
            )
        
        for parameter, argument in zip(function_definiion.parameters, call.args):
            argument_type = __class__.visit(argument)

            if argument and not check_can_cast_to(argument_type, parameter.type):
                __class__.semanticError(argument.token, 
                    f"In call to method {call.name.value} of class {self_class.name.value}, "
                    + f"actual type {argument_type.value} of formal parameter {parameter.name.value} "
                    + f"is incompatible with declared type {parameter.type.value}"
                )

        if isinstance(function_definiion.return_type, SelfType):
            return SelfType(...,
                used_in=__class__.visit(call.name.containing_scope["self"]),
                containing_scope=call.name.containing_scope
            )
        
        return function_definiion.return_type

    @AST_visits(FunctionParameter)
    def visitFunctionParameter(functionParameter: FunctionParameter):
        functionParameter: FunctionParameter
        return functionParameter.type

    @AST_visits(Assign)
    def visitAssign(assign: Assign):
        assign: Assign

        value_type = __class__.visit(assign.new_value)
        target_type = __class__.visit(assign.target)

        if assign.target.value == "self":
            __class__.semanticError(assign.target.token,
                "Cannot assign to self"
            )
            return value_type

        if target_type and value_type and not check_can_cast_to(value_type, target_type):
            __class__.semanticError(assign.new_value.token,
                f"Type {value_type.value} of assigned expression is incompatible "
                + f"with declared type {target_type.value} of identifier {assign.target.value}"
            )
            
        return value_type


    @AST_visits(AttributeDefinition)
    def visitAttributeDefinition(attributeDefinition: AttributeDefinition):
        return attributeDefinition.type

    @AST_visits(Class)
    def visitClass(class_: Class):
        return class_.name

    @AST_visits(SelfType)
    @AST_visits(Type)
    def visitType(type_: Type):
        return type_

    @AST_visits(Id)
    def visitId(id: Id):
        if id.value == "self":
            return SelfType(..., value="SELF_TYPE", used_in=id.definition.name, containing_scope=id.containing_scope)

        if id.definition:
            return __class__.visit(id.definition)

        return __class__.semanticError(id.token, 
            f"Undefined identifier {id.value}"
        )

    '''
    Int and Bool do NOT need a scope
    they have no methods and can NOT be extended

    '''
    @AST_visits(String)
    def builtin_type_String(node: String):
        return Type(..., "String", containing_scope=__class__.global_scope)

    @AST_visits(INT)
    def builtin_type_Int(node: INT):
        return Type(..., "Int", containing_scope=__class__.global_scope)

    @AST_visits(Bool)
    def builtin_type_Bool(node: Bool):
        return Type(..., "Bool", containing_scope=__class__.global_scope)

    def builtin_type_Object():
        return Type(..., "Object", containing_scope=__class__.global_scope)

    @AST_visits(type(None))
    def ignore(node):
        return None


class TypeCheckVisitor(ASTVisitor):
    global_scope : Scope

    errors: bool
    def semanticError(token: Token, msg: str):
        token: Token
        filename = Path(token.source[1].fileName).name
        print(f"\"{filename}\", line {token.line}:{token.column+1}, Semantic error: {msg}")
        __class__.errors = True


    @AST_visits(Program)
    def visitProgram(program: Program):
        # init
        __class__.errors        = TypeEvaluationVisitor.errors       = False
        __class__.global_scope  = TypeEvaluationVisitor.global_scope = program
        
        for class_ in program.classes:
            __class__.resolve_class_inheritence_linkage(class_)

        for class_ in program.classes:
            __class__.visit(class_)

        __class__.errors |= TypeEvaluationVisitor.errors

        if not program["Main"] \
                or "main" not in program["Main"]._scope_function_store \
                or len(program["Main"].get_function("main").parameters):
            # random token SHOULD be changed
            __class__.semanticError(program.classes[0].name.token, 
                f"No method main in class Main"
            )

    def resolve_class_inheritence_linkage(class_: Class):
        class_: Class
        if class_.in_loop:
            return

        if not class_.base_class:
            class_.base_class   = Type(..., "Object", containing_scope=class_.scope_parent)
            class_.scope_parent = class_["Object"]
            return

        if class_.base_class.value in {"SELF_TYPE", "Int", "String", "Bool"}:
            return __class__.semanticError(class_.base_class.token,
                f"Class {class_.name.value} has illegal parent {class_.base_class.value}"
            )
            
        if not class_.base_class.definition:
            return __class__.semanticError(class_.base_class.token,
                f"Class {class_.name.value} has undefined parent {class_.base_class.value}"
            )

        ancestor:   class_ = class_
        ancestors : Dict[str, Class] = {}
        while ancestor:
            if ancestor.name.value in ancestors:
                class_.in_loop = True
                break

            ancestors[ancestor.name.value] = ancestor
            ancestor = ancestor.base_class.definition if ancestor.base_class else None

        if class_.in_loop:
            for ancestor in ancestors.values():
                ancestor.in_loop = True
                __class__.semanticError(ancestor.name.token,
                    f"Inheritance cycle for class {ancestor.name.value}"
                )
            
            return 

        class_.scope_parent=class_.base_class.definition


    @AST_visits(Class)
    def visitClass(class_: Class):
        class_: Class

        for feature in class_._scope_store.values():
            if feature is not class_:
                __class__.visit(feature)

        for feature in class_._scope_function_store.values():
            __class__.visit(feature)

    @AST_visits(AttributeDefinition)
    def visitAttribute_definition(attributeDefinition: AttributeDefinition):
        attributeDefinition: AttributeDefinition

        if attributeDefinition.name.value not in attributeDefinition.owned_by._scope_store:
            return

        if not attributeDefinition.type.definition:
            return __class__.semanticError(attributeDefinition.type.token, 
                f"Class {attributeDefinition.owned_by.name.value} " 
                + f"has attribute {attributeDefinition.name.value} " 
                + f"with undefined type {attributeDefinition.type.value}"
            )

        
        if inheritet_definition := attributeDefinition.owned_by.scope_parent[attributeDefinition.name.value]:
            return __class__.semanticError(attributeDefinition.name.token, 
                f"Class {attributeDefinition.owned_by.name.value} " 
                + f"redefines inherited attribute {attributeDefinition.name.value}" 
            )
        
        init_value_type: Type = TypeEvaluationVisitor.visit(attributeDefinition.default_value)
        if not init_value_type:
            return

        if not check_can_cast_to(init_value_type.definition, attributeDefinition.type.definition):
            return __class__.semanticError(attributeDefinition.default_value.token, 
                f"Type {init_value_type.value} of initialization expression "
                + f"of attribute {attributeDefinition.name.value} " 
                + f"is incompatible with declared type {attributeDefinition.type.value}" 
            )

    @AST_visits(FunctionDefinition)
    def visitFunctionDefinition(functionDefinition: FunctionDefinition):
        functionDefinition: FunctionDefinition
        if not functionDefinition.return_type.definition:
            return __class__.semanticError(functionDefinition.return_type.token, 
                f"Class {functionDefinition.owned_by.name.value} " 
                + f"has method {functionDefinition.name.value} " 
                + f"with undefined type {functionDefinition.return_type.value}"
            )
            
        if inheritet_definition := functionDefinition.owned_by.scope_parent.get_function(functionDefinition.name.value):
            inheritet_definition: FunctionDefinition

            if len(inheritet_definition.parameters) != len(functionDefinition.parameters):
                return __class__.semanticError(functionDefinition.name.token, 
                    f"Class {functionDefinition.owned_by.name.value} " 
                    + f"overrides method {functionDefinition.name.value} " 
                    + f"with different number of formal parameters"
                )
            
            for old_parameter, new_parameter in zip(inheritet_definition.parameters, functionDefinition.parameters):
                if not old_parameter.type.containing_scope \
                        or not new_parameter.type.containing_scope:
                    continue
                if old_parameter.type == new_parameter.type:
                    continue

                return __class__.semanticError(new_parameter.type.token, 
                    f"Class {functionDefinition.owned_by.name.value} " 
                    + f"overrides method {functionDefinition.name.value} " 
                    + f"but changes type of formal parameter {new_parameter.name.value} "
                    + f"from {old_parameter.type.value} to {new_parameter.type.value}"
                )

            if inheritet_definition.return_type != functionDefinition.return_type:
                return __class__.semanticError(functionDefinition.return_type.token, 
                    f"Class {functionDefinition.owned_by.name.value} " 
                    + f"overrides method {functionDefinition.name.value} " 
                    + f"but changes return type "
                    + f"from {inheritet_definition.return_type.value} "
                    + f"to {functionDefinition.return_type.value}"
                )
        
        for parameter in functionDefinition.parameters:
            if not parameter.type.containing_scope:
                continue
            if not parameter.type.definition:
                return __class__.semanticError(parameter.type.token, 
                    f"Method {functionDefinition.name.value} " 
                    + f"of class {functionDefinition.owned_by.name.value} " 
                    + f"has formal parameter {parameter.name.value} "
                    + f"with undefined type {parameter.type.value}"
                )
        
        body_value_type: Type = TypeEvaluationVisitor.visit(functionDefinition.body)
        if body_value_type and not check_can_cast_to(body_value_type, functionDefinition.return_type):
            return __class__.semanticError(functionDefinition.body.token, 
                f"Type {body_value_type.value} of the body "
                + f"of method {functionDefinition.name.value} " 
                + f"is incompatible with declared return type {functionDefinition.return_type.value}"
            )
