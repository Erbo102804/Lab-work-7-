"""Представления приложения tours.

CRUD для туров + отправка данных: покупка тура (Booking) и комментарии (Comment).
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import (CreateView, DeleteView, DetailView, ListView,
                                  UpdateView)

from .forms import BookingForm, CommentForm, TourForm
from .models import Booking, Comment, Tour, TourSession


class TourListView(ListView):
    """Список туров с поиском (?q=) и фильтром по категории (?category=)."""

    model = Tour
    context_object_name = 'tours'

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(title__icontains=q)
        category = self.request.GET.get('category')
        if category:
            qs = qs.filter(categories__pk=category)
        return qs.distinct()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from .models import Category
        ctx['categories'] = Category.objects.all()
        return ctx


class TourDetailView(DetailView):
    """Страница тура: слоты (1:N), категории (M:N) и комментарии."""

    model = Tour
    context_object_name = 'tour'


class TourCreateView(CreateView):
    """Создание тура (POST-отправка формы)."""

    model = Tour
    form_class = TourForm


class TourUpdateView(UpdateView):
    """Редактирование тура (POST-отправка формы)."""

    model = Tour
    form_class = TourForm


class TourDeleteView(DeleteView):
    """Удаление тура (POST-подтверждение)."""

    model = Tour
    success_url = reverse_lazy('tours:list')


class BookingCreateView(LoginRequiredMixin, CreateView):
    """Покупка тура: POST с выбранным слотом.

    Правило «1 человек = 1 тур на день и время» проверяется в BookingForm.
    """

    model = Booking
    form_class = BookingForm
    template_name = 'tours/booking_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.session = get_object_or_404(TourSession, pk=kwargs['pk'])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        kwargs.setdefault('initial', {})['session'] = self.session
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['session'] = self.session
        return ctx

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return self.session.tour.get_absolute_url()


class CommentCreateView(LoginRequiredMixin, CreateView):
    """Добавление комментария к туру (POST).

    Доступно только если у пользователя есть бронирование этого тура.
    """

    model = Comment
    form_class = CommentForm
    template_name = 'tours/comment_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.tour = get_object_or_404(Tour, pk=kwargs['pk'])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        kwargs['tour'] = self.tour
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['tour'] = self.tour
        return ctx

    def form_valid(self, form):
        form.instance.user = self.request.user
        form.instance.tour = self.tour
        return super().form_valid(form)

    def get_success_url(self):
        return self.tour.get_absolute_url()
