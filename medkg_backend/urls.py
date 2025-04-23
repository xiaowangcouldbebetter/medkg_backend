# """
# URL configuration for medkg_backend project.
#
# The `urlpatterns` list routes URLs to views. For more information please see:
#     https://docs.djangoproject.com/en/5.1/topics/http/urls/
# Examples:
# Function views
#     1. Add an import:  from my_app import views
#     2. Add a URL to urlpatterns:  path('', views.home, name='home')
# Class-based views
#     1. Add an import:  from other_app.views import Home
#     2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
# Including another URLconf
#     1. Import the include() function: from django.urls import include, path
#     2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
# """

from django.contrib import admin
from django.urls import path
from django.http import JsonResponse

from accounts import views as account_views
from qa_api.views import medical_qa, get_history, clear_history
from kg_module import views as kg_views



def home(request):
    return JsonResponse({
        'message': 'Welcome to the Medical KG QA System!',
        'endpoints': {
            'qa': '/api/qa/',
            'history': '/api/history/',
            'history/clear': '/api/history/clear/',
            'auth': {
                'login': '/api/login/',
                'register': '/api/register/',
                'logout': '/api/logout/',
                'public-key': '/api/public-key/',
                'admin-login': '/api/admin/login/'
            },
            'user': {
                'info': '/api/user/info/',
                'feedback': '/api/user/feedback/'
            },
            'admin': {
                'user-logs': '/api/admin/logs/user/',
                'system-logs': '/api/admin/logs/system/',
                'feedbacks': '/api/admin/feedbacks/'
            },
            'kg': {
                'statistics': '/api/kg/statistics/',
                'visualization': '/api/kg/visualization/',
                'update': '/api/kg/update/',
                'search': '/api/kg/search/'
            }
        }
    })

urlpatterns = [
    path('', home),  # 根路径
    path('api/qa/', medical_qa, name='medical_qa'),  # QA接口
    path('api/history/', get_history, name='get_history'),  # 获取历史记录
    path('api/history/clear/', clear_history, name='clear_history'),  # 清空历史记录
    path('admin/', admin.site.urls, name='admin'),
    
    # 用户认证相关
    path('api/public-key/', account_views.public_key, name='public_key'),
    path('api/verify/', account_views.verify, name='verify'),
    path('api/login/', account_views.login, name='login'),
    path('api/register/', account_views.register, name='register'),
    path('api/logout/', account_views.logout, name='logout'),
    path('api/user/info/', account_views.user_info, name='user_info'),
    
    # 用户反馈相关
    path('api/user/feedback/', account_views.submit_feedback, name='submit_feedback'),
    path('api/admin/feedbacks/', account_views.admin_feedback_list, name='admin_feedback_list'),
    path('api/admin/feedbacks/<int:feedback_id>/', account_views.update_feedback_status, name='update_feedback_status'),
    
    # 管理员相关
    path('api/admin/login/', account_views.admin_login, name='admin_login'),
    path('api/admin/logs/user/', account_views.get_user_logs, name='get_user_logs'),
    path('api/admin/logs/system/', account_views.get_system_logs, name='get_system_logs'),
    
    # 日志记录
    path('api/logs/chat/', account_views.record_chat_log, name='record_chat_log'),
    
    # 知识图谱相关
    path('api/kg/statistics/', kg_views.kg_statistics_view, name='kg_statistics'),
    path('api/kg/visualization/', kg_views.kg_visualization_view, name='kg_visualization'),
    path('api/kg/update/', kg_views.kg_update_view, name='kg_update'),
    path('api/kg/search/', kg_views.search_knowledge_graph, name='search_knowledge_graph'),
]