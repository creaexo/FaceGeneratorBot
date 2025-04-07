import os
import uuid
import requests
import telebot
from telebot import types
from telebot.types import Message, ReplyKeyboardMarkup, InputMediaPhoto
from typing import List

bot = telebot.TeleBot(os.environ['TELEGRAM_TOKEN'])

IMAGE_URL = "https://thispersondoesnotexist.com/"
MAX_IMAGES = 100
GROUP_SIZE = 9


def create_main_markup() -> ReplyKeyboardMarkup:
    """
    Создает и возвращает основное меню с кнопками.

    :return: Клавиатура с основными действиями.
    """
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    markup.add(
        types.KeyboardButton('Получить изображение'),
        types.KeyboardButton('Получить 9 изображений'),
        types.KeyboardButton('Своё количество')
    )
    return markup


def create_quantity_markup() -> ReplyKeyboardMarkup:
    """
    Создает и возвращает меню выбора количества изображений.

    :return: Клавиатура с вариантами выбора количества.
    :rtype: Меню кнопок с количеством изображений.
    """
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    markup.add(
        types.KeyboardButton('Назад'),
        types.KeyboardButton('30'),
        types.KeyboardButton('60'),
        types.KeyboardButton('90')
    )
    return markup


def download_image() -> str:
    """
    Загружает одно случайное изображение с сайта и сохраняет во временный файл.

    :return: Путь к сохраненному изображению.
    """
    filename = f"{uuid.uuid4()}.jpg"
    response = requests.get(IMAGE_URL)
    with open(filename, "wb") as f:
        f.write(response.content)
    return filename


@bot.message_handler(commands=['start'])
def handle_start(message: Message) -> None:
    """
    Обрабатывает команду /start. Отправляет приветственное сообщение с меню.

    :param message: Объект сообщения Telegram.
    """
    bot.send_message(
        message.chat.id,
        "Привет! Нажми на кнопку и получи сгенерированное лицо",
        parse_mode='html',
        reply_markup=create_main_markup()
    )


@bot.message_handler(content_types=['text'])
def handle_text(message: Message) -> None:
    """
    Обрабатывает текстовые команды от пользователя и перенаправляет на соответствующее действие.

    :param message: Объект сообщения Telegram.
    """
    text = message.text.strip().lower()

    try:
        bot.delete_message(message.chat.id, message.id - 1)
    except Exception as e:
        print(f"Ошибка при удалении сообщения: {e}")

    if text == 'получить изображение':
        send_single_image(message)

    elif text == 'получить 9 изображений':
        send_multiple_images(message, 9)

    elif text == 'своё количество':
        ask_for_custom_quantity(message)

    else:
        bot.send_message(message.chat.id, "Главная страница", parse_mode='html', reply_markup=create_main_markup())


def send_single_image(message: Message) -> None:
    """
    Загружает и отправляет одно изображение пользователю.

    :param message: Объект сообщения Telegram.
    """
    filename = download_image()
    with open(filename, 'rb') as img:
        bot.send_photo(message.chat.id, img)

    os.remove(filename)

    try:
        bot.delete_message(message.chat.id, message.id)
    except:
        pass

    bot.send_message(message.chat.id, "Готово! Выберите следующую команду", parse_mode='html', reply_markup=create_main_markup())


def send_multiple_images(message: Message, count: int) -> None:
    """
    Загружает и отправляет несколько изображений в группах по GROUP_SIZE.

    :param message: Объект сообщения Telegram.
    :param count: Количество изображений для отправки.
    """
    images: List[InputMediaPhoto] = []
    filenames: List[str] = []

    progress_msg = bot.send_message(
        message.chat.id,
        f"Генерация 0/{count}. Пожалуйста, не отправляйте сообщения, пока процесс не завершится.",
        parse_mode='html'
    )

    for i in range(1, count + 1):
        filename = download_image()
        filenames.append(filename)
        with open(filename, 'rb') as img_file:
            images.append(types.InputMediaPhoto(img_file.read()))

        bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=progress_msg.message_id,
            text=f"Генерация {i}/{count}. Пожалуйста, не отправляйте сообщения."
        )

        if len(images) == GROUP_SIZE or i == count:
            bot.send_media_group(message.chat.id, images)
            images.clear()

    try:
        bot.delete_message(message.chat.id, progress_msg.message_id)
    except:
        pass

    for file in filenames:
        os.remove(file)

    bot.send_message(message.chat.id, "Готово! Выберите следующую команду", parse_mode='html', reply_markup=create_main_markup())


def ask_for_custom_quantity(message: Message) -> None:
    """
    Запрашивает у пользователя количество изображений, которые он хочет получить.

    :param message: Объект сообщения Telegram.
    """
    prompt = bot.send_message(
        message.chat.id,
        "Напишите, сколько лиц сгенерировать. Максимум 100",
        parse_mode='html',
        reply_markup=create_quantity_markup()
    )
    bot.register_next_step_handler(prompt, handle_custom_quantity)


def handle_custom_quantity(message: Message) -> None:
    """
    Обрабатывает ввод пользователя с числом изображений.
    Проверяет корректность и запускает генерацию или просит повторить ввод.

    :param message: Объект сообщения Telegram.
    """
    if message.text.lower() == 'назад':
        bot.send_message(message.chat.id, "Вы вернулись на главную страницу", reply_markup=create_main_markup())
        return

    try:
        quantity = int(message.text)
        if 1 <= quantity <= MAX_IMAGES:
            generate_custom_images(message, quantity)
        else:
            raise ValueError
    except ValueError:
        retry_msg = bot.send_message(
            message.chat.id,
            "Введите число от 1 до 100",
            parse_mode='html',
            reply_markup=create_quantity_markup()
        )
        bot.register_next_step_handler(retry_msg, handle_custom_quantity)


def generate_custom_images(message: Message, total_count: int) -> None:
    """
    Генерирует и отправляет указанное пользователем количество изображений.

    :param message: Объект сообщения Telegram.
    :param total_count: Общее количество изображений для генерации.
    """
    ...
    images: List[InputMediaPhoto] = []
    filenames: List[str] = []
    sent = 0

    progress_msg = bot.send_message(
        message.chat.id,
        f"Генерация 0/{total_count}. Пожалуйста, не отправляйте сообщения.",
        parse_mode='html'
    )

    for i in range(1, total_count + 1):
        filename = download_image()
        filenames.append(filename)
        with open(filename, 'rb') as img_file:
            images.append(types.InputMediaPhoto(img_file.read()))

        sent += 1
        bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=progress_msg.message_id,
            text=f"Генерация {sent}/{total_count}. Пожалуйста, не отправляйте сообщения."
        )

        if len(images) == GROUP_SIZE or i == total_count:
            bot.send_media_group(message.chat.id, images)
            images.clear()

    try:
        bot.delete_message(message.chat.id, progress_msg.message_id)
    except:
        pass

    for file in filenames:
        os.remove(file)

    bot.send_message(message.chat.id, "Готово! Выберите следующую команду", parse_mode='html', reply_markup=create_main_markup())


if __name__ == '__main__':
    bot.polling(none_stop=True)
