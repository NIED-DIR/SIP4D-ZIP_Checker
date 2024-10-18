# 使い方
SIP4D-ZIPのフォーマットチェックを行うツールです。
```
$ python3 sip4dzip_check.py [入力パス] 
```
* 入力パス
    * チェック対象のZIPファイルまたはフォルダ
    * フォルダを指定した場合、フォルダ内の全てのZIPファイルをチェック対象とします。また、サブフォルダも再帰的にチェックします
* 出力
    * チェック結果を標準出力に表示します
    * チェック結果をステータスコードで返します（注意：フォルダを指定した場合、最後にチェックしたZIPファイルのステータスコードを返します）
        * 0: 正常終了
        * 1: エラー終了

:warning: SIP4D-ZIPの仕様については、[災害情報共有のための共通データフレームワーク－SIP4D-ZIP](https://webdesk.jsa.or.jp/books/W11M0090/index/?bunsyo_id=JSA-S1016%3A2023)を参照してください。

# 設定ファイル
templateフォルダにフォーマットチェックの設定ファイルを配置します。  
templateフォルダ直下にtemp_meta.jsonが配置してあり、このファイルを使用してメタデータファイルの初期チェックを行います。初期チェックによって、バージョン、ペイロードタイプ、情報種別コードを読み取り、サブフォルダに格納されているテンプレートファイルを使用し、改めて詳細なフォーマットチェックを行います。
```
template
├── temp_meta.json                      # 初期チェック用の設定ファイル
├── 1                                   # バージョン1の設定ファイル
│   └── VECTOR                          # VECTORの設定ファイル
│       ├── temp_meta.json              
│       ├── temp_column.json
│       ├── temp_style.json
│       └── [情報種別コード].json
└── 1.1                                 # バージョン1.1の設定ファイル
    └── VECTOR
```
各フォルダ内には、以下の設定ファイルを配置します。
* temp_meta.json
    * メタデータファイルをチェックするためのテンプレートファイル
* temp_column.json
    * 属性定義ファイルをチェックするためのテンプレートファイル
    * 情報種別コード個別のテンプレートファイルがない場合に使用
* temp_style.json
    * 凡例ファイルをチェックするためのテンプレートファイル
* [情報種別コード].json
    * 属性定義ファイルをチェックするためのテンプレートファイル
    * 情報種別コード個別に定義
    * ファイル名は情報種別コード

## テンプレートファイル
チェック対象となるJSONファイルの構造を定義します。

* オブジェクト配列の「members」を持つ
    * membersで、チェック対象となるJSONの要素を定義する
    * members はネストを許容する
* membersは、以下の構成要素を持つ
    * keyを持ち、要素名を指定する
    * ng_keysを持ち、禁止されている要素名のリストを指定する
    * typeを持ち、Object, String, Bool, Integer, Double, Number, StrNum, ArrayOfObject, ArrayOfString, ArrayOfBool, ArrayOfInteger, ArrayOfDouble, ArrayOfNumberのいずれかを指定する
        * NumberはInteger, Doubleのいずれかの型を許容する
        * StrNumはInteger, Double, Stringのいずれかの型を許容する
    * valuesを持ち、値の配列を指定する
        * 配列で定義した値と一致する場合は正常とする
    * necessaryを持ち、必須項目かどうかを指定する
    * numberを持ち、配列の要素数を指定する
        * typeがArrayOfObject, ArrayOfString, ArrayOfBool, ArrayOfInteger, ArrayOfDouble, ArrayOfNumberのみ
    * min_valueメンバを持ち、数値の最小値を指定する
        * typeがInteger, Double, ArrayOfInteger, ArrayOfDoubleのみ
    * max_valueメンバを持ち、数値の最大値を指定する
        * typeがInteger, Double, ArrayOfInteger, ArrayOfDoubleのみ
    * string_formatsメンバを持ち、文字列のフォーマットを正規表現で指定する
        * String, ArrayOfStringのみ
    * file_existsメンバを持ち、ファイルが存在するかどうかをチェックする
        * wrkPathのフォルダにvalueのファイルが存在する場合は正常とする
        * Stringのみ
* オブジェクト配列の「exist_members」を持つ
    * exist_membersは、下位のmembers(ArrayOfObject)に対するチェックを定義する
    * exist_membersは、4種類の項目チェックを定義することができる
        1. 項目名(keys)と値(value)の組み合わせが存在するかチェックする
            * exist_membersのデータがkeys, valueの場合、keysとvalueの組み合わせが存在するかチェックする
        2. 項目名(ifkey)(ifkeys)と値(ifvalue)の組み合わせが存在する場合に、項目名(keys)が存在するかチェックする 
            * exist_membersのデータがifkey, ifvalue, keysの場合、ifkeyとifvalueの組み合わせが存在するObjectにおいて、keysが存在するかチェックする
            * members配列にkeysの要素が1つでも存在する場合、正常とする
            * valuesが存在する場合、keysの要素の値がvaluesのいずれかと一致する場合、正常とする
        3. membersの上位階層に項目名(ifkey_p)と値(ifvalue_p)の組み合わせが存在する場合に、members内に項目名(keys)が存在するかチェックする
            * exist_membersのデータがifkey_p, ifvalue_p, keysの場合、上位階層にifkey_pとifvalue_pの組み合わせが存在する場合において、membersにkeysが存在するかチェックする
            * members配列にkeysの要素が全て存在する場合、正常とする
        4. membersの上位階層に項目名(ifkey_p)の値が(ifminvalue_p)で示す値以上の場合、members内に項目名(keys)が存在するかチェックする
            * exist_membersのデータがifkey_p, ifminvalue_p, keysの場合、上位階層にifkey_pの値がifminvalue_p以上の場合において、membersにkeysが存在するかチェックする
            * members配列にkeysの要素が全て存在する場合、正常とする
* オブジェクト配列の「properties_value」を持つ
    * properties_valueは、情報種別コード個別の属性定義ファイルのテンプレートにおいて使用する
    * SIP4D-ZIPチェッカーは、属性定義ファイルのフォーマットをチェックした後、同ファイルを使用してGeoJSONのpropertiesの値をチェックするためのテンプレートを生成する
    * 上記のテンプレートを生成する際に、properties_valueを参照する
    * properties_valueは、membersと同じ構成要素を使うことが出来るが、keyを使用せず代わりにconnidを使用する
    * connidで指定した値を持つ name要素を探す。見つかれば、その要素に対して properties_valueの内容を適用する
    * 上記処理で見つからない場合、connid要素を探し、その要素に対して properties_valueの内容を適用する
    * 属性定義ファイルのtypeと、properties_valueのtypeが競合する場合、属性定義のtypeを優先する
* ペイロードチェックのスキップ
    * do_not_check_payload_files メンバがある場合、ペイロードのチェックをスキップする

### テンプレートサンプル
```
{
    "members" : [
        {
            "key": "format",                            # formatという要素名（Key値）
            "type": "String",                           # valueの型は文字列  
            "necessary": true,                          # 必須項目
            "values": ["SIP4D-ZIP"]                     # 値は"SIP4D-ZIP"のみ
        },
        {
            "key": "version",                           # versionという要素名（Key値）
            "type": "String",                           # valueの型は文字列
            "necessary": true,                          # 必須項目
            "values": ["1","1.1","2.0"]                 # 値は"1","1.1","2.0"のいずれか
        },
        {
            "key": "author",                            # authorという要素名（Key値）
            "type": "Object",                           # valueの型はオブジェクト
            "necessary": true,                          # 必須項目
            "members": [                                # authorの要素を定義
                {
                    "key": "name",                      # nameという要素名（Key値）
                    "type": "String",                   # valueの型は文字列
                    "necessary": true                   # 必須項目
                },
                {
                    "key": "email",                     # emailという要素名（Key値）
                    "type": "String",                   # valueの型は文字列
                    "necessary": true                   # 必須項目
                    "string_formats": ["^.+@.+$"]       # emailのフォーマット
                }
            ]
        }
    ]
} EOF
```

## 新しい情報種別コードのテンプレートファイルの作り方
新しい情報種別コードのテンプレートファイルを作成する場合、以下の手順で作成してください。
1. temp_column.jsonをコピーし、ファイル名を変更する（情報種別コード）
2. 必須の要素を定義する（exist_members、properties_valueに追記する）

以下に「避難所」（01-001-01）をサンプルにして、新しい情報種別コードのテンプレートファイルを作成する手順を示します。
```
{
    "members": [

        ... 省略 ...
        {
            "key" : "columns",
            "type" : "ArrayOfObject",
            "necessary" : true,
            "count_members" : "num_column",
            "members" : [

                ... 省略 ...
                {
                    "key" : "conn_attr_list",
                    "type" : "ArrayOfString",
                    "necessary" : false,
                    "count_members" : "num_key"
                }
            ],
            "exist_members" : [
                {
                    "keys": ["num_key","key_list","value_list"],
                    "ifkey": "type",
                    "ifvalue" : "List",
                    "necessary": true
                }
            ]
        }
    ],
    "properties_value" : [
    ]
} EOF
```
上記は、temp_column.jsonをコピーした状態の内容です。exist_membersに１つオブジェクトが定義されています。  
このオブジェクト配列に、避難所データとして必須の項目を追加します。
```
{
    "members": [

        ... 省略 ...
        {
            "key" : "columns",
            "type" : "ArrayOfObject",
            "necessary" : true,
            "count_members" : "num_column",
            "members" : [

                ... 省略 ...
                {
                    "key" : "conn_attr_list",
                    "type" : "ArrayOfString",
                    "necessary" : false,
                    "count_members" : "num_key"
                }
            ],
            "exist_members" : [
                {
                    "keys": ["num_key","key_list","value_list"],
                    "ifkey": "type",
                    "ifvalue" : "List",
                    "necessary": true
                },                                                  # カンマを忘れずに追加
                {
                    "keys": ["connid","name"],                      # 追加１
                    "value": "eststts",
                    "necessary": true
                },
                {
                    "keys": ["connid","name"],                      # 追加２
                    "value": "name",
                    "necessary": true
                },
                {
                    "keys": ["connid","name"],                      # 追加３
                    "value": "cityname",
                    "necessary": true
                }
            ]
        }
    ],
    "properties_value" : [
    ]
} EOF
```
避難所の必須項目は、esttsts、name、citynameの３つです。  
項目名 connid もしくは name で、値が esttsts、name、cityname の存在をチェックするため、exist_membersに３つのオブジェクトを追加しました。
```
                {
                    "keys": ["conn_attr_list"],                      # 追加４
                    "ifkeys" : ["connid","name"],                    # conn_attr_listが必要になる条件
                    "ifvalue" : "eststts",                           # conn_attr_listが必要になる条件
                    "necessary": false,
                    "values" : ["notopen","open","close","permanent","unknown","other"]
                }

```
項目名の「eststts」は選択肢（List型）の必須項目です。そのため選択肢の内容によって「conn_attr_list」が必須になる場合があります。ifkeysとifvalueでconn_attr_listが必要になる条件を指定します。上記の場合、connidもしくはnameのいずれかの値がeststtsの場合に、conn_attr_listが必要になることを設定しています。SIP4D-ZIPの仕様では、value_listの値がモデル定義仕様どおりの値の場合、conn_attr_listは省略できます。そのため、necessaryはfalseに設定します。conn_attr_listが存在する場合、その値の取るべき値としてvaluesを指定します。


次に、GeoJSONのpropertiesの値をチェックするためのproperties_valueを作成します。  本チェックプログラムは、属性定義ファイルのフォーマットをチェックした後、そのファイルを使用してGeoJSONのpropertiesの値をチェックするためのテンプレートを生成します。ですが、属性定義ファイルのみでは、GeoJSONのpropertiesの値をチェックするための情報が不足しています。そのため、properties_valueを使用して、GeoJSONのpropertiesの値をチェックするためのテンプレートを補完します。
※初期状態では、properties_valueは空の配列です。
```
    ... 省略 ...
    "properties_value" : [
         {
            "connid" : "id",                                         # 推奨する属性名 id
            "type" : "String",                                       # 文字列
            "necessary" : false                                      # 必須項目でない
        },
        {
            "connid" : "citycode",                                   # 推奨する属性名 citycode
            "type" : "String",                                       # 文字列
            "necessary" : false,                                     # 必須項目でない
            "string_formats": ["^[0-9]{5}$"]                         # citycodeのフォーマットを正規表現で指定
        },
        {
            "connid" : "eststts",                                    # 推奨する属性名 eststts
            "type" : "String",                                       # 文字列
            "values" : ["未開設","開設","閉鎖","常設","不明","その他"],# "未開設","開設","閉鎖","常設","不明","その他"のいずれか
            "necessary" : true                                       # 必須項目
        }
   ]
} EOF
```
推奨する属性名として、key名をconnid として、id, citycode, eststts の３つを定義しました。  
eststtsの typeは Listではなく Stringです。JSONの型としての定義であることに注意してください。そして、取りうる値としてvaluesを定義しました。  
同じ要領で全ての属性を定義してください。membersと同じ構成要素を使うことができます。