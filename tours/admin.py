from django.contrib import admin

from .models import Booking, Category, Comment, Profile, Tour, TourSession


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'birth_date')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)


class TourSessionInline(admin.TabularInline):
    model = TourSession
    extra = 1


@admin.register(Tour)
class TourAdmin(admin.ModelAdmin):
    list_display = ('title', 'price', 'duration_hours')
    filter_horizontal = ('categories',)
    inlines = [TourSessionInline]


@admin.register(TourSession)
class TourSessionAdmin(admin.ModelAdmin):
    list_display = ('tour', 'date', 'time', 'max_participants')


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('user', 'session', 'created_at')


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'tour', 'rating', 'created_at')
