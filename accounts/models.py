# accounts/models.py
from django.db import models
from django.contrib.auth.hashers import make_password, check_password


class BaseUser(models.Model):
    class Meta:
        abstract = True

    name = models.CharField(max_length=50)
    email = models.EmailField(unique=True)
    password_hash = models.CharField(max_length=128, null=True)  # 存储哈希后的密码
    last_login = models.DateTimeField(null=True, blank=True)  # 上次登录时间
    created_at = models.DateTimeField(auto_now_add=True)
    
    def set_password(self, raw_password):
        """设置密码，自动进行哈希处理"""
        self.password_hash = make_password(raw_password)
        
    def check_password(self, raw_password):
        """检查密码是否正确"""
        return check_password(raw_password, self.password_hash)


class User(BaseUser):
    """普通用户模型"""
    class Meta:
        db_table = 'accounts_user'  # 映射现有用户表


class Admin(BaseUser):
    """管理员用户模型"""
    class Meta:
        db_table = 'account_admin'  # 映射管理员表


# 用户日志模型
class UserLog(models.Model):
    """
    用户日志，记录用户询问的问题和系统回复
    """
    class Meta:
        db_table = 'account_user_log'
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    question = models.TextField()  # 用户提问
    answer = models.TextField(null=True, blank=True)  # 系统回答
    status = models.CharField(max_length=20, choices=[
        ('success', '成功回复'),
        ('not_found', '知识图谱中未找到'),
        ('error', '系统错误'),
    ])
    created_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)


# 系统日志模型
class SystemLog(models.Model):
    """
    系统日志，记录后端日志
    """
    class Meta:
        db_table = 'system_log'
    
    level = models.CharField(max_length=20, choices=[
        ('INFO', '信息'),
        ('WARNING', '警告'),
        ('ERROR', '错误'),
        ('CRITICAL', '严重错误'),
    ])
    module = models.CharField(max_length=100)  # 模块名称
    message = models.TextField()  # 日志消息
    created_at = models.DateTimeField(auto_now_add=True)
    trace = models.TextField(null=True, blank=True)  # 错误追踪信息


# 用户反馈模型
class UserBug(models.Model):
    """
    用户反馈的bug和建议
    """
    class Meta:
        db_table = 'accounts_user_bug'
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    title = models.CharField(max_length=200)  # 反馈标题
    content = models.TextField()  # 反馈内容
    bug_type = models.CharField(max_length=20, choices=[
        ('bug', '系统错误'),
        ('suggestion', '功能建议'),
        ('other', '其他')
    ])
    status = models.CharField(max_length=20, choices=[
        ('pending', '待处理'),
        ('processing', '处理中'),
        ('resolved', '已解决'),
        ('rejected', '不予处理')
    ], default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    admin_remarks = models.TextField(null=True, blank=True)  # 管理员备注