from typing import Optional, List
from pydantic import Field
from cognee.low_level import DataPoint
from cognee.shared.CodeGraphEntities import CodeFile as BaseCodeFile


class InterfaceDefinition(DataPoint):
    """Represents a TypeScript interface declaration."""
    name: str
    start_point: tuple
    end_point: tuple
    source_code: str
    file_path: Optional[str] = None
    metadata: dict = {"index_fields": ["source_code"]}


class TypeAliasDefinition(DataPoint):
    """Represents a TypeScript type alias declaration."""
    name: str
    start_point: tuple
    end_point: tuple
    source_code: str
    file_path: Optional[str] = None
    metadata: dict = {"index_fields": ["source_code"]}


class EnumDefinition(DataPoint):
    """Represents a TypeScript enum declaration."""
    name: str
    start_point: tuple
    end_point: tuple
    source_code: str
    file_path: Optional[str] = None
    metadata: dict = {"index_fields": ["source_code"]}


class ExportStatement(DataPoint):
    """Represents an export from a TypeScript file."""
    name: str                    # exported name (or '*' for re-exports, 'default' for default exports)
    local_name: Optional[str] = None  # original name if aliased
    is_default: bool = False     # True for default exports
    is_type_only: bool = False   # True for 'export type'
    start_point: tuple
    end_point: tuple
    source_code: str
    file_path: Optional[str] = None
    metadata: dict = {"index_fields": ["name"]}


class MethodDefinition(DataPoint):
    """Represents a method within a class."""
    name: str
    class_name: str              # parent class name
    is_static: bool = False
    is_async: bool = False
    is_private: bool = False     # TypeScript # private fields or 'private' keyword
    is_getter: bool = False
    is_setter: bool = False
    is_constructor: bool = False
    start_point: tuple
    end_point: tuple
    source_code: str
    file_path: Optional[str] = None
    metadata: dict = {"index_fields": ["source_code"]}


class TypeScriptCodeFile(BaseCodeFile):
    """Extended CodeFile with TypeScript-specific fields."""
    provides_interface_definition: List[InterfaceDefinition] = Field(default_factory=list)
    provides_type_alias: List[TypeAliasDefinition] = Field(default_factory=list)
    provides_enum_definition: List[EnumDefinition] = Field(default_factory=list)
    exports: List[ExportStatement] = Field(default_factory=list)
    provides_method_definition: List[MethodDefinition] = Field(default_factory=list)


TypeScriptCodeFile.model_rebuild()
