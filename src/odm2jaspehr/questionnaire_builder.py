from __future__ import annotations

from datetime import UTC, datetime
import re
from urllib.parse import quote

from .models import FormDef, ItemDef, ItemGroupRef, OdmMetadata, ValueListItemRef

JASPEHR_QUESTIONNAIRE_PROFILE = "http://www.hosp.ncgm.go.jp/JASPEHR/fhir/StructureDefinition/jaspehr-questionnaire"
MIN_VALUE_EXTENSION_URL = "http://hl7.org/fhir/StructureDefinition/minValue"
MAX_VALUE_EXTENSION_URL = "http://hl7.org/fhir/StructureDefinition/maxValue"
QUESTIONNAIRE_ITEM_CONTROL_URL = "http://hl7.org/fhir/StructureDefinition/questionnaire-itemControl"
QUESTIONNAIRE_ITEM_CONTROL_SYSTEM = "http://hl7.org/fhir/questionnaire-item-control"
SDC_ENABLE_WHEN_EXPRESSION_URL = "http://hl7.org/fhir/uv/sdc/StructureDefinition/sdc-questionnaire-enableWhenExpression"

_ALLOWED_NAME_RE = re.compile(r"[^A-Za-z0-9_]", flags=re.ASCII)
_ALLOWED_LINK_ID_RE = re.compile(r"[^A-Za-z0-9\-.]", flags=re.ASCII)


def _sanitize_name(value: str, max_len: int = 15) -> str:
    cleaned = _ALLOWED_NAME_RE.sub("_", value)
    if not cleaned:
        cleaned = "Q"
    if not cleaned[0].isalpha() or not cleaned[0].isupper():
        cleaned = f"Q{cleaned}"
    if len(cleaned) > max_len:
        cleaned = cleaned[:max_len]
    return cleaned


def _sanitize_link_id(value: str, fallback_prefix: str = "item") -> str:
    cleaned = _ALLOWED_LINK_ID_RE.sub("-", value)
    cleaned = cleaned.strip("-.")
    if not cleaned:
        cleaned = f"{fallback_prefix}-1"
    if len(cleaned) > 255:
        cleaned = cleaned[:255]
    return cleaned


def _allocate_unique_link_id(base_value: str, used_link_ids: set[str], fallback_prefix: str = "item") -> str:
    base = _sanitize_link_id(base_value, fallback_prefix=fallback_prefix)
    if base not in used_link_ids:
        used_link_ids.add(base)
        return base

    suffix_num = 2
    while True:
        suffix = f"-{suffix_num}"
        trimmed = base[: max(1, 255 - len(suffix))]
        candidate = f"{trimmed}{suffix}"
        if candidate not in used_link_ids:
            used_link_ids.add(candidate)
            return candidate
        suffix_num += 1


def _map_item_type(item_def: ItemDef) -> str:
    if item_def.codelist_oid:
        return "choice"

    data_type = item_def.data_type.lower()
    mapping = {
        "text": "text",
        "string": "string",
        "integer": "integer",
        "float": "decimal",
        "double": "decimal",
        "decimal": "decimal",
        "date": "date",
        "datetime": "dateTime",
        "time": "time",
        "boolean": "boolean",
        "uri": "url",
    }
    return mapping.get(data_type, "string")


def _join_canonical(base: str, oid: str) -> str:
    encoded_oid = quote(oid, safe="-._~")
    if base.startswith("urn:"):
        sep = "" if base.endswith(":") else ":"
        return f"{base}{sep}{encoded_oid}"
    return f"{base.rstrip('/')}/{encoded_oid}"


def _to_typed_value(item_def: ItemDef, raw_value: str) -> tuple[str, int | float | str]:
    data_type = item_def.data_type.lower()
    try:
        if data_type == "integer":
            return "valueInteger", int(raw_value)
        if data_type in {"float", "double", "decimal"}:
            return "valueDecimal", float(raw_value)
        if data_type == "date":
            return "valueDate", raw_value
        if data_type == "datetime":
            return "valueDateTime", raw_value
        if data_type == "time":
            return "valueTime", raw_value
    except ValueError:
        return "valueString", raw_value
    return "valueString", raw_value


def _fhirpath_string_literal(raw_value: str) -> str:
    escaped = raw_value.replace("\\", "\\\\").replace("'", "\\'")
    return f"'{escaped}'"


def _fhirpath_literal(item_def: ItemDef | None, raw_value: str) -> str:
    if item_def is None:
        return _fhirpath_string_literal(raw_value)

    data_type = item_def.data_type.lower()
    try:
        if data_type == "integer":
            return str(int(raw_value))
        if data_type in {"float", "double", "decimal"}:
            return str(float(raw_value))
        if data_type == "boolean":
            return "true" if raw_value.strip().lower() in {"1", "true", "yes", "y"} else "false"
        if data_type == "date":
            return f"@{raw_value}"
        if data_type == "datetime":
            return f"@{raw_value}"
        if data_type == "time":
            normalized = raw_value if raw_value.startswith("T") else f"T{raw_value}"
            return f"@{normalized}"
    except ValueError:
        return _fhirpath_string_literal(raw_value)
    return _fhirpath_string_literal(raw_value)


def _question_text(item_def: ItemDef) -> str:
    return item_def.question or item_def.prompt_alias or item_def.name


def _choice_item_control_extension(control_code: str) -> dict:
    return {
        "url": QUESTIONNAIRE_ITEM_CONTROL_URL,
        "valueCodeableConcept": {
            "coding": [
                {
                    "system": QUESTIONNAIRE_ITEM_CONTROL_SYSTEM,
                    "code": control_code,
                }
            ]
        },
    }


def _build_range_extensions(item_def: ItemDef) -> list[dict]:
    min_raw: str | None = None
    max_raw: str | None = None
    for check in item_def.range_checks:
        if not check.check_values:
            continue
        check_value = check.check_values[0]
        if check.comparator == "GE":
            min_raw = check_value
        elif check.comparator == "LE":
            max_raw = check_value
        elif check.comparator == "EQ":
            min_raw = check_value
            max_raw = check_value

    extensions: list[dict] = []
    if min_raw is not None:
        value_key, value = _to_typed_value(item_def, min_raw)
        extensions.append({"url": MIN_VALUE_EXTENSION_URL, value_key: value})
    if max_raw is not None:
        value_key, value = _to_typed_value(item_def, max_raw)
        extensions.append({"url": MAX_VALUE_EXTENSION_URL, value_key: value})
    return extensions


def _answer_value_path(link_id: str) -> str:
    return f"%resource.repeat(item).where(linkId='{link_id}').answer.value"


def _range_check_expression(check, odm: OdmMetadata, resolve_link_id) -> str | None:
    if not check.item_oid or not check.check_values:
        return None
    source_item = odm.items.get(check.item_oid)
    path = _answer_value_path(resolve_link_id(check.item_oid))
    literals = [_fhirpath_literal(source_item, raw) for raw in check.check_values]

    if check.comparator in {"EQ", "IN"}:
        parts = [f"({path} = {literal})" for literal in literals]
        return " or ".join(parts) if len(parts) > 1 else parts[0]
    if check.comparator in {"NE", "NOTIN"}:
        parts = [f"({path} != {literal})" for literal in literals]
        return " and ".join(parts) if len(parts) > 1 else parts[0]
    if check.comparator in {"GT", "GE", "LT", "LE"}:
        op = {"GT": ">", "GE": ">=", "LT": "<", "LE": "<="}[check.comparator]
        parts = [f"({path} {op} {literal})" for literal in literals]
        return " and ".join(parts) if len(parts) > 1 else parts[0]
    return None


def _build_enable_when_expression(vlist_item_ref: ValueListItemRef, odm: OdmMetadata, resolve_link_id) -> str | None:
    clause_expressions: list[str] = []
    for where_clause_oid in vlist_item_ref.where_clause_oids:
        where_clause = odm.where_clauses.get(where_clause_oid)
        if where_clause is None:
            continue
        check_expressions = [
            expr for expr in (_range_check_expression(check, odm, resolve_link_id) for check in where_clause.range_checks) if expr
        ]
        if not check_expressions:
            continue
        clause = " and ".join(f"({expr})" for expr in check_expressions)
        clause_expressions.append(clause)

    if not clause_expressions:
        return None
    if len(clause_expressions) == 1:
        return clause_expressions[0]
    return " or ".join(f"({clause})" for clause in clause_expressions)


def _enable_when_expression_extension(expression: str) -> dict:
    return {
        "url": SDC_ENABLE_WHEN_EXPRESSION_URL,
        "valueExpression": {
            "language": "text/fhirpath",
            "expression": expression,
        },
    }


def _build_question_item(
    item_def: ItemDef,
    codelists: dict,
    codelist_mode: str,
    value_set_base: str,
    choice_item_control: str,
    link_id_override: str | None = None,
) -> dict:
    item_type = _map_item_type(item_def)
    item = {
        "linkId": _sanitize_link_id(link_id_override or item_def.oid, fallback_prefix="q"),
        "text": _question_text(item_def),
        "type": item_type,
    }
    if item_def.length and item_type in {"string", "text", "url"}:
        item["maxLength"] = item_def.length

    if item_def.codelist_oid:
        if codelist_mode == "valueset":
            item["answerValueSet"] = _join_canonical(value_set_base, item_def.codelist_oid)
        elif item_def.codelist_oid in codelists:
            codelist = codelists[item_def.codelist_oid]
            item["answerOption"] = [
                {
                    "valueCoding": {
                        "system": f"urn:odm:codelist:{codelist.oid}",
                        "code": answer.coded_value,
                        "display": answer.decode,
                    }
                }
                for answer in codelist.items
            ]

    if item_type == "choice":
        extensions = item.get("extension", [])
        extensions.append(_choice_item_control_extension(choice_item_control))
        item["extension"] = extensions

    extensions = _build_range_extensions(item_def)
    if extensions:
        existing = item.get("extension", [])
        existing.extend(extensions)
        item["extension"] = existing

    return item


def _build_form_items(
    form: FormDef,
    odm: OdmMetadata,
    codelist_mode: str,
    value_set_base: str,
    choice_item_control: str,
) -> list[dict]:
    form_items: list[dict] = []
    used_link_ids: set[str] = set()
    global_primary_link_by_item_oid: dict[str, str] = {}

    for group_ref in form.item_group_refs:
        item_group = odm.item_groups.get(group_ref.item_group_oid)
        if item_group is None:
            continue

        group_link_id = _allocate_unique_link_id(item_group.oid, used_link_ids, fallback_prefix="g")
        group_item: dict = {
            "linkId": group_link_id,
            "text": item_group.name,
            "type": "group",
            "repeats": item_group.repeating,
            "item": [],
        }
        if group_ref.mandatory:
            group_item["required"] = True

        group_primary_link_by_item_oid: dict[str, str] = {}
        direct_link_by_index: dict[int, str] = {}

        # Allocate direct item linkIds first so ValueListRef conditions can resolve references.
        for ref_index, item_ref in enumerate(item_group.item_refs):
            item_def = odm.items.get(item_ref.item_oid)
            if item_def is None:
                continue
            value_list = odm.value_lists.get(item_def.value_list_oid or "")
            if value_list and value_list.item_refs:
                continue
            direct_link = _allocate_unique_link_id(item_def.oid, used_link_ids, fallback_prefix="q")
            direct_link_by_index[ref_index] = direct_link
            group_primary_link_by_item_oid.setdefault(item_def.oid, direct_link)
            global_primary_link_by_item_oid.setdefault(item_def.oid, direct_link)

        def resolve_item_link(item_oid: str) -> str:
            return (
                group_primary_link_by_item_oid.get(item_oid)
                or global_primary_link_by_item_oid.get(item_oid)
                or _sanitize_link_id(item_oid, fallback_prefix="q")
            )

        for ref_index, item_ref in enumerate(item_group.item_refs):
            item_def = odm.items.get(item_ref.item_oid)
            if item_def is None:
                continue
            value_list = odm.value_lists.get(item_def.value_list_oid or "")
            if value_list and value_list.item_refs:
                for idx, value_item_ref in enumerate(value_list.item_refs, start=1):
                    value_item_def = odm.items.get(value_item_ref.item_oid)
                    if value_item_def is None:
                        continue

                    conditional_group_link = _allocate_unique_link_id(
                        f"{item_def.oid}.vl.{idx}",
                        used_link_ids,
                        fallback_prefix="vg",
                    )
                    conditional_group = {
                        "linkId": conditional_group_link,
                        "text": value_item_def.name,
                        "type": "group",
                        "item": [],
                    }
                    expression = _build_enable_when_expression(value_item_ref, odm, resolve_item_link)
                    if expression:
                        conditional_group["extension"] = [_enable_when_expression_extension(expression)]

                    question_link = _allocate_unique_link_id(
                        f"{item_def.oid}.{idx}",
                        used_link_ids,
                        fallback_prefix="q",
                    )
                    group_primary_link_by_item_oid.setdefault(value_item_def.oid, question_link)
                    global_primary_link_by_item_oid.setdefault(value_item_def.oid, question_link)
                    question = _build_question_item(
                        value_item_def,
                        odm.codelists,
                        codelist_mode=codelist_mode,
                        value_set_base=value_set_base,
                        choice_item_control=choice_item_control,
                        link_id_override=question_link,
                    )
                    if item_ref.mandatory or value_item_ref.mandatory:
                        question["required"] = True
                    conditional_group["item"].append(question)
                    group_item["item"].append(conditional_group)
                continue

            question_link = direct_link_by_index.get(ref_index)
            if question_link is None:
                question_link = _allocate_unique_link_id(item_def.oid, used_link_ids, fallback_prefix="q")
                group_primary_link_by_item_oid.setdefault(item_def.oid, question_link)
                global_primary_link_by_item_oid.setdefault(item_def.oid, question_link)
            question = _build_question_item(
                item_def,
                odm.codelists,
                codelist_mode=codelist_mode,
                value_set_base=value_set_base,
                choice_item_control=choice_item_control,
                link_id_override=question_link,
            )
            if item_ref.mandatory:
                question["required"] = True
            group_item["item"].append(question)

        form_items.append(group_item)

    return form_items


def _synthesize_forms_from_item_groups(odm: OdmMetadata) -> list[FormDef]:
    synthesized: list[FormDef] = []
    for item_group in odm.item_groups.values():
        form_oid = f"PFORM.{item_group.oid}"
        form_name = f"{item_group.name} (Pseudo Form)"
        synthesized.append(
            FormDef(
                oid=form_oid,
                name=form_name,
                repeating=item_group.repeating,
                item_group_refs=[
                    ItemGroupRef(
                        item_group_oid=item_group.oid,
                        mandatory=False,
                        order_number=1,
                    )
                ],
            )
        )
    return synthesized


def build_questionnaires(
    odm: OdmMetadata,
    canonical_base: str,
    status: str = "draft",
    version: str = "0.1.0",
    codelist_mode: str = "valueset",
    value_set_base: str = "urn:odm:codelist",
    choice_item_control: str = "drop-down",
    pseudo_form_mode: str = "off",
) -> list[dict]:
    base = canonical_base.rstrip("/")
    generated_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    questionnaires: list[dict] = []

    forms = odm.forms
    if not forms and pseudo_form_mode == "itemgroup":
        forms = _synthesize_forms_from_item_groups(odm)

    for form in forms:
        form_items = _build_form_items(
            form,
            odm,
            codelist_mode=codelist_mode,
            value_set_base=value_set_base,
            choice_item_control=choice_item_control,
        )
        questionnaire = {
            "resourceType": "Questionnaire",
            "meta": {
                "profile": [JASPEHR_QUESTIONNAIRE_PROFILE],
            },
            "url": f"{base}/Questionnaire/{quote(form.oid, safe='-._~')}",
            "identifier": [{"system": "urn:ietf:rfc:3986", "value": form.oid}],
            "version": version,
            "name": _sanitize_name(form.oid),
            "title": form.name,
            "status": status,
            "date": generated_at,
            "subjectType": ["Patient"],
            "item": form_items,
        }
        questionnaires.append(questionnaire)

    return questionnaires
