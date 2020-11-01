import sys
import ctypes
from array import array
from pathlib import Path
from subprocess import run
from os.path import join, dirname, realpath
from PySide2.QtCore import Qt
from PySide2.QtCore import QFileInfo
from PySide2.QtCore import Signal
from PySide2.QtGui import QMouseEvent
from PySide2.QtGui import QColor
from PySide2.QtGui import QVector4D
from PySide2.QtGui import QOpenGLFunctions
from PySide2.QtGui import QSurfaceFormat
from PySide2.QtGui import QOpenGLTexture
from PySide2.QtGui import QOpenGLShader
from PySide2.QtGui import QOpenGLShaderProgram
from PySide2.QtGui import QOpenGLVertexArrayObject
from PySide2.QtGui import QOpenGLBuffer
from PySide2.QtGui import QMatrix4x4
from PySide2.QtWidgets import QFileIconProvider
from PySide2.QtWidgets import QApplication
from PySide2.QtWidgets import QMainWindow
from PySide2.QtWidgets import QWidget
from PySide2.QtWidgets import QVBoxLayout
from PySide2.QtWidgets import QHBoxLayout
from PySide2.QtWidgets import QPushButton
from PySide2.QtWidgets import QLabel
from PySide2.QtWidgets import QColorDialog
from PySide2.QtWidgets import QOpenGLWidget
from PySide2.QtWidgets import QStatusBar
from OpenGL import GL
# Pillow
from PIL import Image, UnidentifiedImageError
from PIL.ImageQt import ImageQt


class TGLViewport(QOpenGLWidget, QOpenGLFunctions):
	def __init__(self, parent=None):
		QOpenGLWidget.__init__(self, parent)
		QOpenGLFunctions.__init__(self)
		self.setMinimumSize(32, 32)

		self.info = ""
		self._supported_images = ["TGA", "PNG", "JPG", "JPEG", "TIF", "TIFF", "BMP", "DDS"]

		# indices
		indices = [0, 1, 3, 1, 2, 3]
		self._indices = array('I', indices)

		# vertices
		# 3 position | 2 texture coord
		vertex = [
			 1.0,  1.0, 0.0, 1.0, 1.0,  # top right
			 1.0, -1.0, 0.0, 1.0, 0.0,  # bottom right
			-1.0, -1.0, 0.0, 0.0, 0.0,  # bottom left
			-1.0,  1.0, 0.0, 0.0, 1.0   # top left
		]
		self._vertex = array('f', vertex)

		# opengl data related
		self._program = QOpenGLShaderProgram()
		self._program_bg = QOpenGLShaderProgram()
		self._vao = QOpenGLVertexArrayObject()
		self._vbo = QOpenGLBuffer(QOpenGLBuffer.VertexBuffer)
		self._texture = None
		self._texture_size = (1, 1)
		self._location = ()

		self._colors_default = (
			QColor.fromRgbF(0.65, 0.65, 0.65, 1.0),
			QColor.fromRgbF(0.90, 0.90, 0.90, 1.0)
		)
		self._u_colors = self._colors_default
		self._height = QVector4D(0, self.height(), 0, 0)

		self._u_channels = QMatrix4x4(
			1, 0, 0, 0,
			0, 1, 0, 0,
			0, 0, 1, 0,
			0, 0, 0, 0
		)

	def initializeGL(self):
		# Set up the rendering context, define display lists etc.
		self.initializeOpenGLFunctions()
		self.glClearColor(0.2, 0.0, 0.2, 0.0)
		self.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)

		# shader code (OpenGL ES)
		# texture
		vs_source_es = """
		attribute highp vec3 Pos;
		attribute highp vec2 UV;
		uniform highp vec2 Scale;
		varying highp vec2 oUV;
		void main() {
			gl_Position = vec4(Pos * vec3(Scale, 1.0), 1.0);
			oUV = UV;
		}
		"""
		ps_source_es = """
		varying highp vec2 oUV;
		uniform sampler2D Texture;
		uniform highp mat4 Channels;
		uniform highp vec4 Add;
		void main() {
			gl_FragColor = texture2D(Texture, oUV * vec2(1.0, -1.0)) * Channels;
			gl_FragColor.a += (1.0 - Channels[3][3]);
		}
		"""
		# background
		vs_grid_es = """
		attribute highp vec3 Pos;
		void main() {
			gl_Position = vec4(Pos, 1.0);
		}
		"""
		ps_grid_es = """
		uniform highp vec4 Color1;
		uniform highp vec4 Color2;
		uniform highp vec4 Height;
		void main() {
			highp vec2 a = floor((Height.xy - gl_FragCoord.xy) / 64.0);
			highp float even = mod(a.x + a.y, 2.0);
			highp vec3 c = mix(Color1.rgb, Color2.rgb, even);
			gl_FragColor = vec4(c, 1);
		}
		"""

		# program - texture
		# shader
		vs = self.__create_shader(QOpenGLShader.Vertex, vs_source_es)
		fs = self.__create_shader(QOpenGLShader.Fragment, ps_source_es)
		# program
		self._program = QOpenGLShaderProgram(self.context())
		self._program.addShader(vs)
		self._program.addShader(fs)
		# attribute location
		self._program.bindAttributeLocation("Pos", 0)
		self._program.bindAttributeLocation("UV", 1)
		# link program
		r = self._program.link()

		# program - background
		# shader
		vs = self.__create_shader(QOpenGLShader.Vertex, vs_grid_es)
		fs = self.__create_shader(QOpenGLShader.Fragment, ps_grid_es)
		# program
		self._program_bg = QOpenGLShaderProgram(self.context())
		self._program_bg.addShader(vs)
		self._program_bg.addShader(fs)
		# attribute location
		self._program_bg.bindAttributeLocation("Pos", 0)
		# link program
		r = self._program_bg.link()

		# uniform locations
		self._location = (
			self._program.uniformLocation("Scale"),
			self._program.uniformLocation("Channels"),
			self._program_bg.uniformLocation("Color1"),
			self._program_bg.uniformLocation("Color2"),
			self._program_bg.uniformLocation("Height"),
		)

		# vao
		r = self._vao.create()
		r = self._vao.bind()
		# vbo
		r = self._vbo.create()
		self._vbo.setUsagePattern(QOpenGLBuffer.StaticDraw)
		r = self._vbo.bind()
		sz_float = ctypes.sizeof(ctypes.c_float)
		self._vbo.allocate(self._vertex.tobytes(), sz_float * len(self._vertex))
		self._vao.release()
		# texture
		self.set_texture(r"C:")

	def resizeGL(self, width, height):
		self.__update_scale(width, height)
		self._height = QVector4D(0, self.height(), 0, 0)
		self.glViewport(0, 0, width, height)

	def paintGL(self):
		SZ_FLOAT = ctypes.sizeof(ctypes.c_float)

		# draw the scene
		self.glClear(GL.GL_COLOR_BUFFER_BIT)

		self._vao.bind()

		# background
		self._program_bg.bind()
		self._program.setAttributeBuffer(0, GL.GL_FLOAT, 0, 3, 5 * SZ_FLOAT)
		self._program.enableAttributeArray(0)
		self._program.setUniformValue(self._location[2], self._u_colors[0])
		self._program.setUniformValue(self._location[3], self._u_colors[1])
		self._program.setUniformValue(self._location[4], self._height)
		self.glDrawElements(GL.GL_TRIANGLES, len(self._indices), GL.GL_UNSIGNED_INT, self._indices.tobytes())

		# texture
		if self._texture is None:
			return

		self.glEnable(GL.GL_BLEND)
		self._program.bind()
		self._program.setAttributeBuffer(1, GL.GL_FLOAT, 3 * SZ_FLOAT, 2, 5 * SZ_FLOAT)
		self._program.enableAttributeArray(1)
		self._program.setUniformValue(self._location[0], *self._scale)
		self._program.setUniformValue(self._location[1], self._u_channels)
		self._texture.bind()
		self.glDrawElements(GL.GL_TRIANGLES, len(self._indices), GL.GL_UNSIGNED_INT, self._indices.tobytes())
		self.glDisable(GL.GL_BLEND)

	@staticmethod
	def __create_shader(type_: QOpenGLShader.ShaderType, source):
		shader = QOpenGLShader(type_)
		r = shader.compileSourceCode(source)
		if not r:
			print(shader.log())
		return shader

	def __update_scale(self, width, height):
		# calc texture scale

		if self._texture_size[0] < width and self._texture_size[1] < height:
			self._scale = (
				self._texture_size[0] / width,
				self._texture_size[1] / height
			)
		else:
			tw = width
			th = self._texture_size[1] / self._texture_size[0] * tw
			if th > height:
				th = height
				tw = th * self._texture_size[0] / self._texture_size[1]
			self._scale = (tw / width, th / height)

	def get_gl_info(self):
		self.makeCurrent()
		info = """
			Vendor: {0}
			Renderer: {1}
			OpenGL Version: {2}
			Shader Version: {3}
			""".format(
			self.glGetString(GL.GL_VENDOR),
			self.glGetString(GL.GL_RENDERER),
			self.glGetString(GL.GL_VERSION),
			self.glGetString(GL.GL_SHADING_LANGUAGE_VERSION)
		)
		return info

	def set_channels(self, r, g, b, a):
		r, g, b, a = float(r), float(g), float(b), float(a)
		s = r + g + b
		if s > 1.1:
			self._u_channels = QMatrix4x4(
				r, 0, 0, 0,
				0, g, 0, 0,
				0, 0, b, 0,
				0, 0, 0, a
			)
		elif s < 0.1:
			self._u_channels = QMatrix4x4(
				0, 0, 0, 0,
				0, 0, 0, 0,
				0, 0, 0, 0,
				a, a, a, 0
			)
		elif a:
			self._u_channels = QMatrix4x4(
				r, 0, 0, 0,
				0, g, 0, 0,
				0, 0, b, 0,
				0, 0, 0, a
			)
		else:
			self._u_channels = QMatrix4x4(
				r, r, r, 0,
				g, g, g, 0,
				b, b, b, 0,
				0, 0, 0, a

			)
		# redraw
		self.update()

	def set_texture(self, filename):
		# load image
		p = Path(filename)
		suffix = p.suffix[1:].upper()
		try:
			if p.is_file() and suffix in self._supported_images:
				pim = Image.open(filename)
				img = ImageQt(pim)
				self.info = f"{pim.format} - {pim.size} - {pim.mode} "
			else:
				ico = QFileIconProvider().icon(QFileInfo(filename))
				pix = ico.pixmap(256, 256)
				img = pix.toImage()
				self.info = "not an image "
		except UnidentifiedImageError as e:
			print("UnidentifiedImageError:\n", e, flush=True)
			return

		self._texture_size = img.width(), img.height()
		self.__update_scale(self.width(), self.height())

		# create texture
		self.makeCurrent()
		self._texture = QOpenGLTexture(QOpenGLTexture.Target2D)
		self._texture.create()
		self._texture.bind()
		self._texture.setMinMagFilters(QOpenGLTexture.LinearMipMapLinear, QOpenGLTexture.Linear)
		self._texture.setWrapMode(QOpenGLTexture.DirectionS, QOpenGLTexture.Repeat)
		self._texture.setWrapMode(QOpenGLTexture.DirectionT, QOpenGLTexture.Repeat)
		self._texture.setData(img)
		self._texture.release()

		# redraw
		self.update()

	def set_colors(self, checkerboard, color1, color2):
		if checkerboard:
			self._u_colors = self._colors_default
		else:
			self._u_colors = (color1, color2)

		self.update()


class TRightClickButton(QPushButton):
	rightClicked = Signal(QMouseEvent)

	def __init__(self, parent=None):
		super(TRightClickButton, self).__init__(parent)
		self.setFixedWidth(24)

	def mousePressEvent(self, event):
		if event.button() == Qt.RightButton:
			self.rightClicked.emit(event)
		else:
			super(TRightClickButton, self).mousePressEvent(event)


class TViewerWindow(QMainWindow):
	def __init__(self, parent=None):
		super(TViewerWindow, self).__init__(parent)
		self.__set_title("")
		self.resize(600, 600)

		self._filename = ""

		# file info
		self._info = QLabel(self)
		# status bar
		self.status = QStatusBar(self)
		self.status.setSizeGripEnabled(True)
		self.status.insertPermanentWidget(0, self._info)
		self.setStatusBar(self.status)
		# central widget
		window = QWidget(self)
		self.setCentralWidget(window)

		# main layout
		layout = QVBoxLayout(window)
		layout.setContentsMargins(0, 0, 0, 0)
		window.setLayout(layout)

		layout_2 = QHBoxLayout(self)
		layout_2.addStretch()
		layout_2.setSpacing(0)

		layout_2.addWidget(QLabel(" Channels: "))
		button = TRightClickButton("R")
		button.setStatusTip("Show Red (Right click to toggle solo)")
		button.setCheckable(True)
		button.setChecked(True)
		button.clicked.connect(self.__slot_channels)
		button.rightClicked.connect(self.__slot_channels_right)

		self._btn_r = button
		layout_2.addWidget(button)
		button = TRightClickButton("G")
		button.setStatusTip("Show Green (Right click to toggle solo)")
		button.setCheckable(True)
		button.setChecked(True)
		button.clicked.connect(self.__slot_channels)
		button.rightClicked.connect(self.__slot_channels_right)
		self._btn_g = button
		layout_2.addWidget(button)
		button = TRightClickButton("B")
		button.setStatusTip("Show Blue (Right click to toggle solo)")
		button.setCheckable(True)
		button.setChecked(True)
		button.clicked.connect(self.__slot_channels)
		button.rightClicked.connect(self.__slot_channels_right)
		self._btn_b = button
		layout_2.addWidget(button)
		button = TRightClickButton("A")
		button.setStatusTip("Show Alpha (Right click to toggle solo)")
		button.setCheckable(True)
		button.clicked.connect(self.__slot_channels)
		button.rightClicked.connect(self.__slot_channels_right)
		self._btn_a = button

		layout_2.addWidget(button)
		layout_2.addSpacing(32)
		layout_2.addWidget(QLabel(" Background: "))
		button = QPushButton("Checkerboard")
		button.setStatusTip("Show checkerboard background")
		button.clicked.connect(self.__slot_checkerboard)
		layout_2.addWidget(button)
		button = QPushButton("Pick Color")
		button.setStatusTip("Pick solid background color")
		button.clicked.connect(self.__slot_solid_color)
		layout_2.addWidget(button)

		layout_2.addStretch()
		layout.addLayout(layout_2)

		# image viewer
		view = TGLViewport(self)
		self._viewport = view
		# view.doubleClicked.connect(self.__slot_action_open)
		view.setContextMenuPolicy(Qt.DefaultContextMenu)
		view.setStatusTip("Use context menu or double click to open")
		layout.addWidget(view)

		layout.setStretch(1, 1)
		layout.setSpacing(0)

	# @override
	def contextMenuEvent(self, event):
		if self.childAt(event.pos()) == self._viewport:
			self._menu.popup_for_file(self._filename, event.globalPos())

	def view(self, filename):
		self._filename = filename
		self.__set_title(filename)
		self._viewport.set_texture(filename)
		self._info.setText(self._viewport.info)

	def __set_title(self, title):
		if title != "":
			title = " - " + title
		self.setWindowTitle("Texture Viewer" + title)

	def __slot_action_open(self):
		run(["explorer", self._filename])

	def __slot_channels(self):
		self._viewport.set_channels(
			self._btn_r.isChecked(),
			self._btn_g.isChecked(),
			self._btn_b.isChecked(),
			self._btn_a.isChecked()
		)

	def __slot_channels_right(self, event):
		self._btn_r.setChecked(self.sender() == self._btn_r)
		self._btn_g.setChecked(self.sender() == self._btn_g)
		self._btn_b.setChecked(self.sender() == self._btn_b)
		self._btn_a.setChecked(self.sender() == self._btn_a)
		self.__slot_channels()

	def __slot_checkerboard(self):
		self._viewport.set_colors(True, None, None)

	def __slot_solid_color(self):
		color = QColorDialog.getColor(Qt.black, self, "Choose background color")
		if color.isValid():
			self._viewport.set_colors(False, color, color)


if __name__ == '__main__':
	# Create the Qt Application
	app = QApplication(sys.argv)
	# must be called before the OpenGLWidget or its parent window gets shown
	# set default OpenGL surface format
	glformat = QSurfaceFormat()
	glformat.setDepthBufferSize(24)
	glformat.setStencilBufferSize(8)
	glformat.setVersion(3, 1)
	glformat.setProfile(QSurfaceFormat.CoreProfile)
	QSurfaceFormat.setDefaultFormat(glformat)
	# Create and show the form
	form = TViewerWindow()
	form.show()
	sample = join(dirname(realpath(__file__)), "rgba.tga")
	form.view(sample)
	# Run the main Qt loop
	sys.exit(app.exec_())
