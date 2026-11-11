"""
Digital Signature Module
Ed25519 signatures for reports and audit logs.
"""
import json
from pathlib import Path
from typing import Union, Optional
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives import serialization
import base64

class Signer:
    """
    Ed25519 digital signature for cryptographic verification.
    """
    
    def __init__(self, private_key_path: Optional[Path] = None):
        """
        Initialize signer with private key.
        
        Args:
            private_key_path: Path to private key file. If None, generates new key.
        """
        if private_key_path and Path(private_key_path).exists():
            # Load existing private key
            with open(private_key_path, 'rb') as f:
                private_key_bytes = f.read()
            self.private_key = serialization.load_pem_private_key(
                private_key_bytes,
                password=None
            )
        else:
            # Generate new key pair
            self.private_key = Ed25519PrivateKey.generate()
        
        self.public_key = self.private_key.public_key()
    
    def sign_data(self, data: Union[str, bytes, dict]) -> str:
        """
        Sign data with private key.
        
        Args:
            data: Data to sign (string, bytes, or dict)
            
        Returns:
            Base64-encoded signature
        """
        if isinstance(data, dict):
            data = json.dumps(data, sort_keys=True, default=str)
        
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        signature = self.private_key.sign(data)
        return base64.b64encode(signature).decode('utf-8')
    
    def verify_signature(self, data: Union[str, bytes, dict], signature_b64: str) -> bool:
        """
        Verify a signature with public key.
        
        Args:
            data: Original data
            signature_b64: Base64-encoded signature
            
        Returns:
            True if signature is valid, False otherwise
        """
        try:
            if isinstance(data, dict):
                data = json.dumps(data, sort_keys=True, default=str)
            
            if isinstance(data, str):
                data = data.encode('utf-8')
            
            signature = base64.b64decode(signature_b64)
            self.public_key.verify(signature, data)
            return True
        except Exception:
            return False
    
    def save_keys(self, directory: Path):
        """
        Save private and public keys to files.
        
        Args:
            directory: Directory to save keys
        """
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        
        # Save private key
        private_pem = self.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        with open(directory / 'private_key.pem', 'wb') as f:
            f.write(private_pem)
        
        # Save public key
        public_pem = self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        with open(directory / 'public_key.pem', 'wb') as f:
            f.write(public_pem)
    
    def get_public_key_b64(self) -> str:
        """
        Get public key as base64 string (for sharing).
        
        Returns:
            Base64-encoded public key
        """
        public_pem = self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return base64.b64encode(public_pem).decode('utf-8')

# Global signer instance
_global_signer = None

def get_signer() -> Signer:
    """Get or create the global signer instance."""
    global _global_signer
    if _global_signer is None:
        _global_signer = Signer()
    return _global_signer

def reset_signer():
    """Reset the global signer (for testing)."""
    global _global_signer
    _global_signer = None
