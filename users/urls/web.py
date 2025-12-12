from django.contrib.auth.views import LogoutView
from django.urls import path
from users.views.web import RegisterView, ActivateAccountView, ResendActivationView, UserLoginView, UserProfileView

app_name = "users_web"

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("activation-sent/", ActivationSentView.as_view(), name="activation_sent"),
    path("activate/<int:user_id>/<str:token>/", ActivateAccountView.as_view(), name="activate"),
    path("resend/", ResendActivationView.as_view(), name="resend_activation"),
    path("login/", UserLoginView.as_view(), name="login"),
    path("profile/", UserProfileView.as_view(), name="profile"),
    path("logout/", LogoutView.as_view(next_page="users_web:login"), {"next_page": "/"}, name="logout"),

]