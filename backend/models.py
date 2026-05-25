from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime
import bcrypt

engine = create_engine("sqlite:///./hastakayit.db", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class Hospital(Base):
    __tablename__ = "hospitals"
    id       = Column(Integer, primary_key=True)
    name     = Column(String, nullable=False)
    city     = Column(String, nullable=False)
    capacity = Column(Integer, default=50)


class Doctor(Base):
    __tablename__ = "doctors"
    id              = Column(Integer, primary_key=True)
    hospital_id     = Column(Integer, ForeignKey("hospitals.id"))
    name            = Column(String, nullable=False)
    surname         = Column(String, nullable=False)
    specialty       = Column(String, nullable=False)
    username        = Column(String, unique=True, nullable=True)
    password_hash   = Column(String, nullable=True)
    is_active_today = Column(Boolean, default=False)


class HospitalAdmin(Base):
    __tablename__ = "hospital_admins"
    id            = Column(Integer, primary_key=True)
    hospital_id   = Column(Integer, ForeignKey("hospitals.id"))
    username      = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)


class TriageUser(Base):
    __tablename__ = "triage_users"
    id            = Column(Integer, primary_key=True)
    hospital_id   = Column(Integer, ForeignKey("hospitals.id"))
    username      = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)


class Patient(Base):
    __tablename__ = "patients"
    id                = Column(String, primary_key=True)
    name              = Column(String, nullable=False)
    surname           = Column(String, nullable=False)
    hospital_id       = Column(Integer, ForeignKey("hospitals.id"))
    doctor_id         = Column(Integer, ForeignKey("doctors.id"), nullable=True)
    is_active         = Column(Boolean, default=True)
    admitted_at       = Column(DateTime, default=datetime.utcnow)
    discharged_at     = Column(DateTime, nullable=True)
    diagnosis         = Column(Text, nullable=True)
    medications       = Column(Text, nullable=True)
    is_medical_locked = Column(Boolean, default=False)
    queue_number      = Column(Integer, nullable=True)
    queue_status      = Column(String, default="None")  # None|Waiting|Called|InProcedure|Seen|NoShow
    no_show_count     = Column(Integer, default=0)
    queued_at         = Column(DateTime, nullable=True)
    procedures        = relationship("PatientProcedure", back_populates="patient")


class PatientProcedure(Base):
    __tablename__ = "patient_procedures"
    id           = Column(Integer, primary_key=True)
    patient_id   = Column(String, ForeignKey("patients.id"))
    type         = Column(String, nullable=False)
    notes        = Column(String, nullable=True)
    requested_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    is_completed = Column(Boolean, default=False)
    patient      = relationship("Patient", back_populates="procedures")


def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    if db.query(Hospital).count() > 0:
        db.close()
        return
    pw = bcrypt.hashpw(b"123456", bcrypt.gensalt()).decode()
    db.add_all([
        Hospital(id=1, name="Merkez Devlet Hastanesi", city="Istanbul", capacity=47),
        Hospital(id=2, name="Kuzey Şehir Hastanesi",   city="Istanbul", capacity=30),
        Hospital(id=3, name="Güney Bölge Hastanesi",   city="Istanbul", capacity=25),
        Doctor(id=1, hospital_id=1, name="Merkez", surname="DoktorA", specialty="Acil Tıp"),
        Doctor(id=2, hospital_id=1, name="Merkez", surname="DoktorB", specialty="Acil Tıp"),
        Doctor(id=3, hospital_id=1, name="Merkez", surname="DoktorC", specialty="Genel Cerrahi"),
        Doctor(id=4, hospital_id=2, name="Kuzey",  surname="DoktorA", specialty="Acil Tıp"),
        Doctor(id=5, hospital_id=2, name="Kuzey",  surname="DoktorB", specialty="Kardiyoloji"),
        Doctor(id=6, hospital_id=2, name="Kuzey",  surname="DoktorC", specialty="Acil Tıp"),
        Doctor(id=7, hospital_id=3, name="Güney",  surname="DoktorA", specialty="Acil Tıp"),
        Doctor(id=8, hospital_id=3, name="Güney",  surname="DoktorB", specialty="Dahiliye"),
        Doctor(id=9, hospital_id=3, name="Güney",  surname="DoktorC", specialty="Acil Tıp"),
        HospitalAdmin(hospital_id=1, username="admin1", password_hash=pw),
        HospitalAdmin(hospital_id=2, username="admin2", password_hash=pw),
        HospitalAdmin(hospital_id=3, username="admin3", password_hash=pw),
        TriageUser(hospital_id=1, username="triaj1", password_hash=pw),
        TriageUser(hospital_id=2, username="triaj2", password_hash=pw),
        TriageUser(hospital_id=3, username="triaj3", password_hash=pw),
    ])
    db.commit()
    db.close()
