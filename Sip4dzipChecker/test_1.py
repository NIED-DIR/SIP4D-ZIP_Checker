import os
import pytest
from Sip4dzipChecker import Sip4dzipChecker

_ROOT = os.path.dirname(os.path.abspath(__file__))

def test_check():
    ck = Sip4dzipChecker()
    assert ck.check(os.path.abspath(_ROOT+"/testdata/052_20250721_0000001.zip")) == True
    assert ck.check(os.path.abspath(_ROOT+"/testdata/052_20250721_0000006.zip")) == False

test_check()