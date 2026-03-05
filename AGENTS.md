# AGENTS.md

## Purpose
This file captures project-specific operating rules for AI/code agents working on `ODM2JASPEHR`.

## Project Summary
- Convert CDISC ODM / Define-XML metadata to JASPEHR v1.0-compatible FHIR Questionnaire JSON.
- Primary implementation language: Python.

## Agreed Defaults
1. `FormDef` exists:
- Generate Questionnaire from `FormDef` (normal mode).
- Do not synthesize pseudo forms.

2. `FormDef` does not exist:
- Use `--pseudo-form-mode itemgroup` to synthesize pseudo forms from `ItemGroupDef`.

3. CodeList conversion:
- Default: `--codelist-mode valueset` (`answerValueSet`).
- When explicit options are needed: `--codelist-mode option` (`answerOption`).

4. Choice UI control:
- Configurable via `--choice-item-control drop-down|radio-button`.
- Current user operation frequently uses: `option + radio-button`.

## Define-XML Mapping Rules
- `ValueListRef` / `WhereClauseDef` are converted to conditional groups.
- Condition logic is exported via SDC extension:
  - `http://hl7.org/fhir/uv/sdc/StructureDefinition/sdc-questionnaire-enableWhenExpression`
- Logical handling:
  - Within a `WhereClauseDef`: AND
  - Multiple `WhereClauseRef`: OR
  - `IN` and `NOTIN` are expanded explicitly in expression logic.

## Safety Rules (Important)
- `Questionnaire.item.linkId` must be unique within each Questionnaire.
- If source OIDs repeat, generator must auto-resolve duplicates (suffixing) and keep expression references consistent.

## Expected Output Behavior
- One Questionnaire JSON per form (or per pseudo form).
- Preserve choice semantics (`answerValueSet` or `answerOption`) according to CLI mode.
- Attach `questionnaire-itemControl` extension for choice items.

## Repository Hygiene
- Keep generated outputs in `out/` for local work only.
- `out/` is ignored via `.gitignore` and should not be committed.

## Recommended Validation Before Release
1. Unit tests
```bash
pytest -q
```

2. Smoke conversion
```bash
odm2jaspehr examples/sample_odm.xml --output-dir out --canonical-base http://example.org/fhir --codelist-mode option --choice-item-control radio-button
```

3. Check duplicate `linkId` count is zero
- Use the README sanity-check snippet.

## Notes for Future Work
- Fallback support for runtimes that do not evaluate `enableWhenExpression`.
- Additional mapping for `MeasurementUnit` and advanced constraints.
