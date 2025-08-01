from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException
import os
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from databases import SessionLocal
from typing import Annotated
from sqlalchemy.orm import Session
from models import Users, Customer
from jose import jwt, JWTError
from datetime import timedelta, datetime, timezone
from starlette import status
from schemas import UserCreate, Token

load_dotenv()

router = APIRouter(prefix="/auth", tags=["auth"])

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"

bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_bearer = OAuth2PasswordBearer(tokenUrl="/auth/token")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]

def authenticate_user(username: str, password: str, db):
    user = db.query(Users).filter(Users.username == username).first()
    if not user:
        return False
    if not bcrypt_context.verify(password, user.hashed_password):
        return False
    return user

def create_access_token(username: str, user_id: int, role: str, customer_id: int | None, expires_delta: timedelta):
    encode = {
        "sub": username,
        "id": user_id,
        "role": role,
        "customer_id": customer_id,
    }
    expires = datetime.now(timezone.utc) + expires_delta
    encode.update({"exp": expires})
    return jwt.encode(encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: Annotated[str, Depends(oauth2_bearer)]):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        user_id: int = payload.get("id")
        user_role: str = payload.get("role")
        customer_id: int | None = payload.get("customer_id")
        if username is None or user_id is None:
            raise HTTPException(status_code=401, detail="使用者驗證失敗")
        return {
            "username": username,
            "id": user_id,
            "user_role": user_role,
            "customer_id": customer_id
        }
    except JWTError:
        raise HTTPException(status_code=403, detail="Token 驗證失敗")

@router.post("/", status_code=201)
async def create_user(db: db_dependency, create_user_request: UserCreate):
    existing_user = db.query(Users).filter(Users.email == create_user_request.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="此 email 已被註冊")

    customer = db.query(Customer).filter(Customer.email == create_user_request.email).first()

    create_user_model = Users(
        email=create_user_request.email,
        username=create_user_request.email,
        first_name=create_user_request.first_name,
        last_name=create_user_request.last_name,
        role=create_user_request.role,
        hashed_password=bcrypt_context.hash(create_user_request.password),
        is_active=True,
        customer_id=customer.id if customer else None
    )
    db.add(create_user_model)
    db.commit()
    db.refresh(create_user_model)
    return {"message": "帳號建立成功", "username": create_user_model.username}

@router.post("/register_with_customer", status_code=201)
def register_with_customer(user_data: UserCreate, db: db_dependency):
    existing_user = db.query(Users).filter(Users.email == user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="此 email 已被註冊")

    existing_customer = db.query(Customer).filter(Customer.email == user_data.email).first()
    if not existing_customer:
        new_customer = Customer(
            name=f"{user_data.first_name} {user_data.last_name}",
            email=user_data.email,
            phone=user_data.phone,
            is_active=True
        )
        db.add(new_customer)
        db.commit()
        db.refresh(new_customer)
        customer_id = new_customer.id
    else:
        customer_id = existing_customer.id

    new_user = Users(
        username=user_data.email,
        email=user_data.email,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        role=user_data.role,
        hashed_password=bcrypt_context.hash(user_data.password),
        is_active=True,
        customer_id=customer_id
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "帳號與顧客建立成功", "username": new_user.username}

@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: db_dependency
):
    user = authenticate_user(form_data.username, form_data.password, db)
    if not user:
        raise HTTPException(status_code=401, detail="使用者驗證失敗")
    token = create_access_token(user.username, user.id, user.role, user.customer_id, timedelta(minutes=20))
    return {"access_token": token, "token_type": "bearer"}
