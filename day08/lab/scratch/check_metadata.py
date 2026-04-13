import sys
from pathlib import Path

# Add current dir to path to import index
sys.path.append(str(Path(__file__).parent.parent))

from index import list_chunks, inspect_metadata_coverage

print("--- Checking list_chunks ---")
list_chunks()

print("\n--- Checking metadata coverage ---")
inspect_metadata_coverage()
