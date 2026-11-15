"""Functional scientific figures; all plots are regenerated from analysis data."""
from pathlib import Path
import json,shutil,subprocess,shlex
import numpy as np
import networkx as nx
from matplotlib.figure import Figure
from matplotlib.colors import ListedColormap,LinearSegmentedColormap
from matplotlib import colormaps
from matplotlib.patches import Rectangle,FancyArrowPatch,Ellipse,PathPatch,RegularPolygon,Polygon
from matplotlib.path import Path as MplPath
from .projection import sammon_mapping,natural_neighbor,naive_grid
from .geometry import treemap,group_cyclic


def matlab_colors(name,n):
    """MATLAB's discrete map sampling (not Matplotlib's different jet endpoints)."""
    import colorsys
    t=np.linspace(0,1,n) if n>1 else np.zeros(1)
    if name=='jet':
        k=int(np.ceil(n/4)); u=np.r_[np.arange(1,k+1)/k,np.ones(k-1),np.arange(k,0,-1)/k]
        g=int(np.ceil(k/2))-(n%4==1)+np.arange(1,len(u)+1); r=g+k; b=g-k
        g=g[g<=n]; r=r[r<=n]; b=b[b>=1]; colors=np.zeros((n,3))
        colors[r-1,0]=u[:len(r)]; colors[g-1,1]=u[:len(g)]; colors[b-1,2]=u[-len(b):]
        return colors
    if name=='hot':
        k=int(np.floor(3*n/8)); up=np.arange(1,k+1)/k if k else np.array([])
        return np.column_stack((np.r_[up,np.ones(n-k)],np.r_[np.zeros(k),up,np.ones(n-2*k)],np.r_[np.zeros(2*k),np.arange(1,n-2*k+1)/(n-2*k)]))
    if name=='autumn': return np.column_stack((np.ones(n),t,np.zeros(n)))
    if name=='spring': return np.column_stack((np.ones(n),t,1-t))
    if name=='summer': return np.column_stack((t,.5+.5*t,np.full(n,.4)))
    if name=='winter': return np.column_stack((np.zeros(n),t,1-.5*t))
    if name=='cool': return np.column_stack((t,1-t,np.ones(n)))
    if name=='gray': return np.column_stack((t,t,t))
    if name=='hsv': return np.array([colorsys.hsv_to_rgb(i/n,1,1) for i in range(n)])
    if name=='prism': return np.resize(np.array([[1,0,0],[1,.5,0],[1,1,0],[0,1,0],[0,0,1],[2/3,0,1]]),(n,3))
    p=Path(__file__).parent/'assets'/'parula_base.json'
    if name=='parula' and p.exists():
        a=np.array(json.loads(p.read_text())); return np.column_stack([np.interp(np.linspace(0,1,n) if n>1 else [1],np.linspace(0,1,len(a)),a[:,i]) for i in range(3)])
    return colormaps.get_cmap(name)(np.linspace(0,1,n))[:,:3]


def color_map(name='jet',reverse=False):
    p=Path(__file__).parent/'assets'/'parula.json'
    if name=='parula' and p.exists(): cmap=ListedColormap(json.loads(p.read_text()))
    else: cmap=ListedColormap(matlab_colors(name,100))
    return cmap.reversed() if reverse else cmap


def find_graphviz(engine='dot'):
    local=Path(__file__).resolve().parent.parent/'.graphviz'/'bin'/(engine+'.exe')
    if local.exists(): return str(local)
    path=shutil.which(engine)
    if path: return path
    for base in [Path('C:/Program Files/Graphviz'),Path('C:/Program Files (x86)/Graphviz2.38')]:
        p=base/'bin'/(engine+'.exe')
        if p.exists(): return str(p)
    raise FileNotFoundError('Install Graphviz and add its bin folder to PATH to use Graphviz layouts')


def network_dot(network,labels=True):
    lines=['digraph g {','nodesep=0.4;','node [shape=ellipse,color=white,style=filled,fontsize=20];']
    for i,j in zip(*np.nonzero(network.adjacency)):
        w=network.adjacency[i,j]
        # Match generateDotFile's edge filter and implicit node-creation order;
        # inserting node declarations here changes deterministic Graphviz layouts.
        if network.weights is not None and 0<w<1: continue
        color='blue' if network.rules is not None else ('green' if w>0 else 'red')
        label=(f'+ {w:g} ' if w>0 else f' {w:g} ') if network.weights is not None and labels else ''
        style='bold' if network.weights is not None else 'solid'
        lines.append(f'{json.dumps(network.names[i],ensure_ascii=False)} -> {json.dumps(network.names[j],ensure_ascii=False)} [color={color},style={style},label={json.dumps(label)}];')
    return '\n'.join(lines+['}'])


def graphviz_figure(dot,engine='dot',title='Regulatory Network'):
    result=subprocess.run([find_graphviz(engine),'-Tplain'],input=dot,text=True,capture_output=True,check=True)
    fig=Figure(figsize=(9,7)); ax=fig.add_subplot(); nodes={}; edges=[]; width=height=1.
    for line in result.stdout.splitlines():
        a=shlex.split(line)
        if not a: continue
        if a[0]=='graph': width,height=map(float,a[2:4])
        elif a[0]=='node': nodes[a[1]]=(float(a[2]),float(a[3]),float(a[4]),float(a[5]),a[6],a[-1],a[-3],a[-2])
        elif a[0]=='edge':
            count=int(a[3]); xy=np.array(list(map(float,a[4:4+2*count]))).reshape(-1,2)
            rest=a[4+2*count:]; label=rest[0] if len(rest)>=5 else ''; labelpos=tuple(map(float,rest[1:3])) if len(rest)>=5 else None
            edges.append((xy,rest[-1],label,labelpos))
    for xy,color,label,pos in edges:
        if len(xy)>1 and (len(xy)-1)%3==0:
            codes=[MplPath.MOVETO]+[MplPath.CURVE4]*(len(xy)-1)
            ax.add_patch(PathPatch(MplPath(xy,codes),fill=False,color=color,lw=1.5))
        else: ax.plot(xy[:,0],xy[:,1],color=color,lw=1.5)
        if len(xy)>1: ax.add_patch(FancyArrowPatch(xy[-2],xy[-1],arrowstyle='-|>',mutation_scale=12,color=color))
        if label and pos: ax.text(*pos,label,color=color,ha='center',va='center',fontsize=9)
    for name,(x,y,w,h,label,fill,shape,edge) in nodes.items():
        if shape in ('box','rect','rectangle','square','record','Mrecord'):
            patch=Rectangle((x-w/2,y-h/2),w,h,facecolor=fill,edgecolor=edge,lw=.5)
        elif shape=='diamond':
            patch=Polygon([[x,y+h/2],[x+w/2,y],[x,y-h/2],[x-w/2,y]],facecolor=fill,edgecolor=edge,lw=.5)
        elif shape in ('hexagon','octagon','triangle','pentagon'):
            sides={'hexagon':6,'octagon':8,'triangle':3,'pentagon':5}[shape]
            patch=RegularPolygon((x,y),sides,radius=max(w,h)/2,facecolor=fill,edgecolor=edge,lw=.5)
        else: patch=Ellipse((x,y),w,h,facecolor=fill,edgecolor=edge,lw=.5)
        ax.add_patch(patch)
        ax.text(x,y,label,ha='center',va='center',fontsize=10)
    ax.set(xlim=(-.2,width+.2),ylim=(-.2,height+.2),aspect='equal',title=title); ax.axis('off')
    fig.atlantis_data={'dot':dot,'nodes':nodes}; fig.tight_layout(); return fig


def network_figure(network,layout='spring',labels=True):
    if layout in ('dot','neato','fdp','sfdp','circo','twopi','osage'):
        return graphviz_figure(network_dot(network,labels),layout,network.name)
    g=nx.from_numpy_array(network.adjacency,create_using=nx.DiGraph)
    if network.positions:
        pos={i:np.asarray(network.positions[n]) for i,n in enumerate(network.names)}
    elif layout=='circular': pos=nx.circular_layout(g)
    elif layout=='shell': pos=nx.shell_layout(g)
    else: pos=nx.spring_layout(g,seed=0,weight=None)
    fig=Figure(figsize=(9,7)); ax=fig.add_subplot()
    nx.draw_networkx_nodes(g,pos,ax=ax,node_color='white',edgecolors='black',node_size=1200)
    nx.draw_networkx_labels(g,pos,labels=dict(enumerate(network.names)),ax=ax,font_size=9,font_color=(1/250,1/250,139/250))
    for sign,color,arrow in [(1,'green','-|>'),(-1,'red','-|>')]:
        edges=[(u,v) for u,v in g.edges if np.sign(network.adjacency[u,v])==sign]
        color=(.1/250,.1/250,205/250) if network.rules is not None else ((50/250,205/250,50/250) if sign==1 else (1,1/250,1/250))
        nx.draw_networkx_edges(g,pos,ax=ax,edgelist=edges,edge_color=color,width=[abs(network.adjacency[u,v]) for u,v in edges],arrowstyle=arrow,arrowsize=17,node_size=1200,connectionstyle='arc3,rad=0.08')
    if labels and network.weights is not None:
        nx.draw_networkx_edge_labels(g,pos,ax=ax,edge_labels={(u,v):f'{network.adjacency[u,v]:+g}' for u,v in g.edges},font_size=8)
    ax.set_title(network.name); ax.axis('off'); fig.tight_layout()
    fig.atlantis_data={'positions':{network.names[i]:np.asarray(v).tolist() for i,v in pos.items()}}
    return fig


def landscape_values(states,kind,deterministic=None,probabilistic=None,factor=1):
    lookup={row.tobytes():i for i,row in enumerate(states)}
    if kind=='basin':
        if deterministic is None: raise ValueError('Run deterministic analysis for basin sizes')
        z=np.zeros(len(states))
        for a in deterministic.attractors:
            for row in a.states:
                if row.tobytes() in lookup: z[lookup[row.tobytes()]]=a.basin
        return z,'Basin Sizes','Basin Size Landscape'
    if probabilistic is None: raise ValueError('Run probabilistic analysis first')
    p=probabilistic.probabilities.copy()
    p[p==0]=1000; p[p==1000]=p.min()  # source zero replacement before plotting
    if len(p)!=len(states) or not np.array_equal(states,probabilistic.states):
        z=np.full(len(states),p.min())
        for row,val in zip(probabilistic.states,p):
            if row.tobytes() in lookup: z[lookup[row.tobytes()]]=val
        p=z
    if kind=='probability': return p,'Probabilities','Probability Landscape'
    if kind!='energy': raise ValueError('Unknown landscape type')
    if not isinstance(factor,(int,np.integer)) or factor<1: raise ValueError('Noise reduction factor must be a positive integer')
    with np.errstate(divide='ignore',invalid='ignore'):
        pe=-np.log(p); pe=(pe-pe.max())**factor
        minimum=pe.min()
        
        if minimum==0: raise ValueError('Original potential-energy normalization is undefined for this exponent or a uniform distribution. Select an odd noise-reduction factor and a nonuniform distribution.')
        pe=pe/minimum
    if not np.isfinite(pe).all(): raise ValueError('Potential energies are undefined for this probability distribution')
    return pe,'Normalized Transformed Potential Energies','Potential Energy Landscape'


def landscape_figure(states,kind='basin',deterministic=None,probabilistic=None,mapping='naive',coordinates=None,permutation=None,seed=None,factor=1,cmap='jet',annotate=True,group=False,title=None,progress=None,cancel=None,tooltips=True):
    states=np.asarray(states,dtype=np.uint8)
    z,label,default_title=landscape_values(states,kind,deterministic,probabilistic,factor)
    if mapping=='naive':
        x,y,Z,permutation=naive_grid(states,z,permutation,seed)
        if group and deterministic:
            permutation,Z=group_cyclic(deterministic.attractors,states,permutation,Z)
        coordinates=np.column_stack((x.ravel(order='F'),y.ravel(order='F')))
        pointxy=np.empty((len(states),2))
        for k,i in enumerate(permutation):
            if i<len(states): pointxy[i]=coordinates[k]
    elif mapping=='sammon':
        if coordinates is None: coordinates,_=sammon_mapping(states,progress=progress,cancel=cancel)
        coordinates=np.asarray(coordinates)
        if coordinates.shape!=(len(states),2): raise ValueError('Saved coordinates do not match state count')
        resolution=np.ptp(coordinates[:,0])/np.sqrt(len(states)*4)
        if resolution<=0: raise ValueError('Projection has no horizontal extent')
        xn=np.arange(coordinates[:,0].min(),coordinates[:,0].max()+resolution*1e-8,resolution)
        yn=np.arange(coordinates[:,1].min(),coordinates[:,1].max()+resolution*1e-8,resolution)
        x,y=np.meshgrid(xn,yn)
        Z=natural_neighbor(coordinates,z,np.column_stack((x.ravel(),y.ravel()))).reshape(x.shape)
        pointxy=coordinates
    else: raise ValueError('Mapping must be naive or sammon')
    fig=Figure(figsize=(560/96,420/96),dpi=96); ax=fig.add_subplot(projection='3d')
    # Tessellate the same surface for interpolated coloring. Analysis data and
    # exported grid remain unchanged; no filtering or smoothing is applied.
    draw_x,draw_y,draw_z=x,y,Z
    if min(Z.shape)>1:
        from scipy.ndimage import map_coordinates
        ny=max(Z.shape[0],min(256,(Z.shape[0]-1)*4+1)); nx=max(Z.shape[1],min(256,(Z.shape[1]-1)*4+1))
        rr,cc=np.meshgrid(np.linspace(0,Z.shape[0]-1,ny),np.linspace(0,Z.shape[1]-1,nx),indexing='ij')
        draw_z=map_coordinates(Z,[rr,cc],order=1,mode='nearest')
        draw_x,draw_y=np.meshgrid(np.linspace(x.min(),x.max(),nx),np.linspace(y.min(),y.max(),ny))
    surface=ax.plot_surface(draw_x,draw_y,draw_z,cmap=color_map(cmap,True),edgecolor='none',antialiased=False,rcount=draw_z.shape[0],ccount=draw_z.shape[1],vmin=np.nanmin(Z),vmax=np.nanmax(Z) if np.nanmax(Z)!=np.nanmin(Z) else 1)
    contour=None
    if min(Z.shape)>=2 and np.isfinite(Z).any() and np.nanmax(Z)!=np.nanmin(Z):
        contour=ax.contour(x,y,Z,zdir='z',offset=0,cmap=color_map(cmap,True),linewidths=.6)
    fig.colorbar(surface,ax=ax,shrink=.65,pad=.08)
    ax.set(xlabel='States',ylabel='States',zlabel=label,title=title or default_title,zlim=(0,1.08))
    ax.set_zlabel(label,fontsize=8,labelpad=3)
    ax.title.set_fontweight('bold'); ax.title.set_fontsize(11)
    for axis in (ax.xaxis,ax.yaxis): axis.set_rotate_label(False); axis.label.set_rotation(0)
    ax.set_xticklabels([]); ax.set_yticklabels([]); ax.view_init(elev=30,azim=-127.5)
    for axis in (ax.xaxis,ax.yaxis,ax.zaxis): axis.set_pane_color((1,1,1,0))
    lookup={row.tobytes():i for i,row in enumerate(states)}
    marks=[]; arrows=[]
    if annotate and deterministic:
        for k,a in enumerate(deterministic.attractors,1):
            indices=[lookup[r.tobytes()] for r in a.states if r.tobytes() in lookup]
            if not indices: continue
            xy=pointxy[indices]; zz=z[indices]
            mark=ax.scatter(xy[:,0],xy[:,1],zz+.005,c=[(.8216,.2176,.8137)],marker='*',s=120,linewidths=2,label='Attractor States' if k==1 else None)
            marks.append(mark)
    if annotate and probabilistic:
        indices=np.argsort(z)[::-1][:sum(len(a.states) for a in deterministic.attractors) if deterministic else 10]
        if len(indices):
            xy=pointxy[indices]; marks.append(ax.scatter(xy[:,0],xy[:,1],z[indices]+.045,c=[(.1137,.4667,.9216)],marker='x',s=80,linewidths=2,label='Robust/High Probability States'))
        if probabilistic.trajectory is not None:
            ti=[lookup[probabilistic.states[i].tobytes()] for i in probabilistic.trajectory if probabilistic.states[i].tobytes() in lookup]
            if ti:
                xy=pointxy[ti]; marks.append(ax.scatter(xy[:,0],xy[:,1],z[ti]+.025,c=[(.3,1,.1)],marker='+',s=40,linewidths=2,label='States in the Mapped Trajectory'))
                for j,i in enumerate(ti):
                    text=f'End ({len(ti)})' if j==0 else 'Start (1)' if j==len(ti)-1 else str(len(ti)-j)
                    marks.append(ax.text(pointxy[i,0],pointxy[i,1],z[i]+.025,text,fontweight='bold',fontsize=10))
                for current,nxt in zip(ti[:-1],ti[1:]):
                    start=np.r_[pointxy[nxt],z[nxt]]; stop=np.r_[pointxy[current],z[current]]
                    arrow=ax.quiver(*start,*(stop-start),color='black',linewidth=.8,arrow_length_ratio=.1)
                    arrow.set_visible(False); arrows.append(arrow)
    has_legend=bool(ax.get_legend_handles_labels()[0])
    if has_legend: ax.legend(loc='upper center',bbox_to_anchor=(.5,-.09),fontsize=7)
    fig.subplots_adjust(left=.07,right=.92,bottom=.23 if has_legend else .10,top=.91)
    fig.atlantis_data={'states':states,'values':z,'coordinates':coordinates,'permutation':permutation,'mapping':mapping,'grid':Z,'pointxy':pointxy,'annotations':marks,'arrows':arrows,'surface':surface,'contour':contour,'tooltips':tooltips,'deterministic':deterministic,'probabilistic':probabilistic}
    return fig


def cell_fate_figure(propensities,cmap='jet',annotate=True,title='Cell Fate Landscape',legends=True):
    pairs=sorted(propensities.items(),key=lambda x:x[1],reverse=True)
    if not pairs: raise ValueError('No cell-fate classification found; load fate logic and run deterministic analysis')
    # MATLAB rounds to two significant digits before computing treemap areas.
    values=np.array([float(f'{v:.2g}') for _,v in pairs]); rectangles=treemap(values)
    colors=(matlab_colors(cmap,len(pairs))+1)/2
    fig=Figure(figsize=(560/96,420/96),dpi=96); ax=fig.add_subplot(); patches=[]
    for (name,_),value,rect,color in zip(pairs,values,rectangles,colors):
        x,y,w,h=rect; patch=Rectangle((x,y),w,h,facecolor=color,edgecolor='black'); ax.add_patch(patch); patches.append(patch)
        if annotate: ax.text(x+w/2,y+h/2,f'{value:g}',ha='center',va='center')
    if legends: ax.legend(patches,[f'{n or "Uncharacterized"} ( {v:g} )' for (n,_),v in zip(pairs,values)],loc='center left',bbox_to_anchor=(1.02,.5))
    ax.set(xlim=(0,1),ylim=(0,1),aspect='equal',title=title); ax.axis('off')
    fig.tight_layout(); fig.atlantis_data={'rectangles':rectangles,'fates':pairs}; return fig
