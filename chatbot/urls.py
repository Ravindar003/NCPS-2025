from django.urls import path
from . import views

app_name = 'chatbot'

urlpatterns = [
    path('api/message/', views.chatbot_message, name='message'),
    path('api/init/', views.chatbot_init, name='init'),
]
