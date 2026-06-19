from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import pandas as pd
import os
import uvicorn

app = FastAPI(title="GSP1 Prototype API with Edit Feature")

# เปิด CORS ให้เพื่อนฝั่ง Frontend ดึงและส่งข้อมูลมาหาเราได้
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
    return {"message": "GSP1 API with Edit Feature is running!", "status": "success"}


# 1. [GET] ประตูสำหรับส่งข้อมูลให้เพื่อนไปโชว์ (เพิ่มคอลัมน์ id)
@app.get("/api/relays")
def get_all_relays():
    conn = get_db_connection()
    # ดึง rowid ของ SQLite มาตั้งชื่อเป็น id ให้เพื่อนเอาไปใช้อ้างอิงแถว
    df = pd.read_sql_query("SELECT rowid as id, * FROM relays", conn)
    conn.close()
    return {"status": "success", "total": len(df), "data": df.to_dict(orient="records")}


# 2. [PUT] ประตูบานใหม่! สำหรับรับข้อมูลแก้ไขจากเพื่อนมาเซฟลง .db
@app.put("/api/relays/{relay_id}")
def update_relay(relay_id: int, updated_data: dict):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # เช็คก่อนว่ามีไอดีนี้จริงไหม
    cursor.execute("SELECT rowid FROM relays WHERE rowid = ?", (relay_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail=f"ไม่พบข้อมูล Relay ไอดี {relay_id}")
    
    # สร้างคำสั่ง SQL UPDATE แบบอัตโนมัติจากข้อมูลที่เพื่อนส่งมา
    fields = list(updated_data.keys())
    values = list(updated_data.values())
    
    # สร้างข้อความเช่น "Breaker = ?, CT_Ratio = ?"
    set_clause = ", ".join([f"{field} = ?" for field in fields])
    query = f"UPDATE relays SET {set_clause} WHERE rowid = ?"
    
    try:
        # รันคำสั่งอัปเดตข้อมูลลงฐานข้อมูล
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