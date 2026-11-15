"""Recreate GUIDE controls using positions, labels, and defaults extracted from .fig."""
from pathlib import Path
import json
from PySide6 import QtCore,QtGui,QtWidgets as W

ASSETS=Path(__file__).parent/'assets'

def load_system_fonts():
    # Qt offscreen on restricted Windows hosts cannot enumerate system fonts.
    for name in ['arial.ttf','arialbd.ttf','calibri.ttf','calibrib.ttf','times.ttf','timesbd.ttf']:
        path=Path('C:/Windows/Fonts')/name
        if path.exists(): QtGui.QFontDatabase.addApplicationFont(str(path))



def string(value):
    if value is None or value==[]: return ''
    return '\n'.join(str(x) for x in value) if isinstance(value,list) else str(value)


def show_warning(parent, title, message):
    warning = W.QMessageBox(parent)
    warning.setWindowTitle(title)
    warning.setIcon(W.QMessageBox.Icon.Warning)
    warning.setTextFormat(QtCore.Qt.TextFormat.PlainText)
    warning.setTextInteractionFlags(
        QtCore.Qt.TextInteractionFlag.TextSelectableByMouse
        | QtCore.Qt.TextInteractionFlag.TextSelectableByKeyboard
    )
    warning.setText(message.strip() or 'The operation failed without providing an error description.')
    warning.setStandardButtons(W.QMessageBox.StandardButton.Ok)
    warning.setStyleSheet('QMessageBox { background-color:#ffffff; } QLabel { color:#202020; }')
    warning.exec()


class GuideWindow(W.QDialog):
    def __init__(self,name,parent=None):
        super().__init__(parent)
        load_system_fonts()
        self.guide_name=name; self.controls={}; self.spec=json.loads((ASSETS/'guide'/(name+'.json')).read_text(encoding='utf-8'))
        self.setWindowTitle(self.spec['properties'].get('Name',name) or name)
        self.setObjectName(self.spec['properties'].get('Tag',name))
        self.unit=(5.,13.); self.geometries=[]
        p=self.spec['properties']; pos=p.get('Position',[0,0,100,30]); units=p.get('Units','characters')
        width,height=(pos[2]*5,pos[3]*13) if units=='characters' else (pos[2],pos[3])
        self.resize(round(width),round(height)); self.setMinimumSize(round(width),round(height))
        self.setStyleSheet(
            'QDialog { background:white; } '
            'QDialog QLabel { color:#202020; } '
            'QGroupBox { border:1px solid #b0b0b0; margin-top:5px; background:transparent; } '
            'QGroupBox::title { subcontrol-origin:margin; left:8px; padding:0 3px; background:white; color:#202020; }'
        )
        self.base_size=(self.width(),self.height())
        self.build(self.spec,self)

    def build(self,node,parent):
        for child in node.get('children',[]):
            typ=child['type']; p=child['properties']; tag=p.get('Tag',''); text=string(p.get('String','')); style=p.get('Style','')
            if typ in ('uipanel','uitools.uibuttongroup','uibuttongroup'):
                title=string(p.get('Title',''))
                # Untitled panels in the main screen are decorative frame strips.
                if self.guide_name=='ATLANTIS' and not title: continue
                obj=W.QGroupBox(title,parent)
            elif typ=='uicontrol':
                if style in ('pushbutton','togglebutton'): obj=W.QPushButton(text or ('...' if tag.startswith('Browse') else tag),parent)
                elif style=='text':
                    obj=W.QLabel(text,parent); obj.setWordWrap(tag=='Console')
                    alignment=p.get('HorizontalAlignment','center')
                    obj.setAlignment({'left':QtCore.Qt.AlignLeft,'right':QtCore.Qt.AlignRight}.get(alignment,QtCore.Qt.AlignHCenter)|QtCore.Qt.AlignVCenter)
                elif style=='edit': obj=W.QLineEdit(text,parent)
                elif style=='checkbox': obj=W.QCheckBox(text,parent); obj.setChecked(bool(p.get('Value',0)))
                elif style=='radiobutton': obj=W.QRadioButton(text,parent); obj.setChecked(bool(p.get('Value',0)))
                elif style in ('popupmenu','listbox'):
                    obj=W.QComboBox(parent); obj.addItems(p['String'] if isinstance(p.get('String'),list) else [text]); obj.setCurrentIndex(max(0,int(p.get('Value',1))-1))
                else: continue
            else: continue
            obj.setObjectName(tag); self.controls[tag]=obj
            if 'FontSize' in p:
                font=QtGui.QFont(('Arial' if p.get('FontName')=='MS Sans Serif' else p.get('FontName','Arial')),max(7,round(p['FontSize'])))
                font.setBold(p.get('FontWeight')=='bold'); obj.setFont(font)
            color=p.get('ForegroundColor')
            if isinstance(color,list) and len(color)==3:
                pal=obj.palette(); pal.setColor(QtGui.QPalette.WindowText,QtGui.QColor.fromRgbF(*color)); pal.setColor(QtGui.QPalette.Text,QtGui.QColor.fromRgbF(*color)); obj.setPalette(pal)
            if p.get('TooltipString'): obj.setToolTip(string(p['TooltipString']))
            pos=p.get('Position',[0,0,1,1]); units=p.get('Units','characters')
            if units=='normalized': x,y,w,h=[pos[i]*(parent.width() if i%2==0 else parent.height()) for i in range(4)]
            elif units=='characters': x,y,w,h=pos[0]*5,pos[1]*13,pos[2]*5,pos[3]*13
            else: x,y,w,h=pos
            rect=(round(x),round(parent.height()-y-h),max(1,round(w)),max(1,round(h)))
            obj.setGeometry(*rect)
            if isinstance(obj,W.QPushButton) and tag.startswith('Browse'):
                icon=ASSETS/'images'/'OpenFile.jpg'
                if icon.exists(): obj.setText(''); obj.setIcon(QtGui.QIcon(str(icon))); obj.setIconSize(QtCore.QSize(20,20))
            if isinstance(obj,W.QLabel) and tag!='Console' and text:
                font=obj.font()
                while QtGui.QFontMetrics(font).horizontalAdvance(text)>rect[2] and font.pointSizeF()>7:
                    font.setPointSizeF(font.pointSizeF()-.5)
                obj.setFont(font)
            self.geometries.append((obj,parent,rect,(parent.width(),parent.height())))
            self.build(child,obj)

    def resizeEvent(self,event):
        if hasattr(self,'geometries'):
            for obj,parent,(x,y,w,h),(pw,ph) in self.geometries:
                if pw and ph: obj.setGeometry(round(x*parent.width()/pw),round(y*parent.height()/ph),round(w*parent.width()/pw),round(h*parent.height()/ph))
        super().resizeEvent(event)

    def bind(self,tag,callback):
        obj=self.controls.get(tag)
        if obj is None: return
        signal=obj.clicked if hasattr(obj,'clicked') else obj.currentIndexChanged if isinstance(obj,W.QComboBox) else None
        if signal: signal.connect(lambda *args:self.safe(callback))

    def safe(self,callback):
        try: callback()
        except Exception as e: self.error(str(e).strip() or f'The operation failed ({type(e).__name__}).')

    def error(self,message): show_warning(self,'ATLANTIS',message)

    def text(self,tag):
        obj=self.controls[tag]
        return obj.currentText() if isinstance(obj,W.QComboBox) else obj.text()

    def checked(self,tag): return self.controls[tag].isChecked()
    def set_text(self,tag,text):
        if tag in self.controls: self.controls[tag].setText(str(text))

    def console(self,message): self.set_text('Console',message)
