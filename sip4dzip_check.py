import sys
from sip4dzip import Sip4dZipChecker

#コマンドライン引数を取得
#引き数のチェック
if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("SIP4D-ZIPのフォーマットをチェックします。")
        print("使い方: python sip4dzip_check.py input_path output_path\n")
        print("input_path:")
        print("SIP4D-ZIPのパスもしくはディレクトリ。ディレクトリの場合、そのディレクトリ内の全てのZIPファイルをチェックします。また、サブディレクトリも再帰的にチェックします。\n")
        print("output_path:")
        print("チェック結果の出力先のパス。チェックを実行した時刻のサブフォルダを作成し、その中にSIP4D-ZIPを展開します。また、同ディレクトにチェック結果のレポートファイル（00_report.txt）を格納します。\n")
        sys.exit()

    input_path = sys.argv[1]
    output_path = sys.argv[2]

    #SIP4D-ZIPのチェック
    checker = Sip4dZipChecker()
    checker.reportfile = True       #レポートファイルを出力する
    #checker.removewrk = True        #正常だったチェック結果の出力先のフォルダを削除する
    checker.wrk_root = output_path  #チェック結果の出力先
    checker.Check(input_path)