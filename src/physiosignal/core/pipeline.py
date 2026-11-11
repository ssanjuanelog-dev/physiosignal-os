"""Pipeline Engine. Composable signal processing pipelines with audit trail."""
from typing import List, Dict, Any
from ..signals.base import BaseSignal
from ..integrity import get_audit_log, hash_array

class Pipeline:
    def __init__(self, name: str, patient_id: str = None):
        self.name = name
        self.blocks = []
        self.audit = get_audit_log(patient_id=patient_id)
        self.audit.add_entry("PIPELINE_INIT", {"name": name})
    
    def add_block(self, block: Any, params: Dict[str, Any] = None):
        self.blocks.append({"block": block, "params": params or {}, "name": block.__class__.__name__})
        self.audit.add_entry("BLOCK_ADD", {"block_name": block.__class__.__name__, "params": params or {}})
    
    def execute(self, signal: BaseSignal) -> BaseSignal:
        current_data = signal.data.copy()
        self.audit.add_entry("PIPELINE_START", {"signal_type": signal.get_signal_type(), "n_channels": signal.get_n_channels()})
        
        for i, block_info in enumerate(self.blocks):
            block = block_info["block"]
            input_hash = hash_array(current_data)
            
            if hasattr(block, 'fit_transform'):
                current_data = block.fit_transform(current_data)
            elif hasattr(block, 'process'):
                current_data = block.process(current_data)
            else:
                raise ValueError(f"Block {block_info['name']} has no fit_transform or process method")
            
            output_hash = hash_array(current_data)
            self.audit.add_entry("BLOCK_EXECUTE", {"block": block_info["name"], "in": input_hash[:16], "out": output_hash[:16]})
        
        self.audit.add_entry("PIPELINE_COMPLETE", {"n_blocks": len(self.blocks)})
        return signal.__class__(data=current_data, sfreq=signal.sfreq, ch_names=signal.ch_names, ch_types=signal.ch_types)
    
    def save_audit(self): return self.audit.save()
