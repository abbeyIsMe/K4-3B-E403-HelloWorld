import os
import json
import time
from pathlib import Path
import numpy as np
from dotenv import load_dotenv

repo_root = Path(__file__).resolve().parent.parent
load_dotenv(repo_root / ".env")

EMBED_MODEL = "gemini-embedding-001"

def get_gemini_client():
    from google import genai
    key = os.getenv("GEMINI_API_KEY")
    if not key or not key.strip():
        raise ValueError("GEMINI_API_KEY is not set.")
    return genai.Client(api_key=key.strip())


def build_or_load_vector_index(force_rebuild=False):
    """
    Build or load dense vector embeddings for all_chunks.jsonl.
    Stores embeddings in materials/derived/embeddings/
    """
    embed_dir = repo_root / "materials/derived/embeddings"
    embed_dir.mkdir(parents=True, exist_ok=True)
    
    npy_file = embed_dir / "embeddings.npy"
    meta_file = embed_dir / "metadata.json"
    chunks_file = repo_root / "materials/derived/chunks/all_chunks.jsonl"
    
    if not chunks_file.exists():
        raise FileNotFoundError(f"Chunks file not found at {chunks_file}")

    # Load chunks
    chunks = []
    with open(chunks_file, "r", encoding="utf-8") as f:
        for line in f:
            chunks.append(json.loads(line))

    # Check if existing index is fresh
    if not force_rebuild and npy_file.exists() and meta_file.exists():
        with open(meta_file, "r", encoding="utf-8") as f:
            meta = json.load(f)
        if len(meta.get("chunks", [])) == len(chunks):
            embeddings = np.load(npy_file)
            return embeddings, chunks

    print(f"Generating semantic vector embeddings for {len(chunks)} chunks using {EMBED_MODEL}...")
    client = get_gemini_client()
    
    batch_size = 50
    all_vectors = []
    
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        texts = [f"Bài {c.get('lesson_name', '')} | {c['source_name']} ({c['timestamp_label']}): {c['text'][:800]}" for c in batch]
        
        try:
            resp = client.models.embed_content(
                model=EMBED_MODEL,
                contents=texts
            )
            for emb in resp.embeddings:
                all_vectors.append(emb.values)
            print(f"  Embedded {len(all_vectors)}/{len(chunks)} chunks...")
            time.sleep(1.0)
        except Exception as e:
            print(f"Batch embedding failed at {i}: {e}. Retrying individual chunks with backoff...")
            time.sleep(3.0)
            for c in batch:
                t = f"Bài {c.get('lesson_name', '')} | {c['source_name']} ({c['timestamp_label']}): {c['text'][:800]}"
                r = client.models.embed_content(model=EMBED_MODEL, contents=t)
                all_vectors.append(r.embeddings[0].values)
                time.sleep(0.5)

    embeddings_np = np.array(all_vectors, dtype=np.float32)
    # Normalize vectors for fast cosine similarity via dot product
    norms = np.linalg.norm(embeddings_np, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    embeddings_np = embeddings_np / norms

    np.save(npy_file, embeddings_np)
    with open(meta_file, "w", encoding="utf-8") as f:
        json.dump({"model": EMBED_MODEL, "total": len(chunks), "chunks": chunks}, f, ensure_ascii=False)

    print(f"Vector index created successfully: shape {embeddings_np.shape}")
    return embeddings_np, chunks


def embed_query(query: str):
    client = get_gemini_client()
    resp = client.models.embed_content(
        model=EMBED_MODEL,
        contents=query
    )
    vec = np.array(resp.embeddings[0].values, dtype=np.float32)
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec


def hybrid_search(query: str, lesson_id="all", allowed_sources=None, top_k=3):
    """
    Hybrid Search combining:
    1. Dense Semantic Vector Search (understanding concept meaning & context)
    2. Sparse BM25 (exact keyword match)
    Using Reciprocal Rank Fusion (RRF) with balanced source allocation.
    """
    if allowed_sources is None:
        allowed_sources = ["pdf", "video"]
        
    try:
        embeddings, chunks = build_or_load_vector_index()
    except Exception as e:
        print(f"Vector index load failed: {e}. Falling back to BM25.")
        from src.retrieval import retrieve_evidence
        return retrieve_evidence(query, lesson_id=lesson_id, allowed_sources=allowed_sources, top_k=top_k)

    # 1. Semantic Vector Similarity
    try:
        q_vec = embed_query(query)
        cos_sims = np.dot(embeddings, q_vec)
    except Exception as e:
        print(f"Query embedding failed: {e}. Falling back to BM25.")
        from src.retrieval import retrieve_evidence
        return retrieve_evidence(query, lesson_id=lesson_id, allowed_sources=allowed_sources, top_k=top_k)

    # Filter eligible indices
    pdf_indices = []
    vid_indices = []
    
    for idx, chk in enumerate(chunks):
        if lesson_id and lesson_id != "all" and chk.get("lesson_id") != lesson_id:
            continue
        if chk["source_type"] == "pdf" and "pdf" in allowed_sources:
            pdf_indices.append(idx)
        elif chk["source_type"] == "video" and "video" in allowed_sources:
            vid_indices.append(idx)

    # 2. BM25 Search
    from src.retrieval import BM25Retriever
    
    def rank_source_hybrid(eligible_indices, k_out):
        if not eligible_indices:
            return []
            
        sub_chunks = [chunks[i] for i in eligible_indices]
        
        # Vector ranking
        sub_sims = [cos_sims[i] for i in eligible_indices]
        vec_sorted_order = np.argsort(sub_sims)[::-1]
        vec_ranks = {eligible_indices[sub_idx]: rank for rank, sub_idx in enumerate(vec_sorted_order)}

        # BM25 ranking
        bm25 = BM25Retriever()
        bm25.index(sub_chunks)
        bm25_res = bm25.search(query, top_k=len(sub_chunks))
        
        bm25_ranks = {}
        for rank, (chk, _) in enumerate(bm25_res):
            # Find global index
            g_idx = next(i for i in eligible_indices if chunks[i]["chunk_id"] == chk["chunk_id"])
            bm25_ranks[g_idx] = rank

        # Reciprocal Rank Fusion (RRF)
        # RRF = 1 / (60 + rank_vector) + 1 / (60 + rank_bm25)
        rrf_scores = []
        for g_idx in eligible_indices:
            v_rank = vec_ranks.get(g_idx, 999)
            b_rank = bm25_ranks.get(g_idx, 999)
            sim = float(cos_sims[g_idx])
            
            # Semantic threshold: if vector similarity is too low (< 0.25) and BM25 has no match, skip
            if sim < 0.28 and b_rank == 999:
                continue
                
            rrf = (1.0 / (40.0 + v_rank)) + (1.0 / (40.0 + b_rank) if b_rank != 999 else 0.0)
            rrf_scores.append((rrf, sim, chunks[g_idx]))

        rrf_scores.sort(key=lambda x: x[0], reverse=True)
        
        results = []
        for rrf, sim, chk in rrf_scores[:k_out]:
            item = dict(chk)
            item["relevance_score"] = round(sim * 10, 3)
            item["rrf_score"] = round(rrf, 4)
            results.append(item)
            
        return results

    results = []
    
    # Balanced Dual Source: Get top_k from PDF and top_k from Video
    if "pdf" in allowed_sources and "video" in allowed_sources:
        pdf_res = rank_source_hybrid(pdf_indices, top_k)
        vid_res = rank_source_hybrid(vid_indices, top_k)
        results = pdf_res + vid_res
    elif "pdf" in allowed_sources:
        results = rank_source_hybrid(pdf_indices, top_k * 2)
    else:
        results = rank_source_hybrid(vid_indices, top_k * 2)

    if not results:
        return {
            "status": "NOT_FOUND",
            "reason": "Không tìm thấy nội dung có liên quan về mặt ngữ nghĩa trong các bài giảng đã chọn.",
            "chunks": []
        }

    return {
        "status": "FOUND",
        "chunks": results
    }

if __name__ == "__main__":
    build_or_load_vector_index(force_rebuild=True)
