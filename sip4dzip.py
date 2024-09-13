import sys
import os
import json
import re
import datetime
import zipfile
import tempfile

# SIP4D-ZIPをチェックするクラス
class Sip4dZipChecker:
    tmp_dir = ""                    # 一時ディレクトリ SIP4D-ZIPを展開する
    multi_geometry = False          # 複数のgeometry混在を許可するか
                                    #           以下リセット対象
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
    _datetime_formats = ["^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$", "^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+$","^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+[zZ]{1}$"]

    def __init__(self, wrk_dir: str = ""):
        self.wrk_dir = wrk_dir

    def reset(self):
        self.tmp_dir = ""
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
        print(message)
    
    # ワークディレクトリのパスを返す
    def wrkPath(self):
        return self.tmp_dir + "/"
    
    # データディレクトリのパスを返す
    def templatePath(self):
        return "./template/" + self.version + "/" + self.payload_type + "/"
    
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
            except json.JSONDecodeError as e:
                self.result = False
                self.addMessage("[ERROR]ファイルの読み込みに失敗しました " + filename)
                return None


    #GeoJSONの形式チェック
    def CheckGeojson(self, data: dict, temp: dict = None):
        ret = True
        if data['type'] != 'FeatureCollection':
            self.result = ret = False
            self.addMessage("[ERROR]FeatureCollectionがありません")
        #地物なし
        if len(data['features']) == 0:
            self.addMessage("[INFO]Featureがありません")
            return ret
        for feature in data['features']:
            geotype = 0
            if feature['type'] != 'Feature':
                self.result = ret = False
                self.addMessage("[ERROR]Featureではありません")
            if 'geometry' not in feature:
                self.result = ret = False
                self.addMessage("[ERROR]geometryがありません")
            if 'properties' not in feature:
                self.result = ret = False
                self.addMessage("[ERROR]propertiesがありません")
            if 'type' not in feature['geometry']:
                self.result = ret = False
                self.addMessage("[ERROR]geometryのtypeがありません")
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
            if not self._CheckGeometry(feature['geometry']['coordinates'], geotype) :
                # エラーの場合、該当する地物のプロパティをメッセージに追加する
                self.addMessage(feature['properties'].__str__())

            #プロパティチェックをする
            if temp is not None:
                self._CheckProperties(feature['properties'], temp)
                    
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
    def _CheckGeometry(self, coordinates: dict, geotype: int):
        # Multiかどうかの判定
        if geotype & 0x38 == 0:
            # シングルの場合
            return self._CheckCoordinate(coordinates, geotype)
        else:
            # マルチの場合
            if len(coordinates) == 0:
                self.result = False
                self.addMessage("[ERROR]座標が不正です")
                return False
            else:
                ret = True
                for coordinate in coordinates:
                    if not self._CheckCoordinate(coordinate, geotype) :
                        ret = False
                return ret

    #座標のデータをチェックする
    def _CheckCoordinate(self, coordinate: dict, geotype: int):
        # ポイントの場合
        if geotype == 0x01 or geotype == 0x08:
            return self._CheckLatLng(coordinate)
        # ラインストリングの場合
        if geotype == 0x02 or geotype == 0x10:
            if len(coordinate) < 2 :
                self.result = False
                self.addMessage("[ERROR]LineStringは2組以上の座標が必要です")
                return False
            else:
                for coord in coordinate:
                    return self._CheckLatLng(coord)
        # ポリゴンの場合
        if geotype == 0x04 or geotype == 0x20:
            if len(coordinate) == 0:
                self.result = False
                self.addMessage("[ERROR]Polygonのジオメトリ座標が不正です")
                return False
            for polygon in coordinate:
                if len(polygon) < 4 :
                    self.result = False
                    self.addMessage("[ERROR]Polygonは4組以上の座標が必要です")
                    return False
                else:
                    for coord in polygon:
                        return self._CheckLatLng(coord)
                # 最初の座標と最後の座標が同じかどうか
                if polygon[0] != polygon[-1]:
                    self.result = False
                    self.addMessage("[ERROR]Polygonの最初の座標と最後の座標が異なります")
                    return False
        # 未定義
        self.result = False
        self.addMessage("[ERROR]不明なジオメトリタイプです")
        return False
        
    #緯度経度のチェック（配列が２つで、float型であること）
    def _CheckLatLng(self, dat: any):
        if len(dat) != 2:
            self.result = False
            self.addMessage("[ERROR]緯度経度が不正です " + dat.__str__())
            return False
        if type(dat[0]) is not float or type(dat[1]) is not float:
            self.result = False
            self.addMessage("[ERROR]緯度経度が不正です " + dat.__str__())
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
    def _CheckProperties(self, properties: dict, temp: dict):
        if type(properties) is not dict:
            self.result = False
            self.addMessage("[ERROR]プロパティが不正です")
            return False
        return self.CheckJsonFormat(properties, temp, "properties")

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
            t = self._FindKey(temp, connid)
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

    
    # ArrayOfObjectから指定したconnid に紐づくkeyを検索する
    def _FindKey(sel, aoo: list, connid: str):
        for data in aoo:
            if data.get('connid') is not None:
                if data['connid'] == connid:
                    return data
        return None

    # メンバーの存在チェック
    def _ExistMembers(self, members: list, temp: dict, parent: str = ""):
        self.addMessage("[INFO]要素の存在チェック " + parent + "." + temp['key'])
        ret = True
        for m in temp['exist_members']:
            # valueの設定がある場合、key=valueのペアが存在すればOK
            if m.get('value') is not None:
                ret = False
                for key in m['keys']:
                    if self._FindData(members, key, m['value']) is not None:
                        ret = True
                if ret != True:
                    # keys=valueのペアが全て存在しない
                    self.result = False
                    self.addMessage("[ERROR]必須要素がありません " + parent + "." + temp['key'] + "." + key + " = " + m['value'].__str__())
            elif m.get('ifkey') is not None and m.get('ifvalue') is not None:
                # ifkey=ifvalueのペアが存在するか？
                if self._FindData(members, m['ifkey'], m['ifvalue']) is not None:
                    for key in m['keys']:
                        if self._FindData(members, key) is None :
                            ret = False
                            self.result = False
                            self.addMessage("[ERROR]必須要素がありません " + parent + "." + temp['key'] + "." + key +"("+ m['ifkey'] + " = " + m['ifvalue'] + ")")
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
                        continue
                    #要素数チェック
                    if column.get('count_members') is not None:
                        num = column['count_members']
                        if data.get(num) is not None:
                            c = data[column['count_members']]
                            if c != len(x):
                                self.result = ret = False
                                self.addMessage("[ERROR]要素数が不正です " + parent + "." + column['key'] + " = " + str(len(x)) + " " + num + "=" + str(c))
                                continue
                    # 配列の要素をチェック
                    if not self._CheckArray(x, column, parent):
                        self.result = ret = False
                    # 要素の存在チェック
                    if column.get('exist_members') is not None and column.get('type') == 'ArrayOfObject':
                        if self._ExistMembers(x, column, parent) == False:
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
        columns = self.LoadJson("./template/temp_meta.json", 'utf-8')

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
        
        # ファイルの存在チェック
        for geofile in self.geofiles:
            # Columns.jsonの存在チェック
            if not os.path.exists(self.wrkPath() + "/" + os.path.splitext(geofile)[0] + "_columns.json"):
                self.result = False
                self.addMessage("[ERROR]属性定義ファイルがありません " + os.path.splitext(geofile)[0] + "_columns.json")
            # Style.jsonの存在チェック
            if not os.path.exists(self.wrkPath() + "/" + os.path.splitext(geofile)[0] + "_style.json"):
                # スタイルが無くてもエラーではない
                self.addMessage("[INFO]凡例ファイルがありません " + os.path.splitext(geofile)[0] + "_style.json")

        # entry数とファイル数が一致するか
        if len(data['entry']) != data['entry_num']:
            self.result = False
            self.addMessage("[ERROR]entry_numとファイル数が一致しません")
        
        return True
    

    # 属性定義ファイルと地理空間情報ファイルのチェック
    def CheckColumnsAndGeoDataFile_VECTOR(self):
        # テンプレートを読み込む
        temp: dict
        data: dict
        temfilemessage = ""
        if os.path.exists(self.templatePath() + self.code + ".json"):
            # 情報種別コードに対応する属性定義ファイルがある場合
            tempfilemessage = "[INFO]テンプレートファイル: " + self.code + ".json を使用して、"
            temp = self.LoadJson(self.templatePath() + self.code + ".json", 'utf-8')
        else:
            # 汎用の属性定義ファイルを読み込む
            tempfilemessage = "[INFO]テンプレートファイル: temp_column.json を使用して、"
            temp = self.LoadJson(self.templatePath() + "temp_column.json", 'utf-8')

        # 地理空間情報ファイルのリストを取得
        for geofile in self.geofiles:
            columns_file = os.path.splitext(geofile)[0] + "_columns.json"
            
            self.addMessage( tempfilemessage + " 属性定義ファイル: " + columns_file + " をチェックします")

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
            self.addMessage("[ERROR]SIP4D-ZIPファイルの展開に失敗しました " + zip_file)
            return False

        self.addMessage("[INFO]SIP4D-ZIPを展開しました " + self.wrkPath())   
        return True

    # チェック開始
    # zip_file: ZIPファイル名
    # return: チェック結果
    #  True: 正常
    #  False: エラーあり
    # メッセージはmessageに格納される
    def CheckFile(self, zip_file: str):
        if os.path.splitext(zip_file)[1] != ".zip":
            self.result = False
            self.addMessage("[ERROR]SIP4D-ZIPファイルではありません " + zip_file)
            return False
        
        self.addMessage("[INFO]SIP4D-ZIPをチェックします " + zip_file )
        self.addMessage("[INFO]開始時刻: " + datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"))

        with tempfile.TemporaryDirectory() as self.tmp_dir:        
            # ZIPファイルを展開
            if not self.Unzip(zip_file):
                return False
        
            # メタファイルのチェック
            if self.CheckMetaFile() :
                # 属性定義ファイルのチェック
                self.CheckColumnsAndGeoDataFile_VECTOR() 
                # スタイルファイルのチェック
                self.CheckStyleFile()
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
           ret = self.CheckFile(path)
        # パスがディレクトリならディレクトリ内のZIPファイルをチェック
        if os.path.isdir(path):
            files = os.listdir(path)
            for file in files:
                if os.path.isfile(path + "/" + file) and os.path.splitext(file)[1] == ".zip":
                    self.reset()
                    self.CheckFile(path + "/" + file)
                #サブフォルダのZIPファイルを検索
                if os.path.isdir(path + "/" + file):
                    self.Check(path + "/" + file)
                if self.result == False:
                    ret = False
        return ret

