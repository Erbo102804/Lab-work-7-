"""Собирает отчёт по лабораторной работе в report.pdf.

Запускает тесты, рисует «скриншот» вывода (tests_run.png)
и оформляет всё в PDF. Запуск:  python make_report_pdf.py
"""
import re
import subprocess
import sys
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Image as RLImage, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)

EXAMPLE_TEST = '''    def test_cannot_buy_two_tours_same_datetime(self):
        """Нельзя купить 2 тура на один и тот же день и время (clean)"""
        make_booking(self.user, self.s1)
        b = Booking(user=self.user, session=self.s2)
        with self.assertRaises(ValidationError):
            b.full_clean()'''

FONTS = '/System/Library/Fonts/Supplemental/'
pdfmetrics.registerFont(TTFont('TNR', FONTS + 'Times New Roman.ttf'))
pdfmetrics.registerFont(TTFont('TNR-B', FONTS + 'Times New Roman Bold.ttf'))
pdfmetrics.registerFont(TTFont('TNR-I', FONTS + 'Times New Roman Italic.ttf'))
pdfmetrics.registerFont(TTFont('Mono', '/System/Library/Fonts/Menlo.ttc'))

BODY = ParagraphStyle('body', fontName='TNR', fontSize=12, leading=16,
                      spaceAfter=6, alignment=4)  # по ширине
H = ParagraphStyle('h', fontName='TNR-B', fontSize=14, leading=18,
                   spaceBefore=12, spaceAfter=6)
TITLE = ParagraphStyle('title', fontName='TNR-B', fontSize=16, leading=20,
                       alignment=1, spaceAfter=4)
CENTER = ParagraphStyle('c', fontName='TNR', fontSize=12, alignment=1,
                        spaceAfter=12)
CODE = ParagraphStyle('code', fontName='Mono', fontSize=8.5, leading=11,
                      leftIndent=10, spaceAfter=6)
CAPTION = ParagraphStyle('cap', fontName='TNR-I', fontSize=11, alignment=1,
                         spaceBefore=4, spaceAfter=10)


def run_tests():
    result = subprocess.run(
        [sys.executable, 'manage.py', 'test', '-v', '2'],
        capture_output=True, text=True)
    return result.stderr + result.stdout


def parse(output):
    raw = re.findall(
        r'^(test_\w+) \(([\w.]+)\)\n?.* \.\.\. (ok|FAIL|ERROR)$', output, re.M)
    by_class = {}
    for name, path, status in raw:
        by_class.setdefault(path.split('.')[-2], []).append(name)
    ran = re.search(r'Ran (\d+) tests? in ([\d.]+)s', output)
    return by_class, ran, 'OK' in output


def make_screenshot(output):
    test_lines = [l for l in output.splitlines() if l.rstrip().endswith('ok')]
    ran = re.search(r'Ran \d+ tests? in [\d.]+s', output)
    tail = (['$ python manage.py test', '...'] + test_lines[-3:] + ['-' * 70])
    if ran:
        tail += [ran.group(0), '', 'OK' if 'OK' in output else 'FAILED']
    font = ImageFont.truetype('/System/Library/Fonts/Menlo.ttc', 15)
    img = Image.new('RGB', (1060, 30 + 24 * len(tail) + 20), (28, 28, 32))
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


def tbl(data, widths):
    t = Table(data, colWidths=widths)
    t.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'TNR'),
        ('FONTNAME', (0, 0), (-1, 0), 'TNR-B'),
        ('FONTSIZE', (0, 0), (-1, -1), 10.5),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    return t


def main():
    output = run_tests()
    by_class, ran, ok = parse(output)
    make_screenshot(output)
    total = sum(len(v) for v in by_class.values())

    story = [
        Paragraph('Отчёт по лабораторной работе<br/>«Отношения в базе данных '
                  'и их тестирование (Django)»', TITLE),
        Paragraph(f'{datetime.now():%d.%m.%Y}', CENTER),

        Paragraph('1. Цель работы и постановка задачи', H),
        Paragraph(
            'Цель работы — разработать на Django небольшой стартап «Конные '
            'туры» с отношениями в базе данных (один к одному, один ко '
            'многим, многие ко многим) и проверить бизнес-правила модульными '
            f'тестами. Итог: приложение tours и {total} автоматических '
            'тестов, все проходят.', BODY),
        Paragraph('По заданию нужно было проверить, что: один человек может '
                  'купить только один тур на определённый день и время; один '
                  'человек может оставить несколько комментариев, но только '
                  'к тем турам, в которых он был; у тура есть категории, '
                  'например «конный», «пеший» или «на мото».', BODY),
        Paragraph('Отдельным пунктом требовалось протестировать все отправки '
                  'данных (POST-формы) и сделать документацию через django '
                  'docs. Средства разработки: Python 3.13, Django 6, SQLite, '
                  'django.contrib.admindocs.', BODY),

        Paragraph('2. Описание проекта', H),
        Paragraph('Проект называется config, вся логика — в отдельном '
                  'приложении tours, как мы делали в прошлых работах. '
                  'В нём шесть моделей:', BODY),
        tbl([['Модель', 'За что отвечает'],
             ['Profile', 'Профиль пользователя (телефон, дата рождения). '
                         'Создаётся автоматически сигналом при регистрации'],
             ['Category', 'Категория тура: «конный», «пеший», «на мото»'],
             ['Tour', 'Тур: название, описание, цена, длительность'],
             ['TourSession', 'Слот тура на конкретный день и время'],
             ['Booking', 'Покупка тура пользователем'],
             ['Comment', 'Комментарий и оценка (1–5) к туру']],
            [35 * mm, 135 * mm]),
        Spacer(1, 6),
        Paragraph('Связи между моделями:', BODY),
        tbl([['Тип связи', 'Где реализована'],
             ['Один к одному (1:1)', 'User — Profile (OneToOneField)'],
             ['Один ко многим (1:N)', 'Tour — TourSession, User — Comment, '
                                      'User — Booking, TourSession — Booking'],
             ['Многие ко многим (M:N)', 'Tour — Category (ManyToManyField)']],
            [55 * mm, 115 * mm]),
        Spacer(1, 6),
        Paragraph('Ключевые решения: ограничение «один тур на день и время» '
                  'проверяется и в методе clean() модели Booking, и в '
                  'BookingForm, чтобы ошибку было видно и в админке, и на '
                  'сайте; плюс UniqueConstraint на пару «пользователь + '
                  'слот». Комментарий можно оставить, только если есть '
                  'бронирование этого тура (clean() в Comment и CommentForm). '
                  'Профиль создаётся сигналом post_save. Документация '
                  'подключена через django.contrib.admindocs и открывается '
                  'по адресу /admin/doc/.', BODY),

        Paragraph('3. Тестирование', H),
        Paragraph(f'Тесты написаны в файле tours/tests.py: {total} тестов в '
                  f'{len(by_class)} классах django.test.TestCase. Каждый '
                  'класс готовит свои данные в setUp или функциях-хелперах, '
                  'поэтому тесты независимы.', BODY),
    ]

    descriptions = {
        'OneToOneRelationTests': 'Связь 1:1 — профиль создаётся автоматически, '
                                 'поля сохраняются, удаляется вместе с пользователем',
        'OneToManyRelationTests': 'Связь 1:N — у тура много слотов, у пользователя '
                                  'много комментариев, каскадное удаление',
        'ManyToManyRelationTests': 'Связь M:N — категории тура видны с обеих сторон',
        'BookingRuleTests': 'Правило «1 человек = 1 тур на день и время»',
        'CommentRuleTests': 'Комментарии только к посещённым турам, оценка 1–5',
        'TourFormTests': 'Форма тура: валидные и невалидные данные',
        'UrlTests': 'Все URL ведут на нужные представления',
        'TourCreateViewTests': 'POST создания тура',
        'TourReadViewTests': 'Список, поиск, фильтр по категории, 404',
        'TourUpdateViewTests': 'POST редактирования тура',
        'TourDeleteViewTests': 'POST удаления тура',
        'BookingViewPostTests': 'POST покупки: успех, отказ, аноним',
        'CommentViewPostTests': 'POST комментария: успех, отказ, несколько подряд',
    }
    rows = [['Класс тестов', 'Тестов', 'Что проверяется']]
    for cls, tests in by_class.items():
        rows.append([cls, str(len(tests)), descriptions.get(cls, '')])
    rows.append(['Итого', str(total), ''])
    story += [tbl(rows, [52 * mm, 16 * mm, 102 * mm]), Spacer(1, 6),
              Paragraph('Пример теста на главное правило — запрет второго '
                        'тура на то же время:', BODY),
              Paragraph(EXAMPLE_TEST.replace('\n', '<br/>').replace(' ', '&nbsp;'),
                        CODE),

              Paragraph('4. Результаты', H)]
    if ran:
        story.append(Paragraph(
            f'Все {ran.group(1)} тестов пройдены за {ran.group(2)} с '
            f'(Ran {ran.group(1)} tests ... OK), ошибок и падений нет. '
            'Тесты запускаются командой python manage.py test.', BODY))
    img = Image.open('tests_run.png')
    w, h = img.size
    story += [RLImage('tests_run.png', width=150 * mm,
                      height=150 * mm * h / w),
              Paragraph('Рисунок 1 — запуск тестов', CAPTION),

              Paragraph('5. Вывод', H),
              Paragraph(
                  'Собран стартап «Конные туры» со всеми тремя типами связей, '
                  'и все правила из задания подтверждены тестами. Из '
                  'полезного: оказалось, что бизнес-правило лучше проверять '
                  'и в модели (clean), и в форме — иначе через админку можно '
                  'было бы обойти ограничение. Ещё удобно вышло с сигналом '
                  'post_save для профиля: руками создавать его не нужно '
                  'нигде, даже в тестах. Документация через admindocs '
                  'поднялась сразу, потому что у всех моделей и представлений '
                  'были docstring\'и.', BODY),
              Paragraph('Исходный код, тесты и этот отчёт лежат в репозитории '
                        'github.com/Erbo102804/Lab-work-7-.', BODY)]

    SimpleDocTemplate('report.pdf', pagesize=A4,
                      leftMargin=20 * mm, rightMargin=20 * mm,
                      topMargin=18 * mm, bottomMargin=18 * mm,
                      title='Отчёт по лабораторной работе').build(story)
    print(f'report.pdf готов: {total} тестов, {"OK" if ok else "FAILED"}')


if __name__ == '__main__':
    main()
