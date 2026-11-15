"""Matplotlib desktop windows with export, data inspection, and plot controls."""
from pathlib import Path
import json
import numpy as np
from PySide6 import QtCore,QtGui,QtWidgets as W
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg,NavigationToolbar2QT
from .guide import GuideWindow, show_warning
from .plots import color_map


class FigureWindow(W.QMainWindow):
    def __init__(self,figure,title='ATLANTIS Figure',parent=None):
        super().__init__(parent); self.setWindowTitle(title); self.figure=figure
        self.canvas=FigureCanvasQTAgg(figure); self.setCentralWidget(self.canvas)
        self.addToolBar(NavigationToolbar2QT(self.canvas,self)); self.resize(950,730)
        view=self.menuBar().addMenu('Figure')
        self.action(view,'Export Figure...',self.export)
        self.action(view,'Export Plot Data...',self.export_data)
        self.action(view,'Toggle Annotations',self.toggle_annotations)
        self.action(view,'Show / Hide Trajectory Arrows',self.toggle_trajectory)
        self.action(view,'Invert Z Axis',self.invert)
        self.action(view,'Show / Hide Surface',self.toggle_surface)
        self.action(view,'Show / Hide Contours',self.toggle_contour)
        self.action(view,'Transparent Surface',lambda:self.alpha(.5))
        self.action(view,'Opaque Surface',lambda:self.alpha(1.))
        alpha_menu=view.addMenu('Surface Alpha')
        for value in np.linspace(0,1,11): self.action(alpha_menu,f'{value:.1f}',lambda v=value:self.alpha(v))
        colors=view.addMenu('Color Scheme')
        for name in ['jet','parula','spring','winter','autumn','hot','hsv','gray']:
            self.action(colors,name,lambda n=name:self.recolor(n))
        self.statusBar().showMessage('Drag to rotate 3D figures; use the toolbar to zoom, pan, and save. Click a landscape state to inspect its data.')
        self.canvas.mpl_connect('pick_event',self.pick)
        data=getattr(figure,'atlantis_data',{})
        if 'pointxy' in data and len(data['states']) and data.get('tooltips',True):
            xy=data['pointxy']; ax=figure.axes[0]
            self.points=ax.scatter(xy[:,0],xy[:,1],data['values'],s=2,alpha=0.01,picker=5)
        self.canvas.draw()

    def action(self,menu,title,callback):
        a=menu.addAction(title); a.triggered.connect(lambda *_:self.safe(callback)); return a
    def safe(self,callback):
        try: callback()
        except Exception as e: show_warning(self,'ATLANTIS Figure',str(e))
    def pick(self,event):
        data=getattr(self.figure,'atlantis_data',{})
        if not event.ind.size or 'states' not in data: return
        i=int(event.ind[0])
        state=data['states'][i]
        text=[f'State {i+1}: {" ".join(map(str,state))}',f'Plotted value: {data["values"][i]:.12g}']
        det=data.get('deterministic'); prob=data.get('probabilistic')
        if det:
            for number,attr in enumerate(det.attractors,1):
                if np.any(np.all(attr.states==state,axis=1)):
                    text.extend([f'Attractor {number}: {attr.kind}',f'Basin size ratio: {attr.basin:.12g}',f'Cell fate: {attr.fate or "Uncharacterized"}','Average activities: '+', '.join(f'{x:.6g}' for x in attr.average)])
        if prob:
            index=np.flatnonzero(np.all(prob.states==state,axis=1))
            if len(index):
                j=int(index[0]); text.append(f'Probability: {prob.probabilities[j]:.12g}')
                if prob.fates:text.append('State cell fate: '+(prob.fates[j] or 'Uncharacterized'))
                if prob.trajectory is not None and j in prob.trajectory:text.append(f'Order in probability-ranked trajectory: {int(np.flatnonzero(prob.trajectory==j)[0])+1}')
        self.statusBar().showMessage(' | '.join(text[:2]))
        W.QToolTip.showText(QtGui.QCursor.pos(),'\n'.join(text),self.canvas)
    def toggle_annotations(self):
        for artist in getattr(self.figure,'atlantis_data',{}).get('annotations',[]): artist.set_visible(not artist.get_visible())
        self.canvas.draw_idle()
    def toggle_trajectory(self):
        for arrow in getattr(self.figure,'atlantis_data',{}).get('arrows',[]): arrow.set_visible(not arrow.get_visible())
        self.canvas.draw_idle()
    def invert(self):
        ax=self.figure.axes[0]
        if hasattr(ax,'invert_zaxis'): ax.invert_zaxis(); self.canvas.draw_idle()
    def toggle_surface(self):
        s=getattr(self.figure,'atlantis_data',{}).get('surface')
        if s is not None: s.set_visible(not s.get_visible()); self.canvas.draw_idle()
    def toggle_contour(self):
        contour=getattr(self.figure,'atlantis_data',{}).get('contour')
        if contour is not None: contour.set_visible(not contour.get_visible()); self.canvas.draw_idle()
    def alpha(self,value):
        s=getattr(self.figure,'atlantis_data',{}).get('surface')
        if s is not None: s.set_alpha(value); self.canvas.draw_idle()
    def recolor(self,name):
        for ax in self.figure.axes:
            for collection in ax.collections: collection.set_cmap(color_map(name,True))
            if ax.patches:
                colors=(color_map(name)(np.linspace(0,1,len(ax.patches)))[:,:3]+1)/2
                for patch,color in zip(ax.patches,colors): patch.set_facecolor(color)
        self.canvas.draw_idle()
    def export(self):
        d=GuideWindow('ExportFigureMenu',self)
        d.bind('Done',lambda:self.save_from_dialog(d)); d.exec()
    def save_from_dialog(self,d):
        dpi=float(d.text('EditResolution'))
        if not 1<=dpi<=9600: raise ValueError('DPI must be between 1 and 9600')
        fmt=d.text('SelectFormat').lower(); p,_=W.QFileDialog.getSaveFileName(self,'Export Figure','figure.'+fmt,f'Image (*.{fmt});;PDF (*.pdf);;SVG (*.svg);;EPS (*.eps)')
        if p: self.figure.savefig(p,dpi=dpi); d.accept()
    def export_data(self):
        data=getattr(self.figure,'atlantis_data',{})
        p,_=W.QFileDialog.getSaveFileName(self,'Export Plot Data','plot_data.npz','NumPy arrays (*.npz)')
        if p:
            arrays={k:v for k,v in data.items() if isinstance(v,np.ndarray) and v.dtype!=object}
            np.savez_compressed(p,**arrays)
