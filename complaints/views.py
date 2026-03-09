from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from .ml import predict_department_and_priority
from .models import (
    Complaint,
    Department,
    Notification,
    ComplaintHistory,
    ensure_departments_seeded,
)


@login_required
def file_complaint(request: HttpRequest) -> HttpResponse:
    """
    Citizen-facing view to file a new complaint.

    Uses the ML model to classify department and priority,
    generates a ticket number, and saves the complaint.
    """
    if not getattr(request.user, "is_citizen", False):
        return HttpResponseForbidden("Only citizens can file complaints.")

    ensure_departments_seeded()

    if request.method == "POST":
        description = request.POST.get("description", "").strip()
        location = request.POST.get("location", "").strip()
        city = request.POST.get("city", "").strip()
        pincode = request.POST.get("pincode", "").strip()
        district = request.POST.get("district", "").strip()
        image_file = request.FILES.get("image")

        if not description or not location:
            messages.error(
                request, "Please provide complaint description and location."
            )
            return render(request, "file_complaint.html")

        # ML model predicts routing department + priority from description.
        prediction = predict_department_and_priority(description)

        # Safety: if ML code does not map to a known department,
        # fall back to Helpline, then to the first configured department.
        department = (
            Department.objects.filter(code=prediction.department_code).first()
            or Department.objects.filter(is_helpline=True).first()
            or Department.objects.first()
        )

        if department is None:
            messages.error(
                request, "No departments configured. Contact administrator."
            )
            return render(request, "file_complaint.html")

        complaint = Complaint.objects.create(
            citizen=request.user,
            department=department,
            description=description,
            location=location,
            city=city,
            pincode=pincode,
            district=district,
            image=image_file,
            priority=prediction.priority,
        )

        ComplaintHistory.objects.create(
            complaint=complaint,
            actor=request.user,
            action="FILED",
            to_status=complaint.status,
            to_department=complaint.department,
            notes="Complaint filed by citizen.",
        )

        messages.success(
            request,
            f"Complaint filed successfully with Ticket No. {complaint.ticket_number} "
            f"and routed to {complaint.department.name}.",
        )
        return redirect("citizen_dashboard")

    return render(request, "file_complaint.html")


@login_required
def complaint_detail(request: HttpRequest, pk: int) -> HttpResponse:
    """
    Shared detail view for both citizen and official.
    """
    complaint = get_object_or_404(Complaint, pk=pk)

    if request.user.is_citizen and complaint.citizen != request.user:
        return HttpResponseForbidden("You are not allowed to view this complaint.")

    history_events = complaint.history.select_related(
        "actor", "from_department", "to_department"
    )

    context = {
        "complaint": complaint,
        "history_events": history_events,
    }
    return render(request, "complaint_detail.html", context)


@login_required
def close_complaint(request: HttpRequest, pk: int) -> HttpResponse:
    """
    Official closes a complaint. This creates a notification
    for the citizen to confirm or reopen.
    """
    complaint = get_object_or_404(Complaint, pk=pk)

    if not getattr(request.user, "is_official", False):
        return HttpResponseForbidden("Only officials can close complaints.")

    if request.method == "POST":
        from_status = complaint.status
        complaint.status = "CLOSED"
        complaint.save(update_fields=["status", "updated_at"])

        ComplaintHistory.objects.create(
            complaint=complaint,
            actor=request.user,
            action="CLOSED",
            from_status=from_status,
            to_status=complaint.status,
            from_department=complaint.department,
            to_department=complaint.department,
            notes="Complaint closed by official.",
        )

        Notification.objects.create(
            user=complaint.citizen,
            complaint=complaint,
            message=f"Complaint {complaint.ticket_number} has been marked as CLOSED.",
        )

        messages.success(request, f"Complaint {complaint.ticket_number} closed.")
        return redirect("official_dashboard")

    return redirect("complaint_detail", pk=pk)


@login_required
def send_to_helpline(request: HttpRequest, pk: int) -> HttpResponse:
    """
    Citizen-initiated escalation:
    Move a complaint from its current department to the Helpline department.
    """
    complaint = get_object_or_404(Complaint, pk=pk)

    if not getattr(request.user, "is_citizen", False):
        return HttpResponseForbidden("Only citizens can escalate to helpline.")

    if complaint.citizen != request.user:
        return HttpResponseForbidden("You are not allowed to escalate this complaint.")

    ensure_departments_seeded()
    helpline = Department.objects.filter(is_helpline=True).first()

    if request.method == "POST":
        if helpline is None:
            messages.error(
                request,
                "Helpline department is not configured. Please contact administrator.",
            )
            return redirect("complaint_detail", pk=pk)

        if complaint.department == helpline:
            messages.info(
                request,
                "This complaint is already assigned to the Helpline department.",
            )
            return redirect("complaint_detail", pk=pk)

        from_department = complaint.department
        from_status = complaint.status
        complaint.department = helpline
        complaint.status = "TRANSFERRED"
        complaint.save(update_fields=["department", "status", "updated_at"])

        ComplaintHistory.objects.create(
            complaint=complaint,
            actor=request.user,
            action="ESCALATED_TO_HELPLINE",
            from_status=from_status,
            to_status=complaint.status,
            from_department=from_department,
            to_department=helpline,
            notes="Citizen escalated complaint to Helpline.",
        )

        Notification.objects.create(
            user=complaint.citizen,
            complaint=complaint,
            message=(
                f"Complaint {complaint.ticket_number} has been moved to "
                f"{helpline.name} for resolution."
            ),
        )

        messages.success(
            request,
            f"Complaint {complaint.ticket_number} has been escalated to Helpline.",
        )
        return redirect("complaint_detail", pk=pk)

    return redirect("complaint_detail", pk=pk)


@login_required
def mark_wrong_department(request: HttpRequest, pk: int) -> HttpResponse:
    """
    Official marks a complaint as wrong department and reassigns
    it to another department via picklist.
    """
    if not getattr(request.user, "is_official", False):
        return HttpResponseForbidden("Only officials can transfer complaints.")

    ensure_departments_seeded()
    complaint = get_object_or_404(Complaint, pk=pk)

    if request.method == "POST":
        new_department_id = request.POST.get("department_id")
        new_department = get_object_or_404(Department, id=new_department_id)

        from_department = complaint.department
        from_status = complaint.status

        complaint.department = new_department
        complaint.status = "TRANSFERRED"
        complaint.save(update_fields=["department", "status", "updated_at"])

        ComplaintHistory.objects.create(
            complaint=complaint,
            actor=request.user,
            action="TRANSFERRED",
            from_status=from_status,
            to_status=complaint.status,
            from_department=from_department,
            to_department=new_department,
            notes="Complaint transferred to another department by official.",
        )

        Notification.objects.create(
            user=complaint.citizen,
            complaint=complaint,
            message=(
                f"Complaint {complaint.ticket_number} has been transferred to "
                f"{new_department.name}."
            ),
        )

        messages.success(
            request,
            f"Complaint {complaint.ticket_number} transferred to {new_department.name}.",
        )
        return redirect("official_dashboard")

    departments = Department.objects.all().order_by("name")
    context = {
        "complaint": complaint,
        "departments": departments,
    }
    return render(request, "reassign_complaint.html", context)


@login_required
def citizen_notifications(request: HttpRequest) -> HttpResponse:
    """
    Show notifications to the logged-in citizen, with actions
    to reopen or keep a complaint closed.
    """
    if not getattr(request.user, "is_citizen", False):
        return HttpResponseForbidden("Only citizens can view these notifications.")

    notifications = request.user.notifications.all()
    context = {"notifications": notifications}
    return render(request, "citizen_notifications.html", context)


@login_required
def reopen_complaint(request: HttpRequest, pk: int) -> HttpResponse:
    """
    Citizen chooses to reopen a closed complaint from notification/history.
    """
    complaint = get_object_or_404(Complaint, pk=pk)

    if not getattr(request.user, "is_citizen", False):
        return HttpResponseForbidden("Only citizens can reopen complaints.")

    if complaint.citizen != request.user:
        return HttpResponseForbidden("You are not allowed to reopen this complaint.")

    if request.method == "POST":
        from_status = complaint.status
        complaint.status = "REOPENED"
        complaint.save(update_fields=["status", "updated_at"])

        ComplaintHistory.objects.create(
            complaint=complaint,
            actor=request.user,
            action="REOPENED",
            from_status=from_status,
            to_status=complaint.status,
            from_department=complaint.department,
            to_department=complaint.department,
            notes="Complaint reopened by citizen.",
        )

        Notification.objects.create(
            user=complaint.citizen,
            complaint=complaint,
            message=f"Complaint {complaint.ticket_number} has been REOPENED.",
        )

        messages.success(request, f"Complaint {complaint.ticket_number} reopened.")
        return redirect("citizen_dashboard")

    return redirect("complaint_detail", pk=pk)


@login_required
def acknowledge_notification(request: HttpRequest, notification_id: int) -> HttpResponse:
    """
    Mark a notification as read without changing complaint status.
    """
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)

    if request.method == "POST":
        notification.is_read = True
        notification.save(update_fields=["is_read"])
        return redirect("citizen_notifications")

    return redirect("citizen_notifications")

