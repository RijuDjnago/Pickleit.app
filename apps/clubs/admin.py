from django.contrib import admin
from .models import *

class ClubImageInline(admin.TabularInline):
    model = ClubImage
    extra = 0


class ClubPackageInline(admin.TabularInline):
    model = ClubPackage
    extra = 0


class ClubRatingInline(admin.TabularInline):
    model = ClubRating
    extra = 0




@admin.register(Club)
class ClubAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'location', 'contact', 'email', 'overall_rating')
    search_fields = ('name', 'location', 'contact', 'email')
    list_filter = ('open_time', 'close_time')
    inlines = [ClubImageInline, ClubPackageInline, ClubRatingInline]
    readonly_fields = ('overall_rating',)  # Prevent manual editing
    ordering = ('name',)

admin.site.register(ClubPackage)
admin.site.register(ClubRating)
admin.site.register(BookClub)
admin.site.register(JoinClub)