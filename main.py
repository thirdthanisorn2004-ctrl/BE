from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
import libsql_client
import os
import uvicorn
import bcrypt
import jwt
from datetime import datetime, timedelta

app = FastAPI(title="GSP1 API - Production Grade")

app.add_middleware(
    CORSMiddleware, 
    allow_origins=["*"], 
    allow_methods=["*"], 
    allow_headers=["*"]
)

TURSO_URL = os.environ.get("TURSO_DATABASE_URL", "")
TURSO_TOKEN = os.environ.get("TURSO_AUTH_TOKEN", "")
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "changeme")
ADMIN_CODE = "PTT888"

security = HTTPBearer()

def get_db_client():
    if not TURSO_URL or not TURSO_TOKEN:
        raise HTTPException(status_code=500, detail="Database credentials missing")
    return libsql_client.create_client_sync(url=TURSO_URL, auth_token=TURSO_TOKEN)

# --- ยามเฝ้าประตูขั้นเด็ดขาด (ห้ามส่งฟิลด์แปลกปลอมเข้ามาเด็ดขาด!) ---
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

    # ตั้งค่าให้ Reject (422) ทันทีถ้ามีฟิลด์อื่นที่ไม่ได้อยู่ในลิสต์ด้านบนโผล่มา
    model_config = {"extra": "forbid"}

class RegisterSchema(BaseModel):
    username: str
    password: str
    admin_code: Optional[str] = None

class LoginSchema(BaseModel):
    username: str
    password: str

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
        return payload
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

def require_admin(payload=Depends(verify_token)):
    if payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return payload

@app.post("/api/register")
def register(user_data: RegisterSchema):
    role = "admin" if user_data.admin_code == ADMIN_CODE else "user"
    hashed_password = bcrypt.hashpw(user_data.password.encode(), bcrypt.gensalt()).decode()
    try:
        with get_db_client() as client:
            existing = client.execute("SELECT username FROM users WHERE username = ?", [user_data.username])
            if existing.rows:
                raise HTTPException(status_code=400, detail="Username already exists")
            client.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                [user_data.username, hashed_password, role]
            )
        return {"status": "success", "message": "Account created", "role": role}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/login")
def login(user_data: LoginSchema):
    try:
        with get_db_client() as client:
            result = client.execute("SELECT username, password_hash, role FROM users WHERE username = ?", [user_data.username])
            if not result.rows:
                raise HTTPException(status_code=401, detail="Invalid credentials")
            row = dict(zip(result.columns, result.rows[0]))
            if not bcrypt.checkpw(user_data.password.encode(), row["password_hash"].encode()):
                raise HTTPException(status_code=401, detail="Invalid credentials")
            db_role = row["role"]
            token = jwt.encode(
                {"sub": user_data.username, "role": db_role, "exp": datetime.utcnow() + timedelta(hours=8)},
                SECRET_KEY, algorithm="HS256"
            )
            return {"status": "success", "access_token": token, "role": db_role}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/")
def home():
    return {"message": "GSP1 API Production Grade is running!", "status": "success"}

@app.get("/api/relays")
def get_all_relays():
    # ใช้ with block: รับประกันว่า connection จะถูกปิดเสมอ (แก้ข้อ 3)
    with get_db_client() as client:
        result = client.execute("SELECT * FROM relays")
        data = [dict(zip(result.columns, row)) for row in result.rows]
        return {"status": "success", "total": len(data), "data": data}

@app.get("/api/relays/{plant}")
def get_relays_by_plant(plant: str):
    with get_db_client() as client:
        result = client.execute("SELECT * FROM relays WHERE Plant = ?", [plant.upper()])
        data = [dict(zip(result.columns, row)) for row in result.rows]
        if not data:
            return {"status": "error", "message": f"ไม่พบข้อมูลของ {plant}"}
        return {"status": "success", "total": len(data), "data": data}

@app.put("/api/relays/{relay_id}")
def update_relay(relay_id: str, updated_data: RelayUpdateSchema):
    update_dict = updated_data.model_dump(exclude_unset=True)
    
    if not update_dict:
        return {"status": "success", "message": "ไม่มีข้อมูลอัปเดต"}
    
    fields = list(update_dict.keys())
    values = list(update_dict.values())
    
    set_clause = ", ".join([f"{field} = ?" for field in fields])
    query = f"UPDATE relays SET {set_clause} WHERE Relay_ID = ?"
    
    try:
        # ยิง UPDATE รอบเดียว แล้วเช็คแถวที่โดนผลกระทบเลย (ลด Round-trip แก้ข้อ 2)
        with get_db_client() as client:
            result = client.execute(query, values + [relay_id])
            
            # ถ้ายิงไปแล้วบอกว่าโดนแก้ 0 แถว แปลว่าไอดีนี้ไม่มีในตาราง
            if result.rows_affected == 0:
                raise HTTPException(status_code=404, detail=f"ไม่พบข้อมูล Relay ID: {relay_id}")
                
            return {"status": "success", "message": f"แก้ไขข้อมูล Relay ID: {relay_id} สำเร็จ!"}
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"เกิดข้อผิดพลาด: {str(e)}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)