# Remaining Evidence Gaps — methodology.tex

Items marked `[NEEDS EVIDENCE]` in the LaTeX that must be filled before submission.

## 1. Table Flagging Statistics (§5 Validity and Limitations)

**Current placeholder text:**
> Of the tables in the audited subset, **[NEEDS EVIDENCE]** were flagged by structural consistency checks; the audit outcome for each flagged table is reported in the results.

**What to fill in:**
- Total number of tables in the audited subset
- Number of tables flagged by structural consistency checks
- How many were repaired vs excluded
- If none were excluded, state that explicitly

**Where to find this:**
- Check `prepare_tables.py` run logs or `prep_tables_full.log`
- Or re-run the pipeline and count flagged items

---

## 2. Judge Model Version Strings (§4.3 LLM Judge Adjudication)

**Current text uses display names:**
> Claude Sonnet 4.6, GPT 5.4 Thinking, and Grok Expert

**Consider adding:**
- Exact model version dates if available from chat UI session history
- Screenshots or session dates for reproducibility
