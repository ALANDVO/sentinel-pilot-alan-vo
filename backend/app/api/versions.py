from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional
import httpx
import asyncio

router = APIRouter(prefix="/versions", tags=["versions"])


class MinecraftVersion(BaseModel):
    id: str
    type: str
    url: str
    time: str
    release_time: str = Field(alias="releaseTime", serialization_alias="releaseTime")

    class Config:
        populate_by_name = True
        serialize_by_alias = True


class MinecraftVersionManifest(BaseModel):
    latest: dict
    versions: List[MinecraftVersion]


class LoaderVersion(BaseModel):
    version: str
    stable: bool
    build: Optional[int] = None


class FabricVersionsResponse(BaseModel):
    game: List[LoaderVersion]
    loader: List[LoaderVersion]
    intermediary: List[LoaderVersion]
    mappings: List[LoaderVersion]
    installer: List[LoaderVersion]


# Cache for version data
_minecraft_versions_cache: Optional[MinecraftVersionManifest] = None
_fabric_versions_cache: Optional[FabricVersionsResponse] = None
_cache_timestamp = 0
CACHE_TTL = 3600  # 1 hour


async def fetch_minecraft_versions() -> MinecraftVersionManifest:
    global _minecraft_versions_cache, _cache_timestamp
    import time

    if _minecraft_versions_cache and (time.time() - _cache_timestamp) < CACHE_TTL:
        return _minecraft_versions_cache

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get("https://launchermeta.mojang.com/mc/game/version_manifest.json")
        response.raise_for_status()
        data = response.json()
        _minecraft_versions_cache = MinecraftVersionManifest(**data)
        _cache_timestamp = time.time()
        return _minecraft_versions_cache


async def fetch_fabric_versions() -> FabricVersionsResponse:
    global _fabric_versions_cache, _cache_timestamp
    import time

    if _fabric_versions_cache and (time.time() - _cache_timestamp) < CACHE_TTL:
        return _fabric_versions_cache

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get("https://meta.fabricmc.net/v2/versions")
        response.raise_for_status()
        data = response.json()
        _fabric_versions_cache = FabricVersionsResponse(**data)
        _cache_timestamp = time.time()
        return _fabric_versions_cache


@router.get("/minecraft", response_model=List[MinecraftVersion])
async def list_minecraft_versions(
    type_filter: Optional[str] = Query(None, description="Filter by type: release, snapshot, old_beta, old_alpha"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of versions to return"),
):
    """List available Minecraft versions from Mojang's version manifest."""
    manifest = await fetch_minecraft_versions()
    versions = manifest.versions

    if type_filter:
        versions = [v for v in versions if v.type == type_filter]

    return versions[:limit]


@router.get("/minecraft/latest", response_model=dict)
async def get_latest_minecraft_versions():
    """Get latest release and snapshot versions."""
    manifest = await fetch_minecraft_versions()
    return manifest.latest


@router.get("/fabric", response_model=List[LoaderVersion])
async def list_fabric_versions(
    game_version: Optional[str] = Query(None, description="Filter by Minecraft version"),
    loader_only: bool = Query(False, description="Return only loader versions"),
):
    """List available Fabric loader versions."""
    data = await fetch_fabric_versions()

    if loader_only:
        versions = data.loader
    elif game_version:
        game_versions = [v for v in data.game if v.version == game_version]
        if not game_versions:
            return []
        versions = data.loader
    else:
        versions = data.loader

    return versions


@router.get("/fabric/game", response_model=List[LoaderVersion])
async def list_fabric_game_versions():
    """List Minecraft versions supported by Fabric."""
    data = await fetch_fabric_versions()
    return data.game


@router.get("/forge")
async def list_forge_versions(
    game_version: Optional[str] = Query(None, description="Filter by Minecraft version"),
    limit: int = Query(50, ge=1, le=200),
):
    """List available Forge versions. Uses files.minecraftforge.net API."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            url = "https://files.minecraftforge.net/net/mavenforge/forge/maven-metadata.xml"
            response = await client.get(url)
            response.raise_for_status()
            return {"versions": [], "message": "Forge version listing not fully implemented - requires Maven metadata parsing"}
        except Exception:
            return {"versions": [], "message": "Could not fetch Forge versions"}


@router.get("/quilt")
async def list_quilt_versions(
    game_version: Optional[str] = Query(None, description="Filter by Minecraft version"),
    limit: int = Query(50, ge=1, le=200),
):
    """List available Quilt versions."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get("https://meta.quiltmc.org/v3/versions/game")
            response.raise_for_status()
            data = response.json()
            versions = [v["version"] for v in data]
            if game_version:
                versions = [v for v in versions if v == game_version]
            return {"versions": versions[:limit]}
        except Exception:
            return {"versions": [], "message": "Could not fetch Quilt versions"}


@router.get("/loaders/{loader}")
async def list_loader_versions(
    loader: str,
    game_version: Optional[str] = Query(None, description="Filter by Minecraft version"),
    limit: int = Query(50, ge=1, le=200),
):
    """Get loader versions for a specific mod loader (fabric, forge, quilt)."""
    loader = loader.lower()

    if loader == "fabric":
        data = await fetch_fabric_versions()
        versions = [v.version for v in data.loader]
        return {"loader": "fabric", "versions": versions[:limit]}
    elif loader == "forge":
        return await list_forge_versions(game_version, limit)
    elif loader == "quilt":
        return await list_quilt_versions(game_version, limit)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown loader: {loader}")
