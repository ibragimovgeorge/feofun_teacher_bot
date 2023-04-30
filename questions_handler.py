import postgres_handler
import random
import pandas as pd
from config import amount_of_types_of_questions, amount_of_periods, amount_of_themes, questions_layout, answers_layout, periods_themes


global questions_dict, answers_dict
random.seed()
# обновляет вопросы из базы данных
def update_questions_from_db():
    pd.options.display.max_rows = 100
    pd.options.display.max_columns = 10
    data = postgres_handler.get_monuments()
    questions_df = pd.DataFrame(data=data, index=range(1, len(data)+1), columns=['names', 'photos', 'dates', 'facts', 'authors', 'hints', 'periods', 'themes'])
    #очистка от NaN
    questions_df.fillna('', inplace=True)

    # словари вопросов и ответов для функции генерации вопросов
    # разбиты по периодам и темам (в трёхмерный словарь [период][тема][тип вопроса])
    # аналогично разбит словарь подсказок для корректного вывода оных (только без типа вопроса, конечно)
    #генерация вопросов и ответов
    global questions_dict, answers_dict
    questions_dict = {i: {
        j: {k: questions_df[questions_df['periods'] == i][questions_df['themes'] == j][questions_layout[k]] for k
            in range(amount_of_types_of_questions)} for j in list(periods_themes)[amount_of_periods:]} for i in
                      list(periods_themes)[0:amount_of_periods]}
    answers_dict = {i: {
        j: {k: questions_df[questions_df['periods'] == i][questions_df['themes'] == j][answers_layout[k]] for k
            in range(amount_of_types_of_questions)} for j in list(periods_themes)[amount_of_periods:]} for i in
                      list(periods_themes)[0:amount_of_periods]}
    for j in list(periods_themes)[amount_of_periods:]:
        for k in range(amount_of_types_of_questions):
            questions_dict['all_periods'][j][k] = questions_df[questions_df['themes'] == j][questions_layout[k]]
            answers_dict['all_periods'][j][k] = questions_df[questions_df['themes'] == j][answers_layout[k]]
    for i in list(periods_themes)[0:amount_of_periods]:
        for k in range(amount_of_types_of_questions):
            questions_dict[i]['all_themes'][k] = questions_df[questions_df['periods'] == i][questions_layout[k]]
            answers_dict[i]['all_themes'][k] = questions_df[questions_df['periods'] == i][answers_layout[k]]
    for k in range(amount_of_types_of_questions):
        questions_dict['all_periods']['all_themes'][k] = questions_df[questions_layout[k]]
        answers_dict['all_periods']['all_themes'][k] = questions_df[answers_layout[k]]


    hints_dict = {i: [questions_df.photos[i], questions_df.hints[i]] for i in questions_df.index}
    return hints_dict


# функция генерации нового вопроса, при задании необязательного
# параметра num_right_monument обязательно использует его как правильный вопрос/ответ
def generate_question(period, theme,
                      num_right_monument=True, type_question = True):
    if num_right_monument is True:
        type_question = random.choice(range(amount_of_types_of_questions))
        while len(questions_dict[period][theme][type_question])-questions_dict[period][theme][type_question].tolist().count('') < 4 or len(answers_dict[period][theme][type_question])-answers_dict[period][theme][type_question].tolist().count('') < 4:
            type_question = random.choice(range(amount_of_types_of_questions))
        answers = ['', '', '', '']
        questions = ['', '', '', '']
        questions_array = questions_dict[period][theme][type_question]
        answers_array = answers_dict[period][theme][type_question]
        num_right_monument = random.choice(list(questions_array.axes[0]))
        num_right_answer = random.randint(0, 3)
        n = 0
        while questions_array[num_right_monument] == '' or answers_array[num_right_monument] == '':
            num_right_monument = random.choice(list(questions_array.axes[0]))
        questions[num_right_answer] = questions_array[num_right_monument]
        answers[num_right_answer] = answers_array[num_right_monument]
        while n < 4:
            if n == num_right_answer:
                answers[n] = answers_array[num_right_monument]
                n += 1
                continue
            num_rnd_answer = random.choice(list(questions_array.axes[0]))
            while answers_array[num_rnd_answer] in answers or num_rnd_answer == '' or \
                    questions_array[num_rnd_answer] in questions:
                num_rnd_answer = random.choice(list(questions_array.axes[0]))
            answers[n] = answers_array[num_rnd_answer]
            questions[n] = questions_array[num_rnd_answer]
            n += 1
        return type_question, questions_array[num_right_monument], answers, num_right_answer, num_right_monument
    else:
        answers = ['', '', '', '']
        questions = ['', '', '', '']
        num_right_answer = random.randint(0, 3)
        n = 0
        questions_array = questions_dict['all_periods']['all_themes'][type_question]
        answers_array = answers_dict['all_periods']['all_themes'][type_question]
        questions[num_right_answer] = questions_array[num_right_monument]
        answers[num_right_answer] = answers_array[num_right_monument]
        while n < 4:
            if n == num_right_answer:
                answers[n] = answers_array[num_right_monument]
                n += 1
                continue
            num_rnd_answer = random.choice(list(questions_array.axes[0]))
            while answers_array[num_rnd_answer] in answers or num_rnd_answer == '' or \
                    questions_array[num_rnd_answer] in questions:
                num_rnd_answer = random.choice(list(questions_array.axes[0]))
            answers[n] = answers_array[num_rnd_answer]
            questions[n] = questions_array[num_rnd_answer]
            n += 1
        return type_question, questions_array[num_right_monument], answers, num_right_answer, num_right_monument

def amount_of_monuments_in_period_theme_more_than_4 (period: str, theme: str) -> bool:
    return (len(questions_dict[period][theme][0]) >= 4)
    pass
