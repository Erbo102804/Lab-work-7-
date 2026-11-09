"""Записывает результаты тестов Django-проекта в файл Word (report.docx).

Запуск:  python make_report.py
"""
import re
import subprocess
import sys
from datetime import datetime

from docx import Document
from docx.shared import Pt


def run_tests():
    """Запускает тесты и возвращает полный вывод."""
    result = subprocess.run(
        [sys.executable, 'manage.py', 'test', '-v', '2'],
        capture_output=True, text=True)
    return result.stderr + result.stdout  # django пишет отчёт тестов в stderr


def parse_results(output):
    """Разбирает вывод: список (тест, статус) + итоговые строки."""
    raw = re.findall(
        r'^(test_\w+) \(([\w.]+)\)\n?.* \.\.\. (ok|FAIL|ERROR)$', output, re.M)
    tests = [(name, path.split('.')[-2], status) for name, path, status in raw]
    ran = re.search(r'Ran (\d+) tests? in ([\d.]+)s', output)
    ok = 'OK' in output
    return tests, ran, ok


def main():
    output = run_tests()
    tests, ran, ok = parse_results(output)

    doc = Document()
    doc.add_heading('Отчёт о тестировании — стартап «Конные туры»', 0)
    doc.add_paragraph(f'Дата: {datetime.now():%d.%m.%Y %H:%M}')
    doc.add_paragraph('Проект: Django, приложение tours (отношения в БД: 1:1, 1:N, M:N)')

    if ran:
        doc.add_paragraph(
            f'Выполнено тестов: {ran.group(1)} за {ran.group(2)} с. '
            f'Результат: {"OK — все тесты пройдены" if ok else "ЕСТЬ ОШИБКИ"}.')

    doc.add_heading('Результаты по каждому тесту', level=1)
    table = doc.add_table(rows=1, cols=3)
    table.style = 'Light Grid Accent 1'
    hdr = table.rows[0].cells
    hdr[0].text, hdr[1].text, hdr[2].text = 'Тест', 'Класс', 'Статус'
    for name, cls, status in tests:
        row = table.add_row().cells
        row[0].text, row[1].text, row[2].text = name, cls, status

    doc.add_heading('Полный вывод', level=1)
    p = doc.add_paragraph()
    run = p.add_run(output.strip())
    run.font.size = Pt(8)
    run.font.name = 'Courier New'

    doc.save('report.docx')
    print(f'report.docx записан: {len(tests)} тестов, '
          f'{"OK" if ok else "FAILED"}')


if __name__ == '__main__':
    main()
