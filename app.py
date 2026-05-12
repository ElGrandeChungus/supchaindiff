import io
import os
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from config import load_config
from ingestion import prepare_sheets
from diff import align_columns, compute_diff, group_by_ben
from llm import score_tool_severity, generate_executive_summary, build_tool_summaries
from output import write_output_file

load_dotenv()

st.set_page_config(page_title="Supply-Chain Diff", layout="wide")
st.title("Supply-Chain Diff Report Generator")


def _extract_date_code(sheet_name: str) -> str:
    """Extract mmdd code from sheet name like rawdata_0312 → 0312."""
    parts = sheet_name.rsplit("_", 1)
    return parts[-1] if len(parts) == 2 else sheet_name


def _get_non_key_cols(df_a: pd.DataFrame, df_b: pd.DataFrame, config) -> list:
    keys = set(config.composite_key_columns)
    seen = {}
    for c in list(df_a.columns) + list(df_b.columns):
        if c not in keys:
            seen[c] = None
    return list(seen)


# --- Screen: Upload ---
uploaded_file = st.file_uploader("Upload supply-chain .xlsx file", type=["xlsx"])

if not uploaded_file:
    st.info("Upload a .xlsx file to begin.")
    st.stop()

# Write uploaded file to temp location for openpyxl
tmp_dir = tempfile.mkdtemp()
input_path = os.path.join(tmp_dir, uploaded_file.name)
with open(input_path, "wb") as f:
    f.write(uploaded_file.getbuffer())

# Load sheet names
from openpyxl import load_workbook as _lw
_wb = _lw(input_path, read_only=True, data_only=True)
sheet_names = _wb.sheetnames
_wb.close()

if len(sheet_names) < 2:
    st.error("The uploaded file must contain at least 2 sheets.")
    st.stop()

# Load config
config = load_config()

# --- Screen: Configure ---
st.subheader("Configure")

col1, col2 = st.columns(2)
with col1:
    sheet_a = st.selectbox("Sheet A (baseline / earlier date)", sheet_names, index=0)
with col2:
    sheet_b = st.selectbox(
        "Sheet B (current / later date)",
        sheet_names,
        index=min(1, len(sheet_names) - 1),
    )

if sheet_a == sheet_b:
    st.warning("Sheet A and Sheet B must be different.")
    st.stop()

col3, col4 = st.columns(2)
with col3:
    ben_col = st.text_input("BEN column name", value=config.ben_column)
with col4:
    pn_col = st.text_input("Part Number column name", value=config.part_number_column)

config.ben_column = ben_col
config.part_number_column = pn_col

st.caption(f"Composite key (read-only): `{config.composite_key_columns}`")

config.llm_enabled = st.toggle("Enable LLM (severity flags + executive summary)", value=config.llm_enabled)

if not st.button("Run Diff", type="primary"):
    st.stop()

# --- Screen: Processing ---
st.subheader("Processing")
warnings: list = []

date_a = _extract_date_code(sheet_a)
date_b = _extract_date_code(sheet_b)

progress = st.progress(0, text="Ingestion & validation...")
try:
    df_a, df_b, skipped_bens, dup_warnings = prepare_sheets(
        input_path, sheet_a, sheet_b, config
    )
except ValueError as exc:
    st.error(str(exc))
    st.stop()

progress.progress(15, text="Column alignment...")
df_a, df_b, col_asymmetry = align_columns(df_a, df_b, config)

if col_asymmetry:
    warnings.append(f"Column asymmetry detected: {', '.join(col_asymmetry)}")
if skipped_bens:
    warnings.append(
        f"BEN groups skipped due to duplicate keys: {', '.join(skipped_bens)}"
    )

progress.progress(30, text="Computing diff...")
non_key_cols = _get_non_key_cols(df_a, df_b, config)
diff_result = compute_diff(df_a, df_b, config)

progress.progress(50, text="Grouping by tool...")
groups = group_by_ben(diff_result, config, tool_order=config.tool_order)

progress.progress(60, text="LLM severity flags...")
tool_summaries = build_tool_summaries(groups, date_a, date_b)
severities: dict = {}
llm_parse_failures: list = []

if config.llm_enabled:
    for ts in tool_summaries:
        with st.spinner(f"Scoring {ts['tool_id']}..."):
            result = score_tool_severity(ts, config)
            severities[ts["tool_id"]] = result
            if result["severity"] == "UNSCORED":
                llm_parse_failures.append(ts["tool_id"])
else:
    for ts in tool_summaries:
        severities[ts["tool_id"]] = {
            "tool_id": ts["tool_id"],
            "severity": "UNSCORED",
            "note": "LLM disabled",
        }

if llm_parse_failures:
    warnings.append(
        f"LLM scoring failed (UNSCORED) for: {', '.join(llm_parse_failures)}"
    )

progress.progress(80, text="LLM executive summary...")
with st.spinner("Generating executive summary..."):
    all_summaries_with_sev = [
        {
            **ts,
            "severity": severities.get(ts["tool_id"], {}).get("severity", "UNSCORED"),
        }
        for ts in tool_summaries
    ]
    exec_summary = generate_executive_summary(all_summaries_with_sev, config)

progress.progress(90, text="Writing output file...")
stem = Path(uploaded_file.name).stem
output_filename = f"{stem}_diff_{date_a}_{date_b}.xlsx"
output_path = os.path.join(tmp_dir, output_filename)

write_output_file(
    input_filepath=input_path,
    output_filepath=output_path,
    groups=groups,
    severities=severities,
    skipped_bens=skipped_bens,
    col_asymmetry=col_asymmetry,
    exec_summary=exec_summary,
    date_a=date_a,
    date_b=date_b,
    config=config,
    non_key_cols=non_key_cols,
)

progress.progress(100, text="Done.")

# --- Screen: Results ---
st.subheader("Results")

for w in warnings:
    st.warning(w)

# Summary table mirroring DIFF_INDEX
summary_rows = []
for ben, group in groups.items():
    sev = severities.get(ben, {})
    summary_rows.append(
        {
            "BEN": ben,
            "Added": len(group["added"]),
            "Removed": len(group["removed"]),
            "Changed": len(group["changed_b"]),
            "Unchanged": len(group["unchanged"]),
            "Status": "OK",
            "Severity": sev.get("severity", "UNSCORED"),
            "LLM Note": sev.get("note", ""),
        }
    )
for ben in skipped_bens:
    summary_rows.append(
        {
            "BEN": ben,
            "Added": 0,
            "Removed": 0,
            "Changed": 0,
            "Unchanged": 0,
            "Status": "SKIPPED — DUPLICATE KEYS",
            "Severity": "",
            "LLM Note": "",
        }
    )

if summary_rows:
    st.dataframe(pd.DataFrame(summary_rows), use_container_width=True)
else:
    st.info("No tools found in the diff.")

with open(output_path, "rb") as f:
    st.download_button(
        label=f"Download {output_filename}",
        data=f.read(),
        file_name=output_filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
