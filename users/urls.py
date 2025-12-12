from django.contrib.auth.views import LogoutView, PasswordResetView, PasswordResetDoneView, PasswordResetConfirmView, \
    PasswordResetCompleteView
from django.urls import path, reverse_lazy

from users.forms.password_reset_form import CustomPasswordResetForm, CustomSetPasswordForm
from users.views import RegisterView, ActivateAccountView, ResendActivationView, UserLoginView, UserProfileView, \
    ActivationSentView

app_name = "users_web"

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("activation-sent/", ActivationSentView.as_view(), name="activation_sent"),
    path("activate/<int:user_id>/<str:token>/", ActivateAccountView.as_view(), name="activate"),
    path("resend/", ResendActivationView.as_view(), name="resend_activation"),
    path("login/", UserLoginView.as_view(), name="login"),
    path("profile/", UserProfileView.as_view(), name="profile"),
    path("logout/", LogoutView.as_view(next_page="users_web:login"), {"next_page": "/"}, name="logout"),
    path(
        "password_reset/",
        PasswordResetView.as_view(
            template_name="users/password_reset_form.html",
            form_class=CustomPasswordResetForm,
            email_template_name="users/password_reset_email.html",
            subject_template_name="users/password_reset_subject.txt",
            success_url=reverse_lazy("users:password_reset_done"),
            extra_email_context={},
        ),
        name="password_reset",
    ),
    path(
        "password_reset_done/",
        PasswordResetDoneView.as_view(template_name="users/password_reset_done.html"),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        PasswordResetConfirmView.as_view(
            template_name="users/password_reset_confirm.html",
            form_class=CustomSetPasswordForm,
            success_url=reverse_lazy("users:password_reset_complete"),
        ),
        name="password_reset_confirm",
    ),
    path(
        "password_reset_complete/",
        PasswordResetCompleteView.as_view(template_name="users/password_reset_complete.html"),
        name="password_reset_complete",
    ),
]