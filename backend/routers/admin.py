"""Admin config router."""
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db, AdminConfig

router = APIRouter()


class ConfigItem(BaseModel):
    key: str
    value: str
    description: Optional[str] = None


class ConfigUpdate(BaseModel):
    configs: list[ConfigItem]


@router.get("/configs")
async def get_configs(db: Session = Depends(get_db)):
    configs = db.query(AdminConfig).all()
    return [
        {
            "id": c.id,
            "key": c.key,
            "value": c.value,
            "description": c.description,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        }
        for c in configs
    ]


@router.put("/configs")
async def update_configs(req: ConfigUpdate, db: Session = Depends(get_db)):
    for item in req.configs:
        config = db.query(AdminConfig).filter_by(key=item.key).first()
        if config:
            config.value = item.value
            if item.description:
                config.description = item.description
            config.updated_at = datetime.utcnow()
        else:
            db.add(AdminConfig(key=item.key, value=item.value, description=item.description))
    db.commit()
    return {"status": "saved", "count": len(req.configs)}


@router.post("/reset")
async def reset_configs(db: Session = Depends(get_db)):
    """Reset all configs to defaults."""
    from database import init_db
    init_db()
    return {"status": "reset"}
