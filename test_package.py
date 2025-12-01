import os
from Sip4dzipChecker import Sip4dzipChecker
_ROOT = os.path.dirname(os.path.abspath(__file__))

def test_1():
    ck = Sip4dzipChecker()
    assert ck.check(os.path.abspath(_ROOT + "/Sip4dzipChecker/testdata/052_20250801_0000000.zip")) == True
    assert ck.version == "1.1"
    assert ck.author == "陸上自衛隊東北方面隊"    
    assert ck.title == "道路被害"
    assert ck.min_lat == 35.691532826901806
    assert ck.min_lng == 139.79476379308534
    assert ck.max_lat == 38.265337718859854
    assert ck.max_lng == 140.9245411015138


def test_2():
    ck = Sip4dzipChecker()
    # BOM付UTF-8のJSONファイルを読み込んでエラーになればOK
    assert ck.loadJson(os.path.abspath(_ROOT+"/Sip4dzipChecker/testdata/utf8bom.json")) == None

def test_3():
    ck = Sip4dzipChecker()
    # BOM付UTF-8のJSONファイルを含むZIPファイルを読み込んでエラーになればOK
    assert ck.check(os.path.abspath(_ROOT+"/Sip4dzipChecker/testdata/bomtest.zip")) == False