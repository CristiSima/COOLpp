from antlr4.Lexer import Token
from typing import List, Dict, Union
from dataclasses import dataclass, field, KW_ONLY
from functools import partial

__all__ = [
    "ASTNode", "Scope",
    "Id", "Type", "SelfType", "INT", "Bool", "String",
    "Block", "While", "If", "Case", "CaseBranch", "Let", "LetEntry",
    "Negate", "IsVoid", "Not", "Arithmetic", "Comparison",
    "ImplicitCall", "ExplicitCall",
    "Instanciation", "Assign", "New",
    "FunctionDefinition", "FunctionParameter","AttributeDefinition", "Class", "Program",
    "DummyClass", "Expresion",
]


SymbolDefinition = Union["Class", "AttributeDefinition", "FunctionDefinition", "FunctionParameter", "LetEntry", "CaseBranch"]
Symbol = Union["Id", "Type", SymbolDefinition]


def DummyClass(class_):
    return partial(class_, ...)


@dataclass
class Scope:
    _scope_store:           Dict[str, Symbol]               = field(init = False, default_factory=dict, compare=False)
    _scope_function_store:  Dict[str, "FunctionDefinition"] = field(init = False, default_factory=dict, compare=False)
    scope_parent:           "Scope"                         = field(init = False, default=None, compare=False)

    def add(self, symbol_name: Union[str, "Id", "Type"], elem: Symbol):
        symbol_name: str = symbol_name.value if isinstance(symbol_name, Union[Id, Type]) else symbol_name

        if symbol_name in self._scope_store:
            return False

        self._scope_store[symbol_name] = elem

        return True

    def add_function(self, function_name: Union[str, "Id"], elem: "FunctionDefinition"):
        symbol_name: str = function_name.value if isinstance(function_name, Union[Id]) else function_name

        if function_name in self._scope_function_store:
            return False
            
        self._scope_function_store[function_name] = elem

        return True

    def __getitem__(self, symbol_name: Union[str, "Id", "Type"]) -> Symbol:
        symbol_name: str = symbol_name.value if isinstance(symbol_name, Union[Id, Type]) else symbol_name
        
        if symbol_name in self._scope_store:
            return self._scope_store[symbol_name]

        if self.scope_parent:
            return self.scope_parent[symbol_name]

        return None

    def get_function(self, function_name: Union[str, "Id"]) -> "FunctionDefinition":
        function_name: str = function_name.value if isinstance(function_name, Id) else function_name

        if function_name in self._scope_function_store:
            return self._scope_function_store[function_name]

        if self.scope_parent:
            return self.scope_parent.get_function(function_name)

        return None

    # unused
    def __delitem__(self, symbol_name: str):
        del self._scope_store[symbol_name]

@dataclass
class SymbolReference:
    containing_scope: Scope = field(init = True, kw_only=True, default=None, repr=False, compare=False)

    @property
    def definition(self) -> SymbolDefinition:
        return self.containing_scope[self.value]

    @property
    def function_definition(self) -> SymbolDefinition:
        return self.containing_scope.get_function(self.value)

@dataclass
class Symbol:
    name: str

@dataclass
class ASTNode:
    pass

@dataclass
class Expresion(ASTNode):
    token: Token = field(compare=False, repr=False)
    static_type: "Type" = field(init=False, default=None)

@dataclass
class Type(Expresion, SymbolReference):
    value: str

    def __hash__(self):
        return hash(self.value)

@dataclass
class SelfType(Type):
    value:      str  = field(init=True, kw_only=True, compare=False, default="SELF_TYPE")
    used_in:    Type = field(init=True, kw_only=True, compare=False, default=None)

    def __repr__(self) -> str: 
        return f"SelfType({self.used_in.value if self.used_in else None})"

    def __hash__(self):
        return hash(self.used_in.value)

@dataclass
class Id(Expresion, SymbolReference):
    value:  str

@dataclass
class INT(Expresion):
    value: int

@dataclass
class String(Expresion):
    value: str

@dataclass
class Bool(Expresion):
    value: bool

@dataclass
class Instanciation(Expresion):
    type:  Type

@dataclass
class CaseBranch(Scope):
    name:       Id
    type:       Type
    expresion:  Expresion

    index:          int = field(init=False, default=None)

@dataclass
class Case(Expresion):
    target:     Expresion
    cases:      List[CaseBranch]

@dataclass
class LetEntry(Scope):
    name:           Id
    type:           Type
    default_value:  Expresion

    index:          int = field(init=False, default=None)

@dataclass
class Let(Expresion):
    entries:    List[LetEntry]
    body:       Expresion

@dataclass
class Block(Expresion):
    expresions:     List[Expresion]

@dataclass
class While(Expresion):
    condition:      Expresion
    body:           Expresion

@dataclass
class If(Expresion):
    condition:      Expresion
    is_true:        Expresion
    is_false:       Expresion

@dataclass
class ImplicitCall(Expresion):
    name:           Id
    args:           List[Expresion]

@dataclass
class ExplicitCall(Expresion):
    target:         Expresion
    upcall_target:  Type
    name:           Id
    args:           List[Expresion]

@dataclass
class Negate(Expresion):
    target:         Expresion

@dataclass
class IsVoid(Expresion):
    target:         Expresion

@dataclass
class Not(Expresion):
    target:         Expresion

@dataclass
class Assign(Expresion):
    target:         Id
    new_value:      Expresion

@dataclass
class New(Expresion):
    target:         Type

@dataclass
class Arithmetic(Expresion):
    elem1:          Expresion
    elem2:          Expresion
    operator:       str

@dataclass
class Comparison(Expresion):
    elem1:          Expresion
    elem2:          Expresion
    operator:       str

@dataclass
class FunctionParameter:
    name:           Id
    type:           Type
    
    # used at code generation
    index:          int = field(init=False, default=None)


@dataclass
class FunctionDefinition(ASTNode, Scope):
    name:           Id
    parameters:     List[FunctionParameter]
    return_type:    Type
    body:           Expresion

    # used at code generation
    index:          int = field(init=False, default=None)

    @property
    def owned_by(self) -> "Class":
        return self.scope_parent

@dataclass
class AttributeDefinition(ASTNode):
    name:           Id
    type:           Type
    default_value:  Expresion

    # used at code generation
    index:          int = field(init=False, default=None)
    
    @property
    def owned_by(self) -> "Class":
        return self.name.containing_scope


@dataclass
class Class(ASTNode, Scope):
    name:           Type
    base_class:     Type
    features:       List[FunctionDefinition|AttributeDefinition]
    in_loop:        bool = field(init=False, default=False)
    
    # used at code generation
    tag:            int = field(init=False, default=None)


@dataclass
class Program(ASTNode, Scope):
    classes:        List[Class]


