from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from complaints.models import (
    Complaint,
    Department,
    ensure_departments_seeded,
    auto_escalate_overdue_complaints,
)


@login_required
def citizen_view(request):
    user = request.user

    if not getattr(user, "is_citizen", False):
        return redirect("home")

    # Run SLA auto-escalation periodically whenever citizen opens dashboard.
    auto_escalate_overdue_complaints()

    profile = user.citizen_profile

    complaints = (
        Complaint.objects.filter(citizen=user)
        .select_related("department")
        .order_by("-created_at")[:20]
    )

    total_filed = Complaint.objects.filter(citizen=user).count()
    solved_count = Complaint.objects.filter(citizen=user, status="CLOSED").count()

    context = {
        "user": user,
        "full_name": user.full_name,
        "email": user.email,
        "phone_number": user.phone_number,
        "aadhar_number": user.aadhar_number,
        "address": profile.address,
        "city": profile.city,
        "pincode": profile.pincode,
        "user_type": "Citizen",
        "complaints": complaints,
        "total_filed": total_filed,
        "solved_count": solved_count,
    }
    return render(request, "citizendashboard.html", context)


@login_required
def citizen_cases(request):
    user = request.user

    if not getattr(user, "is_citizen", False):
        return redirect("home")

    complaints = (
        Complaint.objects.filter(
            citizen=user, status__in=["OPEN", "REOPENED", "TRANSFERRED"]
        )
        .select_related("department")
        .order_by("-created_at")
    )

    context = {
        "full_name": user.full_name,
        "email": user.email,
        "complaints": complaints,
    }
    return render(request, "citizen_cases.html", context)


@login_required
def citizen_history(request):
    user = request.user

    if not getattr(user, "is_citizen", False):
        return redirect("home")

    complaints = (
        Complaint.objects.filter(citizen=user)
        .select_related("department")
        .order_by("-created_at")
    )

    context = {
        "full_name": user.full_name,
        "email": user.email,
        "complaints": complaints,
    }
    return render(request, "citizen_history.html", context)


@login_required
def citizen_profile(request):
    user = request.user

    if not getattr(user, "is_citizen", False):
        return redirect("home")

    profile = user.citizen_profile
    context = {
        "full_name": user.full_name,
        "email": user.email,
        "phone_number": user.phone_number,
        "aadhar_number": user.aadhar_number,
        "address": profile.address,
        "city": profile.city,
        "pincode": profile.pincode,
    }
    return render(request, "citizen_profile.html", context)


@login_required
def citizen_profile_edit(request):
    user = request.user

    if not getattr(user, "is_citizen", False):
        return redirect("home")

    profile = user.citizen_profile

    if request.method == "POST":
        full_name = request.POST.get("full_name", "").strip()
        phone_number = request.POST.get("phone_number", "").strip()
        address = request.POST.get("address", "").strip()
        city = request.POST.get("city", "").strip()
        pincode = request.POST.get("pincode", "").strip()
        avatar_file = request.FILES.get("avatar")

        if not full_name or not phone_number:
            messages.error(request, "Full name and phone number are required.")
        else:
            user.full_name = full_name
            user.phone_number = phone_number
            update_fields = ["full_name", "phone_number"]
            if avatar_file:
                user.avatar = avatar_file
                update_fields.append("avatar")
            user.save(update_fields=update_fields)

            profile.address = address
            profile.city = city
            profile.pincode = pincode
            profile.save(update_fields=["address", "city", "pincode"])

            messages.success(request, "Profile updated successfully.")
            return redirect("citizen_profile")

    context = {
        "full_name": user.full_name,
        "email": user.email,
        "phone_number": user.phone_number,
        "aadhar_number": user.aadhar_number,
        "address": profile.address,
        "city": profile.city,
        "pincode": profile.pincode,
        "user": user,
    }
    return render(request, "citizen_profile_edit.html", context)


@login_required
def citizen_helpline(request):
    user = request.user

    if not getattr(user, "is_citizen", False):
        return redirect("home")

    ensure_departments_seeded()
    helpline = Department.objects.filter(is_helpline=True).first()
    context = {
        "full_name": user.full_name,
        "email": user.email,
        "helpline": helpline,
    }
    return render(request, "citizen_helpline.html", context)


@login_required
def citizen_chat(request):
    user = request.user
    if not getattr(user, "is_citizen", False):
        return redirect("home")
    context = {
        "full_name": user.full_name,
        "email": user.email,
    }
    return render(request, "citizen_chat.html", context)


@login_required
def citizen_permissions(request):
    user = request.user
    if not getattr(user, "is_citizen", False):
        return redirect("home")
    context = {
        "full_name": user.full_name,
        "email": user.email,
    }
    return render(request, "citizen_permissions.html", context)


@login_required
def official_view(request):
    user = request.user

    if not getattr(user, "is_official", False):
        return redirect("home")

    profile = user.official_profile

    ensure_departments_seeded()
    auto_escalate_overdue_complaints()

    department = profile.department

    if department is not None:
        complaints = (
            Complaint.objects.filter(department=department)
            .select_related("citizen", "department")
            .order_by("-created_at")
        )
    else:
        complaints = Complaint.objects.none()

    context = {
        "user": user,
        "full_name": user.full_name,
        "email": user.email,
        "phone_number": user.phone_number,
        "aadhar_number": user.aadhar_number,
        "official_id": profile.official_id,
        "department": department.name if department else "",
        "user_type": "Official",
        "complaints": complaints,
        "bound_department": department,
    }
    return render(request, "officialdashboard.html", context)


@login_required
def official_assigned(request):
    user = request.user

    if not getattr(user, "is_official", False):
        return redirect("home")

    ensure_departments_seeded()
    auto_escalate_overdue_complaints()
    profile = user.official_profile
    department = profile.department

    if department is not None:
        complaints = (
            Complaint.objects.filter(
                department=department, status__in=["OPEN", "REOPENED", "TRANSFERRED"]
            )
            .select_related("citizen", "department")
            .order_by("-created_at")
        )
    else:
        complaints = Complaint.objects.none()

    context = {
        "full_name": user.full_name,
        "email": user.email,
        "complaints": complaints,
        "bound_department": department,
    }
    return render(request, "official_assigned.html", context)


@login_required
def official_history(request):
    user = request.user

    if not getattr(user, "is_official", False):
        return redirect("home")

    ensure_departments_seeded()
    auto_escalate_overdue_complaints()
    profile = user.official_profile
    department = profile.department

    if department is not None:
        complaints = (
            Complaint.objects.filter(department=department)
            .select_related("citizen", "department")
            .order_by("-created_at")
        )
    else:
        complaints = Complaint.objects.none()

    context = {
        "full_name": user.full_name,
        "email": user.email,
        "complaints": complaints,
        "bound_department": department,
    }
    return render(request, "official_history.html", context)


@login_required
def official_alerts(request):
    user = request.user

    if not getattr(user, "is_official", False):
        return redirect("home")

    ensure_departments_seeded()
    auto_escalate_overdue_complaints()
    profile = user.official_profile
    department = profile.department

    if department is not None:
        complaints = (
            Complaint.objects.filter(
                department=department,
                priority__in=["HIGH", "CRITICAL"],
            )
            .select_related("citizen", "department")
            .order_by("-created_at")
        )
    else:
        complaints = Complaint.objects.none()

    context = {
        "full_name": user.full_name,
        "email": user.email,
        "complaints": complaints,
        "bound_department": department,
    }
    return render(request, "official_alerts.html", context)


@login_required
def official_helpline(request):
    user = request.user

    if not getattr(user, "is_official", False):
        return redirect("home")

    ensure_departments_seeded()
    helpline = Department.objects.filter(is_helpline=True).first()
    context = {
        "full_name": user.full_name,
        "email": user.email,
        "helpline": helpline,
    }
    return render(request, "official_helpline.html", context)


@login_required
def citizen_profile_edit(request):
    user = request.user

    if not getattr(user, "is_citizen", False):
        return redirect("home")

    profile = user.citizen_profile

    if request.method == "POST":
        full_name = request.POST.get("full_name", "").strip()
        phone_number = request.POST.get("phone_number", "").strip()
        address = request.POST.get("address", "").strip()
        city = request.POST.get("city", "").strip()
        pincode = request.POST.get("pincode", "").strip()

        if not full_name or not phone_number:
            messages.error(request, "Full name and phone number are required.")
        else:
            user.full_name = full_name
            user.phone_number = phone_number
            user.save(update_fields=["full_name", "phone_number"])

            profile.address = address
            profile.city = city
            profile.pincode = pincode
            profile.save(update_fields=["address", "city", "pincode"])

            messages.success(request, "Profile updated successfully.")
            return redirect("citizen_profile")

    context = {
        "full_name": user.full_name,
        "email": user.email,
        "phone_number": user.phone_number,
        "aadhar_number": user.aadhar_number,
        "address": profile.address,
        "city": profile.city,
        "pincode": profile.pincode,
    }
    return render(request, "citizen_profile_edit.html", context)


@login_required
def official_profile_edit(request):
    user = request.user

    if not getattr(user, "is_official", False):
        return redirect("home")

    profile = user.official_profile

    ensure_departments_seeded()
    departments = Department.objects.all().order_by("name")

    if request.method == "POST":
        full_name = request.POST.get("full_name", "").strip()
        phone_number = request.POST.get("phone_number", "").strip()
        official_id = request.POST.get("official_id", "").strip()
        department_id = request.POST.get("department_id", "").strip()

        if not full_name or not phone_number or not official_id or not department_id:
            messages.error(
                request,
                "Full name, phone number, official ID and department are required.",
            )
        else:
            department = Department.objects.filter(id=department_id).first()
            if department is None:
                messages.error(request, "Selected department is invalid.")
            else:
                user.full_name = full_name
                user.phone_number = phone_number
                user.save(update_fields=["full_name", "phone_number"])

                profile.official_id = official_id
                profile.department = department
                profile.save(update_fields=["official_id", "department"])

                messages.success(request, "Official profile updated successfully.")
                return redirect("official_dashboard")

    context = {
        "full_name": user.full_name,
        "email": user.email,
        "phone_number": user.phone_number,
        "aadhar_number": user.aadhar_number,
        "official_id": profile.official_id,
        "current_department": profile.department,
        "departments": departments,
    }
    return render(request, "official_profile_edit.html", context)

