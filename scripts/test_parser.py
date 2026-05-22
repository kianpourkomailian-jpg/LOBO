"""
test_parser.py
=============
Stage 3 test. Exercises the parser fully OFFLINE (no Google Drive needed) by
building a realistic LinkedIn export in memory:

  * a Connections.csv with LinkedIn's typical 2-line preamble above the header
  * the same data wrapped inside a ZIP

It then parses both and confirms the output matches LEAD_SCHEMA.

Run:
    python -m scripts.test_parser
"""

import io
import zipfile

from app.config.constants import LEAD_SCHEMA
from app.ingestion import linkedin_parser

# A LinkedIn-style CSV: 2 preamble lines, blank line, then the real header.
SAMPLE_CSV = (
    "Notes:\n"
    '"When exporting your connection data, you may notice..."\n'
    "\n"
    "First Name,Last Name,URL,Email Address,Company,Position,Connected On\n"
    "Jane,Doe,https://linkedin.com/in/janedoe,jane@acme.com,Acme Mfg,"
    "Maintenance Manager,01 Jan 2024\n"
    "John,Smith,https://linkedin.com/in/johnsmith,,Globex Industrial,"
    "Operations Director,15 Feb 2024\n"
)


def _check(label: str, df) -> None:
    assert list(df.columns) == LEAD_SCHEMA, f"{label}: columns != schema"
    print(f"[OK] {label}: {len(df)} rows, schema matches")
    print(df[["full_name", "company", "role", "email"]].to_string(index=False))
    print("-" * 50)


def main() -> None:
    print("LOBO AI Leads — Stage 3 parser test")
    print("=" * 50)

    # 1) Plain CSV with preamble.
    csv_buf = io.BytesIO(SAMPLE_CSV.encode("utf-8"))
    _check("CSV", linkedin_parser.parse("Connections.csv", csv_buf))

    # 2) Same data inside a ZIP.
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as z:
        z.writestr("Connections.csv", SAMPLE_CSV)
    zip_buf.seek(0)
    _check("ZIP", linkedin_parser.parse("export.zip", zip_buf))

    print("SUCCESS: parser produces schema-shaped leads from CSV and ZIP.")


if __name__ == "__main__":
    main()
