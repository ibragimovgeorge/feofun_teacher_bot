import logging
import random
import os
from dotenv import load_dotenv
import atexit
import schedule
from threading import Thread
from time import sleep

from config import types_of_questions, periods_themes, amount_of_periods
import users_handler
import postgres_handler
import questions_handler
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
    CallbackContext, PicklePersistence,
)

# глобальные переменные
global connection
global users_dict
global hints
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
my_father_id, my_mother_id, bot_token, monuments_csv_url = int(os.environ.get('my_father_id')), int(os.environ.get('my_mother_id')), os.environ.get('bot_token'), os.environ.get('monuments_csv_url')

# первоначальная загрузка всех данных
def setup_data():
    logging_file = os.path.join(os.getenv('HOME'), 'test.log')
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s : %(levelname)s : %(message)s',
        filename=logging_file,
        filemode='w',
    )
    logging.disable(logging.DEBUG)

    global users_dict
    users_dict = users_handler.update_users_from_db()
    global hints
    hints = questions_handler.update_questions_from_db()

    logging.info("дата апдейтед саксессфулли, бот стартед")


# обработчик команды /start
# спрашивает, нужны ли подсказки после неправильных ответов
def start(update: Update, context: CallbackContext) -> None:
    logging.info("start with user " + update.effective_chat.full_name + " with id " + str(update.effective_chat.id))
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
                                 f'Велик труд твой, и награда по заслугам, за последние {users_dict[update.effective_chat.id].amount_of_answers} '
                                 f'вопросов ты ответил правильно на {sum(users_dict[update.effective_chat.id].last_stat)}!')

    else:
        context.bot.send_message(update.effective_chat.id,
                                 f'Велик труд твой, и награда по заслугам, за последние 100 '
                                 f'вопросов ты ответил правильно на {sum(users_dict[update.effective_chat.id].last_stat)}')


# обработчик команды /help
def helper(update: Update, context: CallbackContext) -> None:
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text="Просто продолжайте отвечать на вопросы, и знания придут к вам. Если бот перестал "
                                  "задавать вопросы, нажмите /start. Если надоело отвечать на старые вопросы и "
                                  "хотите новых, тоже нажмите /start. Если вы хотите включить или отключить подсказки, "
                                  "тоже нажмите /start. Если хотите тщательнее повторить определённый период или тему, "
                                  "нажмите /set_periods или /set_themes")


# раз в час сохранение статистики юзеров в бд
def scheduler():
    schedule.every().hour.do(users_handler.save_users_to_db, users_dict)
    while True:
        schedule.run_pending()
        sleep(3600)


# обработчик незарегистрированных и сервисных команд
def unknown(update: Update, context: CallbackContext) -> None:
    if update.effective_chat.id in [my_father_id, my_mother_id]:
        if update.effective_message.text == '/save_users_data':
            users_handler.save_users_to_db(users_dict)
            context.bot.send_message(chat_id=update.effective_chat.id, text="сохранил юзеров в бд")
        elif update.effective_message.text == '/update_questions':
            questions_handler.update_questions_from_db()
            context.bot.send_message(chat_id=update.effective_chat.id, text="апдейтил куестионс саксессфули")
        elif update.effective_message.text == '/update_questions_from_csv':
            postgres_handler.update_questions_from_csv(monuments_csv_url, update.effective_chat.id, context)
            context.bot.send_message(chat_id=update.effective_chat.id, text="запилил ид картинок в базу, успешно апдейтил все монументы")
        elif update.effective_message.text == '/logs':
            context.bot.send_document(chat_id=update.effective_chat.id, document=open(os.path.join(os.getenv('HOME'), 'test.log')))
    else:
        context.bot.send_message(chat_id=update.effective_chat.id, text="Таким командам я не подчиняюсь🖕")


# функция отправки вопроса, сама ничего не генерирует, только отправляет и запоминает в payload тип вопроса и памятник
def send_question(effective_chat_id, type_question, question, answers, num_right_answer, num_right_monument,
                  context: CallbackContext) -> None:
    logging.info("send_question")
    questions_predefined_text = ('', '', '', '', 'Выберите подходящий факт', 'Выберите автора произведения',
                                 'Выберите название', ('1', '2', '3', '4'), ('1', '2', '3', '4'), ('1', '2', '3', '4'),
                                 ('1', '2', '3', '4'))

    if type_question in types_of_questions['text_to_text']:
        message = context.bot.send_poll(
            chat_id=effective_chat_id, question=question, options=answers, type=Poll.QUIZ,
            correct_option_id=num_right_answer, is_anonymous=True
        )
        payload = {
            message.poll.id: {"chat_id": effective_chat_id, "message_id": message.message_id,
                              "type_question": type_question, "num_right_monument": num_right_monument}
        }
        context.bot_data.update(payload)

    elif type_question in types_of_questions['picture_to_text']:
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

    elif type_question in types_of_questions['text_to_pictures']:
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
def new_quiz(effective_chat_id, context: CallbackContext):
    logging.info("new_quiz")
    type_question, question, answers, num_right_answer, num_right_monument = questions_handler.generate_question(
        period=users_dict[effective_chat_id].periods,
        theme=users_dict[effective_chat_id].themes,
    )
    send_question(effective_chat_id, type_question, question, answers, num_right_answer, num_right_monument, context)


# функция отправки старого вопроса из числа отвеченных неправильно, отправляет его в send_question
def old_quiz(effective_chat_id, context: CallbackContext):
    logging.info("old_quiz")
    type_question, question, answers, num_right_answer, num_right_monument = questions_handler.generate_question(
        period=users_dict[effective_chat_id].periods,
        theme=users_dict[effective_chat_id].themes,
        num_right_monument=users_dict[effective_chat_id].wrong_answers[0][1],
        type_question=users_dict[effective_chat_id].wrong_answers[0][0]
    )
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

                #посылает справку с фото о памятнике из неправильно выбранного ответа
                context.bot.send_photo(chat_id=quiz_data["chat_id"],
                                       caption=hints[quiz_data["num_right_monument"]][1],
                                       photo=hints[quiz_data["num_right_monument"]][0],
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
def buttons_handler(update: Update, context: CallbackContext) -> None:
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
                 "памятники культуры сами вам запомнятся. Подсказки отключил. Если хотите тщательнее повторить "
                 "определённый период или тему, нажмите /set_periods или /set_themes")
        if update.effective_chat.id not in users_dict:
            users_dict[update.effective_chat.id] = users_handler.register_user(update.effective_chat.id,
                                                                               update.effective_chat.full_name, False)
        users_dict[update.effective_chat.id].is_on_wrong_answers_sequence = False
        users_dict[update.effective_chat.id].if_hints_required = False
        new_quiz(update.effective_chat.id, context)
    elif query.data == "hints_required":
        query.edit_message_text(
            text="Этот бот нужен для подготовки к ЕГЭ по истории. Проходите задания одно за другим, и все необходимые "
                 "памятники культуры сами вам запомнятся. Подсказки включил. Если хотите тщательнее повторить "
                 "определённый период или тему, нажмите /set_periods или /set_themes")
        if update.effective_chat.id not in users_dict:
            users_dict[update.effective_chat.id] = users_handler.register_user(update.effective_chat.id,
                                                                               update.effective_chat.full_name, True)
        users_dict[update.effective_chat.id].is_on_wrong_answers_sequence = False
        users_dict[update.effective_chat.id].if_hints_required = True
        new_quiz(update.effective_chat.id, context)
    elif query.data in list(periods_themes)[0:amount_of_periods]:
        users_dict[update.effective_chat.id].periods = query.data
        query.edit_message_text(
            text="Теперь буду задавать вопросы по {} {}".format(
                periods_themes[users_dict[update.effective_chat.id].themes][1],
                periods_themes[users_dict[update.effective_chat.id].periods][1]))
        next_question(update.effective_chat.id, context)
    elif query.data in list(periods_themes)[amount_of_periods:]:
        users_dict[update.effective_chat.id].themes = query.data
        query.edit_message_text(
            text="Теперь буду задавать вопросы по {} {}".format(
                periods_themes[users_dict[update.effective_chat.id].themes][1],
                periods_themes[users_dict[update.effective_chat.id].periods][1]))
        next_question(update.effective_chat.id, context)


def set_periods(update: Update, context: CallbackContext) -> None:
    keyboard = [
        [InlineKeyboardButton(periods_themes[i][0], callback_data=i)] for i in list(periods_themes)[0:amount_of_periods] if (questions_handler.amount_of_monuments_in_period_theme_more_than_4(i, users_dict[update.effective_chat.id].themes))
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Выберите период, который хотите повторить. Если периодов не хватает, значит нет столько памятников по выбранной теме:",
                              reply_markup=reply_markup)


def set_themes(update: Update, context: CallbackContext) -> None:
    keyboard = [
        [InlineKeyboardButton(periods_themes[i][0], callback_data=i)] for i in list(periods_themes)[amount_of_periods:] if (questions_handler.amount_of_monuments_in_period_theme_more_than_4(users_dict[update.effective_chat.id].periods, i))
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Выберите тему, которую хотите повторить. Если каких-то тем не хватает, значит нет столькор памятников в выбранном периоде:",
                              reply_markup=reply_markup)

def downloader(update: Update, context: CallbackContext) -> None:
    if update.effective_chat.id in [my_father_id, my_mother_id]:
        postgres_handler.update_questions_from_csv(context.bot.get_file(update.message.document).download(), update.effective_chat.id, context)

def get_picture_id(url: str, chat_id, context, name)->str:
    try:
        return context.bot.send_photo(chat_id=chat_id, photo=url).photo[-1].file_id
    except Exception as e:
        return context.bot.send_message(chat_id=chat_id, text='одна из картинок более недоступна к загрузке, замените урл в файле, имя памятника ' + name)

def main() -> None:
    setup_data()
    #my_persistence = PicklePersistence(filepath='my_file')
    """Run bot."""
    # Create the Updater and pass it your bot's token.
    updater = Updater(bot_token)#.persistence(persistence=my_persistence)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CommandHandler('start', start))
    updater.dispatcher.add_handler(CallbackQueryHandler(buttons_handler))
    dispatcher.add_handler(PollHandler(receive_quiz_answer))
    dispatcher.add_handler(CommandHandler('help', helper))
    dispatcher.add_handler(CommandHandler('stat', stat))
    dispatcher.add_handler(CommandHandler('repeat_wrong', repeat_wrong))
    dispatcher.add_handler(CommandHandler('set_periods', set_periods))
    dispatcher.add_handler(CommandHandler('set_themes', set_themes))
    dispatcher.add_handler(MessageHandler(Filters.command, unknown))
    dispatcher.add_handler(MessageHandler(Filters.document, downloader))
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
    users_handler.save_users_to_db(users_dict)
    #postgres_handler.save_bot_data(context.bot_data, context.user_data, context.chat_data)
    postgres_handler.close_connection()
    logging.info("Бот закрыт")
