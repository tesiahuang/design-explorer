from PyQt5.QtWidgets import (QTreeWidget)

""""
Class Name: Hierarchy
Class Description: Represents the widget in the Hierarchy tab of the main
interface. Given module nodes from the class FileTree, creates a hierarchy
out of those modules.
"""
class Hierarchy(QTreeWidget):
    
    def __init__(self, mainWindow):
        super(QTreeWidget, self).__init__()
        self.title = 'Hierarchy View'
        self.nodes = {} # key - module name, value - corresponding node
        self.nodePaths = {} # key - module name, value - corresponding file path
        self.nodesExplored = {} # key - file name, value - True if that file has been parsed, False otherwise
        self.hasParent = {} # key - module name, value - True if that module has a parent
        self.nodeFiles = {} # key - module name, value - file name module is found in
        self.allNodes = [] # list of all nodes in the hierarchy
        self.defineVars = {} # key - define variable, value - corresponding value
        self.setHeaderHidden(True)
        self.itemDoubleClicked.connect(self.openFile)
        self.treeGenerated = False
        self.fileSaved = False
        self.mainWindow = mainWindow
    
    # for search bar functionality - displays all nodes with str in their names + their parents
    def searchModule(self,  str):
        for node in self.allNodes:
            node.setExpanded(True) # expand all to help visualize search
            if (str in node.name or str == "" or self.searchChildren(node,  str)):
                parent = node.parent()
                while (parent != None): # set all parent nodes as visible
                    parent.setHidden(False)
                    parent = parent.parent()
                node.setHidden(False)
            else:
                node.setHidden(True)

    # helper function for searchModule: returns true if str is in the  name of any of node's children
    def searchChildren(self,  node,  str):
        for c in node.nodeChildren:
            if (str in c.name):
                return True
            self.searchChildren(c,  str)
    
    # gives a reference to the FileTree in the other tab
    def getFileTree(self,  fileTree):
        self.fileTree = fileTree
    
    # when user double clicks on a node in the widget, opens the corresponding file
    def openFile(self, item):
        # if the file is already open, set that tab to be the current viewed tab
        for index in range(self.mainWindow.fileView.count()):
            if (self.mainWindow.fileView.tabText(index) == item.fileName):
                self.mainWindow.openTab(index)
                return
        # else, add a new tab for the new file
        f = open(item.path, 'r')
        data = f.read()
        index = self.mainWindow.addTab(item.fileName,  data,  item.path)
        self.mainWindow.fileView.setCurrentWidget(self.mainWindow.editors[item.fileName])
        self.mainWindow.fileView.setCurrentIndex(index)
    
    # parse through the files of all the nodes and generate the hierarchy
    def readFiles(self):
        self.mainWindow.statusBar().showMessage('Generating Tree...')
        # reset the tree if a tree has already been generated
        if (self.treeGenerated or self.fileSaved):
            self.clear()
            self.fileTree.generateTree(self.fileTree.dir)
            self.fileSaved = False
        # read the file of all the nodes that have not already been read
        for node in self.nodes.values():
            if (not self.nodesExplored[node.fileName]):
                node.readFile()
        self.treeGenerated = True
        # remove all top level modules that have been added as children of other nodes
        for name in self.hasParent:
            if (self.hasParent[name]):
                self.takeTopLevelItem(self.indexOfTopLevelItem(self.nodes[name]))
                self.allNodes.remove(self.nodes[name])
            elif("#" in name): # remove any modules with the same name
                self.takeTopLevelItem(self.indexOfTopLevelItem(self.nodes[name]))
                self.allNodes.remove(self.nodes[name])
        # for all remaining nodes, check their generate conditions and delete any necessary nodes
        for node in self.allNodes:
            node.parseConditions()
        # reset the nodes explored for the next hierarchy to be generated
        for name in self.nodesExplored:
            self.nodesExplored[name] = False
    
    # given nodes, which is a list of Nodes that represent all the modules declared in the verilog
    # files in the directory.
    def generateTree(self,  nodes):
        modules = nodes
        if (self.treeGenerated or self.fileSaved): # clear the tree and all helper data structures to make new tree
            self.clear()
            self.nodes.clear()
            self.nodesExplored.clear()
            self.nodePaths.clear()
            self.nodeFiles.clear()
            self.hasParent.clear()
            self.allNodes.clear()
            self.treeGenerated = False
        for node in modules.values(): # set up default values for all helper data structures
            self.nodes[node.module_name] = node
            self.allNodes.append(node)
            self.nodePaths[node.module_name] = node.path
            self.nodesExplored[node.fileName] = False
            self.hasParent[node.module_name] = False
            self.nodeFiles[node.module_name] = node.fileName
        self.addTopLevelItems(modules.values())
