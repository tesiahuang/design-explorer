from PyQt5.QtWidgets import (QTreeWidgetItem)
import re
from operator import xor
import parser

""""
Class Name: FileNode
Class Description: Represents a node in the file view of the explorer. Parses through
a given file in order to find the modules declared in it along with their parameters.
Also looks through and keeps track of generate statements.
"""
class FileNode (QTreeWidgetItem):
    def __init__(self, title, path,  fileTree):
        super(QTreeWidgetItem, self).__init__()
        self.name = title
        self.path = path
        self.fileName = title
        self.fileTree = fileTree
        self.modules = {} # key = module name, value = data of the module
        self.setText(0,  title)
        self.parseData = "" # version to parse through - shorter/simpler than actual file data
        self.generateConditions = {} # conditions for module instantiation in a generate block
        self.defineVars = {} # all defined variables in define files
        self.stack = [] # helper to parse parentheses
        self.parens = [] # helper to parse parentheses
        self.parameters = {} # key = parameter name, value = parameter's current value
        self.dirChildren = [] # if this node represents a directory - keeps track of children directories
        self.elseCondition = ""
    
    """"
    Parses through file, deletes comments, and finds all module declarations. Also
    searches for generate statements and any module instantiations made in 
    generate blocks.
    """
    def getModuleNames(self):
        # retrieve data of the original file
        f = open(self.path, 'r')
        data = f.read()
        
        # remove comments for easier parsing
        data = re.sub(r'//.*',  "",  data)
        self.parseData = re.sub(r'/\*\w*\*/',  "",  data)
        
        # look at generate blocks
        if ("generate" in self.parseData):
            beg = self.parseData.find("generate") + 8
            end = self.parseData.find("endgenerate")
            generateBlock = self.parseData[beg:end]
            # module instantiaion in generate block, parse it more thoroughly
            if ("." in generateBlock):
                self.searchGenerateBlock(generateBlock)
        
        # find all module declarations in the file
        modules = re.findall(r'^\s*module\s*(\w+)\s*\(', self.parseData, re.M)
        for mod in modules: # finds the data associated with each module
            beg = self.parseData.find(mod)
            end = self.parseData.find("endmodule",  beg,  len(self.parseData))
            self.modules[mod] = self.parseData[beg:end]
        if (len(self.modules) > 0):
            return self.modules
        else:
            return []
    
    # searches for define variables and saves their values
    def getDefines(self):
        defines = re.findall(r'^\s*`define\s*(\w+)\s*(.*)',  self.parseData,  re.M)
        for var in defines:
            self.fileTree.defineVars[var[0]] = var[1]
    
    # searches for parameter declarations and stores their values in self.parameters
    def getParameters(self):
        # search for regular parameter declarations
        parameters = re.findall('parameter\s*(\[\d+:\d+\])?\s*(\w+)\s*=\s*(.*);',  self.parseData,  re.M)
        for param in parameters:
            self.parameters[param[1]] = param[2]
        # search for multi-line parameter declarations
        parameters = re.findall('(parameter\s*(\[\d+:\d+\])?\s*(.*,\n)+\s*(.*);)',  self.parseData,  re.M)
        for param in parameters:
            str = param[0]
            temp = re.findall('\s*([\w\d_]*)\s*=\s*(.*),\s*',  str,  re.M)
            for param in temp:
                self.parameters[param[0]] = param[1]
        
        # if needed, evaluate the parameter's values
        for param in self.parameters:
            value = self.parameters[param]
            if (value.isdigit() or "'" in value): # extract binary value from the number
                self.parameters[param] = self.extractNumber(value)
            elif (value[0] == "`"): # set equal to corresponding defines variable
                self.parameters[param] = self.fileTree.defineVars[value[1:]]
            elif ("\"" in value): # parameter's value is a string
                self.parameters[param] = value
            else: # evaluate the expressiong of the parameter's value
                self.parameters[param] = self.evaluate(value)
    
    # searches a generate block for any if statements or for loops with module instantiations in them
    # block = the data block to be searched
    def searchGenerateBlock(self,  block):
        # find the index of any if or for statements
        ifIndex = block.find("if")
        forIndex = block.find("for")
        ifCondition = ""
        # find the statements and add them to self.generateConditions
        if (ifIndex > -1 and (ifIndex < forIndex or forIndex == -1)):
            repl = block[ifIndex:block.find("end\n")+3]
            ifBlock = block[ifIndex + 2:block.find("end\n")]
            ifCondition = ifBlock[:ifBlock.find("begin")].lstrip().rstrip()
            ifBlock = ifBlock[ifBlock.find("begin")+5:]
            ifIndex = ifBlock.find("if")
            elseIndex = ifBlock.find("else")
            if ((elseIndex < ifIndex or ifIndex == -1) and elseIndex > -1):
                repl = repl[repl[2:].find("else"):]
                ifBlock = ifBlock[ifBlock.find("else")+4:]
                if ("." in ifBlock):
                    self.generateConditions[self.elseCondition] = ifBlock
            else:
                while ("if" in ifBlock):
                    if (ifIndex > -1):
                        cond = ifBlock[ifIndex + 2:ifBlock.find("begin")].lstrip().rstrip()
                        if (cond[0] == "(" and cond[len(cond) - 1] == ")"):
                            self.elseCondition = ifCondition + " && !" + cond
                            ifCondition = ifCondition + " && " + cond
                        else:
                            self.elseCondition = ifCondition + " && !(" + cond + ")"
                            ifCondition = ifCondition + " && (" + cond + ")"
                        repl = repl[repl[2:].find("if"):]
                        ifBlock = ifBlock[ifBlock.find("if")+2:]
                if ("." in ifBlock): # only add if there's a module instantiation
                    self.generateConditions[ifCondition] = ifBlock
            # continue searching the file
            self.searchGenerateBlock(block.replace(repl,  ""))
        elif (forIndex > -1 and (ifIndex > forIndex or ifIndex == -1)):
            forBlock = block[forIndex+3:block.find("end")+3]
            repl = block[forIndex:block.find("end")+3]
            if ("." in forBlock): # only add if there's a module instantiation
                forLoop = forBlock[:forBlock.find("begin")].lstrip().rstrip()
                self.generateConditions[forLoop] = forBlock[forBlock.find("begin")+5:]
            # continue searching the file
            self.searchGenerateBlock(block.replace(repl,  ""))
    
    # returns true if value still has to be evaluated further, false otherwise
    def hasEval(self,  value):
        return ("(" in value or "<" in value or ">" in value or "|" in value
                    or "&" in value or "~" in value or "^" in value or "+" in value
                    or "-" in value or "*" in value or "/" in value or "%" in value
                    or "'" in value or "[" in value or "`" in value)
    
    # evaluates value to be a binary value by performing various operations
    def evaluate(self,  value):
        reductions = ["|",  "&",  "~|",  "~&",  "^",  "~^",  "^~"]
        if ("(" in value): # parse parentheses
            return self.parseParens(value,  False)
        elif ("<<" in value): # left shift
            return self.shift(value,  "<<")
        elif (">>" in value): # right shift
            return self.shift(value,  ">>")
        elif (self.hasCondition(value)): # evaluate a boolean condition
            return self.parseIf(value)
        elif (value[0] in reductions): # evaluate a reduction
            return self.reduce(value)
        elif ("|" in value): # evaluate bitwise or
            return self.evalBitwise("|",  value)
        elif ("&" in value): # evaluate bitwise and
            return self.evalBitwise("&",  value)
        elif ("^" in value): # evaluate bitwise xor
            return self.evalBitwise("^",  value)
        elif ("~" in value): # evaluate bitwise not
            return self.evalBitwise("~",  value)
        # evaluate an arithmatic expression
        elif ("+" in value or "-" in value or "*" in value or "/" in value or "%" in value):
            return self.evalMath(value)
        elif ("[" in value): # evaluate brackets
            valIndex = self.extractBracket(value)
            valStart = 0
            valEnd = len(value) - 1
            if (len(valIndex) > 1):
                valStart = valIndex[0]
                valEnd = valIndex[1]
            value = value.split("[")[0]
            if (value in self.parameters):
                return self.parameters[value][valStart:valEnd]
        elif value in self.parameters: # value already found
            return self.parameters[value]
        elif (value.isdigit() or "'" in value): # value is a number
            return self.extractNumber(value)
        elif (value[0] == "`"): # set equal to corresponding defines variable
            return self.fileTree.defineVars[value[1:]]
    
    # returns true if there's still a condtion to be evaluated
    def hasCondition(self,  str):
        return ("||" in str or "&&" in str or "==" in str or "!" in str or "<" in str or ">" in str)
    
    # splits a statement with parentheses into parts
    def parseParens(self,  condition,  isBool):
        negate = False
        if (condition[0] == "!"):
            negate = True
        # keep track of parentheses locations
        self.stack.clear()
        self.parens.clear()
        for i in range(len(condition)):
            if (condition[i] == "("):
                self.stack.append(i)
            elif(condition[i] == ")"):
                self.parens.append([self.stack.pop(),  i])
        # parse through parentheses
        for ind in range(len(self.parens)):
            # find the expression inside the parentheses and evaluate it
            substr = condition[self.parens[ind][0]:self.parens[ind][1]+1]
            parse = self.evaluate(substr[1:len(substr) - 1])
            if (not parse is None):
                if (isBool): # if a condition, replace with 1/0 to represent True/False
                    if (parse):
                        if (negate and ind == len(self.parens) - 1):
                            condition = condition.replace(substr,  "0")
                        else:
                            condition = condition.replace(substr,  "1")
                    else:
                        if (negate and ind == len(self.parens) - 1):
                            condition = condition.replace(substr,  "1")
                        else:
                            condition = condition.replace(substr,  "0")
                    length = 1
                else: # else, replace the parentheses expression with the result of evaluation
                    condition = condition.replace(substr,  parse)
                    length = len(parse)
                # update the locations of the parentheses because condition was modified
                for i in range(ind, len(self.parens)):
                    if (self.parens[i][0] > self.parens[ind][1] + length):
                        self.parens[i][0] = self.parens[i][0] - (len(substr) - length)
                    if (self.parens[i][1] > self.parens[ind][1] + length):
                        self.parens[i][1] = self.parens[i][1] - (len(substr) - length)
        return condition

    # parse an if condition and returns the boolean it evaluates to using recursion
    def parseIf(self,  condition):
        # evalute parentheses if they're in the condition
        if ("(" in condition or ")" in condition):
            return self.parseParens(condition,  True)
        if ("&&" in condition): # evaluate and
            # split into right/left side, evaluate further if necessary
            rightSide = condition.split("&&",  1)[0].lstrip().rstrip()
            leftSide = condition.split("&&",  1)[1].lstrip().rstrip()
            if (self.hasCondition(rightSide)):
                right = self.parseIf(rightSide)
            else:
                right = self.getBool(rightSide)
            if (self.hasCondition(leftSide)):
                left = self.parseIf(leftSide)
            else:
                left = self.getBool(leftSide)
            return left and right
        elif ("||" in condition): # evaluate or
            # split into right/left side, evaluate further if necessary
            rightSide = condition.split("||",  1)[0].lstrip().rstrip()
            leftSide = condition.split("||",  1)[1].lstrip().rstrip()
            if (self.hasCondition(rightSide)):
                right = self.parseIf(rightSide)
            else:
                right = self.getBool(rightSide)
            if (self.hasCondition(leftSide)):
                left = self.parseIf(leftSide)
            else:
                left = self.getBool(leftSide)
            return left or right
        elif ("==" in condition): # evaluate equals
            rightSide = condition.split("==",  1)[0].lstrip().rstrip()
            leftSide = condition.split("==",  1)[1].lstrip().rstrip()
            return self.parseIfHelper(condition,  rightSide,  leftSide)
        elif ("<=" in condition): # evaluate less than or equal to
            rightSide = condition.split("<=",  1)[0].lstrip().rstrip()
            leftSide = condition.split("<=",  1)[1].lstrip().rstrip()
            return self.parseIfHelper(condition,  rightSide,  leftSide)
        elif (">=" in condition): # evaluate greater than or equal to
            rightSide = condition.split(">=",  1)[0].lstrip().rstrip()
            leftSide = condition.split(">=",  1)[1].lstrip().rstrip()
            return self.parseIfHelper(condition,  rightSide,  leftSide)
        elif ("<" in condition): # evaluate less than
            rightSide = condition.split("<",  1)[0].lstrip().rstrip()
            leftSide = condition.split("<",  1)[1].lstrip().rstrip()
            return self.parseIfHelper(condition,  rightSide,  leftSide)
        elif (">" in condition): # evaluate greater than
            rightSide = condition.split(">",  1)[0].lstrip().rstrip()
            leftSide = condition.split(">",  1)[1].lstrip().rstrip()
            return self.parseIfHelper(condition,  rightSide,  leftSide)
        elif ("!=" in condition): # evaluate not equals
            rightSide = condition.split("!=",  1)[0].lstrip().rstrip()
            leftSide = condition.split("!=",  1)[1].lstrip().rstrip()
            return self.parseIfHelper(condition,  rightSide,  leftSide)
        elif ("!" in condition): # evaluate not
            var = condition.split("!",  1)[1].lstrip().rstrip()
            if (self.hasCondition(var)):
                bool = self.parseIf(var)
            else:
                bool = self.getBool(var)
            if (bool is None):
                return None
            return not bool
        else:
            return self.getBool(condition)
    
    # helper method for parseIf that extracts value for rightSide and leftSide and evaluates
    # for ==, <=, >=, <, >, and !=
    def parseIfHelper(self, condition,  rightSide,  leftSide):
        # evaluate the right side for its value
        if (self.hasCondition(rightSide)):
            right = self.parseIf(rightSide)
        else:
            if (rightSide in self.parameters):
                right = int(self.parameters[rightSide],  2)
            elif ("'" in rightSide or rightSide.isdigit()):
                right = int(self.extractNumber(rightSide),  2)
            elif (rightSide[0] == "`"):
                right = int(self.extractNumber(self.fileTree.defineVars[rightSide[1:]]),  2)
            else:
                return None
        # evaluate the left side for its value
        if (self.hasCondition(leftSide)):
            left = self.parseIf(leftSide)
        else:
            if (leftSide in self.parameters):
                left = int(self.parameters[leftSide],  2)
            elif("'" in leftSide or leftSide.isdigit()):
                left = int(self.extractNumber(leftSide),  2)
            elif (leftSide[0] == "`"):
                left = int(self.extractNumber(self.fileTree.defineVars[leftSide[1:]]),  2)
            else:
                return None
        # return the result of the comparision between left and right
        if (not left is None and not right is None):
            if ("==" in condition):
                return left == right
            elif ("<=" in condition):
                return left <= right
            elif (">=" in condition):
                return left >= right
            elif ("<" in condition):
                return left < right
            elif (">" in condition):
                return left > right
            elif ("!=" in condition):
                return left != right
    
    # returns what var would be as a boolean (if var = 1, return True, else return False)
    def getBool(self,  var):
        if(var in self.parameters):
            num = self.extractNumber(self.parameters[var])
            return int(num,  2) == 1
        elif ("'" in var or var.isdigit()):
            return int(self.extractNumber(var),  2) == 1
        elif (self.hasEval(var)):
            return int(self.evaluate(var),  2) == 1
    
    # evaluates statement, which is a shift statement, op determines which shift it is
    def shift(self,  statement,  op):
        # split the value to the variable and the shift amount
        var = statement.split(op)[0].lstrip().rstrip()
        shift = statement.split(op)[1].lstrip().rstrip()
        # find the value of the variable in the statement
        if (var.isdigit() or "'" in var):
            var = self.extractNumber(var)
        elif var in self.parameters:
            var = self.parameters[var]
        elif self.hasEval(var):
            var = self.evaluate(var)
        else:
            return ""
        # find the shift amount
        if (shift.isdigit() or "'" in shift):
            shift = self.extractNumber(shift)
        elif shift in self.parameters:
            shift = self.parameters[shift]
        elif self.hasEval(shift):
            shift = self.evaluate(var)
        else:
            return ""
        # shift the value by shift amount of places
        num = int(shift,  2)
        if (op == "<<"):
            return var[num:] + "0"*num
        if (op == ">>"):
            return "0"*num + var[:len(var) - num]
    
    # evalutes value, an arithmatic expression to its value
    def evalMath(self,  value):
        # find all variables in the expression
        vars = re.findall('[a-zA-Z_`\'\[\]]+',  value,  re.M)
        # replace those variables with their numerical value
        for var in vars:
            if (var in self.parameters):
                value = value.replace(var,  str(int(self.parameters[var],  2)))
            elif (self.hasEval(var)):
                value = value.replace(var,  str(int(self.evaluate(var),  2)))
            else:
                return ""
        return self.extractNumber(str(eval(parser.expr(value).compile())))
    
    # given a string value, returns the binary form of value
    def extractNumber(self,  value):
        size = 0 # number of bits
        radix = 0
        signed = False
        # value is in the form _'_ _
        if ("'" in value and value.split("'")[0].isdigit() and value.split("'")[1] != ""):
            size = int(value.split("'")[0])
        elif ("'" in value): # use default size
            size = 32
        elif (value.isdigit()): # convert directly to binary
            size = 32
            value = bin(int(value))[2:]
            if (len(value) <= size):
                return value.zfill(size)
            else:
                index = len(value) - size
                return value[index:]
        else:
            return
        # find out what radix the value is using
        value = value.split("'")[1]
        if (value[0] == "s" or value[0] == "S"):
            radix = 10
            signed = True
            value = value[1:]
        if (value[0] == "b" or value[0] == "B"):
            radix = 2
            value = value[1:]
        elif (value[0] == "o" or value[0] == "O"):
            radix = 8
            value = value[1:]
        elif (value[0] == "h" or value[0] == "H"):
            radix = 16
            value = value[1:]
        elif (value[0] == "d" or value[0] == "D"):
            radix = 10
            value = value[1:]
        else:
            radix = 10
        # get rid of extra formatting
        value = value.replace("_",  "")
        # convert to binary and fill in any necessary 0's
        if (radix != 2):
            value = bin(int(value,  radix))[2:]
        if (len(value) <= size):
            if (signed):
                index = size - len(value)
                return value[0]*index + value
            else:
                return value.zfill(size)
        else:
            index = len(value) - size
            return value[index:]
    
    # perform the bitwise operation op on value
    def evalBitwise(self,  op,  value):
        if (op == "~"):
            value = value[1:]
            if (self.hasEval(value)):
                value = self.evaluate(value)
            return str(bin(~int(value,  2)))[2:]
        var1 = value.split(op)[0]
        if (self.hasEval(var1)):
            var1 = self.evaluate(var1)
        var2 = value.split(op)[1]
        if (self.hasEval(var2)):
            var2 = self.evaluate(var2)
        if (var1 in self.parameters and var2 in self.parameters):
            val1 = self.parameters[var1]
            val2 = self.parameters[var2]
            if (val1.isdigit() and val2.isdigit()):
                if (op == "|"):
                    return str(bin(int(val1,  2) | int(val2,  2)))[2:]
                elif (op == "&"):
                    return str(bin(int(val1,  2) & int(val2,  2)))[2:]
                elif (op == "^"):
                    return str(bin(int(val1,  2) | int(val2,  2)))[2:]
        return ""
    
    # perform reduction operation on value
    def reduce(self,  value):
        op = value[0]
        neg = False
        if (op == "~"): # takes care of any negation
            neg = True
            op = value[1]
            value = value[1:]
        # extract whatever value is in binary form
        if (op == "|" or op == "&" or op == "^"):
            value = value[1:] 
            if ("'" in value or value.isdigit()):
                value = self.extractNumber(value)
            else:
                if ("[" in value):
                    valIndex = self.extractBracket(value)
                    if (len(valIndex) > 0):
                        valStart = valIndex[0]
                        valEnd = valIndex[1]
                        value = value.split("[")[0]
                        value = self.parameters[value][valStart:valEnd]
                elif (value in self.parameters):
                    value = self.parameters[value]
                else:
                    return
            result = bool(value[0])
            value = value[1:]
            if (op == "|"):
                for v in value:
                    if (neg):
                        result = not result or bool(v)
                    else:
                        result = result or bool(v)
            elif (op == "&"):
                for v in value:
                    if (neg):
                        result = not result and bool(v)
                    else:
                        result = result and bool(v)
            elif (op == "^"):
                for v in value:
                    if (neg):
                        result = not xor(result,  bool(v))
                    else:
                        result = xor(result,  bool(v))
        return result

    # extracts the values contained in the bracket and returns an array of size 2 containing those values
    def extractBracket(self,  var):
        result = []
        if (":" in var):
            varIndex = var.split("[")[1].split(":")[0].lstrip().rstrip()
            if ("[" in varIndex):
                return result
            if (varIndex.isdigit()):
                result.append(int(varIndex))
            varIndex = var.split("]")[0].split(":")[1].lstrip().rstrip()
            if (varIndex.isdigit()):
                result.append(int(varIndex))
            if (len(result) > 1):
                if (result[0] > result[1]):
                    temp = result[0]
                    result[0] = result[1]
                    result[1] = temp
        else:
            varIndex = var.split("[")[1].split("]")[0]
            if (varIndex.isdigit()):
                result.append(int(varIndex))
                result.append(int(varIndex))
        return result
