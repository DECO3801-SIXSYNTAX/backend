# backend/authentication/firebase_auth.py
"""
Firebase Token Authentication for Django REST Framework

This authentication class allows Django to authenticate users using Firebase ID tokens.
Place this file in: backend/authentication/firebase_auth.py

Usage in settings.py:
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'authentication.firebase_auth.FirebaseAuthentication',
        ...
    ),
}
"""

from rest_framework import authentication
from rest_framework import exceptions
from django.contrib.auth import get_user_model
from firebase_admin import auth as firebase_auth
from SiPanit.firebase import init_firebase

User = get_user_model()

# Initialize Firebase (safe to call multiple times)
try:
    init_firebase()
    print("[OK] Firebase initialized successfully for authentication")
except Exception as e:
    print(f"[WARNING] Firebase initialization: {e}")


class FirebaseAuthentication(authentication.BaseAuthentication):
    """
    Firebase Token Authentication for Django REST Framework
    
    Accepts: Authorization: Bearer <firebase-id-token>
    
    Flow:
    1. Extract Firebase ID token from Authorization header
    2. Verify token with Firebase Admin SDK
    3. Get or create Django user from Firebase user data
    4. Return authenticated Django user
    """
    
    def authenticate(self, request):
        """
        Authenticate request using Firebase ID token
        
        Args:
            request: Django REST Framework request object
            
        Returns:
            tuple: (user, None) if authentication successful
            None: if this authenticator should be skipped
            
        Raises:
            AuthenticationFailed: if authentication fails
        """
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        
        # Skip if no Bearer token present
        if not auth_header.startswith('Bearer '):
            return None
        
        # Extract token from header
        id_token = auth_header.split('Bearer ')[1].strip()
        
        if not id_token:
            return None
        
        try:
            # Verify Firebase ID token using Firebase Admin SDK
            decoded_token = firebase_auth.verify_id_token(id_token)
            
            # Extract user information from token
            uid = decoded_token['uid']
            email = decoded_token.get('email', '')
            name = decoded_token.get('name', '')
            
            if not email:
                raise exceptions.AuthenticationFailed('Email not found in Firebase token')
            
            print(f"[OK] Firebase token verified for: {email}")
            
            # Get or create Django user using Firebase UID
            # This ensures Firebase UID matches Django user ID for event ownership
            try:
                # Try to get user by firebase_uid first, then email
                user = User.objects.filter(firebase_uid=uid).first()
                if not user:
                    user = User.objects.get(email=email)
                    # Update firebase_uid if user exists but doesn't have it set
                    if not user.firebase_uid:
                        user.firebase_uid = uid
                        user.save()
                created = False
                print(f"[OK] Found existing Django user: {email}")
            except User.DoesNotExist:
                # Create new user with Firebase UID stored in firebase_uid field
                user = User.objects.create(
                    firebase_uid=uid,  # Store Firebase UID in separate field
                    username=email.split('@')[0],
                    email=email,
                    first_name=name.split(' ')[0] if name else email.split('@')[0],
                    last_name=' '.join(name.split(' ')[1:]) if name and ' ' in name else '',
                    role='planner',  # Default role for new users
                    is_active=True,
                )
                # Set password to unusable since auth is via Firebase
                user.set_unusable_password()
                user.save()
                created = True
                print(f"[OK] Created new Django user with Firebase UID: {email} (Firebase UID: {uid})")
            
            if created:
                print(f"[OK] Auto-created Django user from Firebase: {email}")
            else:
                print(f"[OK] Found existing Django user: {email}")
            
            # Return user for authentication
            return (user, None)
            
        except firebase_auth.InvalidIdTokenError as e:
            print(f"[ERROR] Invalid Firebase token: {e}")
            raise exceptions.AuthenticationFailed(f'Invalid Firebase token: {str(e)}')
            
        except firebase_auth.ExpiredIdTokenError:
            print(f"[ERROR] Firebase token expired")
            raise exceptions.AuthenticationFailed('Firebase token has expired')
            
        except firebase_auth.RevokedIdTokenError:
            print(f"[ERROR] Firebase token revoked")
            raise exceptions.AuthenticationFailed('Firebase token has been revoked')
            
        except Exception as e:
            print(f"[ERROR] Firebase authentication error: {e}")
            import traceback
            traceback.print_exc()
            raise exceptions.AuthenticationFailed(f'Authentication failed: {str(e)}')
    
    def authenticate_header(self, request):
        """
        Return string to be used as the value of the WWW-Authenticate header
        in a 401 Unauthenticated response.
        """
        return 'Bearer realm="api"'