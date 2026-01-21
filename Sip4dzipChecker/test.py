import os
from Sip4dzipChecker import Sip4dzipChecker
_ROOT = os.path.dirname(os.path.abspath(__file__))

def test_1():
    ck = Sip4dzipChecker()
    assert ck.check(os.path.abspath(_ROOT + "/testdata/0304-02.zip")) == False

def test_2():
    ck = Sip4dzipChecker()
    assert ck.check(os.path.abspath(_ROOT + "/testdata/052_20250801_0000000.zip")) == True

def test_3():
    ck = Sip4dzipChecker()
    assert ck.check(os.path.abspath(_ROOT + "/testdata/polygon_style_err_sample.zip")) == False

test_3()