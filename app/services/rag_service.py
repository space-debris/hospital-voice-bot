import os
from pathlib import Path
from typing import List
import chromadb
from app.config import settings


class RAGService:
    """RAG retriever using ChromaDB for hospital FAQ document search."""

    def __init__(self):
        self._client = None
        self._collection = None
        self._initialized = False

    def initialize(self):
        """Load FAQ documents and build the vector index."""
        if self._initialized:
            return

        print("Initializing RAG service...")

        # Create persistent ChromaDB client
        self._client = chromadb.Client(chromadb.Settings(
            anonymized_telemetry=False,
        ))

        # Create or get collection
        self._collection = self._client.get_or_create_collection(
            name="hospital_faqs",
            metadata={"hnsw:space": "cosine"},
        )

        # Check if already indexed
        if self._collection.count() > 0:
            print(f"RAG index already has {self._collection.count()} chunks. Skipping ingestion.")
            self._initialized = True
            return

        # Load and index FAQ documents
        faq_dir = Path(settings.FAQ_DIR)
        if not faq_dir.exists():
            print(f"Warning: FAQ directory not found at {faq_dir}")
            self._initialized = True
            return

        documents = []
        metadatas = []
        ids = []
        chunk_id = 0

        for faq_file in sorted(faq_dir.glob("*.md")):
            content = faq_file.read_text(encoding="utf-8")
            source = faq_file.stem.replace("_", " ").title()

            # Split by sections (## headers)
            chunks = self._split_into_chunks(content)

            for chunk in chunks:
                if len(chunk.strip()) < 30:  # skip tiny chunks
                    continue
                documents.append(chunk.strip())
                metadatas.append({
                    "source": source,
                    "file": faq_file.name,
                    "access_level": "public",  # all FAQs are public
                })
                ids.append(f"chunk_{chunk_id}")
                chunk_id += 1

        if documents:
            # Add to ChromaDB in batches
            batch_size = 50
            for i in range(0, len(documents), batch_size):
                self._collection.add(
                    documents=documents[i:i + batch_size],
                    metadatas=metadatas[i:i + batch_size],
                    ids=ids[i:i + batch_size],
                )

            print(f"Indexed {len(documents)} chunks from {len(list(faq_dir.glob('*.md')))} FAQ files.")
        else:
            print("No FAQ documents found to index.")

        self._initialized = True

    def _split_into_chunks(self, content: str) -> List[str]:
        """Split markdown content into meaningful chunks by sections."""
        chunks = []
        current_chunk_lines = []

        for line in content.split("\n"):
            # Split on ## headers (section boundaries)
            if line.startswith("## ") and current_chunk_lines:
                chunks.append("\n".join(current_chunk_lines))
                current_chunk_lines = [line]
            else:
                current_chunk_lines.append(line)

        # Don't forget the last chunk
        if current_chunk_lines:
            chunks.append("\n".join(current_chunk_lines))

        return chunks

    def retrieve(self, query: str, top_k: int = 4, access_level: str = "public") -> List[dict]:
        """
        Retrieve the most relevant FAQ chunks for a query.
        
        Args:
            query: User's question
            top_k: Number of results to return
            access_level: "public" for guests, "all" for registered users
        
        Returns list of {"content": str, "source": str, "score": float}
        """
        if not self._initialized or not self._collection:
            return []

        if self._collection.count() == 0:
            return []

        # Build query kwargs
        query_kwargs = {
            "query_texts": [query],
            "n_results": min(top_k, self._collection.count()),
        }

        # Filter by access level for guest users
        if access_level == "public":
            query_kwargs["where"] = {"access_level": "public"}

        results = self._collection.query(**query_kwargs)

        retrieved = []
        if results and results["documents"]:
            for doc, metadata, distance in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            ):
                # ChromaDB returns distance; lower = more similar for cosine
                relevance_score = max(0, 1 - distance)
                retrieved.append({
                    "content": doc,
                    "source": metadata.get("source", "Unknown"),
                    "file": metadata.get("file", ""),
                    "score": round(relevance_score, 3),
                })

        return retrieved


# Global RAG service instance
rag_service = RAGService()
