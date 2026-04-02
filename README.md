# 🩸 Gluconova — Non-Invasive Glucose Monitoring System

## Project Structure

```
gluconova/
├── backend/
│   ├── app.py              ← Flask backend (all APIs)
│   ├── requirements.txt    ← Python dependencies
│   └── .env                ← Environment variables
└── frontend/
    ├── index.html          ← Login / Register page
    └── dashboard.html      ← Main dashboard (all features)
```

---

## ⚡ Quick Start

### 1. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run Flask server
python app.py
```

Flask will start at: `http://localhost:5000`

---

### 2. Frontend Setup

No build step required — pure HTML/CSS/JS.

Option A — Open directly:
```
open frontend/index.html
```

Option B — Serve with Python:
```bash
cd frontend
python -m http.server 8080
# Visit http://localhost:8080
```

---

## 🔌 API Reference

### Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register new user |
| POST | `/api/auth/login` | Login & get JWT token |
| GET | `/api/auth/me` | Get current user |

### Glucose
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/glucose/current` | Latest reading + status |
| GET | `/api/glucose/readings?days=7` | Historical readings |
| POST | `/api/glucose/readings` | Add manual reading |
| POST | `/api/glucose/simulate` | ESP32 simulation |
| GET | `/api/glucose/stats` | 7-day statistics |

### Food
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/food/predict` | Predict glucose spike |
| POST | `/api/food/log` | Log a meal |
| GET | `/api/food/logs?days=7` | Recent food logs |
| GET | `/api/food/report` | Weekly report |
| GET | `/api/food/search?q=rice` | Search food database |

### Alerts
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/alerts` | Smart glucose alerts |

---

## 🔧 ESP32 Integration

To send real sensor data from ESP32, POST to:

```
POST http://<your-server-ip>:5000/api/glucose/readings
Headers: Authorization: Bearer <JWT_TOKEN>
Body: {"value": 98.5, "source": "sensor"}
```

---

## 📊 Features

- ✅ JWT Authentication (register/login)
- ✅ Real-time glucose dashboard with Chart.js
- ✅ 7-day trend visualization
- ✅ AI food impact predictor (GI database)
- ✅ Meal logging with spike history
- ✅ Weekly health report
- ✅ Smart alerts (low/high/critical)
- ✅ ESP32 sensor simulation
- ✅ SQLite database with bcrypt passwords
- ✅ 70+ foods in glycemic index database

---

## 🎨 Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Flask 2.3.3, SQLAlchemy, JWT |
| Database | SQLite + bcrypt |
| Frontend | HTML5, Tailwind CSS, Chart.js |
| Fonts | Space Grotesk + JetBrains Mono |
| Auth | JWT tokens (24hr expiry) |
