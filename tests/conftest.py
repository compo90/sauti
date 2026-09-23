import sys
from pathlib import Path
# rend 'sauti' et 'config' importables depuis la racine du depot
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
