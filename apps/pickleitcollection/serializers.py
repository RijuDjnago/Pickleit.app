from rest_framework import serializers
from .models import *

class AdvertisementSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    created_by_first_name = serializers.CharField(source='created_by.first_name', read_only=True)
    created_by_last_name = serializers.CharField(source='created_by.last_name', read_only=True)
    days_left = serializers.SerializerMethodField()
    admin_approve_status = serializers.SerializerMethodField()

    class Meta:
        model = Advertisement
        fields = [
            "id", "uuid", "secret_key", "name", "image", "script_text", "url",
            "approved_by_admin", "admin_approve_status", "description", "start_date",
            "end_date", "created_by_first_name", "created_by_last_name", "days_left",
            "view_count"
        ]

    def get_image(self, obj):
        # obj.image.url is already the relative path, e.g. "/media/…"
        return obj.image.url if obj.image else None

    def get_days_left(self, obj):
        if obj.end_date:
            try:
                today = datetime.now().date()
                end_date = obj.end_date.date() if isinstance(obj.end_date, datetime) else obj.end_date
                days_remaining = (end_date - today).days
                return max(days_remaining, 0)  # Ensures it doesn't return negative values
            except (TypeError, AttributeError):
                return None
        return None

    def get_admin_approve_status(self, obj):
        """Dynamically determine admin_approve_status based on conditions."""
        current_status = obj.admin_approve_status
        if current_status == "Pending":
            return "Approved"
        elif current_status == "Rejected":
            return "Rejected"
        elif current_status == "Approved" and obj.approved_by_admin:
            try:
                today = datetime.now().date()
                end_date = obj.end_date.date() if isinstance(obj.end_date, datetime) else obj.end_date
                return "Renew" if end_date < today else "Approved"
            except (TypeError, AttributeError):
                return "Approved"  # Fallback to Approved if date handling fails
        return current_status
    
    
class FacilityImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = FacilityImage
        fields = "__all__"

class AdvertiserFacilitySerializer(serializers.ModelSerializer):
    facility_image = FacilityImageSerializer(many=True)

    class Meta:
        model = AdvertiserFacility
        fields = [
            'id',
            'uuid',
            'secret_key',
            'facility_name',
            'facility_type',
            'court_type',
            'membership_type',
            'complete_address',
            'latitude',
            'longitude',
            'number_of_courts',
            'response',
            'created_at',
            'created_by',
            'updated_at',
            'updated_by',
            'acknowledgement',
            'is_view',
            'facility_image'
        ]