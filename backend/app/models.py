from typing import Optional
from pydantic import field_validator
from sqlmodel import SQLModel, Field


class User(SQLModel, table=True):
    __tablename__ = "app_user"

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    hashed_password: str
    role: str = Field(default="admin")  # "admin" | "viewer"
    avatar: Optional[str] = Field(default=None)


class UserCreate(SQLModel):
    username: str
    password: str
    role: str = "admin"


class UserRead(SQLModel):
    id: int
    username: str
    role: str
    avatar: Optional[str] = None


class CreatureBase(SQLModel):
    name: str = Field(index=True)
    mythology: str
    creature_type: str
    danger_level: int
    habitat: str = Field(default="Unknown")
    last_modify: str = Field(default="Unknown")
    image_url: str = Field(default="")
    lore: Optional[str] = Field(default=None)

    @field_validator("danger_level", mode="before")
    @classmethod
    def danger_level_must_be_int(cls, v: object) -> object:
        if isinstance(v, bool):
            raise ValueError("danger_level must be an integer, not a boolean")
        return v


class Creature(CreatureBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: Optional[int] = Field(default=None, foreign_key="app_user.id", index=True)


class CreatureCreate(CreatureBase):
    pass


class CreatureRead(CreatureBase):
    id: int
    owner_id: Optional[int] = None


class CreatureClassBase(SQLModel):
    name: str = Field(index=True, unique=True)
    color: str = Field(
        default="rgba(127,19,236,0.1)"
    )  # CSS background value (rgba/hex)
    border_color: str = Field(default="rgba(127,19,236,0.2)")
    text_color: str = Field(default="#ad92c9")


class CreatureClass(CreatureClassBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)


class CreatureClassCreate(CreatureClassBase):
    pass


class CreatureClassRead(CreatureClassBase):
    id: int


class CreatureClassUpdate(SQLModel):
    name: Optional[str] = None
    color: Optional[str] = None
    border_color: Optional[str] = None
    text_color: Optional[str] = None
