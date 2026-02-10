from pathlib import Path
import re
import unicodedata
import argparse
from pathlib import Path

import pdfplumber
import pandas as pd


def remove_accents(input_str: str) -> str:
    if not isinstance(input_str, str):
        return input_str
    nfkd_form = unicodedata.normalize("NFKD", input_str)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)])


def process_statement(
    pdf_path: str | Path, output_csv: str | None = None
) -> pd.DataFrame:
    pdf_path = Path(pdf_path).resolve()
    if not pdf_path.is_file() or pdf_path.suffix.lower() != ".pdf":
        raise AttributeError(
            f"Error: File '{pdf_path}' does not exist or is not a PDF."
        )

    all_data = []
    statement_month = None
    statement_year = None
    due_month = None
    due_year = None

    with pdfplumber.open(pdf_path) as pdf:
        # 1. Extract Due Date Year/Month from Page 1
        tables = []
        for page in pdf.pages:
            table = page.extract_tables()
            if table is not None:
                tables.extend(table)

        if len(tables) == 0:
            raise ValueError(
                "No tables found in PDF. Ensure the PDF is correctly formatted."
            )

        for table in tables:
            text = remove_accents(str(table)).lower()
            if "date du releve" in text:
                # Extract "Jour 13 Mois 02 Année 2026" pattern
                match = re.search(
                    r"jour\s+(\d{2})\s+mois\s+(\d{2})\s+annee\s+(\d{4})",
                    text,
                )
                if match:
                    statement_day = int(match.group(1))
                    statement_month = int(match.group(2))
                    statement_year = int(match.group(3))
                    break
            if "date d'echeance" in text:
                # Extract "Jour 13 Mois 02 Année 2026" pattern
                match = re.search(
                    r"jour\s+(\d{2})\s+mois\s+(\d{2})\s+annee\s+(\d{4})",
                    text,
                )
                if match:
                    due_day = int(match.group(1))
                    due_month = int(match.group(2))
                    due_year = int(match.group(3))
                    break
            if "doit nous parvenir au plus tard" in text:
                # Extract "Jour 13 Mois 02 Année 2026" pattern
                match = re.search(
                    r"le\s+(\d{1,2})\s+([a-zéû]+)\s+(\d{4})",
                    text,
                )
                if match:
                    # Map French month names to numbers
                    month_map = {
                        "janvier": 1,
                        "février": 2,
                        "mars": 3,
                        "avril": 4,
                        "mai": 5,
                        "juin": 6,
                        "juillet": 7,
                        "août": 8,
                        "septembre": 9,
                        "octobre": 10,
                        "novembre": 11,
                        "décembre": 12,
                    }
                    due_day = int(match.group(1))
                    due_month = month_map.get(match.group(2), 0)
                    due_year = int(match.group(3))
                    break

        if not due_year or not due_month:
            if statement_year and statement_month:
                due_month = statement_month + 1 if statement_month < 12 else 1
                due_year = (
                    statement_year if statement_month < 12 else statement_year + 1
                )
            else:
                raise ValueError(
                    "Due date not found in PDF. Ensure 'Date d'échéance' is present."
                )

        for table in tables:
            header_text = " ".join([str(cell) for cell in table[0] if cell])

            # Identify Account vs Card
            account_match = re.search(r"compte.+(\d{4}$)", header_text, re.IGNORECASE)
            card_match = re.search(
                r"Carte\s+:\s+.+(\d{4})$", header_text, re.IGNORECASE
            )
            current_id = None
            if card_match is not None:
                current_id = f"VISA **** **** **** {card_match.group(1)}"
            elif account_match is not None:
                current_id = f"VISA **** **** **** {account_match.group(1)}"

            if not current_id:
                continue

            data_row = None
            for i, row in enumerate(table):
                if row[0] and "Date de transaction" in str(row[0]):
                    if i + 1 < len(table):
                        data_row = table[i + 1]
                    break

            if not data_row:
                continue

            # Extraction: Index 1 = Inscription, 2 = Desc, 4 = Amount
            dates_raw = str(data_row[1]).split("\n")
            desc_raw = str(data_row[2]).split("\n")
            amounts_raw = str(data_row[4]).split("\n")

            # Fix Misalignment: Merge Dollar/TX lines into previous description
            cleaned_desc = []
            for line in desc_raw:
                line = line.strip()
                if ("DOLLAR " in line or "TX:" in line) and cleaned_desc:
                    cleaned_desc[-1] = f"*{cleaned_desc[-1]}"
                else:
                    cleaned_desc.append(line)

            seq_id = 1
            for i in range(min(len(dates_raw), len(amounts_raw))):
                date_val = dates_raw[i].strip()
                if not date_val:
                    continue

                trans_day, trans_month = map(int, date_val.split())

                # Year Rollover: If Month is Dec (12) and Due is Feb (02), Year is 2025
                # If Month is Jan (01) and Due is Feb (02), Year is 2026
                trans_year = due_year
                if trans_month > due_month:
                    trans_year = due_year - 1
                formatted_date = f"{trans_year}/{trans_month:02d}/{trans_day:02d}"
                desc = remove_accents(cleaned_desc[i] if i < len(cleaned_desc) else "")
                amt_str = amounts_raw[i].strip()

                is_credit = "CR" in amt_str
                amount_val = float(
                    amt_str.replace("CR", "").replace(",", ".").replace(" ", "").strip()
                )

                all_data.append(
                    [
                        current_id,
                        "",
                        "",
                        formatted_date,
                        f"{seq_id:03d}",
                        desc,
                        "",
                        "",
                        "",
                        "",
                        "",
                        "" if is_credit else f"{amount_val:.2f}",
                        f"{amount_val:.2f}" if is_credit else "",
                        "",
                    ]
                )
                seq_id += 1

    df_gen = pd.DataFrame(all_data)
    if output_csv is None:
        output_csv = pdf_path.with_suffix(".csv")
    df_gen.to_csv(output_csv, index=False, header=False, quoting=1)
    return df_gen


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Desjardins PDF to CSV Converter")
    parser.add_argument("pdf", help="Input PDF file")
    parser.add_argument("-o", "--output", default=None, help="Output CSV")
    args = parser.parse_args()
    process_statement(args.pdf, args.output)
