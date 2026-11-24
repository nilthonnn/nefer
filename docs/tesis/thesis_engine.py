"""
ThesisEngine - Sistema RAG Avanzado para Análisis y Estudio de Tesis
Optimizado para documentos de Ingeniería Eléctrica, Normativas y Papers Académicos.
"""

import os
import re
from typing import List, Dict, Any
from dataclasses import dataclass

# Procesamiento de PDFs e Ingesta Avanzada
import fitz  # PyMuPDF
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Vector Store y Embeddings
import chromadb
from chromadb.utils import embedding_functions

# Búsqueda Léxica (BM25)
from rank_bm25 import BM25Okapi

# LLM Engine (Anthropic Claude)
import anthropic


MODELO_CLAUDE = "claude-opus-5-5"


@dataclass
class DocumentChunk:
    chunk_id: str
    content: str
    source_file: str
    page_number: int
    metadata: Dict[str, Any]


class ThesisIngestor:
    """Extrae texto de PDFs preservando estructura, tablas y números de página."""

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 150):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n# ", "\n\n## ", "\n\n", "\n", " ", ""]
        )

    def extract_from_pdf(self, pdf_path: str) -> List[DocumentChunk]:
        chunks = []
        doc = fitz.open(pdf_path)
        filename = os.path.basename(pdf_path)

        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text")

            # Limpieza básica preservando notación científica/matemática
            cleaned_text = re.sub(r'(\n\s*){3,}', '\n\n', text)

            if not cleaned_text.strip():
                continue

            # División semántica
            page_chunks = self.splitter.split_text(cleaned_text)

            for idx, chunk in enumerate(page_chunks):
                chunk_obj = DocumentChunk(
                    chunk_id=f"{filename}_p{page_num+1}_c{idx}",
                    content=chunk,
                    source_file=filename,
                    page_number=page_num + 1,
                    metadata={
                        "source": filename,
                        "page": page_num + 1,
                        "chunk_index": idx,
                        "chunk_id": f"{filename}_p{page_num+1}_c{idx}",
                    }
                )
                chunks.append(chunk_obj)

        doc.close()
        return chunks


class HybridRetriever:
    """Búsqueda Híbrida: Vectorial (ChromaDB) + Léxica (BM25Okapi)."""

    def __init__(self, db_path: str = "./chroma_db"):
        self.chroma_client = chromadb.PersistentClient(path=db_path)
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        self.collection = self.chroma_client.get_or_create_collection(
            name="thesis_knowledge_base",
            embedding_function=self.embedding_fn
        )
        self.bm25 = None
        self.chunks_cache: List[DocumentChunk] = []

    def index_documents(self, chunks: List[DocumentChunk]):
        if not chunks:
            return

        ids = [c.chunk_id for c in chunks]
        documents = [c.content for c in chunks]
        metadatas = [c.metadata for c in chunks]

        # 1. Indexar en ChromaDB (upsert: la base es persistente y se re-ejecuta
        #    sobre los mismos PDFs; add() fallaría con IDs duplicados)
        self.collection.upsert(ids=ids, documents=documents, metadatas=metadatas)

        # 2. Indexar en BM25
        self.chunks_cache = chunks
        tokenized_corpus = [doc.lower().split() for doc in documents]
        self.bm25 = BM25Okapi(tokenized_corpus)

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        # Búsqueda Vectorial
        vector_results = self.collection.query(query_texts=[query], n_results=top_k)

        vector_chunks = []
        if vector_results['documents']:
            for doc, meta in zip(vector_results['documents'][0], vector_results['metadatas'][0]):
                vector_chunks.append({"content": doc, "metadata": meta, "score": 1.0})

        # Búsqueda Léxica (BM25)
        if self.bm25 and self.chunks_cache:
            tokenized_query = query.lower().split()
            bm25_scores = self.bm25.get_scores(tokenized_query)
            top_bm25_indices = sorted(range(len(bm25_scores)), key=lambda i: bm25_scores[i], reverse=True)[:top_k]

            for idx in top_bm25_indices:
                c = self.chunks_cache[idx]
                vector_chunks.append({"content": c.content, "metadata": c.metadata, "score": float(bm25_scores[idx])})

        # Desduplicación por fragmento (no por página: una página tiene varios
        # fragmentos y la clave por página descartaba fragmentos distintos)
        unique_results = {}
        for item in vector_chunks:
            meta = item['metadata']
            key = meta.get('chunk_id') or f"{meta['source']}_p{meta['page']}_c{meta.get('chunk_index', 0)}"
            if key not in unique_results:
                unique_results[key] = item

        return list(unique_results.values())[:top_k]


class ThesisAssistant:
    """Agente de RAG con integración nativa con Claude de Anthropic."""

    def __init__(self, retriever: HybridRetriever, api_key: str = None):
        self.retriever = retriever
        # Sin api_key explícita, el SDK resuelve ANTHROPIC_API_KEY u otro perfil configurado.
        self.client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()

    def ask(self, question: str) -> str:
        # 1. Recuperar contexto relevante
        context_items = self.retriever.search(question, top_k=5)

        context_str = ""
        for i, item in enumerate(context_items, 1):
            source = item['metadata']['source']
            page = item['metadata']['page']
            context_str += f"\n--- FUENTE [{i}]: {source} (Página {page}) ---\n{item['content']}\n"

        # 2. System Prompt Académico Estricto
        system_prompt = (
            "Eres un Asistente Experto en Revisión de Tesis de Ingeniería Eléctrica.\n"
            "Tu tarea es responder preguntas técnicas basándote ÚNICAMENTE en los fragmentos de contexto provistos.\n"
            "REGLAS OBLIGATORIAS:\n"
            "1. Cita siempre la fuente y página exacta en formato [Archivo.pdf, Pág. X].\n"
            "2. Conserva ecuaciones matemáticas y notación en formato LaTeX ($...$ o $$...$$).\n"
            "3. Si la respuesta no se encuentra en el contexto, declara objetivamente: 'Información no encontrada en las fuentes indicadas.'\n"
            "4. Sé preciso, técnico y directo en la exposición."
        )

        user_prompt = f"CONTEXTO RECUPERADO:\n{context_str}\n\nPREGUNTA DE INVESTIGACIÓN:\n{question}"

        # 3. Consulta a Claude.
        #    - `temperature` ya no se acepta en este modelo (400): el apego a las
        #      fuentes lo fija el system prompt.
        #    - El razonamiento (thinking) siempre está activo; `effort` controla
        #      su profundidad (por defecto "medium", aquí "high" por el rigor técnico).
        #    - `fallbacks="default"`: si un clasificador de seguridad declina la
        #      consulta, el servidor la reintenta en el modelo recomendado.
        response = self.client.beta.messages.create(
            model=MODELO_CLAUDE,
            max_tokens=16000,
            output_config={"effort": "high"},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )

        if response.stop_reason == "refusal":
            return "La consulta fue declinada por el modelo; reformule la pregunta."

        # La respuesta incluye bloques de thinking antes del texto: no usar content[0].
        respuesta = "".join(b.text for b in response.content if b.type == "text")
        if response.stop_reason == "max_tokens":
            respuesta += "\n\n[Respuesta truncada por límite de tokens]"
        return respuesta


# ==========================================
# EJEMPLO DE USO / PIPELINE COMPLETO
# ==========================================
if __name__ == "__main__":
    # Configurar carpeta de fuentes
    PDF_FOLDER = "./fuentes_tesis"
    os.makedirs(PDF_FOLDER, exist_ok=True)

    print("⚡ Inicializando ThesisEngine...")
    ingestor = ThesisIngestor()
    retriever = HybridRetriever()

    # Procesar todos los PDFs
    all_chunks = []
    for file in os.listdir(PDF_FOLDER):
        if file.lower().endswith(".pdf"):
            pdf_path = os.path.join(PDF_FOLDER, file)
            print(f"📖 Ingeriendo: {file}...")
            chunks = ingestor.extract_from_pdf(pdf_path)
            all_chunks.extend(chunks)

    if all_chunks:
        print(f"🧩 Total de fragmentos procesados: {len(all_chunks)}")
        retriever.index_documents(all_chunks)

        assistant = ThesisAssistant(retriever)

        # Consulta de prueba
        pregunta = "¿Cuáles son las normas técnicas y criterios de derating por altitud a 4500 msnm para el BESS?"
        print(f"\n❓ Pregunta: {pregunta}\n")
        respuesta = assistant.ask(pregunta)
        print("🤖 Respuesta del Asistente:\n")
        print(respuesta)
    else:
        print(f"⚠️ Coloque sus archivos PDF en la carpeta '{PDF_FOLDER}' y vuelva a ejecutar.")
