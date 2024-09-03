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

#シングルジオメトリをマルチに変換
def to_multi(data):
    if data['type'] != 'FeatureCollection':
        return None
    for feature in data['features']:
        if feature['geometry']['type'] == 'Point':
            feature['geometry']['type'] = 'MultiPoint'
            feature['geometry']['coordinates'] = [feature['geometry']['coordinates']]
        elif feature['geometry']['type'] == 'LineString':
            feature['geometry']['type'] = 'MultiLineString'
            feature['geometry']['coordinates'] = [feature['geometry']['coordinates']]
        elif feature['geometry']['type'] == 'Polygon':
            feature['geometry']['type'] = 'MultiPolygon'
            feature['geometry']['coordinates'] = [[feature['geometry']['coordinates']]]
    return data

#引き数のチェック
if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("geojsonファイルに含まれるシングルジオメトリをマルチジオメトリに変換します")
        print("Usage: python to_multi.py input.geojson output.geojson")
        sys.exit()

    data = load_json(sys.argv[1])
    if data is None:
        sys.exit()

    data = to_multi(data)
    if data is None:
        print("FeatureCollectionではありません")
        sys.exit()

    write_json(sys.argv[2], data)
    print("変換が完了しました")