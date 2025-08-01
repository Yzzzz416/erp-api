# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers.customers import router as customer_router
from routers.auth import router as auth_router
from routers.products import router as product_router
from routers.order import router as order_router
from routers.exports import router as export_router
from databases import Base, engine  # 自動建表需要
import models  # 確保所有 model 被載入

# 建立資料表（若尚未建立）
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="簡易 ERP 系統 API",
    description="支援顧客、商品、訂單、管理員與 JWT 驗證的 ERP 系統",
    version="1.0.0"
)

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 依部署環境調整
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 路由導入 ---
app.include_router(auth_router)            # /auth → 使用者註冊、登入
app.include_router(customer_router)        # /customer → 顧客資料相關 
app.include_router(export_router)          # /export  →  報表
app.include_router(product_router)         # /products → 商品查詢
app.include_router(order_router)           # /order → 訂單操作

# --- 健康檢查 ---
@app.get("/")
def root():
    return {"message": "ERP 系統 API 正常運作中"}

