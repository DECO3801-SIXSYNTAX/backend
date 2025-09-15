from django.urls import path
from .views import register, login, logout, GoogleLoginView

urlpatterns = [
    path("register/", register, name="register"),
    path("login/",    login,    name="login"),
    path("logout/",   logout,   name="logout"),
    path("google/", GoogleLoginView.as_view(), name="auth_google"),
    
]
