import logging
import random
import psycopg2
import os
import atexit
import schedule
from threading import Thread
from time import sleep
from config import host, user, password, db_name, bot_token, my_father_id
from telegram import (
    Poll,
    Update,
    InputMediaPhoto,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    Updater,
    CommandHandler,
    PollHandler,
    MessageHandler,
    CallbackQueryHandler,
    Filters,
    CallbackContext,
)

# глобальные переменные
global connection
global users_dict
global amount_of_monuments
global questions_dict
global answers_dict
global hints


# класс пользователя для работы
class User:
    def __init__(self, amount_of_answers, last_stat, wrong_answers, is_on_wrong_answers_sequence, if_hints_required):
        self.amount_of_answers = amount_of_answers
        self.last_stat = last_stat
        self.wrong_answers = wrong_answers
        self.is_on_wrong_answers_sequence = is_on_wrong_answers_sequence
        self.if_hints_required = if_hints_required


# первоначальная загрузка всех данных
def setup_data() -> None:
    logging_file = os.path.join(os.getenv('HOME'), 'test.log')
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s : %(levelname)s : %(message)s',
        filename=logging_file,
        filemode='w',
    )
    global connection
    try:
        connection = psycopg2.connect(
            host=host,
            user=user,
            password=password,
            database=db_name
        )
        connection.autocommit = True

    except Exception as _ex:
        logging.info("Ошибка при работе с PostgreSQL")
        exit(0)

    update_questions_from_db()
    update_users_from_db()
    logging.info("дата апдейтед саксессфулли")


# создаёт экземпляр класса User и записывает данные о новом юзере в бд
def register_user(effective_chat_id, name, if_hints_required) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            'INSERT INTO users (tg_id, tg_name)'
            'VALUES ({tg_id}, \'{tg_name}\');'.format(tg_id=effective_chat_id, tg_name=name.replace("'", "").replace('"', '').replace(";", ""))
        )
    users_dict[effective_chat_id] = User(0, [0] * 100, [], False, if_hints_required)


# обновляет юзеров из базы данных (используется только при запуске бота)
def update_users_from_db() -> None:
    # получение списка пользователей из бд
    global users_dict
    users_dict = {}
    with connection.cursor() as cursor:
        cursor.execute(
            'CREATE TABLE IF NOT EXISTS users('
            'tg_id integer PRIMARY KEY NOT NULL,'
            'tg_name varchar(128),'
            'amount_of_answers integer DEFAULT 0,'
            'wrong_answers integer [][] DEFAULT ARRAY []::integer[], '
            'is_on_wrong_answers_sequence boolean DEFAULT false,'
            'if_hints_required boolean DEFAULT false, '
            'last_stat integer[] DEFAULT ARRAY [0, 0, 0, 0, 0, 0, '
            '0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, '
            '0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, '
            '0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]); '
            'SELECT array_agg(tg_id) FROM users;'
        )
        users_ids = cursor.fetchone()[0]
    if users_ids is not None:
        for i in users_ids:
            with connection.cursor() as cursor:
                cursor.execute(
                    'SELECT amount_of_answers FROM users WHERE tg_id = %d;' % i
                )
                amount_of_answers = cursor.fetchone()[0]
            with connection.cursor() as cursor:
                cursor.execute(
                    'SELECT last_stat FROM users WHERE tg_id = %d;' % i
                )
                last_stat = cursor.fetchone()[0]
            with connection.cursor() as cursor:
                cursor.execute(
                    'SELECT wrong_answers FROM users WHERE tg_id = %d;' % i
                )
                wrong_answers = cursor.fetchone()[0]
            with connection.cursor() as cursor:
                cursor.execute(
                    'SELECT is_on_wrong_answers_sequence FROM users WHERE tg_id = %d;' % i
                )
                is_on_wrong_answers_sequence = cursor.fetchone()[0]
            with connection.cursor() as cursor:
                cursor.execute(
                    'SELECT if_hints_required FROM users WHERE tg_id = %d;' % i
                )
                if_hints_required = cursor.fetchone()[0]
            users_dict[i] = User(amount_of_answers, last_stat, wrong_answers, is_on_wrong_answers_sequence,
                                 if_hints_required)


# обновляет вопросы из базы данных
def update_questions_from_db() -> None:
    global amount_of_monuments
    with connection.cursor() as cursor:
        cursor.execute(
            'SELECT max(id) from raw_questions'
        )
        amount_of_monuments = cursor.fetchone()[0]
    names_of_monuments = [''] * amount_of_monuments
    photos_of_monuments = [''] * amount_of_monuments
    dates_of_monuments = [''] * amount_of_monuments
    facts_of_monuments = [''] * amount_of_monuments
    authors_of_monuments = [''] * amount_of_monuments
    global hints
    hints = [''] * amount_of_monuments

    # получение памятников
    for i in range(amount_of_monuments):
        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT names_of_monuments FROM raw_questions WHERE id = %d;' % (i + 1)
            )
            names_of_monuments[i] = (cursor.fetchone()[0])

        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT photos_of_monuments FROM raw_questions WHERE id = %d;' % (i + 1)
            )
            photos_of_monuments[i] = (cursor.fetchone()[0])
        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT dates_of_monuments FROM raw_questions WHERE id = %d;' % (i + 1)
            )
            dates_of_monuments[i] = (cursor.fetchone()[0])
        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT facts_of_monuments FROM raw_questions WHERE id = %d;' % (i + 1)
            )
            facts_of_monuments[i] = (cursor.fetchone()[0])
        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT authors_of_monuments FROM raw_questions WHERE id = %d;' % (i + 1)
            )
            authors_of_monuments[i] = (cursor.fetchone()[0])
        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT hints FROM raw_questions WHERE id = %d;' % (i + 1)
            )
            hints[i] = (cursor.fetchone()[0])
    for i in range(amount_of_monuments):
        if names_of_monuments[i] is None:
            names_of_monuments[i] = ''
        if photos_of_monuments[i] is None:
            photos_of_monuments[i] = ''
        if dates_of_monuments[i] is None:
            dates_of_monuments[i] = ''
        if facts_of_monuments[i] is None:
            facts_of_monuments[i] = ''
        if authors_of_monuments[i] is None:
            authors_of_monuments[i] = ''
        if hints[i] is None:
            hints[i] = ''
        global questions_dict
        global answers_dict
        # словари вопросов и ответов нужны для функции генерации вопросов
        questions_dict = {
            0: names_of_monuments,
            1: names_of_monuments,
            2: names_of_monuments,
            3: names_of_monuments,
            4: photos_of_monuments,
            5: photos_of_monuments,
            6: photos_of_monuments,
            7: names_of_monuments,
            8: dates_of_monuments,
            9: facts_of_monuments,
            10: authors_of_monuments
        }
        answers_dict = {
            0: dates_of_monuments,
            1: facts_of_monuments,
            2: authors_of_monuments,
            3: dates_of_monuments,
            4: facts_of_monuments,
            5: authors_of_monuments,
            6: names_of_monuments,
            7: photos_of_monuments,
            8: photos_of_monuments,
            9: photos_of_monuments,
            10: photos_of_monuments
        }


# обработчик команды /start
# спрашивает, нужны ли подсказки после неправильных ответов
def start(update: Update, context: CallbackContext) -> None:
    logging.info("start")
    keyboard = [
        [
            InlineKeyboardButton("Подсказки нужны!", callback_data="hints_required"),
            InlineKeyboardButton("Подсказки не нужны!", callback_data="hints_unrequired"),
        ]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Этот бот нужен для подготовки к ЕГЭ по истории. Проходите задания одно за другим, "
                              "и все необходимые памятники культуры сами вам запомнятся. Выберите, пожалуйста, "
                              "нужны ли вам подсказки, выводимые после неправильных ответов, для лучшего запоминания",
                              reply_markup=reply_markup)


# выводит статистику последних 100 вопросов (или меньшего количества, если ответил на меньше вопросов)
def stat(update: Update, context: CallbackContext) -> None:
    if users_dict[update.effective_chat.id].amount_of_answers < 100:
        context.bot.send_message(update.effective_chat.id,
                                 'Велик труд твой, и награда по заслугам, за последние %d '
                                 'вопросов ты ответил правильно на %d!' % (
                                     users_dict[update.effective_chat.id].amount_of_answers,
                                     sum(users_dict[update.effective_chat.id].last_stat)))

    else:
        context.bot.send_message(update.effective_chat.id,
                                 'Велик труд твой, и награда по заслугам, за последние 100 '
                                 'вопросов ты ответил правильно на %d!' % (
                                     sum(users_dict[update.effective_chat.id].last_stat)))


# сохраняет данные пользователей в бд
def save_users_data_to_db() -> None:
    # запись статистики юзеров в бд
    for i in users_dict:
        with connection.cursor() as cursor:
            cursor.execute(
                'UPDATE users SET amount_of_answers = {}, last_stat = ARRAY {}::integer[], wrong_answers = ARRAY {}::integer[], '
                'is_on_wrong_answers_sequence = {}, if_hints_required = {} WHERE tg_id = {}'.format(
                    users_dict[i].amount_of_answers,
                    users_dict[i].last_stat,
                    users_dict[i].wrong_answers,
                    users_dict[i].is_on_wrong_answers_sequence,
                    users_dict[i].if_hints_required, i)
            )


# обработчик команды /help
def helper(update: Update, context: CallbackContext) -> None:
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text="Просто продолжайте отвечать на вопросы, и знания придут к вам. Если бот перестал "
                                  "задавать вопросы, нажмите /start. Если надоело отвечать на старые вопросы и "
                                  "хотите новых, тоже нажмите /start. Если вы хотите включить или отключить подсказки, "
                                  "тоже нажмите /start")


# раз в час сохранение статистики юзеров в бд
def scheduler():
    schedule.every().hour.do(save_users_data_to_db)
    while True:
        schedule.run_pending()
        sleep(3600)


# обработчик незарегистрированных и сервисных команд
def unknown(update: Update, context: CallbackContext) -> None:
    if update.effective_chat.id == my_father_id:
        if update.effective_message.text == '/save_users_data':
            save_users_data_to_db()
            context.bot.send_message(chat_id=update.effective_chat.id, text="Всё сохранил")
        elif update.effective_message.text == '/update_questions':
            update_questions_from_db()
            context.bot.send_message(chat_id=update.effective_chat.id, text="апдейтил куестионс саксессфули")
        elif update.effective_message.text == '/update_pictures':
            # получение id всех картинок и запихивание их в бд
            for i in range(amount_of_monuments):
                g1 = context.bot.send_photo(chat_id=my_father_id, photo=open(str(i) + '.jpg', 'rb'))
                with connection.cursor() as cursor:
                    cursor.execute(
                        'UPDATE raw_questions SET photos_of_monuments = \'' + g1.photo[
                            -1].file_id + '\' WHERE Id = {};'.format(i + 1)
                    )
            context.bot.send_message(chat_id=update.effective_chat.id, text="запилил ид картинок в базу")
        elif update.effective_message.text == '/update_hints':
            hints_texts = ['Подсказка к памятнику Десятинная церковь',
                           'Подсказка к памятнику Собор Святой Софии в Киеве',
                           'Подсказка к памятнику Собор Святой Софии в Киеве',
                           'Подсказка к памятнику Софийский собор в Новгороде',
                           'Подсказка к памятнику Георгиевский собор Юрьева монастыря в Новгороде',
                           'Подсказка к памятнику Церковь Спаса на Нередице',
                           'Подсказка к памятнику Церковь Спаса на Ильине улице',
                           'Подсказка к памятнику Золотые ворота во Владимире',
                           'Подсказка к памятнику Церковь Покрова на Нерли',
                           'Подсказка к памятнику Успенский собор во Владимире',
                           'Подсказка к памятнику Дмитриевский собор во Владимире',
                           'Подсказка к памятнику Троицкий собор Троице - Сергиева монастыря',
                           'Подсказка к памятнику Успенский собор в Москве',
                           'Подсказка к памятнику Спасская башня Московского кремля',
                           'Подсказка к памятнику Благовещенский собор Кремля',
                           'Подсказка к памятнику Грановитая палата',
                           'Подсказка к памятнику Архангельский собор в Москве',
                           'Подсказка к памятнику Колокольня Ивана Великого',
                           'Подсказка к памятнику Церковь Вознесения в Коломенском',
                           'Подсказка к памятнику Собор Покрова на Рву', 'Подсказка к памятнику Смоленский кремль',
                           'Подсказка к памятнику Церковь Покрова в Медведкове',
                           'Подсказка к памятнику Теремной дворец',
                           'Подсказка к памятнику Дворец Алексея Михайловича в Коломенском',
                           'Подсказка к памятнику Церковь Троицы в Никитниках',
                           'Подсказка к памятнику Церковь Рождества Богородицы в Путинках',
                           'Подсказка к памятнику Воскресенский собор Новоиерусалимского монастыря',
                           'Подсказка к памятнику Колокольня Новодевичьего монастыря',
                           'Подсказка к памятнику Церковь Покрова в Филях',
                           'Подсказка к памятнику Меншикова башня(церковь Архангела Гавриила)',
                           'Подсказка к памятнику Архитектурный ансамбль в Кижах',
                           'Подсказка к памятнику Дворец Меншикова в Санкт - Петербурге',
                           'Подсказка к памятнику Петропавловский собор',
                           'Подсказка к памятнику Здание Двенадцати коллегий в Петербурге',
                           'Подсказка к памятнику Летний дворец Петра I в Петербурге']
            for i in range(amount_of_monuments):
                with connection.cursor() as cursor:
                    cursor.execute(
                        'UPDATE raw_questions SET hints = \'{}\' WHERE Id = {};'.format(hints_texts[i], i + 1)
                    )
            context.bot.send_message(chat_id=update.effective_chat.id, text="запилил подсказки в базу")
    else:
        context.bot.send_message(chat_id=update.effective_chat.id, text="Таким командам я не подчиняюсь🖕")


# функция генерации нового вопроса, при задании необязательного
# параметра num_right_monument обязательно использует его как правильный вопрос/ответ
def generate_question(type_question, num_right_monument=True):
    logging.info("generate")
    if num_right_monument is True:
        answers = ['', '', '', '']
        questions = ['', '', '', '']
        num_right_monument = random.randint(0, amount_of_monuments - 1)
        num_right_answer = random.randint(0, 3)
        n = 0
        questions_array = questions_dict[type_question]
        answers_array = answers_dict[type_question]
        while questions_array[num_right_monument] == '' or answers_array[num_right_monument] == '':
            num_right_monument = random.randint(0, amount_of_monuments - 1)
        questions[num_right_answer] = questions_array[num_right_monument]
        answers[num_right_answer] = answers_array[num_right_monument]
        while n < 4:
            if n == num_right_answer:
                answers[n] = answers_array[num_right_monument]
                n += 1
                continue
            num_rnd_answer = random.randint(0, amount_of_monuments - 1)
            while answers_array[num_rnd_answer] in answers or num_rnd_answer == '' or questions_array[
                num_rnd_answer] in questions:
                num_rnd_answer = random.randint(0, amount_of_monuments - 1)
            answers[n] = answers_array[num_rnd_answer]
            questions[n] = questions_array[num_rnd_answer]
            n += 1
        return type_question, questions_array[num_right_monument], answers, num_right_answer, num_right_monument
    else:
        answers = ['', '', '', '']
        questions = ['', '', '', '']
        num_right_answer = random.randint(0, 3)
        n = 0
        questions_array = questions_dict[type_question]
        answers_array = answers_dict[type_question]
        questions[num_right_answer] = questions_array[num_right_monument]
        answers[num_right_answer] = answers_array[num_right_monument]
        while n < 4:
            if n == num_right_answer:
                answers[n] = answers_array[num_right_monument]
                n += 1
                continue
            num_rnd_answer = random.randint(0, amount_of_monuments - 1)
            while answers_array[num_rnd_answer] in answers or num_rnd_answer == '' or questions_array[
                num_rnd_answer] in questions:
                num_rnd_answer = random.randint(0, amount_of_monuments - 1)
            answers[n] = answers_array[num_rnd_answer]
            questions[n] = questions_array[num_rnd_answer]
            n += 1
        return type_question, questions_array[num_right_monument], answers, num_right_answer, num_right_monument


# функция отправки вопроса, сама ничего не генерирует, только отправляет и запоминает в payload тип вопроса и памятник
def send_question(effective_chat_id, type_question, question, answers, num_right_answer, num_right_monument,
                  context: CallbackContext) -> None:
    logging.info("send_question")
    questions_predefined_text = ['', '', '', '', 'Выберите подходящий факт', 'Выберите автора произведения',
                                 'Выберите название', ['1', '2', '3', '4'], ['1', '2', '3', '4'], ['1', '2', '3', '4'],
                                 ['1', '2', '3', '4']]

    if 0 <= type_question <= 3:
        message = context.bot.send_poll(
            chat_id=effective_chat_id, question=question, options=answers, type=Poll.QUIZ,
            correct_option_id=num_right_answer, is_anonymous=True
        )
        payload = {
            message.poll.id: {"chat_id": effective_chat_id, "message_id": message.message_id,
                              "type_question": type_question, "num_right_monument": num_right_monument}
        }
        context.bot_data.update(payload)

    elif 4 <= type_question <= 6:
        context.bot.send_photo(chat_id=effective_chat_id,
                               photo=question)

        message = context.bot.send_poll(
            chat_id=effective_chat_id, question=questions_predefined_text[type_question], options=answers,
            type=Poll.QUIZ,
            correct_option_id=num_right_answer, is_anonymous=True
        )
        payload = {
            message.poll.id: {"chat_id": effective_chat_id, "message_id": message.message_id,
                              "type_question": type_question, "num_right_monument": num_right_monument}
        }
        context.bot_data.update(payload)

    elif 7 <= type_question <= 10:
        context.bot.send_media_group(chat_id=effective_chat_id, media=[
            InputMediaPhoto(answers[0]),
            InputMediaPhoto(answers[1]),
            InputMediaPhoto(answers[2]),
            InputMediaPhoto(answers[3])
        ])
        message = context.bot.send_poll(
            chat_id=effective_chat_id, question=question, options=questions_predefined_text[type_question],
            type=Poll.QUIZ,
            correct_option_id=num_right_answer, is_anonymous=True
        )
        payload = {
            message.poll.id: {"chat_id": effective_chat_id, "message_id": message.message_id,
                              "type_question": type_question, "num_right_monument": num_right_monument}
        }
        context.bot_data.update(payload)


# функция отправки нового вопроса из генератора в send_question
def new_quiz(effective_chat_id, context: CallbackContext) -> None:
    logging.info("new_quiz")
    type_question = random.randint(0, 10)
    type_question, question, answers, num_right_answer, num_right_monument = generate_question(type_question)
    send_question(effective_chat_id, type_question, question, answers, num_right_answer, num_right_monument, context)


# функция отправки старого вопроса из числа отвеченных неправильно, отправляет его в send_question
def old_quiz(effective_chat_id, context: CallbackContext) -> None:
    logging.info("old_quiz")
    type_question, question, answers, num_right_answer, num_right_monument = generate_question(
        users_dict[effective_chat_id].wrong_answers[0][0],
        users_dict[effective_chat_id].wrong_answers[0][1])
    users_dict[effective_chat_id].wrong_answers.pop(0)
    send_question(effective_chat_id, type_question, question, answers, num_right_answer, num_right_monument, context)


# функция запуска последовательности вопросов, на которые отвечали неправильно, пока не закончатся
def repeat_wrong(update: Update, context: CallbackContext) -> None:
    if users_dict[update.effective_chat.id].is_on_wrong_answers_sequence:
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text="Я уже задаю вам те вопросы, на которые вы дали неверные ответы")
    elif len(users_dict[update.effective_chat.id].wrong_answers) == 0:
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text="У вас пока нет вопросов, на которые вы не смогли ответить")
    else:
        users_dict[update.effective_chat.id].is_on_wrong_answers_sequence = True
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text="Далее пойдут вопросы, на которые вы ранее не смогли ответить, и будут идти, "
                                      "пока вы не ответите правильно на все")
        old_quiz(update.effective_chat.id, context)


# функция обработки ответов на вопрос, отправляет данные в БД для статистики и
# запоминания неправильных ответов, так же распределяет юзеров в old_quiz и new_quiz после ответа
def receive_quiz_answer(update: Update, context: CallbackContext) -> None:
    logging.info("receive_quiz_answer")
    # the bot can receive closed poll updates we don't care about
    if update.poll.is_closed:
        return
    if update.poll.total_voter_count == 1:
        try:
            quiz_data = context.bot_data[update.poll.id]
        # this means this poll answer update is from an old poll, we can't stop it then
        except KeyError:
            return
        context.bot.stop_poll(quiz_data["chat_id"], quiz_data["message_id"])
        users_dict[quiz_data["chat_id"]].amount_of_answers += 1
        # обработка правильности ответа
        answers = [update.poll.options[0].voter_count, update.poll.options[1].voter_count,
                   update.poll.options[2].voter_count, update.poll.options[3].voter_count]
        if update.poll.correct_option_id == answers.index(1):  # правильный ответ
            users_dict[quiz_data["chat_id"]].last_stat.pop(0)
            users_dict[quiz_data["chat_id"]].last_stat.append(1)
            next_question(quiz_data["chat_id"], context)
        else:  # неправильный ответ
            users_dict[quiz_data["chat_id"]].last_stat.pop(0)
            users_dict[quiz_data["chat_id"]].last_stat.append(0)
            users_dict[quiz_data["chat_id"]].wrong_answers.append(
                [quiz_data["type_question"], quiz_data["num_right_monument"]])
            if users_dict[quiz_data["chat_id"]].if_hints_required:
                keyboard = [
                    [
                        InlineKeyboardButton("Следующий вопрос", callback_data="next_question")
                    ]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                context.bot.send_photo(chat_id=quiz_data["chat_id"],
                                       caption=hints[quiz_data["num_right_monument"]],
                                       photo=questions_dict[4][quiz_data["num_right_monument"]],
                                       reply_markup=reply_markup)
            else:
                next_question(quiz_data["chat_id"], context)


# обрабатывает переход к следующему вопросу
def next_question(effective_chat_id, context: CallbackContext):
    if users_dict[effective_chat_id].is_on_wrong_answers_sequence:
        if len(users_dict[effective_chat_id].wrong_answers) == 0:
            context.bot.send_message(chat_id=effective_chat_id,
                                     text="Вы ответили на все вопросы, на которые ранее отвечали "
                                          "неправильно! Отныне буду задавать вам только новые вопросы")
            users_dict[effective_chat_id].is_on_wrong_answers_sequence = False
            new_quiz(effective_chat_id, context)
        else:
            old_quiz(effective_chat_id, context)
    else:
        new_quiz(effective_chat_id, context)


# обработчик нажатия кнопок
# обрабатывает необходимость подсказок, если юзер обратился в первый раз отправлет его на регистрацию,
# а так же переключает прохождение последовательности старых вопросов на новые (но не сами вопросы)
# а ещё задаёт следующий вопрос после нажатия кнопки следующий вопрос (если нужны подсказки)
def if_hints_required_button(update: Update, context: CallbackContext) -> None:
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query

    # CallbackQueries need to be answered, even if no notification to the user is needed
    # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
    query.answer()
    if query.data == "next_question":
        query.edit_message_caption(
            caption=update.effective_message.caption)
        next_question(update.effective_chat.id, context)
    elif query.data == "hints_unrequired":
        query.edit_message_text(
            text="Этот бот нужен для подготовки к ЕГЭ по истории. Проходите задания одно за другим, и все необходимые "
                 "памятники культуры сами вам запомнятся. Подсказки отключил.")
        if update.effective_chat.id not in users_dict:
            register_user(update.effective_chat.id, update.effective_chat.full_name, False)
        users_dict[update.effective_chat.id].is_on_wrong_answers_sequence = False
        users_dict[update.effective_chat.id].if_hints_required = False
        new_quiz(update.effective_chat.id, context)
    elif query.data == "hints_required":
        query.edit_message_text(
            text="Этот бот нужен для подготовки к ЕГЭ по истории. Проходите задания одно за другим, и все необходимые "
                 "памятники культуры сами вам запомнятся. Подсказки включил.")
        if update.effective_chat.id not in users_dict:
            register_user(update.effective_chat.id, update.effective_chat.full_name, True)
        users_dict[update.effective_chat.id].is_on_wrong_answers_sequence = False
        users_dict[update.effective_chat.id].if_hints_required = True
        new_quiz(update.effective_chat.id, context)


def main() -> None:
    setup_data()

    """Run bot."""
    # Create the Updater and pass it your bot's token.
    updater = Updater(bot_token)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CommandHandler('start', start))
    updater.dispatcher.add_handler(CallbackQueryHandler(if_hints_required_button))
    dispatcher.add_handler(PollHandler(receive_quiz_answer))
    dispatcher.add_handler(CommandHandler('help', helper))
    dispatcher.add_handler(CommandHandler('stat', stat))
    dispatcher.add_handler(CommandHandler('repeat_wrong', repeat_wrong))
    dispatcher.add_handler(MessageHandler(Filters.command, unknown))
    # Start the Bot
    updater.start_polling()
    random.seed()
    t = Thread(target=scheduler)
    t.start()


if __name__ == "__main__":
    main()


# на выходе сохраняет данные пользователей в бд и закрывает подключение к бд
@atexit.register
def goodbye():
    save_users_data_to_db()
    # закрытие соединения с бд
    if connection:
        connection.close()
        logging.info("Подключение к PostgreSQL закрыто")
        logging.info("Бот закрыт")
