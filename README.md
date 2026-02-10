# desjardins_statement_convert
Scripts to convert Desjardins Monthly Statement PDF to CSV.

## Credit Card Statement Converter.
To convert Desjardins credit card PDF monthly statement files to CSV format with similar formating to the Reconciliation format that is only available for the last three months.

After installing  requirements, run `python credit_statement_convert_pdf_to_csv.py {path to Desjardins Credit Card PDF Statement file.pdf} -o {Optional csv output path}`.

### Unit Tests
To test PDF to CSV conversion software against a known valid CSV from Desjardins.
Install virtual environment and pytest.
Add in "./test/ref/" directory at least one Desjardins Credit Card PDF statement and a matching period CSV s.
Get them from AccesD, from Manage Card -> Manage my Account -> Statements of account -> Reconciliation/Download Conciliation.
Run pytest and check results.

## Buy me a coffee ☕ (or a beer 🍺)
[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/fcol95)
