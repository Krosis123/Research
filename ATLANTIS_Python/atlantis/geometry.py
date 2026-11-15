"""Source treemap partition and cyclic-state grouping geometry."""
import numpy as np


def treemap(data,width=1.,height=1.):
    data=np.asarray(data,dtype=float)
    if not len(data) or (data<=0).any() or not np.isfinite(data).all():
        raise ValueError('Treemap values must be finite and positive')
    def partition(v,w,h):
        
        if len(v)==1: return [1]
        long=max(w,h); short=min(w,h); ratio=w*h/v.sum(); best=np.inf; part=len(v)
        for i in range(1,len(v)+1):
            column_width=v[:i].sum()*ratio/short
            block_height=v[:i]*ratio/column_width
            aspect=block_height/column_width
            score=np.maximum(aspect,1/aspect).mean()
            if score>=best:
                # Preserve original recursion, including its rejected column width.
                return [part]+partition(v[i-1:],short,long-column_width) if part<i else [part]
            best=score; part=i
        return [part]
    order=np.argsort(-data,kind='stable'); v=data[order]; ratio=width*height/data.sum()
    parts=partition(v,width,height); rect=np.zeros((len(data),4)); ox=oy=0.; first=0
    for count in parts:
        area=v[first:first+count]*ratio; x=ox; y=oy
        if width<height:
            colheight=area.sum()/width
            for j,a in enumerate(area): rect[order[first+j]]=[x,y,a/colheight,colheight]; x+=a/colheight
            oy+=colheight; height-=colheight
        else:
            colwidth=area.sum()/height
            for j,a in enumerate(area): rect[order[first+j]]=[x,y,colwidth,a/colwidth]; y+=a/colwidth
            ox+=colwidth; width-=colwidth
        first+=count
    return rect


def find_positions(r,c,needed,size):
    # MATLAB's expanding square spiral, then bounds filtering and center deletion.
    points=[(0,0)]; dx=dy=1; count=1
    while len(points)<needed:
        for dr,dc in [(0,dy),(dx,0)]:
            for _ in range(count):
                if len(points)>=needed: break
                a,b=points[-1]; points.append((a+dr,b+dc))
        count+=1; dx=-dx; dy=-dy
    points=[(a+r,b+c) for a,b in points]
    return np.array([(a,b) for a,b in points[1:] if 0<=a<size and 0<=b<size],dtype=int).reshape(-1,2)


def group_cyclic(attractors,states,permutation,z):
    size=z.shape[0]; grid=permutation.reshape((size,size),order='F').copy(); z=z.copy(); blocked=set()
    lookup={row.tobytes():i for i,row in enumerate(states)}
    for attr in attractors:
        if len(attr.states)<=1: continue
        indices=[lookup.get(row.tobytes()) for row in attr.states]
        if any(i is None for i in indices): continue
        old=np.array([np.argwhere(grid==i)[0] for i in indices]); candidates=[]
        for r,c in old:
            available=find_positions(r,c,len(indices)*2+2*len(blocked),size)
            available=np.array([pt for pt in available if tuple(pt) not in blocked],dtype=int).reshape(-1,2)
            dist=np.linalg.norm(available-[r,c],axis=1)
            score=dist.mean()+np.var(dist,ddof=1) if len(dist)>=len(indices) else np.inf
            candidates.append((score,dist,available))
        center=int(np.argmin([c[0] for c in candidates])); _,dist,available=candidates[center]
        if not np.isfinite(candidates[center][0]): raise ValueError('Insufficient grid positions for cyclic-state grouping')
        selected=np.argsort(dist,kind='stable')[:len(indices)-1]; new=available[selected]
        blocked.add(tuple(old[center])); blocked.update(map(tuple,new)); old=np.delete(old,center,axis=0)
        for (rn,cn),(ro,co),weight in zip(new,old,2*dist[selected]):
            grid[rn,cn],grid[ro,co]=grid[ro,co],grid[rn,cn]
            z[rn,cn],z[ro,co]=z[ro,co]/weight,z[rn,cn]
    return grid.ravel(order='F'),z
