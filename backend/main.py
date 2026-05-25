from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session, joinedload
from models import (SessionLocal, init_db, Hospital, Doctor, HospitalAdmin,
                    TriageUser, Patient, PatientProcedure)
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import jwt, bcrypt, uuid, os

SECRET = "HastaKayit_JWT_2024"
FRONTEND = os.path.join(os.path.dirname(__file__), "..", "frontend", "index.html")

app = FastAPI(title="Hasta Kayıt Sistemi")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
init_db()


# ─── yardımcılar ──────────────────────────────────────────────────────────────

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()


def auth(authorization: str = Header(None)) -> dict:
    if not authorization:
        raise HTTPException(401)
    try:
        return jwt.decode(authorization.split()[1], SECRET, algorithms=["HS256"])
    except Exception:
        raise HTTPException(401, "Geçersiz token")


def role(r: str):
    def dep(c: dict = Depends(auth)):
        if c.get("role") != r:
            raise HTTPException(403)
        return c
    return dep


def p_dict(p: Patient) -> dict:
    return {
        "patientId": p.id, "name": p.name, "surname": p.surname,
        "hospitalId": p.hospital_id, "isActive": p.is_active,
        "admittedAt": p.admitted_at, "dischargedAt": p.discharged_at,
        "doctorId": p.doctor_id, "diagnosis": p.diagnosis,
        "medications": p.medications, "isMedicalLocked": p.is_medical_locked,
        "queueNumber": p.queue_number, "queueStatus": p.queue_status,
        "noShowCount": p.no_show_count, "queuedAt": p.queued_at,
        "procedures": [
            {"procedureId": pr.id, "type": pr.type, "notes": pr.notes,
             "requestedAt": pr.requested_at, "completedAt": pr.completed_at,
             "isCompleted": pr.is_completed}
            for pr in (p.procedures or [])
        ],
    }


def next_q(db: Session, hospital_id: int) -> int:
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    nums = [r[0] for r in db.query(Patient.queue_number).filter(
        Patient.hospital_id == hospital_id, Patient.queued_at >= today
    ).all() if r[0]]
    return (max(nums) + 1) if nums else 1


def get_patient(db: Session, pid: str) -> Patient:
    p = db.query(Patient).options(joinedload(Patient.procedures)).filter(Patient.id == pid).first()
    if not p:
        raise HTTPException(404)
    return p


def auto_call(db: Session, doctor_id: int) -> Optional[Patient]:
    p = db.query(Patient).filter(
        Patient.doctor_id == doctor_id, Patient.queue_status == "Waiting"
    ).order_by(Patient.queued_at).first()
    if p:
        p.queue_status = "Called"
    return p


def validate_name(s: str, field: str):
    s = (s or "").strip()
    if len(s) < 2:
        raise HTTPException(400, f"{field} en az 2 karakter olmalı")
    if any(c.isdigit() for c in s):
        raise HTTPException(400, f"{field} rakam içeremez")


# ─── auth ─────────────────────────────────────────────────────────────────────

class Login(BaseModel):
    username: str
    password: str


@app.post("/api/auth/admin/login")
def admin_login(b: Login, db: Session = Depends(get_db)):
    a = db.query(HospitalAdmin).filter(HospitalAdmin.username == b.username).first()
    if not a or not bcrypt.checkpw(b.password.encode(), a.password_hash.encode()):
        raise HTTPException(401, "Hatalı kullanıcı adı veya şifre")
    h = db.query(Hospital).filter(Hospital.id == a.hospital_id).first()
    token = jwt.encode({"role": "Admin", "hospitalId": a.hospital_id}, SECRET)
    return {"token": token, "role": "Admin", "hospitalId": a.hospital_id, "hospitalName": h.name}


@app.post("/api/auth/doctor/login")
def doctor_login(b: Login, db: Session = Depends(get_db)):
    d = db.query(Doctor).filter(Doctor.username == b.username).first()
    if not d or not d.password_hash or not bcrypt.checkpw(b.password.encode(), d.password_hash.encode()):
        raise HTTPException(401, "Hatalı kullanıcı adı veya şifre")
    h = db.query(Hospital).filter(Hospital.id == d.hospital_id).first()
    token = jwt.encode({"role": "Doctor", "doctorId": d.id,
                        "doctorName": f"{d.name} {d.surname}", "hospitalId": d.hospital_id}, SECRET)
    return {"token": token, "role": "Doctor", "doctorId": d.id,
            "doctorName": f"{d.name} {d.surname}", "hospitalId": d.hospital_id, "hospitalName": h.name}


@app.post("/api/auth/triage/login")
def triage_login(b: Login, db: Session = Depends(get_db)):
    u = db.query(TriageUser).filter(TriageUser.username == b.username).first()
    if not u or not bcrypt.checkpw(b.password.encode(), u.password_hash.encode()):
        raise HTTPException(401, "Hatalı kullanıcı adı veya şifre")
    h = db.query(Hospital).filter(Hospital.id == u.hospital_id).first()
    token = jwt.encode({"role": "Triage", "hospitalId": u.hospital_id}, SECRET)
    return {"token": token, "role": "Triage", "hospitalId": u.hospital_id, "hospitalName": h.name}


# ─── hastaneler ───────────────────────────────────────────────────────────────

@app.get("/api/hospitals")
def hospitals(db: Session = Depends(get_db)):
    return [
        {"hospitalId": h.id, "name": h.name, "city": h.city, "capacity": h.capacity,
         "doctorCount": db.query(Doctor).filter(Doctor.hospital_id == h.id).count()}
        for h in db.query(Hospital).all()
    ]


# ─── doktorlar ────────────────────────────────────────────────────────────────

@app.get("/api/doctors/hospital/{hid}")
def doctors(hid: int, db: Session = Depends(get_db)):
    return [
        {"doctorId": d.id, "name": d.name, "surname": d.surname, "specialty": d.specialty,
         "isActiveToday": d.is_active_today, "hasCredentials": bool(d.username and d.password_hash)}
        for d in db.query(Doctor).filter(Doctor.hospital_id == hid).all()
    ]


@app.put("/api/doctors/{did}/toggle-active")
def toggle_active(did: int, db: Session = Depends(get_db), c: dict = Depends(role("Admin"))):
    d = db.query(Doctor).filter(Doctor.id == did, Doctor.hospital_id == c["hospitalId"]).first()
    if not d:
        raise HTTPException(404)
    d.is_active_today = not d.is_active_today
    db.commit()


class Cred(BaseModel):
    username: str
    password: str


@app.put("/api/doctors/{did}/credentials")
def set_cred(did: int, b: Cred, db: Session = Depends(get_db), c: dict = Depends(role("Admin"))):
    if len(b.password) < 6:
        raise HTTPException(400, "Şifre en az 6 karakter olmalı")
    d = db.query(Doctor).filter(Doctor.id == did, Doctor.hospital_id == c["hospitalId"]).first()
    if not d:
        raise HTTPException(404)
    if db.query(Doctor).filter(Doctor.username == b.username, Doctor.id != did).first():
        raise HTTPException(409, "Bu kullanıcı adı zaten kullanılıyor")
    d.username = b.username
    d.password_hash = bcrypt.hashpw(b.password.encode(), bcrypt.gensalt()).decode()
    db.commit()


# ─── doluluk ──────────────────────────────────────────────────────────────────

@app.get("/api/density")
def density(db: Session = Depends(get_db)):
    result = []
    for h in db.query(Hospital).all():
        active = db.query(Patient).filter(Patient.hospital_id == h.id, Patient.is_active == True).count()
        docs   = db.query(Doctor).filter(Doctor.hospital_id == h.id, Doctor.is_active_today == True).count()
        result.append({
            "hospitalId": h.id, "hospitalName": h.name, "city": h.city,
            "capacity": h.capacity, "activePatientCount": active, "doctorCount": docs,
        })
    return result


# ─── hastalar ─────────────────────────────────────────────────────────────────

@app.get("/api/patients/hospital/{hid}")
def active_by_hospital(hid: int, db: Session = Depends(get_db)):
    ps = db.query(Patient).options(joinedload(Patient.procedures)).filter(
        Patient.hospital_id == hid, Patient.is_active == True
    ).all()
    return [p_dict(p) for p in ps]


class TriageBody(BaseModel):
    name: str
    surname: str
    doctorId: int


@app.post("/api/patients/triage")
def register_triage(b: TriageBody, db: Session = Depends(get_db), c: dict = Depends(role("Triage"))):
    validate_name(b.name, "Ad")
    validate_name(b.surname, "Soyad")
    now = datetime.utcnow()
    p = Patient(
        id=str(uuid.uuid4()), name=b.name.strip(), surname=b.surname.strip(),
        hospital_id=c["hospitalId"], doctor_id=b.doctorId,
        admitted_at=now, queue_number=next_q(db, c["hospitalId"]),
        queue_status="Waiting", queued_at=now,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p_dict(p)


@app.get("/api/patients/doctor/{did}/today")
def today_by_doctor(did: int, db: Session = Depends(get_db), c: dict = Depends(role("Doctor"))):
    if c["doctorId"] != did:
        raise HTTPException(403)
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    ps = db.query(Patient).options(joinedload(Patient.procedures)).filter(
        Patient.doctor_id == did, Patient.queued_at >= today
    ).order_by(Patient.queued_at).all()
    return [p_dict(p) for p in ps]


@app.put("/api/patients/{pid}/discharge")
def discharge(pid: str, db: Session = Depends(get_db), c: dict = Depends(role("Doctor"))):
    p = get_patient(db, pid)
    if p.hospital_id != c["hospitalId"]:
        raise HTTPException(403)
    if not p.is_active:
        raise HTTPException(409, "Hasta zaten taburcu edilmiş")
    p.is_active, p.discharged_at, p.queue_status = False, datetime.utcnow(), "Seen"
    nxt = auto_call(db, p.doctor_id)
    db.commit()
    return {"actioned": p_dict(p), "nextCalled": p_dict(nxt) if nxt else None}


@app.put("/api/patients/{pid}/noshow")
def noshow(pid: str, db: Session = Depends(get_db), c: dict = Depends(role("Doctor"))):
    p = get_patient(db, pid)
    if p.doctor_id != c["doctorId"]:
        raise HTTPException(403)
    if p.is_medical_locked:
        raise HTTPException(409, "Tıbbi kaydı girilmiş hastaya 'Gelmedi' işareti yapılamaz")
    if p.queue_status == "InProcedure":
        raise HTTPException(409, "Hasta tedavide, 'Gelmedi' işareti yapılamaz")
    if any(pr.is_completed for pr in p.procedures):
        raise HTTPException(409, "Hasta daha önce tedavi aldı, 'Gelmedi' işareti yapılamaz")

    p.no_show_count += 1

    if p.no_show_count >= 3:
        p.queue_status, p.is_active, p.discharged_at = "NoShow", False, datetime.utcnow()
        nxt = auto_call(db, p.doctor_id)
        db.commit()
        return {"actioned": p_dict(p), "nextCalled": p_dict(nxt) if nxt else None}

    # Hasta hâlâ "Called" — sıradaki bekliyeni bul, sonra no-show'u kuyruğun başına al
    nxt = db.query(Patient).filter(
        Patient.doctor_id == c["doctorId"], Patient.queue_status == "Waiting"
    ).order_by(Patient.queued_at).first()

    today0 = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    p.queue_status = "Waiting"
    p.queued_at    = today0.replace(second=p.no_show_count)
    if nxt:
        nxt.queue_status = "Called"

    db.commit()
    return {"actioned": p_dict(p), "nextCalled": p_dict(nxt) if nxt else None}


@app.put("/api/patients/queue/doctor/{did}/call-next")
def call_next_route(did: int, db: Session = Depends(get_db), c: dict = Depends(role("Doctor"))):
    if c["doctorId"] != did:
        raise HTTPException(403)
    nxt = auto_call(db, did)
    db.commit()
    return {"nextCalled": p_dict(nxt) if nxt else None}


class Medical(BaseModel):
    diagnosis:   Optional[str] = None
    medications: Optional[str] = None


@app.put("/api/patients/{pid}/medical")
def update_medical(pid: str, b: Medical, db: Session = Depends(get_db), c: dict = Depends(role("Doctor"))):
    p = get_patient(db, pid)
    if p.doctor_id != c["doctorId"]:
        raise HTTPException(403)
    if p.is_medical_locked:
        raise HTTPException(409, "Tıbbi kayıt zaten kilitlenmiş")
    if p.queue_status != "Called":
        raise HTTPException(409, "Sadece muayenedeki hasta için tıbbi kayıt girilebilir")
    p.diagnosis, p.medications, p.is_medical_locked = b.diagnosis, b.medications, True
    db.commit()
    return p_dict(p)


class Proc(BaseModel):
    procedureType: str
    notes:         Optional[str] = None


@app.post("/api/patients/{pid}/procedure")
def send_procedure(pid: str, b: Proc, db: Session = Depends(get_db), c: dict = Depends(role("Doctor"))):
    p = get_patient(db, pid)
    if p.doctor_id != c["doctorId"]:
        raise HTTPException(403)
    if p.queue_status != "Called":
        raise HTTPException(409, "Sadece muayenedeki hasta tedaviye gönderilebilir")
    p.queue_status = "InProcedure"
    db.add(PatientProcedure(patient_id=pid, type=b.procedureType, notes=b.notes))
    nxt = auto_call(db, p.doctor_id)
    db.commit()
    return {"actioned": p_dict(p), "nextCalled": p_dict(nxt) if nxt else None}


@app.put("/api/patients/{pid}/return")
def return_from_proc(pid: str, db: Session = Depends(get_db), c: dict = Depends(role("Doctor"))):
    p = get_patient(db, pid)
    if p.doctor_id != c["doctorId"]:
        raise HTTPException(403)
    if p.queue_status != "InProcedure":
        raise HTTPException(409, "Hasta tedavide değil")
    now = datetime.utcnow()
    for pr in p.procedures:
        if not pr.is_completed:
            pr.is_completed, pr.completed_at = True, now
    busy = db.query(Patient).filter(
        Patient.doctor_id == c["doctorId"], Patient.queue_status == "Called"
    ).first()
    if busy:
        p.queue_status = "Waiting"
        p.queued_at    = now.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        p.queue_status = "Called"
    db.commit()
    return p_dict(p)


@app.get("/api/patients/admin/doctor/{did}/daily")
def admin_daily(did: int, db: Session = Depends(get_db), c: dict = Depends(role("Admin"))):
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    ps    = db.query(Patient).options(joinedload(Patient.procedures)).filter(
        Patient.doctor_id == did, Patient.queued_at >= today
    ).all()
    dicts = [p_dict(p) for p in ps]
    return {
        "total":       len(dicts),
        "seen":        sum(1 for p in dicts if p["queueStatus"] == "Seen"),
        "waiting":     sum(1 for p in dicts if p["queueStatus"] in ("Waiting", "Called")),
        "inProcedure": sum(1 for p in dicts if p["queueStatus"] == "InProcedure"),
        "noShow":      sum(1 for p in dicts if p["queueStatus"] == "NoShow"),
        "patients":    dicts,
    }


# ─── frontend ─────────────────────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
def index():
    return FileResponse(FRONTEND)
