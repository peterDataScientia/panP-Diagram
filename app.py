"""panP-Diagram — original user-provided TikZ design, dynamically populated."""
import copy
import io
import json
import re
import subprocess
import tempfile
from pathlib import Path

import streamlit as st
from PIL import Image

LOGO_PATH = Path(__file__).parent / "assets" / "panp_logo.png"

ORIGINAL = Path(__file__).with_name("V2.tex").read_text(encoding="utf-8")
DEMO = {
    "databases": [{"name": "Scopus", "n": 142}, {"name": "PubMed", "n": 38}, {"name": "Web of Science", "n": 20}],
    "other_sources": [],
    "pre_screen_reasons": [
        {"name": "Duplicate records", "n": 12},
        {"name": "Marked ineligible by automation", "n": 3},
        {"name": "Other reasons", "n": 5},
    ],
    "screen_excluded": 150,
    "not_retrieved": 2,
    "exclusion_reasons": [{"name": "Ineligible study design", "n": 4}, {"name": "Ineligible outcomes", "n": 3}, {"name": "Insufficient relevant data", "n": 1}],
    "study_count": 20,
    "auto_studies": True,
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
    removed = count(p["pre_screen_reasons"])
    screened = identified - removed
    sought = screened - p["screen_excluded"]
    assessed = sought - p["not_retrieved"]
    reports = assessed - count(p["exclusion_reasons"])
    return dict(identified=identified, removed=removed, screened=screened,
                sought=sought, assessed=assessed, reports=reports,
                studies=reports if p.get("auto_studies", True) else p["study_count"])

def validate(p, c):
    issues = []
    if not p["databases"] and not p["other_sources"]:
        issues.append("At least one identification source is required.")
    for k in ("databases", "other_sources", "pre_screen_reasons", "exclusion_reasons"):
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
    removed = []
    if p["pre_screen_reasons"]:
        removed = [r"\textbf{Records removed before\\screening:}"]
        removed += [latex_escape(r["name"]) + " " + tex_count(r["n"])
                    for r in p["pre_screen_reasons"]]
        removed.append(r"\textbf{Total " + tex_count(c["removed"]) + "}")
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

    # Preserve V2's original styling. Each row is positioned relative to
    # the actual bottom of the previous row, regardless of content height.
    # All horizontal connections share the same vertical centre.
    def position(name, coordinate, top=False):
        nonlocal source
        pattern = (r"(\\node\[)([^\]]+)(\]\s*\(" + re.escape(name) +
                   r"\)\s*at\s*)\([^\n]*?\)")
        source, matched = re.subn(
            pattern,
            lambda m: m.group(1) + m.group(2) +
                      (",anchor=north" if top else "") +
                      m.group(3) + coordinate,
            source, count=1
        )
        if matched != 1:
            raise ValueError(f"Could not locate layout node: {name}")

    def after_node(name, addition):
        nonlocal source
        pattern = (r"(\\node\[[^\]]+\]\s*\(" + re.escape(name) +
                   r"\)\s*at\s*[^\n]*?\s*\{.*?\};)")
        source, matched = re.subn(
            pattern, lambda m: m.group(1) + "\n" + addition,
            source, count=1, flags=re.S
        )
        if matched != 1:
            raise ValueError(f"Could not locate row anchor: {name}")

    # Remove labels before repositioning, then draw them beside the actual rows.
    for name in ("phaseID", "phaseScreen", "phaseInclude"):
        pat = (r"\\node\[phase\]\s*\(" + name +
               r"\)\s*at\s*\([^\n]*?\)\s*\{.*?\};")
        source, matched = re.subn(pat, "", source, count=1, flags=re.S)
        if matched != 1:
            raise ValueError(f"Could not find phase label: {name}")

    position("records", "(1.15,-0.80)", top=True)
    position("preremoved", r"($(records.center)+(6.95cm,0)$)")
    after_node("preremoved",
               r"\node[inner sep=0pt,outer sep=0pt,fit=(records)(preremoved)] (rowident) {};")

    position("screen", r"($(records.center |- rowident.south)+(0,-0.90cm)$)", top=True)
    position("screenout", r"($(screen.center)+(6.95cm,0)$)")
    after_node("screenout",
               r"\node[inner sep=0pt,outer sep=0pt,fit=(screen)(screenout)] (rowscreen) {};")

    position("sought", r"($(screen.center |- rowscreen.south)+(0,-0.85cm)$)", top=True)
    position("unavailable", r"($(sought.center)+(6.95cm,0)$)")
    after_node("unavailable",
               r"\node[inner sep=0pt,outer sep=0pt,fit=(sought)(unavailable)] (rowretrieve) {};")

    # Place the taller eligibility box first. Align the smaller assessed box
    # to its vertical centre so the arrow stays horizontal.
    assessment_pat = r"\\node\[basic\]\s*\(assessed\)\s*at\s*[^\n]*?\s*\{.*?\};"
    reason_pat = r"\\node\[exclusion\]\s*\(reasons\)\s*at\s*[^\n]*?\s*\{.*?\};"
    assessed_node = re.search(assessment_pat, source, flags=re.S)
    reasons_node = re.search(reason_pat, source, flags=re.S)
    if not assessed_node or not reasons_node:
        raise ValueError("Could not arrange eligibility row")
    source = (source[:assessed_node.start()] +
              source[reasons_node.start():reasons_node.end()] + "\n" +
              source[assessed_node.start():assessed_node.end()] +
              source[reasons_node.end():])
    position("reasons", r"($(unavailable.center |- rowretrieve.south)+(0,-0.95cm)$)", top=True)
    position("assessed", r"($(reasons.center)+(-6.95cm,0)$)")
    after_node("assessed",
               r"\node[inner sep=0pt,outer sep=0pt,fit=(assessed)(reasons)] (roweligible) {};")

    position("final", r"($(assessed.center |- roweligible.south)+(0,-1.05cm)$)", top=True)
    labels = (
        r"\node[phase] (phaseID) at ($(records.west)+(-2.95cm,0)$) {Identification};" + "\n" +
        r"\node[phase] (phaseScreen) at ($(screen.west)+(-2.95cm,0)$) {Screening};" + "\n" +
        r"\node[phase] (phaseInclude) at ($(final.west)+(-2.95cm,0)$) {Included};" + "\n"
    )
    source = source.replace("% Draw after nodes", labels + "% Draw after nodes", 1)
    if not p["pre_screen_reasons"]:
        # An empty pre-screening exclusion section should not appear in the figure.
        # Retain the invisible node as a layout anchor for the row geometry.
        source = source.replace(
            r"\node[exclusion] (preremoved)",
            r"\node[exclusion,draw=none,fill=none,text opacity=0] (preremoved)", 1
        )
        source = source.replace(
            r"\draw[link] (records.east) -- (preremoved.west);", "", 1
        )
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
        if st.button("＋ Add reason", key=f"{key}_add"):
            p[key].append({"name": "New reason", "n": 0})
            st.rerun()

st.set_page_config(
    page_title="panP-Diagram",
    layout="wide",
    page_icon=Image.open(LOGO_PATH).convert("RGBA").crop((0, 0, 116, 107)),
)
if "project" not in st.session_state:
    st.session_state.project = copy.deepcopy(DEMO)
p = st.session_state.project
# Keep JSON projects from previous releases compatible with the new editor.
if "pre_screen_reasons" not in p:
    p["pre_screen_reasons"] = [
        {"name": "Duplicate records", "n": int(p.get("duplicates", 0))},
        {"name": "Marked ineligible by automation",
         "n": int(p.get("automation_removed", 0))},
        {"name": "Other reasons", "n": int(p.get("other_removed", 0))},
    ]
st.image(str(LOGO_PATH), width=360)
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
            if "pre_screen_reasons" not in new and any(
                key in new for key in ("duplicates", "automation_removed", "other_removed")
            ):
                updated["pre_screen_reasons"] = [
                    {"name": "Duplicate records", "n": int(new.get("duplicates", 0))},
                    {"name": "Marked ineligible by automation",
                     "n": int(new.get("automation_removed", 0))},
                    {"name": "Other reasons", "n": int(new.get("other_removed", 0))},
                ]
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
        editor(p, "pre_screen_reasons", "Removal reasons")
    with st.expander("Screening and retrieval", expanded=True):
        p["screen_excluded"] = int(st.number_input(
            "Records excluded", min_value=0, value=int(p["screen_excluded"])))
        p["not_retrieved"] = int(st.number_input(
            "Reports not retrieved", min_value=0, value=int(p["not_retrieved"])))
    with st.expander("Eligibility exclusions", expanded=True):
        editor(p, "exclusion_reasons", "Exclusion reasons")
    with st.expander("Included", expanded=True):
        p["auto_studies"] = st.checkbox(
            "Automatically calculate included studies",
            value=bool(p.get("auto_studies", True)),
            help="Uses included reports as the study count. Turn off if multiple reports refer to the same study.",
        )
        if not p["auto_studies"]:
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
