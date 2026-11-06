from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime, timedelta
import secrets

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    verify_token,
    get_current_user,
    get_current_active_user,
    require_role,
    verify_csrf_token,
)
from app.core.oidc import oidc_client
from app.models import User, AuditLog

router = APIRouter(prefix="/auth", tags=["auth"])

settings = get_settings()


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    email: Optional[str] = None


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None


class UserRead(BaseModel):
    id: int
    email: str
    full_name: Optional[str] = None
    is_active: bool
    is_superuser: bool
    role: str
    created_at: datetime

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    password: Optional[str] = None


class OIDCLoginRequest(BaseModel):
    redirect_uri: str


class OIDCCallbackRequest(BaseModel):
    code: str
    redirect_uri: str
    state: str


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
    _csrf: bool = Depends(verify_csrf_token),
):
    # Check if user exists
    result = await db.execute(select(User).where(User.email == user_data.email))
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create user (password hashing would go here in production)
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    hashed_password = pwd_context.hash(user_data.password)

    user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        role="viewer",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Audit log
    audit = AuditLog(
        user_id=user.id,
        action="register",
        resource_type="user",
        resource_id=str(user.id),
        details=f"User registered: {user.email}",
    )
    db.add(audit)
    await db.commit()

    return user


@router.post("/login", response_model=Token)
async def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
    _csrf: bool = Depends(verify_csrf_token),
):
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()
    if not user or not user.hashed_password or not pwd_context.verify(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )

    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "role": user.role},
        expires_delta=access_token_expires,
    )

    # Set HttpOnly cookie
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=settings.environment == "production",
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
    )

    # Audit log
    audit = AuditLog(
        user_id=user.id,
        action="login",
        resource_type="session",
        resource_id=str(user.id),
        details=f"User logged in: {user.email}",
    )
    db.add(audit)
    await db.commit()

    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/logout")
async def logout(
    response: Response,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _csrf: bool = Depends(verify_csrf_token),
):
    response.delete_cookie(key="access_token", httponly=True, secure=settings.environment == "production", samesite="lax")

    audit = AuditLog(
        user_id=current_user.id,
        action="logout",
        resource_type="session",
        resource_id=str(current_user.id),
        details=f"User logged out: {current_user.email}",
    )
    db.add(audit)
    await db.commit()

    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserRead)
async def read_me(current_user: User = Depends(get_current_active_user)):
    return current_user


@router.patch("/me", response_model=UserRead)
async def update_me(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    _csrf: bool = Depends(verify_csrf_token),
):
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    if user_update.full_name is not None:
        current_user.full_name = user_update.full_name
    if user_update.password is not None:
        current_user.hashed_password = pwd_context.hash(user_update.password)

    current_user.updated_at = None  # Will be set by DB onupdate
    await db.commit()
    await db.refresh(current_user)

    return current_user


# OIDC/Keycloak endpoints
@router.get("/oidc/login")
async def oidc_login(redirect_uri: str):
    """Initiate OIDC login flow with Keycloak."""
    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    auth_url = oidc_client.get_auth_url(redirect_uri, state, nonce)
    return {"auth_url": auth_url, "state": state, "nonce": nonce}


@router.post("/oidc/callback")
async def oidc_callback(
    response: Response,
    callback_data: OIDCCallbackRequest,
    db: AsyncSession = Depends(get_db),
    _csrf: bool = Depends(verify_csrf_token),
):
    """Handle OIDC callback from Keycloak."""
    # Exchange code for tokens
    tokens = await oidc_client.exchange_code_for_tokens(
        callback_data.code,
        callback_data.redirect_uri,
    )

    # Verify ID token
    id_token = tokens.get("id_token")
    if not id_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No ID token in response",
        )

    payload = await oidc_client.verify_id_token(id_token)

    # Get user info
    userinfo = await oidc_client.get_userinfo(tokens["access_token"])

    # Find or create user
    email = userinfo.get("email") or payload.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email not found in token",
        )

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user:
        # Create new user from Keycloak
        user = User(
            email=email,
            full_name=userinfo.get("name") or userinfo.get("preferred_username"),
            role="viewer",
            is_active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    elif not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )

    # Create session token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "role": user.role},
        expires_delta=access_token_expires,
    )

    # Set HttpOnly cookie
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=settings.environment == "production",
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
    )

    # Audit log
    audit = AuditLog(
        user_id=user.id,
        action="oidc_login",
        resource_type="session",
        resource_id=str(user.id),
        details=f"User logged in via OIDC: {user.email}",
    )
    db.add(audit)
    await db.commit()

    return {"access_token": access_token, "token_type": "bearer", "user": user}


@router.get("/oidc/logout")
async def oidc_logout(redirect_uri: str):
    """Get Keycloak logout URL."""
    logout_url = oidc_client.get_logout_url(redirect_uri)
    return {"logout_url": logout_url}


@router.get("/oidc/config")
async def oidc_config():
    """Get OIDC configuration for frontend."""
    return {
        "keycloak_url": settings.keycloak_url,
        "realm": settings.keycloak_realm,
        "client_id": settings.keycloak_client_id,
        "auth_url": oidc_client.auth_url,
        "token_url": oidc_client.token_url,
    }

