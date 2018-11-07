from pyparsing import (Word, Keyword, infixNotation, Forward, nestedExpr, 
srange, opAssoc, nums, Suppress, ZeroOrMore, Group, Optional)

TRUE = Keyword("True")
FALSE = Keyword("False")
boolOperand = TRUE | FALSE |  Word(srange("[a-zA-Z0-9_']"))

LPARR,RPARR= map(Suppress, '()')
LPARC,RPARC=map(Suppress,'{}')
LPAR=LPARC | LPARR
RPAR=RPARC | RPARR
expr = Forward()
factor = Group(Optional(LPAR) + expr + Optional(RPAR)) | boolOperand
multibit = Group(Word(nums) + LPARC + factor + RPARC) | factor # should recognize expressions like 2{A & B}
inverted = ZeroOrMore('~') + multibit # should recognize expressions like ~A
leftsideor = ZeroOrMore('|') + inverted # should recognize expressions like |A, but also ~{A & B}
andterm = leftsideor + ZeroOrMore('&' + leftsideor) # should recognize expressions like |A & B
orterm = andterm + ZeroOrMore('|' + andterm)  # should recognize expressions like A | B
expr <<= Group(Optional(LPAR) + orterm + ZeroOrMore(',' + orterm) + Optional(RPAR)) | orterm # {A,B,C&D}, (A,B,C&D)

if __name__ == "__main__":
    p = True
    q = False
    r = True
    tests = ["p",
             "q",
             "p & q",
             "p & ~q",
             "(p & ~q)",
             "{p & ~q}",
             "~~p",
             "q | ~p & r",
             "q | ~p | ~r",
             "q | ~(p & r)",
             "p | q | r",
             "p | q | r & False",
             "(p | q | r) & False",
             "|p",
             "{p,q,d&c,r}",
             "{2{p&q}}",
             "{p,q,d&c,3'd4}",
             "{2{p_1_&q}}",
             "{2{p23padsf_1_&q_2_3}}",
             "{~ITHERMSEL, ~IUNITSEL, ~IAVGSEL1} & {{2{EQEN}} , EQ3D }",
             "{{~ITHERMSEL, ~IUNITSEL, ~IAVGSEL1} & {{2{EQEN}} , EQ3D }}",
             "~(p & q)"
            ]


    print()
    for t in tests:
        print(t)
        res = expr.parseString(t)[0]
        print(res)

        print
