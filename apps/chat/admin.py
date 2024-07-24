from django.contrib import admin
from apps.chat.models import *
# Register your models here.

admin.site.register(Room)
admin.site.register(MessageBox)
admin.site.register(NotifiRoom)
admin.site.register(NotificationBox)