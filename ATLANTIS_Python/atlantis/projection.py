"""Original Sammon projection and Sibson natural-neighbor surface interpolation.

Sammon algorithm: supplied MATLAB routine credits Dr Gavin C. Cawley (2007).
ATLANTIS adaptation: Biomedical Informatics Research Laboratory, LUMS.
"""
import warnings
import numpy as np
from scipy.spatial import Voronoi,Delaunay,QhullError
from .analysis import checkpoint


def euclid(x,y):
    return np.sqrt(np.maximum(0,np.sum(x*x,axis=1)[:,None]+np.sum(y*y,axis=1)[None,:]-2*x@y.T))


def sammon_mapping(x,n=2,max_iter=500,max_halves=40,tol=1e-9,progress=None,cancel=None,initial=None,input_type='raw',initialisation='pca',seed=None):
    x=np.asarray(x,dtype=float)
    if x.ndim!=2 or len(x)<n+1: raise ValueError('Sammon mapping needs at least three states for a 2D map')
    if len(np.unique(x,axis=0))!=len(x): raise ValueError('Sammon mapping requires distinct states')
    if max_iter<1 or max_halves<1 or tol<0: raise ValueError('Invalid Sammon iteration settings')
    D=x.copy() if input_type=='distance' else euclid(x,x)
    if D.shape!=(len(x),len(x)) or np.any(D<0): raise ValueError('Distance matrix must be square and nonnegative')
    scale=.5/D.sum(); D+=np.eye(len(x)); Dinv=1/D
    if initial is None:
        if initialisation=='pca':
            u,s,_=np.linalg.svd(x,full_matrices=False)
            if len(s)<n: raise ValueError('Not enough dimensions for requested projection')
            y=u[:,:n]*s[:n]
        else: y=np.random.default_rng(seed).normal(size=(len(x),n))
    else: y=np.asarray(initial,dtype=float).copy()
    one=np.ones_like(y); d=euclid(y,y)+np.eye(len(x))
    if np.any(d==0): raise ValueError('PCA initialization overlaps points; supply non-overlapping initial coordinates')
    dinv=1/d; delta=D-d; E=np.sum(delta**2*Dinv)
    if E==0: return y,0.
    for i in range(max_iter):
        checkpoint(progress,cancel,(i+1)/max_iter,'Sammon projection')
        delta=dinv-Dinv; deltaone=delta@one
        g=delta@y-y*deltaone
        dinv3=dinv**3; y2=y*y
        H=dinv3@y2-deltaone-2*y*(dinv3@y)+y2*(dinv3@one)
        if np.any(H==0): raise FloatingPointError('Zero Sammon Hessian diagonal')
        direction=-g/np.abs(H); old=y.copy()
        for j in range(max_halves):
            y=old+direction; d=euclid(y,y)+np.eye(len(x))
            with np.errstate(divide='ignore',invalid='ignore'):
                dinv=1/d; delta=D-d; new=np.sum(delta**2*Dinv)
            if new<E: break
            direction*=.5
        else: warnings.warn('MaxHalves exceeded. Sammon mapping may not converge.',RuntimeWarning)
        if not np.isfinite(new): raise FloatingPointError('Sammon projection did not produce finite coordinates')
        if abs((E-new)/E)<tol: break
        E=new
    # MATLAB retains the previous E at the tolerance break; preserve that report.
    return y,float(E*scale)


def clip_halfplane(poly,normal,offset,tol=1e-11):
    if not len(poly): return np.empty((0,2))
    output=[]; prev=poly[-1]; dp=float(prev@normal-offset)
    for curr in poly:
        dc=float(curr@normal-offset)
        if (dc<=tol)!=(dp<=tol):
            denominator=dp-dc
            if denominator: output.append(prev+(curr-prev)*(dp/denominator))
        if dc<=tol: output.append(curr)
        prev=curr; dp=dc
    return np.array(output).reshape(-1,2)


def polygon_area(poly):
    if len(poly)<3: return 0.
    return abs(float(np.dot(poly[:,0],np.roll(poly[:,1],-1))-np.dot(poly[:,1],np.roll(poly[:,0],-1))))/2


def natural_neighbor(points,values,queries):
    """Sibson coordinates from stolen Voronoi areas. NaN outside the convex hull.

    This implements MATLAB griddata(...,'natural') without replacing it with
    linear/cubic interpolation. Qhull and polygon arithmetic use float64.
    """
    p=np.asarray(points,dtype=float); z=np.asarray(values,dtype=float); q=np.asarray(queries,dtype=float)
    if len(p)<3 or np.linalg.matrix_rank(p-p.mean(axis=0))<2: raise ValueError('A surface requires noncollinear projected points')
    hull=Delaunay(p); original=Voronoi(p)
    neighbors=[set() for _ in p]
    for i,j in original.ridge_points: neighbors[i].add(j); neighbors[j].add(i)
    out=np.full(len(q),np.nan)
    for k,point in enumerate(q):
        distance=np.linalg.norm(p-point,axis=1); exact=np.flatnonzero(distance<1e-10)
        if len(exact): out[k]=z[exact[0]]; continue
        if hull.find_simplex(point)<0: continue
        vor=Voronoi(np.vstack((p,point)))
        region=vor.regions[vor.point_region[-1]]
        if not region or -1 in region:
            # Convex-hull boundary has the continuous 1D interpolation limit.
            simplex=hull.find_simplex(point)
            tri=hull.simplices[simplex]
            b=hull.transform[simplex,:2]@(point-hull.transform[simplex,2])
            out[k]=np.r_[b,1-b.sum()]@z[tri]
            continue
        cell=vor.vertices[region]
        adjacent=set()
        for i,j in vor.ridge_points:
            if i==len(p): adjacent.add(j)
            elif j==len(p): adjacent.add(i)
        weights=[]; indices=[]
        for i in sorted(adjacent):
            polygon=cell.copy()
            for j in neighbors[i]:
                normal=p[j]-p[i]; offset=(p[j]@p[j]-p[i]@p[i])/2
                polygon=clip_halfplane(polygon,normal,offset)
                if not len(polygon): break
            weights.append(polygon_area(polygon)); indices.append(i)
        total=sum(weights)
        if total>0: out[k]=np.dot(weights,z[indices])/total
    return out


def naive_grid(states,values,permutation=None,seed=None):
    size=int(np.ceil(np.sqrt(len(states)))); n=len(states)
    if permutation is None:
        permutation=np.r_[np.random.default_rng(seed).permutation(n),np.arange(n,size*size)]
    permutation=np.asarray(permutation,dtype=int).reshape(-1)
    if sorted(permutation.tolist())!=list(range(size*size)): raise ValueError('Invalid saved grid permutation')
    z=np.r_[np.asarray(values),np.zeros(size*size-n)]
    x,y=np.meshgrid(np.arange(1,size+1),np.arange(1,size+1))
    return x,y,z[permutation].reshape((size,size),order='F'),permutation
