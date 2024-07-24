from django.contrib import admin
from apps.team.models import *
# Register your models here.

admin.site.register(Team)
admin.site.register(Player)
admin.site.register(LeaguesTeamType)
admin.site.register(LeaguesPesrsonType)
admin.site.register(Leagues)
admin.site.register(Tournament)
admin.site.register(LeaguesPlayType)
admin.site.register(SaveLeagues)
admin.site.register(RoundRobinGroup)
admin.site.register(TournamentSetsResult)
admin.site.register(PaymentDetailsForRegister)