from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.views import LoginView
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView
from django.views.generic.edit import FormView

from users.forms.profile_form import UserProfileForm, UserPasswordForm
from users.forms.register_form import RegisterForm
from users.forms.authentication_form import CustomAuthenticationForm
from users.tasks import send_activation_email_task


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
        self.request.session["resend_user_id"] = user.pk  # Сохраняем user_id в сессии для повторной отправки письма
        self.send_activation_email(user)
        return super().form_valid(form)

    def send_activation_email(self, user):
        """Отправляет email пользователю для подтверждения регистрации"""
        token = default_token_generator.make_token(user)
        activation_url = self.request.build_absolute_uri(
            reverse("users:activate", kwargs={"user_id": user.pk, "token": token})
        )

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
        User = get_user_model()
        user = get_object_or_404(User, pk=user_id)

        if user.is_active:
            messages.info(request, "Аккаунт уже активирован")
            return redirect("users:login")

        if default_token_generator.check_token(user, token):
            user.is_active = True
            user.save()
            messages.success(request, "Аккаунт успешно активирован!")
            request.session.pop("resend_user_id", None)
            return redirect("users:login")

        messages.error(request, "Неверная или устаревшая ссылка активации аккаунта")
        return redirect("users:activation_sent")


class ResendActivationView(View):
    """Повторная попытка активации аккаунта"""

    def post(self, request):
        """
        Получает user_id из сессии. Если аккаунт пользователя не активирован,
        отправляет повторное письмо для активации (не чаще одного паза в две минуты)
        """
        user_id = request.session.get("resend_user_id")
        if not user_id:
            messages.error(request, "Мы не смогли определить ваш аккаунт. Попробуйте зарегистрироваться заново")
            return redirect("users:activation_sent")

        User = get_user_model()
        user = User.objects.get(pk=user_id)
        if not user:
            messages.error(request, "Мы не смогли определить ваш аккаунт. Попробуйте зарегистрироваться заново")
            return redirect("users:activation_sent")

        if user.is_active:
            messages.info(request, "Ваш аккаунт уже активирован")
            return redirect("users:login")

        last = request.session.get("last_resend")
        now = timezone.now().timestamp()
        if last and now - last < 120:
            messages.error(request, "Попробуйте снова через 2 минуты")
            return redirect("users:activation_sent")
        request.session["last_resend"] = now

        token = default_token_generator.make_token(user)
        activation_url = request.build_absolute_uri(
            reverse("users:activate", kwargs={"user_id": user.pk, "token": token})
        )

        send_activation_email_task.delay(
            user_id=user.pk,
            email=user.email,
            activation_url=activation_url,
        )

        messages.success(request, "Письмо отправлено повторно!")
        return redirect("users:activation_sent")


class UserLoginView(SuccessMessageMixin, LoginView):
    """Авторизация пользователя"""

    authentication_form = CustomAuthenticationForm
    template_name = "users/login.html"
    success_message = "Вы успешно вошли!"
    redirect_authenticated_user = True

    def form_valid(self, form: CustomAuthenticationForm):
        """
        Если аккаунт не активирован, перенаправляет на страницу активации.
        При успешной валидации логина(email) и пароля сообщение о входе в аккаунт
        """
        user = form.get_user()
        if not user.is_active:
            self.request.session["resend_user_id"] = user.pk
            messages.warning(
                self.request,
                "Ваш аккаунт не активирован. Проверьте почту или запросите письмо повторно"
            )
            return redirect("users:activation_sent")

        messages.success(self.request, self.success_message)
        return super().form_valid(form)

    def get_success_url(self):
        """При входе в аккаунт перенаправляет в личный кабинет пользователя"""
        return reverse_lazy("users:profile")


class UserProfileView(LoginRequiredMixin, TemplateView):
    """Профиль пользователя"""

    template_name = "users/profile.html"

    def get_context_data(self, **kwargs):
        """Добавляет формы для личных данных и смены пароля в контекст"""
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context["profile_form"] = kwargs.get("profile_form") or UserProfileForm(instance=user)
        context["password_form"] = kwargs.get("password_form") or UserPasswordForm(user=user)
        return context

    def post(self, request, *args, **kwargs):
        """Обновляет данные пользователя"""
        user = request.user

        if "save_profile" in request.POST:
            profile_form = UserProfileForm(request.POST, request.FILES, instance=user)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, "Профиль успешно обновлён")
                return redirect("users:account")
            return self.render_to_response(self.get_context_data(profile_form=profile_form))

        elif "change_password" in request.POST:
            password_form = UserPasswordForm(user=request.user, data=request.POST)
            if password_form.is_valid():
                password_form.save()
                messages.success(request, "Профиль успешно обновлён")
                update_session_auth_hash(request, password_form.user)
                return redirect("users:account")
            return self.render_to_response(self.get_context_data(password_form=password_form))

        return self.get(request, *args, **kwargs)
