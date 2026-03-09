
from django.urls import path
from . import views

urlpatterns = [
    path("", views.citizen_view, name="citizen_dashboard"),
    path("citizen/cases/", views.citizen_cases, name="citizen_cases"),
    path("citizen/history/", views.citizen_history, name="citizen_history"),
    path("citizen/profile/", views.citizen_profile, name="citizen_profile"),
    path("citizen/profile/edit/", views.citizen_profile_edit, name="citizen_profile_edit"),
    path("citizen/helpline/", views.citizen_helpline, name="citizen_helpline"),
    path("citizen/chat/", views.citizen_chat, name="citizen_chat"),
    path("citizen/permissions/", views.citizen_permissions, name="citizen_permissions"),
    path("official/", views.official_view, name="official_dashboard"),
    path("official/assigned/", views.official_assigned, name="official_assigned"),
    path("official/history/", views.official_history, name="official_history"),
    path("official/alerts/", views.official_alerts, name="official_alerts"),
    path("official/helpline/", views.official_helpline, name="official_helpline"),
    path("official/profile/edit/", views.official_profile_edit, name="official_profile_edit"),
]

