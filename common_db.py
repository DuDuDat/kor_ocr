import json
import mysql.connector
import pandas as pd

with open('root_user.json') as f:
    config = json.load(f)


class DataSelector: # DB 질의문 사용
    def __init__(self, root_dir, data_count=300000, is_zip=False):
        """
        :param root_dir: Root Directory 예시: './', '../', './data/'
        :param is_zip: 경로가 압축폴더라면 True
        """
        self.root_dir = root_dir
        self.is_zip = is_zip
        self.data_count = data_count

    def to_check_zip_path(self):
        query = """
            SELECT ZIP_PATH, KIND FROM ROOT_ZIP
        """
        return self.__fetchall(query)

    def to_check_kind_unique(self, table):
        query = f"""
            SELECT DISTINCT R.KIND FROM {table} AS T
            INNER JOIN IMAGE_PATH AS I ON T.IMAGE_ID = I.ID
            INNER JOIN ROOT_ZIP AS R ON I.ZIP_PATH = R.ZIP_PATH
        """
        return self.__fetchunique(query)

    def to_check_unique(self, table='COORD_IMAGE_INFO', what='CLASS'):
        query = f"""
            SELECT DISTINCT {what} FROM {table}
        """
        return self.__fetchunique(query)

    """--------------------- 좌표 없는 데이터 --------------------- """
    def search_basic_by_kind(self, kind, _class=None): # 이미지 종류 고르기
        """
        :param kind: '필기체', '인쇄체', '인쇄체(증강)' '인쇄체(간판)' 중 하나 고르기
        :param _class: '문자', '문장', '단어' 중 하나 선택 선택 안하면 전체
        """
        placeholder, param = self.__search_class('B', kind, _class)
        query = f"""
            SELECT R.ZIP_PATH, I.IMAGE_PATH, B.* FROM BASIC_INFO AS B
            INNER JOIN IMAGE_PATH AS I ON B.IMAGE_ID = I.ID
            INNER JOIN ROOT_ZIP AS R ON I.ZIP_PATH = R.ZIP_PATH
            WHERE R.KIND = %s {placeholder} LIMIT %s
        """
        return self.__fetchall(query, param)

    def search_basic_by_path(self, path, _class=None): # 경로 검색
        """
        :param path: 경로에 포함되는 단어
        :param _class: '문자', '문장', '단어' 중 하나 선택 선택 안하면 전체
        """
        path = f'%{path}%'
        path = path.replace('\\', '/')

        if path.startswith(self.root_dir):
            path = path[len(self.root_dir):]

        placeholder, param = self.__search_class('B', path, _class)
        query = f"""
            SELECT R.ZIP_PATH, I.IMAGE_PATH, B.* FROM BASIC_INFO AS B
            INNER JOIN IMAGE_PATH AS I ON B.IMAGE_ID = I.ID
            INNER JOIN ROOT_ZIP AS R ON I.ZIP_PATH = R.ZIP_PATH
            WHERE R.ZIP_PATH LIKE %s {placeholder} LIMIT %s
        """
        return self.__fetchall(query, param)

    def search_basic_by_kind_and_path(self, kind, path, _class=None): # 종류, 경로 동시 검색
        """
        :param kind: '필기체', '인쇄체', '인쇄체(증강)' '인쇄체(간판)' 중 하나 고르기
        :param path: 경로에 포함되는 단어
        :param _class: '문자', '문장', '단어' 중 하나 선택 선택 안하면 전체
        """
        path = f'%{path}%'
        path = path.replace('\\', '/')

        if path.startswith(self.root_dir):
            path = path[len(self.root_dir):]

        param = (kind, path)
        placeholder, param = self.__search_class('B', param, _class)
        query = f"""
            SELECT R.ZIP_PATH, I.IMAGE_PATH, B.* FROM BASIC_INFO AS B
            INNER JOIN IMAGE_PATH AS I ON B.IMAGE_ID = I.ID
            INNER JOIN ROOT_ZIP AS R ON I.ZIP_PATH = R.ZIP_PATH
            WHERE R.KIND = %s AND R.ZIP_PATH LIKE %s {placeholder} LIMIT %s
        """
        return self.__fetchall(query, param)

    """--------------------- 좌표 있는 데이터 --------------------- """
    def search_coord_by_kind(self, kind, _class=None): # 이미지 종류 고르기
        """
        :param kind: '필기체', '인쇄체(다양한 형태)' 중 하나 고르기
        :param _class: '문자', '단어' 중 하나 선택 선택 안하면 전체
        """
        placeholder, param = self.__search_class('T', kind, _class)
        query = f"""
            SELECT R.ZIP_PATH, I.IMAGE_PATH, T.*, C.TYPE FROM COORD_IMAGE_INFO AS C
            INNER JOIN IMAGE_PATH AS I ON C.IMAGE_ID =I.ID
            INNER JOIN ROOT_ZIP AS R ON I.ZIP_PATH = R.ZIP_PATH
            INNER JOIN COORD_TEXT_INFO AS T ON C.IMAGE_ID = C.IMAGE_ID
            WHERE R.KIND = %s {placeholder} LIMIT %s
        """
        return self.__fetchall(query, param)

    def search_coord_by_path(self, path, _class=None): # 경로 검색
        """
        :param path: 경로에 포함되는 단어
        :param _class: '문자', '단어' 중 하나 선택 선택 안하면 전체
        """
        path = f'%{path}%'
        path = path.replace('\\', '/')

        if path.startswith(self.root_dir):
            path = path[len(self.root_dir):]

        path = f'%{path}%'
        placeholder, param = self.__search_class('T', path, _class)
        query = f"""
            SELECT R.ZIP_PATH, I.IMAGE_PATH, T.*, C.TYPE FROM COORD_IMAGE_INFO AS C
            INNER JOIN IMAGE_PATH AS I ON C.IMAGE_ID =I.ID
            INNER JOIN ROOT_ZIP AS R ON I.ZIP_PATH = R.ZIP_PATH
            INNER JOIN COORD_TEXT_INFO AS T ON T.IMAGE_ID = C.IMAGE_ID
            WHERE R.ZIP_PATH LIKE %s {placeholder} LIMIT %s
        """
        return self.__fetchall(query, param)

    def search_coord_by_kind_and_path(self, kind, path, _class=None): # 종류, 경로 검색
        """
        :param kind: '필기체', '인쇄체(다양한 형태)' 중 하나 고르기
        :param path: 경로에 포함되는 단어
        :param _class: '문자', '단어' 중 하나 선택 선택 안하면 전체
        """
        path = f'%{path}%'
        path = path.replace('\\', '/')
        if path.startswith(self.root_dir):
            path = path[len(self.root_dir):]
        param = (kind, path)

        placeholder, param = self.__search_class('T', param, _class)
        query = f"""
                SELECT R.ZIP_PATH, I.IMAGE_PATH, T.*, C.TYPE FROM COORD_IMAGE_INFO AS C
                INNER JOIN IMAGE_PATH AS I ON C.IMAGE_ID =I.ID
                INNER JOIN ROOT_ZIP AS R ON I.ZIP_PATH = R.ZIP_PATH
                INNER JOIN COORD_TEXT_INFO AS T ON T.IMAGE_ID = C.IMAGE_ID
                WHERE R.KIND = %s AND R.ZIP_PATH LIKE %s {placeholder} LIMIT %s
            """
        return self.__fetchall(query, param)

    def search_coord_by_type(self, type, _class=None):
        """
        :param type: 'book', 'Goods', 'Signboard', 'Traffic_Sign', 'form', 'cursive' 중 하나 고르기
        :param _class: '문자', '단어' 중 하나 선택 선택 안하면 전체
        """
        placeholder, param = self.__search_class('T', type, _class)
        query = f"""
            SELECT R.ZIP_PATH, I.IMAGE_PATH, T.*, C.TYPE FROM COORD_IMAGE_INFO AS C
            INNER JOIN IMAGE_PATH AS I ON C.IMAGE_ID =I.ID
            INNER JOIN ROOT_ZIP AS R ON I.ZIP_PATH = R.ZIP_PATH
            INNER JOIN COORD_TEXT_INFO AS T ON T.IMAGE_ID = C.IMAGE_ID
            WHERE C.TYPE = %s {placeholder} LIMIT %s
        """
        return self.__fetchall(query, param)

    def search_coord_by_path_and_type(self, path, type, _class=None):
        """
        :param path: 경로에 포함되는 단어
        :param type: 'book', 'Goods', 'Signboard', 'Traffic_Sign', 'form', 'cursive' 중 하나 고르기
        :param _class: '문자', '단어' 중 하나 선택 선택 안하면 전체
        """
        path = f'%{path}%'
        path = path.replace('\\', '/')
        if path.startswith(self.root_dir):
            path = path[len(self.root_dir):]
        param = (path, type)

        placeholder, param = self.__search_class('T', param, _class)
        print(placeholder, param)
        query = f"""
            SELECT R.ZIP_PATH, I.IMAGE_PATH, T.*, C.TYPE FROM COORD_IMAGE_INFO AS C
            INNER JOIN IMAGE_PATH AS I ON C.IMAGE_ID =I.ID
            INNER JOIN ROOT_ZIP AS R ON I.ZIP_PATH = R.ZIP_PATH
            INNER JOIN COORD_TEXT_INFO AS T ON T.IMAGE_ID = C.IMAGE_ID
            WHERE R.ZIP_PATH LIKE %s AND C.TYPE = %s {placeholder} LIMIT %s
        """
        return self.__fetchall(query, param)

    """-------------------------------------- 아래는 파일 내부에서만 사용하는 코드입니다. -------------------------------------- """
    def __search_class(self, table, param, _class):
        placeholder = ''
        if _class is not None:
            if isinstance(param, tuple):
                param = param + (_class,)
            else:
                param = (param, _class)
            placeholder = f'AND {table}.CLASS = %s'
        return placeholder, param

    def __path_in_default(self, dataframe): # 경로 수정
        dataframe['IMAGE_PATH'] = dataframe['IMAGE_PATH'].apply(lambda x: x.encode('cp437').decode('cp949'))
        dataframe['IMAGE_PATH'] = self.root_dir + dataframe['ZIP_PATH'] + '/' + dataframe['IMAGE_PATH']
        del dataframe['ZIP_PATH']

    def __zip_in_default(self, dataframe): # 경로 수정
        dataframe['ZIP_PATH'] = self.root_dir + dataframe['ZIP_PATH']

    def __fetchall(self, query, param=None):
        """
        :param query: 쿼리문 
        :param param: 쿼리문에 들어갈 매개변수
        :return: dataframe
        """
        if param is not None and not isinstance(param, tuple):
            param = [param, self.data_count]
            param = tuple(param)
        elif param is not None:
            param = param + (self.data_count, )

        with _DatabaseManager() as cursor:
            result = cursor.execute_fetchall(query, param)
            result = pd.DataFrame(result)

        if 'IMAGE_PATH' in result.columns:
            if self.is_zip:
                self.__zip_in_default(result)
            else:
                self.__path_in_default(result)
        if 'IMAGE_ID' in result.columns:
            del result['IMAGE_ID']
        if 'COORD_FIRST' in result.columns:
            result['COORD'] = list(zip(result['COORD_FIRST'], result['COORD_SECOND'], result['COORD_THIRD'], result['COORD_FOURTH']))
            result = result.drop(['COORD_FIRST', 'COORD_SECOND', 'COORD_THIRD', 'COORD_FOURTH'], axis=1)
        return result

    def __fetchunique(self, query):
        with _DatabaseManager() as cursor:
            result = cursor.execute_fetchall(query, None)
            return result

"""-------------------------------------- 데이터베이스 연결 관리 -------------------------------------- """
class _DatabaseManager:
    def __init__(self):
        self.config = config
        self.connection = None
        self.cursor = None

    def __enter__(self):
        self.connection = mysql.connector.connect(**self.config)
        self.cursor = self.connection.cursor(dictionary=True)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.cursor is not None:
            self.cursor.close()
        if self.connection is not None:
            self.connection.close()

    def execute_fetchall(self, query, param):
        if param is None:
            self.cursor.execute(query)
        else:
            self.cursor.execute(query, param)
        return self.cursor.fetchall()

    def execute_fetchone(self, query):
        self.cursor.execute(query)
        return self.cursor.fetchone()