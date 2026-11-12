#!/usr/bin/env python3
"""
Run PhysioSignal OS API server.
"""
import uvicorn
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

if __name__ == "__main__":
    print("🚀 Starting PhysioSignal OS API...")
    print("📖 Swagger UI: http://localhost:8000/docs")
    print("📖 ReDoc: http://localhost:8000/redoc")
    print("\nPress Ctrl+C to stop\n")
    
    uvicorn.run(
        "physiosignal.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
