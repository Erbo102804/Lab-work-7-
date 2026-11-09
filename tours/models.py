"""Модели стартапа «Конные туры».

Связи в базе данных:
- один к одному (1:1)      — User <-> Profile;
- один ко многим (1:N)     — Tour -> TourSession, User -> Comment, Tour -> Comment,
                             User -> Booking, TourSession -> Booking;
- многие ко многим (M:N)   — Tour <-> Category («конный», «пеший», «на мото»).
"""
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse


class Profile(models.Model):
    """Профиль пользователя — связь один к одному (1:1) с User."""

    user = models.OneToOneField(User, on_delete=models.CASCADE,
                                related_name='profile', verbose_name='Пользователь')
    phone = models.CharField('Телефон', max_length=20, blank=True)
    birth_date = models.DateField('Дата рождения', null=True, blank=True)

    class Meta:
        verbose_name = 'Профиль'
        verbose_name_plural = 'Профили'

    def __str__(self):
        return f'Профиль {self.user.username}'


class Category(models.Model):
    """Категория тура: «конный», «пеший», «на мото» и т.д. — связь M:N с Tour."""

    name = models.CharField('Название', max_length=50, unique=True)
    description = models.TextField('Описание', blank=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'

    def __str__(self):
        return self.name


class Tour(models.Model):
    """Тур. Категории — связь многие ко многим (M:N)."""

    title = models.CharField('Название', max_length=100)
    description = models.TextField('Описание', blank=True)
    price = models.DecimalField('Цена', max_digits=10, decimal_places=2,
                                validators=[MinValueValidator(0)])
    duration_hours = models.PositiveIntegerField('Длительность (ч)', default=3)
    categories = models.ManyToManyField(Category, related_name='tours',
                                        verbose_name='Категории')
    created_at = models.DateTimeField('Создан', auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']
        verbose_name = 'Тур'
        verbose_name_plural = 'Туры'

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('tours:detail', args=[self.pk])


class TourSession(models.Model):
    """Слот тура на конкретный день и время — связь один ко многим (1:N) с Tour."""

    tour = models.ForeignKey(Tour, on_delete=models.CASCADE,
                             related_name='sessions', verbose_name='Тур')
    date = models.DateField('Дата')
    time = models.TimeField('Время')
    max_participants = models.PositiveIntegerField('Макс. участников', default=10)

    class Meta:
        ordering = ['date', 'time']
        verbose_name = 'Слот тура'
        verbose_name_plural = 'Слоты туров'
        constraints = [
            models.UniqueConstraint(fields=['tour', 'date', 'time'],
                                    name='unique_tour_session'),
        ]

    def __str__(self):
        return f'{self.tour} — {self.date} {self.time:%H:%M}'


class Booking(models.Model):
    """Покупка тура пользователем.

    Правило: 1 человек может купить только 1 тур на определённый день и время.
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE,
                             related_name='bookings', verbose_name='Пользователь')
    session = models.ForeignKey(TourSession, on_delete=models.CASCADE,
                                related_name='bookings', verbose_name='Слот')
    created_at = models.DateTimeField('Куплено', auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']
        verbose_name = 'Бронирование'
        verbose_name_plural = 'Бронирования'
        constraints = [
            models.UniqueConstraint(fields=['user', 'session'],
                                    name='unique_user_session_booking'),
        ]

    def clean(self):
        """Запрещаем второй тур на тот же день и время."""
        super().clean()
        if self.user_id and self.session_id:
            clash = Booking.objects.filter(
                user_id=self.user_id,
                session__date=self.session.date,
                session__time=self.session.time,
            ).exclude(pk=self.pk)
            if clash.exists():
                raise ValidationError(
                    'Нельзя купить два тура на один и тот же день и время.')

    def __str__(self):
        return f'{self.user} → {self.session}'


class Comment(models.Model):
    """Комментарий к туру.

    1 человек может оставить несколько комментариев,
    но только к тем турам, в которых он был (есть бронирование).
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE,
                             related_name='comments', verbose_name='Пользователь')
    tour = models.ForeignKey(Tour, on_delete=models.CASCADE,
                             related_name='comments', verbose_name='Тур')
    text = models.TextField('Текст')
    rating = models.PositiveSmallIntegerField(
        'Оценка', default=5,
        validators=[MinValueValidator(1), MaxValueValidator(5)])
    created_at = models.DateTimeField('Создан', auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']
        verbose_name = 'Комментарий'
        verbose_name_plural = 'Комментарии'

    def clean(self):
        """Комментировать можно только туры, в которых пользователь был."""
        super().clean()
        if self.user_id and self.tour_id:
            attended = Booking.objects.filter(
                user_id=self.user_id, session__tour_id=self.tour_id).exists()
            if not attended:
                raise ValidationError(
                    'Комментировать можно только туры, в которых вы были.')

    def __str__(self):
        return f'{self.user} о «{self.tour}»: {self.text[:30]}'
