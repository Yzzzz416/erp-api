from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from databases import SessionLocal
from typing import Annotated
from models import Customer, Order, Product
from fastapi.responses import StreamingResponse
from io import StringIO
import csv
from utils.permissions import roles_required 

router = APIRouter(prefix="/exports", tags=["export"])

# --- 取得 DB session ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]

# --- 匯出顧客資料（限 admin） ---
@router.get("/customers", dependencies=[Depends(roles_required("admin"))])
def export_customers(db: db_dependency):
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Name", "Email", "Phone"])
    for customer in db.query(Customer).all():
        writer.writerow([customer.id, customer.name, customer.email, customer.phone])
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=customers.csv"}
    )

# --- 匯出訂單資料（限 admin） ---
@router.get("/orders", dependencies=[Depends(roles_required("admin"))])
def export_orders(db: db_dependency):
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Customer ID", "Total Amount"])
    for order in db.query(Order).all():
        writer.writerow([order.id, order.customer_id, order.total_amount])
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=orders.csv"}
    )

# --- 匯出商品資料（限 admin） ---
@router.get("/products", dependencies=[Depends(roles_required("admin"))])
def export_products(db: db_dependency):
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Name", "Price", "Stock"])
    for product in db.query(Product).all():
        writer.writerow([product.id, product.name, product.price, product.stock])
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=products.csv"}
    )
