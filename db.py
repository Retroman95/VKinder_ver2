import psycopg2
from psycopg2 import IntegrityError, errorcodes
from config import user, password, database

with psycopg2.connect(user=user, password=password, database=database) as conn:
    conn.autocommit = True

# создаем таблицу
# def create_table_users():
#     with conn.cursor() as cursor:
#         cursor.execute(
#             """CREATE TABLE IF NOT EXISTS seen_users(
#             id SERIAL,            vk_id INT PRIMARY KEY);
#             """)

# добавляем id найденных пользователей
def insert_data_search(new_vk_ids):
    with conn.cursor() as cursor:
        delete_query = "DELETE FROM temp_results"
        cursor.execute(delete_query)
        insert_query = "INSERT INTO temp_results(vk_id) VALUES (%s)"
        cursor.executemany(insert_query, [(vk_id,) for vk_id in new_vk_ids])
        insert_unviewed_profiles_to_seen_users_table()

def insert_unviewed_profiles_to_seen_users_table():
    with conn.cursor() as cursor:
        select_query = "SELECT DISTINCT vk_id FROM temp_results WHERE vk_id NOT IN (SELECT vk_id FROM seen_users) AND viewed = FALSE"
        cursor.execute(select_query)
        unique_vk_ids = [result[0] for result in cursor.fetchall()]
        insert_query = "INSERT INTO seen_users(vk_id) VALUES (%s)"
        cursor.executemany(insert_query, [(vk_id,) for vk_id in unique_vk_ids])

# запрашиваем список id найденных пользователей
def get_seen_users():
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT DISTINCT sr.vk_id
            FROM seen_users su
            JOIN temp_results sr ON su.vk_id = sr.vk_id
        """)
        seen_users = cursor.fetchall()
        return seen_users

# # удаляем таблицу
# def drop_users():
#     with conn.cursor() as cursor:
#         cursor.execute(
#             """DROP TABLE IF EXISTS seen_users CASCADE;"""
#         )

def create_database():
    with conn.cursor() as cursor:
        # проверяем, существует ли таблица seen_users в базе данных
        cursor.execute("SELECT EXISTS(SELECT * FROM information_schema.tables WHERE table_name='seen_users')")
        table_exists = cursor.fetchone()[0]
        if table_exists:
            print("Table search_results already exists")
        else:
            # создаем таблицу search_results, если она не существует
            cursor.execute("""
                CREATE TABLE seen_users (
                    vk_id BIGINT PRIMARY KEY
                )
            """)
            conn.commit()
            print("Table search_results created")

        # проверяем, существует ли таблица temp_results в базе данных
        cursor.execute("SELECT EXISTS(SELECT * FROM information_schema.tables WHERE table_name='temp_results')")
        table_exists = cursor.fetchone()[0]
        if table_exists:
            print("Table temp_results already exists")
        else:
            # создаем таблицу temp_results, если она не существует
            cursor.execute("""
                CREATE TABLE temp_results (
                    vk_id BIGINT PRIMARY KEY,
                    viewed BOOLEAN NOT NULL DEFAULT FALSE
                )
            """)
            conn.commit()
            print("Table temp_results created")

if __name__ == '__main__':
    create_database()
