from pathlib import Path
import logging

ROOT_PATH = Path(__file__).resolve().parents[1]
print(ROOT_PATH)

def configure_logging():
    logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)