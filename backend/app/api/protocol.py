from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Optional
import base64

router = APIRouter(prefix="/protocol", tags=["protocol"])


class MinecraftVersion(BaseModel):
    name: str
    protocol: int


class MinecraftPlayers(BaseModel):
    max: int
    online: int


class MinecraftDescription(BaseModel):
    text: str
    extra: Optional[list] = None


class ResourceResponse(BaseModel):
    version: MinecraftVersion
    players: MinecraftPlayers
    description: MinecraftDescription
    favicon: Optional[str] = None


@router.post("/status", response_model=ResourceResponse)
async def minecraft_resource_status(request: Request):
    """Handle Minecraft resource/status protocol request.

    The Minecraft protocol uses:
    1. Handshake packet (protocol version 1, state: status)
    2. Status request packet (JSON: {"id": ""})
    3. Response with server info

    This endpoint handles the status request phase, returning
    server resource information in the format Minecraft clients expect.
    """
    # Determine server info - in production this would query real server stats
    # For now, use configured/default values
    settings = request.app.state.settings

    # Build a basic Minecraft resource response
    # Minecraft clients expect specific format for resource packs/mods info
    version_name = f"1.{settings.protocol_version or 20}"

    # Try to decode favicon if configured, otherwise None
    favicon_b64 = getattr(settings, 'favicon_base64', None)
    favicon = favicon_b64

    return ResourceResponse(
        version=MinecraftVersion(
            name=version_name,
            protocol=int(settings.protocol_version or 20),
        ),
        players=MinecraftPlayers(
            max=getattr(settings, 'max_players', 20),
            online=getattr(settings, 'online_players', 0),
        ),
        description=MinecraftDescription(
            text=getattr(settings, 'motd', 'Sentinel Pilot'),
        ),
        favicon=favicon,
    )


@router.post("/ping", response_model=ResourceResponse)
async def minecraft_ping(request: Request):
    """Handle Minecraft ping protocol variant.

    Some clients use a simpler ping endpoint. Returns the same
    resource format as the status endpoint.
    """
    return await minecraft_resource_status(request)
