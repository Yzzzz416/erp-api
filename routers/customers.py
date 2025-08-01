from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from databases import SessionLocal
from models import Customer
from schemas import CustomerCreate, CustomerUpdate
from routers.auth import get_current_user
from utils.permissions import roles_required

router = APIRouter(prefix="/customers", tags=["customers"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- 查詢所有顧客（限 admin） ---
@router.get("/", dependencies=[Depends(roles_required("admin"))])
def list_customers(db: Session = Depends(get_db), search: Optional[str] = Query(None)):
    query = db.query(Customer)
    if search:
        query = query.filter(Customer.name.contains(search))
    return query.all()

# --- 新增顧客（限 admin） ---
@router.post("/", dependencies=[Depends(roles_required("admin"))])
def create_customer(new_customer: CustomerCreate, db: Session = Depends(get_db)):
    existing = db.query(Customer).filter(Customer.email == new_customer.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="此 Email 已存在，無法新增")
    customer = Customer(
        name=new_customer.name,
        email=new_customer.email,
        phone=new_customer.phone,
        is_active=True
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer

# --- 更新顧客（限 admin） ---
@router.put("/{customer_id}", dependencies=[Depends(roles_required("admin"))])
def update_customer(customer_id: int, update_data: CustomerUpdate, db: Session = Depends(get_db)):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="查無此顧客")
    for field, value in update_data.dict(exclude_unset=True).items():
        setattr(customer, field, value)
    db.commit()
    db.refresh(customer)
    return customer

# --- 刪除顧客（限 admin） ---
@router.delete("/{customer_id}", dependencies=[Depends(roles_required("admin"))])
def delete_customer(customer_id: int, confirm: bool = Query(False), db: Session = Depends(get_db)):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="找不到此客戶")
    if not confirm:
        raise HTTPException(status_code=400, detail="請加上 confirm=true 才能執行刪除")
    db.delete(customer)
    db.commit()
    return {"message": f"客戶 ID {customer_id} 已刪除"}

# --- 加入黑名單（限 admin） ---
@router.patch("/{customer_id}/blacklist", dependencies=[Depends(roles_required("admin"))])
def blacklist_customer(customer_id: int, db: Session = Depends(get_db)):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="找不到此顧客")
    customer.is_active = False
    db.commit()
    return {"message": f"客戶 ID {customer_id} 已加入黑名單"}

# --- 顧客查詢自己資料 ---
@router.get("/me")
def get_my_info(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    if not user["customer_id"]:
        raise HTTPException(status_code=400, detail="尚未綁定顧客資料")
    customer = db.query(Customer).filter(Customer.id == user["customer_id"]).first()
    if not customer:
        raise HTTPException(status_code=404, detail="找不到對應顧客")
    return customer

# --- 顧客更新自己資料（僅可改 name 與 phone） ---
@router.put("/me")
def update_my_info(update_data: CustomerUpdate, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    if not user["customer_id"]:
        raise HTTPException(status_code=400, detail="尚未綁定顧客資料")
    customer = db.query(Customer).filter(Customer.id == user["customer_id"]).first()
    if not customer:
        raise HTTPException(status_code=404, detail="找不到顧客資料")
    if not customer.is_active:
        raise HTTPException(status_code=403, detail="帳號已被停用")

    allowed_fields = ["name", "phone"]
    updates = update_data.dict(exclude_unset=True)
    for field in updates:
        if field not in allowed_fields:
            raise HTTPException(403, detail=f"欄位 '{field}' 不允許修改")

    for field, value in updates.items():
        setattr(customer, field, value)

    db.commit()
    db.refresh(customer)
    return customer
