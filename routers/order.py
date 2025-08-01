from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Annotated, Optional
from databases import SessionLocal
from models import Order, OrderItem, Product, Customer
from schemas import OrderCreate, OrderRead, OrderUpdate, OrderItemCreate
from routers.auth import get_current_user
from utils.permissions import roles_required
from datetime import datetime


router = APIRouter(prefix="/orders", tags=["orders"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]
current_user = Annotated[dict, Depends(get_current_user)]

# --- 建立訂單（顧客或管理員） ---
@router.post("/", response_model=OrderRead)
def create_order(order_data: OrderCreate, db: db_dependency, user: current_user):
    if user["user_role"] == "admin":
        customer = db.query(Customer).filter(Customer.id == order_data.customer_id).first()
    else:
        if not user["customer_id"]:
            raise HTTPException(400, detail="目前帳號尚未綁定顧客資料")
        customer = db.query(Customer).filter(Customer.id == user["customer_id"]).first()

    if not customer:
        raise HTTPException(404, detail="找不到顧客")
    if not customer.is_active:
        raise HTTPException(403, detail="此顧客帳號已停用，無法建立訂單")

    total = 0
    items = []
    for item in order_data.items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if not product or product.stock < item.quantity:
            raise HTTPException(400, detail=f"商品 {item.product_id} 不存在或庫存不足")
        total += product.price * item.quantity
        items.append(OrderItem(product_id=item.product_id, quantity=item.quantity, unit_price=product.price))
        product.stock -= item.quantity

    new_order = Order(
        customer_id=customer.id,
        total_amount=total,
        order_date=datetime.utcnow(),
        payment_status="pending",
        items=items
    )
    db.add(new_order)
    db.commit()
    db.refresh(new_order)
    return new_order

# --- 查詢訂單（顧客：自己的 / 管理員：全部） ---
@router.get("/", response_model=List[OrderRead])
def list_orders(db: db_dependency, user: current_user):
    if user["user_role"] == "admin":
        return db.query(Order).all()
    if not user["customer_id"]:
        raise HTTPException(400, detail="目前帳號尚未綁定顧客資料")
    return db.query(Order).filter(Order.customer_id == user["customer_id"]).all()

# --- 標記為已付款（限 admin） ---
@router.patch("/{order_id}/pay", dependencies=[Depends(roles_required("admin"))])
def mark_paid(order_id: int, db: db_dependency):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order or order.payment_status != "pending":
        raise HTTPException(400, detail="訂單無法付款")
    order.payment_status = "paid"
    db.commit()
    return {"message": f"訂單 {order_id} 已付款"}

# --- 取消訂單（顧客：只能取消自己的，管理員可取消所有） ---
@router.patch("/{order_id}/cancel")
def cancel_order(order_id: int, db: db_dependency, user: current_user):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order or order.payment_status != "pending":
        raise HTTPException(400, detail="訂單無法取消")

    # 權限檢查：非 admin 僅能取消自己的訂單
    if user["user_role"] != "admin":
        if not user["customer_id"] or order.customer_id != user["customer_id"]:
            raise HTTPException(403, detail="您無權取消此訂單")

    for item in order.items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if product:
            product.stock += item.quantity
    order.payment_status = "cancelled"
    db.commit()
    return {"message": f"訂單 {order_id} 已取消"}

# --- 修改訂單項目（限 admin） ---
@router.patch("/{order_id}", response_model=OrderRead, dependencies=[Depends(roles_required("admin"))])
def update_order(order_id: int, update_data: OrderUpdate, db: db_dependency):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(404, detail="找不到訂單")

    if update_data.items is not None:
        # 回補原商品庫存
        for item in order.items:
            product = db.query(Product).filter(Product.id == item.product_id).first()
            if product:
                product.stock += item.quantity
        order.items.clear()

        new_items = []
        total = 0
        for item in update_data.items:
            product = db.query(Product).filter(Product.id == item.product_id).first()
            if not product or product.stock < item.quantity:
                raise HTTPException(400, detail="商品不存在或庫存不足")
            total += product.price * item.quantity
            new_items.append(OrderItem(product_id=item.product_id, quantity=item.quantity, unit_price=product.price))
            product.stock -= item.quantity

        order.items = new_items
        order.total_amount = total

    db.commit()
    db.refresh(order)
    return order
