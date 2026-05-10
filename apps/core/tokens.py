from django.core import signing

VERIFICATION_TOKEN_MAX_AGE = 60 * 60 * 24


def generate_verification_token(user_id):
    payload = {
        "user_id": user_id,
        "purpose": "email_verification",
    }
    return signing.dumps(payload)


def decode_verification_token(token: str) -> str:
    """
    Returns user_id string on success.
    """
    payload = signing.loads(token, max_age=VERIFICATION_TOKEN_MAX_AGE)

    if payload.get("purpose") != "email_verification":
        raise signing.BadSignature("Invalid token purpose")

    return payload["user_id"]
