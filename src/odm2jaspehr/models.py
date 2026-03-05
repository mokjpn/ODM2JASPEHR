from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class CodeListItem:
    coded_value: str
    decode: str


@dataclass(slots=True)
class CodeList:
    oid: str
    name: str
    items: list[CodeListItem] = field(default_factory=list)


@dataclass(slots=True)
class ItemDef:
    oid: str
    name: str
    data_type: str
    question: str | None = None
    description: str | None = None
    prompt_alias: str | None = None
    completion_instruction: str | None = None
    length: int | None = None
    codelist_oid: str | None = None
    value_list_oid: str | None = None
    range_checks: list["RangeCheck"] = field(default_factory=list)


@dataclass(slots=True)
class RangeCheck:
    comparator: str
    check_values: list[str] = field(default_factory=list)
    item_oid: str | None = None


@dataclass(slots=True)
class ValueListItemRef:
    item_oid: str
    mandatory: bool = False
    order_number: int | None = None
    where_clause_oids: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ValueListDef:
    oid: str
    item_refs: list[ValueListItemRef] = field(default_factory=list)


@dataclass(slots=True)
class WhereClauseDef:
    oid: str
    range_checks: list[RangeCheck] = field(default_factory=list)


@dataclass(slots=True)
class ItemRef:
    item_oid: str
    mandatory: bool = False
    order_number: int | None = None


@dataclass(slots=True)
class ItemGroupDef:
    oid: str
    name: str
    repeating: bool = False
    item_refs: list[ItemRef] = field(default_factory=list)


@dataclass(slots=True)
class ItemGroupRef:
    item_group_oid: str
    mandatory: bool = False
    order_number: int | None = None


@dataclass(slots=True)
class FormDef:
    oid: str
    name: str
    repeating: bool = False
    item_group_refs: list[ItemGroupRef] = field(default_factory=list)


@dataclass(slots=True)
class OdmMetadata:
    study_oid: str | None
    metadata_version_oid: str | None
    forms: list[FormDef] = field(default_factory=list)
    item_groups: dict[str, ItemGroupDef] = field(default_factory=dict)
    items: dict[str, ItemDef] = field(default_factory=dict)
    codelists: dict[str, CodeList] = field(default_factory=dict)
    value_lists: dict[str, ValueListDef] = field(default_factory=dict)
    where_clauses: dict[str, WhereClauseDef] = field(default_factory=dict)
