import json
import glob
import zipfile
import pandas as pd
from tqdm import tqdm
from functools import reduce


""" ---------------------------- 데이터 불러오기 ---------------------------- """
# 일반 폴더 안 JSON 데이터 가져오기
def get_default_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        result = json.load(file)
    return result

# zip 폴더 안 JSON 데이터 가져오기
def get_zip_json(zip_path, paths):
    result = []
    with zipfile.ZipFile(zip_path, 'r') as z:
        for path in tqdm(paths):
            with z.open(path) as f:
                json_file = json.load(f)
                result.append(json_file)
    return result

def get_zip_csv(zip_path, extension):
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_contents = zip_ref.namelist()
        file = [file for file in zip_contents if file.lower().endswith(extension)][0]
        with zip_ref.open(file) as f:
            return pd.read_csv(f)


# find_json_paths, list_zip_files_glob , 이름 변경 및 파라미터 추가임
""" ---------------------------- 파일 경로 가져오기 ---------------------------- """
# 일반 폴더 내 파일 경로 찾는 함수
def find_file_paths(directory, extension, replace=True):
    result = glob.glob(f"{directory}/**/*.{extension}", recursive=True)
    result = [file.replace('\\', '/') for file in result]
    if extension == 'zip' and replace:
        root_len = len(directory)+1
        result = [file[root_len:] if file.startswith(directory) else file for file in result]
    return  result

""" ---------------------------- 데이터 구조 확인하기 ---------------------------- """
# json 데이터 구조 확인
def get_json_structure(data, prefix=''):
    '''
    :param data: json 데이터
    :param prefix: 이전
    :return: json 구조를 나타내는 tuple
    '''
    result = []
    if isinstance(data, dict):
        for key, value in data.items():
            current_prefix = f"{prefix}.{key}" if prefix else key
            result.append(current_prefix)
            if isinstance(value, (dict, list)):
                result.extend(get_json_structure(data=value, prefix=current_prefix))
    elif isinstance(data, list) and data:
        result.append(f"{prefix}[list]")
        result.extend(get_json_structure(data=data[0], prefix=prefix))
    return tuple(result)


""" ---------------------------- json 필요한 데이터 추출 ---------------------------- """
# 13.한국어 글자체 json -> df 처리 함수
def kor_directory(json_data, select_cols):
    '''
    :param json_data: json 정보
    :param select_cols: 최종 선택 컬럼
    :return:
    '''
    cols = ['images', 'annotations']
    select_df = pd.json_normalize(json_data)

    dfs = []
    for col in cols:
        tmp = []
        for nested_json in select_df[col]:
            tmp.append(pd.json_normalize(nested_json))
        dfs.append(pd.concat(tmp))

    merge_function = \
        lambda left, right: pd.merge(left, right, left_on='id', right_on='image_id', how='inner', validate="1:m")

    result = reduce(merge_function, dfs)

    _class = 'attributes.type'

    if 'attributes.class' in result.columns:
        _class = 'attributes.class'

    result.rename(columns={'file_name':'FILE_NAME', 'text': 'TEXT', 'bbox': 'BOX', _class: 'CLASS'}, inplace=True)

    # '문장': '문장'
    change_name = {
        '글자(음절)': '문자', '단어(어절)': '단어', 'character': '문자', 'word': '단어'
    }

    result['CLASS'] = result['CLASS'].replace(change_name)

    return result[select_cols]

def variables_directory(jsons_list):
    infos = []
    image_infos = []
    for json_info in tqdm(jsons_list):
        image = json_info['image']
        filename = image.get('file_name', image.get('file_fame', None))

        text = json_info['text']
        if 'letter' in text.keys(): # 단일 값
            _class = '문자'
            value = text['letter']['value'] # 텍스트 값
            infos.append({
                'FILE_NAME': filename,
                'CLASS': _class,
                'TEXT': value
            })
            continue

        word = text['word']

        _type = 'form' # 인쇄체
        _class = '단어'
        if 'output' in text.keys(): # 필기체 좌표
            _type = 'cursive'
            _class = '문자'

        for item in word:
            item.update({'FILE_NAME': filename, 'CLASS': _class})

        image_infos.append({'FILE_NAME': filename, 'TYPE': _type})
        infos.extend(word)
    return image_infos, infos