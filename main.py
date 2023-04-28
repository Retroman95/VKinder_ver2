from vk_api.longpoll import VkEventType, VkLongPoll
from bot import bot
from db import create_database


if __name__ == '__main__':
    create_database()
    for event in bot.longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me:
            res = event.text.lower()
            user_id = event.user_id
            if res == 'поиск':
                bot.get_age(user_id)
                bot.get_city(user_id)
                bot.get_sex(user_id)
                bot.users_search(bot.move_offset())
                bot.show_found_person(user_id)
            elif res == 'привет':
                bot.send_msg(user_id,f'Привет! Бот Vkinder готов к поиску! Набери "поиск", если хочешь начать искать пользователей')
            elif res == 'пока':
                bot.send_msg(user_id,f'Пока! Увидимся в следующий раз!')
            else:
                bot.send_msg(user_id, f'Прости, не понял тебя...')
