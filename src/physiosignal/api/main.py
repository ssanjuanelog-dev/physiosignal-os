"""
PhysioSignal OS API
FastAPI application with REST endpoints for signal processing.
"""
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from pathlib import Path
import uuid
from datetime import datetime

from ..integrity import get_audit_log, hash_array
from ..integrity.report_generator import ClinicalReportGenerator

app = FastAPI(
    title="PhysioSignal OS API",
    description="State-of-the-art physiological signal processing platform",
    version="0.1.0",
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

# In-memory storage for demo (replace with DB in production)
analysis_results = {}

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

@app.get("/")
async def root():
    """API root endpoint."""
    return {
        "name": "PhysioSignal OS API",
        "version": "0.1.0",
        "status": "operational",
        "docs": "/docs"
    }

@app.get("/api/v1/signals", response_model=List[SignalInfo])
async def get_signals():
    """
    List all available signal types.
    """
    from ..signals import EMGSignal, EEGSignal, ECGSignal
    
    signals = [
        SignalInfo(id="emg", name="EMG", full_name="Electromyography", exam_count=2),
        SignalInfo(id="eeg", name="EEG", full_name="Electroencephalography", exam_count=2),
        SignalInfo(id="ecg", name="ECG", full_name="Electrocardiography", exam_count=2),
    ]
    return signals

@app.get("/api/v1/signals/{signal_type}/exams", response_model=List[ExamInfo])
async def get_exams(signal_type: str):
    """
    List available exams for a specific signal type.
    """
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
    }
    
    if signal_type not in exams_db:
        raise HTTPException(status_code=404, detail=f"Signal type '{signal_type}' not found")
    
    return exams_db[signal_type]

@app.post("/api/v1/analyze", response_model=AnalyzeResponse)
async def analyze_signal(request: AnalyzeRequest):
    """
    Execute signal processing pipeline.
    
    This endpoint:
    1. Loads or generates physiological data
    2. Applies the selected algorithm
    3. Generates cryptographic audit trail
    4. Creates signed clinical report
    """
    analysis_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now().isoformat()
    
    try:
        # Import processing modules
        import mne
        import numpy as np
        from ..algorithms.emg.ecg_subspace_remover import ECGSubspaceRemover
        from ..algorithms.ecg.hrv_analyzer import HRVAnalyzer
        
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
            # Run ECG Subspace Canceller
            remover = ECGSubspaceRemover(
                ref_channel_idx=request.parameters.get("ref_channel", "auto"),
                ecg_max_freq=request.parameters.get("ecg_max_freq", 25.0),
                subtraction_strength=request.parameters.get("strength", 1.5)
            )
            raw_clean = remover.fit_transform(raw_mixture)
            
            # Run HRV on cleaned signal
            hrv = HRVAnalyzer(sfreq=raw_clean.info['sfreq'])
            metrics = hrv.fit_transform(raw_clean)
            
        elif request.signal_type == "ecg" and request.exam_type == "hrv-analysis":
            # Direct HRV analysis
            hrv = HRVAnalyzer(sfreq=raw_mixture.info['sfreq'])
            metrics = hrv.fit_transform(raw_mixture)
            raw_clean = raw_mixture  # No cleaning needed
            
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
        
        # Store result
        analysis_results[analysis_id] = {
            "metrics": metrics,
            "report_path": str(report_path),
            "timestamp": timestamp
        }
        
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
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@app.get("/api/v1/reports/{analysis_id}")
async def get_report(analysis_id: str):
    """
    Retrieve analysis report by ID.
    """
    if analysis_id not in analysis_results:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    return analysis_results[analysis_id]

@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "0.1.0"
    }
