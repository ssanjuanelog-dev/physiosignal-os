"""
Tests for cryptographic integrity modules.
"""
import pytest
import numpy as np
from pathlib import Path

def test_hash_array_deterministic():
    """Test that hash_array produces consistent hashes."""
    from physiosignal.integrity.hasher import hash_array
    
    data = np.random.randn(1000)
    
    hash1 = hash_array(data)
    hash2 = hash_array(data)
    
    assert hash1 == hash2
    assert len(hash1) == 64  # SHA-256 produces 64 hex chars

def test_hash_array_different_data():
    """Test that different data produces different hashes."""
    from physiosignal.integrity.hasher import hash_array
    
    data1 = np.random.randn(1000)
    data2 = np.random.randn(1000)
    
    hash1 = hash_array(data1)
    hash2 = hash_array(data2)
    
    assert hash1 != hash2

def test_audit_log_creation():
    """Test audit log can be created and entries added."""
    from physiosignal.integrity import get_audit_log
    
    audit = get_audit_log(patient_id="TEST_PATIENT")
    
    audit.add_entry("TEST", {"message": "Test entry"})
    
    assert len(audit.entries) > 0

def test_signer_initialization():
    """Test cryptographic signer can be initialized."""
    from physiosignal.integrity.signer import get_signer
    
    signer = get_signer()
    assert signer is not None

def test_sign_data():
    """Test data can be signed."""
    from physiosignal.integrity.signer import get_signer
    
    signer = get_signer()
    
    data = "Test data to sign"
    signature = signer.sign_data(data)
    
    assert signature is not None
    assert len(signature) > 0
    # Signature should be base64 encoded
    assert isinstance(signature, str)

def test_report_generator():
    """Test clinical report generator."""
    from physiosignal.integrity.report_generator import ClinicalReportGenerator
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmpdir:
        generator = ClinicalReportGenerator(
            patient_id="TEST_PATIENT",
            output_dir=Path(tmpdir)
        )
        
        metrics = {"rmssd_ms": 42.5, "sdnn_ms": 58.3}
        report_path = generator.generate(
            metrics=metrics,
            input_hash="abc123",
            output_hash="def456",
            pipeline_name="test_pipeline"
        )
        
        assert report_path.exists()
        assert report_path.suffix == ".json"
