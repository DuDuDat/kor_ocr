import json
import pandas as pd

from multiprocessing import Pool

from sqlalchemy import inspect
from sqlalchemy.sql import select, and_
from sqlalchemy import create_engine, MetaData, Table, Column, String, Integer, ForeignKey

with open('root_user.json') as f:
    mysql = json.load(f)

host_name = mysql['host']
user_name = mysql['user']
user_password = mysql['password']
db_name = mysql['database']
port = mysql['port']

engine = create_engine(f'mysql+pymysql://{user_name}:{user_password}@{host_name}:{port}/{db_name}')
metadata = MetaData()
inspector = inspect(engine)

root = 'ROOT_ZIP'
root_table = Table(
    root, metadata,
    Column('ZIP_PATH', String(300), primary_key=True, nullable=False),
    Column('KIND', String(50), nullable=False)
)

image_path = 'IMAGE_PATH'
image_path_table = Table(
    image_path, metadata,
    Column('ID', Integer, primary_key=True, nullable=False, autoincrement=True),
    Column('IMAGE_PATH', String(300), nullable=False),
    Column('ZIP_PATH', String(300), ForeignKey(f'{root}.ZIP_PATH', ondelete='CASCADE'), nullable=False),
)

image_info = 'COORD_IMAGE_INFO'
image_info_table = Table(
    image_info, metadata,
    Column('IMAGE_ID', Integer, ForeignKey(f'{image_path}.ID', ondelete='CASCADE'), primary_key=True, nullable=False),
    Column('TYPE', String(50), nullable=False), # 양식 종류
)

basic = 'BASIC_INFO'
basic_table = Table(
    basic, metadata,
    Column('TEXT', String(300), nullable=False),
    Column('CLASS', String(50), nullable=False), # 문자, 문장, 단어
    Column('IMAGE_ID', Integer, ForeignKey(f'{image_path}.ID', ondelete='CASCADE'), nullable=False),
)

coord_info = 'COORD_TEXT_INFO'
coord_info_table = Table(
    coord_info, metadata,
    Column('TEXT', String(300), nullable=False),
    Column('CLASS', String(50), nullable=False), # 문자, 문장, 단어
    Column('COORD_FIRST', Integer, nullable=False),
    Column('COORD_SECOND', Integer, nullable=False),
    Column('COORD_THIRD', Integer, nullable=False),
    Column('COORD_FOURTH', Integer, nullable=False),
    Column('IMAGE_ID', Integer, ForeignKey(f'{image_info}.IMAGE_ID', ondelete='CASCADE'), nullable=False),
)

# 전체 테이블 재생성
def create_tables():
    metadata.create_all(engine)

""" ---------------------------- INSERT ---------------------------- """
def insert_root(root_df):
    root_df.to_sql(name=root, con=engine, if_exists='append', index=False)

def insert_image_path(image_path_df):
    image_path_df.to_sql(name=image_path, con=engine, if_exists='append', index=False)

def insert_image_info(image_info_df):
    image_info_df.to_sql(name=image_info, con=engine, if_exists='append', index=False)

def chunk_insert_basic(df):
    df.to_sql(name=basic, con=engine, if_exists='append', index=False)

def chunk_insert_coord(df):
    df.to_sql(name=coord_info, con=engine, if_exists='append', index=False)

def insert_info(info_df, key=''):
    select_columns = ['IMAGE_ID', 'TEXT', 'CLASS']

    if 'BOX' in info_df.columns:
        coord_cols = ['COORD_FIRST', 'COORD_SECOND', 'COORD_THIRD', 'COORD_FOURTH']
        select_columns.extend(coord_cols)

        info_df[coord_cols] = pd.DataFrame(info_df['BOX'].tolist(), index=info_df.index)

        if key == 'sum':
            info_df['COORD_THIRD'] = info_df['COORD_FIRST'] + info_df['COORD_THIRD']
            info_df['COORD_FOURTH'] = info_df['COORD_FOURTH'] + info_df['COORD_SECOND']

    info_df = info_df.loc[:, select_columns]

    pool = Pool(processes=8)
    batch_size = 1000
    batches = [info_df.iloc[i:i + batch_size] for i in range(0, len(info_df), batch_size)]
    if 'COORD_FIRST' in info_df.columns:
        pool.map(chunk_insert_coord, batches)
    else:
        pool.map(chunk_insert_basic, batches)
    pool.close()


""" ---------------------------- SELECT ---------------------------- """
def select_zip_path_by_root(search):
    query = select(root_table).where(root_table.c.ZIP_PATH.like(f'%{search}%'))
    with engine.connect() as connection:
        results = connection.execute(query)
    return results.fetchall()

def select_image_by_zip_path(search):
    query = select(image_path_table).where(image_path_table.c.ZIP_PATH.like(f'%{search}%'))
    with engine.connect() as connection:
        results = connection.execute(query)
    return results.fetchall()

def select_coord_info_by_image_path(zip_path, image_path):
    query = select(coord_info_table). \
        select_from(image_path_table.join(coord_info_table, image_path_table.c.ID == coord_info_table.c.IMAGE_ID)). \
        where(
        and_(
            image_path_table.c.ZIP_PATH == zip_path,
            image_path_table.c.IMAGE_PATH == image_path
        )
    )

    # 데이터베이스 연결 및 쿼리 실행
    with engine.connect() as connection:
        results = connection.execute(query)
    return results.fetchall()