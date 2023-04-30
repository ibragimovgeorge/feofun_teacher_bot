import postgres_handler


# класс пользователя для работы
class User:
    def __init__(self, name, amount_of_answers, last_stat, wrong_answers, is_on_wrong_answers_sequence,
                 if_hints_required,
                 periods, themes):
        self.name = name
        self.amount_of_answers = amount_of_answers
        self.last_stat = last_stat
        self.wrong_answers = wrong_answers
        self.is_on_wrong_answers_sequence = is_on_wrong_answers_sequence
        self.if_hints_required = if_hints_required
        self.periods = periods
        self.themes = themes


# создаёт экземпляр класса User и записывает данные о новом юзере в бд
def register_user(effective_chat_id, name, if_hints_required):
    postgres_handler.write_user_to_db(effective_chat_id, name)
    return User(name, 0, [0] * 100, [], False, if_hints_required, "all_periods", "all_themes")


# обновляет юзеров из базы данных (используется только при запуске бота)
def update_users_from_db() -> dict:
    users_ids = postgres_handler.get_users_ids()
    users_dict = {}
    if users_ids is not None:
        for i in users_ids:
            name, amount_of_answers, last_stat, wrong_answers, is_on_wrong_answers_sequence, if_hints_required, periods, themes = postgres_handler.read_user_from_db(i)
            users_dict[i] = User(name, amount_of_answers, last_stat, wrong_answers, is_on_wrong_answers_sequence,
                                 if_hints_required, periods, themes)
    return users_dict


# сохраняет данные пользователей в бд
def save_users_to_db(users_dict) -> int:
    # запись статистики юзеров в бд
    for i in users_dict:
        postgres_handler.write_user_to_db(i,
                                          users_dict[i].name,
                                          users_dict[i].amount_of_answers,
                                          users_dict[i].last_stat,
                                          users_dict[i].wrong_answers,
                                          users_dict[i].is_on_wrong_answers_sequence,
                                          users_dict[i].if_hints_required,
                                          users_dict[i].periods,
                                          users_dict[i].themes)
    return 0