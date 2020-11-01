import os
import MaxPlus
from PySide.QtCore import Qt
from PySide.QtCore import QDirIterator
from PySide.QtCore import QSize
from PySide.QtGui import QIcon
from PySide.QtGui import QWidget
from PySide.QtGui import QToolButton
from PySide.QtGui import QHBoxLayout
from PySide.QtGui import QVBoxLayout
from PySide.QtGui import QSortFilterProxyModel
from PySide.QtGui import QLineEdit
from PySide.QtGui import QListView
from PySide.QtGui import QStringListModel
from PySide.QtGui import QLabel
from PySide.QtGui import QImageReader
from PySide.QtGui import QPixmap
from PySide.QtGui import QImage


class TListModel(QStringListModel):
	def __init__(self, parent=None):
		super(TListModel, self).__init__(parent)
		self.supported_image_formats = set()
		self.paths = []
		self.icons = []
		self.load_icons()
		
	def rowCount(self, parent):
		return len(self.paths)
		
	def data(self, index, role=Qt.DisplayRole):
		row = index.row()
		
		if role in (Qt.DisplayRole, Qt.EditRole):
			return str(self.paths[row])

		if role == Qt.DecorationRole:
			return self.icons[row]
		
		if role == Qt.SizeHintRole:
			return QSize(100, 48)

	def load_icons(self):
		for format in QImageReader.supportedImageFormats():
			self.supported_image_formats.add('.' + str(format))
		
		it = QDirIterator(":", QDirIterator.Subdirectories)
		while it.hasNext():
			path = it.next()
			fn, ext = os.path.splitext(path)
			if ext in self.supported_image_formats:
				image = QImage(path)
				self.icons.append(image)
				self.paths.append(path)

class IconExplorer(QWidget):
	def __init__(self, parent=None):
		super(IconExplorer, self).__init__(parent)
		self.setAttribute(Qt.WA_DeleteOnClose)
		self.setWindowTitle("3ds Max Icon Explorer")
		self.setup_ui()
		self.resize(800, 600)
	
	def setup_ui(self):
		main_layout = QHBoxLayout(self)
		
		edt = QLineEdit(self)
		edt.setPlaceholderText("Wildcard filter")
		btn = QToolButton(self)
		btn.clicked.connect(self.set_icon)
		
		layout = QHBoxLayout(self)
		layout.addWidget(edt)
		layout.addWidget(btn)
		
		layout2 = QVBoxLayout()
		layout2.addLayout(layout)
		
		model = TListModel(self)
		proxy = QSortFilterProxyModel(self)
		proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)
		proxy.setSourceModel(model)
		edt.textChanged.connect(proxy.setFilterWildcard)
		
		list = QListView()
		list.setModel(proxy)
		selection_model = list.selectionModel()
		selection_model.currentChanged.connect(self.currentChanged)
		layout2.addWidget(list)
		
		main_layout.addLayout(layout2)
		
		image = QLabel("Select icon", self)
		image.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter);
		image.setMinimumWidth(256)
		main_layout.addWidget(image)
		
		self.btn = btn
		self.edt = edt
		self.image = image
		self.list = list
		self.proxy = proxy
		self.model = model
		self.selection_model = selection_model

	def currentChanged(self, current, previous):
		row = current.row()
		proxyIndex = self.proxy.index(row, 0)
		sourceIndex = self.proxy.mapToSource(proxyIndex)
		row = sourceIndex.row()
		image = self.proxy.sourceModel().icons[row]
		self.image.setPixmap(QPixmap(image));
		
	def set_icon(self):
		i = self.list.currentIndex()
		if i is not None:
			path = self.model.data(i, Qt.DisplayRole)
			ico = QIcon(path)
			self.btn.setIcon(ico)

		
if __name__ == '__main__':
	wnd = IconExplorer(MaxPlus.GetQMaxWindow())
	wnd.show()