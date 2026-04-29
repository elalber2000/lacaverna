from pathlib import Path
from urllib.parse import urlparse
import logging
import base64

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer

from utils import ROOT_PATH, configure_logging


CSV_PATH = f"{ROOT_PATH}/data/posts.csv"
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def has_embedding(value) -> bool:
    if pd.isna(value):
        return False

    value = str(value).strip()
    return value not in {"", "[]", "null", "None"}


def read_text_from_local_link(link: str) -> str:
    link = str(link).strip()

    parsed = urlparse(link)
    if parsed.scheme in {"http", "https"}:
        raise ValueError(f"Remote URL, not local file: {link}")

    path = Path(link).expanduser()

    # Resolve relative paths from the CSV directory.
    if not path.is_absolute():
        path = Path(CSV_PATH).parent / path

    path = path.resolve()

    if not path.exists():
        raise FileNotFoundError(f"Local file not found: {path}")

    return path.read_text(encoding="utf-8")


def fallback_text_from_row(row) -> str:
    title = "" if pd.isna(row.get("title")) else str(row.get("title")).strip()
    description = (
        "" if pd.isna(row.get("description")) else str(row.get("description")).strip()
    )

    return f"{title}\n\n{description}".strip()


def get_embedding_text(row) -> str:
    link = row.get("link")

    try:
        if pd.isna(link) or not str(link).strip():
            raise ValueError("Empty link")

        return read_text_from_local_link(str(link).strip())

    except Exception as exc:
        fallback_text = fallback_text_from_row(row)

        if not fallback_text:
            raise ValueError(
                f"No local file and no fallback title/description for id={row.get('id')}"
            ) from exc

        logging.warning(
            f"Could not read local file for id={row.get('id')} link={link!r}. "
            f"Using title + description instead. Error: {exc}"
        )

        return fallback_text


def pack_embedding(embedding: np.ndarray) -> str:
    """
    Store embedding as base64-encoded float32 bytes.
    """
    arr = np.asarray(embedding, dtype=np.float32)
    return base64.b64encode(arr.tobytes()).decode("ascii")


def unpack_embedding(value: str) -> np.ndarray:
    """
    Decode embedding back into a numpy float32 array.
    """
    return np.frombuffer(base64.b64decode(value), dtype=np.float32)


def main():
    configure_logging()

    df = pd.read_csv(CSV_PATH)

    if "embedding" not in df.columns:
        df["embedding"] = ""

    # Important: empty CSV columns are often inferred as float64.
    # Force object dtype so pandas accepts base64 strings.
    df["embedding"] = df["embedding"].fillna("").astype(object)

    missing_mask = ~df["embedding"].apply(has_embedding)
    rows_to_embed = df[missing_mask]

    logging.info(f"Rows total: {len(df)}")
    logging.info(f"Rows missing embeddings: {len(rows_to_embed)}")

    model = SentenceTransformer(MODEL_NAME, device="cpu")

    for idx, row in rows_to_embed.iterrows():
        try:
            text = get_embedding_text(row)

            embedding = model.encode(
                text,
                normalize_embeddings=True,
            )

            df.at[idx, "embedding"] = pack_embedding(embedding)

            logging.info(f"Embedded row {idx} / id={row.get('id')}")

        except Exception as exc:
            logging.exception(f"Failed to embed row {idx} / id={row.get('id')}: {exc}")

    df.to_csv(CSV_PATH, index=False)
    logging.info(f"Saved updated CSV to {CSV_PATH}")


if __name__ == "__main__":
    main()