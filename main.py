#!/usr/bin/python3
# -*- coding: utf-8 -*-

import sys
from PyQt5.QtWidgets import (QWidget, QSplitter, 
    QApplication,  QDesktopWidget, QTabWidget, 
    QMainWindow,  QAction,  qApp,  QMenu,  QFileDialog, 
    QHBoxLayout,  QVBoxLayout,  QLineEdit,  QLabel)
from PyQt5.QtGui import (QIcon)
from PyQt5.QtCore import (Qt)
from hierarchy import Hierarchy
from editor import CodeEditor
from fileTree import FileTree

""""
Class Name: Main
Class Description: Main file for the design explorer that creates the GUI and handles
user interaction.
"""
class Main(QMainWindow):
    
    # initial dimensions for the window
    def __init__(self):
        super().__init__()
        self.left = 10
        self.top = 10
        self.width = 940
        self.height = 480
        self.title = 'Design Explorer'
        self.initUI()
        
    """" 
    Creates the main parts of the explorer and uses QSplitter and BoxLayouts to
    make the layout of the explorer.
    """
    def initUI(self):
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)
        
        #tabbed view that displays the design hierarchy in tree form
        self.folderView = QTabWidget()
        self.constraintView = FileTree(self,  None,  None)
        self.hierarchy = Hierarchy(self)
        self.fileTree = FileTree(self,  self.hierarchy,  self.constraintView)
        self.folderView.addTab(self.fileTree,  "Files")
        self.folderView.addTab(self.hierarchy, "Hierarchy")
        self.folderView.addTab(self.constraintView,  "Constraints")
        
        #parts of the search bar to search for certain files in the tabbed view
        searchBarLabel = QLabel()
        searchBarLabel.setText("Search modules:")
        self.searchBar = QLineEdit()
        self.searchBar.setStatusTip('Search modules')
        self.searchBar.textChanged.connect(self.fileTree.searchModule)
        
        #tabbed view to view and edit files
        self.fileView = QTabWidget()
        self.fileView.tabBarClicked.connect(self.openTab)
        self.fileView.tabCloseRequested.connect(self.closeTab)
        self.fileView.setTabsClosable(True)
        self.fileView.setMovable(True)
        
        #helpers to keep track of which editor is being viewed by the user
        self.textEdit = CodeEditor("verilog")
        self.editors = {}
        self.filePaths = {}
        
        #creates the basic layout for the user interface
        wid = QWidget(self)
        self.setCentralWidget(wid)
        rightSide = QWidget(self)
        leftSide = QWidget(self)
        hbox = QHBoxLayout(wid)
        vrbox = QVBoxLayout(rightSide)
        vrbox.addWidget(self.fileView)
        vlbox = QVBoxLayout(leftSide)
        vlbox.addWidget(searchBarLabel)
        vlbox.addWidget(self.searchBar)
        vlbox.addWidget(self.folderView)
        rightSide.setLayout(vrbox)
        leftSide.setLayout(vlbox)
        main_splitter = QSplitter(Qt.Horizontal)
        main_splitter.addWidget(leftSide)
        main_splitter.addWidget(rightSide)
        main_splitter.setStretchFactor(0,1)
        main_splitter.setStretchFactor(1,6)
        hbox.addWidget(main_splitter)
        wid.setLayout(hbox)
        
        # set up the status bar and file menus
        self.statusBar()
        self.setUpMenus()
        self.center()    
        self.show()
    
    
    """"
    Creates and links the actions to be called when the user selects something
    on the status menu or file menu.
    """
    def setUpMenus(self):
        # exit and quit out of the explorer
        exitAct = QAction(QIcon('exit.png'), '&Exit', self)        
        exitAct.setShortcut('Ctrl+Q')
        exitAct.setStatusTip('Exit application')
        exitAct.triggered.connect(qApp.quit)
         
        # open a new file tab in the file view
        openFile = QAction(QIcon('open.png'), 'Open', self)
        openFile.setShortcut('Ctrl+O')
        openFile.setStatusTip('Open new File')
        openFile.triggered.connect(self.showDialog)
         
        # save the current file being edited
        saveFile = QAction("&Save File", self)
        saveFile.setShortcut("Ctrl+S")
        saveFile.setStatusTip('Save File')
        saveFile.triggered.connect(self.file_save)
        saveAsFile = QAction("&Save File", self)
        saveAsFile.setStatusTip('Save File')
        saveAsFile.triggered.connect(self.file_save)
        
        # set the directory that will be searched for Verilog modules
        openDir = QAction('Set Directory',  self)
        openDir.setStatusTip('Set Directory')
        openDir.triggered.connect(self.openDirectory)
        
        # generates a hierarchy based on the verilog modules in the folder view
        generateHierarchy = QAction('Generate Hierarchy',  self)
        generateHierarchy.setStatusTip('Generate Hierarchy')
        generateHierarchy.triggered.connect(self.hierarchy.readFiles)
        
        # undo and redo actions made in the current editor
        undo = QAction(QIcon('undo1.png'), 'Undo',  self)
        undo.triggered.connect(self.undo)
        redo = QAction(QIcon('redo1.png'), 'Redo',  self)
        redo.triggered.connect(self.redo)
         
        # adding all actions to the menu bar
        menubar = self.menuBar()
        fileMenu = menubar.addMenu('File')
        fileMenu.addAction(exitAct)
        fileMenu.addAction(openFile)
        fileMenu.addAction(saveFile)
        fileMenu.addAction(saveAsFile)
        fileMenu.addAction(openDir)
        
        # adding all actions to the tool bar
        self.toolbar = self.addToolBar("Generate Hierarchy")
        self.toolbar.addAction(generateHierarchy)
        self.toolbar = self.addToolBar('Undo')
        self.toolbar.addAction(undo)
        self.toolbar.addAction(redo)
    
    # centers the browser to the middle of the screen
    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())
    
    # create and set up the context menu
    def contextMenuEvent(self, event):
        cmenu = QMenu(self)
        opnAct = cmenu.addAction("Open")
        quitAct = cmenu.addAction("Quit")
        action = cmenu.exec_(self.mapToGlobal(event.pos()))
           
        if action == quitAct:
            qApp.quit()
        elif action == opnAct:
            self.showDialog
    
    # saves the current file being edited
    def file_save(self):
        if (self.fileView.currentIndex() >= 0):
            self.hierarchy.fileSaved = True
            name = self.filePaths[self.fileView.tabText(self.fileView.currentIndex())]
            if (not name == ""):
                file = open(name,'w')
                text = self.textEdit.text()
                file.write(text)
                file.close()
    
    # saves the current file being edited as a new name
    def file_saveAs(self):
        if (self.fileView.currentIndex() >= 0):
            self.hierarchy.fileSaved = True
            name = QFileDialog.getSaveFileName(self, 'Save File')
            if name[0]:
                file = open(name[0],'w')
                text = self.textEdit.text()
                file.write(text)
                file.close()
    
    # opens a dialog to open a file to be edited
    def showDialog(self):
        fname = QFileDialog.getOpenFileName(self, 'Open file', '/home')
        if fname[0]:
            f = open(fname[0], 'r')
            with f:
                data = f.read()
                fileNames = fname[0].split("/")
                fileName = fileNames[len(fileNames) - 1]
                # if the file's tab is already open, select that tab
                for index in range(self.fileView.count()):
                    if (self.fileView.tabText(index) == fileName):
                        self.openTab(index)
                        return
                index = self.addTab(fileName,  data,  fname[0])
                self.fileView.setCurrentWidget(self.editors[fileName])
                self.fileView.setCurrentIndex(index)
    
    # sets a new directory and retrieves its files
    def openDirectory(self):
        self.fileTree.showDialog()
    
    # adds a new tab to the fileview that can be viewed
    def addTab(self, name, data,  path):
        editor = CodeEditor("verilog")
        index = self.fileView.addTab(editor,  name)
        self.editors[name] = editor
        self.filePaths[name] = path
        editor.setText(data)
        self.textEdit = editor
        return index
    
    # opens a tab in the file view to be edited
    def openTab(self, index):
        name = self.fileView.tabText(index)
        self.fileView.setCurrentWidget(self.editors[name])
        self.fileView.setCurrentIndex(index)
        self.textEdit = self.editors[name]
    
    # closes a tab in the file view
    def closeTab(self,  index):
        del self.editors[self.fileView.tabText(index)]
        del self.filePaths[self.fileView.tabText(index)]
        self.fileView.removeTab(index)
    
    # undos the last action made in the current editor
    def undo(self):
        if (self.textEdit.isUndoAvailable()):
            self.textEdit.undo()
    
    # redos the last action in the current editor
    def redo(self):
        if (self.textEdit.isRedoAvailable()):
            self.textEdit.redo()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = Main()
    sys.exit(app.exec_())
