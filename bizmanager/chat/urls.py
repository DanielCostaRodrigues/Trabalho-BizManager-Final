from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('', views.index, name='index'),
    path('room/<str:room_name>/', views.room, name='room'),
    path('start/<str:username>/', views.start_chat, name='start_chat'),
    path('contacts/', views.contacts, name='contacts'),
    path('unread-count/', views.unread_count, name='unread_count'),
]