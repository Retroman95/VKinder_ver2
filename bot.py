from vk_api.longpoll import VkLongPoll, VkEventType
import datetime
import vk_api
from vk_api.utils import get_random_id
from config import user_token, group_token
from db import *
import threading


class VKBot:
    def __init__(self):
        self.vk_user = vk_api.VkApi(token=user_token)
        self.vk_user_got_api = self.vk_user.get_api()
        self.vk_group = vk_api.VkApi(token=group_token)
        self.vk_group_got_api = self.vk_group.get_api()
        self.longpoll = VkLongPoll(self.vk_group)

    # функция отправки сообщений
    def send_msg(self, user_id, message, attachment=None):
        self.vk_group_got_api.messages.send(
            user_id=user_id,
            message=message,
            random_id=get_random_id(),
            attachment=attachment
        )


    # запрашиваем возрастной диапазон для поиска
    def input_age(self, user_id, age):
        global age_from, age_to

        # Проверяем, что введенный возраст является числом
        if not age.replace('-', '').isdigit():
            return 'Неправильный формат ввода возраста'

        age_from, age_to = map(int, age.split('-'))

        # Проверяем, что диапазон возрастов задан корректно
        if age_from >= age_to:
            return 'Неправильный формат ввода возраста'

        self.send_msg(user_id, f' Ищем возраст в пределах от {age_from} и до {age_to}')

    # ищем пользователей на 2 года старше и младше от возраста пользователя, взаимодействующего с ботом.
    # Иначе пользователь вводит интересующий его возрастной интервал, если стандартный вариант не устраивает
    def get_age(self, user_id):
        global age_from, age_to

        self.send_msg(user_id,
                      'Введи "далее", если тебя устраивает поиск людей в стандартном возрастном диапазоне +2 и -2 года от твоего возраста. Если не устраивает вариант по умолчанию, то введи желаемый возрастной диапазон, например 18-25')

        while True:
            events = self.longpoll.listen()
            for event in events:
                if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                    answer = event.text.lower()
                    if answer == "далее":
                        info = self.vk_user_got_api.users.get(user_id=user_id, fields="bdate", )
                        if info and 'bdate' in info[0]:
                            date = info[0]['bdate']
                            date_list = date.split('.')
                            if len(date_list) == 3:
                                year = int(date_list[2])
                                year_now = int(datetime.date.today().year)
                                age = year_now - year
                                age_from = age - 2
                                age_to = age + 2
                                return
                        else:
                            return 'Не удалось получить информацию о пользователе'
                    else:
                        age = answer
                        result = self.input_age(user_id, age)
                        if result:
                            return result
            datetime.sleep(0.1)  # добавляем небольшую паузу между вызовами метода listen()

    # получение города для поиска
    def get_city(self, user_id):
        global city_id, city_title

        self.send_msg(user_id,
                      'Если хочешь искать в своём городе (указан в твоём профиле), пиши "далее". Если же хочешь искать в другом городе, введи его название, например: Москва')

        while True:
            events = self.longpoll.listen()
            for event in events:
                if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                    answer = event.text.lower()

                    if answer == "далее":
                        info = self.vk_user_got_api.users.get(user_id=user_id, fields="city")
                        if info and 'city' in info[0]:
                            city_id = info[0]['city'].get('id')
                            city_title = info[0]['city'].get('title')
                            if not city_id or not city_title:
                                return 'Не удалось получить информацию о городе пользователя'
                            return f' в городе {city_title}'
                        else:
                            return 'Не удалось получить информацию о городе пользователя'

                    else:
                        cities = \
                        self.vk_user_got_api.database.getCities(country_id=1, q=answer.capitalize(), need_all=1,
                                                                count=1000)['items']
                        city = next((c for c in cities if c['title'] == answer.capitalize()), None)
                        if city:
                            city_id = city['id']
                            city_title = city['title']
                            return f' в городе {city_title}'
                        else:
                            return 'Не удалось найти указанный город'
            datetime.sleep(0.1)  # добавляем небольшую паузу между вызовами метода listen()

     # в зависимости от пола пользователя ищем людей противоположного пола
    def get_sex(self, user_id):
        global sex

        info = self.vk_user_got_api.users.get(user_id=user_id, fields="sex")
        if info and 'sex' in info[0]:
            sex = 2 if info[0]['sex'] == 1 else 1
            return sex
        else:
            return 'Не удалось получить информацию о поле пользователя'


    # ищем пользователей, удовлетворяющих запросам, и сохраняем ссылки на них в список
    # id  найденных пользователей сохраняем в БД
    def users_search(self, offset=None):
        global list_found_persons
        list_found_persons = []
        res = self.vk_user_got_api.users.search(
            city=city_id,
            hometown=city_title,
            sex=sex,
            status=1,
            age_from=age_from,
            age_to=age_to,
            has_photo=1,
            count=30,
            offset=offset,
            fields="screen_name"
        )
        if "items" not in res:
            raise Exception("API Error: 'items' key not found in response")
        vk_ids = [person["id"] for person in res["items"] if
                  not person["is_closed"] and ("city" not in person or person["city"]["id"] == city_id)]
        insert_data_search(vk_ids)
        list_found_persons = [f"vk.com/id{vk_id}" for vk_id in vk_ids]
        if not list_found_persons and offset is not None:
            offset += 30
            return self.users_search(offset=offset)
        return list_found_persons

    # сдвигаем offset для нового списка пользователей
    def move_offset(self):
        global offset
        try:
            offset += 30
        except NameError:
            offset = 0
        return offset

    # возвращает 3 лучших(лайки+комменты) фото найденного пользователя
    def get_photo(self, user_id):
        photos = self.vk_user_got_api.photos.get(
            owner_id=user_id,
            album_id='profile',
            extended=1,
            count=30
        )
        if "items" not in photos:
            raise Exception("API Error: 'items' key not found in response")
        top_photos = sorted(photos["items"], key=lambda x: x['likes']['count'] + x['comments']['count'], reverse=True)[
                     :3]
        photo_ids = [f"{user_id}_{photo['id']}" for photo in top_photos]
        attachments = [f"photo{photo_id}" for photo_id in photo_ids]
        return attachments


    # запрашиваем из бд id найденных пользователей
    def get_profile_id(self):
        id_list = [int(person[0]) for person in get_seen_users()]
        return id_list

    def show_found_person(self, user_id):
        threads = []
        for id in self.get_profile_id():
            link = str('vk.com/id' + str(id))
            attachments = self.get_photo(id)
            thread = threading.Thread(target=self.send_msg, args=(user_id, link, attachments))
            thread.start()
            threads.append(thread)

        for thread in threads:
            thread.join()


bot = VKBot()

if __name__ == '__main__':
    bot.show_found_person()
