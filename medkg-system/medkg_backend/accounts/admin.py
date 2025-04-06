from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Admin

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'is_admin', 'date_joined', 'last_login')
    search_fields = ('username', 'email')
    readonly_fields = ('date_joined', 'last_login')
    
    fieldsets = (
        (None, {'fields': ('username', 'email', 'password')}),
        ('权限', {'fields': ('is_active', 'is_staff', 'is_superuser', 'is_admin')}),
        ('重要日期', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'is_admin'),
        }),
    )
    
    ordering = ('-date_joined',)

admin.site.register(User, CustomUserAdmin)
admin.site.register(Admin)
