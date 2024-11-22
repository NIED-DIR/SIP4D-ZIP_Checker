import sys
import os
import json
import re
import datetime
import zipfile
import tempfile

# SIP4D-ZIPをチェックするクラス
class Sip4dZipChecker:
    report_dir = ""                 # レポート出力先ディレクトリ　空文字の場合は標準出力
    multi_geometry = False          # 複数のgeometry混在を許可するか
    template_root = "./template"    # テンプレートのルートディレクトリ
    # 以下リセット対象
    report = ""                     # レポート
    tmp_dir = ""                    # 一時ディレクトリ ここにSIP4D-ZIPを展開する
    filename = ""                   # チェック対象のファイル名
    result = True                   # チェック結果
    geotype = 0                     # geometryタイプ 0x01:Point 0x02:LineString 0x04:Polygon 0x08:MultiPoint 0x10:MultiLineString 0x20:MultiPolygon
                                    # 複数のgeometryが混在している場合、複数のビットが立つ
    version = ""                    # sip4d_zip_meta.json に記載されているバージョン
    code = ""                       # sip4d_zip_meta.json に記載されているコード
    payload_type = "VECTOR"         # sip4d_zip_meta.json に記載されているペイロードタイプ　デフォルトはVECTOR
    title = ""                      # sip4d_zip_meta.json に記載されているタイトル
    author = ""                     # sip4d_zip_meta.json に記載されている著作者
    information_date = ""           # sip4d_zip_meta.json に記載されている情報日時
    disaster_name = ""              # sip4d_zip_meta.json に記載されている災害名
    geofiles = []                   # 地理空間情報ファイルのリスト
    min_lng = 0.0                   # 経度の最小値
    max_lng = 0.0                   # 経度の最大値
    min_lat = 0.0                   # 緯度の最小値
    max_lat = 0.0                   # 緯度の最大値
    _datetime_formats = ["^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\\.[0-9]+){0,1}[zZ]{0,1}$"]

    def __init__(self, report_dir: str = ""):
        self.report_dir = report_dir
        self.reset()

    def reset(self):
        self.report = ""
        self.tmp_dir = ""
        self.filename = ""
        self.result = True
        self.geotype = 0
        self.version = ""
        self.code = ""
        self.payload_type = "VECTOR"
        self.title = ""
        self.author = ""
        self.information_date = ""
        self.disaster_name = ""
        self.geofiles = []
        self.min_lng = 0.0
        self.max_lng = 0.0
        self.min_lat = 0.0
        self.max_lat = 0.0

    # メッセージを追加する
    def addMessage(self, message: str):
        if self.report_dir != "" :
            with open(self.report_dir + "/" + self.filename + ".txt", "a") as f:
                f.write(message + "\n")
        else:
            print(message)
            self.report += message + "\n"
    
    # ワークディレクトリのパスを返す
    def wrkPath(self):
        return self.tmp_dir + "/"
    
    # データディレクトリのパスを返す
    def templatePath(self):
        return str(self.template_root) + "/" + self.version + "/" + self.payload_type + "/"
    
    # 空間情報の初期化
    def initSpatial(self):
        self.geotype = 0
        self.min_lng = 0.0
        self.max_lng = 0.0
        self.min_lat = 0.0
        self.max_lat = 0.0

    #jsonファイルの読み込み
    def LoadJson(self, filename: str, encoding='utf-8'):
        with open(filename, 'r', encoding=encoding) as file:
            try:
                return json.load(file)
            except UnicodeDecodeError as e:
                self.result = False
                self.addMessage("[ERROR]ファイルの文字コードが不正です " + filename)
                return None
            except json.JSONDecodeError as e:
                self.result = False
                self.addMessage("[ERROR]JSONデコードに失敗しました " + filename)
                return None


    #GeoJSONの形式チェック
    def CheckGeojson(self, data: dict, temp: dict = None):
        ret = True
        if data['type'] != 'FeatureCollection':
            self.result = ret = False
            self.addMessage("[ERROR]FeatureCollectionがありません")
        #地物なし
        if len(data['features']) == 0:
            self.addMessage("[INFO]Featuresがありません")
            return ret
        cnt = 0
        for feature in data['features']:
            geotype = 0
            if feature['type'] != 'Feature':
                self.result = ret = False
                self.addMessage("[ERROR]features[" + str(cnt) + ".Featureではありません")
            if 'geometry' not in feature:
                self.result = ret = False
                self.addMessage("[ERROR]features[" + str(cnt) + "].geometryがありません")
            if 'properties' not in feature:
                self.result = ret = False
                self.addMessage("[ERROR]features[" + str(cnt) + "].propertiesがありません")
            if 'type' not in feature['geometry']:
                self.result = ret = False
                self.addMessage("[ERROR]features[" + str(cnt) + "].geometry.typeがありません")
            # ジオメトリタイプを記録する
            if feature['geometry']['type'] == 'Point':
                geotype = 0x01
            elif feature['geometry']['type'] == 'LineString':
                geotype = 0x02
            elif feature['geometry']['type'] == 'Polygon':
                geotype = 0x04
            elif feature['geometry']['type'] == 'MultiPoint':
                geotype = 0x08
            elif feature['geometry']['type'] == 'MultiLineString':
                geotype = 0x10
            elif feature['geometry']['type'] == 'MultiPolygon':
                geotype = 0x20
            else:
                self.result = ret = False
                self.addMessage("[ERROR]不明なgeometry.typeです " + feature['geometry']['type'])
        
            self.geotype |= geotype
            if not self._CheckGeometry(feature['geometry']['coordinates'], geotype, cnt) :
                # エラーの場合、該当する地物のプロパティをメッセージに追加する
                self.addMessage(feature['properties'].__str__())

            #プロパティチェックをする
            if temp is not None:
                self._CheckProperties(feature['properties'], temp, cnt)
            cnt += 1

        #複数のgeometryが混在していないかチェック
        if not (self.geotype == 0x01 or self.geotype == 0x02 or self.geotype == 0x04 or \
            self.geotype == 0x08 or self.geotype == 0x10 or self.geotype == 0x20) :
            m = "複数のgeometry.typeが混在しています ("
            if self.geotype & 0x01:
                m += " Point"
            if self.geotype & 0x02:
                m += " LineString"
            if self.geotype & 0x04:
                m += " Polygon"
            if self.geotype & 0x08:
                m += " MultiPoint"
            if self.geotype & 0x10:
                m += " MultiLineString"
            if self.geotype & 0x20:
                m += " MultiPolygon"
            m += " )"
            if not self.multi_geometry:
                self.result = ret = False
                self.addMessage("[ERROR]" + m)
            else:
                self.addMessage("[INFO]" + m)    
        
        return ret


    #Geometryのデータをチェックする
    def _CheckGeometry(self, coordinates: dict, geotype: int, no: int):
        # Multiかどうかの判定
        if geotype & 0x38 == 0:
            # シングルの場合
            return self._CheckCoordinate(coordinates, geotype, no)
        else:
            # マルチの場合
            if len(coordinates) == 0:
                self.result = False
                self.addMessage("[ERROR]features[" + str(no) + "].geometry.coordinates 座標が不正です")
                return False
            else:
                ret = True
                for coordinate in coordinates:
                    if not self._CheckCoordinate(coordinate, geotype, no) :
                        ret = False
                return ret

    #座標のデータをチェックする
    def _CheckCoordinate(self, coordinate: dict, geotype: int, no: int):
        # ポイントの場合
        if geotype == 0x01 or geotype == 0x08:
            return self._CheckLatLng(coordinate, no)
        # ラインストリングの場合
        if geotype == 0x02 or geotype == 0x10:
            if len(coordinate) < 2 :
                self.result = False
                self.addMessage("[ERROR]features[" + str(no) + "].geometry.coordinates LineStringは2組以上の座標が必要です")
                return False
            else:
                for coord in coordinate:
                    return self._CheckLatLng(coord, no)
        # ポリゴンの場合
        if geotype == 0x04 or geotype == 0x20:
            if len(coordinate) == 0:
                self.result = False
                self.addMessage("[ERROR]features[" + str(no) + "].geometry.coordinates Polygonのジオメトリ座標が不正です")
                return False
            for polygon in coordinate:
                if len(polygon) < 4 :
                    self.result = False
                    self.addMessage("[ERROR]features[" + str(no) + "].geometry.coordinates Polygonは4組以上の座標が必要です")
                    return False
                else:
                    for coord in polygon:
                        return self._CheckLatLng(coord, no)
                # 最初の座標と最後の座標が同じかどうか
                if polygon[0] != polygon[-1]:
                    self.result = False
                    self.addMessage("[ERROR]features[" + str(no) + "].geometry.coordinates Polygonの最初の座標と最後の座標が異なります")
                    return False
        # 未定義
        self.result = False
        self.addMessage("[ERROR]features[" + str(no) + "].geometry.coordinates 不明なジオメトリタイプです")
        return False
        
    #緯度経度のチェック（配列が２つで、float型であること）
    def _CheckLatLng(self, dat: any, no: int):
        if len(dat) != 2:
            self.result = False
            self.addMessage("[ERROR]features[" + str(no) + "].geometry.coordinates 緯度経度が不正です " + dat.__str__())
            return False
        if type(dat[0]) is not float or type(dat[1]) is not float:
            self.result = False
            self.addMessage("[ERROR]features[" + str(no) + "].geometry.coordinates 緯度経度が不正です " + dat.__str__())
            return False
        if self.min_lat == 0.0 and self.max_lat == 0.0 and self.min_lng == 0.0 and self.max_lng == 0.0:
            self.min_lng = dat[0]
            self.max_lng = dat[0]
            self.min_lat = dat[1]
            self.max_lat = dat[1]
        else:
            if dat[0] < self.min_lng:
                self.min_lng = dat[0]
            if dat[0] > self.max_lng:
                self.max_lng = dat[0]
            if dat[1] < self.min_lat:
                self.min_lat = dat[1]
            if dat[1] > self.max_lat:
                self.max_lat = dat[1]
        return True


    #ＧｅｏＪＳＯＮのプロパティのチェック
    def _CheckProperties(self, properties: dict, temp: dict, no: int):
        if type(properties) is not dict:
            self.result = False
            self.addMessage("[ERROR]プロパティが不正です")
            return False
        r1 = self.CheckJsonFormat(properties, temp, "features["+ str(no) +"].properties")
        # 属性定義されていないプロパティがあるか
        for key in properties:
            if not self._FindKey(temp['members'], key):
                #エラーにしない
                self.addMessage("[WARN]属性定義ファイルで未定義のプロパティがあります features[" + str(no) + "].properties." + key)
        return r1
    
    def _CheckString(self, x: str, temp: dict):
        # 値のチェック valuesに一致するか
        if temp.get('values') is not None:
            for value in temp['values']:
                if x == value:
                    return True
        # 文字列のフォーマットチェック string_formatsに一致するか
        if temp.get('string_formats') is not None:
            for format in temp['string_formats']:
                if re.match(format, x):
                    return True
        # チェック文字列なしならOK
        if temp.get('values') is None and temp.get('string_formats') is None:
            return True
        if not temp['necessary'] and x == "":
            return True
        return False

    def _CheckInt(self, x: int, temp: dict):
        r1 = True
        # 最小値チェック
        if temp.get('min_value') is not None:
            if x < temp['min_value']:
                r1 = False
        # 最大値チェック
        if temp.get('max_value') is not None:
            if x > temp['max_value']:
                r1 = False
        # values チェック
        r2 = False
        if temp.get('values') is not None:
            for value in temp['values']:
                if x == value:
                    r2 = True
        return r1 or r2
    
    def _CheckFloat(self, x: float, temp: dict):
        r1 = True
        # 最小値チェック
        if temp.get('min_value') is not None:
            if x < temp['min_value']:
                r1 = False
        # 最大値チェック
        if temp.get('max_value') is not None:
            if x > temp['max_value']:
                r1 = False
        # values チェック
        r2 = False
        if temp.get('values') is not None:
            for value in temp['values']:
                if x == value:
                    r2 = True
        return r1 and r2
    
    def _CheckArray(self, x: list, temp: dict, parent: str = ""):
        ret = True
        # 配列の要素数チェック
        if temp.get('number') is not None:
            if len(x) != temp['number']:
                ret = False
        # 配列の要素をチェック
        for value in x:
            match value:
                case str(y) :
                    if temp['type'] != 'ArrayOfString':
                        ret = False
                    elif not self._CheckString(y, temp):
                        ret = False
                case int(y) :
                    if not(temp['type'] == 'ArrayOfInteger' or temp['type'] == 'ArrayOfNumber'):
                        ret = False
                    elif not self._CheckInt(y, temp):
                        ret = False
                case float(y) :
                    if not(temp['type'] != 'ArrayOfDouble' or temp['type'] == 'ArrayOfNumber'):
                        ret = False
                    elif not self._CheckFloat(y, temp):
                        ret = False
                case bool(y) :
                    if temp['type'] != 'ArrayOfBool':
                        ret = False
                case dict(y) :
                    if temp['type'] != 'ArrayOfObject':
                        ret = False
                    elif temp.get('members') is not None:
                        if not self.CheckJsonFormat(y, temp, parent + "." + temp['key']):
                            ret = False
        return ret

    # 属性定義ファイルからGeoJSONのプロパティ定義に変換する
    def _ConvertColumns(self, data: dict, temp: dict = None):
        if data.get('columns') is None:
            return None
        
        properties = {"members": []}
        for column in data['columns']:
            # connid を探す
            connid = column['name']
            if column.get('connid') is not None:
                connid = column['connid']
            #テンプレート検索
            t = self._FindConnid(temp, connid)
            # 汎用的なプロパティ定義
            d = {"key": column['name'], "type": "StrNum", "necessary": False }
            if column.get('necessary') is not None:
                d['necessary'] = column['necessary']
            # String, Integer, Doubleの場合はそのまま
            if column.get('type') is not None:
                d['type'] = column['type']
            
                # Listの場合は、valuesを追加
                if column['type'] == 'List' :
                    if column.get('key_list') is not None :
                        d['values'] = column['key_list']
                    d['type'] = 'String'
                # Datetimeの場合は、Stringに変換
                if column['type'] == 'Datetime' :
                    d['type'] = 'String'
                    # 日付フォーマットを追加
                    d['string_formats'] = self._datetime_formats
            if t is not None:
                # テンプレートのproperties_valueでGeoJSONのプロパティチェック設定を補強する
                if t.get('type') is not None and d.get('type') is None:
                    d['type'] = t['type']
                if t.get('values') is not None and d.get('values') is None:
                    d['values'] = t['values']
                if t.get('string_formats') is not None and d.get('string_formats') is None:
                    d['string_formats'] = t['string_formats']
                if t.get('necessary') is not None and d.get('necessary') is None:
                    d['necessary'] = t['necessary']
                if t.get('number') is not None and d.get('number') is None:
                    d['number'] = t['number']
                if t.get('min_value') is not None and d.get('min_value') is None:
                    d['min_value'] = t['min_value']
                if t.get('max_value') is not None and d.get('max_value') is None:
                    d['max_value'] = t['max_value']
                if t.get('file_exists') is not None and d.get('file_exists') is None:
                    d['file_exists'] = t['file_exists']
                if t.get('count_members') is not None and d.get('count_members') is None:
                    d['count_members'] = t['count_members']

            properties["members"].append(d)
        return properties

    # ArrayOfObjectから指定したキーと値を持つデータを検索する
    def _FindData(self, aoo: list, key: str, value: str = "" ):
        for data in aoo:
            if data.get(key) is not None:
                if value != "" :
                    if data[key] == value:
                        return data
                else:
                    return data
        return None        

    # ArrayOfObjectから指定した複数候補のキーと値を持つデータを検索する
    def _FindDataKeys(self, aoo: list, keys: list, value: str = "" ):
        for key in keys:
            d = self._FindData(aoo, key, value)
            if d is not None:
                return d
        return None
    
    # 型不明のデータ群が指定したvaluesであるかチェックする
    def _CheckValues(self, data: any, values: list):
        ret = True
        match data:
            case str(x) | int(x) | float(x) :
                ret = False
                for value in values:
                    if x == value:
                        ret = True
            case list(x) :
                for d in x:
                    if not self._CheckValues(d, values) :
                        ret = False
        return ret
    
    # ArrayOfObjectから指定したconnidを検索する
    def _FindConnid(sel, aoo: list, connid: str):
        for data in aoo:
            if data.get('connid') is not None:
                if data['connid'] == connid:
                    return data
        return None

    # ArrayOfObjectから指定したkeyを検索する
    def _FindKey(sel, aoo: list, key: str):
        for data in aoo:
            if data.get('key') is not None:
                if data['key'] == key:
                    return data
        return None

    # メンバーの存在チェック
    def _ExistMembers(self, data: dict, members: list, temp: dict, parent: str = ""):
        self.addMessage("[INFO]要素の存在チェック ")
        ret = True
        for m in temp['exist_members']:
            # valueの設定がある場合、key=valueのペアが存在すればOK
            if m.get('value') is not None:
                ret = False
                for key in m['keys']:
                    if self._FindData(members, key, m['value']) is not None:
                        ret = True
                if ret != True and m['necessary']:
                    # keys=valueのペアが全て存在しない
                    self.result = False
                    self.addMessage("[ERROR]必須要素がありません " + parent + "." + temp['key'] + "." + key + " = " + m['value'].__str__())
            if m.get('ifvalue') is not None:
                tg = None
                ifk = None
                # ifkey=ifvalueのペアが存在するか？
                if m.get('ifkey') is not None:
                    ifk = m['ifkey']
                    tg = self._FindData(members, m['ifkey'], m['ifvalue'])
                if m.get('ifkeys') is not None:
                    ifk = m['ifkeys']
                    tg = self._FindDataKeys(members, m['ifkeys'], m['ifvalue'])
                if tg is not None:
                    for key in m['keys']:
                        if tg.get(key) is None : # members配列にkeyが1つでも存在すればOK
                            if m['necessary']:
                                ret = False
                                self.result = False
                                self.addMessage("[ERROR]必須要素がありません " + parent + "." + temp['key'] + "." + key +" ("+ str(ifk) + "=" + m['ifvalue'] + ")")
                        else :
                            if m.get('values') is not None:
                                if not self._CheckValues(tg[key], m['values']) :
                                    ret = False
                                    self.result = False
                                    self.addMessage("[ERROR]値が不正です " + parent + "." + temp['key'] + "." + key + "=" + str(tg[key]) + " (" + str(ifk) + "=" + m['ifvalue'] + ")")

            if m.get('ifkey_p') is not None and m.get('ifvalue_p') is not None:
                # ifkey_p=ifvalue_pのペアが存在するか？
                if data.get(m['ifkey_p']) is not None and data[m['ifkey_p']] == m['ifvalue_p']:
                    for key in m['keys']:
                        cnt = 0
                        for member in members: # members配列にkeyが全て存在すればOK
                            if member.get(key) is None and m['necessary']:
                                ret = False
                                self.result = False
                                self.addMessage("[ERROR]必須要素がありません " + parent + "." + temp['key'] + "["+ str(cnt) +"]." + key +" (上位."+ m['ifkey_p'] + " = " + m['ifvalue_p'] + ")")
                            cnt += 1
            if m.get('ifkey_p') is not None and m.get('ifminvalue_p') is not None:
                # ifkey_p=ifvalue_pのペアが存在するか？
                if data.get(m['ifkey_p']) is not None and data[m['ifkey_p']] >= m['ifminvalue_p']:
                    for key in m['keys']:
                        cnt = 0
                        for member in members: # members配列にkeyが全て存在すればOK
                            if member.get(key) is None and m['necessary']:
                                ret = False
                                self.result = False
                                self.addMessage("[ERROR]必須要素がありません " + parent + "." + temp['key'] + "["+ str(cnt) +"]." + key +" (上位."+ m['ifkey_p'] + " = " + str(data[m['ifkey_p']]) + ")")
                            cnt += 1
        return ret

    # JSONファイルをチェックするための、データフォーマットを規定する
    # ルートのオブジェクト名はmembersで、array of objectである。 以下のメンバを持つ
    #   keyメンバを持ち、要素名を指定する
    #   ng_keysメンバを持ち、禁止されている要素名のリストを指定する
    #   typeメンバを持ち、Object, String, Bool, Integer, Double, Number, StrNum
    #       ArrayOfObject, ArrayOfString, ArrayOfBool, ArrayOfInt, ArrayOfDouble, ArrayOfNumberのいずれかを指定する
    #       NumberはInteger, Doubleのいずれかの型を許容する
    #       StrNumはInteger, Double, Stringのいずれかの型を許容する
    #   valuesメンバを持ち、値の配列を指定する（固定値の場合）　配列で定義した値と一致する場合のみ正常とする
    #   necessaryメンバを持ち、必須項目かどうかを指定する
    #   numberメンバを持ち、配列の要素数を指定する
    #   min_valueメンバを持ち、数値の最小値を指定する(int, flat, array_of_int, array_of_floatのみ)
    #   max_valueメンバを持ち、数値の最大値を指定する(int, flat, array_of_int, array_of_floatのみ)
    #   string_formatsメンバを持ち、文字列のフォーマットを正規表現で指定する(string, array_of_stringのみ)
    #   file_existsメンバを持ち、ファイルが存在するかどうかをチェックする（stringのみ）
    #   count_membersメンバを持ち、子となるmembers配列の要素数の要素名を指定する
    #   子となるmembersを持ち、メンバの要素を定義する　メンバオブジェクトは、親オブジェクトと同じ形式で定義する（ネストする）
    # ルートにexist_members(ArrayOfObject)メンバを持ち、指定したキー(key)と値(value)を持つデータが存在するかチェックする
    #    keyメンバを持ち、要素名を指定する
    #    valueメンバを持ち、値を指定する 
    #    ifkeyメンバを持ち、存在チェックの条件となるキーを指定する
    #    ifvaluesメンバを持ち、存在チェックの条件となる値を指定する
    def CheckJsonFormat(self, data: dict, temp: dict, parent: str = ""):
        ret = True
        for column in temp['members']:
            target = data.get(column['key'])
            if target is None :
                #必須項目チェック
                if column['necessary'] :
                    self.result = ret = False
                    self.addMessage("[ERROR]必須項目がありません " + parent + "." + column['key'])
                    continue 
            
            # メンバのチェック
            match target:
                case str(x) :
                    #typeチェック Stirng, StrNum
                    if not(column['type'] == 'String' or column['type'] == 'StrNum'):
                        self.result = ret = False
                        self.addMessage("[ERROR]" + parent + "." + column['key'] + " の型が不正です " + column['type'] + "である必要があります")
                        # エラーの場合、該当する地物のプロパティをメッセージに追加する
                        self.addMessage(data.__str__())
                        continue
                    if not self._CheckString(x, column):
                        self.result = ret = False
                        self.addMessage("[ERROR]" + parent + "." + column['key'] + " の値が不正です " + str(x))
                    if column.get('file_exists') is not None:
                        if not os.path.exists(self.wrkPath()+"/"+ x):
                            self.result = ret = False
                            self.addMessage("[ERROR]" + parent + "." + column['key'] + " のファイルがありません " + str(x))

                case int(x) :
                    #typeチェック Integer, Number, StrNum, Bool
                    if not (column['type'] == 'Integer' or column['type'] == 'Number' or column['type'] == 'StrNum' or column['type'] == 'Bool'): 
                        self.result = ret = False
                        self.addMessage("[ERROR]" + parent + "." + column['key'] + " の型が不正です " + column['type'] + "である必要があります")
                        # エラーの場合、該当する地物のプロパティをメッセージに追加する
                        self.addMessage(data.__str__())
                        continue
                    if not self._CheckInt(x, column):
                        self.result = ret = False
                        self.addMessage("[ERROR]" + parent + "." + column['key'] + " の値が不正です " + str(x))

                case float(x) :
                    #typeチェック Double, Number, StrNum
                    if not (column['type'] == 'Double' or column['type'] == 'Number' or column['type'] == 'StrNum'):
                        self.result = ret = False
                        self.addMessage("[ERROR]" + parent + "." + column['key'] + " の型が不正です " + column['type'] + "である必要があります")
                        # エラーの場合、該当する地物のプロパティをメッセージに追加する
                        self.addMessage(data.__str__())
                        continue
                    if self._CheckFloat(x, column):
                        self.result = ret = False
                        self.addMessage("[ERROR]" + parent + "." + column['key'] + " の値が不正です " + str(x))
 
                case dict(x) :
                    #typeチェック Object
                    if column['type'] != 'Object':
                        self.result = ret = False
                        self.addMessage("[ERROR]" + parent + "." + column['key'] + " の型が不正です " + str(x))
                        continue
                    if column.get('members') is not None:
                        # Objectなら再起呼び出し
                        if self.CheckJsonFormat(x, column, parent + "." + column['key']) == False:
                            ret = False

                case list(x) :
                    #typeチェック ArrayOfObject, ArrayOfString, ArrayOfBool, ArrayOfInt, ArrayOfDouble, ArrayOfNumber
                    if column['type'] != 'ArrayOfObject' and column['type'] != 'ArrayOfString' and column['type'] != 'ArrayOfBool' and \
                    column['type'] != 'ArrayOfInteger' and column['type'] != 'ArrayOfDouble' and column['type'] != 'ArrayOfNumber':
                        self.result = ret = False
                        self.addMessage("[ERROR]" + parent + "." + column['key'] + " の型が不正です " + column['type'])
                    #要素数チェック
                    if column.get('count_members') is not None:
                        num = column['count_members']
                        if data.get(num) is not None:
                            c = data[column['count_members']]
                            if c != len(x):
                                self.result = ret = False
                                self.addMessage("[ERROR]要素数が不正です " + parent + "." + column['key'] + " = " + str(len(x)) + " " + num + "=" + str(c))
                    # 配列の要素をチェック
                    if not self._CheckArray(x, column, parent):
                        self.result = ret = False
                    # 要素の存在チェック
                    if column.get('exist_members') is not None and column.get('type') == 'ArrayOfObject':
                        if self._ExistMembers(data, target, column, parent) == False:
                            ret = False


            # 禁止されている要素名がないかチェック
            if column.get('ng_keys') is not None:
                for ng_name in column['ng_keys']:
                    if data.get(ng_name) is not None:
                        self.result = ret = False
                        self.addMessage("[ERROR]禁止されている要素名があります " + parent + "." + ng_name)
        return ret
    
    # メタファイルのチェック
    def CheckMetaFile(self):
        # 初期チェックのテンプレートを読み込む
        columns = self.LoadJson( str(self.template_root) + "/temp_meta.json", 'utf-8')

        #　メタファイルが存在するか
        if not os.path.exists(self.wrkPath() + "sip4d_zip_meta.json"):
            self.result = False
            self.addMessage("[ERROR]メタファイル sip4d_zip_meta.json がありません")
            return False
        #　メタファイルのフォーマット概要をチェック（バージョン番号、コード、ペイロードタイプがあるか）
        data = self.LoadJson(self.wrkPath() + "sip4d_zip_meta.json", 'utf-8')
        self.CheckJsonFormat(data, columns)
     
        # 初期チェックでエラーがあった場合は、以降のチェックは行わない（テンプレートファイルを参照できなくなるので）
        if self.result == False:
            return False    
        
        #バージョン番号取得
        self.version = data['version']
        #コード取得
        self.code = data['code']
        #ペイロードタイプ取得
        if data.get('payload_type') is not None:
            self.payload_type = data['payload_type']
        else:
            self.payload_type = "VECTOR"
        
        #　バージョン別のテンプレートを読み込む
        self.addMessage("[INFO]メタデータファイルをチェックします sip4d_zip_meta.json")
        columns = self.LoadJson(self.templatePath() + "temp_meta.json", 'utf-8')
        # メタデータのフォーマットをチェック
        self.CheckJsonFormat(data, columns)
        self.title = data['title']
        self.author = data['author']['name']
        self.information_date = data['information_date']
        self.disaster_name = data['disaster']['name']
        # 基本情報を表示
        self.addMessage("[INFO]フォーマット: SIP4D-ZIP")
        self.addMessage("[INFO]バージョン: " + self.version)
        self.addMessage("[INFO]ペイロードタイプ: " + self.payload_type)
        self.addMessage("[INFO]コード: " + self.code)
        self.addMessage("[INFO]災害名: " + self.disaster_name)
        self.addMessage("[INFO]タイトル：" + self.title)
        self.addMessage("[INFO]著作者：" + self.author)
        self.addMessage("[INFO]情報日時：" + self.information_date)

        # 地理空間情報ファイルのリストを取得
        for entry in data['entry'] :
            self.geofiles.append(entry['file'])
        
        # entry数とファイル数が一致するか
        if len(data['entry']) != data['entry_num']:
            self.result = False
            self.addMessage("[ERROR]entry_numとファイル数が一致しません")
        
        return True
    

    # 属性定義ファイルと地理空間情報ファイルのチェック
    def CheckColumnsAndGeoDataFile_VECTOR(self, temp: dict):
        data: dict
        # 地理空間情報ファイルのリストを取得
        for geofile in self.geofiles:
            columns_file = os.path.splitext(geofile)[0] + "_columns.json"
            self.addMessage( "[INFO]属性定義ファイル: " + columns_file + " をチェックします")
            if not os.path.exists(self.wrkPath() + columns_file):
                self.result = False
                self.addMessage("[ERROR]属性定義ファイルがありません " + columns_file)
                continue
            else :
                # 属性定義ファイルをチェックする
                data = self.LoadJson(self.wrkPath() + columns_file, 'utf-8')
                if self.CheckJsonFormat(data, temp) == False:
                    # 属性定義がエラーの場合、GeoJSONのプロパティチェックができないので、次のファイルへ
                    self.addMessage("[INFO]属性定義ファイルにエラーがあるため、地理空間ファイル: " + geofile + " のチェックをスキップします")
                    continue 

            # columns.jsonからpropertiesを作成
            propertys = self._ConvertColumns(data, temp.get('properties_value'))
            # 地理空間情報ファイルをチェックする
            self.addMessage("[INFO]地理空間ファイル: " + geofile + " をチェックします")
            data = self.LoadJson(self.wrkPath() + geofile, 'utf-8')
            if data is None:
                return False
            if not self.CheckGeojson(data, propertys):
                return False
            self.addMessage("[INFO]座標範囲: ( " + str(self.min_lng) + " , " + str(self.min_lat) + " )-( " + str(self.max_lng) + " , " + str(self.max_lat) + " )" )
        return True
    
    # スタイルファイルのチェック
    def CheckStyleFile(self):
        # テンプレートを読み込む
        columns = self.LoadJson(self.templatePath() + "temp_style.json", 'utf-8')

        # 地理空間情報ファイルのリストを取得
        for geofile in self.geofiles:
            style_file = os.path.splitext(geofile)[0] + "_style.json"
            # スタイルファイルが存在するか
            if not os.path.exists(self.wrkPath() + style_file):
                self.addMessage("[WARN]凡例ファイルがありません " + style_file)
                continue

            self.addMessage("[INFO]凡例ファイル: " + style_file + " をチェックします")
            data = self.LoadJson(self.wrkPath() + "/" + style_file, 'utf-8')
            if data is not None:
                return self.CheckJsonFormat(data, columns)
        
        return True
    
    # unzipする
    def Unzip(self, zip_file: str):
        # ZIPファイルを展開
        try:
            with zipfile.ZipFile(zip_file) as existing_zip:
                existing_zip.extractall(self.wrkPath())
        except zipfile.BadZipFile:
            self.result = False
            self.addMessage("[ERROR]SIP4D-ZIPファイルの展開に失敗しました " + str(zip_file))
            return False

        self.addMessage("[INFO]SIP4D-ZIPを展開しました " + self.wrkPath())   
        return True

    # UNZIPしたSIP4D-ZIPをチェックする
    def CheckUnzipFiles(self):
        # メタファイルのチェック
        if self.CheckMetaFile() :
            if self.payload_type == "VECTOR":
                temp : dict
                if os.path.exists(self.templatePath() + self.code + ".json"):
                    # 情報種別コードに対応する属性定義ファイルがある場合
                    self.addMessage("[INFO]テンプレートファイル: " + self.code + ".json を読み込みます")
                    temp = self.LoadJson(self.templatePath() + self.code + ".json", 'utf-8')
                else:
                    # 汎用の属性定義ファイルを読み込む
                    self.addMessage("[INFO]テンプレートファイル: temp_column.json を読み込みます")
                    temp = self.LoadJson(self.templatePath() + "temp_column.json", 'utf-8')

                # テンプレートファイルにdo_not_check_payload_filesがある場合は、ペイロードファイルのチェックを行わない
                if temp.get('do_not_check_payload_files') is None:
                    # 属性定義ファイルのチェック
                    self.CheckColumnsAndGeoDataFile_VECTOR(temp) 
                    # スタイルファイルのチェック
                    self.CheckStyleFile()
                else:
                    self.addMessage("[WARN]***ペイロードファイルのチェックを行いません***")
            

    # チェック開始
    # zip_file: ZIPファイル名
    # return: チェック結果
    #  True: 正常
    #  False: エラーあり
    # メッセージはmessageに格納される
    def CheckZipFile(self, zip_file: str):
        self.filename = os.path.basename(zip_file)
        if os.path.splitext(zip_file)[1].lower() != ".zip":
            self.result = False
            self.addMessage("[ERROR]SIP4D-ZIPファイルではありません " + str(zip_file))
            return False
        self.addMessage("[INFO]SIP4D-ZIPをチェックします " + str(zip_file))
        self.addMessage("[INFO]開始時刻: " + datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"))

        with tempfile.TemporaryDirectory() as self.tmp_dir:        
            # ZIPファイルを展開
            if not self.Unzip(zip_file):
                return False
            # 展開したファイルをチェック
            self.CheckUnzipFiles()
            # 終了時刻を表示
            self.addMessage("[INFO]終了時刻: " + datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"))
            # チェック結果
            if self.result:
                self.addMessage("チェック結果: 正常です")
            else:
                self.addMessage("チェック結果: エラーがあります")
        self.addMessage("")
        return self.result
    
    # チェック開始
    def Check(self, path: str):
        ret = True
        # パスがファイルならファイルをチェック
        if os.path.isfile(path):
           ret = self.CheckZipFile(path)
        # パスがディレクトリならディレクトリ内のZIPファイルをチェック
        if os.path.isdir(path):
            files = os.listdir(path)
            for file in files:
                if os.path.isfile(path + "/" + file) and os.path.splitext(file)[1].lower() == ".zip":
                    self.reset()
                    self.CheckZipFile(path + "/" + file)
                #サブフォルダのZIPファイルを検索
                if os.path.isdir(path + "/" + file):
                    self.Check(path + "/" + file)
                if self.result == False:
                    ret = False
        return ret
