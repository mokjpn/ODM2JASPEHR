from pathlib import Path

from odm2jaspehr import build_questionnaires, parse_odm


def test_sample_conversion():
    sample = Path("examples/sample_odm.xml")
    odm = parse_odm(str(sample))

    resources = build_questionnaires(odm, canonical_base="http://example.org/fhir")

    assert len(resources) == 1
    questionnaire = resources[0]

    assert questionnaire["resourceType"] == "Questionnaire"
    assert questionnaire["meta"]["profile"]
    assert questionnaire["item"][0]["type"] == "group"

    height_item = questionnaire["item"][0]["item"][0]
    assert height_item["type"] == "decimal"
    assert height_item["required"] is True
    assert height_item["extension"][0]["url"] == "http://hl7.org/fhir/StructureDefinition/minValue"
    assert height_item["extension"][0]["valueDecimal"] == 30.0
    assert height_item["extension"][1]["url"] == "http://hl7.org/fhir/StructureDefinition/maxValue"
    assert height_item["extension"][1]["valueDecimal"] == 250.0

    smoking_item = questionnaire["item"][0]["item"][2]
    assert smoking_item["type"] == "choice"
    assert smoking_item["answerValueSet"] == "urn:odm:codelist:CL.YESNO"
    assert smoking_item["extension"][0]["url"] == "http://hl7.org/fhir/StructureDefinition/questionnaire-itemControl"


def test_codelist_option_mode():
    sample = Path("examples/sample_odm.xml")
    odm = parse_odm(str(sample))

    resources = build_questionnaires(
        odm,
        canonical_base="http://example.org/fhir",
        codelist_mode="option",
    )

    smoking_item = resources[0]["item"][0]["item"][2]
    assert "answerOption" in smoking_item
    assert smoking_item["answerOption"][0]["valueCoding"]["code"] == "Y"
    assert smoking_item["extension"][0]["url"] == "http://hl7.org/fhir/StructureDefinition/questionnaire-itemControl"
    assert smoking_item["extension"][0]["valueCodeableConcept"]["coding"][0]["code"] == "drop-down"


def test_choice_item_control_radio_button():
    sample = Path("examples/sample_odm.xml")
    odm = parse_odm(str(sample))

    resources = build_questionnaires(
        odm,
        canonical_base="http://example.org/fhir",
        codelist_mode="option",
        choice_item_control="radio-button",
    )

    smoking_item = resources[0]["item"][0]["item"][2]
    coding = smoking_item["extension"][0]["valueCodeableConcept"]["coding"][0]
    assert coding["system"] == "http://hl7.org/fhir/questionnaire-item-control"
    assert coding["code"] == "radio-button"


def test_url_encoding_and_prompt_alias_fallback(tmp_path):
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<ODM xmlns="http://www.cdisc.org/ns/odm/v1.3" ODMVersion="1.3.2" FileType="Snapshot">
  <Study OID="S1">
    <MetaDataVersion OID="MDV1">
      <FormDef OID="FORM A/B" Name="Form with space and slash">
        <ItemGroupRef ItemGroupOID="IG1" Mandatory="Yes" OrderNumber="1"/>
      </FormDef>
      <ItemGroupDef OID="IG1" Name="Group 1">
        <ItemRef ItemOID="IT1" Mandatory="No" OrderNumber="1"/>
      </ItemGroupDef>
      <ItemDef OID="IT1" Name="FallbackPrompt" DataType="string" Length="12">
        <Alias Name="Prompt Text" Context="prompt"/>
      </ItemDef>
    </MetaDataVersion>
  </Study>
</ODM>
"""
    path = tmp_path / "test.xml"
    path.write_text(xml, encoding="utf-8")

    odm = parse_odm(str(path))
    resources = build_questionnaires(odm, canonical_base="http://example.org/fhir")

    q = resources[0]
    assert q["url"] == "http://example.org/fhir/Questionnaire/FORM%20A%2FB"
    item = q["item"][0]["item"][0]
    assert item["text"] == "Prompt Text"
    assert item["maxLength"] == 12


def test_value_list_ref_generates_conditional_groups(tmp_path):
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<ODM xmlns="http://www.cdisc.org/ns/odm/v1.3" xmlns:def="http://www.cdisc.org/ns/def/v2.1" ODMVersion="1.3.2" FileType="Snapshot">
  <Study OID="S2">
    <MetaDataVersion OID="MDV2">
      <FormDef OID="FORM.VL" Name="VL Form">
        <ItemGroupRef ItemGroupOID="IG.VL" Mandatory="Yes" OrderNumber="1"/>
      </FormDef>
      <ItemGroupDef OID="IG.VL" Name="Group VL">
        <ItemRef ItemOID="IT.PARAM" Mandatory="Yes" OrderNumber="1"/>
        <ItemRef ItemOID="IT.RESULT" Mandatory="No" OrderNumber="2"/>
      </ItemGroupDef>
      <ItemDef OID="IT.PARAM" Name="PARAM" DataType="text">
        <Question><TranslatedText>Parameter</TranslatedText></Question>
        <CodeListRef CodeListOID="CL.PARAM"/>
      </ItemDef>
      <ItemDef OID="IT.RESULT" Name="RESULT" DataType="integer">
        <def:ValueListRef ValueListOID="VL.RESULT"/>
      </ItemDef>
      <ItemDef OID="IT.RESULT.A" Name="RESULT A" DataType="integer">
        <Question><TranslatedText>Result for A</TranslatedText></Question>
      </ItemDef>
      <ItemDef OID="IT.RESULT.B" Name="RESULT B" DataType="integer">
        <Question><TranslatedText>Result for B</TranslatedText></Question>
      </ItemDef>
      <def:ValueListDef OID="VL.RESULT">
        <ItemRef ItemOID="IT.RESULT.A" Mandatory="No" OrderNumber="1">
          <def:WhereClauseRef WhereClauseOID="WC.PARAM.A"/>
        </ItemRef>
        <ItemRef ItemOID="IT.RESULT.B" Mandatory="No" OrderNumber="2">
          <def:WhereClauseRef WhereClauseOID="WC.PARAM.B"/>
        </ItemRef>
      </def:ValueListDef>
      <def:WhereClauseDef OID="WC.PARAM.A">
        <RangeCheck Comparator="EQ" SoftHard="Soft" def:ItemOID="IT.PARAM">
          <CheckValue>A</CheckValue>
        </RangeCheck>
      </def:WhereClauseDef>
      <def:WhereClauseDef OID="WC.PARAM.B">
        <RangeCheck Comparator="EQ" SoftHard="Soft" def:ItemOID="IT.PARAM">
          <CheckValue>B</CheckValue>
        </RangeCheck>
      </def:WhereClauseDef>
      <CodeList OID="CL.PARAM" Name="PARAM CL" DataType="text">
        <CodeListItem CodedValue="A"><Decode><TranslatedText>A</TranslatedText></Decode></CodeListItem>
        <CodeListItem CodedValue="B"><Decode><TranslatedText>B</TranslatedText></Decode></CodeListItem>
      </CodeList>
    </MetaDataVersion>
  </Study>
</ODM>
"""
    path = tmp_path / "value_list.xml"
    path.write_text(xml, encoding="utf-8")
    odm = parse_odm(str(path))
    q = build_questionnaires(odm, canonical_base="http://example.org/fhir")[0]

    group_items = q["item"][0]["item"]
    assert group_items[1]["type"] == "group"
    assert group_items[1]["extension"][0]["url"] == "http://hl7.org/fhir/uv/sdc/StructureDefinition/sdc-questionnaire-enableWhenExpression"
    expr = group_items[1]["extension"][0]["valueExpression"]["expression"]
    assert "linkId='IT.PARAM'" in expr
    assert " = 'A'" in expr
    assert group_items[1]["item"][0]["text"] == "Result for A"


def test_value_list_ref_expression_or_and_in(tmp_path):
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<ODM xmlns="http://www.cdisc.org/ns/odm/v1.3" xmlns:def="http://www.cdisc.org/ns/def/v2.1" ODMVersion="1.3.2" FileType="Snapshot">
  <Study OID="S3">
    <MetaDataVersion OID="MDV3">
      <FormDef OID="FORM.VL2" Name="VL Form 2">
        <ItemGroupRef ItemGroupOID="IG.VL2" Mandatory="Yes" OrderNumber="1"/>
      </FormDef>
      <ItemGroupDef OID="IG.VL2" Name="Group VL2">
        <ItemRef ItemOID="IT.TEST" Mandatory="Yes" OrderNumber="1"/>
        <ItemRef ItemOID="IT.SPEC" Mandatory="Yes" OrderNumber="2"/>
        <ItemRef ItemOID="IT.RESULT" Mandatory="No" OrderNumber="3"/>
      </ItemGroupDef>
      <ItemDef OID="IT.TEST" Name="TEST" DataType="text"/>
      <ItemDef OID="IT.SPEC" Name="SPEC" DataType="text"/>
      <ItemDef OID="IT.RESULT" Name="RESULT" DataType="integer">
        <def:ValueListRef ValueListOID="VL.RESULT"/>
      </ItemDef>
      <ItemDef OID="IT.RESULT.COND" Name="RESULT COND" DataType="integer"/>
      <def:ValueListDef OID="VL.RESULT">
        <ItemRef ItemOID="IT.RESULT.COND" Mandatory="No" OrderNumber="1">
          <def:WhereClauseRef WhereClauseOID="WC.1"/>
          <def:WhereClauseRef WhereClauseOID="WC.2"/>
        </ItemRef>
      </def:ValueListDef>
      <def:WhereClauseDef OID="WC.1">
        <RangeCheck Comparator="IN" SoftHard="Soft" def:ItemOID="IT.TEST">
          <CheckValue>A</CheckValue>
          <CheckValue>B</CheckValue>
        </RangeCheck>
        <RangeCheck Comparator="EQ" SoftHard="Soft" def:ItemOID="IT.SPEC">
          <CheckValue>BLOOD</CheckValue>
        </RangeCheck>
      </def:WhereClauseDef>
      <def:WhereClauseDef OID="WC.2">
        <RangeCheck Comparator="EQ" SoftHard="Soft" def:ItemOID="IT.TEST">
          <CheckValue>C</CheckValue>
        </RangeCheck>
      </def:WhereClauseDef>
    </MetaDataVersion>
  </Study>
</ODM>
"""
    path = tmp_path / "value_list_or_in.xml"
    path.write_text(xml, encoding="utf-8")
    odm = parse_odm(str(path))
    q = build_questionnaires(odm, canonical_base="http://example.org/fhir")[0]

    conditional_group = q["item"][0]["item"][2]
    expr = conditional_group["extension"][0]["valueExpression"]["expression"]
    assert " or " in expr
    assert " and " in expr
    assert "linkId='IT.TEST'" in expr
    assert "linkId='IT.SPEC'" in expr
    assert " = 'A'" in expr and " = 'B'" in expr and " = 'C'" in expr


def test_pseudo_form_mode_from_item_groups(tmp_path):
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<ODM xmlns="http://www.cdisc.org/ns/odm/v1.3" ODMVersion="1.3.2" FileType="Snapshot">
  <Study OID="S4">
    <MetaDataVersion OID="MDV4">
      <ItemGroupDef OID="IG.DM" Name="DM" Repeating="No">
        <ItemRef ItemOID="IT.DM.SEX" Mandatory="No" OrderNumber="1"/>
      </ItemGroupDef>
      <ItemDef OID="IT.DM.SEX" Name="SEX" DataType="text" Length="1">
        <Question><TranslatedText>Sex</TranslatedText></Question>
      </ItemDef>
    </MetaDataVersion>
  </Study>
</ODM>
"""
    path = tmp_path / "pseudo.xml"
    path.write_text(xml, encoding="utf-8")
    odm = parse_odm(str(path))

    resources = build_questionnaires(
        odm,
        canonical_base="http://example.org/fhir",
        pseudo_form_mode="itemgroup",
    )

    assert len(resources) == 1
    q = resources[0]
    assert q["identifier"][0]["value"] == "PFORM.IG.DM"
    assert q["item"][0]["linkId"] == "IG.DM"
    assert q["item"][0]["item"][0]["linkId"] == "IT.DM.SEX"
