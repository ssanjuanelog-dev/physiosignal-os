"""
Verification Module
Tools for verifying integrity of files, audit logs, and signatures.
"""
import json
from pathlib import Path
from typing import Union, Optional
from .hasher import hash_file
from .audit_log import AuditLog
from .signer import Signer

class Verifier:
    """
    Verification tools for data integrity.
    """
    
    @staticmethod
    def verify_file_integrity(file_path: Union[str, Path], expected_hash: str) -> bool:
        """
        Verify that a file matches expected hash.
        
        Args:
            file_path: Path to file
            expected_hash: Expected SHA-256 hash
            
        Returns:
            True if file matches expected hash
        """
        actual_hash = hash_file(file_path)
        return actual_hash == expected_hash
    
    @staticmethod
    def verify_audit_log(log_path: Union[str, Path]) -> dict:
        """
        Verify an audit log file.
        
        Args:
            log_path: Path to audit log JSON file
            
        Returns:
            Dictionary with verification results
        """
        log_path = Path(log_path)
        
        with open(log_path, 'r') as f:
            log_data = json.load(f)
        
        # Reconstruct audit log
        audit = AuditLog()
        audit.session_id = log_data["session_id"]
        audit.entries = log_data["entries"]
        audit.current_hash = log_data["final_hash"]
        
        # Verify chain
        chain_valid = audit.verify_chain()
        
        return {
            "session_id": log_data["session_id"],
            "total_entries": len(log_data["entries"]),
            "chain_valid": chain_valid,
            "final_hash": log_data["final_hash"],
            "created_at": log_data["created_at"]
        }
    
    @staticmethod
    def verify_signature(data: Union[str, bytes, dict], signature_b64: str, public_key_path: Optional[Path] = None) -> bool:
        """
        Verify a digital signature.
        
        Args:
            data: Original data
            signature_b64: Base64-encoded signature
            public_key_path: Path to public key file (optional)
            
        Returns:
            True if signature is valid
        """
        signer = Signer(private_key_path=public_key_path)
        return signer.verify_signature(data, signature_b64)

# Convenience functions
def verify_file(file_path: Union[str, Path], expected_hash: str) -> bool:
    """Verify file integrity."""
    return Verifier.verify_file_integrity(file_path, expected_hash)

def verify_audit(log_path: Union[str, Path]) -> dict:
    """Verify audit log."""
    return Verifier.verify_audit_log(log_path)

def verify_sig(data: Union[str, bytes, dict], signature_b64: str, public_key_path: Optional[Path] = None) -> bool:
    """Verify signature."""
    return Verifier.verify_signature(data, signature_b64, public_key_path)
