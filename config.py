amount_of_types_of_questions = 11
# словари разбивки массивов по типам вопроса, нужны для генерации основных словарей и понимания типов вопросов
questions_layout = {
        0: 'names',
        1: 'names',
        2: 'names',
        3: 'names',
        4: 'photos',
        5: 'photos',
        6: 'photos',
        7: 'names',
        8: 'dates',
        9: 'facts',
        10: 'authors'
    }
answers_layout = {
        0: 'dates',
        1: 'facts',
        2: 'authors',
        3: 'dates',
        4: 'facts',
        5: 'authors',
        6: 'names',
        7: 'photos',
        8: 'photos',
        9: 'photos',
        10: 'photos'
    }
types_of_questions = {
    'text_to_text': (0, 1, 2, 3),
    'picture_to_text': (4, 5, 6),
    'text_to_pictures': (7, 8, 9, 10)
}


#периоды и темы. обязательно последним идёт объединяющий все периоды и все темы (все категории первого вида и все категории второго вида
periods_themes = {'before_18': ('до XVIII века', 'до XVIII века.'), '18-19': ('XVIII-XIX века', 'XVIII-XIX века.'), '20-21': ('XX-XXI века', 'XX-XXI века.'), 'all_periods': ('Все периоды', 'всех периодов.'), 'architecture': ('Архитектура', 'архитектуре'), 'painting': ('Живопись', 'живописи'), 'sculpture': ('Скульптура', 'скульптуре'), 'imagine': ('Памятники эпохи', 'памятникам эпохи'), 'all_themes': ('Все темы', 'всем темам')}
amount_of_periods = 4
amount_of_themes = 5
monuments_csv_url = 'https://docs.google.com/spreadsheets/d/1AzqQFhFYvSEK8X1w3QRzUwoI24MXJHFUZwHys_qaMfc/export?format=csv'
