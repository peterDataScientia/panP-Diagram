# panP-Diagram

**An interactive application for creating, editing, and exporting PRISMA-style study selection flow diagrams.**

panP-Diagram provides a structured interface for documenting the identification, screening, retrieval, eligibility assessment, and inclusion stages of literature reviews. Users can manage search sources and exclusion reasons, review calculated totals, and export figures for reports, manuscripts, or further editing.

## Features

- **Search source management:** Select databases and other information sources from predefined lists, or add custom entries.
- **Editable selection records:** Add, update, and remove source counts, pre-screening removal categories, and eligibility exclusion reasons. If all pre-screening removal categories are removed, their box and connector are omitted from the figure.
- **Automatic calculations:** Calculate totals across identification, screening, retrieval, and eligibility stages.
- **Data validation:** Flag inconsistent counts and distinguish included reports from distinct included studies.
- **Figure preview:** Display the updated diagram as selection data change.
- **Export options:** Download publication-oriented PDF, high-resolution PNG, or editable LaTeX (`.tex`) files.
- **Project portability:** Save and restore project inputs in JSON format.
- **Worked example:** Start with a fully populated example and replace its values with your own.

## Getting started

### Requirements

- Python 3.10 or newer
- A LaTeX distribution providing `pdflatex`, TikZ/PGF, `tcolorbox`, and the `standalone` class
- Poppler's `pdftoppm` utility for PNG rendering

### Local installation

Clone the repository and install the Python dependencies:

```bash
git clone https://github.com/peterDataScientia/panP-Diagram.git
cd panP-Diagram
python -m pip install -r requirements.txt
```

Ensure `pdflatex` and `pdftoppm` are available on your system's `PATH`, then launch the application:

```bash
streamlit run app.py
```

Open the local URL displayed by Streamlit in your browser.

## Using the application

1. **Identify sources.** Choose a database or another information source, enter the number of records identified, and select **Add Database** or **Add Source**. Additional sources can be entered manually.
2. **Record screening decisions.** Enter the numbers of duplicate records, records removed before screening, screening exclusions, and reports not retrieved.
3. **Document eligibility.** Add exclusion reasons and their associated report counts.
4. **Review results.** Check the calculated totals and any validation messages. Enter the number of distinct included studies where it differs from the number of included reports.
5. **Export or save.** Download the diagram as PDF, PNG, or LaTeX, or save a JSON project for subsequent editing.

## Outputs

| Format | Intended use |
| --- | --- |
| PDF | Vector figure for documents and manuscripts |
| PNG | Raster figure for presentations and general use |
| LaTeX (`.tex`) | Editable figure source for LaTeX workflows |
| JSON | Reusable project data and settings |

PDF and PNG rendering uses a LaTeX toolchain. A compatible LaTeX installation is therefore necessary on the host system.

## Streamlit Community Cloud deployment

To deploy the application, connect this repository to [Streamlit Community Cloud](https://share.streamlit.io/) and configure:

| Setting | Value |
| --- | --- |
| Repository | `peterDataScientia/panP-Diagram` |
| Branch | `main` |
| Main file | `app.py` |

Python dependencies are listed in `requirements.txt`, and Linux system dependencies in `packages.txt`. Hosting environments must support the required LaTeX and Poppler packages.

## Reporting considerations

panP-Diagram assists with figure preparation; it does not independently verify literature searches, deduplication procedures, eligibility decisions, or compliance with every PRISMA reporting requirement. Users should confirm that counts, study/report distinctions, source categories, and labels accurately reflect their review methods.

The default records are **illustrative examples**, not findings from a published review.

For reporting guidance, consult the [PRISMA 2020 website](https://www.prisma-statement.org/).

## License

This project is distributed under the [MIT License](LICENSE).
