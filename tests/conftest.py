import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent))   # el paquete nefer
sys.path.insert(0, str(AQUI))          # los ayudantes de las pruebas
