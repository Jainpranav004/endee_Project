"""
chunker.py
----------
Fetches a GitHub repo, chunks every file into overlapping 20-line windows,
and saves each chunk as a .json file under data/chunks/.
"""

import os
import re
import json
import hashlib
import requests
import dotenv

dotenv.load_dotenv()

# ─── CONFIG ────────────────────────────────────────────────────────────────────
WINDOW_SIZE = 20   # lines per chunk
OVERLAP     = 4    # lines shared between consecutive chunks
MIN_TOKENS  = 8    # skip chunks with fewer than this many words
OUTPUT_DIR  = "data/chunks"


# ─── HELPERS ───────────────────────────────────────────────────────────────────

def make_chunk_id(path: str, start_line: int) -> str:
    raw    = f"{path}::{start_line}"
    digest = hashlib.sha256(raw.encode()).hexdigest()[:8]
    slug   = re.sub(r"[^a-zA-Z0-9]", "_", path)[:40]
    return f"{slug}__L{start_line}__{digest}"


def count_tokens(text: str) -> int:
    return len(text.split())


def get_language(path: str) -> str:
    ext_map = {
        ".py": "python", ".js": "javascript", ".ts": "typescript",
        ".tsx": "tsx", ".jsx": "jsx", ".html": "html", ".css": "css",
        ".java": "java", ".go": "go", ".rs": "rust", ".rb": "ruby",
        ".cpp": "cpp", ".c": "c", ".md": "markdown", ".json": "json",
        ".yaml": "yaml", ".yml": "yaml", ".toml": "toml", ".sh": "bash",
    }
    _, ext = os.path.splitext(path)
    return ext_map.get(ext.lower(), "text")


# ─── CHUNKING ──────────────────────────────────────────────────────────────────

def chunk_file(file: dict) -> list:
    path     = file["path"]
    content  = file["content"]
    language = get_language(path)
    lines    = content.splitlines()
    total    = len(lines)
    chunks   = []
    stride   = WINDOW_SIZE - OVERLAP

    start = 0
    while start < total:
        end          = min(start + WINDOW_SIZE, total)
        window_text  = "\n".join(lines[start:end])
        tokens       = count_tokens(window_text)

        if tokens >= MIN_TOKENS:
            chunks.append({
                "chunk_id"   : make_chunk_id(path, start + 1),
                "file"       : path,
                "language"   : language,
                "content"    : window_text,
                "start_line" : start + 1,
                "end_line"   : end,
                "tokens"     : tokens,
            })

        if end == total:
            break
        start += stride

    return chunks


def chunk_all_files(all_files_contents: list) -> list:
    all_chunks = []
    for file in all_files_contents:
        try:
            file_chunks = chunk_file(file)
            all_chunks.extend(file_chunks)
            print(f"  chunked: {file['path']:50s}  ->  {len(file_chunks)} chunks")
        except Exception as e:
            print(f"  [WARN] skipping {file.get('path', '?')}: {e}")
    print(f"\nTotal chunks: {len(all_chunks)}")
    return all_chunks


# ─── STORAGE ───────────────────────────────────────────────────────────────────

def save_chunks(all_chunks: list, repo_name: str = "repo") -> str:
    """Save chunks to disk and return the output directory path."""
    out_dir = os.path.join(OUTPUT_DIR, repo_name)
    os.makedirs(out_dir, exist_ok=True)

    chunk_ids = []
    for chunk in all_chunks:
        file_path = os.path.join(out_dir, f"{chunk['chunk_id']}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(chunk, f, indent=2, ensure_ascii=False)
        chunk_ids.append(chunk["chunk_id"])

    index_path = os.path.join(out_dir, "index.json")
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(chunk_ids, f, indent=2)

    print(f"\nSaved {len(all_chunks)} chunks  ->  {out_dir}/")
    print(f"Index :  {index_path}")
    return out_dir  # ← fixed: was missing, used a global hack before


def load_chunk(chunk_id: str, repo_name: str) -> dict:
    """Load a single chunk by its ID. Returns None if not found."""
    path = os.path.join(OUTPUT_DIR, repo_name, f"{chunk_id}.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return None


def load_all_chunks(repo_name: str) -> list:
    """Load every chunk for a repo in the original index order."""
    index_path = os.path.join(OUTPUT_DIR, repo_name, "index.json")
    if not os.path.exists(index_path):
        print(f"No index found for repo: {repo_name}")
        return []
    with open(index_path, encoding="utf-8") as f:
        chunk_ids = json.load(f)
    return [c for cid in chunk_ids if (c := load_chunk(cid, repo_name))]


# ─── GITHUB FETCH ─────────────────────────────────────────────────────────────

def get_github_repo_contents(owner: str, repo: str, path: str = "", token: str = "") -> list:
    url     = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    headers = {"Authorization": f"token {token}"} if token else {}
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"[ERROR] GitHub API request failed for {url}: {e}")
        return []


def fetch_all_files(owner: str, repo: str, path: str = "", token: str = "") -> list:
    all_files = []
    contents  = get_github_repo_contents(owner, repo, path, token)
    for item in contents:
        try:
            if item["type"] == "file":
                resp = requests.get(item["download_url"], timeout=15)
                resp.raise_for_status()
                all_files.append({"path": item["path"], "content": resp.text})
            elif item["type"] == "dir":
                all_files.extend(fetch_all_files(owner, repo, item["path"], token))
        except requests.RequestException as e:
            print(f"[WARN] Could not fetch {item.get('path', '?')}: {e}")
    return all_files


def extract_owner_repo(url: str):
    match = re.match(r"https://github\.com/([^/]+)/([^/]+)", url)
    if match:
        return match.group(1), match.group(2)
    print("[ERROR] Invalid GitHub URL format.")
    return None, None


def extract_files(url: str) -> str:
    """Fetch, chunk, and save a GitHub repo. Returns the output directory path."""
    owner, repo = extract_owner_repo(url)
    if not owner or not repo:
        raise ValueError(f"Could not parse GitHub URL: {url}")

    token = os.getenv("GITHUB_API_KEY")
    if not token:
        raise EnvironmentError("GITHUB_API_KEY is not set in environment.")

    print(f"Fetching repo: {owner}/{repo} ...")
    all_files_contents = fetch_all_files(owner, repo, "", token)
    if not all_files_contents:
        raise RuntimeError(f"No files fetched from {url}. Check the URL and token.")

    all_chunks = chunk_all_files(all_files_contents)
    if not all_chunks:
        raise RuntimeError("Chunking produced no output. Files may be empty.")

    return save_chunks(all_chunks, repo_name=repo)


# ─── ENTRYPOINT ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    repo_url = "https://github.com/Jainpranav004/n_queen_visualiser"
    try:
        out = extract_files(repo_url)
        print(f"Done. Chunks saved to: {out}")
    except Exception as e:
        print(f"[ERROR] {e}")
