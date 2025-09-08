from django.urls import path
from .views import me
from .views_firebase import firebase_login

urlpatterns = [
    path('firebase/', firebase_login),
    path('me/', me),
]
