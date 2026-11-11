"""
Merkle Tree Module
For computing merkle roots of pipelines and datasets.
"""
import hashlib
from typing import List

class MerkleTree:
    """
    Merkle tree for computing cryptographic root hash of multiple items.
    """
    
    def __init__(self, data: List[str]):
        """
        Initialize merkle tree with list of data (hashes or strings).
        
        Args:
            data: List of strings or hashes
        """
        self.data = data
        self.tree = self._build_tree()
    
    def _hash(self, data: str) -> str:
        """Compute SHA-256 hash of a string."""
        return hashlib.sha256(data.encode('utf-8')).hexdigest()
    
    def _build_tree(self) -> List[List[str]]:
        """
        Build the merkle tree bottom-up.
        
        Returns:
            List of levels (each level is a list of hashes)
        """
        if not self.data:
            return []
        
        # Start with leaf nodes (hash the data if not already hashed)
        current_level = [self._hash(item) if len(item) != 64 else item for item in self.data]
        tree = [current_level]
        
        # Build tree level by level
        while len(current_level) > 1:
            next_level = []
            
            # Pair up nodes
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                right = current_level[i + 1] if i + 1 < len(current_level) else left
                
                # Hash the concatenation
                combined = self._hash(left + right)
                next_level.append(combined)
            
            tree.append(next_level)
            current_level = next_level
        
        return tree
    
    def get_root(self) -> str:
        """
        Get the merkle root hash.
        
        Returns:
            Root hash (or empty string if tree is empty)
        """
        if not self.tree:
            return ""
        return self.tree[-1][0]
    
    def get_proof(self, index: int) -> List[dict]:
        """
        Get merkle proof for a specific leaf.
        
        Args:
            index: Index of the leaf in the original data
            
        Returns:
            List of proof steps (each step has hash and direction)
        """
        if index >= len(self.data):
            raise IndexError(f"Index {index} out of range")
        
        proof = []
        current_index = index
        
        for level in self.tree[:-1]:  # Exclude root level
            if current_index % 2 == 0:
                # Current is left child, sibling is right
                sibling_index = current_index + 1
                if sibling_index < len(level):
                    proof.append({
                        "hash": level[sibling_index],
                        "direction": "right"
                    })
                else:
                    # No sibling, duplicate current
                    proof.append({
                        "hash": level[current_index],
                        "direction": "right"
                    })
            else:
                # Current is right child, sibling is left
                sibling_index = current_index - 1
                proof.append({
                    "hash": level[sibling_index],
                    "direction": "left"
                })
            
            current_index = current_index // 2
        
        return proof
    
    @staticmethod
    def verify_proof(leaf: str, proof: List[dict], root: str) -> bool:
        """
        Verify a merkle proof.
        
        Args:
            leaf: The leaf hash
            proof: List of proof steps
            root: Expected root hash
            
        Returns:
            True if proof is valid
        """
        current_hash = hashlib.sha256(leaf.encode('utf-8')).hexdigest() if len(leaf) != 64 else leaf
        
        for step in proof:
            sibling_hash = step["hash"]
            direction = step["direction"]
            
            if direction == "left":
                combined = sibling_hash + current_hash
            else:
                combined = current_hash + sibling_hash
            
            current_hash = hashlib.sha256(combined.encode('utf-8')).hexdigest()
        
        return current_hash == root
