import psycopg2
from psycopg2 import IntegrityError, errorcodes
from config import user, password, database

with psycopg2.connect(user=user, password=password, database=database) as conn:
    conn.autocommit = True

# создаем таблицу
def create_table_users():
    with conn.cursor() as cursor:
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS seen_users(
            id SERIAL,            vk_id INT PRIMARY KEY);
            """)

# добавляем id найденных пользователей
def insert_data_search(vk_ids):
    with conn.cursor() as cursor:
        # исключаем повторяющихся пользователей в списке найденных пользователей
        new_vk_ids = exclude_duplicates(vk_ids)
        print("new_vk_ids:", new_vk_ids)
        if not new_vk_ids:
            return
        try:
            # формируем SQL-запрос, чтобы получить список уже существующих пользователей
            select_query = "SELECT vk_id FROM seen_users WHERE vk_id IN %s"
            placeholders_list = ["%s" for _ in range(len(new_vk_ids))]
            placeholders = ", ".join(placeholders_list)
            select_query = select_query % "(" + placeholders + ")"
            # передаем список значений в метод execute()
            cursor.execute(select_query, tuple(new_vk_ids))
            existing_vk_ids = [result[0] for result in cursor.fetchall()]
            # создаем список новых пользователей, которых еще нет в базе данных
            new_vk_ids = list(set(new_vk_ids) - set(existing_vk_ids))
            print("new_vk_ids (after checking against the database):", new_vk_ids)
            # добавляем новых пользователей в базу данных
            if new_vk_ids:
                # формируем SQL-запрос с помощью строки форматирования
                insert_query = "INSERT INTO seen_users (vk_id) VALUES %s"
                placeholders_list = ["%s" for _ in range(len(new_vk_ids))]
                placeholders = ", ".join(placeholders_list)
                insert_query = insert_query % "(" + placeholders + ")"
                # передаем список значений в метод execute()
                values = [str(vk_id) for vk_id in new_vk_ids]
                cursor.execute(insert_query, tuple(values))
                conn.commit()
        except IntegrityError as e:
            if e.pgcode == errorcodes.UNIQUE_VIOLATION:
                # ignore the error, the user is already in the database
                pass
            else:
                raise e




# исключаем повторяющихся пользователей в списке найденных пользователей
def exclude_duplicates(vk_ids):
    if not vk_ids:
        return []
    with conn.cursor() as cursor:
        sql = "SELECT vk_id FROM seen_users WHERE vk_id IN (%s)"
        placeholders = ", ".join("%s" for _ in vk_ids)
        sql = sql % placeholders
        values = [(vk_id,) for vk_id in vk_ids]
        cursor.execute(sql, values)
        seen_users = cursor.fetchall()
        new_vk_ids = [vk_id for vk_id in vk_ids if str(vk_id) not in seen_users]
        return new_vk_ids

# запрашиваем список id найденных пользователей
def get_seen_users():
    with conn.cursor() as cursor:
        cursor.execute(
            """SELECT vk_id FROM seen_users;"""
        )
        seen_users = cursor.fetchall()
        return seen_users

# удаляем таблицу
def drop_users():
    with conn.cursor() as cursor:
        cursor.execute(
            """DROP TABLE IF EXISTS seen_users CASCADE;"""
        )

def create_database():
    with conn.cursor() as cursor:
        # проверяем, существует ли таблица seen_users в базе данных
        cursor.execute("SELECT EXISTS(SELECT * FROM information_schema.tables WHERE table_name='seen_users')")
        table_exists = cursor.fetchone()[0]
        if table_exists:
            print("Table seen_users already exists")
        else:
            # создаем таблицу seen_users, если она не существует
            cursor.execute("""
                CREATE TABLE seen_users (
                    id SERIAL PRIMARY KEY,
                    vk_id BIGINT UNIQUE NOT NULL
                )
            """)
            conn.commit()
            print("Table seen_users created")

if __name__ == '__main__':
    create_database()
