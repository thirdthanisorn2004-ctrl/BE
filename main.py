from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import libsql_client
import os
import uvicorn

app = FastAPI(title="GSP1 API - Cloud DB Edition")

app.add_middleware(
    CORSMiddleware, 
    allow_origins=["*"], 
    allow_methods=["*"], 
    allow_headers=["*"]
)

# ดึง URL กับ Token จากตู้เซฟของ Render (ถ้ารันในคอมตัวเองต้องตั้งค่า env ก่อน)
TURSO_URL = os.environ.get("TURSO_DATABASE_URL", "")
TURSO_TOKEN = os.environ.get("TURSO_AUTH_TOKEN", "")

def get_db_client():
    if not TURSO_URL or not TURSO_TOKEN:
        raise HTTPException(status_code=500, detail="ลืมตั้งค่า Database Credentials ใน Render หรือเปล่า?")
    return libsql_client.create_client_sync(url=TURSO_URL, auth_token=TURSO_TOKEN)

# --- ยามเฝ้าประตู (Pydantic Model) ---
class RelayUpdateSchema(BaseModel):
    Breaker: Optional[str] = None
    CT_Ratio: Optional[str] = None
    CT_Class: Optional[str] = None
    CT_Burden_VA: Optional[str] = None
    ZCT_Ratio: Optional[str] = None
    ZCT_Class: Optional[str] = None
    ZCT_Burden_VA: Optional[str] = None
    Relay_Manufacturer: Optional[str] = None
    Relay_Model: Optional[str] = None
    Phase_Curve: Optional[str] = None
    Phase_Pickup: Optional[float] = None
    Phase_Prim_Amps: Optional[float] = None
    Phase_Time_Dial: Optional[float] = None
    Phase_Inst_Pickup: Optional[float] = None
    Phase_Inst_Prim_Amps: Optional[float] = None
    Phase_Inst_Delay_s: Optional[float] = None
    Ground_Curve: Optional[str] = None
    Ground_Pickup: Optional[float] = None
    Ground_Prim_Amps: Optional[float] = None
    Ground_Time_Dial: Optional[float] = None
    Ground_Inst_Pickup: Optional[float] = None
    Ground_Inst_Prim_Amps: Optional[float] = None
    Ground_Inst_Delay_s: Optional[float] = None
    OLR_Trip: Optional[float] = None
    OLR_Prim_Amps: Optional[float] = None
    OLR_Time_Constant: Optional[float] = None
    Remark: Optional[str] = None

@app.get("/")
def home():
    return {"message": "GSP1 API is running with Turso Cloud DB!", "status": "success"}

@app.get("/api/relays")
def get_all_relays():
    client = get_db_client()
    result = client.execute("SELECT * FROM relays")
    client.close()
    
    # แปลงข้อมูลจาก Turso ให้กลายเป็น List ของ Dictionary ส่งให้เพื่อน (เร็วกว่า Pandas)
    data = [dict(zip(result.columns, row)) for row in result.rows]
    return {"status": "success", "total": len(data), "data": data}

@app.get("/api/relays/{plant}")
def get_relays_by_plant(plant: str):
    client = get_db_client()
    result = client.execute("SELECT * FROM relays WHERE Plant = ?", [plant.upper()])
    client.close()
    
    data = [dict(zip(result.columns, row)) for row in result.rows]
    if not data:
        return {"status": "error", "message": f"ไม่พบข้อมูลของ {plant}"}
        
    return {"status": "success", "total": len(data), "data": data}

@app.put("/api/relays/{relay_id}")
def update_relay(relay_id: str, updated_data: RelayUpdateSchema):
    update_dict = updated_data.model_dump(exclude_unset=True)
    
    if not update_dict:
        return {"status": "success", "message": "ไม่มีข้อมูลอัปเดต"}

    client = get_db_client()
    
    # เช็คว่ามี Relay_ID นี้ไหม
    check = client.execute("SELECT Relay_ID FROM relays WHERE Relay_ID = ?", [relay_id])
    if not check.rows:
        client.close()
        raise HTTPException(status_code=404, detail=f"ไม่พบข้อมูล Relay ID: {relay_id}")
    
    fields = list(update_dict.keys())
    values = list(update_dict.values())
    
    set_clause = ", ".join([f"{field} = ?" for field in fields])
    query = f"UPDATE relays SET {set_clause} WHERE Relay_ID = ?"
    
    try:
        client.execute(query, values + [relay_id])
        client.close()
        return {"status": "success", "message": f"แก้ไขข้อมูล Relay ID: {relay_id} สำเร็จ!"}
    except Exception as e:
        client.close()
        raise HTTPException(status_code=400, detail=f"เกิดข้อผิดพลาด: {str(e)}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)