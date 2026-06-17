from passlib.context import CryptContext
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from backend.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
_serializer = URLSafeTimedSerializer(settings.secret_key)

def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

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
