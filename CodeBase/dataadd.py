"""
dataadd.py
----------
Handles Endee index creation and document upsert.
"""

import dotenv
dotenv.load_dotenv()

from endee import Endee, Precision

_client = None

def _get_client() -> Endee:
    global _client
    if _client is None:
        _client = Endee()
    return _client


def get_or_create_index(name: str = "code_repo"):
    client = _get_client()
    try:
        index = client.get_index(name)
        print(f"Index '{name}' already exists, reusing it.")
        return index
    except Exception:
        print(f"Index '{name}' not found, creating it...")
        client.create_index(
            name=name,
            dimension=768,
            space_type="cosine",
            precision=Precision.INT8,
        )
        return client.get_index(name)


def load_doc(doc_list: list, index_name: str = "code_repo"):
    if not doc_list:
        print("[WARN] doc_list is empty, nothing to upsert.")
        return

    index = get_or_create_index(index_name)
    try:
        index.upsert(doc_list)
        print(f"Docs upserted to Endee index '{index_name}'. Total: {len(doc_list)}")
    except Exception as e:
        print(f"[ERROR] Failed to upsert docs: {e}")
        raise
