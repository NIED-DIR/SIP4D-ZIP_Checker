import os
from Sip4dzipChecker import Sip4dzipChecker

def test_1():
    _ROOT = os.path.dirname(os.path.abspath(__file__))
    checker = Sip4dzipChecker()
    assert checker.check(os.path.abspath(_ROOT + "/Sip4dzipChecker/testdata/052_20250801_0000000.zip")) == True
    assert checker.version == "1.1"
    assert checker.author == "陸上自衛隊東北方面隊"    
    assert checker.title == "道路被害"
    assert checker.min_lat == 35.691532826901806
    assert checker.min_lng == 139.79476379308534
    assert checker.max_lat == 38.26529275285557
    assert checker.max_lng == 140.9245214308029