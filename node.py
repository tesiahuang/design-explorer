from PyQt5.QtWidgets import (QMessageBox)
from fileNode import FileNode
import re


""""
Class Name: Node
Class Description: Represents a node found in the Hierarchy tabbed view of the
main window. Each node represents a module declared in the Verilog files found
in the selected directory. Parses through all files and determines a hierarchy of
these modules.
"""
class Node (FileNode):
    def __init__(self, title, path, fileTree, fileName, module_name=""):
        super(FileNode, self).__init__()
        self.name = title
        self.module_name = module_name
        self.path = path
        self.fileTree = fileTree
        self.fileName = fileName
        self.nodeChildren = [] # keep track of all the children of the node
        self.errorModules =  [] # keep track of all instantiated modules that were not declared
        self.setText(0,  title)
        self.stack = [] # helper to parse parentheses
        self.parens = [] # helper to parse parentheses
    
    # helper method for copy, copies all the necesarry data from node
    def copyData(self,  node):
        self.parseData = node.parseData
        self.generateConditions = node.generateConditions.copy()
        self.parameters = node.parameters.copy()
    
    # returns a deep copy of self, including creating new children nodes
    def copy(self):
        node = Node(self.name, self.path,  self.fileTree,  self.fileName, self.module_name)
        node.setText(0,  self.name + " (" + self.module_name + ")")
        for c in self.nodeChildren: # need copy of children nodes too
            node.addChild(c.copy())
        node.copyData(self)
        self.fileTree.allNodes.append(node) # new node added to view
        return node

    """"
    Adds a new child node to self, with moduleName as its module name, instanceName as its
    name, and params as the parameters to passed to the new child node.
    """
    def insertInstance(self,  moduleName,  instanceName,  params):
        if (moduleName in self.fileTree.nodePaths): # check if module has been found
            fileName = self.fileTree.nodeFiles[moduleName]
            # create new child node
            child = Node(instanceName,  self.fileTree.nodePaths[moduleName],  self.fileTree, 
                self.fileTree.nodeFiles[moduleName], moduleName)
            child.setText(0,  instanceName + " (" + moduleName + ")")
            child.copyData(self.fileTree.nodes[moduleName])
            # copy over all children if the file has already been explored
            if (self.fileTree.nodesExplored[fileName]):
                for c in self.fileTree.nodes[moduleName].nodeChildren:
                    copy = c.copy()
                    child.addChild(copy)
                    child.nodeChildren.append(copy)
            # update new parameters for the child node
            if (len(params) > 0):
                self.updateParameters(child,  params)
            self.fileTree.hasParent[moduleName] = True
            self.fileTree.allNodes.append(child)
            self.nodeChildren.append(child)
            self.addChild(child)
            # read file to check for any modules instantiated and add children accordingly
            if (not self.fileTree.nodesExplored[fileName]):
                child.readFile()

        else: # module declaration not found, create a module but send a message box informing user
            child = Node(instanceName, "",  self.fileTree, "", moduleName)
            self.nodeChildren.append(child)
            self.addChild(child)
            if (not moduleName in self.errorModules):
                message = QMessageBox()
                message.setWindowTitle("Warning")
                message.setText("Could not find source file for module " 
                    + moduleName + " called in file " + self.fileName + " while parsing.")
                message.exec();
                self.errorModules.append(moduleName)
    
    # search file for any module instantiations, call insertInstance for each one found
    def readFile(self):
        if re.search(r'#', self.parseData, re.M): # search for parameter instantiations
            withParamInst = re.findall('(\s*(\w+)\s*#\((\s*\..*\n?)*\s*\)\s*\)\s*([^\(\)\.\s#]+)\s*\()',  self.parseData,  re.M)
            for inst in withParamInst:
                params = re.findall('\.(\w+)\s*\(([\w\'`]+)\)',  inst[0],  re.M)
                self.insertInstance(inst[1],  inst[3],  params)
        if re.search(r'.*\.',  self.parseData,  re.M): # search for regular instantiations
            instances = re.findall('\s*([^\(\)\.\s#]+)\s+([^\(\)\.\s#]+)\s*\(\s*\n*\s*\.\w+',  self.parseData,  re.M)
            for inst in instances:
                self.insertInstance(inst[0],  inst[1],  {})
        self.fileTree.nodesExplored[self.fileName] = True # finished parsing file

    # node = node whose parameters to update, newParams = new parameter values
    def updateParameters(self,  node,  newParams):
        for param in newParams:
            if (param[1].isdigit() or "'" in param[1]): # new value is a number
                node.parameters[param[0]] = self.extractNumber(param[1])
            elif (param[1][0] == "`"): # new value is a define variable
                node.parameters[param[0]] = self.extractNumber(self.fileTree.defineVars[param[1][1:]])
            else: # else, evaluate to find the new value
                node.parameters[param[0]] = self.evaluate(param[1])
    
    # given any generate conditions, parses them to check how many new modules to add/delete to the tree
    def parseConditions(self):
        for condition in self.generateConditions:
            # find the condition block from beginning to end
            block = self.generateConditions[condition]
            # find all module instantiations made in the condition blocks
            paramInstances = re.findall('(\s*(\w+)\s*#\((\s*\..*\n?)*\s*\)\s*\)\s*([^\(\)\.\s#]+)\s*\()',  block,  re.M)
            instances = re.findall('\s*([^\(\)\.\s#]+)\s+([^\(\)\.\s#]+)\s*\(\s*\n*\s*\.\w+',  block,  re.M)
            if (";" in condition): # evaluate as a for loop
                count = self.evalLoop(condition)
                paramInstances = []
                instances = []
                while ("for " in block): # for nested for loops
                    forBlock = block[block.find("for ")+4:block.find("end")+3]
                    repl = block[block.find("for "):block.find("end")+3]
                    if ("." in forBlock): # only add if there's a module instantiation
                        tempP = re.findall('(\s*(\w+)\s*#\((\s*\..*\n?)*\s*\)\s*\)\s*([^\(\)\.\s#]+)\s*\()',  forBlock,  re.M)
                        temp = re.findall('\s*([^\(\)\.\s#]+)\s+([^\(\)\.\s#]+)\s*\(\s*\n*\s*\.\w+',  forBlock,  re.M)
                        forLoop = forBlock[:forBlock.find("begin")].lstrip().rstrip()
                        multiply = self.evalLoop(forLoop)
                        paramInstances = paramInstances + (tempP * multiply)
                        instances = instances + (temp * multiply)
                    block = block.replace(repl,  "")
                # add extra instantiations to the tree
                paramInstances = paramInstances + re.findall('(\s*(\w+)\s*#\((\s*\..*\n?)*\s*\)\s*\)\s*([^\(\)\.\s#]+)\s*\()',  block,  re.M)
                instances = instances + re.findall('\s*([^\(\)\.\s#]+)\s+([^\(\)\.\s#]+)\s*\(\s*\n*\s*\.\w+',  block,  re.M)
                deleteNodes = []
                for inst in paramInstances:
                    for ind in range(self.childCount()):
                        if (self.child(ind).name == inst[3] and self.child(ind).module_name == inst[1]):
                            deleteNodes.append(self.child(ind))
                            for index in range(count): # pass parameters on
                                params = re.findall('\.(\w+)\s*\(([\w\'`]+)\)',  inst[0],  re.M)
                                self.insertInstance(inst[1],  inst[3],  params)
                            break
                for deleteNode in deleteNodes:
                    self.removeChild(deleteNode)
                for inst in instances:
                    for node in self.nodeChildren:
                        if (node.name == inst[1] and node.module_name == inst[0]):
                            for ind in range(count - 1):
                                self.insertInstance(inst[0],  inst[1],  {})
            else: # evaluate as a if statement
                condition = self.parseParens(condition, True) # parse any parentheses
                if (not self.parseIf(condition)):
                    toDelete = [] # if condition is false, need to delete node instantiations
                    for inst in paramInstances: # delete parameter instances
                        for ind in range(self.childCount()):
                            if (self.child(ind).name == inst[3] and self.child(ind).module_name == inst[1]):
                                toDelete.append(self.child(ind))
                    for inst in instances: # delete regular instances
                        for node in self.nodeChildren:
                            if (node.name == inst[1] and node.module_name == inst[0]):
                                toDelete.append(self.child(ind))
                    for node in toDelete: # delete necessary nodes
                        self.removeChild(node)
                    self.stack.clear() # clear parentheses helpers
                    self.parens.clear()
        self.generateConditions.clear()
    
    # given a for loop condition, evaluates the number of times the loop iterates and returns it
    def evalLoop(self,  condition):
        loopParts = re.findall('\s*\(\w+\s*=\s*(\w+)\s*;\s*\w+\s*([<>=]+)\s*(\w+)\s*;.*=\s*\w+\s*([\+\*/-]+)\s*(\w)',  condition,  re.M)
        start = self.evaluate(loopParts[0][0]) # value the loop starts at
        op1 = loopParts[0][1] # comparison operator to compare the value
        end = int(self.evaluate(loopParts[0][2]),  2) # what the value will be compared to
        op2 = loopParts[0][3] # what increment is used
        inc = str(int(self.evaluate(loopParts[0][4]),  2)) # how much is incremented
        count = int(start,  2) # convert start to a regular integer
        # run for loop to figure out how many instantiations are made
        if (op1 == "<"):
            while (count < end):
                count = int(self.evaluate(str(count) + op2 + inc),  2)
        elif (op1 == ">"):
            while count > int(end):
                count = int(self.evaluate(str(count) + op2 + inc),  2)
        elif (op1 == "<="):
            while count <= int(end):
                count = int(self.evaluate(str(count) + op2 + inc),  2)
        elif (op1 == ">="):
            while count >= int(end):
                count = int(self.evaluate(str(count) + op2 + inc))
        elif (op1 == "=="):
            while count == int(end):
                count = int(self.evaluate(str(count) + op2 + inc))
        return count
    
