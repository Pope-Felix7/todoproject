from django.contrib import admin
from django.urls import path
from todos import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('todo/add/', views.add_todo, name='add_todo'),
    path('todo/<int:pk>/edit/', views.edit_todo, name='edit_todo'),
    path('todo/<int:pk>/delete/', views.delete_todo, name='delete_todo'),
    path('todo/<int:pk>/toggle/', views.toggle_todo, name='toggle_todo'),
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('profile/change-password/', views.change_password, name='change_password'),
    path('api/upcoming-deadlines/', views.api_upcoming_deadlines, name='api_upcoming_deadlines'),
]
