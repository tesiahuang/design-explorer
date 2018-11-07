from PyQt5.QtGui import *
from PyQt5.Qsci import QsciScintilla, QsciLexerVerilog, QsciLexerVHDL
from PyQt5.QtWidgets import QAction, QLineEdit, QGridLayout, QPushButton, QDialog, QLabel
from PyQt5.QtCore import Qt

""""
Class Name: CodeEditor
Class Description: Uses QsciScintilla to make a code editor for verilog files.
Can search currently open files for words + replace them and undo/redo edits.
"""
class CodeEditor(QsciScintilla):
    ARROW_MARKER_NUM = 8

    def __init__(self, type, parent=None):
        super(CodeEditor, self).__init__(parent)
        self.parent = parent
        self.type = type
        
        # indent settings
        self.setIndentationsUseTabs(True)
        self.setTabWidth(4)
        self.setIndentationGuides(True)
        self.setAutoIndent(True)
        
        self.setWrapMode(QsciScintilla.WrapWord)
        self.setWrapIndentMode(QsciScintilla.WrapIndentIndented)
        
        self.setCaretForegroundColor(QColor("#ff0000ff"))
        self.setCaretLineVisible(True)
        self.setCaretLineBackgroundColor(QColor("#1fff0000"))
        
        # margin settings
        self.setMarginType(0,  QsciScintilla.NumberMargin)
        self.setMarginWidth(0,  "0000000000")
        self.setMarginsForegroundColor(QColor("#ff0000ff"))
        
        # font settings
        font = QFont()
        font.setFamily('Courier')
        font.setFixedPitch(True)
        font.setPointSize(10)
        self.setFont(font)
        self.setMarginsFont(font)

        self.setBraceMatching(QsciScintilla.SloppyBraceMatch)
        
        # set what lexer this editor will use
        self.vhdlLexer = QsciLexerVHDL()
        self.verilogLexer = QsciLexerVerilog()
        if self.type == "vhdl":
            self.setLexer(self.vhdlLexer)
            self.lexer().setFoldAtBegin(True)
            self.lexer().setFoldAtParenthesis(True)
        else:
            self.setLexer(self.verilogLexer)
            self.lexer().setFoldAtModule(True)
            self.lexer().setFoldPreprocessor(True)
        self.lexer().setDefaultFont(font)
        self.lexer().setFont(font)

        self.lexer().setFoldAtElse(True)
        self.lexer().setFoldComments(True)
        self.setFolding(QsciScintilla.BoxedTreeFoldStyle)

        # auto complete settings
        self.setAutoCompletionSource(QsciScintilla.AcsDocument)
        self.setAutoCompletionThreshold(2)
        self.setAutoCompletionCaseSensitivity(False)
        self.setAutoCompletionReplaceWord(False)
        self.setAutoCompletionUseSingle(QsciScintilla.AcusNever)

        self.setCallTipsStyle(QsciScintilla.CallTipsNoContext)
        self.setCallTipsVisible(0)

        self.SendScintilla(QsciScintilla.SCI_SETHSCROLLBAR, 0)

    # adds shortcuts to find words in file
    def contextMenuEvent(self, event):
        cmenu = self.createStandardContextMenu()
        find = QAction('Find...', self)
        find.setStatusTip("Search for text in current file")
        find.setShortcut('Ctrl+F')
        find.triggered.connect(self.findText)

        cmenu.addAction(find)
        cmenu.exec_(self.mapToGlobal(event.pos()))

    def findText(self):
        self.finder = TextFinder(self)

class TextFinder(QDialog):
    """
    The dialog that comes up when the user wants to search for text
    """
    def __init__(self, parent):
        super(TextFinder, self).__init__(parent)
        self.editor = parent
        self.setStyleSheet('font-size: 10pt; font-family: Consolas;')
        self.setWindowTitle("Find")
        self.initUI()

    def initUI(self):
        self.pos = -1
        self.input = QLineEdit()
        self.input.setMaxLength(100)
        self.input.setAlignment(Qt.AlignLeft)
        self.input.setFixedWidth(200)

        self.replace = QLineEdit()
        self.replace.setMaxLength(100)
        self.replace.setAlignment(Qt.AlignLeft)
        self.replace.setFixedWidth(200)

        enter = QPushButton("Find Next")
        enter.clicked.connect(self.findNextText)
        findPrev = QPushButton("Find Previous")
        findPrev.clicked.connect(self.findPrevText)
        replaceB = QPushButton("Replace")
        replaceB.clicked.connect(self.replaceText)
        replaceAll = QPushButton("Replace All")
        replaceAll.clicked.connect(self.replaceTextAll)

        self.grid = QGridLayout()
        t = QLabel()
        t.setText("Search for: ")
        l = QLabel()
        l.setText("Replace with:")

        self.grid.addWidget(t, 0, 0)
        self.grid.addWidget(self.input, 0, 1)
        self.grid.addWidget(enter, 0, 2)
        self.grid.addWidget(findPrev, 1, 2)
        self.grid.addWidget(l, 2, 0)
        self.grid.addWidget(self.replace, 2, 1)
        self.grid.addWidget(replaceB, 2, 2)
        self.grid.addWidget(replaceAll, 3, 2)
        self.setLayout(self.grid)
        self.show()

    def findNextText(self):
        if len(self.input.text()) > 0:
            self.editor.findFirst(self.input.text(), False, False, False, True)

    def findPrevText(self):
        if len(self.input.text()) > 0:
            self.editor.findFirst(self.input.text(), False, False, False, True)

    def replaceText(self):
        if self.editor.selectedText() != "" and self.editor.selectedText() == self.input.text():
            self.editor.replace(self.replace.text())
            self.editor.findFirst(self.input.text(), False, False, False, True)

    def replaceTextAll(self):
        self.editor.findFirst(self.input.text(), False, False, False, True)
        while self.input.text() in self.editor.text():
            self.replaceText()
