# panP-Diagram

An open-source Streamlit PRISMA flow diagram designer with a complete editable demonstration.

## Features
- Add/edit/remove databases, registers and other identification sources
- Dynamic exclusion reasons
- Automatic screening, retrieval and eligibility calculations
- Arithmetic checks for impossible negative counts and included reports/studies
- Live vector diagram with arrows anchored at box borders
- Original navy (#174A7E), teal (#007C83), orange (#B85C00) and green (#287A3D) theme
- PDF, SVG, PNG and standalone LaTeX/TikZ exports
- Save/load editable JSON projects

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy

Connect this public repository to Streamlit Community Cloud. Select the `main` branch and `app.py` as the entry point. There are no paid APIs or secrets.

## Important

The initial counts are **illustrative** and are not actual systematic review results. Several included reports can correspond to one distinct included study. Check source categorization and selection logic against the PRISMA reporting guidance applicable to your study.

PDF rendering uses CairoSVG and may need Cairo system libraries depending on deployment. TikZ is standalone and can be compiled with `pdflatex`.
