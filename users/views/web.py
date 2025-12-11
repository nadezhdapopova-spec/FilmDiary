from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from users.forms import RegisterForm


def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user:
            login(request, user)   # СЕССИЯ Django
            return redirect("users:profile")

        messages.error(request, "Неверный логин или пароль")

    return render(request, "users/login.html")


def register_view(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, "Регистрация успешна!")
            return redirect("users:login")
    else:
        form = RegisterForm()

    return render(request, "users/register.html", {"form": form})


@login_required
def profile_view(request):
    return render(request, "users/profile.html")
