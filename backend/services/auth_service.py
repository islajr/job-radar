import bcrypt
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from backend.config import settings

_serializer = URLSafeTimedSerializer(settings.secret_key)

def hash_password(plain: str) -> str:
    pwd_bytes = plain.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode('utf-8')

def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))
    except Exception:
        return False

def create_session_token(user_id: str) -> str:
    return _serializer.dumps(user_id, salt="session")

def decode_session_token(token: str) -> str | None:
    """Returns user_id string, or None if invalid/expired."""
    try:
        return _serializer.loads(
            token,
            salt="session",
            max_age=settings.session_max_age_seconds
        )
    except (BadSignature, SignatureExpired):
        return None
