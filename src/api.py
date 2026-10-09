"""
Production REST API Server
AI-Powered Crop Pest Prediction & Advisory System
=================================================
Exposes:
- GET  /health           : Healthcheck and model readiness probe
- POST /predict          : Full prediction & advisory inference endpoint
- POST /advisory         : Decoupled agronomic advisory lookup
- POST /login            : User authentication
- POST /register         : New user registration
- GET/POST /profile      : User account profile lookup
- GET/POST /history      : Historical prediction records
- POST /report           : PDF / JSON advisory report export
- GET  /crops            : Supported crops and pest taxonomy
"""
import os
import sys
import json
import base64
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse, parse_qs
from http.server import HTTPServer, BaseHTTPRequestHandler

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.predict import predict, get_advisory, get_production_pipeline
from src.pipeline_config import MODELS_DIR
try:
    from app.database import (
        init_db,
        create_user,
        verify_user,
        get_user_by_id,
        get_user_by_email,
        get_user_prediction_history
    )
    from app.pdf_generator import generate_prediction_pdf
except (ImportError, ModuleNotFoundError):
    from database import (
        init_db,
        create_user,
        verify_user,
        get_user_by_id,
        get_user_by_email,
        get_user_prediction_history
    )
    from pdf_generator import generate_prediction_pdf

# Ensure DB is initialized
init_db()

# -------------------------------------------------------------
# FASTAPI APPLICATION (ENABLED IF FASTAPI + PYDANTIC AVAILABLE)
# -------------------------------------------------------------
app = None
try:
    from pydantic import BaseModel, Field
    from fastapi import FastAPI, HTTPException, Query, status
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse, Response

    class FarmerInputSchema(BaseModel):
        District: str = Field(default="Guntur")
        Crop_Name: str = Field(default="Cotton")
        Season: str = Field(default="Kharif")
        State: Optional[str] = Field(default="Andhra Pradesh")
        Temperature: Optional[float] = Field(default=None)
        Humidity: Optional[float] = Field(default=None)
        Rainfall: Optional[float] = Field(default=None)
        Wind_Speed: Optional[float] = Field(default=None)
        Soil_Type: Optional[str] = Field(default="Black Soil")
        Soil_Moisture: Optional[float] = Field(default=None)
        Soil_pH: Optional[float] = Field(default=None)
        Nitrogen: Optional[float] = Field(default=None)
        Phosphorus: Optional[float] = Field(default=None)
        Potassium: Optional[float] = Field(default=None)
        Organic_Carbon: Optional[float] = Field(default=None)

    class AdvisoryRequestSchema(BaseModel):
        Crop_Name: str
        Predicted_Pest: str
        Predicted_Risk: str
        Season: Optional[str] = "Kharif"
        District: Optional[str] = None
        Temperature: Optional[float] = None
        Humidity: Optional[float] = None
        Rainfall: Optional[float] = None
        Wind_Speed: Optional[float] = None
        Soil_Moisture: Optional[float] = None
        Soil_pH: Optional[float] = None
        Organic_Carbon: Optional[float] = None
        Nitrogen: Optional[float] = None
        Phosphorus: Optional[float] = None
        Potassium: Optional[float] = None

    class LoginRequestSchema(BaseModel):
        email: str
        password: str

    class RegisterRequestSchema(BaseModel):
        name: str
        email: str
        password: str
        role: Optional[str] = "farmer"

    class ProfileRequestSchema(BaseModel):
        user_id: Optional[int] = None
        email: Optional[str] = None

    class HistoryRequestSchema(BaseModel):
        user_id: int
        crop_filter: Optional[str] = None

    class ReportRequestSchema(BaseModel):
        crop: str
        state: str
        district: str
        temperature: float
        humidity: float
        rainfall: float
        predicted_pest: str
        pest_conf: float
        predicted_risk: str
        risk_conf: float
        recommendations: Optional[Dict[str, Any]] = None
        user_name: Optional[str] = "Registered Farmer"

    class WeatherRequestSchema(BaseModel):
        district: str = Field(default="Guntur")
        state: str = Field(default="Andhra Pradesh")
        sowing_season: Optional[str] = Field(default="Kharif")
        demo_mode: Optional[bool] = Field(default=False)
        demo_preset: Optional[str] = Field(default="Monsoon High Pest Outbreak")

    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def lifespan(fastapi_app: FastAPI):
        """Pre-warm production ML pipeline and knowledge base on application boot."""
        try:
            get_production_pipeline()
            load_advisory_knowledgebase()
        except Exception:
            pass
        yield

    app = FastAPI(
        title="AI Crop Pest Prediction & Advisory API",
        version="2.1.0",
        description="Production REST API for Top-3 probability-based agricultural pest diagnostics and IPM recommendations.",
        lifespan=lifespan
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health_check():
        model_exists = os.path.exists(os.path.join(MODELS_DIR, "best_model.pkl"))
        return {
            "status": "healthy" if model_exists else "unhealthy",
            "model_loaded": model_exists,
            "version": "2.1.0-Production"
        }

    @app.post("/predict")
    def predict_endpoint(payload: FarmerInputSchema):
        try:
            return predict(payload.model_dump())
        except ValueError as ve:
            raise HTTPException(status_code=400, detail=str(ve))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/advisory")
    def advisory_endpoint(payload: AdvisoryRequestSchema):
        try:
            npk = None
            if payload.Nitrogen is not None:
                npk = {
                    "Nitrogen": payload.Nitrogen,
                    "Phosphorus": payload.Phosphorus or 15.0,
                    "Potassium": payload.Potassium or 10.0
                }
            weather = None
            if payload.Temperature is not None or payload.Humidity is not None:
                weather = {
                    "temperature": payload.Temperature or 28.0,
                    "humidity": payload.Humidity or 65.0,
                    "rainfall": payload.Rainfall or 0.0,
                    "wind_speed": payload.Wind_Speed or 10.0
                }
            soil = None
            if payload.Soil_Moisture is not None or payload.Soil_pH is not None:
                soil = {
                    "soil_moisture": payload.Soil_Moisture or 50.0,
                    "soil_ph": payload.Soil_pH or 7.0,
                    "organic_carbon": payload.Organic_Carbon or 0.65
                }
            return get_advisory(
                crop=payload.Crop_Name,
                predicted_pest=payload.Predicted_Pest,
                predicted_risk=payload.Predicted_Risk,
                npk=npk,
                season=payload.Season,
                weather=weather,
                soil=soil,
                district=payload.District
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/login")
    def login_endpoint(payload: LoginRequestSchema):
        success, user_or_err = verify_user(payload.email, payload.password)
        if not success:
            raise HTTPException(status_code=401, detail=user_or_err)
        return {
            "success": True,
            "message": "Login successful",
            "user": user_or_err
        }

    @app.post("/register")
    def register_endpoint(payload: RegisterRequestSchema):
        success, user_or_err = create_user(payload.name, payload.email, payload.password, role=payload.role)
        if not success:
            raise HTTPException(status_code=400, detail=user_or_err)
        return {
            "success": True,
            "message": "User registered successfully",
            "user": user_or_err
        }

    @app.get("/profile")
    def get_profile_endpoint(user_id: Optional[int] = None, email: Optional[str] = None):
        if user_id:
            user = get_user_by_id(user_id)
        elif email:
            user = get_user_by_email(email)
        else:
            raise HTTPException(status_code=400, detail="Either user_id or email must be provided")
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        # Sanitize sensitive fields
        user.pop("password_hash", None)
        user.pop("salt", None)
        return {"success": True, "profile": user}

    @app.post("/profile")
    def post_profile_endpoint(payload: ProfileRequestSchema):
        return get_profile_endpoint(user_id=payload.user_id, email=payload.email)

    @app.get("/history")
    def get_history_endpoint(user_id: int = Query(...), crop_filter: Optional[str] = None):
        history = get_user_prediction_history(user_id, crop_filter=crop_filter)
        return {
            "success": True,
            "count": len(history),
            "history": history
        }

    @app.post("/history")
    def post_history_endpoint(payload: HistoryRequestSchema):
        return get_history_endpoint(user_id=payload.user_id, crop_filter=payload.crop_filter)

    @app.post("/report")
    def report_endpoint(payload: ReportRequestSchema):
        try:
            rec = payload.recommendations or get_advisory(payload.crop, payload.predicted_pest, payload.predicted_risk)
            pdf_bytes = generate_prediction_pdf(
                state=payload.state,
                district=payload.district,
                crop=payload.crop,
                crop_category="Cereal",
                sowing_season="Kharif",
                weather_season="Monsoon",
                temp=payload.temperature,
                humidity=payload.humidity,
                rainfall=payload.rainfall,
                thi=round(0.8 * payload.temperature + (payload.humidity / 100.0) * (payload.temperature - 14.3) + 46.4, 2),
                rf_hum_ratio=round(payload.rainfall / (payload.humidity + 1.0), 2),
                weather_source="Open-Meteo Weather API",
                predicted_pest=payload.predicted_pest,
                pest_conf=payload.pest_conf,
                predicted_risk=payload.predicted_risk,
                risk_conf=payload.risk_conf,
                recommendations=rec,
                user_name=payload.user_name
            )
            return {
                "success": True,
                "crop": payload.crop,
                "pest": payload.predicted_pest,
                "pdf_size_bytes": len(pdf_bytes),
                "pdf_base64": base64.b64encode(pdf_bytes).decode("utf-8")
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/weather")
    def get_weather_endpoint(
        district: str = Query(default="Guntur"),
        state: str = Query(default="Andhra Pradesh"),
        sowing_season: Optional[str] = Query(default="Kharif"),
        demo_mode: bool = Query(default=False)
    ):
        try:
            try:
                from app.weather import fetch_open_meteo_weather
            except (ImportError, ModuleNotFoundError):
                from weather import fetch_open_meteo_weather
            return fetch_open_meteo_weather(district, state, sowing_season=sowing_season or "Kharif", demo_mode=demo_mode)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/weather")
    def post_weather_endpoint(payload: WeatherRequestSchema):
        try:
            try:
                from app.weather import fetch_open_meteo_weather
            except (ImportError, ModuleNotFoundError):
                from weather import fetch_open_meteo_weather
            return fetch_open_meteo_weather(
                district=payload.district,
                state=payload.state,
                sowing_season=payload.sowing_season or "Kharif",
                demo_mode=payload.demo_mode or False,
                demo_preset=payload.demo_preset or "Monsoon High Pest Outbreak"
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

except ImportError:
    pass

# -------------------------------------------------------------
# ZERO-DEPENDENCY NATIVE PYTHON HTTP REST SERVER
# -------------------------------------------------------------
class NativeAPIRequestHandler(BaseHTTPRequestHandler):
    def _send_json(self, data: Dict[str, Any], status_code: int = 200):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path == "/health":
            model_exists = os.path.exists(os.path.join(MODELS_DIR, "best_model.pkl"))
            self._send_json({
                "status": "healthy" if model_exists else "unhealthy",
                "model_loaded": model_exists,
                "version": "2.1.0-Production"
            })
        elif path == "/profile":
            user_id = query.get("user_id", [None])[0]
            email = query.get("email", [None])[0]
            if user_id:
                user = get_user_by_id(int(user_id))
            elif email:
                user = get_user_by_email(email)
            else:
                self._send_json({"error": "Either user_id or email must be provided"}, status_code=400)
                return
            if not user:
                self._send_json({"error": "User not found"}, status_code=404)
                return
            user.pop("password_hash", None)
            user.pop("salt", None)
            self._send_json({"success": True, "profile": user})

        elif path == "/history":
            user_id = query.get("user_id", [None])[0]
            if not user_id:
                self._send_json({"error": "user_id is required"}, status_code=400)
                return
            crop_filter = query.get("crop_filter", [None])[0]
            history = get_user_prediction_history(int(user_id), crop_filter=crop_filter)
            self._send_json({"success": True, "count": len(history), "history": history})

        elif path == "/weather":
            try:
                try:
                    from app.weather import fetch_open_meteo_weather
                except (ImportError, ModuleNotFoundError):
                    from weather import fetch_open_meteo_weather
                district = query.get("district", ["Guntur"])[0]
                state = query.get("state", ["Andhra Pradesh"])[0]
                sowing = query.get("sowing_season", ["Kharif"])[0]
                demo = query.get("demo_mode", ["false"])[0].lower() == "true"
                w_data = fetch_open_meteo_weather(district, state, sowing_season=sowing, demo_mode=demo)
                self._send_json(w_data)
            except Exception as e:
                self._send_json({"error": str(e)}, status_code=500)

        elif path == "/crops":
            with open(os.path.join(MODELS_DIR, "feature_columns.json"), "r") as f:
                fc = json.load(f)
            self._send_json({
                "crops": ["Cotton", "Rice", "Wheat", "Sugarcane", "Soybean", "Maize", "Gram", "Mustard", "Groundnut", "Tur (Arhar)"],
                "pests": fc.get("pest_classes", []),
                "risks": fc.get("risk_classes", [])
            })
        else:
            self._send_json({"error": "Endpoint not found"}, status_code=404)

    def do_POST(self):
        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len).decode("utf-8")
        try:
            payload = json.loads(body) if body else {}
        except Exception:
            self._send_json({"error": "Invalid JSON format"}, status_code=400)
            return

        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/predict":
            try:
                res = predict(payload)
                self._send_json(res)
            except ValueError as ve:
                self._send_json({"error": str(ve)}, status_code=400)
            except Exception as e:
                self._send_json({"error": str(e)}, status_code=500)

        elif path == "/advisory":
            try:
                npk = None
                if "Nitrogen" in payload:
                    npk = {
                        "Nitrogen": payload.get("Nitrogen", 25.0),
                        "Phosphorus": payload.get("Phosphorus", 15.0),
                        "Potassium": payload.get("Potassium", 10.0)
                    }
                res = get_advisory(payload.get("Crop_Name"), payload.get("Predicted_Pest"), payload.get("Predicted_Risk"), npk=npk)
                self._send_json(res)
            except Exception as e:
                self._send_json({"error": str(e)}, status_code=500)

        elif path == "/login":
            email = payload.get("email")
            password = payload.get("password")
            if not email or not password:
                self._send_json({"error": "Email and password are required"}, status_code=400)
                return
            success, user_or_err = verify_user(email, password)
            if not success:
                self._send_json({"error": user_or_err}, status_code=401)
            else:
                self._send_json({"success": True, "message": "Login successful", "user": user_or_err})

        elif path == "/register":
            name = payload.get("name")
            email = payload.get("email")
            password = payload.get("password")
            role = payload.get("role", "farmer")
            success, user_or_err = create_user(name, email, password, role=role)
            if not success:
                self._send_json({"error": user_or_err}, status_code=400)
            else:
                self._send_json({"success": True, "message": "User registered successfully", "user": user_or_err})

        elif path == "/profile":
            user_id = payload.get("user_id")
            email = payload.get("email")
            if user_id:
                user = get_user_by_id(int(user_id))
            elif email:
                user = get_user_by_email(email)
            else:
                self._send_json({"error": "Either user_id or email must be provided"}, status_code=400)
                return
            if not user:
                self._send_json({"error": "User not found"}, status_code=404)
                return
            user.pop("password_hash", None)
            user.pop("salt", None)
            self._send_json({"success": True, "profile": user})

        elif path == "/history":
            user_id = payload.get("user_id")
            if not user_id:
                self._send_json({"error": "user_id is required"}, status_code=400)
                return
            crop_filter = payload.get("crop_filter")
            history = get_user_prediction_history(int(user_id), crop_filter=crop_filter)
            self._send_json({"success": True, "count": len(history), "history": history})

        elif path == "/report":
            try:
                crop = payload.get("crop", "Cotton")
                pest = payload.get("predicted_pest", "Whitefly")
                risk = payload.get("predicted_risk", "High")
                rec = payload.get("recommendations") or get_advisory(crop, pest, risk)
                temp = float(payload.get("temperature", 30.0))
                humidity = float(payload.get("humidity", 75.0))
                rainfall = float(payload.get("rainfall", 100.0))
                pdf_bytes = generate_prediction_pdf(
                    state=payload.get("state", "Andhra Pradesh"),
                    district=payload.get("district", "Guntur"),
                    crop=crop,
                    crop_category="Commercial",
                    sowing_season="Kharif",
                    weather_season="Monsoon",
                    temp=temp,
                    humidity=humidity,
                    rainfall=rainfall,
                    thi=round(0.8 * temp + (humidity / 100.0) * (temp - 14.3) + 46.4, 2),
                    rf_hum_ratio=round(rainfall / (humidity + 1.0), 2),
                    weather_source="Open-Meteo Weather API",
                    predicted_pest=pest,
                    pest_conf=float(payload.get("pest_conf", 85.0)),
                    predicted_risk=risk,
                    risk_conf=float(payload.get("risk_conf", 90.0)),
                    recommendations=rec,
                    user_name=payload.get("user_name", "Registered Farmer")
                )
                self._send_json({
                    "success": True,
                    "crop": crop,
                    "pest": pest,
                    "pdf_size_bytes": len(pdf_bytes),
                    "pdf_base64": base64.b64encode(pdf_bytes).decode("utf-8")
                })
            except Exception as e:
                self._send_json({"error": str(e)}, status_code=500)

        elif path == "/weather":
            try:
                try:
                    from app.weather import fetch_open_meteo_weather
                except (ImportError, ModuleNotFoundError):
                    from weather import fetch_open_meteo_weather
                district = payload.get("district", "Guntur")
                state = payload.get("state", "Andhra Pradesh")
                sowing = payload.get("sowing_season", "Kharif")
                demo = bool(payload.get("demo_mode", False))
                preset = payload.get("demo_preset", "Monsoon High Pest Outbreak")
                w_data = fetch_open_meteo_weather(district, state, sowing_season=sowing, demo_mode=demo, demo_preset=preset)
                self._send_json(w_data)
            except Exception as e:
                self._send_json({"error": str(e)}, status_code=500)
        else:
            self._send_json({"error": "Endpoint not found"}, status_code=404)

def run_server(port: int = 8000):
    if app is not None:
        try:
            import uvicorn
            print(f"Starting FastAPI Production Server on http://0.0.0.0:{port} ...")
            uvicorn.run(app, host="0.0.0.0", port=port)
            return
        except ImportError:
            pass

    print(f"Starting High-Performance Native REST Server on http://0.0.0.0:{port} ...")
    httpd = HTTPServer(("0.0.0.0", port), NativeAPIRequestHandler)
    httpd.serve_forever()

if __name__ == "__main__":
    run_server()
