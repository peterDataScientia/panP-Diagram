"""panP-Diagram — original user-provided TikZ design, dynamically populated."""
import copy
import io
import json
import re
import subprocess
import tempfile
from pathlib import Path

import streamlit as st

ORIGINAL = Path(__file__).with_name("FIGURE_original.tex").read_text(encoding="utf-8")
DEMO = {
    "databases": [{"name": "Scopus", "n": 142}, {"name": "PubMed", "n": 38}],
    "other_sources": [],
    "duplicates": 2,
    "automation_removed": 0,
    "other_removed": 0,
    "screen_excluded": 155,
    "not_retrieved": 0,
    "exclusion_reasons": [{"name": "Did not satisfy inclusion criteria", "n": 7}],
    "study_count": 16,
    "heading": "Identification of studies via databases and registers",
    "included_label": "Studies included in qualitative synthesis",
}

def latex_escape(value):
    substitutions = {
        "\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$",
        "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}",
        "~": r"\textasciitilde{}", "^": r"\textasciicircum{}",
    }
    return "".join(substitutions.get(c, c) for c in str(value))

def lines(*items):
    return r"\\".join(items)

def tex_count(number):
    return r"($n=" + str(number) + "$)"

def count(rows):
    return sum(int(r["n"]) for r in rows)

def calculate(p):
    identified = count(p["databases"]) + count(p["other_sources"])
    removed = p["duplicates"] + p["automation_removed"] + p["other_removed"]
    screened = identified - removed
    sought = screened - p["screen_excluded"]
    assessed = sought - p["not_retrieved"]
    reports = assessed - count(p["exclusion_reasons"])
    return dict(identified=identified, removed=removed, screened=screened,
                sought=sought, assessed=assessed, reports=reports,
                studies=p["study_count"])

def validate(p, c):
    issues = []
    if not p["databases"] and not p["other_sources"]:
        issues.append("At least one identification source is required.")
    for k in ("databases", "other_sources", "exclusion_reasons"):
        for r in p[k]:
            if not r["name"].strip():
                issues.append(f"Blank name in {k}.")
            if int(r["n"]) < 0:
                issues.append(f"Negative count in {k}.")
    for k in ("screened", "sought", "assessed", "reports"):
        if c[k] < 0:
            issues.append(f"Negative {k}: check the previous stage.")
    if c["studies"] > c["reports"]:
        issues.append("Included studies cannot exceed included reports.")
    return issues

def populate_node(source, name, content):
    # Replace only the contents of one original \node, not its style or coordinates.
    pattern = r"(\\node\[[^\n]*\]\s*\(" + re.escape(name) + r"\)\s*at\s*\([^\n]*?\)\s*\{)(.*?)(\};)"
    result, n = re.subn(pattern, lambda m: m.group(1) + content + m.group(3),
                         source, count=1, flags=re.S)
    if n != 1:
        raise ValueError(f"Original template node was not found: {name}")
    return result

def build_tex(p, c):
    s = ORIGINAL
    identification = [r"\textbf{Records identified from:}"]
    identification += [latex_escape(r["name"]) + " " + tex_count(r["n"]) for r in p["databases"]]
    if p["other_sources"]:
        identification += [r"\textbf{Other sources:}"]
        identification += [latex_escape(r["name"]) + " " + tex_count(r["n"]) for r in p["other_sources"]]
    removals = [r"\textbf{Records removed before", r"screening:}"]
    removals.append("Duplicate records removed " + tex_count(p["duplicates"]))
    if p["automation_removed"]:
        removals.append("Marked ineligible by automation " + tex_count(p["automation_removed"]))
    if p["other_removed"]:
        removals.append("Removed for other reasons " + tex_count(p["other_removed"]))
    exclusions = [r"\textbf{Reports excluded:}"]
    exclusions += [latex_escape(r["name"]) + " " + tex_count(r["n"]) for r in p["exclusion_reasons"]]
    replacements = {
        "title": r"\textbf{" + latex_escape(p["heading"]) + "}",
        "identified": lines(*identification),
        "removed": lines(*removals),
        "screened": lines(r"\textbf{Records screened}", tex_count(c["screened"])),
        "excluded": lines(r"\textbf{Records excluded}", tex_count(p["screen_excluded"])),
        "sought": lines(r"\textbf{Reports sought for retrieval}", tex_count(c["sought"])),
        "notretrieved": lines(r"\textbf{Reports not retrieved}", tex_count(p["not_retrieved"])),
        "assessed": lines(r"\textbf{Reports assessed for eligibility}", tex_count(c["assessed"])),
        "reportsexcluded": lines(*exclusions),
        "included": lines(r"\textbf{" + latex_escape(p["included_label"]) + "}", tex_count(c["studies"])),
    }
    for name, content in replacements.items():
        s = populate_node(s, name, content)
    # Original TikZ styles, colours, frame and arrow anchors remain unchanged.
    return s

@st.cache_data(show_spinner=False, max_entries=8)
def render(tex):
    with tempfile.TemporaryDirectory() as td:
        folder = Path(td)
        (folder / "figure.tex").write_text(tex, encoding="utf-8")
        compiled = subprocess.run(
            ["pdflatex", "-halt-on-error", "-interaction=nonstopmode",
             "-output-directory", td, str(folder / "figure.tex")],
            capture_output=True, text=True, timeout=90, cwd=td,
        )
        if compiled.returncode:
            raise RuntimeError("LaTeX compilation failed:\n" + compiled.stdout[-4500:])
        pdf = (folder / "figure.pdf").read_bytes()
        png_result = subprocess.run(
            ["pdftoppm", "-f", "1", "-singlefile", "-r", "160", "-png",
             str(folder / "figure.pdf"), str(folder / "preview")],
            capture_output=True, text=True, timeout=90,
        )
        if png_result.returncode:
            raise RuntimeError("Preview conversion failed: " + png_result.stderr[-1500:])
        return pdf, (folder / "preview.png").read_bytes()

DATABASE_OPTIONS = [
    "Scopus", "PubMed / MEDLINE", "Web of Science Core Collection",
    "Embase", "Cochrane CENTRAL", "Cochrane Library", "CINAHL",
    "PsycINFO", "ERIC", "IEEE Xplore", "ACM Digital Library",
    "ScienceDirect", "SpringerLink", "Wiley Online Library",
    "Google Scholar", "Dimensions", "OpenAlex", "LILACS",
    "African Journals Online (AJOL)", "African Index Medicus",
    "ProQuest", "EBSCOhost", "ClinicalTrials.gov", "WHO ICTRP",
    "Custom database..."
]
SOURCE_OPTIONS = [
    "Citation searching (backward)", "Citation searching (forward)",
    "Reference lists", "Websites / organisations", "Google Search",
    "Handsearching journals", "Conference proceedings",
    "Expert contacts", "Author contacts", "Preprint servers",
    "Institutional repositories", "Theses and dissertations",
    "Trial registers", "Grey literature", "Other methods",
    "Custom source..."
]

def editor(p, key, title):
    st.markdown("#### " + title)
    for i, item in enumerate(p[key][:]):
        a, b, d = st.columns([5, 2, 1])
        item["name"] = a.text_input("Name", item["name"], key=f"{key}_name_{i}",
                                    label_visibility="collapsed")
        item["n"] = int(b.number_input("Count", value=int(item["n"]), min_value=0,
                                          key=f"{key}_count_{i}", label_visibility="collapsed"))
        if d.button("✕", key=f"{key}_delete_{i}", help="Remove this entry"):
            p[key].pop(i)
            for prefix in (f"{key}_name_", f"{key}_count_"):
                for widget_key in [k for k in list(st.session_state) if k.startswith(prefix)]:
                    del st.session_state[widget_key]
            st.rerun()
    if key in ("databases", "other_sources"):
        options = DATABASE_OPTIONS if key == "databases" else SOURCE_OPTIONS
        chosen = st.selectbox("Choose " + ("database" if key == "databases" else "source"),
                              options, key=f"{key}_choice")
        custom = None
        if chosen.startswith("Custom"):
            custom = st.text_input("Custom name", key=f"{key}_custom").strip()
        a, b = st.columns([2, 1])
        new_n = int(a.number_input("Records (n)", value=0, min_value=0,
                                    key=f"{key}_new_count"))
        if b.button("＋ Add Database" if key == "databases" else "＋ Add Source",
                    key=f"{key}_add", use_container_width=True):
            name = custom if chosen.startswith("Custom") else chosen
            if not name:
                st.warning("Enter a name first.")
            elif any(x["name"].casefold() == name.casefold() for x in p[key]):
                st.warning("Already in the list. Edit its count above.")
            else:
                p[key].append({"name": name, "n": new_n})
                st.rerun()
    else:
        if st.button("＋ Add exclusion reason", key=f"{key}_add"):
            p[key].append({"name": "New exclusion reason", "n": 0})
            st.rerun()

st.set_page_config(page_title="panP-Diagram", layout="wide", page_icon="🔬")
if "project" not in st.session_state:
    st.session_state.project = copy.deepcopy(DEMO)
p = st.session_state.project
st.title("panP-Diagram")
st.caption("Original FIGURE (1).tex design · Full editable demo · Automatic arithmetic · PDF / PNG / TikZ exports")

with st.sidebar:
    st.subheader("Project")
    if st.button("Restore original full demo", use_container_width=True):
        for k in list(st.session_state):
            del st.session_state[k]
        st.rerun()
    upload = st.file_uploader("Load project JSON", type=["json"])
    if upload is not None:
        try:
            new = json.load(upload)
            if not isinstance(new, dict):
                raise ValueError("Project must be a JSON object")
            updated = copy.deepcopy(DEMO)
            updated.update(new)
            if st.button("Apply project"):
                for k in list(st.session_state):
                    del st.session_state[k]
                st.session_state.project = updated
                st.rerun()
        except (ValueError, TypeError) as e:
            st.error(str(e))
    st.download_button("Save project JSON",
                       json.dumps(p, indent=2).encode(), "panP_Project.json", "application/json")

controls, preview = st.columns([1, 1.5], gap="large")
with controls:
    p["heading"] = st.text_input("Title", p["heading"])
    with st.expander("Identification", expanded=True):
        editor(p, "databases", "Databases")
        editor(p, "other_sources", "Other sources")
    with st.expander("Records removed before screening", expanded=True):
        for key, label in (("duplicates", "Duplicates"),
                           ("automation_removed", "Marked ineligible by automation"),
                           ("other_removed", "Removed for other reasons")):
            p[key] = int(st.number_input(label, min_value=0, value=int(p[key])))
    with st.expander("Screening and retrieval", expanded=True):
        p["screen_excluded"] = int(st.number_input(
            "Records excluded", min_value=0, value=int(p["screen_excluded"])))
        p["not_retrieved"] = int(st.number_input(
            "Reports not retrieved", min_value=0, value=int(p["not_retrieved"])))
    with st.expander("Eligibility exclusions", expanded=True):
        editor(p, "exclusion_reasons", "Exclusion reasons")
    with st.expander("Included", expanded=True):
        p["study_count"] = int(st.number_input(
            "Distinct included studies", min_value=0, value=int(p["study_count"])))
        p["included_label"] = st.text_input("Included label", p["included_label"])

with preview:
    st.subheader("Original LaTeX figure · Live preview")
    counts = calculate(p)
    for col, (name, value) in zip(st.columns(4), (
            ("Identified", counts["identified"]), ("Screened", counts["screened"]),
            ("Reports", counts["reports"]), ("Studies", counts["studies"]))):
        col.metric(name, value)
    issues = validate(p, counts)
    for issue in issues:
        st.error(issue)
    if not issues:
        st.success("Arithmetic validation passed")
        if counts["reports"] != counts["studies"]:
            st.info("Reports and distinct studies differ; verify study grouping.")
        source = build_tex(p, counts)
        try:
            pdf, png = render(source)
            st.image(png, use_container_width=True)
            a, b = st.columns(2)
            a.download_button("Download PDF", pdf, "panP_Diagram.pdf", "application/pdf",
                              use_container_width=True)
            b.download_button("Download PNG", png, "panP_Diagram.png", "image/png",
                              use_container_width=True)
        except (RuntimeError, subprocess.TimeoutExpired, FileNotFoundError) as e:
            st.error(f"LaTeX renderer unavailable: {e}")
        st.download_button("Download original-style TikZ (.tex)", source.encode("utf-8"),
                           "panP_Diagram.tex", "text/plain", use_container_width=True)
    st.caption("Illustrative demonstration counts, not published study findings.")
