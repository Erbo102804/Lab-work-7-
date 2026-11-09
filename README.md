# Django: отношения в БД + тесты

Стартап «Конные туры» (приложение `tours`, startapp).

Связи в базе данных:
- **1 к 1** — `User` ↔ `Profile`;
- **1 ко многим** — `Tour` → `TourSession`, `User` → `Comment`, `Tour` → `Comment`, `User` → `Booking`, `TourSession` → `Booking`;
- **многие ко многим** — `Tour` ↔ `Category` («конный», «пеший», «на мото»).

Проверяемые правила:
- 1 человек может купить только 1 тур на определённый день и время;
- 1 человек может оставить несколько комментариев, но только к турам, в которых был.

Документация — через django docs (`django.contrib.admindocs`): `/admin/doc/`.

    pip install -r requirements.txt
    python manage.py migrate
    python manage.py runserver
    python manage.py test            # запуск тестов
    python manage.py test -v 2       # подробный вывод
    python make_report.py            # записать результаты тестов в report.docx
# Lab-work-7-
