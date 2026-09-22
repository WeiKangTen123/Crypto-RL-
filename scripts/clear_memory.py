import gc
import torch
import sys

def clear_memory():
    print("--- Memory Cleanup ---")
    
    # 1. Clear Python Garbage Collector
    items_cleared = gc.collect()
    print(f"Python GC: Collected {items_cleared} objects.")
    
    # 2. Clear PyTorch MPS Cache (macOS)
    if torch.backends.mps.is_available():
        try:
            # Reclaim unused video memory from the MPS allocator
            torch.mps.empty_cache()
            print("PyTorch MPS: Cache cleared.")
        except Exception as e:
            print(f"PyTorch MPS: Failed to clear cache: {e}")
            
    # 3. Clear PyTorch CUDA Cache (if applicable)
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        print("PyTorch CUDA: Cache cleared.")

if __name__ == "__main__":
    clear_memory()
