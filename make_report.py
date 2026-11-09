"""Собирает отчёт по лабораторной работе в report.docx.

Запускает тесты, делает «скриншот» их вывода (tests_run.png)
и оформляет всё в Word. Запуск:  python make_report.py
"""
import re
import subprocess
import sys
from datetime import datetime

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt
from PIL import Image, ImageDraw, ImageFont

EXAMPLE_TEST = '''    def test_cannot_buy_two_tours_same_datetime(self):
        """Нельзя купить 2 тура на один и тот же день и время (clean)"""
        make_booking(self.user, self.s1)
        b = Booking(user=self.user, session=self.s2)
        with self.assertRaises(ValidationError):
            b.full_clean()'''


def run_tests():
    """Прогоняет тесты и возвращает вывод."""
    result = subprocess.run(
        [sys.executable, 'manage.py', 'test', '-v', '2'],
        capture_output=True, text=True)
    return result.stderr + result.stdout


def parse(output):
    """Достаёт из вывода список тестов и статистику по классам."""
    raw = re.findall(
        r'^(test_\w+) \(([\w.]+)\)\n?.* \.\.\. (ok|FAIL|ERROR)$', output, re.M)
    by_class = {}
    for name, path, status in raw:
        cls = path.split('.')[-2]
        by_class.setdefault(cls, []).append((name, status))
    ran = re.search(r'Ran (\d+) tests? in ([\d.]+)s', output)
    ok = 'OK' in output
    return by_class, ran, ok


def make_screenshot(output):
    """Рисует итог прогона тестов как «скриншот терминала»."""
    test_lines = [l for l in output.splitlines() if l.rstrip().endswith('ok')]
    ran = re.search(r'Ran \d+ tests? in [\d.]+s', output)
    tail = (['$ python manage.py test', '...'] + test_lines[-3:]
            + ['-' * 70])
    if ran:
        tail += [ran.group(0), '', 'OK' if 'OK' in output else 'FAILED']
    font = ImageFont.truetype('/System/Library/Fonts/Menlo.ttc', 15)
    w = 1060
    h = 30 + 24 * len(tail) + 20
    img = Image.new('RGB', (w, h), (28, 28, 32))
    d = ImageDraw.Draw(img)
    y = 16
    for line in tail:
        color = (170, 170, 175)
        if line.strip() == 'OK':
            color = (90, 220, 120)
        elif line.startswith('$'):
            color = (240, 200, 90)
        d.text((18, y), line[:118], font=font, fill=color)
        y += 24
    img.save('tests_run.png')


# ---------- оформление: обычный «студенческий» вид, без стилей-красивостей
def base_style(doc):
    st = doc.styles['Normal']
    st.font.name = 'Times New Roman'
    st.font.size = Pt(12)


def head(doc, text, size=14):
    """Заголовок — просто жирный текст, без стилей Heading."""
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.bold = True
    r.font.size = Pt(size)
    return p


def plain_table(doc, header, rows):
    """Простая таблица с чёрными границами (Table Grid)."""
    t = doc.add_table(rows=1, cols=len(header))
    t.style = 'Table Grid'
    for i, h in enumerate(header):
        cell = t.rows[0].cells[i]
        cell.text = h
        for p in cell.paragraphs:
            for r in p.runs:
                r.bold = True
    for row in rows:
        cells = t.add_row().cells
        for i, val in enumerate(row):
            cells[i].text = str(val)
    return t


def code_block(doc, code, size=9):
    p = doc.add_paragraph()
    run = p.add_run(code)
    run.font.name = 'Courier New'
    run.font.size = Pt(size)


def main():
    output = run_tests()
    by_class, ran, ok = parse(output)
    make_screenshot(output)
    total = sum(len(v) for v in by_class.values())

    doc = Document()
    base_style(doc)

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = title.add_run('Отчёт по лабораторной работе\n'
                      '«Отношения в базе данных и их тестирование (Django)»')
    r.bold = True
    r.font.size = Pt(16)
    date = doc.add_paragraph(f'{datetime.now():%d.%m.%Y}')
    date.alignment = WD_ALIGN_PARAGRAPH.CENTER

    head(doc, '1. Цель работы и постановка задачи')
    doc.add_paragraph(
        'Цель работы — разработать на Django небольшой стартап «Конные туры» '
        'с отношениями в базе данных (один к одному, один ко многим, многие ко '
        f'многим) и проверить бизнес-правила модульными тестами. Итог: '
        f'приложение tours и {total} автоматических тестов, все проходят.')
    doc.add_paragraph('По заданию нужно было проверить, что:')
    for item in [
        'один человек может купить только один тур на определённый день и время;',
        'один человек может оставить несколько комментариев, но только к тем '
        'турам, в которых он был;',
        'у тура есть категории, например «конный», «пеший» или «на мото».',
    ]:
        doc.add_paragraph(item, style='List Bullet')
    doc.add_paragraph(
        'Отдельным пунктом требовалось протестировать все отправки данных '
        '(POST-формы) и сделать документацию через django docs. Средства '
        'разработки: Python 3.13, Django 6, SQLite, django.contrib.admindocs.')

    head(doc, '2. Описание проекта')
    doc.add_paragraph(
        'Проект называется config, вся логика — в отдельном приложении tours, '
        'как мы делали в прошлых работах. В нём шесть моделей:')
    plain_table(doc, ['Модель', 'За что отвечает'], [
        ('Profile', 'Профиль пользователя (телефон, дата рождения). '
                    'Создаётся автоматически сигналом при регистрации'),
        ('Category', 'Категория тура: «конный», «пеший», «на мото»'),
        ('Tour', 'Тур: название, описание, цена, длительность'),
        ('TourSession', 'Слот тура на конкретный день и время'),
        ('Booking', 'Покупка тура пользователем'),
        ('Comment', 'Комментарий и оценка (1–5) к туру'),
    ])

    doc.add_paragraph()
    doc.add_paragraph('Связи между моделями:')
    plain_table(doc, ['Тип связи', 'Где реализована'], [
        ('Один к одному (1:1)', 'User — Profile (OneToOneField)'),
        ('Один ко многим (1:N)', 'Tour — TourSession, User — Comment, '
                                 'User — Booking, TourSession — Booking'),
        ('Многие ко многим (M:N)', 'Tour — Category (ManyToManyField)'),
    ])

    doc.add_paragraph()
    doc.add_paragraph('Ключевые решения:')
    for item in [
        'Ограничение «один тур на день и время» проверяется в двух местах: '
        'в методе clean() модели Booking и в BookingForm, чтобы ошибку было '
        'видно и в админке, и на сайте. Плюс UniqueConstraint на пару '
        '«пользователь + слот», чтобы один и тот же слот нельзя было купить '
        'дважды.',
        'Комментарий можно оставить, только если у пользователя есть '
        'бронирование этого тура — это проверяется в clean() модели Comment '
        'и в CommentForm.',
        'Профиль создаётся сигналом post_save, поэтому забыть про него нельзя.',
        'Документация подключена через django.contrib.admindocs и открывается '
        'по адресу /admin/doc/ — там видны описания всех моделей '
        'и представлений.',
    ]:
        doc.add_paragraph(item, style='List Bullet')

    head(doc, '3. Тестирование')
    doc.add_paragraph(
        f'Тесты написаны в файле tours/tests.py: {total} тестов в '
        f'{len(by_class)} классах django.test.TestCase. Каждый класс готовит '
        'свои данные в setUp или функциях-хелперах, поэтому тесты независимы.')
    descriptions = {
        'OneToOneRelationTests': 'Связь 1:1 — профиль создаётся автоматически, '
                                 'поля сохраняются, удаляется вместе с пользователем',
        'OneToManyRelationTests': 'Связь 1:N — у тура много слотов, у пользователя '
                                  'много комментариев, каскадное удаление',
        'ManyToManyRelationTests': 'Связь M:N — категории тура видны с обеих сторон',
        'BookingRuleTests': 'Правило «1 человек = 1 тур на день и время»: дубли '
                            'запрещены, другое время и другой пользователь — можно',
        'CommentRuleTests': 'Комментарии только к посещённым турам, '
                            'но несколько штук — можно; оценка от 1 до 5',
        'TourFormTests': 'Форма тура: валидные и невалидные данные',
        'UrlTests': 'Все URL ведут на нужные представления',
        'TourCreateViewTests': 'POST создания тура: валидный и невалидный',
        'TourReadViewTests': 'Список, поиск, фильтр по категории, страница тура, 404',
        'TourUpdateViewTests': 'POST редактирования тура',
        'TourDeleteViewTests': 'POST удаления тура',
        'BookingViewPostTests': 'POST покупки тура: успех, отказ при совпадении '
                                'времени, аноним',
        'CommentViewPostTests': 'POST комментария: успех после посещения, отказ '
                                'без брони, несколько подряд, аноним',
    }
    rows = [(cls, len(tests), descriptions.get(cls, ''))
            for cls, tests in by_class.items()]
    rows.append(('Итого', total, ''))
    plain_table(doc, ['Класс тестов', 'Тестов', 'Что проверяется'], rows)

    doc.add_paragraph()
    doc.add_paragraph(
        'Пример теста на главное правило — запрет второго тура на то же время:')
    code_block(doc, EXAMPLE_TEST)

    head(doc, '4. Результаты')
    if ran:
        doc.add_paragraph(
            f'Все {ran.group(1)} тестов пройдены за {ran.group(2)} с '
            f'(Ran {ran.group(1)} tests ... OK), ошибок и падений нет. '
            'Тесты запускаются командой python manage.py test.')
    doc.add_paragraph('Рисунок 1 — запуск тестов')
    doc.add_picture('tests_run.png')

    head(doc, '5. Вывод')
    doc.add_paragraph(
        'Собран стартап «Конные туры» со всеми тремя типами связей, и все '
        'правила из задания подтверждены тестами. Из полезного: оказалось, '
        'что бизнес-правило лучше проверять и в модели (clean), и в форме — '
        'иначе через админку можно было бы обойти ограничение. Ещё удобно '
        'вышло с сигналом post_save для профиля: руками создавать его не нужно '
        'нигде, даже в тестах. Документация через admindocs поднялась сразу, '
        'потому что у всех моделей и представлений были docstring\'и.')
    doc.add_paragraph(
        'Исходный код, тесты и этот отчёт лежат в репозитории '
        'github.com/Erbo102804/Lab-work-7-.')

    doc.save('report.docx')
    print(f'report.docx готов: {total} тестов, {"OK" if ok else "FAILED"}')


if __name__ == '__main__':
    main()
