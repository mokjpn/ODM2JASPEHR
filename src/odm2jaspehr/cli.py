from __future__ import annotations

import argparse
import json
from pathlib import Path

from .odm_parser import parse_odm
from .questionnaire_builder import build_questionnaires


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="odm2jaspehr",
        description="Convert CDISC ODM XML form metadata to JASPEHR Questionnaire JSON.",
    )
    parser.add_argument("input", help="Path to ODM XML file")
    parser.add_argument(
        "--output-dir",
        default="out",
        help="Directory where Questionnaire JSON files are written (default: out)",
    )
    parser.add_argument(
        "--canonical-base",
        default="http://example.org/jaspehr",
        help="Canonical base URL for generated Questionnaire.url",
    )
    parser.add_argument(
        "--status",
        default="draft",
        choices=["draft", "active", "retired", "unknown"],
        help="FHIR Questionnaire.status (default: draft)",
    )
    parser.add_argument(
        "--version",
        default="0.1.0",
        help="FHIR Questionnaire.version (default: 0.1.0)",
    )
    parser.add_argument(
        "--codelist-mode",
        default="valueset",
        choices=["valueset", "option"],
        help="How CodeListRef is emitted: answerValueSet or answerOption (default: valueset)",
    )
    parser.add_argument(
        "--value-set-base",
        default="urn:odm:codelist",
        help="Base canonical/URN used to build answerValueSet from CodeListOID (default: urn:odm:codelist)",
    )
    parser.add_argument(
        "--pseudo-form-mode",
        default="off",
        choices=["off", "itemgroup"],
        help="Fallback when FormDef is absent: create pseudo forms from ItemGroupDef (default: off)",
    )
    parser.add_argument(
        "--choice-item-control",
        default="drop-down",
        choices=["drop-down", "radio-button"],
        help="questionnaire-itemControl code for choice items (default: drop-down)",
    )
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    odm = parse_odm(args.input)
    questionnaires = build_questionnaires(
        odm,
        canonical_base=args.canonical_base,
        status=args.status,
        version=args.version,
        codelist_mode=args.codelist_mode,
        value_set_base=args.value_set_base,
        choice_item_control=args.choice_item_control,
        pseudo_form_mode=args.pseudo_form_mode,
    )

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for resource in questionnaires:
        oid = resource["identifier"][0]["value"]
        path = output_dir / f"{oid}.questionnaire.json"
        path.write_text(json.dumps(resource, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Wrote {len(questionnaires)} Questionnaire resource(s) to {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
