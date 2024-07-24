from django.contrib import admin
from apps.user.models import *
# Register your models here.

admin.site.register(User)
admin.site.register(Role)
admin.site.register(IsSponsorDetails)
admin.site.register(AppUpdate)
admin.site.register(BasicQuestionsUser)
admin.site.register(UserAnswer)
admin.site.register(MatchingPlayers)
admin.site.register(FCMTokenStore)
class LogEntryAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'model_name', 'instance_id', 'timestamp')
    ordering = ('-timestamp',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs
    
    list_per_page = 20

admin.site.register(LogEntry, LogEntryAdmin)