import os
from Sip4dzipChecker import Sip4dzipChecker

ck = Sip4dzipChecker()
ck.check(os.path.abspath("./tests/data/052_20250715_0000201.zip"))
    