from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import pandas as pd
import os
import uvicorn

app = FastAPI(title="GSP1 API - Full Version (Filter & Edit)")

# เปิด CORS ให้เพื่อนฝั่ง Frontend เข้าถึงได้ทุกฟังก์ชัน
app.add_middleware(
    CORSMiddleware, 
    allow_origins=["*"], 
    allow_methods=["*"], 
    allow_headers=["*"]
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "relay_data.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.get("/")
def home():
    return {"message": "GSP1 API with Filter & Edit features is running!", "status": "success"}


# ประตูที่ 1: [GET] ดูข้อมูลทั้งหมดแบบมี ID
@app.get("/api/relays")
def get_all_relays():
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT rowid as id, * FROM relays", conn)
    conn.close()
    return {"status": "success", "total": len(df), "data": df.to_dict(orient="records")}


# ประตูที่ 2: [GET] ดูข้อมูลแยกตาม Plant (ลิงก์ /api/relays/GSP1 จะกลับมาเข้าได้ปกติแล้ว!)
@app.get("/api/relays/{plant}")
def get_relays_by_plant(plant: str):
    conn = get_db_connection()
    # ดึงข้อมูลแยกโรง และดึงเลข rowid มาทำเป็น id ให้ด้วย เผื่อเพื่อนดึงแยกโรงไปแล้วอยากกดแก้
    query = "SELECT rowid as id, * FROM relays WHERE Plant = ?"
    df = pd.read_sql_query(query, conn, params=(plant.upper(),))
    conn.close()
    
    if df.empty:
        return {"status": "error", "message": f"ไม่พบข้อมูลของ {plant}"}
        
    return {"status": "success", "total": len(df), "data": df.to_dict(orient="records")}


# ประตูที่ 3: [PUT] สำหรับรับข้อมูลที่เพื่อนพิมพ์แก้ไขจากหน้าเว็บมาเซฟลง .db
@app.put("/api/relays/{relay_id}")
def update_relay(relay_id: int, updated_data: dict):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # เช็คก่อนว่ามีไอดีนี้ไหม
    cursor.execute("SELECT rowid FROM relays WHERE rowid = ?", (relay_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail=f"ไม่พบข้อมูล Relay ไอดี {relay_id}")
    
    if not updated_data:
        conn.close()
        return {"status": "success", "message": "ไม่มีข้อมูลอัปเดต"}

    # สร้างคำสั่ง SQL UPDATE อัตโนมัติตามข้อมูลที่ส่งมา
    fields = list(updated_data.keys())
    values = list(updated_data.values())
    
    set_clause = ", ".join([f"{field} = ?" for field in fields])
    query = f"UPDATE relays SET {set_clause} WHERE rowid = ?"
    
    try:
        cursor.execute(query, values + [relay_id])
        conn.commit()
        conn.close()
        return {"status": "success", "message": f"แก้ไขข้อมูล Relay ไอดี {relay_id} สำเร็จ!"}
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=400, detail=f"เกิดข้อผิดพลาด: {str(e)}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)