"""Browser-held, high-entropy capabilities for private, expiring character drafts."""
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import re
import secrets

from .auth import AuthError, Principal


@dataclass(frozen=True)
class DraftAccess:
    token_hash: str


def token_hash(token: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{64}", token):
        raise AuthError(401, "invalid draft key")
    return sha256(token.encode()).hexdigest()


def permits(row, access: Principal | DraftAccess) -> bool:
    if isinstance(access, DraftAccess):
        return (row["owner_sub"] is None
                and row["draft_expires_at"] > datetime.now(timezone.utc)
                and secrets.compare_digest(row["draft_token_hash"], access.token_hash))
    return row["owner_sub"] == access.sub or "admin:slots" in access.scopes
