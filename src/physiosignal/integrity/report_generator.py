"""
Clinical Report Generator
Generates cryptographically signed JSON reports for auditability.
"""
import json
import hashlib
from datetime import datetime
from pathlib import Path
from ..integrity.signer import get_signer
from ..integrity.hasher import hash_file, hash_array

class ClinicalReportGenerator:
    """Generates and signs clinical analysis reports."""
    
    def __init__(self, patient_id: str, output_dir: Path = Path("results/reports")):
        self.patient_id_hash = hashlib.sha256(patient_id.encode()).hexdigest()[:16]
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.signer = get_signer()
        
    def generate(self, metrics: dict, input_hash: str, output_hash: str, pipeline_name: str) -> Path:
        """Generate and sign a clinical report."""
        timestamp = datetime.now().isoformat()
        
        report_data = {
            "report_id": hashlib.sha256(f"{timestamp}{pipeline_name}".encode()).hexdigest()[:12],
            "timestamp": timestamp,
            "patient_id_hash": self.patient_id_hash,
            "pipeline": pipeline_name,
            "input_data_hash": input_hash,
            "output_data_hash": output_hash,
            "clinical_metrics": metrics,
            "compliance": {
                "hipaa_ready": True,
                "audit_trail_linked": True,
                "signature_algorithm": "Ed25519"
            }
        }
        
        # Sign the report
        report_json = json.dumps(report_data, sort_keys=True)
        signature = self.signer.sign_data(report_json)
        report_data["cryptographic_signature"] = signature
        
        # Save report
        report_path = self.output_dir / f"report_{report_data['report_id']}.json"
        with open(report_path, 'w') as f:
            json.dump(report_data, f, indent=2)
            
        return report_path
