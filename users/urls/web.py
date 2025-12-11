from django.urls import path
from users.views.web import login_view, register_view, profile_view

app_name = "users_web"

urlpatterns = [
    path("login/", login_view, name="login"),
    path("register/", register_view, name="register"),
    path("profile/", profile_view, name="profile"),
    path("logout/", LogoutView.as_view, {"next_page": "/"}, name="logout"),
]