import csv
import io
from datetime import datetime, timezone
from fastapi import HTTPException
from sqlmodel import Session, select
from app.models import Creature, CreatureCreate

_CSV_FIELDS = [
    "id",
    "name",
    "mythology",
    "creature_type",
    "danger_level",
    "habitat",
    "last_modify",
    "image_url",
]


def create_creature(
    session: Session, creature: CreatureCreate, owner_id: int
) -> Creature:
    # Auto-generate AI Avatar URL if not provided
    if not creature.image_url:
        from urllib.parse import quote

        # Use DiceBear Identicon as the standard avatar generator
        safe_name = quote(creature.name)
        creature.image_url = (
            f"https://api.dicebear.com/7.x/identicon/svg?seed={safe_name}"
        )

    # Auto-stamp
    creature.last_modify = datetime.now(timezone.utc).isoformat()

    # --- AUTO-REGISTER CLASS ---
    # If the creature_type is not in CreatureClass table, add it.
    from app.models import CreatureClass

    existing_class = session.exec(
        select(CreatureClass).where(CreatureClass.name == creature.creature_type)
    ).first()
    if not existing_class:
        # Default "Other" styling
        new_class = CreatureClass(
            name=creature.creature_type,
            color="rgba(127,19,236,0.1)",
            border_color="rgba(127,19,236,0.2)",
            text_color="#ad92c9",
        )
        session.add(new_class)
        # We don't need to refresh new_class here as long as it's committed with the creature

    db_creature = Creature.model_validate(creature)
    db_creature.owner_id = owner_id
    session.add(db_creature)
    session.commit()
    session.refresh(db_creature)
    return db_creature


def export_creatures_csv(session: Session, owner_id: int) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=_CSV_FIELDS, extrasaction="ignore")
    writer.writeheader()
    for c in session.exec(select(Creature).where(Creature.owner_id == owner_id)).all():
        writer.writerow(c.model_dump())
    return buf.getvalue()


def list_creatures(session: Session, owner_id: int) -> list[Creature]:
    return list(
        session.exec(select(Creature).where(Creature.owner_id == owner_id)).all()
    )


def get_creature(session: Session, creature_id: int, owner_id: int) -> Creature:
    creature = session.get(Creature, creature_id)
    if not creature:
        raise HTTPException(status_code=404, detail="Creature not found")
    if creature.owner_id != owner_id:
        raise HTTPException(status_code=403, detail="Not your creature")
    return creature


def update_creature(
    session: Session, creature_id: int, creature: CreatureCreate, owner_id: int
) -> Creature:
    db_creature = session.get(Creature, creature_id)
    if not db_creature:
        raise HTTPException(status_code=404, detail="Creature not found")
    if db_creature.owner_id != owner_id:
        raise HTTPException(status_code=403, detail="Not your creature")

    creature_data = creature.model_dump(exclude_unset=True)
    for key, value in creature_data.items():
        setattr(db_creature, key, value)

    db_creature.last_modify = datetime.now(timezone.utc).isoformat()

    session.add(db_creature)
    session.commit()
    session.refresh(db_creature)
    return db_creature


def delete_creature(session: Session, creature_id: int, owner_id: int) -> None:
    db_creature = session.get(Creature, creature_id)
    if not db_creature:
        raise HTTPException(status_code=404, detail="Creature not found")
    if db_creature.owner_id != owner_id:
        raise HTTPException(status_code=403, detail="Not your creature")

    session.delete(db_creature)
    session.commit()
