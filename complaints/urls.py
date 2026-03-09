from django.urls import path

from . import views

urlpatterns = [
    path("file/", views.file_complaint, name="file_complaint"),
    path("notifications/", views.citizen_notifications, name="citizen_notifications"),
    path(
        "notifications/<int:notification_id>/ack/",
        views.acknowledge_notification,
        name="acknowledge_notification",
    ),
    path("<int:pk>/", views.complaint_detail, name="complaint_detail"),
    path("<int:pk>/close/", views.close_complaint, name="close_complaint"),
    path("<int:pk>/reopen/", views.reopen_complaint, name="reopen_complaint"),
    path("<int:pk>/send-to-helpline/", views.send_to_helpline, name="send_to_helpline"),
    path(
        "<int:pk>/wrong-department/",
        views.mark_wrong_department,
        name="mark_wrong_department",
    ),
]


