"""Тесты приложения tours.

Покрывают:
- связи БД: 1:1 (User-Profile), 1:N (Tour-Session, User-Comment), M:N (Tour-Category);
- бизнес-правила: 1 человек = 1 тур на день и время; комментарии только
  к посещённым турам, но в любом количестве;
- все POST-отправки данных: создание/редактирование/удаление тура,
  покупка тура, добавление комментария.
"""
import datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import resolve, reverse

from . import views
from .forms import BookingForm, CommentForm, TourForm
from .models import Booking, Category, Comment, Profile, Tour, TourSession

DAY = datetime.date(2026, 12, 1)
TIME = datetime.time(10, 0)


def make_user(username='ivan'):
    return User.objects.create_user(username=username, password='pass12345')


def make_category(name='конный'):
    return Category.objects.create(name=name)


def make_tour(title='Конный тур по горам', **kw):
    data = dict(title=title, description='Тестовый тур',
                price=Decimal('1500.00'), duration_hours=3)
    data.update(kw)
    return Tour.objects.create(**data)


def make_session(tour, date=DAY, time=TIME):
    return TourSession.objects.create(tour=tour, date=date, time=time)


def make_booking(user, session):
    return Booking.objects.create(user=user, session=session)


# ------------------------------------------------------------ Связь 1:1
class OneToOneRelationTests(TestCase):
    def test_profile_created_automatically(self):
        """При создании пользователя профиль создаётся автоматически (1:1)"""
        u = make_user()
        self.assertIsInstance(u.profile, Profile)

    def test_one_user_has_only_one_profile(self):
        """У пользователя ровно один профиль"""
        u = make_user()
        self.assertEqual(Profile.objects.filter(user=u).count(), 1)

    def test_profile_fields_saved(self):
        """Поля профиля (телефон, дата рождения) сохраняются"""
        u = make_user()
        u.profile.phone = '+996700123456'
        u.profile.birth_date = datetime.date(2000, 1, 1)
        u.profile.save()
        self.assertEqual(User.objects.get(pk=u.pk).profile.phone, '+996700123456')

    def test_profile_deleted_with_user(self):
        """При удалении пользователя профиль удаляется каскадно"""
        u = make_user()
        u.delete()
        self.assertEqual(Profile.objects.count(), 0)


# ------------------------------------------------------------ Связь 1:N
class OneToManyRelationTests(TestCase):
    def setUp(self):
        self.tour = make_tour()
        self.user = make_user()

    def test_tour_has_many_sessions(self):
        """У тура может быть несколько слотов (дни и время)"""
        s1 = make_session(self.tour, DAY, TIME)
        s2 = make_session(self.tour, DAY, datetime.time(14, 0))
        self.assertEqual(list(self.tour.sessions.all()), [s1, s2])

    def test_session_belongs_to_tour(self):
        """Слот ссылается на свой тур"""
        s = make_session(self.tour)
        self.assertEqual(s.tour, self.tour)

    def test_duplicate_slot_forbidden(self):
        """Один и тот же слот (тур+дата+время) нельзя создать дважды"""
        make_session(self.tour, DAY, TIME)
        with self.assertRaises(Exception):
            make_session(self.tour, DAY, TIME)

    def test_sessions_deleted_with_tour(self):
        """При удалении тура слоты удаляются каскадно"""
        make_session(self.tour)
        self.tour.delete()
        self.assertEqual(TourSession.objects.count(), 0)

    def test_user_has_many_comments(self):
        """Пользователь может оставить несколько комментариев (1:N)"""
        s = make_session(self.tour)
        make_booking(self.user, s)
        c1 = Comment.objects.create(user=self.user, tour=self.tour, text='Первый')
        c2 = Comment.objects.create(user=self.user, tour=self.tour, text='Второй')
        self.assertEqual(self.user.comments.count(), 2)
        self.assertEqual(list(self.tour.comments.all()), [c2, c1])


# ------------------------------------------------------------ Связь M:N
class ManyToManyRelationTests(TestCase):
    def test_tour_has_categories(self):
        """У тура есть категории: «конный», «пеший», «на мото»"""
        horse = make_category('конный')
        walk = make_category('пеший')
        moto = make_category('на мото')
        tour = make_tour()
        tour.categories.set([horse, walk])
        self.assertEqual(list(tour.categories.all()), [horse, walk])
        self.assertIn(moto, Category.objects.all())

    def test_category_reverse_relation(self):
        """Со стороны категории видны все её туры"""
        horse = make_category('конный')
        t1, t2 = make_tour('Тур 1'), make_tour('Тур 2')
        t1.categories.add(horse)
        t2.categories.add(horse)
        self.assertEqual(set(horse.tours.all()), {t1, t2})

    def test_remove_category_keeps_tour(self):
        """Удаление связи не удаляет сам тур"""
        horse = make_category()
        tour = make_tour()
        tour.categories.add(horse)
        tour.categories.remove(horse)
        self.assertTrue(Tour.objects.filter(pk=tour.pk).exists())


# ------------------------------------------- Правило: 1 тур на день и время
class BookingRuleTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.tour1 = make_tour('Конный тур')
        self.tour2 = make_tour('Пеший тур')
        self.s1 = make_session(self.tour1, DAY, TIME)
        self.s2 = make_session(self.tour2, DAY, TIME)

    def test_user_can_buy_one_tour(self):
        """Пользователь может купить тур на свободные день и время"""
        b = make_booking(self.user, self.s1)
        b.full_clean()
        self.assertEqual(Booking.objects.count(), 1)

    def test_cannot_buy_two_tours_same_datetime(self):
        """Нельзя купить 2 тура на один и тот же день и время (clean)"""
        make_booking(self.user, self.s1)
        b = Booking(user=self.user, session=self.s2)
        with self.assertRaises(ValidationError):
            b.full_clean()

    def test_cannot_buy_same_session_twice(self):
        """Нельзя купить один и тот же слот дважды"""
        make_booking(self.user, self.s1)
        with self.assertRaises(Exception):
            make_booking(self.user, self.s1)

    def test_can_buy_tour_other_time(self):
        """Можно купить другой тур в другое время"""
        make_booking(self.user, self.s1)
        s_late = make_session(self.tour2, DAY, datetime.time(16, 0))
        b = Booking(user=self.user, session=s_late)
        b.full_clean()
        b.save()
        self.assertEqual(Booking.objects.count(), 2)

    def test_other_user_can_buy_same_session(self):
        """Тот же слот может купить другой пользователь"""
        make_booking(self.user, self.s1)
        other = make_user('maria')
        b = Booking(user=other, session=self.s1)
        b.full_clean()
        b.save()
        self.assertEqual(Booking.objects.count(), 2)

    def test_booking_form_rejects_same_datetime(self):
        """Форма покупки отклоняет второй тур на то же время"""
        make_booking(self.user, self.s1)
        form = BookingForm({'session': self.s2.pk}, user=self.user)
        self.assertFalse(form.is_valid())

    def test_booking_form_valid_for_free_time(self):
        """Форма покупки принимает свободное время"""
        form = BookingForm({'session': self.s1.pk}, user=self.user)
        self.assertTrue(form.is_valid())


# --------------------------------------- Правило: комментарии только «своим»
class CommentRuleTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.tour = make_tour()
        self.session = make_session(self.tour)

    def test_cannot_comment_unattended_tour(self):
        """Нельзя комментировать тур, в котором не был (clean)"""
        c = Comment(user=self.user, tour=self.tour, text='Привет')
        with self.assertRaises(ValidationError):
            c.full_clean()

    def test_can_comment_attended_tour(self):
        """Можно комментировать тур после покупки"""
        make_booking(self.user, self.session)
        c = Comment(user=self.user, tour=self.tour, text='Отлично!')
        c.full_clean()
        c.save()
        self.assertEqual(Comment.objects.count(), 1)

    def test_several_comments_allowed(self):
        """Один человек может оставить несколько комментариев"""
        make_booking(self.user, self.session)
        for i in range(3):
            c = Comment(user=self.user, tour=self.tour, text=f'Отзыв {i}')
            c.full_clean()
            c.save()
        self.assertEqual(Comment.objects.filter(user=self.user).count(), 3)

    def test_comment_form_rejects_unattended(self):
        """Форма комментария отклоняет непосещённый тур"""
        form = CommentForm({'text': 'Привет', 'rating': 5},
                           user=self.user, tour=self.tour)
        self.assertFalse(form.is_valid())

    def test_comment_rating_range(self):
        """Оценка комментария должна быть от 1 до 5"""
        make_booking(self.user, self.session)
        c = Comment(user=self.user, tour=self.tour, text='X', rating=9)
        with self.assertRaises(ValidationError):
            c.full_clean()


# ------------------------------------------------------------ Форма тура
class TourFormTests(TestCase):
    def setUp(self):
        self.cat = make_category()

    def test_valid_form(self):
        """Форма тура с корректными данными валидна"""
        f = TourForm({'title': 'A', 'description': '', 'price': '100',
                      'duration_hours': 2, 'categories': [self.cat.pk]})
        self.assertTrue(f.is_valid())

    def test_empty_form_invalid(self):
        """Пустая форма невалидна"""
        f = TourForm({})
        self.assertFalse(f.is_valid())
        self.assertIn('title', f.errors)
        self.assertIn('price', f.errors)

    def test_negative_price_invalid(self):
        """Отрицательная цена отклоняется формой"""
        f = TourForm({'title': 'A', 'price': '-10', 'duration_hours': 2,
                      'categories': [self.cat.pk]})
        self.assertFalse(f.is_valid())


# ------------------------------------------------------------ URL
class UrlTests(TestCase):
    def test_urls_resolve_to_views(self):
        """URL-адреса сопоставлены с нужными представлениями"""
        self.assertEqual(resolve('/').func.view_class, views.TourListView)
        self.assertEqual(resolve('/create/').func.view_class, views.TourCreateView)
        self.assertEqual(resolve('/1/').func.view_class, views.TourDetailView)
        self.assertEqual(resolve('/1/edit/').func.view_class, views.TourUpdateView)
        self.assertEqual(resolve('/1/delete/').func.view_class, views.TourDeleteView)
        self.assertEqual(resolve('/1/comment/').func.view_class,
                         views.CommentCreateView)
        self.assertEqual(resolve('/session/1/book/').func.view_class,
                         views.BookingCreateView)


# ------------------------------------------------------------ CRUD (POST)
class TourCreateViewTests(TestCase):
    def setUp(self):
        self.cat = make_category()

    def test_create_page_get(self):
        """GET /create/ отдаёт форму (200, нужный шаблон)"""
        r = self.client.get(reverse('tours:create'))
        self.assertEqual(r.status_code, 200)
        self.assertTemplateUsed(r, 'tours/tour_form.html')

    def test_create_post_valid(self):
        """POST с валидными данными создаёт тур и делает редирект"""
        r = self.client.post(reverse('tours:create'),
                             {'title': 'Новый тур', 'description': 'd',
                              'price': '900.00', 'duration_hours': 4,
                              'categories': [self.cat.pk]})
        t = Tour.objects.get(title='Новый тур')
        self.assertRedirects(r, t.get_absolute_url())
        self.assertEqual(list(t.categories.all()), [self.cat])

    def test_create_post_invalid(self):
        """POST с невалидными данными не создаёт тур"""
        r = self.client.post(reverse('tours:create'), {'title': '', 'price': ''})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Tour.objects.count(), 0)
        self.assertTrue(r.context['form'].errors)


class TourReadViewTests(TestCase):
    def setUp(self):
        self.tour = make_tour('Конный тур в ущелье')

    def test_list_status_and_template(self):
        """Список туров: код 200 и шаблон tour_list.html"""
        r = self.client.get(reverse('tours:list'))
        self.assertEqual(r.status_code, 200)
        self.assertTemplateUsed(r, 'tours/tour_list.html')

    def test_list_contains_tour(self):
        """Созданный тур виден в списке"""
        self.assertContains(self.client.get(reverse('tours:list')),
                            'Конный тур в ущелье')

    def test_list_empty_message(self):
        """При пустой базе выводится сообщение «Туров пока нет»"""
        Tour.objects.all().delete()
        self.assertContains(self.client.get(reverse('tours:list')),
                            'Туров пока нет')

    def test_list_search(self):
        """Поиск ?q= фильтрует туры по названию"""
        make_tour('Пеший поход')
        r = self.client.get(reverse('tours:list'), {'q': 'Пеший'})
        titles = [t.title for t in r.context['tours']]
        self.assertEqual(titles, ['Пеший поход'])

    def test_list_filter_by_category(self):
        """Фильтр ?category= показывает туры только этой категории"""
        horse = make_category('конный')
        self.tour.categories.add(horse)
        other = make_tour('Пеший поход')
        r = self.client.get(reverse('tours:list'), {'category': horse.pk})
        tours = list(r.context['tours'])
        self.assertEqual(tours, [self.tour])
        self.assertNotIn(other, tours)

    def test_detail_ok(self):
        """Страница тура: код 200, виден контекст tour"""
        r = self.client.get(self.tour.get_absolute_url())
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context['tour'], self.tour)

    def test_detail_404(self):
        """Несуществующий тур возвращает 404"""
        self.assertEqual(
            self.client.get(reverse('tours:detail', args=[9999])).status_code, 404)


class TourUpdateViewTests(TestCase):
    def setUp(self):
        self.cat = make_category()
        self.tour = make_tour('Старое название')
        self.url = reverse('tours:update', args=[self.tour.pk])

    def test_update_get_prefilled(self):
        """GET формы редактирования подставляет текущие данные"""
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context['form'].initial['title'], 'Старое название')

    def test_update_post_valid(self):
        """POST с новыми данными изменяет тур"""
        self.client.post(self.url, {'title': 'Новое название', 'description': '',
                                    'price': '100', 'duration_hours': 2,
                                    'categories': [self.cat.pk]})
        self.tour.refresh_from_db()
        self.assertEqual(self.tour.title, 'Новое название')

    def test_update_post_invalid(self):
        """POST с пустым названием не меняет тур"""
        self.client.post(self.url, {'title': '', 'price': '100',
                                    'duration_hours': 2,
                                    'categories': [self.cat.pk]})
        self.tour.refresh_from_db()
        self.assertEqual(self.tour.title, 'Старое название')

    def test_update_404(self):
        """Редактирование несуществующего тура даёт 404"""
        self.assertEqual(
            self.client.get(reverse('tours:update', args=[9999])).status_code, 404)


class TourDeleteViewTests(TestCase):
    def setUp(self):
        self.tour = make_tour()
        self.url = reverse('tours:delete', args=[self.tour.pk])

    def test_delete_confirm_page(self):
        """GET показывает страницу подтверждения, тур не удаляется"""
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertTemplateUsed(r, 'tours/tour_confirm_delete.html')
        self.assertEqual(Tour.objects.count(), 1)

    def test_delete_post(self):
        """POST удаляет тур и перенаправляет на список"""
        r = self.client.post(self.url)
        self.assertRedirects(r, reverse('tours:list'))
        self.assertFalse(Tour.objects.exists())

    def test_delete_404(self):
        """Удаление несуществующего тура даёт 404"""
        self.assertEqual(
            self.client.post(reverse('tours:delete', args=[9999])).status_code, 404)


# ------------------------------------------------ POST: покупка и комментарии
class BookingViewPostTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.tour = make_tour()
        self.s1 = make_session(self.tour, DAY, TIME)
        self.url = reverse('tours:book', args=[self.s1.pk])
        self.client.force_login(self.user)

    def test_booking_page_get(self):
        """GET страницы покупки: 200 и форма"""
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertTemplateUsed(r, 'tours/booking_form.html')

    def test_booking_post_valid(self):
        """POST покупки создаёт бронирование и редиректит на тур"""
        r = self.client.post(self.url, {'session': self.s1.pk})
        self.assertRedirects(r, self.tour.get_absolute_url())
        self.assertEqual(Booking.objects.get().user, self.user)
        self.assertEqual(Booking.objects.get().session, self.s1)

    def test_booking_post_same_datetime_rejected(self):
        """POST второго тура на то же время: ошибка, бронирование не создаётся"""
        other_tour = make_tour('Другой тур')
        s2 = make_session(other_tour, DAY, TIME)
        make_booking(self.user, self.s1)
        r = self.client.post(reverse('tours:book', args=[s2.pk]),
                             {'session': s2.pk})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.context['form'].errors)
        self.assertEqual(Booking.objects.count(), 1)

    def test_booking_post_anonymous_redirects(self):
        """Анонимный POST покупки перенаправляет на вход"""
        self.client.logout()
        r = self.client.post(self.url, {'session': self.s1.pk})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Booking.objects.count(), 0)


class CommentViewPostTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.tour = make_tour()
        self.session = make_session(self.tour)
        self.url = reverse('tours:comment', args=[self.tour.pk])
        self.client.force_login(self.user)

    def test_comment_page_get(self):
        """GET страницы комментария: 200 и форма"""
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertTemplateUsed(r, 'tours/comment_form.html')

    def test_comment_post_attended(self):
        """POST комментария к посещённому туру сохраняется"""
        make_booking(self.user, self.session)
        r = self.client.post(self.url, {'text': 'Супер тур!', 'rating': 5})
        self.assertRedirects(r, self.tour.get_absolute_url())
        c = Comment.objects.get()
        self.assertEqual(c.user, self.user)
        self.assertEqual(c.tour, self.tour)

    def test_comment_post_several_allowed(self):
        """Несколько POST-комментариев от одного человека сохраняются"""
        make_booking(self.user, self.session)
        self.client.post(self.url, {'text': 'Первый', 'rating': 5})
        self.client.post(self.url, {'text': 'Второй', 'rating': 4})
        self.assertEqual(Comment.objects.filter(user=self.user).count(), 2)

    def test_comment_post_unattended_rejected(self):
        """POST комментария к непосещённому туру отклоняется"""
        r = self.client.post(self.url, {'text': 'Не был там', 'rating': 5})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.context['form'].errors)
        self.assertEqual(Comment.objects.count(), 0)

    def test_comment_post_anonymous_redirects(self):
        """Анонимный POST комментария перенаправляет на вход"""
        self.client.logout()
        r = self.client.post(self.url, {'text': 'Привет', 'rating': 5})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Comment.objects.count(), 0)
