from django.contrib import admin
from .models import User,Admin,UserLog,SystemLog

admin.site.register(User)
admin.site.register(Admin)
admin.site.register(UserLog)
admin.site.register(SystemLog)

