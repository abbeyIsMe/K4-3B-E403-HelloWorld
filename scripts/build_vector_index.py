import os
import json
import time
import re
from pathlib import Path
import numpy as np
from dotenv import load_dotenv
from google import genai

repo_root = Path(__file__).resolve().parent.parent
load_dotenv(repo_root / ".env")

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
chunks_file = repo_root / "materials/derived/chunks/all_chunks.jsonl"
embed_dir = repo_root / "materials/derived/embeddings"
embed_dir.mkdir(parents=True, exist_ok=True)

final_npy = embed_dir / "embeddings.npy"
final_meta = embed_dir / "metadata.json"
temp_npy = embed_dir / "temp_vectors.npy"

with open(chunks_file, "r", encoding="utf-8") as f:
    chunks = [json.loads(line) for line in f]

total = len(chunks)
print(f"Total chunks to index: {total}")

# Load checkpoint if exists
existing_vectors = []
if temp_npy.exists():
    try:
        existing_vectors = list(np.load(temp_npy))
        print(f"Resuming from checkpoint: {len(existing_vectors)}/{total} already embedded.")
    except Exception:
        existing_vectors = []

batch_size = 40
start_idx = len(existing_vectors)

all_vectors = list(existing_vectors)
t0 = time.time()

for i in range(start_idx, total, batch_size):
    batch = chunks[i:i + batch_size]
    texts = [f"{c.get('lesson_name', '')} | {c['source_name']} ({c['timestamp_label']}): {c['text'][:600]}" for c in batch]
    
    batch_num = i // batch_size + 1
    total_batches = (total - 1) // batch_size + 1
    
    while True:
        try:
            resp = client.models.embed_content(
                model="gemini-embedding-001",
                contents=texts
            )
            for emb in resp.embeddings:
                all_vectors.append(emb.values)
            
            # Save checkpoint
            np.save(temp_npy, np.array(all_vectors, dtype=np.float32))
            print(f"  [Batch {batch_num}/{total_batches}] Embedded {len(all_vectors)}/{total} chunks (elapsed: {time.time()-t0:.1f}s)")
            time.sleep(4.0)  # Gentle delay to stay well under 15 RPM / 100 RPM
            break
        except Exception as e:
            err_str = str(e)
            print(f"  [Batch {batch_num}/{total_batches}] API notice: {err_str[:120]}...")
            
            # Extract retry delay if available
            delay = 30
            m = re.search(r"retry in (\d+(?:\.\d+)?)s", err_str)
            if m:
                delay = int(float(m.group(1))) + 5
            elif "RESOURCE_EXHAUSTED" in err_str or "429" in err_str:
                delay = 45
                
            print(f"  Waiting {delay}s for quota window to reset...")
            time.sleep(delay)

if len(all_vectors) == total:
    embeddings_np = np.array(all_vectors, dtype=np.float32)
    norms = np.linalg.norm(embeddings_np, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    embeddings_np = embeddings_np / norms

    np.save(final_npy, embeddings_np)
    with open(final_meta, "w", encoding="utf-8") as f:
        json.dump({"model": "gemini-embedding-001", "total": total, "chunks": chunks}, f, ensure_ascii=False)

    if temp_npy.exists():
        temp_npy.unlink()

    print(f"SUCCESS: Dense Vector Index created with {total} chunks in {time.time()-t0:.1f}s!")
