Requirements:
- Implement basic functions (done)
- Display Modules (done)
- Traverse design hierarchies (done, but limited)
	- can currently read through files in a directory and deduce the module hierarchy from the files with 
	  limited support for instances generated through 'generate' blocks
		- 'generate' blocks can currently handle: multiple instances, simple nested if statements/for loops
		- can recognize native Verilog modules 
	- improvements that can be made to 'generate' blocks:
		- currently supports all Verilog operators? (supports <, <=, >, >=, ||, &&, ~, ^, +, -, *, /, %, <<, >>, [] and all reduction ops)
		- BUT not tested super thoroughly for more complicated expressions so may throw exceptions if the expression is too long
		- works with simple nested if/else statements and for loops
			- needs more testing, currently works for if..else, if...if...else..., for...for
		- parses with the assumption that the file's syntax is correct
		- add more cases to work with nested if statements/for loops
	- other improvements:
		- add way to deduce syntax errors
		- catching errors that could trigger while parsing (currently very limited)
		- speed + memory?
- Browse design files : source HDL, constraint files (done)
	- can currently display Verilog files with a separate tab for constraint (.tcl) files
- Edit design files (done)
- With syntax highlighting, code folding, auto-completion,�etc. (done)
