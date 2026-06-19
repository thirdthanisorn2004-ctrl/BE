import libsql_client

# TODO: เอา URL กับ Token ของมึงมาใส่ตรงนี้ (ใส่แค่ตอนรันสร้างตาราง รันเสร็จเราจะลบไฟล์นี้ทิ้ง)
TURSO_URL = "https://gsp-relay-db-thirdthanisorn2004-ctrl.aws-ap-northeast-1.turso.io"
TURSO_TOKEN = "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJpYXQiOjE3ODE4NTMxODAsImlkIjoiMDE5ZWRlYWItNzMwMS03OGZmLWE2NjUtNjA5NWRlNjBmYzkyIiwicmlkIjoiNmM2MjZiODYtZTA2OS00YTkzLWFjZWQtNjZkMTUwYmQwZDU2In0.VlqV69bz8E3SejlZjs2hpDj3xNDy1B2yqRHFD3fTU5SKssyb_o-C_XtJuOjpBkiFXwGI_xIe6ySOF5t_IrZsCQ"

client = libsql_client.create_client_sync(url=TURSO_URL, auth_token=TURSO_TOKEN)

print("กำลังล้างตารางเก่า (ถ้ามี)...")
client.execute("DROP TABLE IF EXISTS relays")

print("กำลังสร้างตารางโครงสร้างใหม่...")
client.execute("""
CREATE TABLE relays (
    Plant TEXT, Breaker TEXT, CT_Ratio TEXT, CT_Class TEXT, CT_Burden_VA TEXT,
    ZCT_Ratio TEXT, ZCT_Class TEXT, ZCT_Burden_VA TEXT, Relay_ID TEXT UNIQUE, 
    Relay_Manufacturer TEXT, Relay_Model TEXT, Phase_Curve TEXT, Phase_Pickup REAL,
    Phase_Prim_Amps REAL, Phase_Time_Dial REAL, Phase_Inst_Pickup REAL,
    Phase_Inst_Prim_Amps REAL, Phase_Inst_Delay_s REAL, Ground_Curve TEXT,
    Ground_Pickup REAL, Ground_Prim_Amps REAL, Ground_Time_Dial REAL,
    Ground_Inst_Pickup REAL, Ground_Inst_Prim_Amps REAL, Ground_Inst_Delay_s REAL,
    OLR_Trip REAL, OLR_Prim_Amps REAL, OLR_Time_Constant REAL, Remark TEXT
)
""")

print("กำลังยัดข้อมูลตั้งต้น GSP1 ทั้ง 28 ตัว...")
for i in range(1, 29):
    relay_id = f"GSP1-R{i:02d}"
    client.execute("INSERT INTO relays (Plant, Relay_ID) VALUES (?, ?)", ["GSP1", relay_id])

print("✅ สร้างฐานข้อมูลบน Cloud สำเร็จ! ข้อมูลมึงเป็นอมตะแล้ว!")
client.close()