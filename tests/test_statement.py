import re
from pathlib import Path

import pytest
import pandas as pd

from credit_statement_convert_pdf_to_csv import process_statement, remove_accents


def get_test_pairs():
    """Scans tests/ref for all PDF files and pairs them with CSV files."""
    ref_dir = Path(__file__).resolve().parent / "ref"
    pdf_files = list(ref_dir.glob("*.pdf"))

    pairs = []
    missing_csv = []
    for pdf in pdf_files:
        csv_ref = pdf.with_suffix(".csv")
        if csv_ref.exists():
            pairs.append((pdf, csv_ref))
        else:
            missing_csv.append(pdf.name)

    if missing_csv:
        pytest.fail(f"Reference CSV missing for: {', '.join(missing_csv)}")
    return pairs


@pytest.mark.parametrize("pdf_path, csv_path", get_test_pairs())
def test_conversion_accuracy(pdf_path, csv_path):
    test_dir = Path(__file__).resolve().parent
    output_gen = test_dir / f"temp_{pdf_path.stem}.csv"

    # Generate data from PDF [cite: 1, 114]
    df_gen = process_statement(str(pdf_path), output_csv=str(output_gen))

    # Load reference CSV
    df_ref = pd.read_csv(csv_path, header=None, dtype=str).fillna("")

    # --- STRIP WHITESPACE BEFORE SORTING ---
    # We create a temporary sorting key by removing all spaces from Descriptions (Col 5)
    # This prevents sorting mismatches caused by extra spaces in the PDF
    for df in [df_gen, df_ref]:
        df["sort_desc"] = df[5].apply(lambda x: re.sub(r"\s+", "", str(x)))

    # Sort by Date (Col 3) and then the stripped Description
    df_gen = df_gen.sort_values(by=[3, "sort_desc"]).reset_index(drop=True)
    df_ref = df_ref.sort_values(by=[3, "sort_desc"]).reset_index(drop=True)

    # Validate row counts match [cite: 85]
    assert len(df_gen) == len(df_ref), f"Row count mismatch in {pdf_path.name}"

    # Content Deep Dive
    for idx in range(len(df_gen)):
        # Final comparison cleaning
        desc_gen = re.sub(r"\s+", "", str(df_gen.iloc[idx, 5]))
        desc_ref = remove_accents(re.sub(r"\s+", "", str(df_ref.iloc[idx, 5])))

        # Verify Critical Columns: ID, Date, Desc, Debit, Credit [cite: 4, 36, 114]
        assert df_gen.iloc[idx, 0] == df_ref.iloc[idx, 0], f"ID mismatch at row {idx}"
        assert df_gen.iloc[idx, 3] == df_ref.iloc[idx, 3], f"Date mismatch at row {idx}"
        assert desc_gen == desc_ref, f"Description mismatch at row {idx}"
        assert (
            df_gen.iloc[idx, 11] == df_ref.iloc[idx, 11]
        ), f"Debit mismatch at row {idx}"
        assert (
            df_gen.iloc[idx, 12] == df_ref.iloc[idx, 12]
        ), f"Credit mismatch at row {idx}"

    # Cleanup
    if output_gen.exists():
        output_gen.unlink()
