import os
from Sip4dzipChecker import Sip4dzipChecker

def test_1():
    _ROOT = os.path.dirname(os.path.abspath(__file__))
    checker = Sip4dzipChecker()
    assert checker.check(os.path.abspath(_ROOT + "/Sip4dzipChecker/testdata/052_20250801_0000000.zip")) == True