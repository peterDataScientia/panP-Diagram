# panP-Diagram

Streamlit PRISMA flow designer powered by the **user-supplied V2 LaTeX figure**.

## Figure fidelity
The authoritative design is [V2.tex](V2.tex), preserved verbatim. Its original `tcolorbox` outer border, colours, TikZ node coordinates, fonts, box styles and arrow paths are retained. Streamlit updates node text and numbers only, then compiles the resulting TikZ source with actual `pdflatex`. Live preview is rasterized from the compiled PDF.

## Features
- Editable full V2 demonstration with Scopus (142), PubMed (38), Web of Science (20) and V2 screening counts
- Select databases and other sources from built-in lists, then click **Add Database** or **Add Source**; enter a custom name if needed
- Edit/remove entries and exclusion reasons, with editable record counts
- Automatic count calculations, basic arithmetic validation and studies/reports distinction
- PDF, PNG, editable LaTeX (.tex) downloads
- Save/load project as JSON
- No SVG download; no SVG diagram generator

## Deploy on Streamlit Community Cloud
- Repository: `peterDataScientia/panP-Diagram`
- Branch: `main`
- Main file: `app.py`
- `requirements.txt` installs Streamlit
- `packages.txt` installs native TeX Live and Poppler PDF rendering utilities

Native LaTeX installation can extend deployment build duration. If a server restricts installation of TeX packages, PDF/PNG preview requires a compatible LaTeX-capable host. A standalone .tex download is generated even if a runtime compilation fails.

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```
Install `pdflatex` (TeX Live with TikZ/tcolorbox) and `pdftoppm` (Poppler) on PATH.

Demo data are illustrative and not real review findings.
