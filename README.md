# 🏥 Hasta Kayıt Sistemi

Çok hastaneli, rol tabanlı bir **hasta kayıt ve kuyruk yönetim sistemi**. FastAPI tabanlı REST API ile tek sayfalı HTML arayüzünden oluşur.

---

## 🚀 Özellikler

- 🏨 **Çok Hastane Desteği** — Birden fazla hastane, kapasite ve doluluk takibi
- 👨‍⚕️ **Doktor Yönetimi** — Uzmanlık bazlı doktor listesi, günlük aktiflik durumu
- 🪑 **Triaj & Kuyruk** — Hasta triajı, otomatik sıra numarası, sıradaki hastayı çağırma
- 📋 **Tıbbi Kayıt** — Tanı ve ilaç bilgisi girişi, kilitleme mekanizması
- 🧪 **Tedavi Takibi** — Laboratuvar / röntgen / konsültasyon gibi işlem yönlendirme
- 🚫 **Gelmedi Yönetimi** — 3 kez gelmeyene otomatik pasifleştirme
- 🔐 **JWT Kimlik Doğrulama** — Admin, Doktor ve Triaj için ayrı roller
- 📊 **Admin Paneli** — Günlük hasta istatistikleri, doktor aktivasyonu, giriş bilgisi atama

---

## 🛠️ Teknolojiler

| Katman    | Teknoloji                        |
|-----------|----------------------------------|
| Backend   | Python 3.10+, FastAPI, Uvicorn   |
| Veritabanı | SQLite, SQLAlchemy ORM          |
| Güvenlik  | JWT (PyJWT), bcrypt              |
| Frontend  | Vanilla HTML / CSS / JavaScript  |

---

## 📁 Proje Yapısı

```
hastakayit-python/
├── backend/
│   ├── main.py          # FastAPI uygulama & tüm endpoint'ler
│   ├── models.py        # SQLAlchemy modelleri & seed verisi
│   └── requirements.txt # Python bağımlılıkları
└── frontend/
    └── index.html       # Tek sayfalı arayüz (SPA)
```

---

## ⚙️ Kurulum & Çalıştırma

### 1. Bağımlılıkları Yükle

```bash
cd backend
pip install -r requirements.txt
```

### 2. Sunucuyu Başlat

```bash
uvicorn main:app --reload
```

### 3. Tarayıcıda Aç

```
http://localhost:8000
```

> API dokümantasyonu: `http://localhost:8000/docs`

---

## 👥 Kullanıcı Rolleri & Test Bilgileri

Sistem ilk açılışta otomatik olarak örnek veri oluşturur.

### 🏥 Hastaneler
| ID | Hastane                   | Şehir    | Kapasite |
|----|---------------------------|----------|----------|
| 1  | Merkez Devlet Hastanesi   | İstanbul | 47       |
| 2  | Kuzey Şehir Hastanesi     | İstanbul | 30       |
| 3  | Güney Bölge Hastanesi     | İstanbul | 25       |

### 🔑 Giriş Bilgileri (tüm hesaplar için şifre: `123456`)

| Rol    | Kullanıcı Adı | Hastane  |
|--------|---------------|----------|
| Admin  | `admin1`      | Merkez   |
| Admin  | `admin2`      | Kuzey    |
| Admin  | `admin3`      | Güney    |
| Triaj  | `triaj1`      | Merkez   |
| Triaj  | `triaj2`      | Kuzey    |
| Triaj  | `triaj3`      | Güney    |

> **Not:** Doktor girişleri Admin panelinden atanır (başlangıçta şifre yoktur).

---

## 📡 API Endpoint'leri

### Auth
| Method | Endpoint                    | Açıklama          |
|--------|-----------------------------|-------------------|
| POST   | `/api/auth/admin/login`     | Admin girişi      |
| POST   | `/api/auth/doctor/login`    | Doktor girişi     |
| POST   | `/api/auth/triage/login`    | Triaj girişi      |

### Hastaneler & Doktorlar
| Method | Endpoint                              | Açıklama                        |
|--------|---------------------------------------|---------------------------------|
| GET    | `/api/hospitals`                      | Tüm hastaneler                  |
| GET    | `/api/density`                        | Hastane doluluk bilgisi         |
| GET    | `/api/doctors/hospital/{id}`          | Hastaneye göre doktorlar        |
| PUT    | `/api/doctors/{id}/toggle-active`     | Doktor aktiflik durumu (Admin)  |
| PUT    | `/api/doctors/{id}/credentials`       | Doktor giriş bilgisi (Admin)    |

### Hastalar & Kuyruk
| Method | Endpoint                                    | Açıklama                        |
|--------|---------------------------------------------|---------------------------------|
| GET    | `/api/patients/hospital/{id}`               | Aktif hastalar                  |
| POST   | `/api/patients/triage`                      | Hasta kaydı (Triaj)             |
| GET    | `/api/patients/doctor/{id}/today`           | Doktorun günlük listesi         |
| PUT    | `/api/patients/{id}/discharge`              | Hasta taburcu (Doktor)          |
| PUT    | `/api/patients/{id}/noshow`                 | Gelmedi işareti (Doktor)        |
| PUT    | `/api/patients/queue/doctor/{id}/call-next` | Sıradaki hasta (Doktor)         |
| PUT    | `/api/patients/{id}/medical`                | Tıbbi kayıt (Doktor)            |
| POST   | `/api/patients/{id}/procedure`              | Tedaviye gönder (Doktor)        |
| PUT    | `/api/patients/{id}/return`                 | Tedaviden dön (Doktor)          |
| GET    | `/api/patients/admin/doctor/{id}/daily`     | Günlük istatistik (Admin)       |

---

## 🔄 Hasta Akışı

```
Triaj → Kayıt (Waiting)
       ↓
    Doktor Çağırır (Called)
       ↓
   Muayene → Tıbbi Kayıt + İşlem
       ↓                ↓
   Taburcu (Seen)   Tedaviye Gönder (InProcedure)
                        ↓
                   Tedaviden Dön → Tekrar Muayene
```

---

## 📝 Lisans

MIT License — özgürce kullanabilirsiniz.
