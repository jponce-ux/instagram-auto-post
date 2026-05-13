"""Token generation and validation for email verification.

Uses python-jose (already installed) to create JWT tokens with
a 20-minute expiration. Tokens contain the user_id, email, and
a type claim to prevent reuse with other token types.
"""

from datetime import datetime, timedelta, timezone

from jose import JWTError, ExpiredSignatureError, jwt

from app.core.config import settings

VERIFICATION_TOKEN_EXPIRE_MINUTES = 20


def create_verification_token(user_id: int, email: str) -> str:
    """
    Generate a JWT verification token for email confirmation.

    The token expires in 20 minutes and contains the user_id,
    email, and a type claim for validation.

    Args:
        user_id: The user's database ID
        email: The user's email address

    Returns:
        Encoded JWT token string
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=VERIFICATION_TOKEN_EXPIRE_MINUTES)
    to_encode = {
        "sub": str(user_id),
        "email": email,
        "type": "email_verification",
        "exp": expire,
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")


def decode_verification_token(token: str) -> dict | None:
    """
    Decode and validate an email verification token.

    Returns None if the token is expired, invalid, or not an
    email verification token.

    Args:
        token: The JWT token string to decode

    Returns:
        Decoded payload dict with 'sub' (user_id) and 'email',
        or None if invalid/expired
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        if payload.get("type") != "email_verification":
            return None
        return payload
    except (ExpiredSignatureError, JWTError):
        return None
