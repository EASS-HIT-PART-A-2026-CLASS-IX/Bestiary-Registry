from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import SQLModel, select

from app.auth import CurrentUser, create_access_token, hash_password, verify_password
from app.db import SessionDep
from app.models import User, UserCreate, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


class PasswordChange(SQLModel):
    old_password: str
    new_password: str


class AvatarUpdate(SQLModel):
    avatar: str


@router.post("/register", response_model=UserRead, status_code=201)
def register(user_in: UserCreate, session: SessionDep) -> UserRead:
    if session.exec(select(User).where(User.username == user_in.username)).first():
        raise HTTPException(status_code=400, detail="Username already taken")
    user = User(
        username=user_in.username,
        hashed_password=hash_password(user_in.password),
        role=user_in.role,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@router.post("/token")
def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: SessionDep,
) -> dict:
    user = session.exec(select(User).where(User.username == form.username)).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token({"sub": user.username, "role": user.role})
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=UserRead)
def get_me(current_user: CurrentUser) -> UserRead:
    return current_user


@router.put("/me/password")
def change_password(
    body: PasswordChange,
    current_user: CurrentUser,
    session: SessionDep,
) -> dict:
    if not verify_password(body.old_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect current password")
    current_user.hashed_password = hash_password(body.new_password)
    session.add(current_user)
    session.commit()
    return {"detail": "Password updated"}


@router.put("/me/avatar")
def update_avatar(
    body: AvatarUpdate,
    current_user: CurrentUser,
    session: SessionDep,
) -> dict:
    print(
        f"[avatar] user={current_user.username} received base64 len={len(body.avatar)}"
    )
    current_user.avatar = body.avatar
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    saved_len = len(current_user.avatar) if current_user.avatar else 0
    print(
        f"[avatar] DB save {'OK' if saved_len == len(body.avatar) else 'MISMATCH'} (stored len={saved_len})"
    )
    return {"detail": "Avatar updated"}
