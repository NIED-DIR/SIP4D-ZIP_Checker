import sys
import json

#jsonファイルの読み込み
def load_json(filename, encoding='utf-8'):
    with open(filename, 'r', encoding=encoding) as file:
        try:
            return json.load(file)
        except json.JSONDecodeError as e:
            print("JSONファイルの読み込みに失敗しました " + filename)
            return None

#jsonファイルの書き込み
def write_json(filename, data, encoding='utf-8'):
    with open(filename, 'w', encoding=encoding) as file:
        json.dump(data, file, ensure_ascii=False, indent=2, sort_keys=True)

def to_simple(data, geometory_type: str):
    if data['type'] != 'FeatureCollection':
        return None
    pdata = data.copy()    
    selected_features = []
    for feature in pdata['features']:
        if feature['geometry']['type'] == geometory_type:
            # プロパティのうちdict, listは削除
            feature['properties'] = {k: v for k, v in feature['properties'].items() if not isinstance(v, (dict, list))}
            selected_features.append(feature)
    if selected_features == []:
        return None
    else:
        pdata['features'] = selected_features
    return pdata

#引き数のチェック
if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("地理院地図のGeoJSONファイルを、シンプルなGeoJSONファイルに変換します")
        print("Usage: python gsi2simple.py input.geojson")
        print("Output: input.point.geojson")
        print("Output: input.line.geojson")
        print("Output: input.polygon.geojson")
        print("Output: input.multi-point.geojson")
        print("Output: input.multi-line.geojson")
        print("Output: input.multi-polygon.geojson")
        sys.exit()

    data = load_json(sys.argv[1])
    if data is None:
        sys.exit()

    pdata = to_simple(data, 'Point')
    if pdata is not None:
        write_json(sys.argv[1].replace('.geojson', '.point.geojson'), pdata)
    pdata = to_simple(data, 'LineString')
    if pdata is not None:
        write_json(sys.argv[1].replace('.geojson', '.line.geojson'), pdata)
    pdata = to_simple(data, 'Polygon')
    if pdata is not None:
        write_json(sys.argv[1].replace('.geojson', '.polygon.geojson'), pdata)
    pdata = to_simple(data, 'MultiPoint')
    if pdata is not None:
        write_json(sys.argv[1].replace('.geojson', '.multi-point.geojson'), pdata)
    pdata = to_simple(data, 'MultiLineString')
    if pdata is not None:
        write_json(sys.argv[1].replace('.geojson', '.multi-line.geojson'), pdata)
    pdata = to_simple(data, 'MultiPolygon')
    if pdata is not None:
        write_json(sys.argv[1].replace('.geojson', '.multi-polygon.geojson'), pdata)

    print("変換が完了しました")