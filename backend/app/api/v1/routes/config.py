"""
config.py — Read-only configuration inspection route.

GET /config → returns operational knobs from config.yaml
"""

from fastapi import APIRouter
from app.config.loader import get_config

router = APIRouter(prefix="/config", tags=["Config"])


@router.get("")
def read_configuration():
    return get_config()
