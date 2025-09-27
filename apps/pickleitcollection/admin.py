from django.contrib import admin
from apps.pickleitcollection.models import *
from django.utils import timezone
from django.utils.html import format_html
from datetime import datetime
from dateutil.relativedelta import relativedelta

@admin.register(Advertisement)
class AdvertisementAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'name', 'company_name', 'approved_by_admin', 'admin_approve_status', 
        'view_count', 'created_at', 'renew', 'remaining_days'
    )
    list_filter = ('admin_approve_status', 'approved_by_admin', 'start_date', 'end_date', 'created_at')
    search_fields = ('name', 'company_name', 'company_website', 'url', 'secret_key')
    readonly_fields = ('uuid', 'view_count', 'created_at')
    autocomplete_fields = ['created_by']
    fieldsets = (
        ('Basic Info', {
            'fields': ('uuid', 'secret_key', 'name', 'company_name', 'company_website', 'description')
        }),
        ('Advertisement Details', {
            'fields': ('duration', 'image', 'script_text', 'url')
        }),
        ('Status', {
            'fields': ('approved_by_admin', 'admin_approve_status', 'view_count')
        }),
        ('Timeline', {
            'fields': ('start_date', 'end_date', 'created_at', 'created_by')
        }),
    )

    def renew(self, obj):
        """Check if the advertisement can be renewed (expired if end_date is before today)."""
        if obj.end_date:
            try:
                end_date = obj.end_date.date() if isinstance(obj.end_date, datetime) else obj.end_date
                return end_date < timezone.now().date()
            except (TypeError, AttributeError):
                return False
        return False
    renew.boolean = True
    renew.short_description = 'Can Renew'

    def remaining_days(self, obj):
        """Display remaining time in years, months, days in green (future/today) or red (past)."""
        if obj.end_date:
            try:
                end_date = obj.end_date.date() if isinstance(obj.end_date, datetime) else obj.end_date
                today = timezone.now().date()
                delta = relativedelta(end_date, today)
                years, months, days = delta.years, delta.months, delta.days
                parts = []
                if abs(years) > 0:
                    parts.append(f"{abs(years)}y")
                if abs(months) > 0 or parts:  # Include months if years exist or months non-zero
                    parts.append(f"{abs(months)}m")
                parts.append(f"{abs(days)}d")  # Always include days
                time_str = " ".join(parts)
                # Apply green for future/today, red for past
                color = "green" if end_date >= today else "red"
                return format_html('<span style="color: {};">{}</span>', color, time_str)
            except (TypeError, AttributeError):
                return "Mismatch Data"
        return "Mismatch Data"
    remaining_days.short_description = 'Remaining Time'

admin.site.register(AdvertisementDurationRate)
admin.site.register(ChargeAmount)
admin.site.register(AmbassadorsDetails)
admin.site.register(Tags)
admin.site.register(Notifications)
admin.site.register(AmbassadorsPost)
admin.site.register(AdvertiserFacility)
admin.site.register(PaymentDetails)


