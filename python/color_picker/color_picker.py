"""
* Color Picker Template
"""
import sys
import re
from math import fmod
from PySide2.QtCore import Qt
from PySide2.QtCore import Signal
from PySide2.QtCore import QSize
from PySide2.QtCore import QPoint
from PySide2.QtCore import QRect
from PySide2.QtCore import QEvent
from PySide2.QtCore import QMimeData
from PySide2.QtGui import QColor
from PySide2.QtGui import QImage
from PySide2.QtGui import QPen
from PySide2.QtGui import QBrush
from PySide2.QtGui import QKeyEvent
from PySide2.QtGui import QPixmap
from PySide2.QtGui import QFont
from PySide2.QtGui import QPainter
from PySide2.QtGui import QDrag
from PySide2.QtGui import QPalette
from PySide2.QtWidgets import QApplication
from PySide2.QtWidgets import QMainWindow
from PySide2.QtWidgets import QWidget
from PySide2.QtWidgets import QMenu
from PySide2.QtWidgets import QLabel
from PySide2.QtWidgets import QStatusBar


_NPALETTE_INDEX_OFFSET = 256


def linear_to_srgb(linear):
    """
    Converts linear float value to a sRGB float value
    :type linear: float
    :param linear: the linear value to convert
    :rtype: float
    :return: the calculated sRGB value
    """
    linear = float(linear)
    if linear <= 0.0031308:
        srgb = linear * 12.92
    else:
        srgb = 1.055 * pow(linear, 1. / 2.4) - 0.055
    return srgb


def srgb_to_linear(srgb):
    """
    Converts sRGB float value to a linear float value
    :type srgb: float
    :param srgb: the sRGB value to convert
    :rtype: float
    :return: the calculated linear value
    """
    srgb = float(srgb)
    if srgb <= 0.04045:
        linear = srgb / 12.92
    else:
        linear = pow((srgb + 0.055) / 1.055, 2.4)
    return linear


def qcolor_srgb_to_linear(color):
    """
    Converts sRGB color value to linear color value
    :type color: QColor
    :param color: the sRGB color to convert
    :rtype: QColor
    :return: the calculated linear color
    """
    r, g, b, _ = color.getRgbF()
    r = srgb_to_linear(r)
    g = srgb_to_linear(g)
    b = srgb_to_linear(b)
    return QColor.fromRgbF(r, g, b)


def qcolor_linear_to_srgb(color):
    """
    Converts linear color value to sRGB color value
    :type color: QColor
    :param color: the linear color to convert
    :rtype: QColor
    :return: the calculated sRGB color
    """
    r, g, b, _ = color.getRgbF()
    r = linear_to_srgb(r)
    g = linear_to_srgb(g)
    b = linear_to_srgb(b)
    return QColor.fromRgbF(r, g, b)


def clamp(value, max_value, min_value):
    return max(max_value, min(min_value, int(value)))


def encode_index(i):
    return "index:{0}".format(i)


def decode_index(text):
    m = re.search(r"^index:(\d+)$", text)
    if m is not None:
        return int(m.group(1))
    return -2


def get_hsv_indexes(index):
    index -= _NPALETTE_INDEX_OFFSET
    sz = 25 * 25
    eh = int(index / sz)
    esv = int(fmod(index, sz))
    ev = int(esv / 25)
    es = esv - ev * 25
    return eh, es, ev


def color_from_index(index):
    eh, es, ev = get_hsv_indexes(index)
    h = int(360.0 * eh / 90)
    s = int(255.0 * es / 24)
    v = int(255.0 * ev / 24)
    return QColor.fromHsv(h, s, v)


class TColorPickerSV(QWidget):
    changed = Signal(QColor)
    doubleClicked = Signal()

    def __init__(self, parent):
        super(TColorPickerSV, self).__init__(parent)
        self.setStatusTip("Saturation, Value. To control use Arrows")
        self._size = QSize(25, 25)
        self._scale = 11
        self.setMinimumSize(self._size * self._scale)
        self._color = QColor(Qt.white)
        self._pixmap = QPixmap()
        self._pos = QPoint(24, 24)
        self._hue = 0
        self._saturation = 255
        self._value = 255

    def set_hue(self, hue):
        hue = clamp(hue, 0, 360)
        self._hue = hue if hue < 360 else 0
        iw = self._size.width()
        ih = self._size.height()
        bpl = iw * 4
        bits = bytearray(iw * ih * 4)
        color = QColor()
        for v in range(ih):
            for s in range(iw):
                color.setHsv(hue, 255.0 / (iw-1) * s, 255.0 - 255.0 / (ih-1) * v)
                color = qcolor_linear_to_srgb(color)
                (r, g, b, a) = color.getRgb()
                # For 3ds Max use bits[index] = chr(value)
                bits[bpl * v + 4*s + 0] = b
                bits[bpl * v + 4*s + 1] = g
                bits[bpl * v + 4*s + 2] = r
                # bits[bpl * v + 4*s + 3] = 0xff

        img = QImage(bits, iw, ih, QImage.Format_RGB32)
        self._pixmap = QPixmap.fromImage(img).scaled(self.minimumSize(), Qt.KeepAspectRatio, Qt.FastTransformation)
        self.set_pos(self._pos)

    def set_pos(self, pos):
        iw = self._size.width() - 1
        ih = self._size.height() - 1
        self._pos.setX(clamp(pos.x(), 0, iw))
        self._pos.setY(clamp(pos.y(), 0, ih))
        self._saturation = clamp(255 * self._pos.x() / iw, 0, 255)
        self._value      = clamp(255 * self._pos.y() / ih, 0, 255)
        self._color = QColor.fromHsv(self._hue, self._saturation, self._value)

        self.update()
        self.changed.emit(self._color)

    def set_remap_pos(self, mouse_pos):
        # Remap mouse position
        pos = QPoint(int(mouse_pos.x() / self._scale), int(self._size.height() - mouse_pos.y() / self._scale))
        self.set_pos(pos)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self._pixmap)
        painter.save()
        painter.setCompositionMode(QPainter.RasterOp_SourceXorDestination)
        pen = QPen(QBrush(Qt.white), 2., Qt.SolidLine, Qt.SquareCap, Qt.MiterJoin)
        painter.setPen(pen)
        s = self._scale
        painter.drawRect(QRect(self._pos.x() * s - 1, (self._size.height() - 1 - self._pos.y()) * s - 1, s + 2, s + 2))
        painter.restore()

    def mouseMoveEvent(self, event):
        self.set_remap_pos(event.pos())
        event.accept()

    def mousePressEvent(self, event):
        self.set_remap_pos(event.pos())
        event.accept()

    def mouseDoubleClickEvent(self, event):
        self.doubleClicked.emit()
        event.accept()

    def keyPressEvent(self, event):
        key = event.key()
        if key in [Qt.Key_Left, Qt.Key_Right, Qt.Key_Up, Qt.Key_Down]:
            x, y = self._pos.x(), self._pos.y()
            if key == Qt.Key_Left: x -= 1
            if key == Qt.Key_Right: x += 1
            if key == Qt.Key_Up: y += 1
            if key == Qt.Key_Down: y -= 1
            self.set_pos(QPoint(x, y))
            event.accept()


class TColorPickerHue(QWidget):
    changed = Signal(int)

    def __init__(self, parent):
        super(TColorPickerHue, self).__init__(parent)
        self.setStatusTip("Hue. To control use Mouse Wheel or Shift+Up/Down")
        self._size = QSize(1, 91)
        self._scale = 3
        self.setFixedSize(QSize(23, self._size.height() * self._scale + 4))
        self._pixmap = QPixmap()
        self._pos = 0
        self.draw()

    def draw(self):
        ih = self._size.height()
        bits = bytearray(ih * 4)
        color = QColor()
        for h in range(ih):
            color.setHsv(360 * h / (ih - 1), 255, 255)
            color = qcolor_linear_to_srgb(color)
            (r, g, b, a) = color.getRgb()
            # For 3ds Max use bits[index] = chr(value)
            bits[h * 4 + 0] = b
            bits[h * 4 + 1] = g
            bits[h * 4 + 2] = r
            # [h * 4 + 3] = 0xff

        img = QImage(bits, 1, ih, QImage.Format_RGB32)
        self._pixmap = QPixmap.fromImage(img).scaled(self.minimumSize() - QSize(4, 4), Qt.IgnoreAspectRatio, Qt.FastTransformation)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        brush = self.palette().window().color()
        painter.fillRect(self.rect(), brush)
        painter.drawPixmap(2, 2, self._pixmap)
        painter.save()
        pen = QPen(QBrush(Qt.black), 2., Qt.SolidLine, Qt.SquareCap, Qt.MiterJoin)
        painter.setPen(pen)
        painter.drawRect(QRect(1, self._pos * self._scale + 1, 21, 5))
        painter.restore()

    def set_pos(self, y):
        ih = self._size.height() - 1
        self._pos = clamp(y, 0, ih)
        hue = int(360 * self._pos / ih)
        self.update()
        self.changed.emit(hue)

    def set_remap_pos(self, y):
        # Remap mouse position
        y = int(y / self._scale)
        self.set_pos(y)

    def mouseMoveEvent(self, event):
        self.set_remap_pos(event.pos().y() - 2)
        event.accept()

    def mousePressEvent(self, event):
        self.set_remap_pos(event.pos().y() - 2)
        event.accept()

    def keyPressEvent(self, event):
        key = event.key()
        if key in [Qt.Key_Left, Qt.Key_Right, Qt.Key_Up, Qt.Key_Down]:
            y = self._pos
            if key == Qt.Key_Up: y -= 1
            if key == Qt.Key_Down: y += 1
            self.set_pos(y)
            event.accept()

    def scale(self, value):
        value = max(1, min(3, value))
        self._scale = value
        self._size = QSize(1, 91 * (4 - value))
        self.setFixedSize(QSize(23, self._size.height() * self._scale + 4))
        self._pos = 0
        self.draw()


class TSwatch(QWidget):
    doubleClicked = Signal()

    def __init__(self, parent, col=12, row=2):
        super(TSwatch, self).__init__(parent)
        self.setMouseTracking(True)
        self._rows = row
        self._cols = col
        self._count = self._rows * self._cols
        self._size = 23
        self._index = 0
        self._colors = [(-1, QColor(Qt.white)) for _ in range(self._count)]

        self.setMinimumSize(self._cols * self._size, self._rows * self._size)
        self.setFocusPolicy(Qt.ClickFocus)
        self.setAcceptDrops(True)

    def load_from_string(self, text):
        # TODO: implement load
        pass

    def save_to_string(self):
        # TODO: implement save
        return

    def index_from_event_pos(self, pos):
        col = min(self._cols - 1, int(pos.x() / self._size))
        row = min(self._rows - 1, int(pos.y() / self._size))
        return row * self._cols + col

    def paintEvent(self, event):
        painter = QPainter(self)

        brush = self.palette().window().color()
        painter.fillRect(self.rect(), brush)

        for y in range(self._rows):
            for x in range(self._cols):
                i = y * self._cols + x
                c = self._colors[i][1]
                r = QRect(self._size * x, self._size * y, self._size - 2, self._size - 2)
                painter.fillRect(r, QBrush(c))

        # Draw index
        painter.setCompositionMode(QPainter.RasterOp_SourceXorDestination)
        pen = QPen(QBrush(Qt.white), 2., Qt.SolidLine, Qt.SquareCap, Qt.MiterJoin)
        painter.setPen(pen)
        row = int(self._index / self._cols)
        col = int(self._index - row * self._cols)
        r = QRect(self._size * col, self._size * row, self._size - 2, self._size - 2)
        painter.drawRect(r.adjusted(1, 1, -1, -1))

    def mouseMoveEvent(self, event):
        if event.button() in [Qt.NoButton, Qt.LeftButton]:
            index = self.index_from_event_pos(event.pos())
            self.update_index(index)
            event.accept()
            return
        event.ignore()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._index = self.index_from_event_pos(event.pos())
            self.update_index(self._index)
            event.accept()
            return
        event.ignore()

    def dragEnterEvent(self, event):
        if event.mimeData().hasText() and decode_index(event.mimeData().text()) >= -1:
            event.acceptProposedAction()
            return
        event.ignore()

    def dragMoveEvent(self, event):
        pos = event.pos()
        self._index = self.index_from_event_pos(event.pos())
        self.update()
        event.acceptProposedAction()

    def dropEvent(self, event):
        if event.mimeData().hasText():
            index = decode_index(event.mimeData().text())
            if index >= -1:
                self._index = self.index_from_event_pos(event.pos())
                color = qcolor_linear_to_srgb(color_from_index(index))
                self._colors[self._index] = (index, color)
                event.acceptProposedAction()
                self.update()
                return
        event.ignore()

    def mouseDoubleClickEvent(self, event):
        # TODO: emit signal
        self._index = self.index_from_event_pos(event.pos())
        print(self._index)
        event.accept()

    def update_index(self, index):
        swatch = self._colors[index]
        color = swatch[1]
        rgb = color.rgb() & 0xFFFFFF
        (r, g, b, _) = color.getRgb()
        tip = "HEX: #{:06X}  RGB: ({:03d} {:03d} {:03d})".format(rgb, r, g, b)
        self.setToolTip(tip)
        self.update()


class TColorPreview(QWidget):
    doubleClicked = Signal()

    def __init__(self, parent):
        super(TColorPreview, self).__init__(parent)
        self._color = QColor(Qt.white)
        self._color_srgb = QColor(Qt.white)
        self._dragStartPosition = QPoint()

        menu = QMenu(self)
        menu.addAction("Copy by index", lambda: self.clipboard_color("index"))
        menu.addAction("Copy as Linear", lambda: self.clipboard_color("linear"))
        menu.addAction("Copy as sRGB", lambda: self.clipboard_color("srgb"))
        self.menu = menu

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QBrush(self._color_srgb))
        painter.setCompositionMode(QPainter.RasterOp_SourceXorDestination)
        pen = QPen(QBrush(Qt.white), 2., Qt.SolidLine, Qt.SquareCap, Qt.MiterJoin)
        painter.setPen(pen)
        painter.drawRect(self.rect().adjusted(1, 1, -1, -1))

    def mouseDoubleClickEvent(self, event):
        self.doubleClicked.emit()
        event.accept()

    def contextMenuEvent(self, event):
        self.menu.popup(event.globalPos())

    @property
    def color(self):
        return self._color

    @color.setter
    def color(self, value):
        self._color = value
        self._color_srgb = qcolor_linear_to_srgb(value)

        rgb = value.rgb() & 0xFFFFFF
        self.setToolTip("#{:06X}".format(rgb))
        r, g, b, _ = value.getRgb()
        h, s, v, _ = value.getHsv()
        # Qt returns a hue value of -1 for achromatic colors
        h = max(0, h)
        tip = "HEX: #{:06X}  RGB: ({:03d} {:03d} {:03d})  HSV: ({:03d} {:03d} {:03d})".format(rgb, r, g, b, h, s, v)
        self.setStatusTip(tip)
        self.update()

    def clipboard_color(self, mode):
        if mode == "hex":
            rgb = self._color.rgb() & 0xFFFFFF
            text = "{:06X}".format(rgb)
        elif mode == "index":
            text = encode_index(self.parentWidget().index)
        else:
            (r, g, b, _) = self._color_srgb.getRgb() if mode == "srgb" else self._color.getRgb()
            text = "{:1f} {:1f} {:1f} 1.0".format(r / 255., g / 255., b / 255.)

        clipboard = QApplication.clipboard()
        clipboard.setText(text)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragStartPosition = event.pos()

    def mouseMoveEvent(self, event):
        if event.buttons() != Qt.LeftButton:
            return
        if (event.pos() - self._dragStartPosition).manhattanLength() < QApplication.startDragDistance():
            return

        pixmap = QPixmap(23, 23)
        pixmap.fill(self._color_srgb)

        drag = QDrag(self)
        mime_data = QMimeData()
        text = encode_index(self.parentWidget().index)
        mime_data.setText(text)
        drag.setMimeData(mime_data)
        drag.setPixmap(pixmap)

        drop_action = drag.start(Qt.CopyAction)  # | Qt.MoveAction)


class TColorPicker(QWidget):
    doubleClicked = Signal()

    def __init__(self, parent=None):
        super(TColorPicker, self).__init__(parent)
        self.setFocusPolicy(Qt.ClickFocus)
        self.setWindowTitle("Color Picker")
        self._index_offset = 256

        self._swatch = TSwatch(self)
        self._swatch.move(8, 8)
        geom = self._swatch.geometry()

        self._prewiew = TColorPreview(self)
        self._prewiew.setGeometry(8, geom.bottom() + 8, 137, 48)
        self._prewiew.doubleClicked.connect(lambda: self.doubleClicked.emit())
        geom = self._prewiew.geometry()

        self._label = QLabel(self)
        self._label.setGeometry(geom.right() + 8, geom.top(), 168, geom.height())
        self._label.setFont(QFont("Courier New"))
        self._label.setText("line 1\nline 2")

        self._box_sv = TColorPickerSV(self)
        self._box_sv.setGeometry(self._box_sv.rect().translated(8, geom.bottom() + 8))
        self._box_sv.changed.connect(self.color_changed)
        self._box_sv.doubleClicked.connect(lambda: self.doubleClicked.emit())
        geom = self._box_sv.geometry()

        self._bar_hue = TColorPickerHue(self)
        self._bar_hue.setGeometry(self._bar_hue.rect().translated(geom.right() + 8, geom.top() - 1))
        self._bar_hue.changed.connect(self._box_sv.set_hue)

        br = self._bar_hue.geometry().bottomRight()
        self.setFixedSize(br.x() + 8, br.y() + 8)
		
        self._box_sv.set_hue(0)

    def keyPressEvent(self, event):
        if event.modifiers() == Qt.ShiftModifier:
            self._bar_hue.keyPressEvent(event)
        else:
            self._box_sv.keyPressEvent(event)

    def wheelEvent(self, event):
        e = QKeyEvent(QEvent.None_, Qt.Key_Down if event.delta() < 0 else Qt.Key_Up, Qt.NoModifier)
        self._bar_hue.keyPressEvent(e)
        event.accept()

    def color_changed(self, value):
        self._prewiew.color = value
        # update color info
        rgb = value.rgb() & 0xFFFFFF    # remove alpha
        (r, g, b, _) = value.getRgb()
        (h, s, v, _) = value.getHsv()
        # Qt returns a hue value of -1 for achromatic colors
        if h == -1: h = 0
        self._label.setText("HEX: #{:>06X}\nRGB: ({:03d} {:03d} {:03d})\nHSV: ({:03d} {:03d} {:03d})".format(rgb, r, g, b, h, s, v))
        self.doubleClicked.emit()

    @property
    def index(self):
        eh = self._bar_hue._pos
        eh = eh if eh < 90 else 0
        es = self._box_sv._pos.x()
        ev = self._box_sv._pos.y()
        if ev == 0 or es == 0:
            es = eh = 0
        index = self._index_offset + eh * 25 * 25 + ev * 25 + es
        return index

    @index.setter
    def index(self, value):
        eh, es, ev = get_hsv_indexes(value)
        self._bar_hue.set_pos(eh)
        self._box_sv.set_pos(QPoint(es, ev))

    @property
    def color(self):
        return self._prewiew.color

    @color.setter
    def color(self, value):
        h, s, v, _ = value.getHsv()
        # Qt returns a hue value of -1 for achromatic colors
        h = max(0, h)
        eh = int(h / 4.)
        es = int(s / 10.2)
        ev = int(v / 10.2)
        if ev == 0:
            eh = es = 0
        if ev == 255 and es == 0:
            eh = 0
        self._bar_hue.set_pos(eh)
        self._box_sv.set_pos(QPoint(es, ev))


class TMainWindow(QMainWindow):
    def __init__(self, parent=None):
        super(TMainWindow, self).__init__(parent)
        self.setWindowFlags(self.windowFlags() | Qt.MSWindowsFixedSizeDialogHint & ~Qt.WindowMaximizeButtonHint)
        self.setWindowTitle("Color Picker")

        self.setStatusBar(QStatusBar(self))

        picker = TColorPicker(self)
        self.setCentralWidget(picker)


def main():
    app = QApplication(sys.argv)
    window = TMainWindow()
    # pal = QPalette()
    # pal.setColor(QPalette.Background, QColor(100, 100, 100))
    # window.setAutoFillBackground(True)
    # window.setPalette(pal)
    window.show()
    app.exec_()


if __name__ == "__main__":
    main()
