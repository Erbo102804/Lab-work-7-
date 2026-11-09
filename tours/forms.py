"""Формы приложения tours."""
from django import forms
from django.core.exceptions import ValidationError

from .models import Booking, Comment, Tour


class TourForm(forms.ModelForm):
    """Форма создания/редактирования тура (с выбором категорий M:N)."""

    class Meta:
        model = Tour
        fields = ['title', 'description', 'price', 'duration_hours', 'categories']
        widgets = {
            'categories': forms.CheckboxSelectMultiple,
        }


class BookingForm(forms.ModelForm):
    """Форма покупки тура.

    Проверяет правило: 1 человек — только 1 тур на определённый день и время.
    """

    class Meta:
        model = Booking
        fields = ['session']

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        session = cleaned.get('session')
        if self.user is not None and session is not None:
            clash = Booking.objects.filter(
                user=self.user,
                session__date=session.date,
                session__time=session.time,
            ).exists()
            if clash:
                raise ValidationError(
                    'Нельзя купить два тура на один и тот же день и время.')
        return cleaned


class CommentForm(forms.ModelForm):
    """Форма комментария: только к турам, в которых пользователь был."""

    class Meta:
        model = Comment
        fields = ['text', 'rating']

    def __init__(self, *args, user=None, tour=None, **kwargs):
        self.user = user
        self.tour = tour
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        if self.user is not None and self.tour is not None:
            attended = Booking.objects.filter(
                user=self.user, session__tour=self.tour).exists()
            if not attended:
                raise ValidationError(
                    'Комментировать можно только туры, в которых вы были.')
        return cleaned
