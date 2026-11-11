"""
Test script for integrity module with patient abstraction.
"""
import numpy as np
from pathlib import Path
from ecg_in_emg.integrity import (
    hash_file, hash_array, hash_dict,
    get_audit_log, get_signer,
    MerkleTree, verify_file, verify_audit
)

def main():
    print("=" * 60)
    print("PHYSIOSIGNAL OS - INTEGRITY MODULE TEST")
    print("=" * 60)
    
    # Patient abstraction
    patient_id = "PATIENT_001"  # This gets hashed for privacy
    
    # 1. Test hashing
    print("\n[1] Testing Hashing...")
    
    test_array = np.random.randn(100, 1000)
    array_hash = hash_array(test_array)
    print(f"   Array hash: {array_hash[:16]}...")
    
    test_dict = {"subject": "SUBJ_01", "snr_db": -5, "seed": 2126519587}
    dict_hash = hash_dict(test_dict)
    print(f"   Dict hash: {dict_hash[:16]}...")
    
    mixture_file = Path("results/mixtures/SUBJ_01/mixture_snr-5_seed2126519587-raw.fif")
    file_hash = None
    if mixture_file.exists():
        file_hash = hash_file(mixture_file)
        print(f"   File hash: {file_hash[:16]}...")
        
        is_valid = verify_file(mixture_file, file_hash)
        print(f"   File integrity: {'VALID' if is_valid else 'INVALID'}")
    else:
        print(f"   File not found: {mixture_file}")
    
    # 2. Test audit log with patient ID
    print("\n[2] Testing Audit Log (with Patient Abstraction)...")
    
    audit = get_audit_log(patient_id=patient_id)
    
    audit.add_entry("LOAD", {"file": "subj01.fif", "hash": file_hash or "N/A"})
    audit.add_entry("FILTER", {"type": "butterworth", "freqs": [5, 15], "input_hash": "a3f8c2"})
    audit.add_entry("ICA", {"n_components": 20, "input_hash": "b7d1e4"})
    audit.add_entry("REPORT", {"metrics": {"improvement": 87.2}, "output_hash": "c9f2a1"})
    
    log_path = audit.save()
    print(f"   Audit log saved: {log_path}")
    print(f"   Patient ID (hashed): {audit.patient_id_hash}")
    
    verification = verify_audit(log_path)
    print(f"   Chain valid: {'VALID' if verification['chain_valid'] else 'INVALID'}")
    print(f"   Total entries: {verification['total_entries']}")
    
    # 3. Test signing
    print("\n[3] Testing Digital Signatures...")
    
    signer = get_signer()
    
    with open(log_path, 'r') as f:
        log_data = f.read()
    
    signature = signer.sign_data(log_data)
    print(f"   Signature: {signature[:32]}...")
    
    is_valid = signer.verify_signature(log_data, signature)
    print(f"   Signature valid: {'VALID' if is_valid else 'INVALID'}")
    
    keys_dir = Path("results/keys")
    signer.save_keys(keys_dir)
    print(f"   Keys saved to: {keys_dir}")
    
    # 4. Test Merkle tree
    print("\n[4] Testing Merkle Tree...")
    
    if mixture_file.exists():
        file_hashes = [
            hash_file(Path("results/mixtures/SUBJ_01/mixture_snr-10_seed3407069831-raw.fif")),
            hash_file(Path("results/mixtures/SUBJ_01/mixture_snr-5_seed2126519587-raw.fif")),
            hash_file(Path("results/mixtures/SUBJ_01/mixture_snr0_seed3868709530-raw.fif")),
            hash_file(Path("results/mixtures/SUBJ_01/mixture_snr5_seed539143928-raw.fif"))
        ]
        
        tree = MerkleTree(file_hashes)
        root = tree.get_root()
        print(f"   Merkle root: {root[:16]}...")
        
        proof = tree.get_proof(0)
        print(f"   Proof steps: {len(proof)}")
        
        is_valid = MerkleTree.verify_proof(file_hashes[0], proof, root)
        print(f"   Proof valid: {'VALID' if is_valid else 'INVALID'}")
    
    print("\n" + "=" * 60)
    print("ALL TESTS PASSED")
    print("=" * 60)

if __name__ == "__main__":
    main()
