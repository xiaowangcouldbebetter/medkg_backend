from django.urls import path
from . import views
from . import performance_views

urlpatterns = [
    path('medical_qa/', views.medical_qa, name='medical_qa'),
    path('feedback/', views.feedback_api, name='feedback'),
    
    # 性能监控API
    path('performance/', performance_views.performance_stats, name='performance_stats'),
    path('performance/reset/', performance_views.reset_stats, name='reset_stats'),
    path('performance/clear_cache/', performance_views.clear_cache, name='clear_cache'),
] 