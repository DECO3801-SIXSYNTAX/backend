import json, os
import firebase_admin
from firebase_admin import credentials, auth as fb_auth
_initialized = False
def init_firebase_if_needed(service_account_json_env: str):
    global _initialized
    if _initialized: return
    if not firebase_admin._apps:
        if not service_account_json_env: return
        try:
            if os.path.exists(service_account_json_env):
                cred = credentials.Certificate(service_account_json_env)
            else:
                data = json.loads(service_account_json_env)
                cred = credentials.Certificate(data)
            firebase_admin.initialize_app(cred)
        except Exception:
            return
    _initialized = True
