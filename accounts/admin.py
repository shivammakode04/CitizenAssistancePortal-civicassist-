
from django.contrib import admin
from django.contrib.auth.hashers import make_password
from .models import User, Citizen, Official


class UserAdmin(admin.ModelAdmin):

    list_display = (
        "email",
        "full_name",
        "phone_number",
        "is_citizen",
        "is_official",
        "is_active",
    )

    list_filter = (
        "is_citizen",
        "is_official",
        "is_active",
    )

    search_fields = (
        "email",
        "full_name",
        "phone_number",
        "aadhar_number",
    )

    ordering = ("email",)

    readonly_fields = ()

    fieldsets = (
        ("Login Credentials", {
            "fields": (
                "email",
                "password",
            )
        }),

        ("Personal Information", {
            "fields": (
                "full_name",
                "phone_number",
                "aadhar_number",
            )
        }),

        ("Roles", {
            "fields": (
                "is_citizen",
                "is_official",
            )
        }),

        ("Permissions", {
            "fields": (
                "is_active",
                "is_staff",
                "is_superuser",
            )
        }),
    )

    add_fieldsets = (
        ("Create User", {
            "classes": ("wide",),
            "fields": (
                "email",
                "password",
                "full_name",
                "phone_number",
                "aadhar_number",
                "is_citizen",
                "is_official",
                "is_active",
            ),
        }),
    )

    def save_model(self, request, obj, form, change):
        if obj.password and not obj.password.startswith("pbkdf2"):
            obj.password = make_password(obj.password)
        super().save_model(request, obj, form, change)


class CitizenAdmin(admin.ModelAdmin):

    list_display = (
        "user",
        "city",
        "pincode",
    )

    search_fields = (
        "user__email",
        "user__full_name",
        "city",
    )


class OfficialAdmin(admin.ModelAdmin):

    list_display = (
        "user",
        "official_id",
        "department",
    )

    search_fields = (
        "user__email",
        "official_id",
        "department__name",
        "department__code",
    )


admin.site.register(User, UserAdmin)
admin.site.register(Citizen, CitizenAdmin)
admin.site.register(Official, OfficialAdmin)
