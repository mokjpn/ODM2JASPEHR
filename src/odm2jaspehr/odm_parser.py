from __future__ import annotations

from xml.etree import ElementTree as ET

from .models import (
    CodeList,
    CodeListItem,
    FormDef,
    ItemDef,
    ItemGroupDef,
    ItemGroupRef,
    ItemRef,
    OdmMetadata,
    RangeCheck,
    ValueListDef,
    ValueListItemRef,
    WhereClauseDef,
)


def _local_name(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[1]
    return tag


def _find_first_text(elem: ET.Element, path_names: list[str]) -> str | None:
    current = elem
    for path_name in path_names:
        child = next((c for c in current if _local_name(c.tag) == path_name), None)
        if child is None:
            return None
        current = child
    text = (current.text or "").strip()
    return text or None


def _get_attr_by_local_name(elem: ET.Element, attr_local_name: str) -> str | None:
    for key, value in elem.attrib.items():
        local_key = key.rsplit("}", 1)[-1]
        if local_key == attr_local_name:
            return value
    return None


def _to_bool(value: str | None) -> bool:
    return (value or "").strip().lower() == "yes"


def _to_int(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def parse_odm(xml_path: str) -> OdmMetadata:
    tree = ET.parse(xml_path)
    root = tree.getroot()

    study = next((e for e in root if _local_name(e.tag) == "Study"), None)
    study_oid = study.attrib.get("OID") if study is not None else None

    metadata_version = None
    if study is not None:
        metadata_version = next((e for e in study if _local_name(e.tag) == "MetaDataVersion"), None)

    if metadata_version is None:
        raise ValueError("MetaDataVersion element not found in ODM XML")

    odm = OdmMetadata(
        study_oid=study_oid,
        metadata_version_oid=metadata_version.attrib.get("OID"),
    )

    for element in metadata_version:
        name = _local_name(element.tag)

        if name == "CodeList":
            codelist = CodeList(
                oid=element.attrib["OID"],
                name=element.attrib.get("Name", element.attrib["OID"]),
            )
            for item in element:
                if _local_name(item.tag) != "CodeListItem":
                    continue
                decode = _find_first_text(item, ["Decode", "TranslatedText"]) or item.attrib.get("CodedValue", "")
                codelist.items.append(
                    CodeListItem(
                        coded_value=item.attrib.get("CodedValue", ""),
                        decode=decode,
                    )
                )
            odm.codelists[codelist.oid] = codelist

        if name == "ItemDef":
            range_checks: list[RangeCheck] = []
            prompt_alias: str | None = None
            completion_instruction: str | None = None
            codelist_oid: str | None = None
            value_list_oid: str | None = None
            for child in element:
                child_name = _local_name(child.tag)
                if child_name != "RangeCheck":
                    if child_name == "Alias":
                        context = (child.attrib.get("Context", "") or "").strip().lower()
                        alias_name = (child.attrib.get("Name", "") or "").strip()
                        if not alias_name:
                            continue
                        if context == "prompt" and prompt_alias is None:
                            prompt_alias = alias_name
                        if context in {"completioninstructions", "(completioninstructions)"} and completion_instruction is None:
                            completion_instruction = alias_name
                    if child_name == "CodeListRef" and codelist_oid is None:
                        codelist_oid = _get_attr_by_local_name(child, "CodeListOID")
                    if child_name == "ValueListRef" and value_list_oid is None:
                        value_list_oid = _get_attr_by_local_name(child, "ValueListOID")
                    continue
                check_values = [(_item.text or "").strip() for _item in child if _local_name(_item.tag) == "CheckValue"]
                check_values = [value for value in check_values if value]
                if not check_values:
                    continue
                range_checks.append(
                    RangeCheck(
                        comparator=(_get_attr_by_local_name(child, "Comparator") or "").strip().upper(),
                        check_values=check_values,
                        item_oid=_get_attr_by_local_name(child, "ItemOID"),
                    )
                )

            odm.items[element.attrib["OID"]] = ItemDef(
                oid=element.attrib["OID"],
                name=element.attrib.get("Name", element.attrib["OID"]),
                data_type=element.attrib.get("DataType", "text"),
                question=_find_first_text(element, ["Question", "TranslatedText"]),
                description=_find_first_text(element, ["Description", "TranslatedText"]),
                prompt_alias=prompt_alias,
                completion_instruction=completion_instruction,
                length=_to_int(element.attrib.get("Length")),
                codelist_oid=codelist_oid,
                value_list_oid=value_list_oid,
                range_checks=range_checks,
            )

        if name == "ValueListDef":
            value_list = ValueListDef(oid=element.attrib["OID"])
            for child in element:
                if _local_name(child.tag) != "ItemRef":
                    continue
                where_clause_oids = [
                    oid
                    for oid in (
                        _get_attr_by_local_name(where_ref, "WhereClauseOID")
                        for where_ref in child
                        if _local_name(where_ref.tag) == "WhereClauseRef"
                    )
                    if oid
                ]
                item_oid = _get_attr_by_local_name(child, "ItemOID") or ""
                value_list.item_refs.append(
                    ValueListItemRef(
                        item_oid=item_oid,
                        mandatory=_to_bool(_get_attr_by_local_name(child, "Mandatory")),
                        order_number=_to_int(_get_attr_by_local_name(child, "OrderNumber")),
                        where_clause_oids=where_clause_oids,
                    )
                )
            value_list.item_refs.sort(key=lambda ref: (ref.order_number is None, ref.order_number))
            odm.value_lists[value_list.oid] = value_list

        if name == "WhereClauseDef":
            where_clause = WhereClauseDef(oid=element.attrib["OID"])
            for child in element:
                if _local_name(child.tag) != "RangeCheck":
                    continue
                check_values = [(_item.text or "").strip() for _item in child if _local_name(_item.tag) == "CheckValue"]
                check_values = [value for value in check_values if value]
                if not check_values:
                    continue
                where_clause.range_checks.append(
                    RangeCheck(
                        comparator=(_get_attr_by_local_name(child, "Comparator") or "").strip().upper(),
                        check_values=check_values,
                        item_oid=_get_attr_by_local_name(child, "ItemOID"),
                    )
                )
            odm.where_clauses[where_clause.oid] = where_clause

        if name == "ItemGroupDef":
            item_group = ItemGroupDef(
                oid=element.attrib["OID"],
                name=element.attrib.get("Name", element.attrib["OID"]),
                repeating=_to_bool(element.attrib.get("Repeating")),
            )
            for item_ref in element:
                if _local_name(item_ref.tag) != "ItemRef":
                    continue
                item_group.item_refs.append(
                    ItemRef(
                        item_oid=item_ref.attrib.get("ItemOID", ""),
                        mandatory=_to_bool(item_ref.attrib.get("Mandatory")),
                        order_number=_to_int(item_ref.attrib.get("OrderNumber")),
                    )
                )
            item_group.item_refs.sort(key=lambda ref: (ref.order_number is None, ref.order_number))
            odm.item_groups[item_group.oid] = item_group

        if name == "FormDef":
            form = FormDef(
                oid=element.attrib["OID"],
                name=element.attrib.get("Name", element.attrib["OID"]),
                repeating=_to_bool(element.attrib.get("Repeating")),
            )
            for group_ref in element:
                if _local_name(group_ref.tag) != "ItemGroupRef":
                    continue
                form.item_group_refs.append(
                    ItemGroupRef(
                        item_group_oid=group_ref.attrib.get("ItemGroupOID", ""),
                        mandatory=_to_bool(group_ref.attrib.get("Mandatory")),
                        order_number=_to_int(group_ref.attrib.get("OrderNumber")),
                    )
                )
            form.item_group_refs.sort(key=lambda ref: (ref.order_number is None, ref.order_number))
            odm.forms.append(form)

    return odm
