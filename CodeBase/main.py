"""
main.py
-------
Entry point: fetch a GitHub repo, chunk it, embed it, and load into Endee.
"""

import os
import sys
import dotenv
dotenv.load_dotenv()

from chunker import extract_files
from data_ingestion import do_check
from dataadd import load_doc


def main():
    repo_url = "https://github.com/Bhavya0608-hub/Resume-Screening-with-Machine-Learning-Job-Recommendations-Parsing-Categorization"
    token    = os.getenv("GITHUB_API_KEY")

    if not repo_url:
        print("[ERROR] repo_url is not set.")
        sys.exit(1)

    if not token:
        print("[ERROR] GITHUB_API_KEY is not set in environment.")
        sys.exit(1)

    chunks_base = "data/chunks"

    # Determine output dir: reuse existing chunks if present
    if os.path.isdir(chunks_base) and os.listdir(chunks_base):
        existing = os.listdir(chunks_base)
        data_out_dir = os.path.join(chunks_base, existing[0])
        print(f"Data chunks already exist, reusing: {data_out_dir}")
    else:
        try:
            data_out_dir = extract_files(repo_url)
        except Exception as e:
            print(f"[ERROR] Failed to extract files: {e}")
            sys.exit(1)

    if not data_out_dir:
        print("[ERROR] No output directory returned from extract_files.")
        sys.exit(1)

    try:
        doc_list = do_check(data_out_dir)
    except Exception as e:
        print(f"[ERROR] Failed during data ingestion: {e}")
        sys.exit(1)

    if not doc_list:
        print("[ERROR] No documents were produced. Aborting upsert.")
        sys.exit(1)

    try:
        load_doc(doc_list)
    except Exception as e:
        print(f"[ERROR] Failed to load docs into Endee: {e}")
        sys.exit(1)

    print("Pipeline complete.")


if __name__ == "__main__":
    main()
