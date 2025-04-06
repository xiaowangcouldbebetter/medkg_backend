from django.contrib import admin
from django.urls import path
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.contrib.admin.views.decorators import staff_member_required

from utils.performance_monitor import get_performance_stats, reset_performance_stats

class MedKGAdmin(admin.AdminSite):
    site_header = "医疗知识图谱问答系统管理"
    site_title = "医疗知识图谱管理"
    index_title = "管理面板"
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('performance/', self.admin_view(self.performance_view), name='performance'),
            path('reset_performance/', self.admin_view(self.reset_performance), name='reset_performance'),
        ]
        return custom_urls + urls
    
    @never_cache
    @staff_member_required
    def performance_view(self, request):
        """获取性能统计数据的视图"""
        stats = get_performance_stats()
        return JsonResponse({
            'success': True,
            'data': stats
        })
    
    @never_cache
    @staff_member_required
    def reset_performance(self, request):
        """重置性能统计数据的视图"""
        reset_performance_stats()
        return JsonResponse({
            'success': True,
            'message': '性能统计数据已重置'
        })

# 注册自定义管理站点
admin_site = MedKGAdmin(name='medkg_admin') 