from django.contrib import admin
from .models import Todo, Category, UserProfile


@admin.register(Todo)
class TodoAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'priority', 'is_completed', 'due_date', 'created_at']
    list_filter = ['is_completed', 'priority', 'category']
    search_fields = ['title', 'user__username']
    list_editable = ['is_completed']


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'color', 'created_at']
    search_fields = ['name', 'user__username']


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'avatar_color']
