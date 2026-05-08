from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import select

from app.auth import create_access_token, hash_password, verify_password
from app.db import SessionDep
from app.models import User, UserCreate, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


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
