import os
from Sip4dzipChecker import Sip4dzipChecker
_ROOT = os.path.dirname(os.path.abspath(__file__))

def test():
    ck = Sip4dzipChecker()
    assert ck.check(os.path.abspath(_ROOT + "/testdata/kunren_023_01-001-01_20260414140049_1.zip")) == False

test()