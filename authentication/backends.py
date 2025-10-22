"""
Custom Authentication Backends for Firebase Integration
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import BaseBackend
from firebase_admin import auth as firebase_auth
from SiPanit.firebase import init_firebase
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

# Initialize Firebase on module load
try:
    init_firebase()
    print("✓ Firebase Admin SDK initialized successfully")
except Exception as e:
    print(f"✗ Firebase initialization failed: {e}")
    logger.error(f"Firebase initialization failed: {e}")


class FirebaseFallbackBackend(BaseBackend):
    """
    Custom authentication backend that authenticates against Firebase
    if user is not found in Django database.
    
    This backend is called AFTER ModelBackend, so it only runs if
    Django authentication failed.
    
    Flow:
    1. ModelBackend tries first (Django users)
    2. If ModelBackend fails, this backend is tried
    3. Authenticate against Firebase REST API
    4. If successful, auto-create user in Django
    5. Return authenticated user
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Authenticate against Firebase and auto-create Django user if successful
        """
        print(f"\n🔥 FirebaseFallbackBackend.authenticate() called")
        print(f"   Username: {username}")
        
        if not username or not password:
            print(f"   ✗ Missing username or password")
            return None
        
        # Try Firebase authentication
        firebase_user = self._authenticate_with_firebase(username, password)
        if firebase_user:
            print(f"   ✓ Firebase auth successful, returning user: {firebase_user.email}")
            return firebase_user
        
        print(f"   ✗ Firebase auth failed")
        return None
    
    def _authenticate_with_firebase(self, email, password):
        """
        Attempt to authenticate with Firebase and auto-create Django user
        
        Args:
            email: User's email address
            password: User's password
            
        Returns:
            User object if successful, None otherwise
        """
        print(f"🔥 Attempting Firebase authentication for: {email}")
        try:
            # Try to verify with Firebase (Note: Firebase Admin SDK doesn't support password verification)
            # We need to use Firebase Auth REST API for this
            import requests
            
            # Firebase Auth REST API endpoint
            FIREBASE_API_KEY = "AIzaSyCBPZiNYZL0W-Y6IfOO0ABpl8VJbXgjgq8"  # From your Firebase config
            url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"
            
            payload = {
                "email": email,
                "password": password,
                "returnSecureToken": True
            }
            
            print(f"  → Sending request to Firebase Auth API...")
            response = requests.post(url, json=payload, timeout=10)
            
            print(f"  → Firebase response status: {response.status_code}")
            
            if response.status_code == 200:
                # Firebase authentication successful!
                print(f"  ✓ Firebase authentication successful!")
                data = response.json()
                firebase_uid = data.get('localId')
                
                # Get user details from Firebase Admin SDK
                try:
                    print(f"  → Getting user details from Firebase Admin SDK...")
                    firebase_user = firebase_auth.get_user(firebase_uid)
                    print(f"  ✓ Got Firebase user: {firebase_user.email}")
                except Exception as e:
                    print(f"  ✗ Failed to get Firebase user details: {e}")
                    return None
                
                # Auto-create user in Django
                print(f"  → Creating Django user from Firebase data...")
                user = self._create_user_from_firebase(firebase_user, password)
                if user:
                    print(f"  ✓ Django user created successfully: {user.email}")
                return user
            else:
                error_data = response.json() if response.text else {}
                print(f"  ✗ Firebase auth failed: {error_data}")
                return None
            
        except Exception as e:
            print(f"  ✗ Firebase authentication error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _create_user_from_firebase(self, firebase_user, password):
        """
        Create Django user from Firebase user data
        
        Args:
            firebase_user: Firebase UserRecord object
            password: User's password (to set in Django)
            
        Returns:
            Django User object
        """
        email = firebase_user.email
        
        if not email:
            return None
        
        # Generate username from email
        username = email.split('@')[0]
        
        # Check if username exists, add number if needed
        original_username = username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{original_username}_{counter}"
            counter += 1
        
        # Parse name
        display_name = firebase_user.display_name or ""
        name_parts = display_name.split() if display_name else [email.split('@')[0]]
        first_name = name_parts[0] if name_parts else ""
        last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
        
        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,  # Set the password they just used
            first_name=first_name,
            last_name=last_name,
            role='planner',  # Default role
            is_active=True
        )
        
        print(f"✓ Auto-created Django user from Firebase: {email}")
        return user
