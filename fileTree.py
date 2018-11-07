from PyQt5.QtWidgets import (QTreeWidget,  QFileDialog)
from node import Node
from fileNode import FileNode
import os

""""
Class Name: FileTree
Class Description: Represents the initial view of the directory the user selects.
Displays verilog files based on their original hierarchy in the selected directory,
without generating a module-based hierarchy. Extracts all modules found in the
files to help generate a hierarchy later.
"""
class FileTree(QTreeWidget):
    
    def __init__(self, mainWindow,  hierarchy,  constraintView):
        super(QTreeWidget, self).__init__()
        self.title = 'Directory View'
        self.nodes = {} # all the nodes in the file view
        self.defineFiles = {} # the nodes that represent the define files
        self.moduleNodes = {} # the modules found in the files
        self.treeGenerated = False # keep track to see if tree needs to be cleared
        self.setHeaderHidden(True)
        self.itemDoubleClicked.connect(self.openFile)
        self.mainWindow = mainWindow
        self.hierarchy = hierarchy
        self.constraintView = constraintView
        self.dir = "" # name of current directory
        self.defineVars = {} # keep track of define vars found in define files
        self.dirNodes = {} # all the  nodes that represent a directory
        if (self.hierarchy):
            self.hierarchy.getFileTree(self) # gives hierarchy a reference to itself
    
    # opens a new tab for the file clicked
    def openFile(self, item):
        # if the file's tab is already open, select that tab
        for index in range(self.mainWindow.fileView.count()):
            if (self.mainWindow.fileView.tabText(index) == item.fileName):
                self.mainWindow.openTab(index)
                self.setView(item)
                return
        # only open nodes that are not directories
        if (not item in self.dirNodes.values()):
            f = open(item.path, 'r')
            data = f.read()
            index = self.mainWindow.addTab(item.fileName,  data,  item.path)
            self.setView(item)
            self.mainWindow.fileView.setCurrentWidget(self.mainWindow.editors[item.fileName])
            self.mainWindow.fileView.setCurrentIndex(index)
            
    
    # scrolls up/down the file so the module declaration is in the user view
    def setView(self,  item):
        if (item.type == "module"):
            num = 1
            if ("(" in item.name): # if several modules with the same name
                str = item.name.split("(", 1)[1].split(")", 1)[0]
                if (str.isdigit()):
                    num = int(str) + 1
            find = "module " + item.module_name # find the module declaration in the file
            for index in range(num):
                if (index == 0):
                    self.mainWindow.editors[item.fileName].findFirst(find,  False, True, True, True,  True,  1,  1,  True,  False)
                else:
                    self.mainWindow.editors[item.fileName].findFirst(find,  False, True,  True, True)
    
    # search bar functionality - hides all nodes that do not have str in their name
    def searchModule(self,  str):
        for dir in self.dirNodes:
            self.dirNodes[dir].setExpanded(True)
        for node in self.nodes:
            self.nodes[node].setExpanded(True)
            if (str in node or str == ""):
                self.nodes[node].setHidden(False)
            else:
                self.nodes[node].setHidden(True)
        self.hierarchy.searchModule(str)

    # shows a dialog for the user to select the root directory
    def showDialog(self):
        self.dir = QFileDialog.getExistingDirectory(self, 'Open Directory','/home',QFileDialog.ShowDirsOnly)
        self.generateTree(self.dir)

    """"
    Parses through the root directory and takes all verilog files and makes nodes
    of them, keeping the hierarchy of the original directory. Then looks through
    all the verilog files and retrieves all module declarations, parameters, and
    any if or for statements in generate blocks. Also parses defines files for t
    heir variables.
    """
    def generateTree(self,  dir):
        if (self.treeGenerated or self.hierarchy.fileSaved): # clears tree to search a new directory
            self.clear()
            self.nodes.clear()
            self.defineVars.clear()
            self.defineFiles.clear()
            self.moduleNodes.clear()
            self.dirNodes.clear()
        if dir:
            for root, dirs, files in os.walk(dir):
                # keep original hierarchy by making nodes representing directories
                rootNode = root
                for dir in dirs:
                    dirNode = FileNode(dir,  os.path.join(root,  dir),  self)
                    self.dirNodes[rootNode + "\\" + dir] = dirNode
                    if (not rootNode in self.dirNodes):
                        self.addTopLevelItem(dirNode)
                    else:
                        self.dirNodes[rootNode].addChild(dirNode)
                        self.dirNodes[rootNode].dirChildren.append(dirNode)
                # search through for Verilog files
                for file in files:
                    if file.endswith(".v"):
                        node = FileNode(file, os.path.join(root, file),  self)
                        self.nodes[file] = node
                        moduleNames = node.getModuleNames()
                        duplicateCheck = {}
                        for moduleName in moduleNames:
                            title = moduleName
                            # if several modules with the same name, differentiate them
                            if (moduleName in duplicateCheck):
                                duplicateCheck[moduleName] = duplicateCheck[moduleName] + 1
                                title = moduleName + " #" + str(duplicateCheck[moduleName])
                            else:
                                duplicateCheck[moduleName] = 0
                            # create one node for this view, another to be passed on for the hierarchy view
                            child = Node(title,  os.path.join(root,  file),  self.hierarchy,  file,  moduleName)
                            mod = Node(title,  os.path.join(root,  file),  self.hierarchy,  file,  moduleName)
                            child.parseData = moduleNames[moduleName]
                            mod.parseData = moduleNames[moduleName]
                            node.addChild(child)
                            self.moduleNodes[moduleName] = mod
                        # no module declarations, so assume it must be a defines file
                        if (len(moduleNames) == 0):
                            node.getDefines()
                            self.defineFiles[file] = node
                        # add nodes such that original hierarchy is preserved
                        if (rootNode in self.dirNodes):
                            self.dirNodes[rootNode].addChild(node)
                            self.dirNodes[rootNode].dirChildren.append(dirNode)
                        else:
                            self.addTopLevelItem(node)
                    elif (file.endswith(".tcl")):
                        node = FileNode(file,  os.path.join(root,  file),  self)
                        self.constraintView.addTopLevelItem(node)
            self.treeGenerated = True
            # remove all directory nodes that do not contain any verilog files
            for dirNode in self.dirNodes.values():
                for child in dirNode.dirChildren:
                    if (child.childCount() == 0):
                        dirNode.removeChild(child)
            delNodes = [] # helper to delete nodes
            for index in range(self.topLevelItemCount()):
                if (self.topLevelItem(index).childCount() == 0):
                    delNodes.append(index)
            for index in delNodes:
                self.takeTopLevelItem(index)
                
            # retrieve parameters for all the nodes representing the modules
            for node in self.nodes.values():
                node.getParameters()
                # copy over parsed data
                for m in node.modules:
                    self.moduleNodes[m].parseData = node.parseData
                    self.moduleNodes[m].generateConditions = node.generateConditions
                    self.moduleNodes[m].parameters = node.parameters
            
            # pass over defined variables and reference to itself to hierarchy to generate tree
            self.hierarchy.defineVars = self.defineVars
            self.hierarchy.getFileTree(self)
            self.hierarchy.generateTree(self.moduleNodes)
