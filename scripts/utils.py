from pathlib import Path
import logging

ROOT_PATH = Path(__file__).resolve().parents[1]

def configure_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def atomic_write_text(path: Path, content: str) -> None:
    """Write generated output completely before replacing the destination."""
    temporary_path = path.with_name(f".{path.name}.tmp")
    temporary_path.write_text(content, encoding="utf-8")
    temporary_path.replace(path)
