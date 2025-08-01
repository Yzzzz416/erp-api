from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
from datetime import datetime

class CustomerCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="顧客名稱")
    email: EmailStr = Field(..., description="電子郵件")
    phone: Optional[str] = Field(None, min_length=5, max_length=20,description="電話號碼")
    is_active: bool = Field(default=True)

class CustomerRead(BaseModel):
    id: int
    name: str
    email: str
    phone: Optional[str]

    class Config:
        orm_mode = True

class CustomerUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100, description="顧客名稱")
    email: Optional[EmailStr] = Field(None, description="電子郵件")
    phone: Optional[str] = Field(None, min_length=5, max_length=20,description="電話號碼")
    is_active: Optional[bool] = Field(default=True)
 


class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="商品名稱")
    price: float = Field(..., gt=0, description="商品價格")
    stock: int = Field(..., ge=0, le=99999, description="商品庫存")
    category: Optional[str]
    is_active: bool

class ProductUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="商品名稱")
    price: float = Field(..., gt=0, description="商品價格")
    stock: int = Field(..., ge=0, le=99999, description="商品庫存")
    category: Optional[str]
    is_active: bool

class ProductRead(BaseModel):
    id: int
    name: str
    price: float
    stock: int
    category: Optional[str]
    is_active: bool

    class Config:
        orm_mode = True

class OrderItemCreate(BaseModel):
    product_id: int = Field(..., description="產品 ID")
    quantity: int = Field(..., ge=1, le=9999, description="購買數量 (1~9999)")

class OrderItemRead(BaseModel):
    id: int
    product_id: int
    quantity: int
    unit_price: float

    class Config:
        orm_mode = True

class OrderCreate(BaseModel):
    customer_id: int = Field(..., description="顧客 ID")
    items: List[OrderItemCreate] = Field(..., description="訂單項目清單")

    model_config = {
        "json_schema_extra": {
            "example": {
                "customer_id": 1,
                "items": [
                    {"product_id": 101, "quantity": 2},
                    {"product_id": 103, "quantity": 1}
                ]
            }
        }
    }
class OrderUpdate(BaseModel):
    items: Optional[List[OrderItemCreate]] = Field(None, description="更新訂單項目")

class OrderRead(BaseModel):
    id: int
    customer_id: int
    order_date: datetime
    total_amount: float
    items: List[OrderItemRead]

    class Config:
        orm_mode = True

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=30)
    email: EmailStr
    first_name: str
    last_name: str
    password: str = Field(..., min_length=6)
    role: str

class Token(BaseModel):
    access_token: str
    token_type: str
