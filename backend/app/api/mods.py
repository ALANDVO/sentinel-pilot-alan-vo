from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import hashlib
import os

from app.core.database import get_db
from app.core.security import get_current_active_user, require_role
from app.models import Mod, Instance, User

router = APIRouter(prefix="/mods", tags=["mods"])


class ModBase(BaseModel):
    name: str
    version: str
    filename: str
    file_path: str
    file_hash: Optional[str] = None
    source: Optional[str] = None
    source_url: Optional[str] = None
    description: Optional[str] = None


class ModCreate(ModBase):
    instance_id: int
    is_enabled: bool = True


class ModUpdate(BaseModel):
    name: Optional[str] = None
    version: Optional[str] = None
    description: Optional[str] = None
    is_enabled: Optional[bool] = None


class ModRead(ModBase):
    id: int
    instance_id: int
    is_enabled: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ModListResponse(BaseModel):
    items: List[ModRead]
    total: int
    page: int
    page_size: int
    total_pages: int


def compute_file_hash(file_path: str) -> str:
    """Compute SHA256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


@router.post("", response_model=ModRead, status_code=status.HTTP_201_CREATED)
async def create_mod(
    mod_data: ModCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify instance ownership
    result = await db.execute(
        select(Instance).where(Instance.id == mod_data.instance_id, Instance.owner_id == current_user.id)
    )
    instance = result.scalar_one_or_none()
    if not instance:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instance not found")

    mod = Mod(**mod_data.model_dump())
    db.add(mod)
    await db.commit()
    await db.refresh(mod)
    return mod


@router.get("", response_model=ModListResponse)
async def list_mods(
    instance_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    enabled_only: bool = Query(False),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Mod).join(Instance).where(Instance.owner_id == current_user.id)

    if instance_id:
        query = query.where(Mod.instance_id == instance_id)
    if enabled_only:
        query = query.where(Mod.is_enabled == True)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()

    query = query.order_by(Mod.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    mods = result.scalars().all()

    return ModListResponse(
        items=[ModRead.model_validate(m) for m in mods],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/{mod_id}", response_model=ModRead)
async def get_mod(
    mod_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Mod).join(Instance).where(Mod.id == mod_id, Instance.owner_id == current_user.id)
    )
    mod = result.scalar_one_or_none()
    if not mod:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mod not found")
    return mod


@router.patch("/{mod_id}", response_model=ModRead)
async def update_mod(
    mod_id: int,
    mod_update: ModUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Mod).join(Instance).where(Mod.id == mod_id, Instance.owner_id == current_user.id)
    )
    mod = result.scalar_one_or_none()
    if not mod:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mod not found")

    update_data = mod_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(mod, field, value)

    await db.commit()
    await db.refresh(mod)
    return mod


@router.delete("/{mod_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mod(
    mod_id: int,
    current_user: User = Depends(require_role("operator", "admin")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Mod).join(Instance).where(Mod.id == mod_id, Instance.owner_id == current_user.id)
    )
    mod = result.scalar_one_or_none()
    if not mod:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mod not found")

    # Delete file if it exists
    if os.path.exists(mod.file_path):
        try:
            os.remove(mod.file_path)
        except OSError:
            pass  # Log in production

    await db.delete(mod)
    await db.commit()


@router.post("/upload", response_model=ModRead, status_code=status.HTTP_201_CREATED)
async def upload_mod(
    instance_id: int = Query(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify instance ownership
    result = await db.execute(
        select(Instance).where(Instance.id == instance_id, Instance.owner_id == current_user.id)
    )
    instance = result.scalar_one_or_none()
    if not instance:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instance not found")

    # Save file
    upload_dir = f"./uploads/mods/{instance_id}"
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, file.filename)
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    file_hash = compute_file_hash(file_path)

    # Check if mod with same hash already exists for this instance
    existing = await db.execute(
        select(Mod).where(Mod.instance_id == instance_id, Mod.file_hash == file_hash)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Mod already exists")

    mod = Mod(
        instance_id=instance_id,
        name=file.filename.replace(".jar", ""),
        version="1.0.0",
        filename=file.filename,
        file_path=file_path,
        file_hash=file_hash,
        source="local",
        is_enabled=True,
    )
    db.add(mod)
    await db.commit()
    await db.refresh(mod)
    return mod