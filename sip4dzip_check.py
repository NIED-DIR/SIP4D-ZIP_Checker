import sys
from sip4dzip import Sip4dZipChecker

#コマンドライン引数を取得
#引き数のチェック
if __name__ == '__main__':

    if len(sys.argv) != 2:
        print("SIP4D-ZIPのフォーマットをチェックします。")
        print("使い方: python sip4dzip_check.py [input_path]\n")
        print("input_path:")
        print("SIP4D-ZIPのパスもしくはディレクトリ。ディレクトリの場合、そのディレクトリ内の全てのZIPファイルをチェックします。また、サブディレクトリも再帰的にチェックします。\n")
        sys.exit()

    input_path = sys.argv[1]

    #SIP4D-ZIPのチェック
    checker = Sip4dZipChecker()
    checker.Check(input_path)

    if checker.result == True:
        sys.exit(0)
    else:
        sys.exit(1)



