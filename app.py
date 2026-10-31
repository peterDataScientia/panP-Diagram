"""panP-Diagram — original user-provided TikZ design, dynamically populated."""
import copy
import io
import json
import re
import subprocess
import tempfile
from pathlib import Path

import streamlit as st

ORIGINAL = Path(__file__).with_name("V2.tex").read_text(encoding="utf-8")
DEMO = {
    "databases": [{"name": "Scopus", "n": 142}, {"name": "PubMed", "n": 38}, {"name": "Web of Science", "n": 20}],
    "other_sources": [],
    "duplicates": 12,
    "automation_removed": 3,
    "other_removed": 5,
    "screen_excluded": 150,
    "not_retrieved": 2,
    "exclusion_reasons": [{"name": "Ineligible study design", "n": 4}, {"name": "Ineligible outcomes", "n": 3}, {"name": "Insufficient relevant data", "n": 1}],
    "study_count": 20,
    "heading": "Identification of studies via databases and registers",
    "included_label": "Studies included in review",
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
    # Modify only user-facing text inside an existing V2 node.
    pattern = (r"(\\node\[[^\]]+\]\s*\(" + re.escape(name)
               + r"\)\s*at\s*\([^\n]*?\)\s*\{)(.*?)(\};)")
    result, n = re.subn(pattern, lambda m: m.group(1) + content + m.group(3),
                         source, count=1, flags=re.S)
    if n != 1:
        raise ValueError(f"V2 template node not found: {name}")
    return result

def build_tex(p, c):
    source = ORIGINAL
    entries = [r"\textbf{Records identified from:}"]
    entries += [latex_escape(r["name"]) + " " + tex_count(r["n"]) for r in p["databases"]]
    if p["other_sources"]:
        entries.append(r"\textbf{Other sources:}")
        entries += [latex_escape(r["name"]) + " " + tex_count(r["n"]) for r in p["other_sources"]]
    entries += [r"\textbf{Total " + tex_count(c["identified"]) + "}"]
    removed = [r"\textbf{Records removed before\\screening:}",
               "Duplicate records " + tex_count(p["duplicates"]),
               "Automation exclusions " + tex_count(p["automation_removed"]),
               "Other reasons " + tex_count(p["other_removed"]),
               r"\textbf{Total " + tex_count(c["removed"]) + "}"]
    reasons = [r"\textbf{Reports excluded:\\(with reasons):}"]
    reasons += [latex_escape(r["name"]) + " " + tex_count(r["n"]) for r in p["exclusion_reasons"]]
    reasons += [r"\textbf{Total " + tex_count(count(p["exclusion_reasons"])) + "}"]
    changes = {
        "heading": latex_escape(p["heading"]),
        "records": lines(*entries),
        "preremoved": lines(*removed),
        "screen": lines(r"\textbf{Records screened}", tex_count(c["screened"])),
        "screenout": lines(r"\textbf{Records excluded}", tex_count(p["screen_excluded"])),
        "sought": lines(r"\textbf{Reports sought for retrieval}", tex_count(c["sought"])),
        "unavailable": lines(r"\textbf{Reports not retrieved}", tex_count(p["not_retrieved"])),
        "assessed": lines(r"\textbf{Reports assessed for eligibility}", tex_count(c["assessed"])),
        "reasons": lines(*reasons),
        "final": lines(r"\textbf{" + latex_escape(p["included_label"]) + "}",
                       tex_count(c["studies"])),
    }
    for name, value in changes.items():
        source = populate_node(source, name, value)

    # Retain V2's exact palette, box styles, frame and anchored arrow definitions.
    # Make the source self-consistent: V2's example-only configuration macros
    # are replaced with a generated comment, as actual values live in the nodes.
    first = source.index("% ==================== CONFIGURATION")
    last = source.index("% ================= END CONFIGURATION") 
    last = source.index("\n", last) + 1
    theme_start = source.index("% Theme", first, last)
    theme_definitions = source[theme_start:last]
    source = (source[:first] +
              "% GENERATED FIGURE DATA — modify values using panP-Diagram.\n" +
              "% Original V2 theme and color definitions retained below.\n" +
              theme_definitions + source[last:])

    # Preserve the exact V2 arrangement and original coordinates for the
    # default dataset. Expand the overall figure vertically only as entries
    # increase. No changes to box styles, colour intensity, or arrow styles.
    additional_sources = max(0, len(entries) - 5)
    additional_reasons = max(0, len(reasons) - 5)
    source_shift = 0.58 * additional_sources
    reason_shift = 0.58 * additional_reasons
    y_positions = {
        "phaseScreen": -5.10 - source_shift,
        "screen": -5.10 - source_shift,
        "screenout": -5.10 - source_shift,
        "sought": -7.05 - source_shift,
        "unavailable": -7.05 - source_shift,
        "assessed": -9.80 - source_shift,
        "reasons": -9.80 - source_shift,
        "phaseInclude": -13.0 - source_shift - reason_shift,
        "final": -13.0 - source_shift - reason_shift,
    }
    for name, y in y_positions.items():
        pat = (r"(\\node\[[^\]]+\]\s*\(" + re.escape(name) +
               r"\)\s*at\s*\(\s*([^,]+),\s*)(-?\d+(?:\.\d+)?)(\s*\))")
        source, found = re.subn(
            pat, lambda m: m.group(1) + f"{y:.2f}" + m.group(4),
            source, count=1)
        if found != 1:
            raise ValueError(f"V2 layout position missing: {name}")
    return source

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
st.caption("Create and export PRISMA flow diagrams")

with st.sidebar:
    st.subheader("Project")
    if st.button("Reset example data", use_container_width=True):
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
    st.subheader("Figure preview")
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
        st.download_button("Download LaTeX (.tex)", source.encode("utf-8"),
                           "panP_Diagram.tex", "text/plain", use_container_width=True)
    st.caption("Example counts are shown. Replace them with your own data.")
