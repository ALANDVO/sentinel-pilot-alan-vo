from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from pydantic import BaseModel, HttpUrl
from typing import Optional, List
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_active_user, require_role
from app.models import Instance, Mod, User

router = APIRouter(prefix="/instances", tags=["instances"])


class InstanceBase(BaseModel):
    name: str
    minecraft_version: str
    loader: Optional[str] = None
    loader_version: Optional[str] = None
    java_path: Optional[str] = None
    jvm_args: Optional[str] = None
    memory_min: Optional[str] = None
    memory_max: Optional[str] = None
    game_dir: Optional[str] = None
    icon_path: Optional[str] = None
    description: Optional[str] = None


class InstanceCreate(InstanceBase):
    pass


class InstanceUpdate(BaseModel):
    name: Optional[str] = None
    minecraft_version: Optional[str] = None
    loader: Optional[str] = None
    loader_version: Optional[str] = None
    java_path: Optional[str] = None
    jvm_args: Optional[str] = None
    memory_min: Optional[str] = None
    memory_max: Optional[str] = None
    game_dir: Optional[str] = None
    icon_path: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class InstanceRead(InstanceBase):
    id: int
    is_active: bool
    owner_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    mods_count: int = 0

    class Config:
        from_attributes = True


class InstanceListResponse(BaseModel):
    items: List[InstanceRead]
    total: int
    page: int
    page_size: int
    total_pages: int


@router.post("", response_model=InstanceRead, status_code=status.HTTP_201_CREATED)
async def create_instance(
    instance_data: InstanceCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    instance = Instance(**instance_data.model_dump(), owner_id=current_user.id)
    db.add(instance)
    await db.commit()
    await db.refresh(instance)
    return instance


@router.get("", response_model=InstanceListResponse)
async def list_instances(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    loader: Optional[str] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Instance).where(Instance.owner_id == current_user.id)

    if search:
        query = query.where(Instance.name.ilike(f"%{search}%"))
    if loader:
        query = query.where(Instance.loader == loader)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()

    # Apply pagination
    query = query.order_by(Instance.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    instances = result.scalars().all()

    # Get mods count for each instance
    instance_ids = [i.id for i in instances]
    mods_count = {}
    if instance_ids:
        mods_result = await db.execute(
            select(Mod.instance_id, func.count(Mod.id))
            .where(Mod.instance_id.in_(instance_ids))
            .group_by(Mod.instance_id)
        )
        mods_count = {row[0]: row[1] for row in mods_result.all()}

    items = []
    for instance in instances:
        item = InstanceRead.model_validate(instance)
        item.mods_count = mods_count.get(instance.id, 0)
        items.append(item)

    return InstanceListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/{instance_id}", response_model=InstanceRead)
async def get_instance(
    instance_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Instance).where(Instance.id == instance_id, Instance.owner_id == current_user.id)
    )
    instance = result.scalar_one_or_none()
    if not instance:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instance not found")

    mods_result = await db.execute(select(func.count(Mod.id)).where(Mod.instance_id == instance_id))
    mods_count = mods_result.scalar() or 0

    item = InstanceRead.model_validate(instance)
    item.mods_count = mods_count
    return item


@router.patch("/{instance_id}", response_model=InstanceRead)
async def update_instance(
    instance_id: int,
    instance_update: InstanceUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Instance).where(Instance.id == instance_id, Instance.owner_id == current_user.id)
    )
    instance = result.scalar_one_or_none()
    if not instance:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instance not found")

    update_data = instance_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(instance, field, value)

    await db.commit()
    await db.refresh(instance)
    return instance


@router.delete("/{instance_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_instance(
    instance_id: int,
    current_user: User = Depends(require_role("operator", "admin")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Instance).where(Instance.id == instance_id, Instance.owner_id == current_user.id)
    )
    instance = result.scalar_one_or_none()
    if not instance:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instance not found")

    await db.delete(instance)
    await db.commit()