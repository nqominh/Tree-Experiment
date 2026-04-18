"""Integration tests for profile-based intent routing with fixed execution model."""

from __future__ import annotations

import argparse
import csv
import json
import sys
import uuid
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import run_experiment_csv as base
import run_experiment_minimax as minimax


def _make_workdir() -> Path:
    root = PROJECT_ROOT / "tmp_router_tests"
    root.mkdir(parents=True, exist_ok=True)
    workdir = root / f"case_{uuid.uuid4().hex[:10]}"
    workdir.mkdir(parents=True, exist_ok=False)
    return workdir


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _read_rows(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _route_fixture_setup(tmp_path: Path, monkeypatch) -> dict[str, Path]:
    html_dir = tmp_path / "RealHiTBench" / "html"
    table_inputs = tmp_path / "table_inputs"
    prompt_dir = tmp_path / "run_doc" / "prompts"

    c1_prompt = prompt_dir / "C1_Vanilla.md"
    c3_prompt = prompt_dir / "C3_SchemaOnly.md"

    _write(c1_prompt, "C1_MARKER\n{html_section}\nQ:{question}\n")
    _write(
        c3_prompt,
        "C3_MARKER\n{col_structure_section}\n{row_structure_section}\n{html_section}\nQ:{question}\n",
    )

    _write(
        table_inputs / "t1.txt",
        "[COLUMN STRUCTURE]\nA\n[ROW STRUCTURE]\nR1\n[TABLE HTML]\n<table><tr><td>1</td></tr></table>\n",
    )
    _write(
        table_inputs / "t2.txt",
        "[COLUMN STRUCTURE]\nB\n[ROW STRUCTURE]\nR2\n[TABLE HTML]\n<table><tr><td>2</td></tr></table>\n",
    )
    _write(html_dir / "t1.html", "<html><body><table><tr><td>1</td></tr></table></body></html>")
    _write(html_dir / "t2.html", "<html><body><table><tr><td>2</td></tr></table></body></html>")

    monkeypatch.setattr(base, "PROFILE_C1_HTML_DIR", html_dir)
    monkeypatch.setattr(base, "PROFILE_C3_TABLE_DIR", table_inputs)
    monkeypatch.setattr(base, "PROFILE_C1_PROMPT_FILE", c1_prompt)
    monkeypatch.setattr(base, "PROFILE_C3_PROMPT_FILE", c3_prompt)
    monkeypatch.setattr(base, "TABLE_INPUTS", table_inputs)

    return {
        "html_dir": html_dir,
        "table_inputs": table_inputs,
        "c1_prompt": c1_prompt,
        "c3_prompt": c3_prompt,
    }


def test_active_routing_switches_profile_and_keeps_model_fixed(monkeypatch) -> None:
    tmp_path = _make_workdir()
    paths = _route_fixture_setup(tmp_path, monkeypatch)

    questions_path = tmp_path / "questions.jsonl"
    output_csv = tmp_path / "routed.csv"
    _write_jsonl(
        questions_path,
        [
            {"id": 1, "query": "How many entries are present?", "label": "ok", "table_id": "t1"},
            {"id": 2, "query": "Rank the entries by value.", "label": "ok", "table_id": "t2"},
        ],
    )

    calls: list[dict] = []

    def fake_call(prompt: str, api_key: str, model: str, temperature: float = 1.0, max_tokens: int = 32000) -> str:
        calls.append({"prompt": prompt, "model": model})
        return "[Final Answer]: ok"

    monkeypatch.setattr(base, "call_gemini", fake_call)

    base.run(
        questions_path=questions_path,
        output_csv=output_csv,
        api_key="dummy",
        model="FixedModel",
        limit=0,
        delay=0.0,
        prompt_template="BASELINE_MARKER\n{html_section}\n{question}\n",
        prompt_template_path=tmp_path / "baseline.md",
        enable_intent_routing=True,
        shadow_mode=False,
        c1_model="deprecated-c1",
        c3_model="deprecated-c3",
    )

    assert [c["model"] for c in calls] == ["FixedModel", "FixedModel"]
    rows = _read_rows(output_csv)
    assert len(rows) == 2

    by_id = {row["id"]: row for row in rows}
    c1_row = by_id["1"]
    c3_row = by_id["2"]

    assert c1_row["route_model"] == "C1"
    assert c1_row["profile_selected"] == "C1"
    assert c1_row["profile_executed"] == "C1"
    assert c1_row["profile_fallback_applied"] == "0"
    assert c1_row["input_mode_used"] == "html"
    assert c1_row["prompt_template_used"] == str(paths["c1_prompt"])
    assert "C1_MARKER" in c1_row["full_prompt"]
    assert c1_row["executed_model"] == "FixedModel"

    assert c3_row["route_model"] == "C3"
    assert c3_row["profile_selected"] == "C3"
    assert c3_row["profile_executed"] == "C3"
    assert c3_row["profile_fallback_applied"] == "0"
    assert c3_row["input_mode_used"] == "txt"
    assert c3_row["prompt_template_used"] == str(paths["c3_prompt"])
    assert "C3_MARKER" in c3_row["full_prompt"]
    assert c3_row["executed_model"] == "FixedModel"


def test_shadow_mode_logs_route_but_keeps_baseline_profile(monkeypatch) -> None:
    tmp_path = _make_workdir()
    _route_fixture_setup(tmp_path, monkeypatch)

    baseline_html_dir = tmp_path / "baseline_html"
    _write(baseline_html_dir / "t1.html", "<html><body><table><tr><td>A</td></tr></table></body></html>")
    _write(baseline_html_dir / "t2.html", "<html><body><table><tr><td>B</td></tr></table></body></html>")

    questions_path = tmp_path / "questions_shadow.jsonl"
    output_csv = tmp_path / "shadow.csv"
    _write_jsonl(
        questions_path,
        [
            {"id": 11, "query": "How many entries are present?", "label": "ok", "table_id": "t1"},
            {"id": 12, "query": "Rank the entries by value.", "label": "ok", "table_id": "t2"},
        ],
    )

    calls: list[dict] = []

    def fake_call(prompt: str, api_key: str, model: str, temperature: float = 1.0, max_tokens: int = 32000) -> str:
        calls.append({"prompt": prompt, "model": model})
        return "[Final Answer]: ok"

    monkeypatch.setattr(base, "call_gemini", fake_call)

    base.run(
        questions_path=questions_path,
        output_csv=output_csv,
        api_key="dummy",
        model="FixedModel",
        limit=0,
        delay=0.0,
        prompt_template="BASELINE_MARKER\n{html_section}\nQ:{question}\n",
        prompt_template_path=tmp_path / "baseline_prompt.md",
        html_dir=str(baseline_html_dir),
        enable_intent_routing=True,
        shadow_mode=True,
    )

    rows = _read_rows(output_csv)
    assert len(rows) == 2
    assert [c["model"] for c in calls] == ["FixedModel", "FixedModel"]

    for row in rows:
        assert row["profile_executed"] == "BASELINE"
        assert row["input_mode_used"] == "html"
        assert row["prompt_template_used"] == str(tmp_path / "baseline_prompt.md")
        assert "BASELINE_MARKER" in row["full_prompt"]
        assert row["shadow_mode"] == "1"

    by_id = {row["id"]: row for row in rows}
    assert by_id["11"]["route_model"] == "C1"
    assert by_id["12"]["route_model"] == "C3"


def test_missing_selected_profile_input_falls_back_to_other_profile(monkeypatch) -> None:
    tmp_path = _make_workdir()
    paths = _route_fixture_setup(tmp_path, monkeypatch)

    # Remove C1 HTML for this table; keep C3 TXT so fallback is possible.
    table_id = "fallback_case"
    _write(
        paths["table_inputs"] / f"{table_id}.txt",
        "[COLUMN STRUCTURE]\nC\n[ROW STRUCTURE]\nR\n[TABLE HTML]\n<table><tr><td>3</td></tr></table>\n",
    )

    questions_path = tmp_path / "questions_fallback.jsonl"
    output_csv = tmp_path / "fallback.csv"
    _write_jsonl(
        questions_path,
        [{"id": 21, "query": "How many rows exist?", "label": "ok", "table_id": table_id}],
    )

    monkeypatch.setattr(base, "call_gemini", lambda *args, **kwargs: "[Final Answer]: ok")

    base.run(
        questions_path=questions_path,
        output_csv=output_csv,
        api_key="dummy",
        model="FixedModel",
        limit=0,
        delay=0.0,
        prompt_template="BASELINE\n{html_section}\n{question}\n",
        prompt_template_path=tmp_path / "baseline_prompt.md",
        enable_intent_routing=True,
        shadow_mode=False,
    )

    rows = _read_rows(output_csv)
    assert len(rows) == 1
    row = rows[0]
    assert row["route_model"] == "C1"
    assert row["profile_selected"] == "C1"
    assert row["profile_executed"] == "C3"
    assert row["profile_fallback_applied"] == "1"
    assert "Selected profile input missing" in row["profile_fallback_reason"]
    assert "C3_MARKER" in row["full_prompt"]


def test_missing_both_profiles_skips_row(monkeypatch) -> None:
    tmp_path = _make_workdir()
    _route_fixture_setup(tmp_path, monkeypatch)

    questions_path = tmp_path / "questions_skip.jsonl"
    output_csv = tmp_path / "skip.csv"
    _write_jsonl(
        questions_path,
        [{"id": 31, "query": "How many rows exist?", "label": "ok", "table_id": "missing_everywhere"}],
    )

    def fail_if_called(*args, **kwargs):
        raise AssertionError("Model call should not happen when both profiles are missing")

    monkeypatch.setattr(base, "call_gemini", fail_if_called)

    base.run(
        questions_path=questions_path,
        output_csv=output_csv,
        api_key="dummy",
        model="FixedModel",
        limit=0,
        delay=0.0,
        prompt_template="BASELINE\n{html_section}\n{question}\n",
        prompt_template_path=tmp_path / "baseline_prompt.md",
        enable_intent_routing=True,
        shadow_mode=False,
    )

    rows = _read_rows(output_csv)
    assert rows == []


def test_minimax_adapter_delegates_profile_routing_to_base_runner(monkeypatch) -> None:
    tmp_path = _make_workdir()
    prompt_file = tmp_path / "baseline_prompt.md"
    _write(prompt_file, "BASELINE\n{html_section}\n{question}\n")

    args = argparse.Namespace(
        questions=str(tmp_path / "questions.jsonl"),
        output=str(tmp_path / "out.csv"),
        model="MiniMax-M2.7",
        limit=0,
        qid="",
        delay=0.0,
        api_key=None,
        api_key_env="ANTHROPIC_API_KEY",
        base_url="https://api.minimax.io/anthropic",
        temperature=1.0,
        max_tokens=32000,
        prompt_file=str(prompt_file),
        csv_dir="",
        json_dir="",
        html_dir="",
        demo=False,
        enable_intent_routing=True,
        mh_conf_threshold=0.55,
        route_policy_version="router_v1_2026_03_29",
        shadow_mode=False,
        c1_model="legacy-c1",
        c3_model="legacy-c3",
    )

    monkeypatch.setattr(minimax, "parse_args", lambda: args)
    monkeypatch.setattr(minimax.base, "load_local_env_files", lambda extra_files=(): None)
    monkeypatch.setattr(minimax.base, "load_prompt_template", lambda path: "BASE_PROMPT")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "dummy-key")

    captured_run: dict = {}

    def fake_run(**kwargs):
        captured_run.update(kwargs)

    monkeypatch.setattr(minimax.base, "run", fake_run)

    seen_models: list[str] = []

    def fake_call_minimax(prompt: str, api_key: str, model: str, base_url: str, temperature: float, max_tokens: int) -> str:
        seen_models.append(model)
        return "[Final Answer]: ok"

    monkeypatch.setattr(minimax, "call_minimax", fake_call_minimax)

    minimax.main()

    assert captured_run["enable_intent_routing"] is True
    assert captured_run["shadow_mode"] is False
    assert captured_run["model"] == "MiniMax-M2.7"
    assert captured_run["prompt_template_path"] == prompt_file

    _ = minimax.base.call_gemini("PROMPT", "dummy-key", "MODEL_UNDER_TEST")
    assert seen_models == ["MODEL_UNDER_TEST"]
