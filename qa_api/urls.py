from django.urls import path
from . import views

urlpatterns = [
    path('query/', views.medical_qa, name='medical_qa'),
    path('history/', views.get_history, name='get_history'),
    path('clear_history/', views.clear_history, name='clear_history'),
] 