
"""
RAG Vector Store for processing PDF and Markdown files with ChromaDB.

Features:
- PDF and Markdown document loading
- Text chunking with overlap
- ChromaDB persistent vector storage
- Embedding generation
- Similarity-based document retrieval
- Source and page metadata
"""

import re
import uuid
import hashlib
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

import chromadb
from chromadb.utils import embedding_functions
from pypdf import PdfReader


@dataclass
class ChunkMetadata:
    """Metadata for a text chunk."""

    chunk_id: str
    text: str
    source: str
    source_name: str
    page: Optional[int] = None
    section: Optional[str] = None
    chunk_index: int = 0


class PolicyVectorStore:
    """
    Vector store for RAG operations with PDF and Markdown support.
    Uses ChromaDB for persistent storage.
    """

    def __init__(
        self,
        collection_name: str = "policy_documents",
        persist_path: str = "./chroma_db"
    ):

        self.collection_name = collection_name
        self.persist_path = persist_path

        self._client = None
        self._collection = None

        self._default_embedding_fn = (
            embedding_functions.DefaultEmbeddingFunction()
        )

    # --------------------------------------------------
    # INITIALIZE CHROMADB
    # --------------------------------------------------

    def _init_client(self):
        """Initialize persistent ChromaDB client and collection."""

        if self._client is None:

            Path(self.persist_path).mkdir(
                parents=True,
                exist_ok=True
            )

            self._client = chromadb.PersistentClient(
                path=self.persist_path
            )

            self._collection = self._client.get_or_create_collection(
                name=self.collection_name,
                metadata={
                    "description": "Policy documents RAG collection"
                },
                embedding_function=self._default_embedding_fn
            )

    # --------------------------------------------------
    # LOAD PDF
    # --------------------------------------------------

    def _load_pdf(self, file_path: str) -> List[Tuple[int, str]]:
        """Extract text from each PDF page."""

        try:

            reader = PdfReader(file_path)

            texts = []

            for page_number, page in enumerate(reader.pages, start=1):

                page_text = page.extract_text() or ""

                if page_text.strip():

                    texts.append(
                        (page_number, page_text.strip())
                    )

            return texts

        except Exception as e:

            print(f"Error loading PDF {file_path}: {e}")

            return []

    # --------------------------------------------------
    # LOAD MARKDOWN
    # --------------------------------------------------

    def _load_markdown(
        self,
        file_path: str
    ) -> List[Tuple[int, str]]:
        """Load Markdown content and split by headings."""

        try:

            with open(
                file_path,
                "r",
                encoding="utf-8"
            ) as file:

                content = file.read()

            if not content.strip():
                return []

            header_pattern = r"^(#{1,6})\s+(.+)$"

            matches = list(
                re.finditer(
                    header_pattern,
                    content,
                    re.MULTILINE
                )
            )

            chunks = []

            if not matches:

                return [(1, content.strip())]

            # Content before the first heading
            first_start = matches[0].start()

            introduction = content[:first_start].strip()

            if introduction:
                chunks.append((len(chunks) + 1, introduction))

            # Content under each heading
            for index, match in enumerate(matches):

                start = match.start()

                end = (
                    matches[index + 1].start()
                    if index + 1 < len(matches)
                    else len(content)
                )

                section_text = content[start:end].strip()

                if section_text:

                    chunks.append(
                        (len(chunks) + 1, section_text)
                    )

            return chunks

        except Exception as e:

            print(f"Error loading Markdown {file_path}: {e}")

            return []

    # --------------------------------------------------
    # TEXT CHUNKING
    # --------------------------------------------------

    def _chunk_text(
        self,
        text: str,
        chunk_size: int = 500,
        overlap: int = 50
    ) -> List[str]:
        """Split text into overlapping chunks."""

        if not text or not text.strip():
            return []

        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than zero")

        if overlap < 0 or overlap >= chunk_size:
            raise ValueError(
                "overlap must be non-negative and smaller than chunk_size"
            )

        chunks = []

        start = 0

        while start < len(text):

            end = min(start + chunk_size, len(text))

            chunk = text[start:end].strip()

            if chunk:
                chunks.append(chunk)

            if end == len(text):
                break

            start = end - overlap

        return chunks

    # --------------------------------------------------
    # ADD FILES
    # --------------------------------------------------

    def add_files(
        self,
        file_paths: List[str],
        batch_id: Optional[str] = None
    ) -> List[ChunkMetadata]:
        """Add PDF and Markdown files to ChromaDB."""

        if self._collection is None:
            self._init_client()

        added_metadata = []

        for file_path in file_paths:

            path_obj = Path(file_path)

            if not path_obj.exists():

                print(f"File not found: {file_path}")

                continue

            source_name = path_obj.stem

            try:

                # Load PDF
                if path_obj.suffix.lower() == ".pdf":

                    texts = self._load_pdf(str(path_obj))

                # Load Markdown
                elif path_obj.suffix.lower() in (
                    ".md",
                    ".markdown"
                ):

                    texts = self._load_markdown(str(path_obj))

                else:

                    print(f"Unsupported file type: {file_path}")

                    continue

                # Unique prefix for each source path
                source_hash = hashlib.sha1(
                    str(path_obj.resolve()).encode("utf-8")
                ).hexdigest()[:10]

                # Process each page or section
                for page_num, content in texts:

                    sub_chunks = self._chunk_text(
                        content,
                        chunk_size=300,
                        overlap=50
                    )

                    for idx, chunk_text in enumerate(sub_chunks):

                        chunk_id = (
                            f"{source_hash}_{page_num}_{idx}"
                        )

                        metadata = ChunkMetadata(
                            chunk_id=chunk_id,
                            text=chunk_text,
                            source=str(path_obj),
                            source_name=source_name,
                            page=page_num,
                            chunk_index=idx
                        )

                        added_metadata.append(metadata)

                        # Store in ChromaDB
                        self._collection.upsert(
                            ids=[chunk_id],
                            documents=[chunk_text],
                            metadatas=[{
                                "source": str(path_obj),
                                "source_name": source_name,
                                "page": page_num,
                                "chunk_index": idx,
                                "batch_id": batch_id or ""
                            }]
                        )

                print(
                    f"Successfully processed: {file_path}"
                )

            except Exception as e:

                print(
                    f"Error processing {file_path}: {e}"
                )

                continue

        return added_metadata

    # --------------------------------------------------
    # ADD PLAIN TEXT
    # --------------------------------------------------

    def add_text(
        self,
        text: str,
        source: str = "text",
        chunk_id: Optional[str] = None
    ) -> ChunkMetadata:
        """Add plain text directly to ChromaDB."""

        if self._collection is None:
            self._init_client()

        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        if not chunk_id:

            chunk_id = f"text_{uuid.uuid4().hex}"

        self._collection.upsert(
            ids=[chunk_id],
            documents=[text],
            metadatas=[{
                "source": source,
                "source_name": source,
                "chunk_index": 0
            }]
        )

        return ChunkMetadata(
            chunk_id=chunk_id,
            text=text,
            source=source,
            source_name=source,
            chunk_index=0
        )

    # --------------------------------------------------
    # QUERY VECTOR STORE
    # --------------------------------------------------

    def query(
        self,
        text: str,
        k: int = 4
    ) -> List[Dict]:
        """Retrieve similar document chunks."""

        if self._collection is None:
            self._init_client()

        if not text or not text.strip():
            return []

        if k <= 0:
            return []

        try:

            collection_count = self._collection.count()

            if collection_count == 0:
                return []

            # Avoid requesting more records than available
            n_results = min(k, collection_count)

            results = self._collection.query(
                query_texts=[text],
                n_results=n_results,
                include=[
                    "documents",
                    "metadatas",
                    "distances"
                ]
            )

            formatted_results = []

            documents = results.get("documents", [[]])[0] or []

            metadatas = results.get("metadatas", [[]])[0] or []

            distances = results.get("distances", [[]])[0] or []

            for i, doc in enumerate(documents):

                metadata = (
                    metadatas[i]
                    if i < len(metadatas) and metadatas[i]
                    else {}
                )

                distance = (
                    distances[i]
                    if i < len(distances)
                    else None
                )

                formatted_results.append({

                    "text": (
                        doc[:500] + "..."
                        if len(doc) > 500
                        else doc
                    ),

                    "source": metadata.get(
                        "source",
                        "unknown"
                    ),

                    "source_name": metadata.get(
                        "source_name",
                        "unknown"
                    ),

                    "page": metadata.get("page"),

                    "section": metadata.get("section"),

                    "chunk_id": (
                        results.get("ids", [[]])[0][i]
                        if i < len(results.get("ids", [[]])[0])
                        else ""
                    ),

                    "distance": distance

                })

            return formatted_results

        except Exception as e:

            print(f"Error querying vector store: {e}")

            return []

    # --------------------------------------------------
    # DELETE DOCUMENTS
    # --------------------------------------------------

    def delete(
        self,
        chunk_ids: List[str]
    ) -> int:
        """Delete chunks from ChromaDB."""

        if self._collection is None:
            self._init_client()

        if not chunk_ids:
            return 0

        try:

            before_count = self._collection.count()

            self._collection.delete(
                ids=chunk_ids
            )

            after_count = self._collection.count()

            return max(0, before_count - after_count)

        except Exception as e:

            print(f"Error deleting chunks: {e}")

            return 0

    # --------------------------------------------------
    # COLLECTION COUNT
    # --------------------------------------------------

    def get_collection_count(self) -> int:
        """Get the number of stored chunks."""

        if self._collection is None:
            self._init_client()

        # Correct ChromaDB collection count method
        return self._collection.count()

    # --------------------------------------------------
    # CLOSE VECTOR STORE
    # --------------------------------------------------

    def close(self):
        """Release local client and collection references."""

        self._collection = None
        self._client = None


# --------------------------------------------------
# CONVENIENCE FUNCTION
# --------------------------------------------------

def create_vector_store(
    collection_name: str = "policy_documents",
    persist_path: str = "./chroma_db"
) -> PolicyVectorStore:
    """Create a new PolicyVectorStore instance."""

    return PolicyVectorStore(
        collection_name=collection_name,
        persist_path=persist_path
    )
