from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from datetime import datetime, timedelta
import bcrypt
import os
import random
import math
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app, origins="*")

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///gluconova.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'gluconova-secret-key-2024')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)

db = SQLAlchemy(app)
jwt = JWTManager(app)

# ─── Models ───────────────────────────────────────────────────────────────────

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    glucose_readings = db.relationship('GlucoseReading', backref='user', lazy=True)
    food_logs = db.relationship('FoodLog', backref='user', lazy=True)

class GlucoseReading(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    value = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    source = db.Column(db.String(20), default='sensor')  # sensor | manual | simulated

class FoodLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    food_name = db.Column(db.String(200), nullable=False)
    portion = db.Column(db.Float, default=1.0)
    predicted_spike = db.Column(db.Float)
    actual_spike = db.Column(db.Float)
    gi_score = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# ─── Glycemic Index Database ───────────────────────────────────────────────────

GI_DATABASE = {
    "white bread": {"gi": 75, "carbs": 50}, "brown bread": {"gi": 50, "carbs": 45},
    "white rice": {"gi": 72, "carbs": 45}, "brown rice": {"gi": 50, "carbs": 40},
    "oatmeal": {"gi": 55, "carbs": 27}, "cornflakes": {"gi": 81, "carbs": 84},
    "apple": {"gi": 36, "carbs": 15}, "banana": {"gi": 51, "carbs": 23},
    "orange": {"gi": 43, "carbs": 12}, "grapes": {"gi": 59, "carbs": 17},
    "watermelon": {"gi": 76, "carbs": 8}, "mango": {"gi": 51, "carbs": 20},
    "potato": {"gi": 78, "carbs": 17}, "sweet potato": {"gi": 63, "carbs": 20},
    "pasta": {"gi": 49, "carbs": 31}, "whole wheat pasta": {"gi": 42, "carbs": 29},
    "milk": {"gi": 39, "carbs": 5}, "yogurt": {"gi": 36, "carbs": 6},
    "ice cream": {"gi": 57, "carbs": 28}, "chocolate": {"gi": 40, "carbs": 60},
    "coca cola": {"gi": 63, "carbs": 39}, "orange juice": {"gi": 50, "carbs": 10},
    "pizza": {"gi": 60, "carbs": 36}, "burger": {"gi": 66, "carbs": 35},
    "french fries": {"gi": 75, "carbs": 35}, "idli": {"gi": 50, "carbs": 39},
    "dosa": {"gi": 60, "carbs": 42}, "sambar": {"gi": 25, "carbs": 12},
    "chapati": {"gi": 52, "carbs": 38}, "dal": {"gi": 29, "carbs": 18},
    "biryani": {"gi": 58, "carbs": 45}, "poha": {"gi": 55, "carbs": 45},
    "upma": {"gi": 50, "carbs": 35}, "roti": {"gi": 52, "carbs": 38},
    "egg": {"gi": 0, "carbs": 1}, "chicken": {"gi": 0, "carbs": 0},
    "fish": {"gi": 0, "carbs": 0}, "salad": {"gi": 10, "carbs": 5},
    "carrot": {"gi": 39, "carbs": 10}, "broccoli": {"gi": 10, "carbs": 7},
    "lentils": {"gi": 32, "carbs": 20}, "chickpeas": {"gi": 28, "carbs": 27},
    "kidney beans": {"gi": 24, "carbs": 22}, "peanuts": {"gi": 14, "carbs": 8},
    "almonds": {"gi": 0, "carbs": 6}, "cashews": {"gi": 25, "carbs": 30},
    "honey": {"gi": 61, "carbs": 82}, "sugar": {"gi": 65, "carbs": 100},
    "cake": {"gi": 67, "carbs": 58}, "cookie": {"gi": 55, "carbs": 60},
    "donut": {"gi": 76, "carbs": 49}, "waffle": {"gi": 76, "carbs": 37}
}

def predict_glucose_spike(food_name, portion=1.0, baseline=100):
    food_lower = food_name.lower().strip()
    food_data = None
    for key, val in GI_DATABASE.items():
        if key in food_lower or food_lower in key:
            food_data = val
            break
    if not food_data:
        food_data = {"gi": 55, "carbs": 30}
    gi = food_data["gi"]
    carbs = food_data["carbs"] * portion
    gl = (gi * carbs) / 100
    spike = gl * 1.5
    return round(spike, 1), gi, round(carbs, 1)

# ─── Auth Routes ──────────────────────────────────────────────────────────────

@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data or not all(k in data for k in ['name', 'email', 'password']):
        return jsonify({'error': 'Missing required fields'}), 400
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already registered'}), 409
    pw_hash = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    user = User(name=data['name'], email=data['email'], password_hash=pw_hash)
    db.session.add(user)
    db.session.commit()
    token = create_access_token(identity=str(user.id))
    return jsonify({'token': token, 'user': {'id': user.id, 'name': user.name, 'email': user.email}}), 201

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or not all(k in data for k in ['email', 'password']):
        return jsonify({'error': 'Missing credentials'}), 400
    user = User.query.filter_by(email=data['email']).first()
    if not user or not bcrypt.checkpw(data['password'].encode('utf-8'), user.password_hash.encode('utf-8')):
        return jsonify({'error': 'Invalid credentials'}), 401
    token = create_access_token(identity=str(user.id))
    return jsonify({'token': token, 'user': {'id': user.id, 'name': user.name, 'email': user.email}}), 200

@app.route('/api/auth/me', methods=['GET'])
@jwt_required()
def me():
    uid = int(get_jwt_identity())
    user = User.query.get(uid)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify({'id': user.id, 'name': user.name, 'email': user.email}), 200

# ─── Glucose Routes ───────────────────────────────────────────────────────────

@app.route('/api/glucose/readings', methods=['GET'])
@jwt_required()
def get_readings():
    uid = int(get_jwt_identity())
    days = int(request.args.get('days', 7))
    since = datetime.utcnow() - timedelta(days=days)
    readings = GlucoseReading.query.filter(
        GlucoseReading.user_id == uid,
        GlucoseReading.timestamp >= since
    ).order_by(GlucoseReading.timestamp.asc()).all()
    return jsonify([{
        'id': r.id, 'value': r.value,
        'timestamp': r.timestamp.isoformat(),
        'source': r.source
    } for r in readings])

@app.route('/api/glucose/readings', methods=['POST'])
@jwt_required()
def add_reading():
    uid = int(get_jwt_identity())
    data = request.get_json()
    if not data or 'value' not in data:
        return jsonify({'error': 'Missing glucose value'}), 400
    reading = GlucoseReading(
        user_id=uid,
        value=float(data['value']),
        source=data.get('source', 'manual')
    )
    db.session.add(reading)
    db.session.commit()
    return jsonify({'id': reading.id, 'value': reading.value, 'timestamp': reading.timestamp.isoformat()}), 201

@app.route('/api/glucose/current', methods=['GET'])
@jwt_required()
def current_glucose():
    uid = int(get_jwt_identity())
    reading = GlucoseReading.query.filter_by(user_id=uid).order_by(GlucoseReading.timestamp.desc()).first()
    if not reading:
        return jsonify({'value': None, 'status': 'no_data'})
    val = reading.value
    if val < 70:
        status = 'low'
    elif val <= 140:
        status = 'normal'
    elif val <= 200:
        status = 'high'
    else:
        status = 'critical'
    return jsonify({'value': val, 'status': status, 'timestamp': reading.timestamp.isoformat()})

@app.route('/api/glucose/simulate', methods=['POST'])
@jwt_required()
def simulate():
    uid = int(get_jwt_identity())
    count = int(request.get_json().get('count', 50))
    base = 95
    readings = []
    for i in range(count):
        noise = random.gauss(0, 8)
        wave = 15 * math.sin(i * 0.3)
        val = max(60, min(280, base + noise + wave))
        ts = datetime.utcnow() - timedelta(hours=count - i)
        r = GlucoseReading(user_id=uid, value=round(val, 1), source='simulated', timestamp=ts)
        db.session.add(r)
        readings.append(round(val, 1))
    db.session.commit()
    return jsonify({'message': f'{count} simulated readings added', 'sample': readings[:5]}), 201

@app.route('/api/glucose/stats', methods=['GET'])
@jwt_required()
def glucose_stats():
    uid = int(get_jwt_identity())
    since = datetime.utcnow() - timedelta(days=7)
    readings = GlucoseReading.query.filter(
        GlucoseReading.user_id == uid,
        GlucoseReading.timestamp >= since
    ).all()
    if not readings:
        return jsonify({'average': 0, 'min': 0, 'max': 0, 'time_in_range': 0, 'total': 0})
    values = [r.value for r in readings]
    in_range = sum(1 for v in values if 70 <= v <= 140)
    return jsonify({
        'average': round(sum(values) / len(values), 1),
        'min': round(min(values), 1),
        'max': round(max(values), 1),
        'time_in_range': round((in_range / len(values)) * 100, 1),
        'total': len(values)
    })

# ─── Food Routes ──────────────────────────────────────────────────────────────

@app.route('/api/food/predict', methods=['POST'])
@jwt_required()
def predict_food():
    data = request.get_json()
    if not data or 'food' not in data:
        return jsonify({'error': 'Missing food name'}), 400
    food = data['food']
    portion = float(data.get('portion', 1.0))
    spike, gi, carbs = predict_glucose_spike(food, portion)
    risk = 'low' if spike < 20 else 'moderate' if spike < 40 else 'high'
    return jsonify({
        'food': food, 'portion': portion,
        'predicted_spike': spike, 'gi_score': gi,
        'carbs': carbs, 'risk_level': risk,
        'recommendation': get_recommendation(gi, spike)
    })

def get_recommendation(gi, spike):
    if gi < 30:
        return "Excellent choice! Very low glycemic impact."
    elif gi < 55:
        return "Good choice. Moderate glycemic impact, safe for most."
    elif gi < 70:
        return "Consume in moderation. Pair with protein or fiber to reduce spike."
    else:
        return "High glycemic food. Limit portion size and pair with low-GI foods."

@app.route('/api/food/log', methods=['POST'])
@jwt_required()
def log_food():
    uid = int(get_jwt_identity())
    data = request.get_json()
    if not data or 'food' not in data:
        return jsonify({'error': 'Missing food name'}), 400
    food = data['food']
    portion = float(data.get('portion', 1.0))
    spike, gi, carbs = predict_glucose_spike(food, portion)
    log = FoodLog(
        user_id=uid, food_name=food,
        portion=portion, predicted_spike=spike,
        gi_score=gi
    )
    db.session.add(log)
    db.session.commit()
    return jsonify({'id': log.id, 'food': food, 'predicted_spike': spike, 'gi_score': gi}), 201

@app.route('/api/food/logs', methods=['GET'])
@jwt_required()
def get_food_logs():
    uid = int(get_jwt_identity())
    days = int(request.args.get('days', 7))
    since = datetime.utcnow() - timedelta(days=days)
    logs = FoodLog.query.filter(
        FoodLog.user_id == uid,
        FoodLog.timestamp >= since
    ).order_by(FoodLog.timestamp.desc()).all()
    return jsonify([{
        'id': l.id, 'food': l.food_name,
        'portion': l.portion, 'predicted_spike': l.predicted_spike,
        'actual_spike': l.actual_spike, 'gi_score': l.gi_score,
        'timestamp': l.timestamp.isoformat()
    } for l in logs])

@app.route('/api/food/report', methods=['GET'])
@jwt_required()
def weekly_report():
    uid = int(get_jwt_identity())
    since = datetime.utcnow() - timedelta(days=7)
    logs = FoodLog.query.filter(FoodLog.user_id == uid, FoodLog.timestamp >= since).all()
    food_impact = {}
    for log in logs:
        key = log.food_name.lower()
        if key not in food_impact:
            food_impact[key] = {'food': log.food_name, 'count': 0, 'total_spike': 0, 'gi': log.gi_score}
        food_impact[key]['count'] += 1
        food_impact[key]['total_spike'] += log.predicted_spike or 0
    report = sorted(food_impact.values(), key=lambda x: x['total_spike'] / max(x['count'], 1), reverse=True)
    for item in report:
        item['avg_spike'] = round(item['total_spike'] / item['count'], 1)
    return jsonify({'period': '7 days', 'total_logs': len(logs), 'top_impacts': report[:10]})

@app.route('/api/food/search', methods=['GET'])
@jwt_required()
def search_food():
    q = request.args.get('q', '').lower()
    results = [{'name': k, 'gi': v['gi'], 'carbs': v['carbs']} 
               for k, v in GI_DATABASE.items() if q in k]
    return jsonify(results[:10])

# ─── Alerts ───────────────────────────────────────────────────────────────────

@app.route('/api/alerts', methods=['GET'])
@jwt_required()
def get_alerts():
    uid = int(get_jwt_identity())
    recent = GlucoseReading.query.filter_by(user_id=uid).order_by(
        GlucoseReading.timestamp.desc()).limit(20).all()
    alerts = []
    for r in recent:
        if r.value < 70:
            alerts.append({'type': 'critical', 'message': f'Low glucose: {r.value} mg/dL', 'timestamp': r.timestamp.isoformat()})
        elif r.value > 200:
            alerts.append({'type': 'critical', 'message': f'Very high glucose: {r.value} mg/dL', 'timestamp': r.timestamp.isoformat()})
        elif r.value > 140:
            alerts.append({'type': 'warning', 'message': f'Elevated glucose: {r.value} mg/dL', 'timestamp': r.timestamp.isoformat()})
    return jsonify(alerts[:5])

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)
