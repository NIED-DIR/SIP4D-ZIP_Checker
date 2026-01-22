import os
from Sip4dzipChecker import Sip4dzipChecker
_ROOT = os.path.dirname(os.path.abspath(__file__))

def test_1():
    ck = Sip4dzipChecker()
    assert ck.check(os.path.abspath(_ROOT + "/Sip4dzipChecker/testdata/052_20250801_0000000.zip")) == True
    assert ck.version == "1.1"
    assert ck.author == "陸上自衛隊東北方面隊"    
    assert ck.title == "道路被害"
    assert ck.operation == "訓練"
    assert ck.geoarea.min_lat == 35.691532826901806
    assert ck.geoarea.min_lng == 139.79476379308534
    assert ck.geoarea.max_lat == 38.265337718859854
    assert ck.geoarea.max_lng == 140.9245411015138


def test_2():
    ck = Sip4dzipChecker()
    # BOM付UTF-8のJSONファイルを読み込んでエラーになればOK
    assert ck.loadJson(os.path.abspath(_ROOT+"/Sip4dzipChecker/testdata/utf8bom.json")) == None

def test_3():
    ck = Sip4dzipChecker()
    # BOM付UTF-8のJSONファイルを含むZIPファイルを読み込んでエラーになればOK
    assert ck.check(os.path.abspath(_ROOT+"/Sip4dzipChecker/testdata/bomtest.zip")) == False

def test_4():
    ck = Sip4dzipChecker()
    # ポリゴンが閉じていない
    assert ck.check(os.path.abspath(_ROOT + "/Sip4dzipChecker/testdata/0304-02.zip")) == False

def test_5():
    ck = Sip4dzipChecker()
    # スタイルファイルにエラー（必須項目がない）がある
    assert ck.check(os.path.abspath(_ROOT+"/Sip4dzipChecker/testdata/polygon_style_err_sample.zip")) == False

def test_6():
    ck = Sip4dzipChecker()
    # 複数のgeometryが混在している
    assert ck.check(os.path.abspath(_ROOT+"/Sip4dzipChecker/testdata/multi_geometry_type_err.zip")) == False