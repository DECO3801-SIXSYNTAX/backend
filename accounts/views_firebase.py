from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from .firebase_auth import init_firebase_if_needed
try:
    from firebase_admin import auth as fb_auth
except Exception:
    fb_auth = None
User = get_user_model()
@api_view(['POST'])
@permission_classes([AllowAny])
def firebase_login(request):
    if fb_auth is None:
        return Response({'detail':'firebase-admin not installed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    id_token = request.data.get('idToken')
    if not id_token:
        return Response({'detail':'idToken is required'}, status=status.HTTP_400_BAD_REQUEST)
    init_firebase_if_needed(getattr(settings, 'FIREBASE_SERVICE_ACCOUNT_JSON', ''))
    try:
        decoded = fb_auth.verify_id_token(id_token)
    except Exception as e:
        return Response({'detail': f'Invalid Firebase ID token: {e}'}, status=status.HTTP_401_UNAUTHORIZED)
    email, uid = decoded.get('email'), decoded.get('uid')
    if not email and not uid:
        return Response({'detail':'Firebase token missing email/uid'}, status=status.HTTP_400_BAD_REQUEST)
    user, created = User.objects.get_or_create(username=email or uid, defaults={'email': email or ''})
    refresh = RefreshToken.for_user(user)
    return Response({'created': created,'user':{'id':str(user.id),'username':user.username,'email':user.email,'role':getattr(user,'role',None)},'refresh':str(refresh),'access':str(refresh.access_token)})
