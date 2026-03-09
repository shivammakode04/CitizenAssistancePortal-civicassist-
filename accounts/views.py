from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
from .models import User, Citizen
import logging

logger = logging.getLogger(__name__)


@csrf_protect
@require_http_methods(["GET", "POST"])
def user_login(request):

    if request.method == "POST":

        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")

        if not email or not password:
            messages.error(request, "Please enter email and password.")
            return render(request, "login.html")

        user = authenticate(request, email=email, password=password)

        if user is not None:

            if not user.is_active:
                messages.error(request, "Account disabled. Contact support.")
                return render(request, "login.html")

            login(request, user)

            messages.success(request, f"Welcome back, {user.full_name}!")

            # role based redirect
            if user.is_official:
                return redirect("official_dashboard")

            elif user.is_citizen:
                return redirect("citizen_dashboard")

            else:
                return redirect("home")

        else:
            messages.error(request, "Invalid email or password.")

    return render(request, "login.html")


def signup(request):

    if request.method == "POST":

        full_name = request.POST.get("full_name")
        email = request.POST.get("email")
        phone = request.POST.get("phone")
        aadhar = request.POST.get("aadhar_number")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        if not full_name or not email or not phone or not aadhar or not password:
            messages.error(request, "All fields are required.")
            return render(request, "signup.html")

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already exists.")
            return render(request, "signup.html")

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, "signup.html")

        try:

            user = User.objects.create_user(
                email=email,
                password=password,
                full_name=full_name,
                phone_number=phone,
                aadhar_number=aadhar,
                is_citizen=True
            )

            Citizen.objects.create(user=user)

            messages.success(request, "Account created successfully.")
            return redirect("login")

        except Exception as e:
            messages.error(request, str(e))

    return render(request, "signup.html")