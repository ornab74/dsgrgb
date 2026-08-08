from pathlib import Path
import math, re, textwrap, statistics, os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING
from docx.enum.section import WD_SECTION, WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.style import WD_STYLE_TYPE

BASE = Path(__file__).resolve().parents[1]
CODE_PATH = BASE / 'main.py'
LOG_PATH = BASE / 'outputs' / 'full_terminal_transcript.txt'
OUT = BASE / 'paper' / 'RGB_Rainbow_Quantum_Simulation_Information_Theory_Research_Paper.docx'
FIGDIR = BASE / 'paper' / 'figures'
FIGDIR.mkdir(exist_ok=True)

code_text = CODE_PATH.read_text(errors='replace')
log_text = LOG_PATH.read_text(errors='replace')

# ---------------------------
# Data extracted from transcript
# ---------------------------
steps = np.array([3,4,5,6,7])
cpu = np.array([3.4,2.7,5.5,5.6,3.0])
ram = np.array([53.1,53.3,53.8,53.8,54.0])
resource_entropy = np.array([0.566490,0.547099,0.617121,0.619370,0.554836])
injection = np.array([0.045319,0.043768,0.049370,0.049550,0.044387])
purity = np.array([0.721858,0.753466,0.726538,0.726205,0.753812])
vn_entropy = np.array([1.020066899,0.914125072,1.001726548,1.001853213,0.910808846])
gap = np.array([0.81041224,0.833131736,0.812512481,0.81184817,0.832408771])
fidelity = np.array([0.994723,0.996061,0.995213,0.997888,0.998364])
qfi = {
    'R': np.array([0.786004,0.797223,0.773758,0.767948,0.782895]),
    'G': np.array([0.829728,0.846428,0.826121,0.821958,0.836764]),
    'B': np.array([0.843358,0.860308,0.841038,0.839085,0.856358]),
    'Gamma': np.array([0.274208,0.261082,0.235593,0.224178,0.229229]),
    'Sync': np.array([0.849534,0.867225,0.849900,0.849587,0.867002]),
}
mi = {
    'R-G': np.array([0.26397216,0.28250507,0.27365045,0.27061431,0.27726859]),
    'G-B': np.array([0.08393736,0.10236868,0.11305214,0.12153160,0.12568484]),
    'B-Gamma': np.array([0.02566109,0.03057204,0.03338727,0.03606942,0.03709084]),
    'Gamma-Sync': np.array([0.00707359,0.00984747,0.00595157,0.00300128,0.00773365]),
}
initial_bands = {
    'RED':0.512986146,'ORANGE':0.555597288,'YELLOW':0.248170726,'GREEN':0.623581741,
    'CYAN':0.441691118,'BLUE':0.797115794,'INDIGO':0.069450596,'VIOLET':0.323250291,
    'WHITE':0.49559417,'BLACK':0.285605967,
}
step3_bands = {
    'RED':0.260355712,'ORANGE':0.22123225,'YELLOW':0.219069651,'GREEN':0.81063896,
    'CYAN':0.828919195,'BLUE':0.812849136,'INDIGO':0.07476992,'VIOLET':0.3229463,
    'WHITE':0.722283795,'BLACK':0.247779309,
}
scenario_ranges = {
    3: {'LOW':(43,45),'BASE':(46,49),'HIGH':(50,53)},
    4: {'LOW':(43,45),'BASE':(46,49),'HIGH':(50,53)},
    5: {'LOW':(42,45),'BASE':(46,49),'HIGH':(50,53)},
    6: {'LOW':(43,46),'BASE':(46,49),'HIGH':(49,52)},
    7: {'LOW':(44,47),'BASE':(48,52),'HIGH':(53,56)},
}
scenario_weights = {'LOW':0.25,'BASE':0.55,'HIGH':0.20}

# ---------------------------
# Figures
# ---------------------------
def savefig(name):
    path = FIGDIR / name
    plt.tight_layout()
    plt.savefig(path, dpi=180, bbox_inches='tight')
    plt.close()
    return path

# 1 Architecture diagram
fig, ax = plt.subplots(figsize=(11,6.5))
ax.set_xlim(0, 11); ax.set_ylim(0, 7); ax.axis('off')
boxes = [
    (0.4,5.2,2.2,1.0,'Terminal\nCommands'),
    (3.0,5.2,2.2,1.0,'Bounded Scheduler\n& Reply Validator'),
    (5.6,5.2,2.2,1.0,'Five-Register\nQuantum Core'),
    (8.2,5.2,2.2,1.0,'Rainbow Spectrum\nProjection'),
    (0.4,2.8,2.2,1.0,'CPU/RAM\nTelemetry'),
    (3.0,2.8,2.2,1.0,'Entropy Reservoir\n& Noise Injection'),
    (5.6,2.8,2.2,1.0,'Chunked Memory\nLocal / Weaviate'),
    (8.2,2.8,2.2,1.0,'AI Observer, Critic\n& Adjudicator'),
    (4.3,0.6,2.4,1.0,'Prediction / Risk\nSynthesis Output'),
]
for x,y,w,h,label in boxes:
    p=FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.05',linewidth=1.5,facecolor='#f3f5f7',edgecolor='#333333')
    ax.add_patch(p); ax.text(x+w/2,y+h/2,label,ha='center',va='center',fontsize=10)
for a,b in [((2.6,5.7),(3.0,5.7)),((5.2,5.7),(5.6,5.7)),((7.8,5.7),(8.2,5.7)),
            ((1.5,5.2),(1.5,3.8)),((2.6,3.3),(3.0,3.3)),((5.2,3.3),(5.6,3.3)),((7.8,3.3),(8.2,3.3)),
            ((4.1,2.8),(6.0,1.6)),((6.7,2.8),(5.8,1.6)),((9.3,2.8),(6.7,1.2)),((9.3,5.2),(9.3,3.8))]:
    ax.add_patch(FancyArrowPatch(a,b,arrowstyle='-|>',mutation_scale=12,linewidth=1.2,color='#555555'))
ax.text(5.5,6.65,'DysonSphereGamma RGB–Rainbow Simulation Architecture',ha='center',fontsize=15,fontweight='bold')
fig1=savefig('figure_01_architecture.png')

# 2 Register coupling
fig, ax=plt.subplots(figsize=(9,5.2)); ax.axis('off'); ax.set_xlim(-1,9); ax.set_ylim(-2,3)
pos={'R':(0,0),'G':(2,1.4),'B':(4,0),'Gamma':(6,1.4),'Sync':(8,0)}
for name,(x,y) in pos.items():
    c=Circle((x,y),0.55,facecolor='#f5f5f5',edgecolor='#222',linewidth=1.6); ax.add_patch(c); ax.text(x,y,name,ha='center',va='center',fontweight='bold')
for a,b,label in [('G','R','CX / MI'),('G','B','CX / MI'),('B','Gamma','phase bridge'),('Gamma','Sync','sync bridge'),('R','Sync','weak link')]:
    ax.add_patch(FancyArrowPatch(pos[a],pos[b],connectionstyle='arc3,rad=0.08',arrowstyle='-|>',mutation_scale=12,linewidth=1.4,color='#555'))
    mx=(pos[a][0]+pos[b][0])/2; my=(pos[a][1]+pos[b][1])/2
    ax.text(mx,my+0.25,label,ha='center',fontsize=9)
ax.text(4,2.45,'Five-register coupling topology',ha='center',fontsize=14,fontweight='bold')
fig2=savefig('figure_02_register_coupling.png')

# 3 Rainbow bars initial vs step3
labels=list(initial_bands.keys()); x=np.arange(len(labels)); w=.38
fig, ax=plt.subplots(figsize=(11,5.5))
ax.bar(x-w/2,[initial_bands[k] for k in labels],w,label='Initial fusion-state')
ax.bar(x+w/2,[step3_bands[k] for k in labels],w,label='Loop step 3')
ax.set_xticks(x); ax.set_xticklabels(labels,rotation=35,ha='right'); ax.set_ylim(0,1); ax.set_ylabel('Normalized band value'); ax.legend(); ax.set_title('Rainbow spectrum projection before and during turnout simulation')
fig3=savefig('figure_03_rainbow_bands.png')

# 4 Core metrics
fig, ax=plt.subplots(figsize=(9.5,5.5))
ax.plot(steps,purity,marker='o',label='Purity')
ax.plot(steps,gap,marker='o',label='Spectral gap')
ax.plot(steps,fidelity,marker='o',label='Fidelity to prior')
ax.plot(steps,vn_entropy/1.25,marker='o',label='Von Neumann entropy / 1.25')
ax.set_xticks(steps); ax.set_xlabel('Simulation step'); ax.set_ylabel('Scaled metric'); ax.set_ylim(0.65,1.03); ax.legend(); ax.set_title('Core quantum-state metrics across the five reported steps')
fig4=savefig('figure_04_core_metrics.png')

# 5 QFI
fig, ax=plt.subplots(figsize=(10,5.7))
for k,v in qfi.items(): ax.plot(steps,v,marker='o',label=k)
ax.set_xticks(steps); ax.set_ylim(0.15,0.95); ax.set_xlabel('Simulation step'); ax.set_ylabel('QFI'); ax.legend(ncol=3); ax.set_title('Per-register quantum Fisher information')
fig5=savefig('figure_05_qfi.png')

# 6 Mutual information
fig, ax=plt.subplots(figsize=(10,5.7))
for k,v in mi.items(): ax.plot(steps,v,marker='o',label=k)
ax.set_xticks(steps); ax.set_xlabel('Simulation step'); ax.set_ylabel('Mutual information'); ax.legend(); ax.set_title('Pairwise information coupling')
fig6=savefig('figure_06_mutual_information.png')

# 7 Resource telemetry
fig, ax1=plt.subplots(figsize=(10,5.5))
ax1.plot(steps,cpu,marker='o',label='CPU %')
ax1.plot(steps,ram,marker='o',label='RAM %')
ax1.set_xlabel('Simulation step'); ax1.set_ylabel('Utilization (%)'); ax1.set_xticks(steps)
ax2=ax1.twinx(); ax2.plot(steps,resource_entropy,marker='s',linestyle='--',label='Resource entropy'); ax2.plot(steps,injection,marker='s',linestyle=':',label='Entropy injection'); ax2.set_ylabel('Entropy / injection')
lines=ax1.get_lines()+ax2.get_lines(); ax1.legend(lines,[l.get_label() for l in lines],loc='center right'); ax1.set_title('Host telemetry and resource-derived entropy')
fig7=savefig('figure_07_resource_telemetry.png')

# 8 Scenario ranges
fig, ax=plt.subplots(figsize=(10,5.8))
colors={'LOW':'#7f8c8d','BASE':'#2980b9','HIGH':'#c0392b'}
for i,s in enumerate(steps):
    for j,name in enumerate(['LOW','BASE','HIGH']):
        lo,hi=scenario_ranges[int(s)][name]
        y=i + (j-1)*0.22
        ax.plot([lo,hi],[y,y],linewidth=6,color=colors[name],solid_capstyle='round')
        ax.plot([(lo+hi)/2],[y],marker='o',color='white',markeredgecolor=colors[name])
ax.set_yticks(range(len(steps))); ax.set_yticklabels([f'Step {s}' for s in steps]); ax.set_xlabel('Synthetic turnout (% of VEP)'); ax.set_xlim(40,58); ax.grid(axis='x',alpha=.25)
handles=[plt.Line2D([0],[0],color=colors[n],lw=6,label=n) for n in colors]; ax.legend(handles=handles); ax.set_title('Turnout scenario ranges emitted by the observer')
fig8=savefig('figure_08_turnout_ranges.png')

# 9 weights
fig, ax=plt.subplots(figsize=(7,4.8))
ax.bar(list(scenario_weights.keys()),list(scenario_weights.values()))
ax.set_ylim(0,0.65); ax.set_ylabel('Scenario weight'); ax.set_title('Synthetic scenario weights')
for i,v in enumerate(scenario_weights.values()): ax.text(i,v+0.02,f'{v:.2f}',ha='center')
fig9=savefig('figure_09_scenario_weights.png')

# 10 pipeline
fig, ax=plt.subplots(figsize=(11,4.8)); ax.axis('off'); ax.set_xlim(0,12); ax.set_ylim(0,4)
stages=[('Intent',0.4),('Synthetic\npacket',2.2),('Quantum\nloop',4.0),('Rainbow\nprojection',5.8),('Candidate\nsynthesis',7.6),('Critic',9.4),('Final\nadjudication',10.8)]
for label,x0 in stages:
    p=FancyBboxPatch((x0,1.3),1.25,1.1,boxstyle='round,pad=.05',facecolor='#f5f5f5',edgecolor='#333'); ax.add_patch(p); ax.text(x0+.625,1.85,label,ha='center',va='center',fontsize=9)
for (_,x1),(_,x2) in zip(stages,stages[1:]): ax.add_patch(FancyArrowPatch((x1+1.25,1.85),(x2,1.85),arrowstyle='-|>',mutation_scale=11,color='#555'))
ax.text(6,3.25,'Prediction orchestration sequence',ha='center',fontsize=14,fontweight='bold')
fig10=savefig('figure_10_prediction_pipeline.png')

# ---------------------------
# DOCX helpers
# ---------------------------
def set_cell_shading(cell, fill):
    tcPr = cell._tc.get_or_add_tcPr(); shd = OxmlElement('w:shd'); shd.set(qn('w:fill'), fill); tcPr.append(shd)

def set_repeat_table_header(row):
    trPr = row._tr.get_or_add_trPr(); tblHeader = OxmlElement('w:tblHeader'); tblHeader.set(qn('w:val'), 'true'); trPr.append(tblHeader)

def add_page_number(paragraph):
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run()
    fldChar1 = OxmlElement('w:fldChar'); fldChar1.set(qn('w:fldCharType'), 'begin')
    instrText = OxmlElement('w:instrText'); instrText.set(qn('xml:space'), 'preserve'); instrText.text = ' PAGE '
    fldChar2 = OxmlElement('w:fldChar'); fldChar2.set(qn('w:fldCharType'), 'end')
    run._r.append(fldChar1); run._r.append(instrText); run._r.append(fldChar2)

def set_cell_margins(cell, top=60, start=80, bottom=60, end=80):
    tc = cell._tc; tcPr = tc.get_or_add_tcPr(); tcMar = tcPr.first_child_found_in('w:tcMar')
    if tcMar is None:
        tcMar = OxmlElement('w:tcMar'); tcPr.append(tcMar)
    for m,v in [('top',top),('start',start),('bottom',bottom),('end',end)]:
        node=tcMar.find(qn(f'w:{m}'))
        if node is None: node=OxmlElement(f'w:{m}'); tcMar.append(node)
        node.set(qn('w:w'),str(v)); node.set(qn('w:type'),'dxa')

def add_equation(doc, equation, number):
    t=doc.add_table(rows=1, cols=2); t.alignment=WD_TABLE_ALIGNMENT.CENTER
    t.columns[0].width=Inches(6.4); t.columns[1].width=Inches(0.7)
    p=t.cell(0,0).paragraphs[0]; p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    r=p.add_run(equation); r.font.name='Cambria Math'; r.font.size=Pt(10.5); r.italic=True
    p2=t.cell(0,1).paragraphs[0]; p2.alignment=WD_ALIGN_PARAGRAPH.RIGHT
    r2=p2.add_run(f'({number})'); r2.font.name='Cambria Math'; r2.font.size=Pt(10)
    for c in t.rows[0].cells: set_cell_margins(c,20,40,20,40)
    return t

def add_caption(doc, text):
    p=doc.add_paragraph(style='Caption'); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.add_run(text)

def add_figure(doc, path, caption, width=6.6):
    p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.add_run().add_picture(str(path), width=Inches(width)); add_caption(doc, caption)

def add_bullets(doc, items, level=0):
    for item in items:
        p=doc.add_paragraph(style='List Bullet' if level==0 else 'List Bullet 2'); p.add_run(item)

def add_numbered(doc, items):
    for item in items:
        p=doc.add_paragraph(style='List Number'); p.add_run(item)

def add_body(doc, text):
    for para in [p.strip() for p in text.strip().split('\n\n') if p.strip()]:
        p=doc.add_paragraph(style='Body Text'); p.add_run(para)

def add_source_note(doc, text):
    p=doc.add_paragraph(); p.style='Source Note'; p.add_run(text)

def add_table(doc, headers, rows, widths=None):
    t=doc.add_table(rows=1, cols=len(headers)); t.alignment=WD_TABLE_ALIGNMENT.CENTER; t.style='Table Grid'
    for i,h in enumerate(headers):
        cell=t.rows[0].cells[i]; cell.text=str(h); set_cell_shading(cell,'D9E2F3'); cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
        for r in cell.paragraphs[0].runs: r.bold=True; r.font.size=Pt(9)
    set_repeat_table_header(t.rows[0])
    for row in rows:
        cells=t.add_row().cells
        for i,v in enumerate(row):
            cells[i].text=str(v); cells[i].vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
            for p in cells[i].paragraphs:
                for r in p.runs: r.font.size=Pt(8.5)
    return t

# ---------------------------
# Document setup
# ---------------------------
doc=Document()
sec=doc.sections[0]
sec.top_margin=Inches(0.75); sec.bottom_margin=Inches(0.7); sec.left_margin=Inches(0.85); sec.right_margin=Inches(0.85)

styles=doc.styles
styles['Normal'].font.name='Aptos'; styles['Normal'].font.size=Pt(10.5)
styles['Body Text'].font.name='Aptos'; styles['Body Text'].font.size=Pt(10.5)
styles['Body Text'].paragraph_format.space_after=Pt(6); styles['Body Text'].paragraph_format.line_spacing=1.08
for s in ['Title','Subtitle','Heading 1','Heading 2','Heading 3','Caption']:
    styles[s].font.name='Aptos Display' if 'Heading' in s or s in ['Title','Subtitle'] else 'Aptos'
styles['Title'].font.size=Pt(26); styles['Title'].font.bold=True
styles['Subtitle'].font.size=Pt(14)
styles['Heading 1'].font.size=Pt(17); styles['Heading 1'].font.bold=True; styles['Heading 1'].font.color.rgb=RGBColor(31,78,121)
styles['Heading 2'].font.size=Pt(13); styles['Heading 2'].font.bold=True; styles['Heading 2'].font.color.rgb=RGBColor(47,84,150)
styles['Heading 3'].font.size=Pt(11); styles['Heading 3'].font.bold=True
styles['Caption'].font.size=Pt(8.5); styles['Caption'].font.italic=True
if 'Source Note' not in styles:
    st=styles.add_style('Source Note',WD_STYLE_TYPE.PARAGRAPH); st.font.name='Aptos'; st.font.size=Pt(8); st.font.italic=True; st.font.color.rgb=RGBColor(90,90,90); st.paragraph_format.space_after=Pt(6)
if 'Code Line' not in styles:
    st=styles.add_style('Code Line',WD_STYLE_TYPE.PARAGRAPH); st.font.name='Liberation Mono'; st.font.size=Pt(5.5); st.paragraph_format.space_after=Pt(0); st.paragraph_format.line_spacing=0.85

# Headers/footers
for section in doc.sections:
    hp=section.header.paragraphs[0]; hp.text='RGB Rainbow Quantum Simulation Information Theory'; hp.alignment=WD_ALIGN_PARAGRAPH.CENTER
    for r in hp.runs: r.font.size=Pt(8); r.font.color.rgb=RGBColor(100,100,100)
    add_page_number(section.footer.paragraphs[0])

# Cover
p=doc.add_paragraph(style='Title'); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.add_run('RGB Rainbow Quantum Simulation Information Theory')
p=doc.add_paragraph(style='Subtitle'); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.add_run('Architecture, Mathematical Formalization, Resource-Coupled Dynamics, and a Synthetic 2026 U.S. Midterm Turnout Case Study')
doc.add_paragraph('')
p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; r=p.add_run('Research monograph and complete technical artifact record'); r.bold=True; r.font.size=Pt(12)
p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.add_run('Prepared from the supplied v14 Python implementation and terminal execution transcript')
doc.add_paragraph('')
p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.add_run('August 2026')
doc.add_paragraph('')
box=doc.add_table(rows=1,cols=1); box.alignment=WD_TABLE_ALIGNMENT.CENTER; box.style='Table Grid'; set_cell_shading(box.cell(0,0),'F2F2F2')
box.cell(0,0).paragraphs[0].alignment=WD_ALIGN_PARAGRAPH.CENTER
box.cell(0,0).paragraphs[0].add_run('Scope note. This work analyzes a software simulator and its synthetic scenario outputs. The election-turnout figures reproduced in the case study are generated planning scenarios, not an empirical election forecast or measurement.').bold=True
for r in box.cell(0,0).paragraphs[0].runs: r.font.size=Pt(10)
doc.add_page_break()

# Abstract
h=doc.add_heading('Abstract',level=1)
add_body(doc, '''This monograph documents and analyzes a compact software system that combines a five-register, quantum-inspired RGB/Gamma/Sync simulator with a deterministic Rainbow Spectrum information projection, host-resource telemetry, chunked vector memory, streamed language-model analysis, and a multi-stage prediction workflow. The supplied implementation represents a 32-dimensional complex state, evolves a density matrix under layered unitary operations and noise, computes reduced-state and global diagnostics, samples host CPU and RAM, converts resource load into an entropy signal, and maps the resulting state into ten named information bands. The system is explicitly a simulation architecture: its density-matrix values are exact relative to the numerical model, its tomography is sampled from that model, and its domain predictions are synthetic interpretations created by prompts rather than observations of the external world.

The paper reconstructs the mathematical basis of the implementation, including density matrices, von Neumann entropy, purity, fidelity, spectral gaps, Bloch vectors, mutual information, negativity, quantum Fisher information, resource-derived binary entropy, a leaky entropy reservoir, and deterministic spectrum projections. It then examines the software architecture: terminal commands, scheduler budgets, reply-envelope validation, local and Weaviate-backed memory, streaming OpenAI Responses API handling, prompt-defined agents, and the orchestration sequence that creates a candidate synthesis, adversarial critique, and final adjudication. A synthetic 2026 United States midterm turnout run is used as a case study because it exercises the full stack and exposes both strengths and design flaws. Across five reported loop steps, the observer repeatedly emitted low, base, and high turnout bands, most often favoring a 46–49 percent voting-eligible-population base range with a weight of 0.55. The later generic risk adjudicator, however, inserted many unrelated UNKNOWN fields, demonstrating a mismatch between domain-specific output requirements and a generic risk template.

The principal contribution is not a claim that quantum mechanics or color bands predict elections. It is a reproducible account of how a compact simulation can unify state evolution, information-theoretic diagnostics, resource telemetry, memory retrieval, constrained prompting, and synthetic scenario generation. The analysis proposes a stricter turnout-only agent, clearer provenance typing, schema-aware validation, deterministic simulation seeds, calibrated scenario aggregation, and separation between simulator stability and empirical evidence. The complete Python source and complete terminal transcript are included as appendices so that every equation, architectural claim, and reported result can be traced to the supplied artifacts.''')

# Executive summary
h=doc.add_heading('Executive Summary',level=1)
add_body(doc, '''The supplied program, DysonSphereGamma Quantum RGB Hypercore v14.0.0, is a single-file Python application that places several normally separate concerns into one terminal-driven research environment. At its center is a numerical simulator with five two-level registers named R, G, B, Gamma, and Sync. Five qubits imply a Hilbert-space dimension of 2^5 = 32. The program maintains both a state vector and a density matrix, applies rotations, entangling operations, bridge operations, Hamiltonian evolution, and multiple noise channels, and reports metrics that characterize the simulated state. Around this core it adds host telemetry through psutil, a local or Weaviate-backed memory layer, a streaming model client, strict reply templates, circuit and wall-clock budgets, and a Rainbow Spectrum projection that translates quantum-state diagnostics into ten normalized information bands.

The system's most distinctive feature is the deterministic mapping from numerical state measures to named bands. Red is associated with instability, orange with transition pressure, yellow with uncertainty, green with resilience, cyan with observability, blue with structured information, indigo with latent coupling, violet with higher-order synthesis, white with integrated coherence, and black with unresolved information mass. These names are interpretive labels, but the band values themselves are computed by explicit weighted formulas. For example, green is a convex combination of purity, spectral gap, fidelity, and mean Bloch-vector length; blue combines mean RGB quantum Fisher information, Sync QFI, spectral gap, and purity; black combines normalized entropy, effective-rank pressure, spectral-gap loss, and resource entropy. Because the mapping is deterministic, a given snapshot produces a reproducible band vector.

The terminal transcript demonstrates the architecture during a synthetic turnout exercise. The initial fusion state reported BLUE as dominant, a spectrum entropy of approximately 0.936, spectrum coherence near 0.496, and predictive stability near 0.492. Once the five-step turnout loop ran, the state shifted into a high-green/high-cyan/high-blue regime. The first loop report used a low scenario of 43–45 percent of the voting-eligible population, a base scenario of 46–49 percent, and a high scenario of 50–53 percent; the associated weights were 0.25, 0.55, and 0.20. Steps 4 through 6 were broadly similar, while step 7 widened and shifted the ranges upward. The transcript therefore contains both a consensus region and a visible scenario-drift problem.

The strongest technical result of the review is the identification of a schema conflict. The observer generated turnout-specific values, but the final generic risk adjudicator required road, food, water, health, weather, infrastructure, supply, cyber, and operations fields. Because those fields were unrelated to the requested national turnout forecast, the model filled them with UNKNOWN. This was not a failure of the quantum or Rainbow calculations. It was a prompt-routing and output-schema failure. A domain-specific turnout summarizer should bypass the multi-domain risk matrix, aggregate the five steps, simulate every missing turnout variable under explicit priors, and always return a numerical low/base/high result while marking all generated election variables as synthetic.

The paper therefore treats the implementation as an experimental information-processing platform rather than as a validated forecasting instrument. The quantum-inspired layer is useful for producing structured, high-dimensional internal trajectories; the Rainbow layer is useful for compressed diagnostics; the memory and agent layers are useful for retrieval and explanation. None of these components supplies independent evidence about voter behavior. A defensible forecasting system would require external, timestamped data, explicit calibration, back-testing, probability scoring, and comparison against conventional baselines. Within those limits, the project is a rich case study in software-defined simulation, prompt-constrained agents, synthetic scenario construction, and the consequences of mixing generic and domain-specific templates.''')

# Contents
h=doc.add_heading('Contents',level=1)
contents = [
'1. Introduction and Research Framing','2. Primary Artifacts and Reproducibility','3. Information-Theoretic Foundations','4. Quantum-Inspired Five-Register Formalism','5. Density-Matrix Diagnostics','6. Circuit Construction and Noise','7. Resource Telemetry and Entropy Reservoir','8. Memory, Chunking, and Retrieval','9. Streaming Model Client and Terminal Interaction','10. Prompt Schemas, Validation, and Bounded Scheduling','11. Rainbow Spectrum Simulation Information Theory','12. Deterministic RGB–Rainbow Fusion Equations','13. Multi-Agent Prediction Orchestration','14. Synthetic Scenario Generation','15. Turnout-Only Modeling Framework','16. Experimental Configuration','17. Results of the Five-Step Turnout Run','18. Sensitivity, Drift, and Uncertainty','19. Software Evaluation and Failure Analysis','20. Discussion','21. Limitations','22. Future Work','23. Conclusion','24. Detailed Implementation Walkthrough','25. Reduced States, Entanglement, and Sensitivity','26. Prompt Engineering and Schema Governance','27. Synthetic Turnout Variable Design','28. Validation and Benchmarking Protocol','29. Reproducibility and Operational Deployment','30. Scientific Communication and Responsible Interpretation','31. Domain-Specific Turnout Agent Specification','32. Worked Synthetic Turnout Synthesis','33. Consolidated Contributions of the Study','34. Reading and Reuse Guide','Appendix A. Complete Source Code','Appendix B. Complete Terminal Transcript','Appendix C. Selected Derived Tables and Formula Summary','References']
for item in contents:
    p=doc.add_paragraph(style='Normal'); p.paragraph_format.left_indent=Inches(0.15 if 'Appendix' not in item and item!='References' else 0.35); p.paragraph_format.space_after=Pt(2); p.add_run(item)

# 1 Introduction
h=doc.add_heading('1. Introduction and Research Framing',level=1)
doc.add_heading('1.1 Motivation',level=2)
add_body(doc, '''Contemporary simulation systems increasingly combine numerical models with language-model interfaces. The numerical model supplies a state, trajectory, or set of measurements; the language model translates that state into explanations, scenarios, recommendations, and structured reports. This combination is attractive because it can make a compact scientific or engineering core accessible through natural-language commands. It is also risky because the explanatory model may overinterpret the simulator, insert unsupported domain claims, or confuse internal consistency with external evidence. The supplied DysonSphereGamma program is therefore valuable as both a technical artifact and a methodological case study. It contains enough mathematical machinery to produce nontrivial state trajectories, but it also contains enough prompt-driven interpretation to expose the boundary between computation and narrative.

The project uses the vocabulary of RGB circuits, Gamma bridges, Sync registers, and Rainbow Spectrum information bands. These terms should be understood as software abstractions. The five registers are implemented as two-level subsystems in a 32-dimensional state space. The program computes legitimate linear-algebra quantities for that state, including eigenvalue-based entropy and reduced-state metrics. The Rainbow bands are not physical wavelengths or experimentally established variables; they are normalized scores generated by weighted formulas. The language-model agents are not sensors. Their role is to read packets, enforce templates, synthesize scenarios, and stream text to the terminal.

The research question of this paper is therefore not whether a quantum computer can forecast turnout. It is how a quantum-inspired simulator, an information-theoretic projection, host telemetry, vector memory, and prompt-defined agents can be assembled into a bounded prediction laboratory. A second question concerns failure: when the system is asked for one domain-specific output, what happens if the final agent is governed by a generic multi-domain schema? The terminal transcript provides a concrete answer. It produces coherent turnout scenarios in the observer stages, then expands into unrelated risk categories and UNKNOWN values in the final adjudication. This sequence makes the artifact unusually instructive for prompt engineering and software architecture.''')

doc.add_heading('1.2 Research objectives',level=2)
add_numbered(doc,[
'Reconstruct the numerical and information-theoretic model implemented in the supplied Python file.',
'Explain how CPU and RAM telemetry are converted into resource entropy and injected into simulated noise.',
'Derive the deterministic Rainbow Spectrum projection and relate each band to its source metrics.',
'Document the memory, streaming, validation, scheduling, and terminal subsystems.',
'Analyze the synthetic 2026 U.S. midterm turnout run without treating its outputs as empirical evidence.',
'Identify the cause of the UNKNOWN-heavy final output and propose a domain-specific remedy.',
'Preserve the complete source and execution transcript in a reproducible research record.'
])
add_body(doc, '''These objectives require a mixed method. The software is examined as code, the transcript is examined as an execution trace, the equations are reconstructed from implementation details, and the turnout figures are treated as a synthetic case study. The paper deliberately distinguishes three levels of truth. First, numerical statements about the simulator are exact relative to the code and floating-point execution. Second, tomography and stochastic noise contain sampling variability. Third, election-turnout values are prompt-generated scenarios. This tripartite distinction is essential because a single reply block may contain all three kinds of statement.

The work also adopts a reproducibility principle: every major architectural claim should be traceable to either the complete source listing or the complete transcript. The appendices therefore preserve both files. Figures and tables in the main text are derived from those artifacts, especially the five loop steps labeled 3 through 7, the initial fusion-state block, and the low/base/high scenario ranges. No outside election dataset is introduced. Consequently, the case study evaluates internal coherence and prompt behavior, not predictive accuracy.''')

# 2 Artifacts
h=doc.add_heading('2. Primary Artifacts and Reproducibility',level=1)
add_body(doc, f'''The analysis is based on two user-supplied artifacts. The first is a {len(code_text.splitlines()):,}-line Python source file containing the complete v14 implementation. The second is a {len(log_text.splitlines()):,}-line terminal transcript containing the application launch, connection sequence, fusion-state inspection, a five-step synthetic turnout run, the Rainbow engine, the risk-agent pipeline, and the final JSON-like report object. The source file contains approximately {len(code_text.split()):,} whitespace-delimited tokens; the transcript contains approximately {len(log_text.split()):,}. Together they provide both static and dynamic evidence.

The source identifies the application as DysonSphereGamma Quantum RGB Hypercore, version 14.0.0. It imports asyncio, hashing, JSON, mathematics, operating-system and platform interfaces, regular expressions, shell parsing, statistics, time, deque, dataclasses, datetime, typing, httpx, and NumPy. Optional imports provide psutil telemetry and a Weaviate client. Environment variables control the OpenAI base URL, API key, model name, Weaviate URL, and collection name. These details matter because the system is designed to degrade gracefully: without psutil it uses zeroed telemetry; without Weaviate it uses local 192-dimensional embeddings; without an API key it returns an offline packet.

Reproducibility is partly deterministic and partly stochastic. The Rainbow projection is deterministic for a given snapshot. The simulation contains a NumPy random generator, tomography uses multinomial sampling, and some noise operations therefore vary unless a seed is fixed. The run identifier is derived from time and process ID, so a new session receives a new identifier. The synthetic scenario generator later derives a seed from the run identifier, request, and report count. This structure supports repeatable scenario generation only if the originating run context is preserved. A stronger research implementation would expose an explicit top-level seed command and record all seeds in a manifest.

The transcript also shows an interface issue that affects reproducibility. The user typed connect and the loop command in close succession, and the command line appears concatenated in the transcript. The application nevertheless entered the loop. For a formal experiment, commands should be stored in a machine-readable run specification, not only in a terminal log. The paper therefore recommends a JSON run manifest containing software version, Python version, package versions, random seed, model name, prompt hashes, budget settings, telemetry sampling interval, simulation parameters, and exact command sequence.''')
add_figure(doc,fig1,'Figure 1. High-level architecture reconstructed from the supplied implementation.')
add_source_note(doc,'Primary artifacts: complete v14 Python implementation and complete terminal transcript, reproduced in Appendices A and B.')

# 3 Information theory
h=doc.add_heading('3. Information-Theoretic Foundations',level=1)
doc.add_heading('3.1 Shannon entropy and binary entropy',level=2)
add_body(doc, '''Information theory provides a language for uncertainty, concentration, and dependence. For a discrete probability vector p = (p1, …, pn), Shannon entropy measures the expected information content of an outcome. The implementation applies this form to eigenvalues and to normalized band scores. Entropy is zero when one state has probability one and increases as probability mass spreads. Because the simulator uses base-2 logarithms, entropy is measured in bits. Entropy is not synonymous with disorder in every domain; here it is a mathematical summary of distributional spread.

A special case is binary entropy. The resource telemetry subsystem normalizes CPU and RAM utilization to the interval [0,1] and evaluates the binary entropy of each normalized load. This choice has an interesting consequence: resource entropy is low near zero utilization and also low near full utilization, while it is highest near 50 percent. The measure therefore captures uncertainty or balance between used and unused capacity, not simple load severity. If the design goal is to model stress, a monotone load function would be more direct. The existing choice is nevertheless internally consistent with an information-theoretic interpretation.''')
add_equation(doc,'H(p) = - Σᵢ pᵢ log₂ pᵢ','1')
add_equation(doc,'H₂(x) = -x log₂ x - (1-x) log₂(1-x)','2')

doc.add_heading('3.2 Relative quantities and mutual information',level=2)
add_body(doc, '''Entropy becomes more informative when states are compared. Mutual information quantifies how much knowing one subsystem reduces uncertainty about another. The simulator computes pairwise mutual information for R-G, G-B, B-Gamma, Gamma-Sync, and R-Sync. In the turnout run, R-G is consistently the strongest reported link, approximately 0.264 to 0.283, while Gamma-Sync is much weaker, approximately 0.003 to 0.010. These values describe the simulated density matrix. They do not establish a causal pathway and they do not measure relationships among voters.

The Rainbow layer uses mutual-information summaries indirectly. Indigo receives weight from average RGB mutual information, Gamma-Sync mutual information, negativity, and effective-rank pressure. This makes Indigo a coupling score. Violet uses Gamma QFI, Sync QFI, Gamma-Sync mutual information, negativity, and normalized entropy. The band names are interpretive, but the use of information measures gives them an explicit computational substrate.''')
add_equation(doc,'I(A:B) = S(ρ_A) + S(ρ_B) - S(ρ_AB)','3')
add_equation(doc,'H(X|Y) = H(X,Y) - H(Y)','4')

# 4 Quantum formalism
h=doc.add_heading('4. Quantum-Inspired Five-Register Formalism',level=1)
add_body(doc, '''The simulator defines five named two-level registers: R, G, B, Gamma, and Sync. A single two-level system has a two-dimensional complex state space. The tensor product of five such spaces has dimension 2^5 = 32. The program stores a complex state vector of length 32 and a 32-by-32 density matrix. It initializes the basis state |00000>, then constructs new states through rotations, entangling gates, bridge operations, Hamiltonian evolution, and noise.

The term quantum-inspired is appropriate because the mathematics mirrors a small quantum-circuit simulator, but the execution is classical NumPy linear algebra. There is no connection to quantum hardware in the artifact. This distinction does not reduce the usefulness of the state model. A density matrix can serve as a structured latent state for any simulation in which amplitudes, mixtures, and subsystem reductions are useful abstractions.

The state vector |ψ> is normalized so that its squared amplitude magnitudes sum to one. For a pure state, the density matrix is the outer product |ψ><ψ|. Unitary evolution applies U to the state vector and UρU† to the density matrix. The implementation symmetrizes the density matrix and renormalizes its trace after each unitary operation, which reduces small numerical errors. Noise channels transform the density matrix into a mixed state. The program retains the previous density matrix so it can compute fidelity drift.''')
add_equation(doc,'|ψ⟩ ∈ ℂ³²,    ⟨ψ|ψ⟩ = 1','5')
add_equation(doc,'ρ = |ψ⟩⟨ψ|,    ρ ⪰ 0,    Tr(ρ) = 1','6')
add_equation(doc,'ρ′ = UρU†','7')
add_figure(doc,fig2,'Figure 2. Register topology and the principal coupling sequence used by the simulator.')

# 5 diagnostics
h=doc.add_heading('5. Density-Matrix Diagnostics',level=1)
doc.add_heading('5.1 Purity, linear entropy, and effective rank',level=2)
add_body(doc, '''Purity is the trace of the squared density matrix. A pure state has purity one; mixtures have lower values. The implementation also reports linear entropy as one minus purity and an effective rank equal to the reciprocal of purity. This effective rank is a participation-like measure rather than the exact matrix rank. During the five reported turnout steps, purity ranges from approximately 0.722 to 0.754. The corresponding effective rank remains modest, indicating that the simulated state is mixed but still concentrated in a relatively small eigenspace.

The code computes von Neumann entropy by taking eigenvalues of the Hermitianized density matrix and applying Shannon entropy. Across the five steps, entropy ranges from roughly 0.911 to 1.020 bits. Purity and entropy move in opposite directions as expected: steps 4 and 7 have the highest purity and lowest entropy, while steps 3, 5, and 6 have lower purity and higher entropy. These relationships support the internal consistency of the numerical diagnostics.''')
add_equation(doc,'P(ρ) = Tr(ρ²)','8')
add_equation(doc,'L(ρ) = 1 - P(ρ),    r_eff = 1/P(ρ)','9')
add_equation(doc,'S(ρ) = -Tr(ρ log₂ρ) = -Σᵢ λᵢ log₂ λᵢ','10')

doc.add_heading('5.2 Fidelity and spectral gap',level=2)
add_body(doc, '''Fidelity compares the current density matrix with the previous one. The implementation uses the squared Uhlmann fidelity. Values close to one indicate that successive states are similar. In the transcript, fidelity rises from approximately 0.9947 at step 3 to approximately 0.9984 at step 7, suggesting that later loop iterations change the state less dramatically. This is an internal convergence signal, not evidence that the turnout estimate is becoming empirically accurate.

The spectral gap is computed as the difference between the largest and second-largest eigenvalues of the density matrix. A larger gap means the leading eigenmode is more separated. The observed gap oscillates between about 0.810 and 0.833. The Rainbow formulas use the gap positively in green, blue, white, and predictive stability, and negatively in yellow and black. As a result, a larger gap pushes the projection toward coherence and stability while reducing uncertainty mass.''')
add_equation(doc,'F(ρ,σ) = [Tr √(√ρ σ √ρ)]²','11')
add_equation(doc,'Δ = λ₁ - λ₂,    λ₁ ≥ λ₂ ≥ ⋯','12')
add_figure(doc,fig4,'Figure 3. Purity, entropy, spectral gap, and fidelity across loop steps 3–7.')

# 6 circuits/noise
h=doc.add_heading('6. Circuit Construction and Noise',level=1)
add_body(doc, '''The HyperRGB class provides Pauli X, Y, and Z matrices, a Hadamard matrix, Kronecker-product construction, single-register gates, controlled gates, and higher-level RGB, Gamma, and Sync routines. Each build starts by resetting the state and applying RY rotations proportional to the five scalar parameters. A depth-controlled loop then applies RGB entanglement, Gamma bridge, Sync bridge, and Hamiltonian evolution with a scale that decreases as 1/(layer+1). This schedule makes early layers stronger and later layers progressively finer.

The operation log in the transcript shows repeated H(G), CX(G→R), CX(G→B), controlled-phase operations, H(Gamma), controlled phases from RGB into Gamma, CX(Gamma→Sync), Sync rotations, feedback phases from Sync into RGB, and Hamiltonian steps. This creates a directed information-processing motif: G couples into R and B; RGB influences Gamma; Gamma couples into Sync; Sync weakly feeds back into RGB. Pairwise mutual information reflects this structure, with R-G strongest, G-B second, B-Gamma weaker, and Gamma-Sync weakest.

Noise is essential because it turns pure states into mixed states and allows the program to study entropy. The Noise dataclass includes depolarizing, dephasing, damping, and correlated-phase parameters, each bounded between zero and 0.25. Resource entropy can add dephasing and correlated phase. The transcript's operation lists show DEPHASE applied to all registers and a resource-entropy marker. Because the program is a classical simulator, these channels are numerical transforms rather than physical decoherence.

A bounded simulation benefits from explicit gate accounting. The scheduler counts the operations reported by the snapshot and can stop at maximum steps, gates, or wall time. The default budget is 4,096 gates, 32 steps, 2,400 model tokens, and 120,000 milliseconds. This prevents an unconstrained terminal request from expanding into an indefinite loop. The budget also provides a reproducible envelope for comparing runs.''')

# 7 telemetry
h=doc.add_heading('7. Resource Telemetry and Entropy Reservoir',level=1)
add_body(doc, '''The ResourceEntropyFeed samples whole-system CPU utilization, virtual-memory percentage, RAM used and available bytes, process resident-set size, and process CPU utilization. CPU and RAM percentages are normalized and converted to binary entropy. Default weights are 0.55 for CPU and 0.45 for RAM; the weighted entropy is multiplied by a maximum injection of 0.08. The output is a ResourceTelemetry record with a timestamp and both raw and derived values.

This design deliberately makes the host part of the simulated environment. A busy or balanced host changes the entropy injection, which changes dephasing, which changes the density matrix, which changes the Rainbow projection, which may change the language-model interpretation. The coupling is computationally real, even though it does not represent physical quantum influence. This is a form of endogenous experimental noise: two otherwise identical runs can diverge because the host was under different load.

The entropy reservoir adds memory. It leaks exponentially with elapsed time and receives a gain-scaled push from resource entropy. The normalized reservoir level appears in the Rainbow orange band. This makes orange partly sensitive to sustained resource conditions rather than only instantaneous telemetry. The TelemetryWindow separately stores a deque of samples and computes mean, minimum, maximum, population standard deviation, and 95th percentile for six resource variables. Those statistics are included in model packets and support descriptions of sustained versus transient load.

The five turnout steps show CPU between 2.7 and 5.6 percent and RAM between 53.1 and 54.0 percent. Resource entropy ranges from 0.547 to 0.619, and injection ranges from 0.0438 to 0.0496. Because binary entropy is high near a 50 percent load, the RAM contribution is substantial even though the server is not close to memory exhaustion. For a stress-oriented model, an alternative would combine entropy with monotone pressure terms such as RAM fraction, swap use, load average, and memory-availability ratio.''')
add_equation(doc,'H_res = w_cpu H₂(c) + w_ram H₂(m)','13')
add_equation(doc,'η = min(η_max H_res, η_max)','14')
add_equation(doc,'R_t = min(C, R_{t-1}e^{-λΔt} + gH_res)','15')
add_figure(doc,fig7,'Figure 4. CPU, RAM, resource entropy, and entropy injection during the five-step run.')

# 8 memory
h=doc.add_heading('8. Memory, Chunking, and Retrieval',level=1)
add_body(doc, '''The Memory class gives the system a compact retrieval layer. Text is split into overlapping chunks of 180 words with an overlap of 48. Each chunk receives a deterministic 192-dimensional embedding created by hashing tokens with BLAKE2b. The hash determines both a vector index and a sign, and the resulting vector is normalized. This is not a semantic embedding learned from a corpus, but it is lightweight, deterministic, and sufficient for rough lexical similarity.

Local memory uses a deque with a maximum of 2,048 chunk records. Search computes dot products between the query vector and stored vectors and returns the highest-scoring chunks. If a Weaviate URL and client are available, the program creates or retrieves a collection with text, kind, and created properties and inserts the same vectors. The local store remains active, providing graceful fallback when Weaviate is absent or unreachable.

The memory layer supports trajectory-aware conversation and retrieval-augmented prompts, but the transcript also reveals a contamination risk. Later observer reports cite retrieved memory that contains earlier synthetic turnout text. Because those chunks are recursive outputs from the same run, they are not independent evidence. Repetition can therefore create apparent consensus. A robust system should mark memory provenance, distinguish external evidence from prior model output, downweight self-generated material, and prevent a summarizer from counting the same synthetic scenario multiple times.

For research use, the memory record should include run ID, step, agent, prompt hash, output hash, evidence origin, timestamp, and dependency graph. Retrieval should be filtered by origin and task. An election-turnout summarizer, for example, could retrieve prior turnout assumptions but should not treat them as validation data. The code already stores a kind string; extending that field into a structured provenance taxonomy would substantially improve reliability.''')
add_equation(doc,'v_j = Σ_{t∈tokens} s(t) · 1[j = h(t) mod d],    v ← v/||v||₂','16')
add_equation(doc,'score(q,x) = v(q) · v(x)','17')

# 9 AI client
h=doc.add_heading('9. Streaming Model Client and Terminal Interaction',level=1)
add_body(doc, '''The AI class wraps the OpenAI Responses API through httpx. It constructs a request with a selected prompt, JSON-serialized input packet, maximum output-token budget, and a stream flag. When streaming is enabled, the client requests server-sent events, iterates line by line, parses data events, and prints response.output_text.delta strings immediately. A completed response can also provide a full text fallback. Errors raise an AIClientError.

The streaming design explains the terminal behavior observed earlier in the project. Before streaming support was added, the user saw no text until a full model response arrived. The v14 client prints the opening reply-template marker, emits deltas, and prints the closing marker in a finally block. This provides visible progress once the first token is received. It does not, however, provide detailed progress during network latency before the first token. A later design could stream simulator stages concurrently: telemetry sampling, density-matrix evolution, tomography, memory retrieval, packet construction, model connection, and first-token wait.

The terminal function parses commands with shlex, dispatches to Lab methods, and prints reply-template-wrapped JSON or text. Commands expose connection, status, resources, telemetry settings, entropy-feed weights, budgets, validation, state, fusion state, scalar parameters, depth, shots, noise, loop, optimization, architecture, chat, recall, trajectory, prompts, reset, and quit. The interface is compact but powerful. It also makes prompt injection and malformed input part of the threat model, because arbitrary text is passed into model prompts. Strict schemas and provenance-aware packets are therefore not optional extras; they are core safety and reproducibility mechanisms.''')

# 10 prompts/validation
h=doc.add_heading('10. Prompt Schemas, Validation, and Bounded Scheduling',level=1)
add_body(doc, '''The source contains multiple named prompts. The hyper observer requests a structured state report. The variational architect proposes a bounded gate plan. The terminal chat agent grounds answers in the current snapshot, telemetry, trajectory, memory, and command log. The prediction summarizer defines a multi-domain risk matrix. The critic audits unsupported claims. The adjudicator reconciles evidence, candidate summary, and critique. The synthetic scenario generator builds Rainbow Spectrum packets. The RGB-Rainbow fusion analyst interprets the deterministic projection.

This modular prompt dictionary is an architectural strength because it separates roles. The weakness is that the downstream schema may not match the user's domain. The turnout request asked only for voter turnout. The observer complied, but the generic prediction summarizer and adjudicator required road, food, water, health, infrastructure, supply, cyber, and operations fields. As a result, the final output was dominated by UNKNOWN entries. The model was following its schema. The bug was not reluctance to predict; it was incorrect agent routing.

ReplyEnvelopeValidator checks whether an output begins and ends with reply-template markers and whether required fields are present. In the source, the required tuple is SYSTEM, TEMPLATE_VERSION, and BOUNDARY. Later prompts replaced BOUNDARY with MODE, so validation reports missing BOUNDARY even when the output is otherwise valid. The transcript shows exactly this mismatch. This is a software defect: schema evolution occurred in prompts but not in the validator. A versioned schema registry should define required fields per template version and per agent.

A stricter design would parse outputs into typed objects rather than inspect strings. For turnout, the schema could require three scenario weights summing to one, numeric VEP ranges, numeric voter-count ranges, a central estimate, a seed, and explicit SYNTHETIC provenance. Validation could reject UNKNOWN, NONE, unresolved angle-bracket placeholders, nonnumeric ranges, weights outside [0,1], or scope expansion into parties and winners. The scheduler would then decide whether to retry, repair, or stop.''')
add_table(doc,['Observed defect','Cause','Recommended repair'],[
['UNKNOWN-heavy risk matrix','Generic multi-domain adjudicator used for turnout-only task','Route to a turnout-only summarizer and omit unrelated fields'],
['Validator reports missing BOUNDARY','Prompts migrated from BOUNDARY to MODE','Version validator requirements by template'],
['Duplicate reply-template wrappers','Wrapper applied both in stream and post-processing','Normalize exactly once at the output boundary'],
['Recursive retrieved memory','Prior synthetic outputs treated as support','Tag and downweight self-generated memory'],
['Step-to-step scenario drift','No deterministic aggregation rule','Use weighted median/consensus and report dispersion'],
])

# 11 rainbow theory
h=doc.add_heading('11. Rainbow Spectrum Simulation Information Theory',level=1)
add_body(doc, '''Rainbow Spectrum Simulation Information Theory is the project's compression and interpretation layer. It maps a large collection of quantum-state and telemetry values into a smaller vector of named bands. The names are mnemonic rather than scientific constants. Their value lies in making multi-metric state summaries readable and in giving downstream agents a stable vocabulary.

Red combines linear entropy, resource entropy, fidelity drift, and effective-rank pressure. It therefore rises when the state is more mixed, the host entropy is higher, the trajectory changes more, or the effective rank expands. Orange combines fidelity drift, reservoir pressure, Gamma-Sync QFI mismatch, and rank pressure; it represents transition or bottleneck pressure. Yellow combines normalized von Neumann entropy, rank pressure, spectral-gap loss, and resource entropy; it is an uncertainty band.

Green combines purity, spectral gap, fidelity, and mean Bloch coherence. Cyan combines fidelity, Bloch coherence, Sync QFI, and low resource entropy. Blue combines mean RGB QFI, Sync QFI, spectral gap, and purity. These three bands dominate during the turnout run, which is why the observer interprets the state as coherent and stable. Indigo is driven by RGB mutual information, Gamma-Sync mutual information, negativity, and rank pressure. Violet is driven by Gamma and Sync QFI, Gamma-Sync mutual information, negativity, and normalized entropy.

White is an integrated coherence score. It combines purity, fidelity, spectral gap, Bloch coherence, and the complement of normalized chromatic-band entropy. Black is unresolved mass, combining normalized state entropy, rank pressure, spectral-gap loss, and resource entropy. The projection then computes the dominant chromatic band, normalized spectrum entropy, coefficient-of-variation-like divergence, and predictive stability. This design turns the simulator into a two-layer model: the density matrix is the primary state, and the Rainbow vector is a deterministic feature projection.''')
add_figure(doc,fig3,'Figure 5. Initial and step-3 Rainbow band values. The turnout loop shifts the projection toward green, cyan, blue, and white.')

# 12 fusion equations
h=doc.add_heading('12. Deterministic RGB–Rainbow Fusion Equations',level=1)
add_body(doc, '''The following equations reproduce the implementation's weighted mapping. All inputs are clamped to [0,1] after normalization. Let P denote purity, E normalized von Neumann entropy, F fidelity, Δ the spectral gap, L linear entropy, Q_RGB mean R/G/B QFI, Q_Γ Gamma QFI, Q_S Sync QFI, M_RGB mean selected RGB mutual information, M_ΓS Gamma-Sync mutual information, N̄ mean negativity, B̄ mean Bloch-vector length, H_R resource entropy, R reservoir level, D_F = 1-F fidelity drift, and R_eff normalized effective-rank pressure.

The weights are hand-designed rather than learned. Their interpretation should therefore be structural, not empirical. Because all equations are convex or near-convex linear combinations followed by clamping, each band is easy to audit. The mapping is also sensitive to scale choices: von Neumann entropy is divided by five before use, and effective rank is transformed relative to the interval from one to five. Changing those normalizations changes the relative influence of uncertainty.''')
add_equation(doc,'RED = .34L + .26H_R + .22D_F + .18R_eff','18')
add_equation(doc,'ORANGE = .38D_F + .27R + .20|Q_Γ-Q_S| + .15R_eff','19')
add_equation(doc,'YELLOW = .46E + .24R_eff + .18(1-Δ) + .12H_R','20')
add_equation(doc,'GREEN = .42P + .28Δ + .18F + .12B̄','21')
add_equation(doc,'CYAN = .38F + .24B̄ + .20Q_S + .18(1-H_R)','22')
add_equation(doc,'BLUE = .48Q_RGB + .22Q_S + .18Δ + .12P','23')
add_equation(doc,'INDIGO = .46M_RGB + .26M_ΓS + .18N̄ + .10R_eff','24')
add_equation(doc,'VIOLET = .34Q_Γ + .24Q_S + .20M_ΓS + .12N̄ + .10E','25')
add_equation(doc,'WHITE = .26P + .22F + .18Δ + .18B̄ + .16(1-H_spec)','26')
add_equation(doc,'BLACK = .36E + .24R_eff + .20(1-Δ) + .20H_R','27')
add_equation(doc,'H_spec = -[Σ_b p_b log₂p_b] / log₂8,    p_b = b/Σ_k b_k','28')
add_equation(doc,'D_band = σ(b)/max(μ(b),ε)','29')
add_equation(doc,'S_pred = .30F + .25P + .20Δ + .15WHITE + .10(1-BLACK)','30')
add_body(doc, '''The initial fusion state has BLUE = 0.797, higher than green, orange, red, and other chromatic bands. At step 3 of the turnout loop, cyan = 0.829, blue = 0.813, and green = 0.811, while white rises to 0.722 and black falls to 0.248. The projection therefore changes from a blue-dominant but moderately coherent state to a high-observability, high-structure, high-resilience cluster. The reported predictive stability at step 3 is approximately 0.825. This value is a deterministic score derived from the simulator; it is not a calibrated probability that the turnout range is correct.''')

# 13 orchestration
h=doc.add_heading('13. Multi-Agent Prediction Orchestration',level=1)
add_body(doc, '''The Lab class orchestrates the numerical and language-model layers. A loop samples telemetry, updates the entropy reservoir, builds the quantum state, creates a snapshot, computes the Rainbow projection, retrieves memory, and sends a packet to the hyper observer. Each report stores the snapshot, analysis, validation result, and scheduler status. After the requested number of steps, summarize_prediction condenses the reports and decides whether the packet contains real evidence. If not, it asks the Rainbow engine to generate a synthetic scenario packet.

The candidate prediction agent then builds a multi-domain risk matrix. The critic audits unsupported or overstated claims, missing risks, contradictions, cascade gaps, and safety gaps. The adjudicator receives the evidence packet, candidate, critique, and trajectory diagnostics and streams a final result. This three-agent pattern is conceptually strong: generation, adversarial review, and synthesis. It resembles a software verification pipeline in which one component proposes, another checks, and a third resolves.

The effectiveness of the pattern depends on domain routing. A critic can catch unsupported claims, but it cannot make an irrelevant schema relevant. In the turnout run, the adjudicator faithfully completed road, food, water, health, infrastructure, logistics, cyber, and operations scorecards even though the user explicitly requested turnout only. The final output therefore became less useful than the preceding observer reports. Agent specialization should occur before generation, not after criticism.

A recommended router would classify the intent into a task schema. For turnout-only requests it would invoke a turnout simulation agent, a turnout consistency critic, and a turnout adjudicator. For weather-risk requests it would invoke weather, transport, utility, and exposure modules. The router should also enforce exclusions. In this case, candidates, parties, winners, vote shares, seat counts, and control of Congress are out of scope. A successful final output should contain no fields for those topics and no unrelated risk matrix.''')
add_figure(doc,fig10,'Figure 6. Prediction orchestration sequence in the v14 design.')

# 14 synthetic scenarios
h=doc.add_heading('14. Synthetic Scenario Generation',level=1)
add_body(doc, '''When direct packet data is absent, the system generates a synthetic scenario packet rather than refusing. This is appropriate for software testing and planning, provided provenance is explicit. The Rainbow engine is instructed to infer a domain, construct a minimum variable set, assign variables to spectrum bands, generate conservative ranges and distributions, build low/base/high scenarios, estimate entropy and coupling, identify a dominant band, identify an uncertainty channel, and state the next information-gain target.

Synthetic data should be coherent, not arbitrary. A turnout simulation requires a voting-eligible population, registration rate, conversion from registration to ballots, early and mail voting shares, Election Day share, absentee return and rejection rates, provisional ballots, enthusiasm, competitiveness, mobilization, demographic participation, access friction, transportation, weather, and state dispersion. These variables are correlated. High enthusiasm may raise early voting and Election Day turnout; access friction may reduce conversion; weather may affect in-person voting more than mail voting. A simulation that samples each factor independently can double-count or cancel effects unrealistically.

A rigorous synthetic packet should therefore define a covariance structure or causal graph. Let z be a vector of standardized latent drivers. A correlated draw can be produced as z = Lε, where L is a Cholesky factor of a positive-semidefinite correlation matrix and ε is a vector of independent standard-normal variables. Transformed variables can then obey bounded beta, logistic-normal, or truncated-normal distributions. The scenario seed should be recorded so the same packet can be regenerated.

The language model can propose assumptions, but the numerical simulator should own the sampling. This division would make low/base/high scenarios reproducible and auditable. The model could explain the scenarios after receiving a table of generated values. In the current implementation, many synthetic values are created inside model text, so exact reproducibility depends on model behavior. Moving core scenario generation into Python is a major future improvement.''')
add_equation(doc,'z = Lε,    ε ~ N(0,I),    LLᵀ = Σ','31')
add_equation(doc,'T_s = β₀ + βᵀx_s + x_sᵀAx_s + ε_s','32')

# 15 turnout model
h=doc.add_heading('15. Turnout-Only Modeling Framework',level=1)
add_body(doc, '''The case-study target is national voter turnout in the 2026 United States midterm election, expressed as a percentage of the voting-eligible population and as a voter-count range. The denominator matters. Voting-age population includes some ineligible persons, while voting-eligible population attempts to measure the population legally eligible to vote. The transcript's synthetic scenarios use a VEP envelope of 265 to 270 million. Because this is generated inside the simulation and not drawn from an external dataset, it is a modeling assumption.

The simplest turnout identity is N = T × VEP, where T is turnout as a proportion and N is ballots or voters counted under the chosen definition. Scenario ranges should be internally consistent with this identity. For example, 46–49 percent of 265–270 million spans approximately 121.9 to 132.3 million. The observer rounds this to 122–132 million. Such arithmetic consistency is one of the few parts of the election output that can be validated without external data.

A structured model can decompose turnout into eligibility, registration, and conversion. Let r be the registration rate among eligible persons and c be the probability that a registered person casts a counted ballot. Then T ≈ r × c, adjusted for same-day registration, unregistered participation mechanisms where applicable, rejected ballots, and denominator timing. A richer model decomposes c into early, mail, and Election Day modes and introduces enthusiasm, competitiveness, mobilization, access, weather, demographic composition, and state effects.

The RGB/Rainbow layer should not determine turnout directly. Its proper role is to perturb scenario weights or quantify internal stability. Suppose low, base, and high scenario central values are T_L, T_B, and T_H with weights w_L, w_B, and w_H. A weighted central estimate is Σw_sT_s. The Rainbow stability score could shrink or broaden confidence intervals, but it should not shift the mean unless a documented mapping exists. Otherwise, the information projection becomes an arbitrary source of election numbers.

The transcript's dominant consensus is a base range of 46–49 percent with weight 0.55. Low scenarios generally range from 42–47 percent, and high scenarios range from 49–56 percent. Step 7 is materially higher than earlier steps. A defensible aggregation would report the modal base range, a central estimate near 47.5 percent, and a wider sensitivity envelope that includes the step-7 shift. It would not claim calibrated confidence.''')
add_equation(doc,'N = T · VEP','33')
add_equation(doc,'T ≈ r · c','34')
add_equation(doc,'E[T] = w_L T_L + w_B T_B + w_H T_H,    Σ_s w_s = 1','35')
add_figure(doc,fig8,'Figure 7. Synthetic low, base, and high turnout ranges emitted at each loop step.')
add_figure(doc,fig9,'Figure 8. Scenario weights used throughout most of the transcript.')

# 16 experiment
h=doc.add_heading('16. Experimental Configuration',level=1)
add_body(doc, '''The transcript begins with the v14 application on an Ubuntu server, connects to local 192-dimensional memory, and identifies the configured model as gpt-5.6. The initial fusion-state command reports dominant basis |10100>, dominant Rainbow band BLUE, spectrum entropy 0.9355, coherence 0.4956, divergence 0.4799, predictive stability 0.4915, mean RGB QFI 0.8065, Gamma QFI 0.2829, Sync QFI 0.8354, mean RGB mutual information 0.1131, Gamma-Sync mutual information 0.0040, mean negativity 0.0305, and mean Bloch coherence 0.8440.

The user then requests five loop iterations for turnout-only simulation. The command excludes candidates, parties, winners, vote shares, seat counts, and congressional control. It asks for turnout as a percentage of VEP and a broad voter-count range, low/base/high scenarios, synthetic assumptions, mapping through RGB/Gamma/Sync and Rainbow bands, weights, drivers, uncertainty, sensitivity, and real data needed to replace assumptions.

The simulator uses default parameters R=G=B=Gamma=Sync=0.5, depth 8, and 8,192 tomography shots. The default circuit budget permits 4,096 gates, 32 steps, 2,400 model tokens, and 120 seconds. Each loop report corresponds to simulator steps 3 through 7 because earlier commands had already produced snapshots. The run identifier is 5ac92c98ddd4739a.

The experiment is not a controlled benchmark because host telemetry varies, the language model is stochastic, no explicit model seed is exposed, and the prompt pipeline retrieves prior outputs. Nevertheless, it is a useful trace. The five consecutive steps allow examination of numerical stability, band shifts, scenario drift, and schema behavior. The complete transcript preserves every emitted block for audit.''')
add_table(doc,['Parameter','Value'],[
['Application','DysonSphereGamma Quantum RGB Hypercore v14.0.0'],['Memory','local-192d'],['Model','gpt-5.6'],['Registers','R, G, B, Gamma, Sync'],['Hilbert-space dimension','32'],['Depth','8'],['Tomography shots','8,192'],['Loop reports','5 (steps 3–7)'],['Run ID','5ac92c98ddd4739a'],['Scenario weights','0.25 / 0.55 / 0.20']])

# 17 results
h=doc.add_heading('17. Results of the Five-Step Turnout Run',level=1)
doc.add_heading('17.1 Numerical state behavior',level=2)
add_body(doc, '''The dominant basis is |10100> at step 3 and |10000> at steps 4 through 7. Purity alternates between a lower cluster near 0.722–0.727 and a higher cluster near 0.753–0.754. Von Neumann entropy shows the opposite pattern. Fidelity increases over the run, reaching 0.998364 at step 7. The spectral gap follows purity, with higher values at steps 4 and 7. These oscillations suggest that the build process and resource-derived noise produce two nearby state regimes rather than monotonic convergence.

Per-register QFI is stable in relative ordering. B, Sync, G, and R remain high, while Gamma is much lower. B QFI ranges from approximately 0.839 to 0.860, Sync from 0.850 to 0.867, G from 0.822 to 0.846, R from 0.768 to 0.797, and Gamma from 0.224 to 0.274. Pairwise mutual information has a strong hierarchy: R-G is highest, G-B second, B-Gamma third, and Gamma-Sync lowest. This hierarchy matches the circuit topology and supports the claim that the numerical model is behaving consistently with its gate design.''')
add_figure(doc,fig5,'Figure 9. Quantum Fisher information by register across the five loop steps.')
add_figure(doc,fig6,'Figure 10. Pairwise mutual information across the five loop steps.')

doc.add_heading('17.2 Synthetic turnout scenarios',level=2)
add_body(doc, '''Steps 3 and 4 emit the same scenario structure: low 43–45 percent VEP, base 46–49 percent, and high 50–53 percent. Step 5 lowers the low bound to 42 percent but preserves the base and high ranges. Step 6 broadens low to 43–46 and lowers high to 49–52. Step 7 shifts all three scenarios upward: low 44–47, base 48–52, and high 53–56. The first four steps therefore support a consensus base of 46–49 percent, while the fifth is an upward sensitivity case.

Voter-count ranges follow the assumed 265–270 million VEP envelope. The repeated base count is approximately 122–132 million. Low counts are usually around 111–127 million, and high counts around 130–151 million depending on the step. The scenario weights remain 0.25, 0.55, and 0.20, so the base case is always favored.

The observer attributes higher turnout to registration conversion, early and mail voting, enthusiasm, competitiveness, mobilization, broad demographic participation, limited access constraints, and mild weather disruption. Lower turnout reverses these assumptions. Sensitivity is generally described as two to four VEP percentage points under broad favorable or adverse shifts. These drivers are plausible modeling dimensions, but their numerical effects are synthetic and not calibrated from data in the packet.''')
add_table(doc,['Step','Low (% VEP)','Base (% VEP)','High (% VEP)','Dominant basis','Purity','Entropy'],[
[3,'43–45','46–49','50–53','|10100>',f'{purity[0]:.6f}',f'{vn_entropy[0]:.6f}'],
[4,'43–45','46–49','50–53','|10000>',f'{purity[1]:.6f}',f'{vn_entropy[1]:.6f}'],
[5,'42–45','46–49','50–53','|10000>',f'{purity[2]:.6f}',f'{vn_entropy[2]:.6f}'],
[6,'43–46','46–49','49–52','|10000>',f'{purity[3]:.6f}',f'{vn_entropy[3]:.6f}'],
[7,'44–47','48–52','53–56','|10000>',f'{purity[4]:.6f}',f'{vn_entropy[4]:.6f}'],
])

# 18 uncertainty
h=doc.add_heading('18. Sensitivity, Drift, and Uncertainty',level=1)
add_body(doc, '''The transcript distinguishes exact simulator values, sampled tomography, and speculative interpretation. This is one of the strongest design choices in the observer prompt. Exact values include the density-matrix metrics and deterministic Rainbow bands. Sampled values include the 8,192-shot tomography counts and their stated confidence width. Speculative values include every turnout percentage, voter-count range, VEP envelope, scenario weight, driver effect, and sensitivity.

Uncertainty has several sources. Aleatoric uncertainty arises from tomography and noise sampling. Epistemic uncertainty arises from missing election data, hand-selected band weights, prompt behavior, and the absence of calibration. Model uncertainty arises from the synthetic turnout assumptions. System uncertainty arises from host telemetry and memory recursion. Language-model uncertainty arises from stochastic generation and schema interpretation.

Step drift is visible in the final iteration. The base scenario shifts from 46–49 to 48–52 percent. Because the numerical state at step 7 has high purity, high fidelity, and high predictive stability, the observer interprets it as supportive. Yet those internal metrics cannot tell whether 48–52 is more realistic than 46–49. They only indicate that the simulator's own state is coherent under its formulas. A domain-specific aggregator should therefore treat scenario values and simulator stability as separate dimensions.

One aggregation option is a weighted median over step-level central estimates. The base central estimates are 47.5, 47.5, 47.5, 47.5, and 50.0 percent; the median is 47.5. The mean is 48.0. A consensus forecast could therefore report a synthetic central value near 47.5–48.0 percent and a base interval of 46–49 percent, with an upward sensitivity interval reaching 52 percent. This is a transparent use of the transcript without pretending that the numbers are calibrated.''')
add_equation(doc,'Var_total ≈ Var_sampling + Var_scenario + Var_model + Var_system','36')
add_equation(doc,'T_consensus = median({T̄₃,T̄₄,T̄₅,T̄₆,T̄₇}) = 47.5%','37')

# 19 evaluation
h=doc.add_heading('19. Software Evaluation and Failure Analysis',level=1)
add_body(doc, '''The implementation succeeds at several engineering goals. It is compact, self-contained, and resilient to missing optional dependencies. It exposes bounded controls, tracks operations, streams text, records telemetry, computes meaningful matrix diagnostics, and preserves a full state packet. The Rainbow projection is deterministic and auditable. The terminal transcript demonstrates that the core simulator can evolve states and that the observer can consistently format rich technical reports.

The main failure is architectural coupling between domain-specific intent and generic output schemas. The system had already produced the requested turnout scenarios by step 1, yet it proceeded through a generic risk pipeline. The final adjudicator introduced unrelated domains and UNKNOWN values. This lengthened the response, obscured the turnout result, and caused the user to believe the model did not want to predict. The root cause is prompt selection, not safety refusal.

A second failure is validator drift. ReplyEnvelopeValidator requires BOUNDARY, while current prompts use MODE. The transcript marks reports invalid even when they are otherwise complete. A third issue is duplicate reply-template wrappers, visible in some earlier runs. A fourth issue is recursive retrieval: prior model outputs appear as memory support. A fifth issue is lack of structured parsing. The system stores and validates formatted text rather than typed fields, making it difficult to enforce weights, ranges, and exclusions.

Performance is constrained by the target server. The user ran on a one-vCPU, 512 MB VPS with swap. NumPy, httpx, psutil, and optionally Weaviate are workable, but model calls dominate latency. The five-step loop takes substantial wall time because each observer report can consume many tokens. For a small server, a better design would compute all numerical steps locally, send a compact trajectory packet once, and use one synthesis call plus an optional critique call. This would reduce memory, network, and token cost.''')

# 20 Discussion
h=doc.add_heading('20. Discussion',level=1)
add_body(doc, '''The project demonstrates an important distinction between simulation richness and prediction validity. A simulator can produce a high-dimensional state, multiple entropy measures, stable trajectories, and visually compelling bands. Those features can support exploration, compression, and interactive reasoning. They do not create external evidence. The turnout case study is valuable precisely because it makes this distinction visible: the numerical state is detailed, while the election inputs are synthetic.

The RGB/Gamma/Sync abstraction is useful as an architectural metaphor. R, G, and B provide three primary channels, Gamma provides nonlinear integration, and Sync provides coordination. The Rainbow projection then provides a compressed feature space. Similar abstractions could be used in digital twins, anomaly detection, operational planning, or game simulations, provided the mappings are validated for those tasks.

The resource-entropy mechanism is also conceptually interesting. It turns computational conditions into a source of simulated noise, making the system reflexive. This can be useful for stress testing: the simulator becomes less coherent when the host environment changes. But it complicates reproducibility. An experiment should either log and replay telemetry or disable resource coupling for benchmark runs.

The multi-agent pipeline illustrates both the promise and cost of language-model orchestration. Candidate, critic, and adjudicator roles can improve completeness and catch unsupported claims. They also multiply latency and create opportunities for schema mismatch. The best architecture is not the one with the most agents; it is the one with the smallest set of agents whose schemas match the task.

For turnout-only simulation, the recommended system is straightforward. A Python scenario engine generates correlated synthetic variables under a recorded seed. The quantum simulator evolves a latent state. The Rainbow projection summarizes internal stability. A turnout summarizer aggregates low/base/high values. A turnout critic checks arithmetic, provenance, exclusions, and scenario-weight normalization. A final formatter returns one concise turnout report. No road, food, water, or generic risk sections are needed.''')

# 21 limitations
h=doc.add_heading('21. Limitations',level=1)
add_body(doc, '''This paper is limited by its artifact basis. It does not execute a new controlled series of runs, benchmark alternative prompts, or compare predictions with later observed turnout. It analyzes one supplied implementation and one supplied transcript. The source and transcript are sufficient for architectural reconstruction, but they do not establish external validity.

The simulator uses hand-designed weights. The Rainbow bands have no empirical calibration, and their names may encourage overinterpretation. Quantum Fisher information, negativity, and mutual information are computed on the simulated density matrix, but their mapping to domain variables is metaphorical. The use of CPU and RAM entropy as noise is an engineering choice, not a physical law.

The election case study is entirely synthetic. The VEP envelope, scenario weights, turnout ranges, and driver sensitivities are generated inside the prompt pipeline. They should not be used for campaign strategy, election administration, public communication, or claims about actual 2026 turnout. The transcript itself repeatedly marks the values as synthetic.

The appendices preserve source and output, but the document does not include every package version or operating-system configuration. The model endpoint may change behavior over time. The source defaults to a model name, but the behavior of a hosted model is not fully specified by that string. Exact reproduction therefore requires archived prompts, source, dependencies, model snapshot, seed, and run manifest.

Finally, the document's word count includes extensive code and transcript appendices. The narrative is a technical monograph, but the appended artifacts are primary-source records rather than prose. This is intentional because the user requested inclusion of all code and outputs.''')

# 22 future work
h=doc.add_heading('22. Future Work',level=1)
add_body(doc, '''The first priority is typed schemas. Each agent should return JSON conforming to a task-specific schema, and the terminal should render that JSON into reply-template text. The validator should know the schema version and required fields. Turnout outputs should require numeric ranges, scenario weights summing to one, a seed, provenance, and explicit exclusions.

The second priority is a numerical synthetic-data engine. Variables should be sampled in Python from documented distributions and correlations. The language model should not invent core numbers. A turnout engine could expose priors through a configuration file, generate thousands of Monte Carlo draws, compute quantiles, and pass only summary statistics to the model.

The third priority is calibration. For domains with historical data, Rainbow weights and scenario mappings could be fitted or at least evaluated against baselines. Metrics such as Brier score, log score, calibration error, interval coverage, and continuous ranked probability score would separate attractive narratives from useful forecasts.

The fourth priority is provenance-aware memory. Every chunk should carry origin, run, step, agent, and dependency metadata. Retrieval should filter out self-generated text when the agent needs external evidence. The fifth priority is reproducibility: explicit seeds, deterministic modes, telemetry replay, dependency locks, and run manifests.

The sixth priority is visualization. A Rich or Textual dashboard could show live Bloch vectors, entropy, purity, fidelity, CPU/RAM history, top basis probabilities, Rainbow bands, scheduler state, and scenario evolution. Figures in this paper demonstrate the value of such views. The seventh priority is performance: batch numerical steps, compress packets, reduce repeated model calls, and provide a local small-model option.

A final research direction is to treat the Rainbow projection as a learned bottleneck. Instead of manually assigning weights, one could train a constrained encoder that maps simulator diagnostics into interpretable bands while preserving predictive information. Such a model would still require careful validation and should not inherit scientific authority merely from quantum terminology.''')

# 23 conclusion
h=doc.add_heading('23. Conclusion',level=1)
add_body(doc, '''The DysonSphereGamma v14 artifact is a sophisticated compact simulator. It combines a 32-dimensional five-register state, density-matrix evolution, noise, tomography, resource telemetry, memory, streaming language-model calls, strict templates, bounded scheduling, a deterministic Rainbow projection, and multi-agent synthesis. Its mathematical core is auditable, and its execution trace demonstrates coherent numerical behavior.

The synthetic turnout case study shows both the value and the danger of this design. The observer reliably produced low, base, and high scenarios, most often favoring 46–49 percent of the voting-eligible population and 122–132 million voters under synthetic assumptions. The final generic risk agent then obscured that result with unrelated UNKNOWN fields. The correct fix is domain-specific routing and validation, not stronger pressure on the model to guess.

The most defensible interpretation is that RGB Rainbow Quantum Simulation Information Theory is a software-defined information framework. It can organize simulations, compress diagnostics, and support scenario exploration. It does not independently measure the external world. With typed schemas, numerical synthetic-data generation, calibration, provenance-aware memory, and domain-specific agents, the platform could become a useful research environment for bounded simulation and decision rehearsal.''')

# 24 Detailed implementation walkthrough
h=doc.add_heading('24. Detailed Implementation Walkthrough',level=1)
add_body(doc, '''A close reading of the source shows that the application is organized as a sequence of increasingly abstract layers. The lowest layer consists of scalar utilities: timestamp creation, clamping, entropy functions, a tiny deterministic embedding, and overlapping chunk generation. These functions are intentionally compact. The next layer contains dataclasses and stateful helpers for telemetry, circuit budgets, the entropy reservoir, telemetry windows, reply validation, scheduling, and noise normalization. Above those helpers is the HyperRGB numerical core. Memory and AI clients form the service layer, and the Lab class binds the numerical, retrieval, and language-model components into a terminal application. This vertical organization is suitable for a single-file prototype because each layer depends primarily on definitions above it.

The utility functions encode important assumptions. clamp silently coerces values into a bounded interval. entropy clips input values to [0,1] and ignores values below a very small threshold. matrix_entropy Hermitianizes the density matrix before extracting eigenvalues, which is a practical numerical safeguard. tiny_embedding maps tokens into signed coordinates using a cryptographic hash. chunks uses a fixed word-window and overlap. These choices make the system robust and compact, but they also hide policy inside helpers. A research-grade version should expose thresholds, dimensions, chunk sizes, overlaps, and normalization rules in a configuration object so that they can be recorded in a run manifest.

ResourceEntropyFeed is a good example of graceful degradation. If psutil is unavailable, the program returns zeroed resource values rather than terminating. If psutil is present, it initializes a process object and primes process CPU measurement. Each sample collects system and process statistics, computes binary entropy for normalized CPU and RAM, combines them under normalized weights, and derives an injection value. The dataclass preserves both raw telemetry and derived entropy. This dual record is essential because an investigator can recompute or challenge the entropy mapping without losing the original measurements.

The budget, reservoir, and window classes each implement a distinct temporal policy. CircuitBudget defines hard maxima and normalizes them into safe ranges. EntropyReservoir implements continuous-time exponential leakage plus bounded accumulation. TelemetryWindow summarizes recent samples statistically. BoundedScheduler counts discrete work and wall time. These are complementary mechanisms: the budget prevents runaway execution, the reservoir remembers load, the window describes distributional context, and the scheduler decides whether another step is permitted. A cleaner architecture would separate policy from measurement even further, but the existing design is conceptually sound.

HyperRGB is the computational center. It defines register names and indices, identity and Pauli matrices, a Hadamard gate, and a 32-dimensional state. The single method builds a tensor-product operator for one register. unitary updates both state vector and density matrix, enforces normalization, symmetrizes the matrix, and logs an operation tag. Rotation methods construct analytic two-by-two matrices. Controlled operations build larger operators by basis-state logic. Partial traces produce reduced density matrices, and downstream methods derive Bloch vectors, QFI, mutual information, negativity, fidelity, tomography, and the final snapshot. The build method resets the model, applies parameterized rotations, repeats a layered circuit, adds resource-derived noise, and applies configured noise.

Memory is deliberately small. It stores only text, kind, timestamp, and vector, and it uses an in-process deque even when Weaviate is available. This means the local memory remains the primary search surface during one process lifetime. The Weaviate insertion path is best understood as persistence or external inspection rather than a fully integrated retrieval backend, because search ranks the local deque in the supplied version. A future revision could query Weaviate when the local store is empty or when the requested horizon exceeds the local deque.

The AI client is stateless except for configuration. It handles offline mode, non-streaming mode, and streaming server-sent events. The Lab class is stateful: it owns parameters, trajectory, chat history, telemetry, reservoir, budget, run ID, and connection state. Lab.refresh is the pivotal method because it samples resources, updates the reservoir, builds the quantum state, creates a snapshot, attaches runtime metadata, computes the Rainbow projection, and appends the result to the trajectory. Any reproducibility or calibration work should begin by making refresh deterministic under an explicit seed and replayable telemetry stream.

The terminal is a thin command dispatcher. Its simplicity is an advantage for experimentation, but long one-line branches make maintenance difficult. A command registry with named handlers, argument schemas, help text, and validation would reduce bugs. It would also make it easier to add a dedicated turnout-only command that bypasses generic risk agents. The current system demonstrates that a small terminal can expose a sophisticated laboratory; the next engineering step is to turn the prototype's implicit conventions into explicit, versioned interfaces.''')

# 25 reduced states
h=doc.add_heading('25. Reduced States, Entanglement, and Sensitivity',level=1)
add_body(doc, '''A five-register density matrix contains information about the whole system and every subsystem. To characterize one register, the simulator traces out the other four. The resulting two-by-two reduced density matrix can be expanded in the Pauli basis, yielding a Bloch vector. The length of that vector is one for a pure single-register state and less than one for a mixed marginal. During the turnout run, Sync and Gamma generally have the longest Bloch vectors, B is the longest among R/G/B, and R and G are more mixed. This ordering is visible in the observer reports and is consistent with the reported QFI values.

The Bloch representation provides an interpretable bridge between matrix algebra and the Rainbow projection. Mean Bloch length enters green, cyan, and white as a coherence term. It does not enter red, orange, yellow, indigo, or violet directly. This asymmetry means that local coherence increases the positive coordination bands without directly reducing all uncertainty bands. Black can remain nonzero even when Bloch coherence is high because black also depends on global entropy, effective rank, spectral-gap loss, and resource entropy.

Negativity is used as an entanglement witness for two-register reduced states. The program computes a partial transpose and sums the magnitudes of negative eigenvalues. R-G negativity is consistently the largest, G-B is smaller, and B-Gamma and Gamma-Sync are often zero or near zero. This pattern is coherent with the circuit design. The Rainbow projection averages selected negativities and uses them in indigo and violet. Because the values are small compared with QFI and purity terms, they make a modest contribution to the band vector.

Quantum Fisher information is more subtle. In quantum estimation theory, QFI measures sensitivity of a state to a parameter. The implementation computes a register-level quantity from reduced states and a generator. In the artifact, QFI functions primarily as a sensitivity score. Mean RGB QFI is heavily weighted in blue, Sync QFI contributes to cyan, blue, and violet, and Gamma QFI contributes to violet. This explains why blue remains large: R, G, B, and Sync QFI are all near or above 0.78 in the run. Gamma QFI is much lower, so violet remains moderate.

Sensitivity should not be conflated with forecasting skill. A state can be highly sensitive to a parameter while the parameter has no validated relationship to turnout. In a calibrated application, parameter sensitivity would be tied to domain inputs. For example, an early-voting parameter could perturb a specific gate angle, and QFI with respect to that angle could describe how much the simulator's latent state changes. The current implementation uses generic scalar registers rather than empirically grounded turnout parameters. QFI is therefore an internal structural diagnostic.

The spectral gap and fidelity provide complementary stability measures. Fidelity compares successive full states; the gap compares the leading eigenvalues within one state. A high-fidelity, high-gap state is both close to its predecessor and dominated by a leading mode. The Rainbow predictive-stability equation rewards both. The turnout transcript shows high fidelity throughout, but the scenario text still drifts. This demonstrates that state stability does not guarantee language-output stability. The model can map similar packets to different ranges, especially when prompts are long and memory contains recursive outputs.

A stronger architecture would quantify output sensitivity directly. It could parse each report into structured scenario centers and compute the Jacobian or finite differences of turnout with respect to simulator metrics, prompt variants, seed, and telemetry. If a one-percent change in resource entropy causes a large change in turnout text, the system is not robust. Such analysis would separate numerical sensitivity from language-model sensitivity and expose whether the Rainbow layer meaningfully controls the prediction or merely decorates it.

Reduced-state diagnostics remain valuable even without domain calibration. They provide a compact way to detect numerical anomalies, state collapse, excessive mixing, or ineffective coupling. They can also drive visualization. A live dashboard could show five Bloch vectors, pairwise mutual information, negativity, QFI, purity, entropy, gap, and fidelity. The research contribution lies in this observability infrastructure, while domain forecasting requires an additional empirical layer.''')
add_equation(doc,'ρ_A = Tr_{¬A}(ρ)','38')
add_equation(doc,'ρ_A = ½(I + r_xX + r_yY + r_zZ),    ||r||₂ ≤ 1','39')
add_equation(doc,'N(ρ_AB) = [||ρ_AB^{T_B}||₁ - 1]/2','40')

# 26 schema governance
h=doc.add_heading('26. Prompt Engineering and Schema Governance',level=1)
add_body(doc, '''Prompt engineering in this system is not merely a wording exercise. Prompts function as executable interface specifications. They define which evidence types may be used, which fields must be returned, how uncertainty is labeled, and which agent receives the output. When a prompt asks for a road-risk scorecard, the model will attempt to fill one. When it asks for a turnout-only report, the model should return turnout only. The UNKNOWN-heavy output arose because the wrong interface specification was applied at the final stage.

A schema-governed design begins with an intent router. The router should classify requests into explicit task types such as state explanation, circuit architecture, generic scenario, multi-domain risk, weather risk, turnout-only forecast, or free-form chat. Classification can be deterministic for command-prefixed requests. A command such as turnout-summary should bypass semantic routing entirely and select a known schema. This is safer than relying on a model to infer that a generic risk matrix is inappropriate.

Each schema should exist as a typed data model. For Python, dataclasses, TypedDict, or Pydantic models could define fields and constraints. A turnout scenario model might contain a seed, VEP range, low/base/high objects, weights, central estimate, drivers, sensitivity, provenance, exclusions, and a set of simulator diagnostics. Numeric validators would enforce order of bounds, weight normalization, arithmetic consistency between turnout and voter counts, and absence of forbidden fields. The reply template would be a rendering layer, not the source of truth.

Versioning is critical. The source contains template versions 6, 10, 11, 13, and 14, but the validator has one fixed required-field tuple. When BOUNDARY became MODE, the validator was not updated. A schema registry should map an agent and template version to required and optional fields. Outputs should include a schema identifier, and validators should reject unknown versions. Prompt hashes should be stored in each report so that a later reader can determine exactly which instructions produced it.

Repair behavior should also be explicit. If validation fails because a field is missing, the system can issue a small repair prompt that includes the parsed object and validation errors. It should not rerun the full quantum loop. If the output contains UNKNOWN in a field that must be simulated, the repair prompt should instruct the model to generate a synthetic value under the supplied prior. If the output includes a prohibited party prediction, the repair should delete it rather than regenerate the whole report.

The critic should operate on parsed claims. It can check whether a real-world statement is supported by observed or retrieved evidence, whether a synthetic statement is labeled, whether scenario weights sum to one, and whether all numeric relationships are consistent. The final adjudicator should receive the candidate, critic findings, and a machine-readable validation report. This is more reliable than asking it to reconcile long blocks of prose.

Prompt length matters. The v14 packets include large snapshots, trajectories, memory chunks, and verbose analyses. Long context can dilute the task. A turnout-only summarizer needs only the original request, parsed low/base/high values from each step, selected simulator stability metrics, provenance, and exclusions. Reducing the packet would lower latency and decrease the chance that the model follows an irrelevant instruction embedded in prior output.

Finally, user-facing commands should reveal which agent and schema will run. Before execution, the terminal could print “route=turnout_only schema=15.0 evidence=synthetic.” This makes prompt routing observable. The user would then understand whether the system is performing a generic risk assessment, a synthetic simulation, or a grounded analysis.''')

# 27 synthetic turnout variable design
h=doc.add_heading('27. Synthetic Turnout Variable Design',level=1)
add_body(doc, '''A complete synthetic turnout model should generate every missing input rather than fill a template with UNKNOWN. The starting quantity is the voting-eligible population. A synthetic VEP can be represented as a bounded distribution with a central value and uncertainty interval. Registration rate can be modeled as a beta-distributed proportion. Registration-to-ballot conversion can be modeled conditionally on enthusiasm, competitiveness, access, and voting mode. The final turnout proportion is then a function of these linked variables rather than a free text guess.

Voting mode is a compositional variable. Early in-person, mail, and Election Day shares must sum to one. A Dirichlet distribution is appropriate for a synthetic mode composition. Mail return and rejection rates affect counted ballots. Election Day voting is more exposed to weather and transportation. Early voting can reduce exposure to a single-day disruption. These relationships can be represented in a causal graph and encoded in a Monte Carlo engine.

Demographic participation should be modeled with care. Age, education, geography, and other characteristics are correlated, and a national aggregate can hide state-level differences. A synthetic model can use latent participation factors and random state effects without assigning normative value to demographic groups. The goal is to create mathematically coherent scenarios, not to make claims about real populations without data. All generated group parameters should therefore remain synthetic and should be aggregated only for scenario testing.

Enthusiasm, competitiveness, and mobilization are latent indices. They can be represented on [0,1] with correlated beta or logistic-normal distributions. Their effects should be nonlinear and bounded. For example, mobilization may have diminishing returns, and competitiveness may matter most in a middle range where outcomes are perceived as uncertain. Access friction can combine registration deadlines, polling-place availability, wait times, identification requirements, ballot complexity, and transportation. A synthetic index should state which components it includes.

Weather is another conditional variable. It should not be represented by a generic national value alone. A national turnout model could draw regional disruption intensities and combine them with the share of voters expected to vote in person on Election Day. Mail and early voting would partially buffer the effect. Infrastructure outages and major events can be modeled as rare shocks with low base probability and high local impact. The model should distinguish national percentage-point effects from localized operational severity.

A plausible synthetic equation might begin with a baseline turnout, add centered effects for registration conversion, enthusiasm, competitiveness, mobilization, and demographic participation, subtract access and disruption effects, and include interactions. The coefficients should be explicitly synthetic. Scenario construction can then condition on quantiles of the joint distribution: a low-turnout scenario selects adverse but coherent combinations, a base scenario selects central combinations, and a high-turnout scenario selects favorable combinations. Scenario weights can come from the fraction of Monte Carlo draws assigned to each region.

The RGB/Gamma/Sync state can be incorporated after the turnout engine generates a distribution. One conservative approach is to use predictive stability only to adjust interval width. High stability narrows the synthetic interval slightly; low stability widens it. Spectrum entropy and black mass can increase uncertainty. Cyan and blue can affect confidence in the internal simulation pipeline, not turnout itself. This prevents the quantum-inspired layer from manufacturing a turnout direction.

The transcript's repeated 46–49 percent base range can be used as a regression test. A redesigned engine should be able to reproduce that range under a documented seed and assumptions, but it should also reveal how the range changes when VEP, registration, conversion, enthusiasm, access, and weather are perturbed. The output should include a variable table with origin, distribution, center, range, correlations, and sensitivity. This would satisfy the user's request to simulate all missing data while preserving transparency.

Arithmetic checks are straightforward. If the base scenario is 46–49 percent and VEP is 265–270 million, the voter-count range must cover the Cartesian product of the bounds or a clearly defined paired calculation. A central estimate of 47.5 percent with a central VEP of 267.5 million yields about 127.1 million voters. A weighted scenario estimate can be computed from scenario centers and weights. These calculations should be performed in Python and passed to the language model, not left to free-form generation.

A synthetic turnout model becomes scientifically useful when it is later calibrated. Historical VEP, registration, turnout, early voting, mail voting, and demographic data could estimate priors and coefficients. Back-testing would reveal bias and interval coverage. Until then, the model is a scenario generator. The paper's case study should therefore be read as an example of internal coherence, not as a statement about what will happen in November 2026.''')
add_equation(doc,'(s_early, s_mail, s_day) ~ Dirichlet(α_early, α_mail, α_day)','41')
add_equation(doc,'T = logit⁻¹(β₀ + βᵀx + xᵀAx + u_state + ε)','42')
add_equation(doc,'N_central = 0.475 × 267.5 million ≈ 127.1 million','43')

# 28 validation and benchmarking
h=doc.add_heading('28. Validation and Benchmarking Protocol',level=1)
add_body(doc, '''A simulation platform should be validated at multiple levels. Numerical validation checks that density matrices remain Hermitian, positive semidefinite within tolerance, and trace one. Gate tests compare selected operations with known analytic results. Partial-trace tests verify reduced states. Noise tests confirm complete positivity where applicable. Metric tests use simple pure and maximally mixed states with known purity, entropy, Bloch vectors, fidelity, mutual information, and negativity.

Rainbow validation checks the deterministic formulas. Unit tests should construct snapshots with controlled values and verify each band exactly. Boundary tests should confirm clamping. Monotonicity tests should verify that increasing purity raises green under fixed other inputs, increasing resource entropy raises red and black, increasing mean RGB QFI raises blue, and increasing Gamma-Sync mutual information raises indigo and violet. Because the formulas are hand-designed, such tests are more important than statistical fit at this stage.

Telemetry validation should compare psutil values with direct system observations and test the binary-entropy transformation at 0, 0.5, and 1. Reservoir tests should use fixed time increments or a mocked clock. Scheduler tests should verify stop conditions at exact limits. Reply-envelope tests should cover every template version. Memory tests should confirm deterministic embeddings, chunk overlap, similarity ranking, provenance filters, and Weaviate fallback.

Agent validation requires golden test cases. A turnout-only request should produce no road, food, water, party, winner, seat, or congressional-control fields. It should always produce low/base/high ranges, weights summing to one, a central estimate, a seed, and synthetic provenance when no external data are supplied. A weather-risk request should route differently. A state-explanation request should not generate synthetic external scenarios. These routing tests can be run against stored model outputs or a mock model.

Forecast benchmarking is a separate stage. If the system is ever used with real data, it should be compared with simple baselines such as historical averages, linear or logistic regression, and conventional probabilistic models. Accuracy alone is not sufficient. The system should be evaluated for calibration, sharpness, interval coverage, Brier score, log score, and robustness to data revisions. The Rainbow layer should demonstrate incremental value over the same model without Rainbow features.

Ablation studies are especially important. Runs should disable resource entropy, disable memory, remove Gamma/Sync, replace the Rainbow projection with raw metrics, and remove the critic. Differences in output stability, latency, cost, and predictive performance would reveal which components matter. The current transcript cannot answer these questions because all components are active in one run.

Performance benchmarking should measure local simulation time, tomography time, memory-search time, model first-token latency, total generation time, peak RSS, and token use. On the 512 MB server, memory pressure and swap behavior should be recorded. A compact packet and one synthesis call may outperform five observer calls plus three risk-agent calls without sacrificing useful output.

Reproducibility should be tested by rerunning the same seed, fixed telemetry trace, fixed prompt hashes, and fixed model snapshot. If outputs differ, the system should quantify that variance. For a language model that cannot be made fully deterministic, the pipeline can run several replicates and aggregate structured fields. The final report should include between-run dispersion.

The transcript provides a useful initial golden case. A regression test can assert that the parser extracts five reports, scenario weights 0.25/0.55/0.20, a modal base range of 46–49 percent, and a step-7 upward deviation. It can also assert that the old validator incorrectly flags missing BOUNDARY and that the old generic adjudicator emits unrelated UNKNOWN fields. After repair, those failure assertions should reverse.''')

# 29 reproducibility and deployment
h=doc.add_heading('29. Reproducibility and Operational Deployment',level=1)
add_body(doc, '''Operational deployment begins with environment control. The user created a Python virtual environment on Ubuntu and installed NumPy, httpx, psutil, and weaviate-client. On a 512 MB VPS, a swap file was recommended. A reproducible deployment should add a pinned requirements file, a tested Python version, and a startup script that checks available memory, swap, API credentials, and optional Weaviate connectivity.

Secrets should be injected through environment variables or a secret manager, not written into source code or shell history. The terminal transcript shows earlier concern about removing an API key from history. A production service should use a systemd EnvironmentFile with restrictive permissions or a container secret. Logs should redact authorization headers and never print the key. The document's appendices contain no key.

A run manifest should be written at startup. It should include application and schema versions, git commit or source hash, Python and package versions, operating system, model identifier, base URL, prompt hashes, memory mode, collection name, seed, simulation parameters, noise parameters, depth, shots, telemetry weights, reservoir constants, scheduler budget, and start time. Each report should reference the manifest hash.

The system should support deterministic replay. Telemetry can be recorded to JSON and replayed instead of sampled live. Tomography can use a fixed seed. The synthetic scenario engine can use a fixed seed. Model outputs can be cached for exact document reproduction. This would allow investigators to distinguish numerical changes from model changes.

Monitoring should separate host health from simulation telemetry. The current design intentionally feeds CPU and RAM into the simulator, but production monitoring should also track these values independently for service reliability. Alerts about actual memory pressure should not be based on binary entropy. Standard thresholds for available memory, swap, load average, disk, and process health remain necessary.

The terminal is appropriate for a research prototype. For multi-user deployment, an API should expose typed requests and responses. Authentication, rate limits, request size limits, audit logs, and task queues would be needed. Model calls should be cancellable. The bounded scheduler should propagate cancellation and stop conditions to all agents.

Persistence requires careful separation. Weaviate can store vector memory, but run manifests, structured snapshots, parsed agent outputs, and validation reports are better stored in a relational or document database. Large raw transcripts and code artifacts can be stored in object storage with hashes. The memory index should refer to these immutable artifacts rather than duplicate full text.

Document generation, such as this paper, can become part of the pipeline. A report command could assemble figures, equations, parsed outputs, code hashes, and appendices into DOCX or PDF. The present monograph demonstrates that the artifact contains enough structured information for automated technical reporting, but it also shows the need for layout verification and explicit source notes.''')

# 30 scientific communication
h=doc.add_heading('30. Scientific Communication and Responsible Interpretation',level=1)
add_body(doc, '''The language used to describe the system strongly influences how readers interpret it. Terms such as quantum, nonlocal, Gamma, Sync, and Rainbow can sound physically authoritative. In this artifact they are names for computational structures and projections. Scientific communication should state that clearly near every domain prediction. The most accurate phrase is “quantum-inspired classical simulation with deterministic information-band projection.”

Provenance labels should be concise and consistent. OBSERVED should mean directly supplied measurement or verified external data. RETRIEVED should identify a source and timestamp. INFERRED should mean a model-derived conclusion from supplied evidence. SYNTHETIC should mean generated scenario data. SIMULATOR should mean a numerical value computed from the internal state. UNKNOWN should be reserved for fields that are genuinely optional; a task that explicitly requests synthetic completion should not use UNKNOWN for required variables.

The turnout case study should be communicated as a synthetic planning exercise. The repeated 46–49 percent base range is a result of the prompt pipeline, not a poll aggregate or official forecast. The Rainbow predictive-stability score is not the probability that turnout will fall in that range. The scenario weights are not calibrated event probabilities. These distinctions do not make the exercise meaningless; they define what it can and cannot support.

Visualizations should reinforce provenance. A chart of turnout ranges should include “synthetic” in the title or caption. A chart of purity and entropy can be labeled “simulator metrics.” A table should not place synthetic turnout and measured CPU values in the same column without origin labels. The figures in this paper separate host telemetry, internal state, Rainbow projection, and turnout scenarios.

The model should avoid false precision. Nine decimal places are appropriate for reproducibility of a simulator metric but not for a synthetic turnout forecast. The final turnout report should use sensible rounding, such as a percentage range and voter counts in millions. Conversely, source appendices should preserve exact values. Different sections of a research record have different precision needs.

Responsible interpretation also requires documenting failure. The UNKNOWN-heavy final output is included rather than hidden because it explains the prompt-routing bug. The step-7 scenario drift is reported rather than averaged away. The validator mismatch is described. A credible research paper should treat these defects as findings.

The broader lesson is that simulation and explanation should be modular. Numerical code should compute values, domain models should generate scenarios, language models should explain and format, validators should enforce structure, and provenance should follow every field. When these responsibilities blur, polished language can conceal unsupported assumptions. When they are separated, imaginative frameworks such as Rainbow Spectrum Simulation Information Theory can be explored without overstating their scientific status.''')


# 31 turnout agent specification
h=doc.add_heading('31. Domain-Specific Turnout Agent Specification',level=1)
doc.add_heading('31.1 Routing contract',level=2)
add_body(doc, '''The final repair proposed by this paper is a dedicated turnout-only agent path. The route should be selected whenever the command explicitly contains turnout-summary, turnout-simulate, or an equivalent typed request. The router should not send the packet through the generic multi-domain risk summarizer. It should instead create a TurnoutRun object that contains the original request, a fixed seed, simulation configuration, parsed observer reports, a compact trajectory summary, selected Rainbow metrics, and explicit exclusions. The route identifier should be printed before execution so the user can verify that the correct schema was selected.

The routing contract should state that the task concerns participation volume only. Candidates, parties, vote shares, winners, seats, and control of institutions are excluded. The agent should not infer them, mention them in scenarios, or include empty fields for them. It should also omit road, food, water, health, infrastructure, and generic risk sections unless the user explicitly asks how those factors influence turnout. Even then, they should appear as turnout drivers rather than as independent scorecards.

The route should distinguish three evidence modes. In grounded mode, the packet contains timestamped external turnout-related data. In hybrid mode, some variables are observed and others are synthetic. In synthetic mode, all domain inputs are generated under documented assumptions. The simulator state and Rainbow projection are always labeled SIMULATOR because they are internal numerical values. The route must never promote SIMULATOR values to OBSERVED election evidence.

The output contract should prohibit required UNKNOWN fields. If a required turnout variable is absent, the numerical scenario engine generates a synthetic value. Optional explanatory fields may be omitted rather than filled with UNKNOWN. This is a crucial distinction: the user asked the system to simulate missing data, so an UNKNOWN response violates the task. The correct response is a bounded synthetic estimate with origin, distribution, center, range, and sensitivity.''')

doc.add_heading('31.2 Structured input model',level=2)
add_body(doc, '''The TurnoutRun input model should begin with identity and provenance. Fields include run_id, schema_version, application_version, source_hash, transcript_hash, seed, evidence_mode, generated_at, model_identifier, prompt_hashes, and simulation configuration. The original request should be preserved verbatim. Exclusions should be stored as a machine-readable set. This metadata makes the result auditable and prevents a later summarizer from silently changing scope.

The domain-input section should contain VEP, registration, conversion, voting modes, enthusiasm, competitiveness, mobilization, demographics, access, transportation, weather, infrastructure shocks, ballot rejection, provisional ballots, and state dispersion. Each variable should be an object with origin, distribution, parameters, range, central value, unit, update time, and source reference if observed. A covariance or dependency graph should describe relationships among variables.

Observer reports should be parsed before entering the agent. Instead of passing thousands of lines of analysis, the parser should extract step, dominant basis, purity, entropy, fidelity, gap, QFI summary, mutual-information summary, Rainbow bands, predictive stability, low/base/high turnout ranges, voter-count ranges, scenario weights, drivers, and sensitivity. Any field that cannot be parsed should generate a validation error rather than being silently dropped.

Trajectory compression should preserve dispersion. The agent needs medians, means, standard deviations, minima, maxima, and step-to-step transitions for selected simulator metrics and turnout scenario centers. It should also know whether retrieved memory is independent external evidence or a prior output from the same run. Self-generated memory should be marked recursive and excluded from evidence counts.

The numerical scenario engine should be invoked before the language model. Its output should contain Monte Carlo draws or sufficient summary statistics. For each scenario, it should provide a turnout distribution, voter-count distribution, driver values, and covariance diagnostics. The language model then explains these results. This architecture removes the requirement that a text model invent every number while still allowing natural-language interaction.''')

add_table(doc,['Required turnout variable','Suggested synthetic representation','Primary effect'],[
['Voting-eligible population','Truncated normal or bounded triangular distribution','Converts turnout rate into voter count'],
['Registration rate','Beta distribution','Sets the registered share of VEP'],
['Registration-to-ballot conversion','Logistic-normal conditional distribution','Direct participation conversion'],
['Early/mail/Election Day composition','Dirichlet distribution','Allocates exposure to mode-specific effects'],
['Mail return and rejection','Beta distributions','Adjusts counted mail ballots'],
['Enthusiasm','Correlated beta index','Raises or lowers conversion'],
['Competitiveness','Bounded nonlinear index','Affects perceived stakes'],
['Mobilization','Correlated beta index with diminishing returns','Changes contact and participation'],
['Access friction','Composite [0,1] index','Reduces conversion and raises dispersion'],
['Weather disruption','Regional shock distribution','Primarily affects in-person modes'],
['Demographic participation','Latent factors plus state random effects','Creates heterogeneous participation'],
['State dispersion','Hierarchical random effects','Maps national assumptions into regional variation'],
])

doc.add_heading('31.3 Scenario construction',level=2)
add_body(doc, '''Low, base, and high scenarios should be derived from the joint distribution rather than written independently. One method is to compute a turnout score for each Monte Carlo draw and divide the draws into lower, middle, and upper regions. Scenario weights are the fraction of draws in each region. A second method is to define coherent conditional regimes and assign prior weights. The transcript uses fixed weights of 0.25, 0.55, and 0.20. A redesigned engine may preserve those weights as a regression mode while allowing data-driven weights in calibrated mode.

Each scenario should report a central turnout rate, an interval, a voter-count interval, and the conditional means of major drivers. The low scenario should not simply subtract a constant from the base case; it should reflect a coherent combination such as lower conversion, weaker enthusiasm, higher access friction, and greater disruption. The high scenario should reflect the opposite combination without pushing variables outside plausible synthetic bounds.

Correlations must be honored. Enthusiasm, competitiveness, and mobilization may move together. Early voting may reduce sensitivity to Election Day weather. Access friction may interact with transportation and polling-place availability. Registration and conversion are not independent because a highly registered population may include marginal registrants with different conversion behavior. The simulation engine should encode these relationships explicitly.

Scenario intervals should reflect both within-scenario variability and between-step simulator uncertainty. One approach is to calculate turnout quantiles from the synthetic engine and then widen them by a factor based on black mass, spectrum entropy, and cross-run dispersion. Predictive stability can reduce the additional width but should never eliminate the underlying domain uncertainty. The formula and bounds should be documented.

The transcript provides an example. Four of five steps place the base scenario at 46–49 percent VEP, while the fifth places it at 48–52 percent. A consensus agent could treat 46–49 as the modal base interval and 48–52 as an upward sensitivity branch. It could set a central estimate around 47.5 or 48.0 percent and report a broader uncertainty envelope. The decision should be arithmetic and reproducible, not a free-form choice by the final model.''')

add_equation(doc,'w_s = n_s / N_MC,    Σ_s w_s = 1','44')
add_equation(doc,'CI_adjusted = CI_domain ⊕ κ(H_spec, BLACK, dispersion)','45')

doc.add_heading('31.4 RGB and Rainbow integration',level=2)
add_body(doc, '''The quantum-inspired simulator should influence the turnout report only through clearly defined internal diagnostics. The five-register state can provide a trajectory fingerprint. Purity and spectral gap describe concentration; fidelity describes step-to-step continuity; QFI describes internal sensitivity; mutual information describes coupling; Rainbow bands compress these values. These metrics can determine whether the internal simulation is stable enough to summarize.

A simple integration policy is to leave scenario central values unchanged and use predictive stability to classify output stability. For example, stability below 0.50 could be LOW, 0.50–0.75 MEDIUM, and above 0.75 HIGH. Spectrum entropy and black mass could widen the displayed interval. Cyan and blue could indicate high observability and structured information within the simulator. None of these values should be described as voter evidence.

A more experimental policy could use the RGB state to select among precomputed synthetic scenarios, but that mapping must be explicit and tested. R could index adverse conditions, G central conditions, and B favorable conditions; Gamma could control nonlinear interaction strength; Sync could control aggregation. The current observer implicitly makes this mapping, but it does so in prose. Moving it into code would make the experiment reproducible.

The agent should print a separate SIMULATOR_DIAGNOSTICS section after the turnout result. This section may contain dominant basis, dominant band, spectrum entropy, spectrum coherence, band divergence, predictive stability, mean RGB QFI, and Gamma-Sync information. It should state that these values characterize the simulation pipeline. The turnout result should appear first so the user does not have to search through quantum metrics.

The initial fusion state in the transcript has predictive stability near 0.492, while step 3 rises to about 0.825. That change can be reported as increased internal stability after the turnout loop is configured. It should not be translated into a jump in turnout probability. The separation of result and diagnostics is therefore both a communication and modeling requirement.''')

doc.add_heading('31.5 Turnout critic',level=2)
add_body(doc, '''The turnout critic should be narrower than the generic risk critic. Its first task is scope enforcement. It checks that no candidate, party, winner, vote-share, seat, or institutional-control content appears. Its second task is provenance. Every generated election value must be SYNTHETIC unless accompanied by a referenced external source. Its third task is arithmetic. It verifies that turnout percentages and voter counts are consistent with VEP assumptions.

The critic should verify scenario structure. Low bounds must not exceed high bounds. Scenario weights must lie in [0,1] and sum to one within tolerance. The base scenario should normally receive the largest weight if the output labels it most likely. Central estimates must fall inside the stated most-likely interval. Voter counts should be rounded consistently.

The critic should check overlap and double counting among drivers. If enthusiasm, competitiveness, and mobilization are correlated, the explanation should not add their effects as independent percentages. If weather effects are conditioned on Election Day share, the model should not also subtract the full weather effect from mail voting. A dependency graph can support this audit.

The critic should compare step outputs. If one step shifts materially, it should require the final report to mention the divergence. In the supplied run, step 7 is an upward sensitivity case. Suppressing it would overstate consensus; allowing it to replace the modal result would overreact to one step. The critic should recommend a consensus rule.

The critic should reject false precision and unsupported confidence. A synthetic scenario can have internal stability but not empirical calibration. Confidence should therefore refer to the coherence of assumptions and the stability of the generated distribution, not to the real election outcome. The final report can say “medium internal scenario confidence” while explicitly stating that empirical confidence is not assessed.''')

doc.add_heading('31.6 Final output schema',level=2)
add_body(doc, '''The final turnout schema should be short enough for practical use and detailed enough for audit. It begins with system, version, mode, seed, data origin, election, target, denominator, and time horizon. The primary forecast contains the most-likely turnout interval, central estimate, voter-count interval, central voter count, and internal confidence. The scenario section contains low, base, and high objects with weights, intervals, counts, and conditions.

A synthetic-input summary follows. It should list VEP, registration, conversion, voting-mode shares, enthusiasm, competitiveness, mobilization, access friction, weather disruption, and demographic participation. A full variable table can be saved as an attachment or memory record. The output should include principal drivers with direction and sensitivity, uncertainty decomposition, simulator diagnostics, and the next real data needed to replace assumptions.

The final summary sentence should be direct. Based on the supplied run, an appropriate synthetic summary is: “The modal synthetic base scenario is 46–49 percent of the voting-eligible population, approximately 122–132 million voters under a 265–270 million VEP assumption, with a 0.55 scenario weight; step 7 provides an upward sensitivity case.” This sentence states the result, assumptions, and divergence without claiming empirical accuracy.

The output should not include UNKNOWN in required fields. It should not repeat the complete quantum report. It should not include unrelated risks. It should not call scenario weights probabilities unless they were derived from a numerical distribution. It should not describe predictive stability as election confidence. These negative requirements are as important as the positive fields.

The terminal could support two views. The default turnout-summary command returns the compact final schema. A turnout-debug command returns the synthetic variable table, covariance summary, per-step parsed values, critic findings, and simulator diagnostics. This keeps routine use concise while preserving research transparency.''')

add_table(doc,['Output block','Required content'],[
['IDENTITY','System, schema version, mode, seed, run ID, data origin'],
['TARGET','Election, national turnout, VEP denominator, horizon'],
['PRIMARY_FORECAST','Most-likely interval, central estimate, voter-count range, internal confidence'],
['SCENARIOS','Low/base/high weights, ranges, counts, conditions'],
['SYNTHETIC_INPUTS','Central assumptions and distribution summaries'],
['DRIVERS','Direction, sensitivity, dependence notes'],
['UNCERTAINTY','Domain, simulation, language, and step-drift components'],
['SIMULATOR_DIAGNOSTICS','Basis, Rainbow bands, entropy, coherence, divergence, stability'],
['NEXT_DATA','Highest-value real inputs that would replace synthetic assumptions'],
['EXCLUSIONS','No candidates, parties, winners, vote shares, seats, or control'],
])

doc.add_heading('31.7 Acceptance tests',level=2)
add_body(doc, '''The turnout route is complete when it passes acceptance tests. Given the supplied transcript, the parser should identify five reports and extract the correct step numbers. It should recover the modal base interval of 46–49 percent, the repeated base voter-count range of 122–132 million, and the scenario weights 0.25, 0.55, and 0.20. It should identify the step-7 base interval of 48–52 percent as a deviation.

The validator should confirm that weights sum to one, that 46–49 percent of a 265–270 million VEP is arithmetically compatible with 122–132 million voters, and that the central estimate lies inside the base range. It should confirm that all election values are labeled synthetic. It should reject any output containing road, food, water, party, winner, seat, or control fields.

The simulator-diagnostic parser should extract dominant basis, purity, entropy, fidelity, gap, QFI, mutual information, resource telemetry, and Rainbow values. It should not require BOUNDARY when the schema uses MODE. It should allow exactly one reply-template wrapper. It should reject unresolved angle-bracket placeholders.

A deterministic replay test should use a fixed seed and recorded telemetry. The numerical snapshots and synthetic scenario table should match exactly. The language explanation may be cached or compared structurally. A robustness test should vary the model temperature or replicate count and ensure that parsed central estimates remain within a defined tolerance.

The final acceptance criterion is user utility. The first screen of output should answer the turnout question. Detailed diagnostics can follow. If a user must scroll through unrelated UNKNOWN fields to find the result, the route has failed even if every agent followed its prompt. Domain alignment is therefore a functional requirement, not merely a stylistic preference.''')

# 32 Worked turnout synthesis
h=doc.add_heading('32. Worked Synthetic Turnout Synthesis',level=1)
add_body(doc, '''This section demonstrates how the proposed turnout-only agent would synthesize the supplied five-step run. The exercise uses only values already present in the transcript. It does not add external election data. The first task is to parse the scenario ranges. Steps 3 and 4 each report low 43–45, base 46–49, and high 50–53 percent of VEP. Step 5 reports low 42–45, base 46–49, and high 50–53. Step 6 reports low 43–46, base 46–49, and high 49–52. Step 7 reports low 44–47, base 48–52, and high 53–56. The modal base range is therefore 46–49 percent, appearing in four of five reports.

The second task is to aggregate central values. Low-scenario centers are 44.0, 44.0, 43.5, 44.5, and 45.5 percent. Base centers are 47.5, 47.5, 47.5, 47.5, and 50.0 percent. High centers are 51.5, 51.5, 51.5, 50.5, and 54.5 percent. The base median is 47.5 percent and the base mean is 48.0 percent. Because the fifth report is the only upward shift and because the first four reports agree, a consensus rule should select 47.5 percent as the central synthetic estimate and preserve 48–52 percent as an upward sensitivity branch.

The third task is to apply the VEP assumption. The transcript repeatedly uses a synthetic 265–270 million VEP envelope. The central VEP is 267.5 million. Multiplying 47.5 percent by 267.5 million yields approximately 127.1 million voters. The Cartesian product of the modal base bounds yields a broad count range from 0.46×265 = 121.9 million to 0.49×270 = 132.3 million. Rounding produces the repeated 122–132 million range.

The fourth task is to preserve scenario weights. Low, base, and high weights are 0.25, 0.55, and 0.20 throughout the main reports. They sum exactly to one. Using representative centers of 44.0, 47.5, and 51.5 percent gives a weighted estimate of 47.25 percent. Using broader centers from the full step set produces a value near the high 47s. The difference between this weighted estimate and the median base center illustrates why the final schema should identify which aggregation rule it uses.

The fifth task is to summarize the simulator state. The dominant basis changes from |10100> at step 3 to |10000> thereafter. Purity oscillates between approximately 0.722 and 0.754. Entropy oscillates between approximately 0.911 and 1.020. Fidelity rises across the run. R-G mutual information remains the strongest coupling, and Gamma-Sync remains weak. The Rainbow projection at step 3 has high green, cyan, blue, and white values and predictive stability around 0.825. These observations support the statement that the internal simulation is coherent, but they do not alter the turnout arithmetic.

The sixth task is to represent uncertainty. The modal base interval is three percentage points wide. The full base envelope across steps extends from 46 to 52 percent. A concise report can therefore provide a most-likely interval of 46–49 percent, a central estimate of 47.5 percent, and an upward sensitivity interval of 48–52 percent. The full low-to-high envelope across all steps is 42–56 percent, but presenting that entire span as one confidence interval would blur scenario meaning. It is better to retain the scenario tree.

The seventh task is to list principal synthetic drivers. The transcript repeatedly names registration-to-ballot conversion, enthusiasm, competitiveness, early voting, mail voting, access constraints, demographic participation, weather, and information uncertainty. The final output can rank registration conversion and enthusiasm/competitiveness as primary, early/mail completion and access as secondary, and weather as a conditional disruption. Because no coefficients are supplied, the report should not assign exact percentage-point effects beyond the transcript's broad two-to-four-point sensitivity language.

A compact worked output would therefore state: the modal synthetic base scenario for 2026 U.S. midterm turnout is 46–49 percent of VEP, approximately 122–132 million voters under a 265–270 million VEP assumption, with a synthetic central estimate near 47.5 percent or 127.1 million voters. The low, base, and high scenario weights are 0.25, 0.55, and 0.20. Step 7 supplies an upward sensitivity case of 48–52 percent. Internal RGB/Rainbow diagnostics are stable enough to summarize the run, but they are not empirical evidence.

This synthesis is more useful than the generic risk output because every field answers the requested question. It also retains the important caveats without replacing required values with UNKNOWN. The worked example demonstrates that the source transcript already contains enough information for a complete turnout-only report; the missing element is a domain-specific parser and formatter.''')
add_equation(doc,'T̄_base = median(47.5,47.5,47.5,47.5,50.0) = 47.5%','46')
add_equation(doc,'N̄ = 0.475 × 267.5 = 127.0625 million','47')
add_equation(doc,'T_weighted = .25(44.0) + .55(47.5) + .20(51.5) = 47.425%','48')
add_table(doc,['Synthetic result','Worked value'],[
['Most-likely turnout interval','46–49% of VEP'],
['Central turnout estimate','47.5% of VEP'],
['Assumed VEP envelope','265–270 million'],
['Central voter count','Approximately 127.1 million'],
['Most-likely voter-count range','Approximately 122–132 million'],
['Scenario weights','Low 0.25; Base 0.55; High 0.20'],
['Upward sensitivity case','48–52% of VEP at step 7'],
['Primary synthetic drivers','Registration conversion, enthusiasm, competitiveness, early/mail voting, access, demographics, weather'],
['Simulator interpretation','Internally stable simulation state; not empirical turnout evidence'],
])

# 33 contribution summary
h=doc.add_heading('33. Consolidated Contributions of the Study',level=1)
add_body(doc, '''The study makes five consolidated contributions. First, it converts a large single-file prototype into an explicit layered architecture. The source is shown to contain utilities, telemetry, budgets, a reservoir, a scheduler, a five-register density-matrix simulator, a memory subsystem, a streamed model client, orchestration logic, and a terminal. This decomposition provides a roadmap for refactoring the prototype into testable modules without changing its conceptual design.

Second, the study reconstructs the mathematical model directly from implementation details. It documents state normalization, density-matrix evolution, purity, entropy, fidelity, spectral gaps, Bloch vectors, mutual information, negativity, QFI, host-derived binary entropy, reservoir dynamics, and the complete deterministic Rainbow mapping. The equations make the named spectrum bands auditable. They also show exactly which internal metrics raise or lower each band.

Third, the study provides an execution-trace analysis. It extracts the five reported simulator steps, resource values, state diagnostics, QFI hierarchy, mutual-information hierarchy, Rainbow state, and synthetic turnout scenarios. The visualizations show oscillation rather than monotonic convergence, stable relative register behavior, and a clear scenario consensus with one upward deviation. This is a more precise account than a narrative reading of the terminal alone.

Fourth, the study diagnoses the UNKNOWN bug as a schema-routing defect. The observer already produced turnout predictions. The generic final risk agent inserted unrelated domains because its prompt required them. The fixed validator also expected BOUNDARY while current templates used MODE. These findings lead to concrete engineering repairs: domain-specific routing, typed schemas, versioned validation, parsed numeric fields, provenance-aware memory, and one-time reply wrapping.

Fifth, the study specifies a complete turnout-only synthetic pipeline. It defines the required variables, suggested distributions, correlation structure, scenario construction, RGB/Rainbow integration policy, critic responsibilities, final schema, arithmetic checks, and acceptance tests. It demonstrates a worked synthesis from the supplied transcript: a modal 46–49 percent VEP base range, a central estimate near 47.5 percent, roughly 122–132 million voters under the synthetic VEP envelope, and an upward sensitivity branch at step 7.

Taken together, these contributions turn the artifact from an experimental terminal script into a documented research platform. The complete code and transcript ensure that readers can inspect the original material, while the main text provides a mathematical, architectural, and methodological interpretation. The result is intentionally balanced: it recognizes the originality and engineering depth of the simulator without presenting its synthetic outputs as external measurements.''')

# 34 reading guide
h=doc.add_heading('34. Reading and Reuse Guide',level=1)
add_body(doc, '''Readers interested primarily in implementation should begin with Chapters 2, 6, 7, 8, 9, 10, and 24, then consult Appendix A. Readers focused on mathematics should begin with Chapters 3 through 5, 11, 12, and 25. Readers focused on the synthetic turnout case study should read Chapters 15 through 18, 27, 31, and 32 before examining Appendix B. The complete transcript is intentionally retained because it shows both successful outputs and schema failures.

The figures may be reused as design references for a future implementation, but the numerical turnout values should remain labeled synthetic. The equations describing the density matrix, information measures, resource entropy, reservoir, and deterministic Rainbow projection are direct reconstructions of the supplied design. The proposed turnout distributions and validation procedures are research recommendations rather than features already present in v14.

A practical development sequence is to preserve the current quantum core, move synthetic numerical generation into Python, add typed schemas, fix versioned validation, introduce provenance-aware retrieval, and create a turnout-only route. Once those changes are complete, the supplied transcript can serve as a regression fixture. The monograph and appendices together provide the source record, expected behaviors, identified defects, and acceptance criteria needed for that work.''')

# Appendix C before huge appendices
h=doc.add_heading('Appendix C. Selected Derived Tables and Formula Summary',level=1)
add_table(doc,['Metric','Step 3','Step 4','Step 5','Step 6','Step 7'],[
['Purity']+[f'{x:.6f}' for x in purity],['Von Neumann entropy']+[f'{x:.6f}' for x in vn_entropy],['Spectral gap']+[f'{x:.6f}' for x in gap],['Fidelity']+[f'{x:.6f}' for x in fidelity],['CPU %']+[f'{x:.1f}' for x in cpu],['RAM %']+[f'{x:.1f}' for x in ram],['Resource entropy']+[f'{x:.6f}' for x in resource_entropy],['Entropy injection']+[f'{x:.6f}' for x in injection],])
add_table(doc,['Band','Initial fusion-state','Step 3 turnout loop'],[[k,f'{initial_bands[k]:.6f}',f'{step3_bands[k]:.6f}'] for k in initial_bands])
add_source_note(doc,'All values in Appendix C are transcribed or derived from the supplied terminal log. Turnout values remain synthetic.')

# References
h=doc.add_heading('References',level=1)
refs=[
'[1] C. E. Shannon, “A Mathematical Theory of Communication,” Bell System Technical Journal, 1948.',
'[2] J. von Neumann, Mathematical Foundations of Quantum Mechanics, English edition, Princeton University Press, 1955.',
'[3] M. A. Nielsen and I. L. Chuang, Quantum Computation and Quantum Information, 10th Anniversary Edition, Cambridge University Press, 2010.',
'[4] T. M. Cover and J. A. Thomas, Elements of Information Theory, 2nd ed., Wiley, 2006.',
'[5] DysonSphereGamma Quantum RGB Hypercore v14.0.0, supplied Python source artifact, reproduced in Appendix A.',
'[6] DysonSphereGamma v14 terminal execution transcript, supplied artifact, reproduced in Appendix B.'
]
for r in refs: doc.add_paragraph(r,style='Body Text')

# Appendix A landscape
secA=doc.add_section(WD_SECTION.NEW_PAGE); secA.orientation=WD_ORIENT.LANDSCAPE; secA.page_width,secA.page_height=secA.page_height,secA.page_width
secA.top_margin=Inches(0.35); secA.bottom_margin=Inches(0.35); secA.left_margin=Inches(0.45); secA.right_margin=Inches(0.45)
h=doc.add_heading('Appendix A. Complete Python Source Code',level=1)
add_source_note(doc,'Verbatim source content from the supplied v14 file. Word may wrap long physical lines for page fit; no source text has been omitted.')
for i,line in enumerate(code_text.splitlines(),1):
    p=doc.add_paragraph(style='Code Line'); p.paragraph_format.keep_together=False; p.paragraph_format.keep_with_next=False
    r=p.add_run(f'{i:04d}  {line}'); r.font.name='Liberation Mono'; r.font.size=Pt(5.5)

# Appendix B landscape
secB=doc.add_section(WD_SECTION.NEW_PAGE); secB.orientation=WD_ORIENT.LANDSCAPE; secB.page_width,secB.page_height=secB.page_height,secB.page_width
secB.top_margin=Inches(0.35); secB.bottom_margin=Inches(0.35); secB.left_margin=Inches(0.45); secB.right_margin=Inches(0.45)
h=doc.add_heading('Appendix B. Complete Terminal Transcript',level=1)
add_source_note(doc,'Verbatim transcript content from the supplied run log. Word may wrap long physical lines for page fit; no transcript text has been omitted.')
for i,line in enumerate(log_text.splitlines(),1):
    p=doc.add_paragraph(style='Code Line'); p.paragraph_format.keep_together=False; p.paragraph_format.keep_with_next=False
    r=p.add_run(f'{i:04d}  {line}'); r.font.name='Liberation Mono'; r.font.size=Pt(5.5)

# Update headers/footers for all sections
for section in doc.sections:
    hp=section.header.paragraphs[0]
    if not hp.text:
        hp.text='RGB Rainbow Quantum Simulation Information Theory'
    hp.alignment=WD_ALIGN_PARAGRAPH.CENTER
    for r in hp.runs: r.font.size=Pt(8); r.font.color.rgb=RGBColor(100,100,100)
    fp=section.footer.paragraphs[0]
    if not fp.text and len(fp._p)==0: add_page_number(fp)

# Core properties
doc.core_properties.title='RGB Rainbow Quantum Simulation Information Theory'
doc.core_properties.subject='Technical monograph, mathematical formalization, code, and complete execution transcript'
doc.core_properties.author='OpenAI — prepared from user-supplied artifacts'
doc.core_properties.keywords='RGB, Rainbow Spectrum, quantum simulation, information theory, synthetic turnout, Python'
doc.core_properties.comments='Complete source and transcript included as appendices.'

doc.save(OUT)

# Word count estimate (all paragraph text + table text)
words=[]
for p in doc.paragraphs: words.extend(p.text.split())
for table in doc.tables:
    for row in table.rows:
        for cell in row.cells:
            for p in cell.paragraphs: words.extend(p.text.split())
print(f'Wrote {OUT}')
print(f'Approx DOCX word count: {len(words):,}')
print(f'Sections: {len(doc.sections)}, paragraphs: {len(doc.paragraphs)}, tables: {len(doc.tables)}')
