from collections import defaultdict, deque
from typing import Union, Dict, Iterator
from ASTVisitor import *
from ASTNode import *
from code_generation.CodeTemplates import CodeTemplates, CodeTemplate
from pprint import pprint
from functools import partial
from pathlib import Path
from antlr4 import Token
import sys

__all__ = [
    "CodeGenerationVisitor"
]
templates = CodeTemplates("cool/code_generation/cgen.stg")

def get_token_file(token: Token):
    return Path(token.source[1].fileName).name

def set_builtin_implementations(program: Program):
    program: Program

    Object:Class = program["Object"]
    Object.get_function("abort").index = 0
    Object.get_function("type_name").index = 1
    Object.get_function("copy").index = 2

    String:Class = program["String"]
    String.get_function("length").index = 3
    String.get_function("concat").index = 4
    String.get_function("substr").index = 5

    IO:Class = program["IO"]
    IO.get_function("out_string").index = 3
    IO.get_function("out_int").index = 4
    IO.get_function("in_string").index = 5
    IO.get_function("in_int").index = 6

def calculate_function_indeses(class_: Class) -> Dict[int, str]:
    class_: Class
    function_indeses: Dict[int, str] = {}
    if class_.base_class:
        function_indeses = calculate_function_indeses(class_.base_class.definition)

    if not len(class_._scope_function_store):
        return function_indeses

    last_index = len(function_indeses)
    if list(class_._scope_function_store.values())[0].index is None:
        for feature in class_.features:
            if not isinstance(feature, FunctionDefinition):
                continue

            if class_.base_class.definition.get_function(feature.name):
                # reuse index from previous definition
                feature.index = class_.base_class.definition.get_function(feature.name).index
                continue

            feature.index = last_index
            last_index += 1
    
    for feature in class_.features:
        if not isinstance(feature, FunctionDefinition):
            continue

        function_indeses[feature.index] = f"{class_.name.value}.{feature.name.value}"

    return function_indeses

def build_dispatch_table(class_: Class) -> str:
    class_: Class
    function_indeses: Dict[int, str] = calculate_function_indeses(class_)

    method_table = templates["sequence"]
    method_table.add(e=f"{class_.name.value}_dispTab:")
    for i in range(len(function_indeses)):
        method_table.add(e=f"\t.word {function_indeses[i]}")

    return method_table.render()
    

def builtin_dispatch_tables(program: Program) -> str:
    set_builtin_implementations(program)

    method_tables = templates["sequence"]
    
    for builtin_name in ["Object", "Int", "String", "Bool", "IO"]:
        method_tables.add(e=build_dispatch_table(program[builtin_name]))

    return method_tables.render()



def builtin_inits(program: Program) -> str:
    inits = templates["sequence"]

    for builtin_name in ["Object", "Int", "String", "Bool", "IO"]:
        inits.add(e=build_init(program[builtin_name]))

    return inits.render()

def build_init(class_: Class) -> str:
    class_: Class
    init_template = templates["gen_init"].add(
        target=class_.name.value
    )

    if class_.base_class:
        init_template.add(parent_init_jump=f"jal     {class_.base_class.value}_init")

    for feature in class_.features:
        if isinstance(feature, FunctionDefinition):
            continue

        feature: AttributeDefinition
        if not feature.default_value or isinstance(feature.default_value, Union[INT, String, Bool]):
            continue
    
        raise Exception("attribut defaul in init")

    return init_template.render()


class CodeGenerationVisitor(ASTVisitor):
    branch_count: int
    stack_element_count: int

    tag_to_parent_tag_mapping: Dict[int, int]
    class_tag_mapping: Dict[Type, int]
    tag_class_mapping: Dict[int, Type]

    DATA_SEGMENT_TEMPLACE: CodeTemplate
    
    CONSTS_SEGMENT: CodeTemplate
    INT_CONSTS_SEGMENT: CodeTemplate
    int_consts: Dict[int, str]
    STRING_CONSTS_SEGMENT: CodeTemplate
    string_consts: Dict[int, str]
    
    PROTOTYPES_SEGMENT_TEMPLACE: CodeTemplate
    DISPATCH_SEGMENT_TEMPLACE: CodeTemplate

    CODE_SEGMENT_TEMPLACE: CodeTemplate
    INIT_SEGMENT_TEMPLACE: CodeTemplate

    def init():
        __class__.branch_count=0

        __class__.tag_to_parent_tag_mapping = {}
        __class__.class_tag_mapping = {}
        __class__.tag_class_mapping = {}
        __class__.int_consts = {}
        __class__.string_consts = {}

        __class__.CODE_SEGMENT_TEMPLACE: CodeTemplate = templates["sequenceSpaced"].add(e=".text")
        __class__.INIT_SEGMENT_TEMPLACE: CodeTemplate = templates["sequenceSpaced"]

        __class__.DATA_SEGMENT_TEMPLACE: CodeTemplate = templates["sequenceSpaced"].add(e=".data")
        __class__.PROTOTYPES_SEGMENT_TEMPLACE: CodeTemplate = templates["sequenceSpaced"]
        __class__.DISPATCH_SEGMENT_TEMPLACE: CodeTemplate = templates["sequenceSpaced"]

        __class__.CONSTS_SEGMENT: CodeTemplate = templates["sequenceSpaced"]
        __class__.INT_CONSTS_SEGMENT: CodeTemplate = templates["sequenceSpaced"]
        __class__.STRING_CONSTS_SEGMENT: CodeTemplate = templates["sequenceSpaced"]



        __class__.CONSTS_SEGMENT.add(e=templates["bool_const"].add(
            name="false",
            val=0,
        ).render())
        __class__.CONSTS_SEGMENT.add(e=templates["bool_const"].add(
            name="true",
            val=1,
        ).render())

    def get_next_branch():
        branch_count = __class__.branch_count
        __class__.branch_count += 1
        return branch_count

    def get_int_const(val):
        if val in __class__.int_consts:
            return __class__.int_consts[val]

        __class__.int_consts[val] = f"Int_const_{val}"
        __class__.INT_CONSTS_SEGMENT.add(e=templates["int_const"].add(
            val=val
        ).render())

        return f"Int_const_{val}"

    def get_string_const(val: str):
        val = val.replace("\n", "\\n")
        if val in __class__.string_consts:
            return __class__.string_consts[val]

        const_tag = 1+len(__class__.string_consts)

        __class__.string_consts[val] = f"String_const_{const_tag}"
        __class__.STRING_CONSTS_SEGMENT.add(e=templates["string_const"].add(
            nr=const_tag,
            val=val,
            str_blocks=(len(val)+3)//4,
            length=__class__.get_int_const(len(val))
        ).render())

        return f"String_const_{const_tag}"

    def calculate_tags(program: Program):
        ...
        program: Program
        childrens: Dict[Type, List[Class_]] = defaultdict(list)

        Object:Class = program["Object"]

        childrens[Object.name] = [
            program["Int"],
            program["String"],
            program["Bool"],
            program["IO"],
        ]

        for class_ in program.classes:
            childrens[class_.base_class].append(class_)

        last_tag = 0
        untagged_classes = deque([Object,])
        class_tag_mapping: Dict[Type, int] = {}
        tag_class_mapping: Dict[int, Type] = {}
        # for class_ in untagged_classes:
        while len(untagged_classes):
            class_ = untagged_classes.popleft()
            class_.tag = last_tag
            class_tag_mapping[class_.name] = last_tag
            tag_class_mapping[last_tag] = class_.name 
            last_tag+=1
            for children in childrens[class_.name]:
                untagged_classes.append(children)

        tag_to_parent_tag_mapping = {
            class_.definition.tag:
            class_.definition.base_class.definition.tag if class_.definition.base_class else 0
            for class_ in class_tag_mapping
        }

        __class__.tag_to_parent_tag_mapping = tag_to_parent_tag_mapping
        __class__.class_tag_mapping = class_tag_mapping
        __class__.tag_class_mapping = tag_class_mapping

        builtin_tags = templates["sequence"]
        for builtin in ["Object", "Int", "String", "Bool", "IO"]:
            builtin_tags.add(e=f"_{builtin.lower()}_tag:")
            builtin_tags.add(e=f"\t.word\t{program[builtin].tag}")

        __class__.DATA_SEGMENT_TEMPLACE.add(e=builtin_tags.render())

        name_table = templates["sequence"].add(
            e="class_nameTab:"
        )
        class_tag_to_parent = templates["sequence"].add(
            e="tag_to_parent_tag_table:"
        )

        
        class_tag_to_parent.add(e=f"\t.word\t{-1}")
        for i in range(1,len(tag_to_parent_tag_mapping)):
            class_tag_to_parent.add(e=f"\t.word\t{tag_to_parent_tag_mapping[i]}")

        for i in range(len(tag_to_parent_tag_mapping)):
            name_table.add(e=f"\t.word\t{__class__.get_string_const(tag_class_mapping[i].value)}")

        __class__.DATA_SEGMENT_TEMPLACE.add(e=class_tag_to_parent.render())
        __class__.DATA_SEGMENT_TEMPLACE.add(e=name_table.render())


    def build_init_table(program: Program) -> str:
        program: Program
        inits = templates["sequence"].add(
            e="inits_table:"
        )
        
        for i in range(len(__class__.tag_class_mapping)):
            inits.add(
                e=f"\t.word {__class__.tag_class_mapping[i].value}_init"
            )

        return inits.render()

    def build_prototype(class_: Class) -> str:
        class_: Class

        template = templates["prototype"].add(
            target=class_.name.value,
            tag=class_.tag
        )

        def get_all_attributes(class_: Class) -> Iterator[AttributeDefinition]:
            if class_.base_class:
                for attr in get_all_attributes(class_.base_class.definition):
                    yield attr
            for feature in class_.features:
                if isinstance(feature, FunctionDefinition):
                    continue
                yield feature

        attrs = list(get_all_attributes(class_))
        template.add(attr_count=len(attrs))

        for index, attr in enumerate(attrs):
            # default value
            if not attr.index:
                attr.index=index
            
            assert attr.index == index

            if not attr.default_value:
                if attr.type.value in ["Int", "String", "Bool"]:
                    # init to prototype
                    template.add(attrs=f"\t.word {attr.type.value}_protObj")
                else:
                    # non builtins inited to 0
                    template.add(attrs="\t.word 0")

                continue

            # w default values
            if isinstance(attr.default_value, INT):
                template.add(attrs=f"\t.word {__class__.get_int_const(attr.default_value.value)}")
            elif isinstance(attr.default_value, String):
                template.add(attrs=f"\t.word {__class__.get_string_const(attr.default_value.value)}")
            elif isinstance(attr.default_value, Bool):
                template.add(attrs=f"\t.word Bool_const_{str(attr.default_value.value).lower()}")
            else:
                raise Exception("Implement eval in init")

        return template.render()

    def build_prototype_table(program: Program) -> str:
        program: Program
        prototypes = templates["sequence"].add(
            e="prototypes_table:"
        ).add(e=".globl\tprototypes_table")
        
        for i in range(len(__class__.tag_class_mapping)):
            prototypes.add(
                e=f"\t.word {__class__.tag_class_mapping[i].value}_protObj"
            )

        return prototypes.render()
            
    def build_builtin_prototypes(program: Program) -> str:
        program: Program
        prototypes = templates["sequenceSpaced"]

        prototypes.add(e=__class__.build_prototype(program["Object"]))

        prototypes.add(e=templates["prototype"].add(
            target="Int",
            tag=1,
            attr_count=1,
            attrs="\t.word 0"
        ).render())

        prototypes.add(e=templates["prototype"].add(
            target="String",
            tag=2,
            attr_count=2,
            attrs="\t.word Int_protObj"
        ).add(attrs='\t.asciiz ""'
        ).add(attrs='\t.align 2'
        ).render())

        prototypes.add(e=templates["prototype"].add(
            target="Bool",
            tag=3,
            attr_count=1,
            attrs="\t.word 0"
        ).render())

        prototypes.add(e=__class__.build_prototype(program["IO"]))

        return prototypes.render()

    @AST_visits(Program)
    def visitProgram(program: Program):
        program: Program
        __class__.init()
        __class__.calculate_tags(program)
        # program.

        __class__.DISPATCH_SEGMENT_TEMPLACE.add(e=builtin_dispatch_tables(program))
        for class_ in program.classes:
            __class__.DISPATCH_SEGMENT_TEMPLACE.add(e=build_dispatch_table(class_))

        __class__.DISPATCH_SEGMENT_TEMPLACE.add(e=__class__.build_init_table(program))
        __class__.INIT_SEGMENT_TEMPLACE.add(e=builtin_inits(program))
        
        __class__.PROTOTYPES_SEGMENT_TEMPLACE.add(e=__class__.build_prototype_table(program))
        __class__.PROTOTYPES_SEGMENT_TEMPLACE.add(e=__class__.build_builtin_prototypes(program))


        for class_ in program.classes:
            __class__.visit(class_)

        __class__.DATA_SEGMENT_TEMPLACE.add(
            e=__class__.PROTOTYPES_SEGMENT_TEMPLACE.render()
        ).add(e=__class__.DISPATCH_SEGMENT_TEMPLACE.render()
        ).add(e=__class__.CONSTS_SEGMENT.render()
        ).add(e=__class__.INT_CONSTS_SEGMENT.render()
        ).add(e=__class__.STRING_CONSTS_SEGMENT.render()
        ).add(e=templates["sequence"]
            .add(e=".globl  heap_start")
            .add(e="heap_start:")
            .add(e="\t.word   0")
            .render()
        )

        __class__.CODE_SEGMENT_TEMPLACE.add(
            e=__class__.INIT_SEGMENT_TEMPLACE.render()
        )


        print(__class__.DATA_SEGMENT_TEMPLACE.render())
        print(__class__.CODE_SEGMENT_TEMPLACE.render())

    @AST_visits(Class)
    def visitClass(class_: Class):
        class_: Class
        __class__.INIT_SEGMENT_TEMPLACE.add(e=build_init(class_))
        __class__.PROTOTYPES_SEGMENT_TEMPLACE.add(e=__class__.build_prototype(class_))

        for feature in class_.features:
            __class__.visit(feature)
    
    @AST_visits(AttributeDefinition)
    def visitAttributeDefinition(attributeDefinition: AttributeDefinition):
        ...
        # TODO: not sure, may refactor


    @AST_visits(FunctionDefinition)
    def visitFunctionDefinition(functionDefinition: FunctionDefinition):
        functionDefinition: FunctionDefinition

        for i, param in enumerate(functionDefinition.parameters):
            param.index = i

        __class__.stack_element_count = 0

        __class__.CODE_SEGMENT_TEMPLACE.add(e=templates["function_enter"].add(
            name=f"{functionDefinition.scope_parent.name.value}.{functionDefinition.name.value}",
            code=__class__.visit(functionDefinition.body),
            param_count=4*len(functionDefinition.parameters)
        ).render())

        assert __class__.stack_element_count == 0

    @AST_visits(INT)
    def visitINT(target: INT):
        return f"\tla $a0 {__class__.get_int_const(target.value)}"

    @AST_visits(String)
    def visitString(target: String):
        return f"\tla $a0 {__class__.get_string_const(target.value)}"

    @AST_visits(Bool)
    def visitBool(target: Bool):
        return f"\tla $a0 Bool_const_{str(target.value).lower()}"

    def get_call_arguments(call: Union[ExplicitCall, ImplicitCall]):
        call: Union[ExplicitCall, ImplicitCall]
        code = templates["sequence"]
        
        for arg in call.args[::-1]:
            code.add(e=templates["call_argument"].add(
                arg_code=__class__.visit(arg)
            ).render())
            __class__.stack_element_count += 1

        return code.render()


    @AST_visits(ExplicitCall)
    def visitExplicitCall(explicitCall: ExplicitCall):
        explicitCall: ExplicitCall

        target = __class__.visit(explicitCall.target)
        __class__.branch_count+=1

        if not explicitCall.upcall_target:
            code = templates["explicit_call_dynamic"].add(
                target=target,
                branch_count=__class__.branch_count,
                filename=__class__.get_string_const(get_token_file(explicitCall.token)),
                line_no=explicitCall.token.line,
                method_index=4*explicitCall.target.static_type.definition.get_function(explicitCall.name).index,
                call_arguments=__class__.get_call_arguments(explicitCall),
            ).render()

            __class__.stack_element_count -= len(explicitCall.args)

            return code

        code = templates["explicit_call_static"].add(
            target=target,
            branch_count=__class__.branch_count,
            filename=__class__.get_string_const(get_token_file(explicitCall.token)),
            line_no=explicitCall.token.line,
            method_name=f"{explicitCall.upcall_target.value}.{explicitCall.name.value}",
            call_arguments=__class__.get_call_arguments(explicitCall),
        ).render()

        __class__.stack_element_count -= len(explicitCall.args)

        return code

    @AST_visits(ImplicitCall)
    def visitImplicitCall(implicitCall: ImplicitCall):
        implicitCall: ImplicitCall

        code = templates["implicit_call"].add(
            method_index=4*implicitCall.name.containing_scope.get_function(implicitCall.name).index,
            call_arguments=__class__.get_call_arguments(implicitCall),
        ).render()

        __class__.stack_element_count -= len(implicitCall.args)

        return code

    @AST_visits(Id)
    def visitId(id_: Id):
        id_: Id

        if id_.value == "self":
            return "\tmove $a0, $s0"

        if isinstance(id_.definition, AttributeDefinition):
            definition: AttributeDefinition = id_.definition
            return f"\tlw $a0 {12+4*definition.index}($s0)"

        if isinstance(id_.definition, FunctionParameter):
            definition: AttributeDefinition = id_.definition
            return f"\tlw $a0 {12+4*definition.index}($fp)"

        if isinstance(id_.definition, Union[LetEntry, CaseBranch]):
            definition: Union[LetEntry, CaseBranch] = id_.definition
            return f"\tlw $a0 {-4*definition.index}($fp)"


        raise Exception("stack base ofset")
            
    @AST_visits(Block)
    def visitBlock(block: Block):
        block: Block

        sequence = templates["sequence"]

        for expr in block.expresions:
            sequence.add(e=__class__.visit(expr))

        return sequence.render()

    @AST_visits(Assign)
    def visitAssign(assign: Assign):
        assign: Assign
        if isinstance(assign.target.definition, AttributeDefinition):
            definition: AttributeDefinition = assign.target.definition
            return templates["sequence"].add(
                e=__class__.visit(assign.new_value)
            ).add(e=f"\tsw $a0 {12+4*definition.index}($s0)"
            ).render()
        
        if isinstance(assign.target.definition, FunctionParameter):
            definition: FunctionParameter = assign.target.definition
            return templates["sequence"].add(
                e=__class__.visit(assign.new_value)
            ).add(e=f"\tsw $a0 {12+4*definition.index}($fp)"
            ).render()
        
        if isinstance(assign.target.definition, Union[LetEntry, CaseBranch]):
            definition: Union[LetEntry, CaseBranch] = assign.target.definition
            return templates["sequence"].add(
                e=__class__.visit(assign.new_value)
            ).add(e=f"\tsw $a0 {-4*definition.index}($fp)"
            ).render()
            
        raise Exception("stack base ofset")

    @AST_visits(Let)
    def visitLet(let: Let):
        let: Let
        code = templates["let"].add(
            entry_count=4*len(let.entries)
        )
        for entry in let.entries:
            default_code: str

            if entry.default_value:
                default_code = __class__.visit(entry.default_value)
            
            elif entry.type.value == "Int":
                default_code = f"\tla $a0 {__class__.get_int_const(0)}"
            elif entry.type.value == "String":
                default_code = f"\tla $a0 {__class__.get_string_const('')}"
            elif entry.type.value == "Bool":
                default_code = f"\tla $a0 Bool_const_false"
            else:
                default_code = "\tli $a0 0"

            code.add(entry=templates["let_entry"].add(
                default_code=default_code
            ).render())
            __class__.stack_element_count += 1
            entry.index = __class__.stack_element_count

        code.add(body=__class__.visit(let.body))

        __class__.stack_element_count -= len(let.entries)
        return code.render()

    @AST_visits(New)
    def VisitNew(new: New):
        new: New
        if type(new.target) is Type:
            return templates["new"].add(
                target=new.target.value
            ).render()

        return templates["new_self"].render()

    @AST_visits(If)
    def VisitIf(if_: If):
        if_: If
        branch_count = __class__.branch_count
        __class__.branch_count +=1

        return templates["if"].add(
            cond=__class__.visit(if_.condition),
            is_true=__class__.visit(if_.is_true),
            is_false=__class__.visit(if_.is_false),
            branch_count=branch_count,
        ).render()

    @AST_visits(IsVoid)
    def VisitIf(isVoid: IsVoid):
        isVoid: IsVoid

        return templates["is_void"].add(
            cond=__class__.visit(isVoid.target)
        ).render()

    @AST_visits(Not)
    def VisitIf(not_: Not):
        not_: Not

        return templates["not"].add(
            cond=__class__.visit(not_.target)
        ).render()

    @AST_visits(Negate)
    def VisitNegate(negate: Negate):
        negate: Negate

        return templates["negate"].add(
            target=__class__.visit(negate.target)
        ).render()

    @AST_visits(Arithmetic)
    def VisitArithmetic(arithmetic: Arithmetic):
        arithmetic: Arithmetic

        code = templates["arithm"].add(calc={
            "+":"\tadd		$t1  $t1  $t2",
            "-":"\tsub		$t1  $t1  $t2",
            "*":"\tmul 	    $t1  $t1  $t2",
            "/":"\tdiv		$t1  $t1  $t2",
        }[arithmetic.operator])
        
        code.add(
            elem1=__class__.visit(arithmetic.elem1)
        )
        __class__.stack_element_count +=1
        code.add(
            elem2=__class__.visit(arithmetic.elem2)
        )
        __class__.stack_element_count -=1
        
        return code.render()
    
    @AST_visits(Comparison)
    def VisitComparison(comparison: Comparison):
        comparison: Comparison

        branch_count = __class__.branch_count
        __class__.branch_count +=1

        code = templates[{
            "=":"is_equal",
            "<":"less_than",
            "<=":"less_than_equal",
        }[comparison.operator]].add(branch_count=__class__.branch_count)
        
        code.add(
            elem1=__class__.visit(comparison.elem1)
        )
        __class__.stack_element_count +=1
        code.add(
            elem2=__class__.visit(comparison.elem2)
        )
        __class__.stack_element_count -=1
        
        return code.render()

    @AST_visits(While)
    def visitWhile(while_: While):
        while_: While


        return templates["while"].add(
            branch_count=__class__.get_next_branch(),
            cond=__class__.visit(while_.condition),
            body=__class__.visit(while_.body),
        ).render()

    @AST_visits(Case)
    def visitCase(case_: Case):
        case_: Case


        target_code = __class__.visit(case_.target)

        __class__.stack_element_count += 1
        target_stack_offset = __class__.stack_element_count
        case_number = __class__.get_next_branch()


        code = templates["case"].add(
            target=target_code,
            branch_count=case_number,
            filename=__class__.get_string_const(get_token_file(case_.token)),
            line_no=case_.token.line,
        )

        for case_branch in case_.cases:
            case_branch.index = target_stack_offset
            code.add(body=templates["case_branch"].add(
                body=__class__.visit(case_branch.expresion),
                target_tag=case_branch.type.definition.tag,
                branch_count=__class__.get_next_branch(),
                exit_case_label=case_number
            ).render())

        __class__.stack_element_count -= 1
        return code.render()

