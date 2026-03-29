# Workspace Copilot Instructions

Use when: working on source code changes in this repository while minimizing context/token usage.

## Prioritize These Folders
- experiment/
- table2tree/
- utils/
- tests/
- evaluation/
- score/ (scripts only, avoid large data files)
- prompts/

## Avoid Pulling Context From
- document/
- note/
- scripts/utility/
- backup_csv_archive/
- old_experiments/
- RealHiTBench/
- table_inputs/
- trees_json/
- Large result artifacts (*.xlsx, *.csv, *.tsv) unless the user explicitly asks for them.

## Search Behavior
- Prefer targeted file lookups and symbol-level reads over broad workspace scans.
- If broad search is needed, start with source-code folders listed above.
- Only read artifact folders when directly requested by the user.
