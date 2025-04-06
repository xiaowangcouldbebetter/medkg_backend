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
from django.urls import path, include
from django.http import JsonResponse
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from qa_api.admin import admin_site

from accounts import views as account_views
from qa_api.views import medical_qa



def home(request):
    return JsonResponse({
        'message': 'Welcome to the Medical KG QA System!',
        'endpoints': {
            'qa': '/api/qa/'
        }
    })

urlpatterns = [
    path('', home),  # 根路径
    path('api/qa/', medical_qa, name='medical_qa'),  # QA接口
    path('admin/', admin_site.urls),  # 使用自定义管理站点
    
    # 用户认证相关接口
    path('api/register/', account_views.register, name='register'),  # 注册接口
    path('api/login/', account_views.login, name='login'),  # 登录接口
    path('api/user-info/', account_views.user_info, name='user_info'),  # 用户信息接口
    
    # 兼容旧接口
    path('api/public-key/', account_views.public_key, name='public_key'),
    path('api/verify/', account_views.verify, name='verify'),
]

# 添加JWT令牌接口
urlpatterns += [
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]

# 添加QA API和KG模块的URL
urlpatterns += [
    path('api/qa/', include('qa_api.urls')),
    path('api/kg/', include('kg_module.urls')),
]