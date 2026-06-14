import os
from pathlib import Path

def print_dir_tree(target_dir, max_depth=2, current_depth=0):
    """Prints a clean, visual directory tree up to a specified depth."""
    path = Path(target_dir)
    if not path.exists():
        print(f"  [Directory does not exist: {target_dir}]")
        return
        
    spacing = "    " * current_depth
    if current_depth == 0:
        print(f"\n📁 {path.absolute()}")
    
    try:
        # Sort directories first, then files
        items = sorted(list(path.iterdir()), key=lambda x: (x.is_file(), x.name.lower()))
        
        for item in items:
            # Skip hidden folders/files and virtual environments to keep things readable
            if item.name.startswith('.') or item.name in ['venv', '__pycache__', 'node_modules']:
                continue
                
            if item.is_dir():
                print(f"{spacing}┗━ 📂 {item.name}/")
                if current_depth < max_depth - 1:
                    print_dir_tree(item, max_depth, current_depth + 1)
            else:
                # Print file with size to help us spot empty or heavy data folders
                size_mb = item.stat().st_size / (1024 * 1024)
                print(f"{spacing}┗━ 📄 {item.name} ({size_mb:.2f} MB)")
    except Exception as e:
        print(f"{spacing}┗━ ❌ Error reading directory: {e}")

print("=" * 60)
print("🔍 INVESTIGATING FILESYSTEM PATHS")
print("=" * 60)

# 1. Check current active workspace
print("\n--- 1. CURRENT PROTOTYPE WORKSPACE ---")
print_dir_tree(".", max_depth=2)

# 2. Check the old repository data paths where raw tracks might be hidden
print("\n--- 2. OLD REPO DATA ROOT ---")
print_dir_tree(r"D:\Aayush_Acharya\Guitarica\StudyRepos\Tab-estimator", max_depth=2)

# 3. Check suspected subdirectories specifically for audio / annotations
print("\n--- 3. DEEPER LOOK: REPO DATA SUSPECTS ---")
print("Checking for raw audio tracks:")
print_dir_tree(r"D:\Aayush_Acharya\Guitarica\StudyRepos\Tab-estimator\data", max_depth=2)

print("=" * 60)