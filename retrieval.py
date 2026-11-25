from pathlib import Path
import re

DOCS_FOLDER = Path("nasa_docs")


def load_documents():
    documents = []

    for file in DOCS_FOLDER.glob("*.md"):
        documents.append({
            "name": file.stem,
            "text": file.read_text(encoding="utf-8")
        })

    return documents


def split_documents(documents, chunk_size=800, overlap=200):
    chunks = []

    for document in documents:
        text = document["text"]

        for i in range(0, len(text), chunk_size - overlap):
            chunks.append({
                "name": document["name"],
                "text": text[i:i + chunk_size]
            })

    return chunks


def search_documents(query, chunks, top_k=3):
    query = query.lower()

    stop_words = {
        "the", "a", "an", "is", "of", "in",
        "what", "how", "does", "to", "and"
    }

    query_words = set(re.findall(r"\w+", query)) - stop_words
    results = []

    for chunk in chunks:
        text = chunk["text"].lower()
        name = chunk["name"].lower()
        chunk_words = set(re.findall(r"\w+", text))

        score = len(query_words.intersection(chunk_words))

        if score == 0:
            continue

        if name in query_words:
            score += 5

        if query in text:
            score += 5

        if "diameter" in query_words:
            if "diameter" in chunk_words:
                score += 5
            elif "radius" in chunk_words:
                score += 4

        results.append({
            "name": chunk["name"],
            "text": chunk["text"],
            "score": score
        })

    results.sort(key=lambda x: x["score"], reverse=True)

    return results[:top_k]


if __name__ == "__main__":
    documents = load_documents()
    chunks = split_documents(documents)

    print(f"Loaded {len(documents)} NASA documents.")
    print(f"Created {len(chunks)} searchable chunks.")

    for question in ["Earth diameter", "Mars diameter"]:
        print(f"\nSearching: {question}")

        results = search_documents(question, chunks)

        for result in results:
            print(f"\nSource: {result['name']}")
            print(f"Score: {result['score']}")
            print(result["text"])