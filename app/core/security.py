"""密码散列与会话签名。

密码用标准库 PBKDF2-SHA256 加盐散列存储；会话用 itsdangerous 签名的 cookie 承载，
服务端只信任签名有效且未过期的 (用户 ID, 身份类别)，不在 cookie 里放任何凭据。
"""
import hashlib
import hmac
import os
import time
from typing import Optional

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from .config import SECRET_KEY, SESSION_EXPIRE

_ITERATIONS = 120_000
_signer = URLSafeTimedSerializer(SECRET_KEY)


# ---------------------------------------------------------------- 密码


def password_hash(plain: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", plain.encode("utf-8"), salt, _ITERATIONS)
    return f"pbkdf2_sha256${_ITERATIONS}${salt.hex()}${dk.hex()}"


def password_verify(plain: str, hashed: Optional[str]) -> bool:
    if not hashed or "$" not in hashed:
        return False
    try:
        algo, iterations, salt_hex, dk_hex = hashed.split("$")
        if algo != "pbkdf2_sha256":
            return False
        dk = hashlib.pbkdf2_hmac(
            "sha256", plain.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations)
        )
        return hmac.compare_digest(dk.hex(), dk_hex)
    except (ValueError, TypeError):
        return False


# ---------------------------------------------------------------- 会话


def make_session(user_id: int, category: str) -> str:
    """category: admin（管理员/教师）| student（学生）。"""
    return _signer.dumps({"uid": user_id, "cat": category})


def read_session(token: Optional[str], max_age: int = SESSION_EXPIRE):
    """返回 (user_id, category)，无效返回 None。"""
    if not token:
        return None
    try:
        data = _signer.loads(token, max_age=max_age)
    except (BadSignature, SignatureExpired):
        return None
    uid, cat = data.get("uid"), data.get("cat")
    if not uid or cat not in ("admin", "student"):
        return None
    return int(uid), cat


def now_ts() -> int:
    return int(time.time())
