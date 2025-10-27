import os
import pytest
from Sip4dzipChecker import Sip4dzipChecker

_ROOT = os.path.dirname(os.path.abspath(__file__))

def test_check():
    ck = Sip4dzipChecker()
    assert ck.check(os.path.abspath(_ROOT+"/testdata/052_20250801_0000000.zip")) == True

def test_utf8_bom():
    ck = Sip4dzipChecker()
    # BOM付UTF-8のJSONファイルを読み込んでエラーになればOK
    assert ck.loadJson(os.path.abspath(_ROOT+"/testdata/utf8bom.json")) == None

