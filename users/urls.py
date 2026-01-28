from django.contrib.auth.views import (
    LogoutView,
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)
from django.urls import path, reverse_lazy

from users.forms.password_reset_form import CustomPasswordResetForm, CustomSetPasswordForm
from users.views.feedback import FeedbackView
from users.views.manager import ManagerUsersView, ManagerUserDataView, ManagerUserFilmsView, ManagerUserReviewsView, \
    ManagerUserCalendarView, BlockUserView, UnblockUserView, ManagerUserOverviewView
from users.views.users_views import (
    ActivateAccountView,
    ActivationErrorView,
    ActivationSentView,
    ConfirmEmailView,
    RegisterView,
    ResendActivationView,
    UserLoginView,
    UserProfileView)


app_name = "users"

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("activation-sent/", ActivationSentView.as_view(), name="activation_sent"),
    path("activation/error/", ActivationErrorView.as_view(), name="activation_error"),
    path("activate/<int:user_id>/<str:token>/", ActivateAccountView.as_view(), name="activate"),
    path("resend/", ResendActivationView.as_view(), name="resend_activation"),
    path("login/", UserLoginView.as_view(), name="login"),
    path("profile/", UserProfileView.as_view(), name="profile"),
    path(
        "confirm-email/<int:user_id>/<str:token>/",
        ConfirmEmailView.as_view(),
        name="confirm_email",
    ),
    path("logout/", LogoutView.as_view(), name="logout"),
    path(
        "password_reset/",
        PasswordResetView.as_view(
            template_name="users/password_reset_form.html",
            form_class=CustomPasswordResetForm,
            email_template_name="users/password_reset_email.txt",
            html_email_template_name="users/password_reset_email.html",
            subject_template_name="users/password_reset_subject.txt",
            success_url=reverse_lazy("users:password_reset_done"),
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
    path("feedback/", FeedbackView.as_view(), name="feedback"),
    path("panel/users/", ManagerUsersView.as_view(), name="manager_users"),
    path("panel/users/<int:user_id>/block/", BlockUserView.as_view(), name="manager_user_block"),
    path("panel/users/<int:user_id>/unblock/", UnblockUserView.as_view(), name="manager_user_unblock"),
    path("panel/users/<int:user_id>/", ManagerUserOverviewView.as_view(), name="manager_user_overview"),
    path("panel/users/<int:user_id>/films/", ManagerUserFilmsView.as_view(), name="manager_user_films"),
    path("panel/users/<int:user_id>/reviews/", ManagerUserReviewsView.as_view(), name="manager_user_reviews"),
    path("panel/users/<int:user_id>/calendar/", ManagerUserCalendarView.as_view(), name="manager_user_calendar"),
]
