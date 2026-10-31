import copy, json, html, textwrap
import streamlit as st
import cairosvg

COLORS = {"navy":"#174A7E","teal":"#007C83","orange":"#B85C00","orange_light":"#FFF0D9","green":"#287A3D","green_light":"#E1F2E5","ink":"#202B36"}
DEMO={"databases":[{"name":"Scopus","n":142},{"name":"PubMed","n":38},{"name":"Web of Science","n":20}],
"other_sources":[],"duplicates":12,"automation_removed":3,"other_removed":5,
"screen_excluded":150,"not_retrieved":2,
"exclusion_reasons":[{"name":"Ineligible study design","n":4},{"name":"Ineligible outcomes","n":3},{"name":"Insufficient relevant data","n":1}],
"study_count":20,"title":"Identification of studies via databases and registers",
"included_label":"Studies included in review","theme":copy.deepcopy(COLORS)}

def total(rows):
    return sum(int(row["n"]) for row in rows)

def counts(p):
    identified=total(p["databases"])+total(p["other_sources"])
    removed=sum(p[k] for k in ("duplicates","automation_removed","other_removed"))
    screened=identified-removed
    sought=screened-p["screen_excluded"]
    assessed=sought-p["not_retrieved"]
    excluded=total(p["exclusion_reasons"])
    return dict(identified=identified,removed=removed,screened=screened,sought=sought,
                assessed=assessed,excluded=excluded,reports=assessed-excluded,studies=p["study_count"])

def errors(p,c):
    result=[]
    if not p["databases"] and not p["other_sources"]:result.append("Add an identification source.")
    for key in ("databases","other_sources","exclusion_reasons"):
        for r in p[key]:
            if not r["name"].strip():result.append(f"Unnamed entry in {key}.")
            if r["n"]<0:result.append(f"Negative count in {key}.")
    for k in ("screened","sought","assessed","reports"):
        if c[k]<0:result.append(f"{k.title()} count is negative.")
    if p["study_count"]>c["reports"]:result.append("Distinct included studies exceed included reports.")
    return result

def diagram(p,c):
    t=p["theme"]
    left,right,w=320,915,490
    def rows(items):
        out=[]
        for item in items:
            out.extend(textwrap.wrap(str(item),width=47,break_long_words=False) or [""])
        return out
    inputs=["Records identified from:"]+[f'{r["name"]} (n={r["n"]})' for r in p["databases"]]
    if p["other_sources"]:inputs+=["Other sources:"]+[f'{r["name"]} (n={r["n"]})' for r in p["other_sources"]]
    inputs += [f'Total (n={c["identified"]})']
    removed=["Records removed before screening:",f'Duplicates (n={p["duplicates"]})',f'Automation exclusions (n={p["automation_removed"]})',f'Other reasons (n={p["other_removed"]})',f'Total (n={c["removed"]})']
    reasons=["Reports excluded (with reasons):"]+[f'{r["name"]} (n={r["n"]})' for r in p["exclusion_reasons"]]+[f'Total (n={c["excluded"]})']
    specs=[
        ("identified",left,inputs,"basic"),("removed",right,removed,"excluded"),
        ("screened",left,[f'Records screened (n={c["screened"]})'],"basic"),
        ("screenout",right,[f'Records excluded (n={p["screen_excluded"]})'],"excluded"),
        ("sought",left,[f'Reports sought for retrieval (n={c["sought"]})'],"basic"),
        ("unavailable",right,[f'Reports not retrieved (n={p["not_retrieved"]})'],"excluded"),
        ("assessed",left,[f'Reports assessed for eligibility (n={c["assessed"]})'],"basic"),
        ("reasons",right,reasons,"excluded"),
        ("included",left,[f'{p["included_label"]} (n={c["studies"]})',f'Included reports (n={c["reports"]})'],"included")
    ]
    data={}
    for name,x,strings,kind in specs:
        ls=rows(strings);data[name]=dict(x=x,lines=ls,kind=kind,h=max(82,30+len(ls)*25))
    y=145
    for a,b in [("identified","removed"),("screened","screenout"),("sought","unavailable"),("assessed","reasons")]:
        data[a]["y"]=data[b]["y"]=y
        y+=max(data[a]["h"],data[b]["h"])+85
    data["included"]["y"]=y
    height=y+data["included"]["h"]+65
    s=[f'<svg xmlns="http://www.w3.org/2000/svg" width="1450" height="{height}" viewBox="0 0 1450 {height}">',
       f'<rect x="5" y="5" width="1440" height="{height-10}" rx="14" fill="white" stroke="{t["navy"]}" stroke-width="2.5"/>',
       f'<rect x="35" y="25" width="1375" height="78" rx="9" fill="{t["navy"]}"/>',
       f'<text x="722" y="73" text-anchor="middle" font-family="Arial" font-size="23" font-weight="bold" fill="white">{html.escape(p["title"])}</text>',
       f'<defs><marker id="tip" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="8" markerHeight="8" orient="auto"><path d="M0 0L10 5L0 10z" fill="{t["navy"]}"/></marker></defs>']
    for name,d in data.items():
        kind=d["kind"];border=t["orange"] if kind=="excluded" else t["green"] if kind=="included" else t["navy"]
        fill=t["orange_light"] if kind=="excluded" else t["green_light"] if kind=="included" else "#FFFFFF"
        s.append(f'<rect x="{d["x"]}" y="{d["y"]}" width="{w}" height="{d["h"]}" rx="10" fill="{fill}" stroke="{border}" stroke-width="2.3"/>')
        for i,line in enumerate(d["lines"]):
            s.append(f'<text x="{d["x"]+20}" y="{d["y"]+32+i*25}" fill="{t["ink"]}" font-family="Arial" font-size="17" font-weight="{"bold" if i==0 else "normal"}">{html.escape(line)}</text>')
    for label,ref in [("Identification","identified"),("Screening","screened"),("Included","included")]:
        d=data[ref];yy=d["y"]+min(8,max(0,(d["h"]-74)/2))
        s.append(f'<rect x="40" y="{yy}" width="212" height="74" rx="9" fill="{t["teal"]}"/>')
        s.append(f'<text x="146" y="{yy+45}" text-anchor="middle" font-family="Arial" font-size="18" font-weight="bold" fill="white">{label}</text>')
    def path(x1,y1,x2,y2):
        s.append(f'<path d="M{x1},{y1} L{x2},{y2}" fill="none" stroke="{t["navy"]}" stroke-width="3" marker-end="url(#tip)"/>')
    for a,b in [("identified","removed"),("screened","screenout"),("sought","unavailable"),("assessed","reasons")]:
        u,v=data[a],data[b];path(u["x"]+w,u["y"]+u["h"]/2,v["x"],v["y"]+v["h"]/2)
    for a,b in [("identified","screened"),("screened","sought"),("sought","assessed"),("assessed","included")]:
        u,v=data[a],data[b];path(u["x"]+w/2,u["y"]+u["h"],v["x"]+w/2,v["y"])
    return "".join(s)+"</svg>"

def tex_escape(s):
    translation={"\\":r"\textbackslash{}","&":r"\&","%":r"\%","$":r"\$","#":r"\#","_":r"\_","{":r"\{","}":r"\}","~":r"\textasciitilde{}"}
    return "".join(translation.get(ch,ch) for ch in str(s))

def tikz(p,c):
    t=p["theme"]
    ident=["Records identified from:"]+[f'{r["name"]} (n={r["n"]})' for r in p["databases"]]
    if p["other_sources"]:ident+=["Other sources:"]+[f'{r["name"]} (n={r["n"]})' for r in p["other_sources"]]
    ident += [f'Total (n={c["identified"]})']
    rem=["Records removed before screening:",f'Duplicates (n={p["duplicates"]})',f'Automation exclusions (n={p["automation_removed"]})',f'Other reasons (n={p["other_removed"]})']
    reason=["Reports excluded (with reasons):"]+[f'{r["name"]} (n={r["n"]})' for r in p["exclusion_reasons"]]
    def block(lines):return r"\\".join(tex_escape(s) for s in lines)
    head=r"""\documentclass[border=7pt]{standalone}
\usepackage{tikz}
\usetikzlibrary{positioning,arrows.meta}
\usepackage{xcolor}
"""
    for k,v in t.items():head+=f'\\definecolor{{p{k}}}{{HTML}}{{{v.lstrip("#")}}}\n'
    head+=r"""\begin{document}
\begin{tikzpicture}[
 basic/.style={rectangle,draw=pnavy,very thick,rounded corners=3pt,align=left,text width=5.2cm,inner sep=7pt,fill=white},
 excluded/.style={basic,draw=porange,fill=porange_light},
 included/.style={basic,draw=pgreen,fill=pgreen_light},
 arrow/.style={-{Latex[length=2.5mm]},draw=pnavy,line width=1.3pt},
 phase/.style={rectangle,rounded corners=3pt,fill=pteal,text=white,align=center,inner sep=7pt,font=\bfseries}
]
"""
    nodes=[("identified","basic",block(ident)),
           ("removed","excluded,right=2.3cm of identified",block(rem)),
           ("screened","basic,below=2cm of identified",f'Records screened (n={c["screened"]})'),
           ("screenout","excluded,right=2.3cm of screened",f'Records excluded (n={p["screen_excluded"]})'),
           ("sought","basic,below=1.2cm of screened",f'Reports sought for retrieval (n={c["sought"]})'),
           ("unavailable","excluded,right=2.3cm of sought",f'Reports not retrieved (n={p["not_retrieved"]})'),
           ("assessed","basic,below=1.2cm of sought",f'Reports assessed for eligibility (n={c["assessed"]})'),
           ("reasons","excluded,right=2.3cm of assessed",block(reason)),
           ("included","included,below=2cm of assessed",f'{tex_escape(p["included_label"])} (n={c["studies"]})'+r'\\'+f'Included reports (n={c["reports"]})')]
    for name,style,value in nodes:head+=f'\\node[{style}] ({name}) {{{value}}};\n'
    for label,ref in [("Identification","identified"),("Screening","screened"),("Included","included")]:
        head+=f'\\node[phase,left=1cm of {ref}] {{{label}}};\n'
    head+=f'\\node[phase,fill=pnavy,above=1.2cm of identified,text width=12cm] {{{tex_escape(p["title"])}}};\n'
    for a,b in [("identified","removed"),("screened","screenout"),("sought","unavailable"),("assessed","reasons")]:
        head+=f'\\draw[arrow] ({a}.east) -- ({b}.west);\n'
    for a,b in [("identified","screened"),("screened","sought"),("sought","assessed"),("assessed","included")]:
        head+=f'\\draw[arrow] ({a}.south) -- ({b}.north);\n'
    return head+"\\end{tikzpicture}\n\\end{document}\n"

def table(p,key,title):
    st.markdown(f"#### {title}")
    for i,r in enumerate(p[key][:]):
        a,b,d=st.columns([5,2,1])
        r["name"]=a.text_input("Name",r["name"],key=f"{key}_name_{i}",label_visibility="collapsed")
        r["n"]=int(b.number_input("Count",min_value=0,value=int(r["n"]),key=f"{key}_n_{i}",label_visibility="collapsed"))
        if d.button("✕",key=f"delete_{key}_{i}"):
            p[key].pop(i);st.rerun()
    if st.button(f"＋ Add {title.lower()}",key=f"add_{key}"):
        p[key].append({"name":"New entry","n":0});st.rerun()

st.set_page_config(page_title="panP-Diagram",page_icon="🔬",layout="wide")
if "project" not in st.session_state:st.session_state.project=copy.deepcopy(DEMO)
p=st.session_state.project
st.title("panP-Diagram")
st.caption("PRISMA Flow Designer · Full demonstration · Editable data · Original navy/teal/orange/green theme")
with st.sidebar:
    st.header("Project")
    if st.button("Restore full demo"):
        st.session_state.clear();st.session_state.project=copy.deepcopy(DEMO);st.rerun()
    upload=st.file_uploader("Load JSON project",type="json")
    if upload:
        try:
            incoming=json.load(upload)
            if not isinstance(incoming,dict) or any(not isinstance(incoming.get(k),list) for k in ("databases","other_sources","exclusion_reasons")):
                raise ValueError("Invalid project structure.")
            if st.button("Apply uploaded project"):
                st.session_state.clear();st.session_state.project={**copy.deepcopy(DEMO),**incoming};st.rerun()
        except (ValueError,TypeError) as exc:st.error(str(exc))
    st.header("Colours")
    for k in COLORS:p["theme"][k]=st.color_picker(k.replace("_"," ").title(),p["theme"].get(k,COLORS[k]))
left,right=st.columns([0.95,1.4],gap="large")
with left:
    p["title"]=st.text_input("Figure heading",p["title"])
    with st.expander("Identification",expanded=True):
        table(p,"databases","Databases")
        table(p,"other_sources","Other sources")
    with st.expander("Removed before screening",expanded=True):
        for k in ("duplicates","automation_removed","other_removed"):
            p[k]=int(st.number_input(k.replace("_"," ").title(),min_value=0,value=int(p[k])))
    with st.expander("Screening and retrieval",expanded=True):
        for k in ("screen_excluded","not_retrieved"):
            p[k]=int(st.number_input(k.replace("_"," ").title(),min_value=0,value=int(p[k])))
    with st.expander("Full-text exclusion reasons",expanded=True):
        table(p,"exclusion_reasons","Exclusion reasons")
    with st.expander("Included studies",expanded=True):
        p["study_count"]=int(st.number_input("Distinct included studies",min_value=0,value=int(p["study_count"])))
        p["included_label"]=st.text_input("Included box label",p["included_label"])
with right:
    c=counts(p);problems=errors(p,c)
    st.subheader("Live preview")
    cols=st.columns(4)
    for col,(name,val) in zip(cols,[("Identified",c["identified"]),("Screened",c["screened"]),("Assessed",c["assessed"]),("Studies",c["studies"])]):col.metric(name,val)
    for issue in problems:st.error(issue)
    if not problems:st.success("Arithmetic validation passed.")
    if c["reports"]>c["studies"] and not problems:st.warning("Multiple reports per included study: verify study-level grouping.")
    art=diagram(p,c)
    st.image(art,use_container_width=True)
    st.caption("Illustrative example data only. Verify your actual selection process and PRISMA reporting.")
    if not problems:
        a,b,d=st.columns(3)
        a.download_button("PDF",cairosvg.svg2pdf(bytestring=art.encode()),"panP_Diagram.pdf","application/pdf",use_container_width=True)
        b.download_button("SVG",art.encode(),"panP_Diagram.svg","image/svg+xml",use_container_width=True)
        d.download_button("PNG",cairosvg.svg2png(bytestring=art.encode(),output_width=1450),"panP_Diagram.png","image/png",use_container_width=True)
        st.download_button("Editable TikZ (.tex)",tikz(p,c).encode(),"panP_Diagram.tex","text/plain")
    st.download_button("Save project JSON",json.dumps(p,indent=2).encode(),"panP_Project.json","application/json")
