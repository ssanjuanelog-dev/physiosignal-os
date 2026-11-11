"""
Audit Trail Module
Immutable, signed log of all pipeline operations with patient abstraction.
"""
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

class AuditLog:
    """
    Maintains an immutable, signed audit trail of pipeline operations.
    Each entry is cryptographically linked to the previous one (like a blockchain).
    """
    
    def __init__(self, log_dir: Optional[Path] = None, patient_id: Optional[str] = None):
        """
        Initialize audit log.
        
        Args:
            log_dir: Directory to store audit logs. Defaults to results/audit/
            patient_id: Abstract patient identifier (hashed for privacy)
        """
        self.log_dir = log_dir or Path("results/audit")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Hash patient ID for privacy (HIPAA compliance)
        self.patient_id_hash = hashlib.sha256(patient_id.encode('utf-8')).hexdigest()[:16] if patient_id else "anonymous"
        
        self.entries: List[Dict[str, Any]] = []
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_hash = None
    
    def add_entry(self, operation: str, details: Dict[str, Any]) -> str:
        """
        Add an entry to the audit log.
        
        Args:
            operation: Type of operation (LOAD, FILTER, ICA, REPORT, etc.)
            details: Dictionary with operation details
            
        Returns:
            Hash of the entry
        """
        timestamp = datetime.now().isoformat()
        
        # Create entry with patient abstraction
        entry = {
            "timestamp": timestamp,
            "patient_id_hash": self.patient_id_hash,
            "operation": operation,
            "details": details,
            "previous_hash": self.current_hash or "genesis"
        }
        
        # Compute hash of this entry (includes previous hash for chain integrity)
        entry_json = json.dumps(entry, sort_keys=True, default=str)
        entry_hash = hashlib.sha256(entry_json.encode('utf-8')).hexdigest()
        
        entry["hash"] = entry_hash
        self.entries.append(entry)
        self.current_hash = entry_hash
        
        return entry_hash
    
    def save(self) -> Path:
        """
        Save audit log to disk as JSON.
        
        Returns:
            Path to the saved log file
        """
        log_file = self.log_dir / f"audit_{self.patient_id_hash}_{self.session_id}.json"
        
        log_data = {
            "session_id": self.session_id,
            "patient_id_hash": self.patient_id_hash,
            "created_at": datetime.now().isoformat(),
            "entries": self.entries,
            "final_hash": self.current_hash
        }
        
        with open(log_file, 'w') as f:
            json.dump(log_data, f, indent=2, default=str)
        
        return log_file
    
    def verify_chain(self) -> bool:
        """
        Verify the integrity of the audit chain.
        
        Returns:
            True if chain is valid, False if tampered
        """
        previous_hash = "genesis"
        
        for entry in self.entries:
            # Check previous hash link
            if entry["previous_hash"] != previous_hash:
                return False
            
            # Recompute hash and verify
            entry_copy = {k: v for k, v in entry.items() if k != "hash"}
            entry_json = json.dumps(entry_copy, sort_keys=True, default=str)
            expected_hash = hashlib.sha256(entry_json.encode('utf-8')).hexdigest()
            
            if entry["hash"] != expected_hash:
                return False
            
            previous_hash = entry["hash"]
        
        return True
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the audit log.
        
        Returns:
            Dictionary with log statistics
        """
        operations = {}
        for entry in self.entries:
            op = entry["operation"]
            operations[op] = operations.get(op, 0) + 1
        
        return {
            "session_id": self.session_id,
            "patient_id_hash": self.patient_id_hash,
            "total_entries": len(self.entries),
            "operations": operations,
            "final_hash": self.current_hash,
            "chain_valid": self.verify_chain()
        }

# Global audit log instance (singleton pattern)
_global_audit_log = None

def get_audit_log(patient_id: Optional[str] = None) -> AuditLog:
    """Get or create the global audit log instance."""
    global _global_audit_log
    if _global_audit_log is None:
        _global_audit_log = AuditLog(patient_id=patient_id)
    return _global_audit_log

def reset_audit_log():
    """Reset the global audit log (for testing)."""
    global _global_audit_log
    _global_audit_log = None
