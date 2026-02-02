import logging

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.views import LoginView
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView
from django.views.generic.edit import FormView

from users.forms.authentication_form import CustomAuthenticationForm
from users.forms.profile_form import UserPasswordForm, UserProfileForm
from users.forms.register_form import RegisterForm
from users.forms.resend_activation_form import ResendActivationForm
from users.tasks import send_activation_email_task, send_confirm_email_task

logger = logging.getLogger("filmdiary.users")
User = get_user_model()


class RegisterView(SuccessMessageMixin, FormView):
    """Регистрация пользователя"""

    template_name = "users/register.html"
    form_class = RegisterForm
    success_url = reverse_lazy("users:activation_sent")

    def form_valid(self, form):
        """Валидирует и сохраняет данные пользователя без активации аккаунта"""
        user = form.save(commit=False)
        user.is_active = False
        user.save()

        logger.info("User REGISTER: user=%s email_sent=True", user.pk)

        self.request.session["resend_user_id"] = user.pk  # Сохраняем user_id в сессии для повторной отправки письма
        self.send_activation_email(user)
        return super().form_valid(form)

    def send_activation_email(self, user):
        """Отправляет email пользователю для подтверждения регистрации"""
        token = default_token_generator.make_token(user)
        activation_url = self.request.build_absolute_uri(
            reverse("users:activate", kwargs={"user_id": user.pk, "token": token})
        )

        logger.debug("User ACTIVATE email queued: user=%s", user.pk)
        send_activation_email_task.delay(
            user_id=user.pk,
            email=user.email,
            activation_url=activation_url,
        )


class ActivationSentView(TemplateView):
    """Вывод сообщения об отправке письма для активации аккаунта и повторной отправке"""

    template_name = "users/activation_sent.html"


class ActivateAccountView(View):
    """Активация аккаунта пользователя при регистрации"""

    def get(self, request, user_id, token):
        """Проверяет ссылку для активации аккаунта пользователя, активирует аккаунт"""
        user = get_object_or_404(User, pk=user_id)

        if user.is_blocked:
            messages.error(request, "Аккаунт заблокирован администратором. Напишите нам, мы сообщим, что делать")
            return redirect("users:activation_error")

        if user.is_active:
            logger.debug("User ACTIVATE: user=%s already active", user_id)
            messages.info(request, "Аккаунт уже активирован")
            return redirect("users:login")

        if default_token_generator.check_token(user, token):
            user.is_active = True
            user.save()
            logger.info("User ACTIVATE success: user=%s", user_id)
            messages.success(request, "Аккаунт успешно активирован!")
            request.session.pop("resend_user_id", None)
            return redirect("users:login")

        logger.warning("User ACTIVATE fail: user=%s invalid token", user_id)
        messages.error(request, "Неверная или устаревшая ссылка активации аккаунта")
        return redirect("users:activation_sent")


class ActivationErrorView(TemplateView):
    """Универсальная страница отображения errors"""

    template_name = "users/activation_error.html"


class ResendActivationView(FormView):
    """Повторная попытка активации аккаунта"""

    template_name = "users/resend_activation.html"
    form_class = ResendActivationForm

    def form_valid(self, form):
        """
        Если аккаунт пользователя не активирован,
        отправляет повторное письмо для активации (не чаще одного паза в две минуты)
        """
        user = form.user
        last = self.request.session.get(f"last_resend_{user.pk}")
        now = timezone.now().timestamp()
        if last and now - last < 120:
            messages.error(self.request, "Попробуйте снова через 2 минуты")
            return super().form_valid(form)
        self.request.session[f"last_resend_{user.pk}"] = now

        token = default_token_generator.make_token(user)
        activation_url = self.request.build_absolute_uri(
            reverse("users:activate", kwargs={"user_id": user.pk, "token": token})
        )

        send_activation_email_task.delay(
            user_id=user.pk,
            email=user.email,
            activation_url=activation_url,
        )

        messages.success(self.request, "Письмо отправлено повторно!")
        return redirect("users:activation_sent")


class UserLoginView(SuccessMessageMixin, LoginView):
    """Авторизация пользователя"""

    authentication_form = CustomAuthenticationForm
    template_name = "users/login.html"
    success_message = "Вы успешно вошли!"
    redirect_authenticated_user = True

    def get_success_url(self):
        """При входе в аккаунт перенаправляет в личный кабинет пользователя"""
        return reverse_lazy("users:profile")


class UserProfileView(LoginRequiredMixin, TemplateView):
    """Профиль пользователя"""

    template_name = "users/profile.html"

    def get_context_data(self, **kwargs):
        """Формирует контекст для профиля пользователя"""
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context["profile_form"] = kwargs.get("profile_form") or UserProfileForm(instance=user)
        context["password_form"] = kwargs.get("password_form") or UserPasswordForm(user=user)
        return context

    def post(self, request, *args, **kwargs):
        """
        Обновляет данные пользователя. Обновляет email:
        проверяет, менялся ли email, генерирует token, отправляет письмо
        """

        user = request.user
        profile_form = UserProfileForm(request.POST, request.FILES, instance=user)
        password_form = UserPasswordForm(user=user, data=request.POST)

        if request.POST.get("form_type") == "profile":
            if profile_form.is_valid():
                email_changed = "email" in profile_form.changed_data
                profile_form.save()

                if email_changed:
                    logger.info("User EMAIL change queued: user=%s new_email=True", user.pk)
                    token = default_token_generator.make_token(user)
                    confirm_url = request.build_absolute_uri(reverse("users:confirm_email", args=[user.pk, token]))

                    send_confirm_email_task.delay(
                        user_id=user.pk,
                        new_email=profile_form.cleaned_data["email"],
                        confirm_url=confirm_url,
                    )

                    messages.warning(request, "Мы отправили письмо для подтверждения нового email")

                logger.debug("User PROFILE updated: user=%s", user.pk)
                messages.success(request, "Профиль обновлён")
                return redirect("users:profile")

            return self.render_to_response(self.get_context_data(profile_form=profile_form))

        elif request.POST.get("form_type") == "password":
            if password_form.is_valid():
                password_form.save()
                messages.success(request, "Пароль успешно изменён")
                return redirect("users:profile")
            return self.render_to_response(self.get_context_data(password_form=password_form))

        return redirect("users:profile")


class ConfirmEmailView(View):
    """Класс для смены пользователем email"""

    def get(self, request, user_id, token):
        """Проверяет token, меняет email"""
        user = get_object_or_404(User, pk=user_id)

        if default_token_generator.check_token(user, token):
            user.email = user.email_new
            user.email_new = None
            user.email_confirmed = True
            user.save()

            messages.success(request, "Email успешно подтверждён")
            return redirect("users:profile")

        messages.error(request, "Ссылка недействительна")
        return redirect("users:profile")
