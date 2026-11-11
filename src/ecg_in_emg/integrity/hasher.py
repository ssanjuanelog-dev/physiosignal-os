"""
Cryptographic Hashing Module
SHA-256 hashing for files, data arrays, and pipeline steps.
"""
import hashlib
import numpy as np
import json
from pathlib import Path
from typing import Union, Dict, Any

class DataHasher:
    """
    Computes SHA-256 hashes for data integrity verification.
    """
    
    @staticmethod
    def hash_file(file_path: Union[str, Path]) -> str:
        """
        Compute SHA-256 hash of a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Hexadecimal SHA-256 hash string
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            # Read in 4KB chunks for memory efficiency
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        
        return sha256_hash.hexdigest()
    
    @staticmethod
    def hash_array(data: np.ndarray) -> str:
        """
        Compute SHA-256 hash of a numpy array.
        
        Args:
            data: Numpy array to hash
            
        Returns:
            Hexadecimal SHA-256 hash string
        """
        # Convert array to bytes (including shape and dtype for uniqueness)
        array_bytes = data.tobytes()
        metadata = f"{data.shape}_{data.dtype}".encode('utf-8')
        
        sha256_hash = hashlib.sha256()
        sha256_hash.update(metadata)
        sha256_hash.update(array_bytes)
        
        return sha256_hash.hexdigest()
    
    @staticmethod
    def hash_dict(data: Dict[str, Any]) -> str:
        """
        Compute SHA-256 hash of a dictionary (for pipeline configs, metadata).
        
        Args:
            data: Dictionary to hash
            
        Returns:
            Hexadecimal SHA-256 hash string
        """
        # Sort keys for deterministic hashing
        json_str = json.dumps(data, sort_keys=True, default=str)
        sha256_hash = hashlib.sha256(json_str.encode('utf-8'))
        
        return sha256_hash.hexdigest()
    
    @staticmethod
    def hash_string(text: str) -> str:
        """
        Compute SHA-256 hash of a string.
        
        Args:
            text: String to hash
            
        Returns:
            Hexadecimal SHA-256 hash string
        """
        return hashlib.sha256(text.encode('utf-8')).hexdigest()

# Convenience functions
def hash_file(file_path: Union[str, Path]) -> str:
    """Compute SHA-256 hash of a file."""
    return DataHasher.hash_file(file_path)

def hash_array(data: np.ndarray) -> str:
    """Compute SHA-256 hash of a numpy array."""
    return DataHasher.hash_array(data)

def hash_dict(data: Dict[str, Any]) -> str:
    """Compute SHA-256 hash of a dictionary."""
    return DataHasher.hash_dict(data)

def hash_string(text: str) -> str:
    """Compute SHA-256 hash of a string."""
    return DataHasher.hash_string(text)
