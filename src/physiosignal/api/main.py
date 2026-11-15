"""
PhysioSignal OS API
FastAPI application with REST endpoints for signal processing.
"""
from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, WebSocket, WebSocketDisconnect
import asyncio
import numpy as np
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from pathlib import Path
import uuid
from datetime import datetime
from sqlalchemy.orm import Session

from ..integrity import get_audit_log, hash_array
from ..integrity.report_generator import ClinicalReportGenerator
from ..database import get_db, Patient, Analysis

app = FastAPI(
    title="PhysioSignal OS API",
    description="State-of-the-art physiological signal processing platform",
    version="0.2.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response models
class AnalyzeRequest(BaseModel):
    signal_type: str
    exam_type: str
    algorithm_id: str
    patient_id: str = "DEMO_PATIENT"
    parameters: Optional[Dict[str, Any]] = {}

class AnalyzeResponse(BaseModel):
    analysis_id: str
    status: str
    metrics: Dict[str, Any]
    report_path: str
    input_hash: str
    output_hash: str
    timestamp: str

class SignalInfo(BaseModel):
    id: str
    name: str
    full_name: str
    exam_count: int

class ExamInfo(BaseModel):
    id: str
    name: str
    description: str
    algorithm_count: int

class PatientResponse(BaseModel):
    patient_hash: str
    created_at: datetime
    total_analyses: int

class AnalysisResponse(BaseModel):
    analysis_id: str
    signal_type: str
    exam_type: str
    algorithm_id: str
    metrics: Dict[str, Any]
    status: str
    created_at: datetime

@app.get("/")
async def root():
    """API root endpoint."""
    return {
        "name": "PhysioSignal OS API",
        "version": "0.2.0",
        "status": "operational",
        "docs": "/docs"
    }

@app.get("/api/v1/signals", response_model=List[SignalInfo])
async def get_signals():
    """List all available signal types."""
    signals = [
        SignalInfo(id="emg", name="EMG", full_name="Electromyography", exam_count=2),
        SignalInfo(id="eeg", name="EEG", full_name="Electroencephalography", exam_count=2),
        SignalInfo(id="ecg", name="ECG", full_name="Electrocardiography", exam_count=2),
        SignalInfo(id="psg", name="PSG", full_name="Polysomnography", exam_count=1),
        SignalInfo(id="ppg", name="PPG", full_name="Photoplethysmography", exam_count=1),
        SignalInfo(id="eda", name="EDA", full_name="Electrodermal Activity", exam_count=1),
    ]
    return signals

@app.get("/api/v1/signals/{signal_type}/exams", response_model=List[ExamInfo])
async def get_exams(signal_type: str):
    """List available exams for a specific signal type."""
    exams_db = {
        "emg": [
            ExamInfo(id="artifact-removal", name="ECG Artifact Removal", description="Remove cardiac artifacts", algorithm_count=2),
            ExamInfo(id="force-estimation", name="Force Estimation", description="Estimate muscle force", algorithm_count=1),
        ],
        "eeg": [
            ExamInfo(id="artifact-cleaning", name="Artifact Cleaning", description="Remove blinks and artifacts", algorithm_count=1),
            ExamInfo(id="spectral-analysis", name="Spectral Analysis", description="PSD and band power", algorithm_count=1),
        ],
        "ecg": [
            ExamInfo(id="morphology-analysis", name="Morphology Analysis", description="P-QRS-T analysis", algorithm_count=1),
            ExamInfo(id="hrv-analysis", name="HRV Analysis", description="Heart rate variability", algorithm_count=1),
        ],
        "psg": [
            ExamInfo(id="sleep-staging", name="Sleep Staging", description="Automatic sleep stage classification", algorithm_count=1),
        ],
        "eda": [
            ExamInfo(id="stress-analysis", name="Stress Analysis", description="Tonic/phasic decomposition", algorithm_count=1),
        ],
        "ppg": [
            ExamInfo(id="heart-rate", name="Heart Rate", description="Extract heart rate from PPG", algorithm_count=1),
        ],
    }
    
    if signal_type not in exams_db:
        raise HTTPException(status_code=404, detail=f"Signal type '{signal_type}' not found")
    
    return exams_db[signal_type]

@app.post("/api/v1/analyze", response_model=AnalyzeResponse)
async def analyze_signal(request: AnalyzeRequest, db: Session = Depends(get_db)):
    """Execute signal processing pipeline and store results in database."""
    import hashlib
    analysis_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now().isoformat()
    
    try:
        # Import processing modules
        import mne
        import numpy as np
        from ..algorithms.emg.ecg_subspace_remover import ECGSubspaceRemover
        from ..algorithms.ecg.hrv_analyzer import HRVAnalyzer
        from ..algorithms.eeg.welch_psd import WelchPSDAnalyzer
        from ..algorithms.eda.eda_analyzer import EDAAnalyzer
        
        # Load test data
        mixture_files = list(Path("results/mixtures/SUBJ_01").glob("mixture_snr-5_seed*-raw.fif"))
        if not mixture_files:
            raise HTTPException(status_code=404, detail="No test data available. Run data generation first.")
        
        mixture_file = mixture_files[0]
        raw_mixture = mne.io.read_raw_fif(mixture_file, verbose=False)
        
        # Initialize audit
        audit = get_audit_log(patient_id=request.patient_id)
        audit.add_entry("API_REQUEST", {
            "analysis_id": analysis_id,
            "signal_type": request.signal_type,
            "exam_type": request.exam_type,
            "algorithm": request.algorithm_id
        })
        
        # Process based on signal type
        if request.signal_type == "emg" and request.exam_type == "artifact-removal":
            remover = ECGSubspaceRemover(
                ref_channel_idx=request.parameters.get("ref_channel", "auto"),
                ecg_max_freq=request.parameters.get("ecg_max_freq", 25.0),
                subtraction_strength=request.parameters.get("strength", 1.5)
            )
            raw_clean = remover.fit_transform(raw_mixture)
            
            hrv = HRVAnalyzer(sfreq=raw_clean.info['sfreq'])
            metrics = hrv.fit_transform(raw_clean)
            
        elif request.signal_type == "ecg" and request.exam_type == "hrv-analysis":
            hrv = HRVAnalyzer(sfreq=raw_mixture.info['sfreq'])
            metrics = hrv.fit_transform(raw_mixture)
            raw_clean = raw_mixture
            
        elif request.signal_type == "eeg" and request.exam_type == "spectral-analysis":
            # Run Welch PSD Analysis
            psd_analyzer = WelchPSDAnalyzer(sfreq=raw_mixture.info['sfreq'])
            metrics = psd_analyzer.fit_transform(raw_mixture)
            raw_clean = raw_mixture  # No cleaning needed for this demo
            
        elif request.signal_type == "eda" and request.exam_type == "stress-analysis":
            # Run EDA Analysis
            eda_analyzer = EDAAnalyzer(sfreq=raw_mixture.info['sfreq'])
            metrics = eda_analyzer.fit_transform(raw_mixture)
            raw_clean = raw_mixture
            
        else:
            # Default: return mock metrics for other combinations
            metrics = {
                "status": "mock",
                "message": f"Algorithm {request.algorithm_id} not yet implemented",
                "n_peaks_detected": 50,
                "mean_hr_bpm": 72.5,
                "rmssd_ms": 42.5,
                "sdnn_ms": 58.3
            }
            raw_clean = raw_mixture
        
        # Calculate hashes
        input_hash = hash_array(raw_mixture.get_data())[:16]
        output_hash = hash_array(raw_clean.get_data())[:16]
        
        # Generate signed report
        report_gen = ClinicalReportGenerator(patient_id=request.patient_id)
        report_path = report_gen.generate(
            metrics=metrics,
            input_hash=input_hash,
            output_hash=output_hash,
            pipeline_name=f"{request.signal_type}_{request.exam_type}"
        )
        
        audit.add_entry("ANALYSIS_COMPLETE", {
            "analysis_id": analysis_id,
            "metrics": metrics,
            "report": str(report_path.name)
        })
        
        # Save audit
        audit.save()
        
        # Store in database
        patient_hash = hashlib.sha256(request.patient_id.encode()).hexdigest()
        
        # Create or get patient
        patient = db.query(Patient).filter(Patient.patient_hash == patient_hash).first()
        if not patient:
            patient = Patient(patient_hash=patient_hash)
            db.add(patient)
            db.commit()
        
        # Create analysis record
        analysis = Analysis(
            id=analysis_id,
            patient_hash=patient_hash,
            signal_type=request.signal_type,
            exam_type=request.exam_type,
            algorithm_id=request.algorithm_id,
            parameters=request.parameters,
            metrics=metrics,
            input_hash=input_hash,
            output_hash=output_hash,
            report_path=str(report_path),
            status="success"
        )
        db.add(analysis)
        db.commit()
        
        return AnalyzeResponse(
            analysis_id=analysis_id,
            status="success",
            metrics=metrics,
            report_path=str(report_path),
            input_hash=input_hash,
            output_hash=output_hash,
            timestamp=timestamp
        )
        
    except Exception as e:
        # Log failed analysis
        try:
            failed_analysis = Analysis(
                id=analysis_id,
                patient_hash=hashlib.sha256(request.patient_id.encode()).hexdigest(),
                signal_type=request.signal_type,
                exam_type=request.exam_type,
                algorithm_id=request.algorithm_id,
                parameters=request.parameters,
                metrics={"error": str(e)},
                input_hash="",
                output_hash="",
                report_path="",
                status="failed"
            )
            db.add(failed_analysis)
            db.commit()
        except:
            pass
        
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@app.get("/api/v1/reports/{analysis_id}", response_model=AnalysisResponse)
async def get_report(analysis_id: str, db: Session = Depends(get_db)):
    """Retrieve analysis report by ID from database."""
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    return AnalysisResponse(
        analysis_id=analysis.id,
        signal_type=analysis.signal_type,
        exam_type=analysis.exam_type,
        algorithm_id=analysis.algorithm_id,
        metrics=analysis.metrics,
        status=analysis.status,
        created_at=analysis.created_at
    )


@app.get("/api/v1/patients", response_model=List[PatientResponse])
async def get_all_patients(db: Session = Depends(get_db)):
    """Get all patients with their analysis count."""
    patients = db.query(Patient).all()
    
    result = []
    for p in patients:
        total_analyses = db.query(Analysis).filter(Analysis.patient_hash == p.patient_hash).count()
        result.append(PatientResponse(
            patient_hash=p.patient_hash[:16] + "...",
            created_at=p.created_at,
            total_analyses=total_analyses
        ))
    
    return result

@app.get("/api/v1/patients/{patient_id}/analyses", response_model=List[AnalysisResponse])
async def get_patient_analyses(patient_id: str, db: Session = Depends(get_db)):
    """Get all analyses for a specific patient."""
    import hashlib
    patient_hash = hashlib.sha256(patient_id.encode()).hexdigest()
    
    analyses = db.query(Analysis).filter(Analysis.patient_hash == patient_hash).all()
    
    return [
        AnalysisResponse(
            analysis_id=a.id,
            signal_type=a.signal_type,
            exam_type=a.exam_type,
            algorithm_id=a.algorithm_id,
            metrics=a.metrics,
            status=a.status,
            created_at=a.created_at
        )
        for a in analyses
    ]


@app.websocket("/ws/stream")
async def websocket_stream(websocket: WebSocket):
    """
    WebSocket endpoint for real-time signal streaming.
    Simulates live physiological data (ECG-like waveform) for demo purposes.
    In production, this would connect to actual hardware (OpenBCI, etc.)
    """
    await websocket.accept()
    print("🔌 WebSocket client connected")
    
    try:
        t = 0
        while True:
            # Generate realistic ECG-like signal with noise
            # P wave + QRS complex + T wave simulation
            phase = (t * 2 * np.pi * 1.2) % (2 * np.pi)  # 1.2 Hz heart rate
            
            # Baseline + P wave
            signal = 0.1 * np.sin(phase * 0.5)
            
            # QRS complex (sharp peak around phase = pi)
            if abs(phase - np.pi) < 0.3:
                signal += 1.5 * np.exp(-((phase - np.pi) ** 2) / 0.01)
                signal -= 0.3 * np.exp(-((phase - np.pi - 0.1) ** 2) / 0.005)
            
            # T wave
            if 0.3 < (phase - np.pi) < 1.0:
                signal += 0.3 * np.sin((phase - np.pi - 0.3) * np.pi / 0.7)
            
            # Add realistic noise
            signal += np.random.normal(0, 0.05)
            
            # Send data as JSON
            await websocket.send_json({
                "timestamp": t,
                "value": float(signal),
                "signal_type": "ecg_simulation",
                "unit": "mV"
            })
            
            t += 0.01  # 100 Hz sampling rate
            await asyncio.sleep(0.01)
            
    except WebSocketDisconnect:
        print("🔌 WebSocket client disconnected")
    except Exception as e:
        print(f"❌ WebSocket error: {e}")
        try:
            await websocket.close()
        except:
            pass

@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "0.2.0",
        "database": "SQLite"
    }
