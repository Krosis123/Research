"""Editable, vector-first paper figures grounded in the integrated 0.2.4 source."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle, Polygon
import numpy as np

OUT = Path(__file__).resolve().parent
NAVY='#142D4E'; BLUE='#2774AE'; TEAL='#087F8C'; GOLD='#B77A18'; GRAY='#516174'
plt.rcParams.update({'font.family':'DejaVu Sans','svg.fonttype':'none','pdf.fonttype':42})

def canvas(w,h,xmax,ymax):
    fig,ax=plt.subplots(figsize=(w,h)); fig.subplots_adjust(left=.02,right=.98,bottom=.02,top=.98)
    ax.set(xlim=(0,xmax),ylim=(0,ymax)); ax.axis('off'); return fig,ax
def txt(ax,x,y,s,size=12,color=NAVY,weight='normal',ha='center'):
    ax.text(x,y,s,fontsize=size,color=color,weight=weight,ha=ha,va='center',linespacing=1.45)
def box(ax,x,y,w,h,title,body='',color=BLUE,fs=11):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.02,rounding_size=0.15',facecolor=color+'0D',edgecolor=color,lw=1.4))
    if body:
        txt(ax,x+w/2,y+h-.28,title,fs+2,color,'bold'); txt(ax,x+w/2,y+h/2-.20,body,fs)
    else: txt(ax,x+w/2,y+h-.38 if h>3 else y+h/2,title,fs,color,'bold')
def arrow(ax,pts,label=None,color=GRAY):
    for a,b in zip(pts[:-2],pts[1:-1]): ax.plot([a[0],b[0]],[a[1],b[1]],color=color,lw=1.4)
    ax.add_patch(FancyArrowPatch(pts[-2],pts[-1],arrowstyle='-|>',mutation_scale=13,color=color,lw=1.4))
    if label:
        a,b=pts[0],pts[1]; txt(ax,(a[0]+b[0])/2,(a[1]+b[1])/2+.15,label,9,color)
def diamond(ax,x,y,w,h,s):
    ax.add_patch(Polygon([(x,y+h/2),(x+w/2,y),(x,y-h/2),(x-w/2,y)],facecolor='#FFF8E9',edgecolor=GOLD,lw=1.4))
    txt(ax,x,y,s,10,NAVY,'bold')
def save(fig,name):
    for ext in ('svg','pdf','png'): fig.savefig(OUT/f'{name}.{ext}',dpi=300,facecolor='white')
    fig.savefig(OUT/f'{name}_preview.png',dpi=100,facecolor='white'); plt.close(fig)

fig,ax=canvas(16,9,16,9)
txt(ax,.35,8.55,'ATLANTIS + adaptive quantum attractor discovery',25,weight='bold',ha='left')
txt(ax,.35,8.05,'From regulatory rules to verified dynamical attractors and interpretable landscapes',13,GRAY,ha='left')
box(ax,.35,2.25,3.05,5.1,'REGULATORY MODEL',color=BLUE)
coords=[(1,6.15),(2.65,6.1),(1.3,5.05),(2.55,4.7)]
for a,b in [(0,1),(1,3),(3,2),(2,0),(0,3)]: arrow(ax,[coords[a],coords[b]],color=BLUE)
for i,(x,y) in enumerate(coords):
    ax.add_patch(Circle((x,y),.24,color='white',ec=BLUE,lw=1.5)); txt(ax,x,y,f'$g_{i+1}$',12)
txt(ax,1.875,3.8,'Weights • truth tables\nBoolean expressions',12)
txt(ax,1.875,2.85,'Shared Boolean state model\n'+r'$x\in\{0,1\}^{n},\quad x_{t+1}=F(x_t)$',12,weight='bold')
box(ax,4.05,5.15,4.65,2.2,'CLASSICAL ANALYSIS','Deterministic trajectories + basins\nWeighted-network stochastic dynamics\nFate classification + landscape projection',TEAL,11)
box(ax,4.05,2.25,4.65,2.3,'QUANTUM COMPILATION','Synchronous Boolean update rules\nAlgebraic normal form → reversible gates\n'+r'$U_F: |x,0,\ldots,0\rangle\mapsto|x,F(x),\ldots,F^T(x)\rangle$',BLUE,11)
arrow(ax,[(3.4,6.2),(4.05,6.2)]); arrow(ax,[(3.4,3.4),(4.05,3.4)])
box(ax,9.35,2.25,6.3,5.1,'ADAPTIVE HYBRID DISCOVERY',color=BLUE)
box(ax,9.65,5.25,2.5,1.12,'Count covered states','QPE / labeled reference',BLUE,10)
box(ax,12.75,5.25,2.55,1.12,'Suppress known cycles','Phase-adjusted search',BLUE,10)
box(ax,12.75,3.25,2.55,1.12,'Measure candidates','Terminal register',BLUE,10)
box(ax,9.65,3.25,2.5,1.12,'Verify + update','Classical cycle tracing',TEAL,10)
arrow(ax,[(12.15,5.81),(12.75,5.81)]); arrow(ax,[(14.025,5.25),(14.025,4.37)])
arrow(ax,[(12.75,3.81),(12.15,3.81)]); arrow(ax,[(10.9,4.37),(10.9,5.25)])
txt(ax,12.5,2.65,'Discover → verify → exclude → repeat',11,weight='bold')
arrow(ax,[(8.7,3.4),(9.35,3.4)])
box(ax,4.05,.5,11.6,1.12,'ATTRACTORS • BASINS / FATES • LANDSCAPES • AUDITABLE EVIDENCE',
    'Classical analysis supplies basins and landscapes; quantum discovery supplies verified cycles and measurement history.',TEAL,10)
arrow(ax,[(6.3,5.15),(6.3,4.85),(8.98,4.85),(8.98,1.62)])
arrow(ax,[(12.5,2.25),(12.5,1.62)])
txt(ax,.4,1.28,'Execution options',11,weight='bold',ha='left')
txt(ax,.4,.77,'Ideal reference • Aer\nIBM execution interface',10,GRAY,ha='left')
txt(ax,8,.12,'Current implementation: no demonstrated quantum speedup and no live QPU validation. T is user supplied.',9,GRAY)
save(fig,'graphical_abstract')

fig,ax=canvas(16,19,16,22)
txt(ax,.4,21.6,'Adaptive attractor discovery: detailed algorithm',24,weight='bold',ha='left')
txt(ax,.4,21.05,'Integrated ATLANTIS implementation • synchronous Boolean dynamics • source-aligned control flow',12,GRAY,ha='left')
box(ax,.5,18.5,9.3,1.85,'1  INPUT + PREFLIGHT',
    'Network F; user-selected T; engine; counting mode; shots; QPE precision p; budgets\nValidate rules and settings; compile ANF; check qubits, memory and synthesis limits\nReject infeasible requests; require an authorized executor for IBM execution',BLUE,11)
box(ax,10.5,18.5,5,1.85,'NOTATION + RESOURCE MODEL',
    'N = 2ⁿ; C = verified cycles; E = all states in C\nM = number of x with Fᵀ(x) in E\nEvolution: n(T+1) qubits; QPE adds p',GRAY,11)
box(ax,2,16.9,6.3,1.05,'2  INITIALIZE','C = ∅; round r = 0; initialize measurements and audit history',BLUE,10)
arrow(ax,[(5.15,18.5),(5.15,17.95)])
box(ax,2,15.2,6.3,1.1,'3  START ROUND','Check cancellation / deadline; set M = 0',BLUE,11)
arrow(ax,[(5.15,16.9),(5.15,16.3)])
diamond(ax,5.15,14.15,3.6,1.15,'Known cycles C ≠ ∅?')
arrow(ax,[(5.15,15.2),(5.15,14.73)])
box(ax,.5,11.6,9.3,1.6,'4  COVERAGE CHECK + COUNTING',
    'If selected, audit all Fᵀ(x); full coverage → classical certificate\nOtherwise count M by exact enumeration, ideal-QPE reference, or actual QPE\nApply the stopping / validity rules at right before computing suppression',BLUE,11)
arrow(ax,[(5.15,13.575),(5.15,13.2)],'Yes')
arrow(ax,[(3.35,14.15),(.15,14.15),(.15,10.65),(2,10.65)],'No: no suppression')
box(ax,10.5,11.3,5,6.45,'STOPPING / VALIDITY RULES',
    'Classical audit: all N terminals in E\n→ complete_classically_certified\n\nQPE policy + exact M = N\n→ complete_classically_certified\n\nQPE policy + estimated M = N:\nrepeat full-coverage evidence checks\n→ complete_qpe_heuristic if supported\n→ inconclusive otherwise\n\nAny remaining M outside 0 < M < N\n→ inconclusive; do not suppress\n\nBounded policy: no completeness claim',GOLD,10.5)
arrow(ax,[(9.8,12.4),(10.5,12.4)])
box(ax,2,9.85,6.3,1.6,'5  PREPARE SEARCH',
    'If C ≠ ∅, compute β = asin√(M/N)\nJ = max(1, ⌈β/(π − 2β)⌉)\nφ = −2 asin[sin(π/(4J+2)) / cos β]',BLUE,11)
arrow(ax,[(5.15,11.6),(5.15,11.45)],'Continue')
box(ax,.5,7.6,9.3,1.7,'6  EXECUTE + MEASURE',
    'Initialize H⊗ⁿ|0ⁿ⟩; if C ≠ ∅, repeat J times:\nU_F → phase E by −φ → U_F† → H⊗ⁿ P₀(φ) H⊗ⁿ\nApply U_F; measure terminal register with configured shots\nReference mode samples its ideal distribution; circuit modes execute compiled circuits',BLUE,11)
arrow(ax,[(5.15,9.85),(5.15,9.3)])
box(ax,.5,5.6,9.3,1.45,'7  CLASSICALLY VERIFY EACH MEASURED STATE',
    'Bounded trajectory tracing; accept only states belonging to a verified cycle\nCanonicalize cycles; reject transients, unresolved candidates and known cycles\nRetain accepted unseen cycles with their measurement weights',TEAL,11)
arrow(ax,[(5.15,7.6),(5.15,7.05)])
diamond(ax,5.15,4.6,3.5,1.1,'New cycle accepted?')
arrow(ax,[(5.15,5.6),(5.15,5.15)])
box(ax,10.5,6,5,3.75,'SEARCH RETRY PATH',
    'No new verified cycle:\nretry search with the same C and M\n(default: two attempts per round)\n\nAttempts exhausted:\n→ inconclusive_no_new_candidate\n\nRecord invalid / rejected counts',GOLD,11)
arrow(ax,[(6.9,4.6),(13,4.6),(13,6)],'No')
arrow(ax,[(10.5,8.45),(9.8,8.45)],'Retry')
box(ax,2,2.8,6.3,1.15,'8  UPDATE DISCOVERED SET','Select one accepted cycle by measurement weight; add to C; r ← r+1',TEAL,10)
arrow(ax,[(5.15,4.05),(5.15,3.95)],'Yes')
arrow(ax,[(2,3.35),(.25,3.35),(.25,15.75),(2,15.75)])
txt(ax,.38,9.7,'Next round if r < limit',9,GRAY,ha='left')
box(ax,10.5,1.2,5,2.6,'9  AT ROUND LIMIT',
    'Perform a final policy-specific coverage check\nClassical audit / exact count: certify if full\nQPE: repeat supported full-count checks\nOtherwise: inconclusive_round_budget\nExport cycles, status, counts and resources',TEAL,10.5)
arrow(ax,[(8.3,3.35),(10.5,3.35)],'Limit reached')
txt(ax,.5,1.75,'Interpretation',12,weight='bold',ha='left')
txt(ax,.5,.95,'QPE completion remains heuristic; exhaustive certification costs O(2ⁿT).\nExact-M and ideal-QPE references enumerate Fᵀ. Candidate verification is bounded.\nCancellation, deadlines and execution errors are recorded by the job layer.',10,GRAY,ha='left')
save(fig,'algorithm_flowchart')
