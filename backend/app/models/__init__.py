from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
from datetime import datetime


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=True)  # Nullable for OIDC users
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    role = Column(String(50), default="viewer")  # viewer, operator, admin
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    instances = relationship("Instance", back_populates="owner")
    audit_logs = relationship("AuditLog", back_populates="user")


class Instance(Base):
    __tablename__ = "instances"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    minecraft_version = Column(String(50), nullable=False)
    loader = Column(String(50), nullable=True)  # forge, fabric, quilt, vanilla
    loader_version = Column(String(50), nullable=True)
    java_path = Column(String(512), nullable=True)
    jvm_args = Column(Text, nullable=True)
    memory_min = Column(String(20), nullable=True)
    memory_max = Column(String(20), nullable=True)
    game_dir = Column(String(512), nullable=True)
    icon_path = Column(String(512), nullable=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    owner = relationship("User", back_populates="instances")
    mods = relationship("Mod", back_populates="instance", cascade="all, delete-orphan")


class Mod(Base):
    __tablename__ = "mods"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    version = Column(String(50), nullable=False)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_hash = Column(String(64), nullable=True)  # SHA256
    source = Column(String(50), nullable=True)  # curseforge, modrinth, local, url
    source_url = Column(String(512), nullable=True)
    description = Column(Text, nullable=True)
    is_enabled = Column(Boolean, default=True)
    instance_id = Column(Integer, ForeignKey("instances.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    instance = relationship("Instance", back_populates="mods")

    __table_args__ = (
        Index("ix_mods_instance_enabled", "instance_id", "is_enabled"),
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(50), nullable=False)
    resource_id = Column(String(100), nullable=True)
    details = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(512), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="audit_logs")

    __table_args__ = (
        Index("ix_audit_logs_user_created", "user_id", "created_at"),
        Index("ix_audit_logs_resource", "resource_type", "resource_id"),
    )