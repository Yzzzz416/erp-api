from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Annotated
from databases import SessionLocal
from models import Product
from schemas import ProductRead, ProductCreate, ProductUpdate
from routers.auth import get_current_user
from utils.permissions import roles_required

router = APIRouter(prefix="/products", tags=["products"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]
current_user = Annotated[dict, Depends(get_current_user)]

# --- 查詢商品（所有人可用，顧客只看啟用商品） ---
@router.get("/", response_model=List[ProductRead])
def list_products(
    db: db_dependency,
    search: Optional[str] = Query(None, description="商品名稱關鍵字"),
    min_price: Optional[float] = Query(None, ge=0, description="最低價格"),
    max_price: Optional[float] = Query(None, ge=0, description="最高價格"),
    category: Optional[str] = Query(None, description="商品分類"),
    include_inactive: bool = Query(False, description="是否包含下架商品"),
    user: dict = Depends(get_current_user)
):
    query = db.query(Product)

    if user["user_role"] != "admin" or not include_inactive:
        query = query.filter(Product.is_active == True)
    if search:
        query = query.filter(Product.name.contains(search))
    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    if max_price is not None:
        query = query.filter(Product.price <= max_price)
    if category:
        query = query.filter(Product.category == category)

    return query.all()

# --- 新增商品（限 admin） ---
@router.post("/", response_model=ProductRead, dependencies=[Depends(roles_required("admin"))])
def create_product(product_data: ProductCreate, db: db_dependency):
    product = Product(**product_data.dict())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product

# --- 修改商品（限 admin） ---
@router.patch("/{product_id}", response_model=ProductRead, dependencies=[Depends(roles_required("admin"))])
def update_product(product_id: int, product_data: ProductUpdate, db: db_dependency):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(404, detail="找不到此商品")

    for field, value in product_data.dict(exclude_unset=True).items():
        setattr(product, field, value)

    db.commit()
    db.refresh(product)
    return product
    
# --- 刪除商品（限 admin） ---
@router.delete("/{product_id}", dependencies=[Depends(roles_required("admin"))])
def delete_product(
    product_id: int,
    confirm: bool = Query(False, description="是否確認刪除商品"),
    db: db_dependency = Depends()
):
    if not confirm:
        raise HTTPException(status_code=400, detail="請加上 confirm=true 才能執行刪除")

    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="找不到此商品")

    db.delete(product)
    db.commit()
    return {"message": f"商品 ID {product_id} 已刪除"}

