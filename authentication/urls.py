
from django.urls import path
from .views import register, login, logout, password_reset, password_reset_confirm, GoogleLoginView

urlpatterns = [
    path("register/", register, name="register"),
    path("login/",    login,    name="login"),
    path("logout/",   logout,   name="logout"),
    path("password-reset/", password_reset, name="password-reset"),
    path("password-reset-confirm/", password_reset_confirm, name="password-reset-confirm"),
    path("google/", GoogleLoginView.as_view(), name="auth_google"),
]
