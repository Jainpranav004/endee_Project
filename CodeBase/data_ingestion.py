"""
data_ingestion.py
-----------------
Converts saved chunk .json files into vector documents ready for upsert.
"""

import os
import json
import dotenv
dotenv.load_dotenv()

from langchain_google_genai import GoogleGenerativeAIEmbeddings


def _get_embedding_model():
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise EnvironmentError("GOOGLE_API_KEY is not set in environment.")
    return GoogleGenerativeAIEmbeddings(
        model="gemini-embedding-2-preview",
        api_key=api_key,
        output_dimensionality=768,
    )


def do_check(data_dir: str) -> list:
    """
    Read all chunk .json files from data_dir, embed their content,
    and return a list of doc dicts ready for index.upsert().
    """
    if not os.path.isdir(data_dir):
        raise FileNotFoundError(f"Data directory not found: {data_dir}")

    embedding_model = _get_embedding_model()
    doc_list = []

    files = [f for f in os.listdir(data_dir) if f.endswith(".json") and f != "index.json"]
    if not files:
        print(f"[WARN] No chunk files found in {data_dir}")
        return doc_list

    for file in files:
        file_path = os.path.join(data_dir, file)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                json_content = json.load(f)

            required = {"chunk_id", "content", "file", "language"}
            if not required.issubset(json_content):
                print(f"[WARN] Skipping {file}: missing keys {required - json_content.keys()}")
                continue

            vector = embedding_model.embed_query(json_content["content"])

            doc_list.append({
                "id"       : json_content["chunk_id"],
                "vector"   : vector,
                "metadata" : {"title": json_content["file"]},
                "language" : json_content["language"],
                "payload"  : json_content["content"],
            })

        except (json.JSONDecodeError, KeyError, Exception) as e:
            print(f"[WARN] Skipping {file}: {e}")

    print(f"\nTotal docs loaded: {len(doc_list)}")
    return doc_list
