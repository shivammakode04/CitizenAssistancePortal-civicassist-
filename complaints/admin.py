from django.contrib import admin

from .models import Complaint, Department, Notification


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "category", "is_helpline")
    list_filter = ("category", "is_helpline")
    search_fields = ("code", "name")


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = (
        "ticket_number",
        "citizen",
        "department",
        "priority",
        "status",
        "created_at",
    )
    list_filter = ("department", "priority", "status", "created_at")
    search_fields = ("ticket_number", "description", "citizen__email")
    readonly_fields = ("ticket_number", "created_at", "updated_at")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "complaint", "message", "created_at", "is_read")
    list_filter = ("is_read", "created_at")
    search_fields = ("user__email", "message")
