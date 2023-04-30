import psycopg2
import os
from main import get_picture_id
from dotenv import load_dotenv
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
db_host, db_user, db_password, db_name = os.environ.get('db_host'), os.environ.get('db_user'), os.environ.get('db_password'), os.environ.get('db_name')
import logging
import pandas as pd

default_stat_list = [0] * 100
logging.getLogger(__name__)
try:
    connection = psycopg2.connect(
        host=db_host,
        user=db_user,
        password=db_password,
        database=db_name
    )
    connection.autocommit = True

except Exception as _ex:
    logging.critical("Ошибка при работе с PostgreSQL")
    exit(1)


def write_user_to_db(effective_chat_id, name = 'default_name', amount_of_answers=0, last_stat=[0]*100, wrong_answers=[[]],
                     is_on_wrong_answers_sequence=False, if_hints_required=False,
                     periods='all_periods', themes='all_themes'):
    name = name.replace("'", "").replace('"', '').replace(";", "")  # экранирование sql инъекций через имя пользователя
    with connection.cursor() as cursor:
        cursor.execute(
            f'INSERT INTO users (tg_id, tg_name) VALUES ({effective_chat_id}, \'{name}\') '
            f'ON CONFLICT (tg_id) DO UPDATE SET '
            f'tg_name = \'{name}\', '
            f'amount_of_answers = {amount_of_answers}, '
            f'last_stat = ARRAY {last_stat}::integer[], '
            f'wrong_answers = ARRAY {wrong_answers}::integer[], '
            f'is_on_wrong_answers_sequence = {is_on_wrong_answers_sequence}, '
            f'if_hints_required = {if_hints_required}, '
            f'periods = \'{periods}\', themes = \'{themes}\';'
        )


def get_users_ids():
    with connection.cursor() as cursor:
        cursor.execute(
            'CREATE TABLE IF NOT EXISTS users('
            'tg_id integer PRIMARY KEY NOT NULL,'
            'tg_name text,'
            'amount_of_answers integer DEFAULT 0,'
            'wrong_answers integer [][] DEFAULT ARRAY []::integer[], '
            'is_on_wrong_answers_sequence boolean DEFAULT false,'
            'if_hints_required boolean DEFAULT false,'
            'periods text DEFAULT \'all_periods\','
            'themes text DEFAULT \'all_themes\','
            f'last_stat integer[] DEFAULT ARRAY {default_stat_list}); '
            'SELECT array_agg(tg_id) FROM users;'
        )
        return cursor.fetchone()[0]


def read_user_from_db(user_id):
    # получение пользователя из бд
    with connection.cursor() as cursor:
        cursor.execute(
            f'SELECT tg_name, amount_of_answers, last_stat, wrong_answers, is_on_wrong_answers_sequence, '
            f'if_hints_required, periods, themes FROM users WHERE tg_id = {user_id}; '
        )
        return cursor.fetchall()[0]


def get_amount_of_monuments() -> int:
    with connection.cursor() as cursor:
        cursor.execute(
            'SELECT max(id) from raw_questions'
        )
        return cursor.fetchone()[0]


def get_monuments():
    with connection.cursor() as cursor:
        cursor.execute(
            f'SELECT names, photos, dates, facts, authors, hints, periods, themes FROM raw_questions ORDER BY Id;'
        )
        return cursor.fetchall()


def update_questions_from_csv(csv_file, chat_id, context):
    df = pd.read_csv(csv_file)
    df.dropna(subset='names', inplace=True)
    df.fillna('', inplace=True)
    with connection.cursor() as cursor:
        cursor.execute(
            f'DROP TABLE raw_questions;'
            f'CREATE TABLE raw_questions (id serial, names text, photos text, dates text, facts text, authors text, '
            f'hints text, periods text, themes text);'
        )
    for i in range(len(df)):
        df.photos[i] = get_picture_id(df.photos[i], chat_id, context, df.names[i])
        with connection.cursor() as cursor:
            cursor.execute(
                f"INSERT INTO raw_questions(names, photos, dates, facts, authors, hints, periods, themes) VALUES {tuple(df.loc[i].values)};"
            )


def save_picture_id(picture_number, picture_id):
    with connection.cursor() as cursor:
        cursor.execute(
            f'UPDATE raw_questions SET photos_of_monuments = \'{picture_id}\' WHERE Id = {picture_number};'
        )


def close_connection():
    # закрытие соединения с бд
    if connection:
        connection.close()
        logging.info("Подключение к PostgreSQL закрыто")
