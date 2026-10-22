from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime, timedelta

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    verify_token,
    get_current_user,
    get_current_active_user,
    require_role,
)
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


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
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