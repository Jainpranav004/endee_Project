"""
chatting.py
-----------
Interactive chatbot that queries the Endee vector index and answers
using Gemini via LangChain.
"""

import os
import sys
import dotenv
dotenv.load_dotenv()

from endee import Endee
from langchain_google_genai import GoogleGenerativeAIEmbeddings, GoogleGenerativeAI


def build_clients():
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise EnvironmentError("GOOGLE_API_KEY is not set in environment.")

    embeddings = GoogleGenerativeAIEmbeddings(
        model="gemini-embedding-2-preview",
        api_key=api_key,
        output_dimensionality=768,
    )
    llm = GoogleGenerativeAI(
        model="gemini-2.0-flash",
        api_key=api_key,
    )
    return embeddings, llm


def get_index(index_name: str = "code_repo"):
    try:
        client = Endee()
        return client.get_index(index_name)
    except Exception as e:
        raise RuntimeError(f"Could not connect to Endee index '{index_name}': {e}")


def answer_query(query: str, index, embeddings, llm, top_k: int = 5) -> str:
    """Embed query, retrieve context from Endee, generate answer with Gemini."""
    try:
        vector = embeddings.embed_query(query)
    except Exception as e:
        raise RuntimeError(f"Embedding failed: {e}")

    try:
        results = index.query(vector, top_k=top_k)
    except Exception as e:
        raise RuntimeError(f"Endee query failed: {e}")

    if results:
        context_parts = []
        for r in results[:3]:
            title   = r.metadata.get("title", "N/A") if hasattr(r, "metadata") else "N/A"
            payload = r.payload if hasattr(r, "payload") else str(r)
            context_parts.append(f"File: {title}\n{payload}")
        context = "\n\n---\n\n".join(context_parts)

        prompt = (
            "You are a helpful code assistant. "
            "Use the following code snippets from the repository to answer the question.\n\n"
            f"Context:\n{context}\n\n"
            f"Question: {query}\n\n"
            "Answer:"
        )
    else:
        print("[WARN] No results found in index, answering without context.")
        prompt = query

    try:
        response = llm.generate([prompt])
        return response.generations[0][0].text
    except Exception as e:
        raise RuntimeError(f"LLM generation failed: {e}")


def main():
    print("Loading clients...")
    try:
        embeddings, llm = build_clients()
        index = get_index("code_repo")
    except Exception as e:
        print(f"[ERROR] Startup failed: {e}")
        sys.exit(1)

    print("Chatbot ready. Type 'exit' to quit.\n")

    while True:
        try:
            query = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if not query:
            continue
        if query.lower() in ("exit", "quit"):
            print("Goodbye.")
            break

        try:
            answer = answer_query(query, index, embeddings, llm)
            print(f"\nAssistant: {answer}\n")
        except Exception as e:
            print(f"[ERROR] {e}\n")


if __name__ == "__main__":
    main()
