from fastapi import APIRouter, Depends

from app.auth import require_role
from app.db import SessionDep
from app.models import CreatureCreate, CreatureRead
from app.services import creatures as service
from app.services import lore as lore_service

router = APIRouter(prefix="/creatures", tags=["creatures"])

_admin = Depends(require_role("admin"))


@router.post("/", response_model=CreatureRead, dependencies=[_admin])
def create_creature_endpoint(
    creature: CreatureCreate, session: SessionDep
) -> CreatureRead:
    return service.create_creature(session, creature)


@router.get("/", response_model=list[CreatureRead])
def get_creatures_endpoint(session: SessionDep) -> list[CreatureRead]:
    return service.list_creatures(session)


@router.get("/{creature_id}", response_model=CreatureRead)
def get_creature_endpoint(creature_id: int, session: SessionDep) -> CreatureRead:
    return service.get_creature(session, creature_id)


@router.put("/{creature_id}", response_model=CreatureRead, dependencies=[_admin])
def update_creature_endpoint(
    creature_id: int, creature: CreatureCreate, session: SessionDep
) -> CreatureRead:
    return service.update_creature(session, creature_id, creature)


@router.delete("/{creature_id}", dependencies=[_admin])
def delete_creature_endpoint(creature_id: int, session: SessionDep) -> dict:
    service.delete_creature(session, creature_id)
    return {"detail": "creature deleted successfully"}


@router.post("/{creature_id}/lore")
def generate_lore_endpoint(creature_id: int, session: SessionDep) -> dict:
    creature = service.get_creature(session, creature_id)
    lore = lore_service.generate_lore(
        creature.name, creature.mythology, creature.creature_type
    )
    return {"lore": lore}
