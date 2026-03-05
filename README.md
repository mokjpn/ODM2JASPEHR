# ODM2JASPEHR

日本語 / English

## 1. 概要 / Overview

### 日本語
CDISC ODM / Define-XML のメタデータ（`FormDef`, `ItemGroupDef`, `ItemDef`, `CodeListRef`, `ValueListRef`, `WhereClauseDef` など）を、
JASPEHR IG v1.0 向けの FHIR `Questionnaire` JSON に変換するCLIツールです。

### English
A CLI tool that converts CDISC ODM / Define-XML metadata (`FormDef`, `ItemGroupDef`, `ItemDef`, `CodeListRef`, `ValueListRef`, `WhereClauseDef`, etc.)
into FHIR `Questionnaire` JSON compatible with JASPEHR IG v1.0.

## 2. 動作環境 / Requirements

### 日本語
- Python 3.10 以上

### English
- Python 3.10+

## 3. セットアップ / Setup

### 日本語
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

### English
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

## 4. 使い方 / Usage

### 基本コマンド / Basic command
```bash
odm2jaspehr <input.xml> \
  --output-dir out \
  --canonical-base http://example.org/fhir
```

### 主要オプション / Key options
- `--codelist-mode valueset|option`
  - `valueset`: `answerValueSet` を出力 / output `answerValueSet`
  - `option`: `answerOption` を出力 / output `answerOption`
- `--choice-item-control drop-down|radio-button`
  - choice項目の表示制御 / UI control code for choice items
- `--pseudo-form-mode off|itemgroup`
  - `FormDef` がない場合に `ItemGroupDef` を擬似フォーム化 / synthesize forms from `ItemGroupDef` when `FormDef` is absent
- `--value-set-base <canonical-or-urn>`
  - `answerValueSet` のベースURI / base URI for `answerValueSet`
- `--status draft|active|retired|unknown`
- `--version <string>`

### 例 / Examples
```bash
# answerOption + radio-button
odm2jaspehr examples/sample_odm.xml \
  --output-dir out \
  --canonical-base http://example.org/fhir \
  --codelist-mode option \
  --choice-item-control radio-button

# FormDefがないDefine-XMLを擬似フォーム化
odm2jaspehr define.xml \
  --output-dir out \
  --canonical-base http://example.org/fhir \
  --pseudo-form-mode itemgroup
```

## 5. 出力内容 / Output behavior

### 日本語
- `FormDef` ごとに `Questionnaire` を1ファイル出力
- `linkId` は1つの `Questionnaire` 内で一意になるよう自動調整
- `ValueListRef` 条件は `enableWhenExpression`（SDC拡張）へ変換

### English
- Generates one `Questionnaire` file per `FormDef`
- Ensures `linkId` uniqueness within each `Questionnaire`
- Converts `ValueListRef` conditions into SDC `enableWhenExpression`

## 6. 開発用テスト / Dev test

### 日本語
```bash
pytest -q
```

### English
```bash
pytest -q
```

## 7. ライセンス / License

MIT License  
See [LICENSE](./LICENSE).

Copyright (c) 2026 Masafumi Okada

## 8. 貢献表記 / Attribution

### 日本語
本リポジトリの実装には、Masafumi Okada による設計・開発に加えて、OpenAI Codex（GPT-5）によるAI支援コード生成・リファクタリングが含まれます。

### English
This repository includes implementation work designed and developed by Masafumi Okada, with AI-assisted code generation and refactoring support from OpenAI Codex (GPT-5).
