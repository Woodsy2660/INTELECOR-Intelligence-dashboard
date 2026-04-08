from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from db.base import get_db

security = HTTPBearer(auto_error=False)


async def get_current_tenant(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> str:
    """
    Extract tenant_id from the authenticated user's JWT.

    For MVP: returns a hardcoded tenant ID.
    Production: decode JWT, look up user's organisation, return tenant_id.
    """
    # MVP: skip auth, return default tenant
    # TODO: implement JWT decode via fastapi-users when auth is added
    return "tnt_roycardiology_001"


async def get_session(session: AsyncSession = Depends(get_db)) -> AsyncSession:
    """Provide a database session to route handlers."""
    return session
