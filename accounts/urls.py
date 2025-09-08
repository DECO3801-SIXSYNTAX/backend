from django.urls import path
from .views import me
from .views_firebase import firebase_login
urlpatterns = [ path('me/', me), path('firebase/', firebase_login) ]
