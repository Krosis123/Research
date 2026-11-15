"""Complete Graphviz SVG rendering with native Qt pan/zoom and figure export."""
import subprocess
from pathlib import Path
from PySide6 import QtCore,QtGui,QtWidgets as W,QtSvgWidgets,QtSvg
from .guide import show_warning
from .plots import find_graphviz


def graphviz_svg(dot,engine='dot'):
    result=subprocess.run([find_graphviz(engine),'-Tsvg'],input=dot,text=True,capture_output=True,check=True)
    return result.stdout.encode('utf-8')


class SvgView(W.QGraphicsView):
    def wheelEvent(self,event):
        scale=1.2 if event.angleDelta().y()>0 else 1/1.2
        self.scale(scale,scale)


class GraphvizWindow(W.QMainWindow):
    def __init__(self,svg,title='ATLANTIS - Regulatory Network',parent=None):
        super().__init__(parent);self.svg=svg;self.setWindowTitle(title)
        self.renderer=QtSvg.QSvgRenderer(QtCore.QByteArray(svg),self)
        if not self.renderer.isValid():raise ValueError('Graphviz returned an invalid SVG document')
        scene=W.QGraphicsScene(self);item=QtSvgWidgets.QGraphicsSvgItem();item.setSharedRenderer(self.renderer);scene.addItem(item)
        self.view=SvgView(scene);self.view.setDragMode(W.QGraphicsView.ScrollHandDrag);self.view.setRenderHint(QtGui.QPainter.Antialiasing);self.setCentralWidget(self.view)
        toolbar=self.addToolBar('Figure')
        for label,callback in [('Zoom In',lambda:self.view.scale(1.2,1.2)),('Zoom Out',lambda:self.view.scale(1/1.2,1/1.2)),('Fit',self.fit),('Export Figure...',self.export)]:
            action=toolbar.addAction(label);action.triggered.connect(lambda _,f=callback:self.safe(f))
        self.statusBar().showMessage('Mouse wheel zooms; drag to pan. This is a generated vector graph, including the DOT shapes, clusters, labels, and arrowheads.')
        self.resize(950,730);QtCore.QTimer.singleShot(0,self.fit)
    def fit(self):self.view.fitInView(self.view.sceneRect(),QtCore.Qt.KeepAspectRatio)
    def safe(self,callback):
        try:callback()
        except Exception as e:show_warning(self,'ATLANTIS',str(e))
    def export(self):
        p,_=W.QFileDialog.getSaveFileName(self,'Export Network Figure','network.svg','SVG (*.svg);;PNG (*.png);;JPEG (*.jpg);;TIFF (*.tiff);;PDF (*.pdf)')
        if not p:return
        suffix=Path(p).suffix.lower()
        if suffix=='.svg':Path(p).write_bytes(self.svg);return
        dpi,ok=W.QInputDialog.getInt(self,'Export Resolution','DPI:',300,1,2400)
        if not ok:return
        size=self.renderer.defaultSize();width=max(1,round(size.width()*dpi/96));height=max(1,round(size.height()*dpi/96))
        if suffix=='.pdf':
            writer=QtGui.QPdfWriter(p);writer.setResolution(dpi)
            writer.setPageSize(QtGui.QPageSize(QtCore.QSizeF(size.width()/96*25.4,size.height()/96*25.4),QtGui.QPageSize.Millimeter))
            writer.setPageMargins(QtCore.QMarginsF(0,0,0,0));painter=QtGui.QPainter(writer)
            self.renderer.render(painter,QtCore.QRectF(0,0,writer.width(),writer.height()));painter.end()
        else:
            image=QtGui.QImage(width,height,QtGui.QImage.Format_ARGB32);image.fill(QtCore.Qt.white)
            painter=QtGui.QPainter(image);self.renderer.render(painter);painter.end()
            # Pillow supplies TIFF on Qt builds whose image plugin omits it.
            if suffix in ('.tif','.tiff'):
                from PIL import Image
                view=image.convertToFormat(QtGui.QImage.Format_RGBA8888);raw=bytes(view.bits())
                Image.frombytes('RGBA',(width,height),raw,'raw','RGBA',view.bytesPerLine()).save(p,dpi=(dpi,dpi))
            elif not image.save(p):raise ValueError('Qt could not export this image format')
