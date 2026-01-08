# reservation/admin.py
from django.contrib import admin

from .models import Facility, Booking


@admin.register(Facility)
class FacilityAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "location",
        "is_active",
        "require_approval",
        "approver",
        "min_rank_level",
        "view_min_rank_level",
    )
    list_filter = ("is_active", "require_approval")
    search_fields = ("name", "location", "approver__username", "approver__email")
    ordering = ("name",)
    filter_horizontal = ("allowed_departments", "allowed_ranks")


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "facility",
        "user",
        "date",
        "start_time",
        "end_time",
        "status",
        "title",
        "created_at",
    )
    list_filter = ("status", "facility", "date")
    search_fields = (
        "facility__name",
        "user__username",
        "user__email",
        "title",
        "decision_note",
        "rejection_reason",
        "cancel_reason",
    )
    ordering = ("-date", "-start_time")
    date_hierarchy = "date"
    raw_id_fields = ("user", "approved_by", "rejected_by", "canceled_by")
