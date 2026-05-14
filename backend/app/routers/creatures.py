from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.auth import CurrentUser, require_role
from app.db import SessionDep
from app.models import CreatureCreate, CreatureRead
from app.services import creatures as service
from app.services import lore as lore_service

router = APIRouter(prefix="/creatures", tags=["creatures"])

_admin = Depends(require_role("admin"))


@router.post("/", response_model=CreatureRead, dependencies=[_admin])
async def create_creature_endpoint(
    creature: CreatureCreate,
    session: SessionDep,
    request: Request,
    current_user: CurrentUser,
) -> CreatureRead:
    db_creature = service.create_creature(session, creature, current_user.id)
    try:
        arq = getattr(request.app.state, "arq", None)
        if arq:
            await arq.enqueue_job("generate_creature_lore_task", db_creature.id)
    except Exception:
        pass
    return db_creature


@router.get("/", response_model=list[CreatureRead])
def get_creatures_endpoint(
    session: SessionDep, current_user: CurrentUser
) -> list[CreatureRead]:
    return service.list_creatures(session, current_user.id)


@router.get("/export/csv")
def export_creatures_csv_endpoint(
    session: SessionDep, current_user: CurrentUser
) -> StreamingResponse:
    csv_content = service.export_creatures_csv(session, current_user.id)
    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=creatures.csv"},
    )


@router.get("/{creature_id}", response_model=CreatureRead)
def get_creature_endpoint(
    creature_id: int, session: SessionDep, current_user: CurrentUser
) -> CreatureRead:
    return service.get_creature(session, creature_id, current_user.id)


@router.put("/{creature_id}", response_model=CreatureRead, dependencies=[_admin])
def update_creature_endpoint(
    creature_id: int,
    creature: CreatureCreate,
    session: SessionDep,
    current_user: CurrentUser,
) -> CreatureRead:
    return service.update_creature(session, creature_id, creature, current_user.id)


@router.delete("/{creature_id}", dependencies=[_admin])
def delete_creature_endpoint(
    creature_id: int, session: SessionDep, current_user: CurrentUser
) -> dict:
    service.delete_creature(session, creature_id, current_user.id)
    return {"detail": "creature deleted successfully"}


@router.post("/{creature_id}/lore")
def generate_lore_endpoint(
    creature_id: int, session: SessionDep, current_user: CurrentUser
) -> dict:
    creature = service.get_creature(session, creature_id, current_user.id)
    lore = lore_service.generate_lore(
        creature.name, creature.mythology, creature.creature_type
    )
    return {"lore": lore}
