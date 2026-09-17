import os
import sys
import json
import time
from pathlib import Path
from faster_whisper import WhisperModel

repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))

from src.ingest import build_all_chunks

def transcribe_batch(limit=None, model_size="base"):
    audit_dir = repo_root / "materials/derived/audit"
    transcripts_dir = repo_root / "materials/derived/transcripts"
    transcripts_dir.mkdir(parents=True, exist_ok=True)
    
    with open(audit_dir / "inventory.json", "r", encoding="utf-8") as f:
        inv = json.load(f)

    videos = [f for f in inv["files"] if f["kind"] == "video"]
    
    # Sort videos by duration ascending (shortest first for quick wins)
    videos.sort(key=lambda x: x["duration_seconds"])

    pending = []
    for v in videos:
        vpath = repo_root / "materials/raw" / v["path"]
        vname = Path(v["path"]).name
        stem = Path(v["path"]).stem
        
        # Check if already transcribed
        if (transcripts_dir / f"{stem}.jsonl").exists() or (transcripts_dir / f"{vname}.jsonl").exists():
            continue
            
        if vpath.exists():
            pending.append((v, vpath, stem, vname))

    print(f"Total videos to transcribe: {len(pending)}")
    if limit:
        pending = pending[:limit]
        print(f"Limiting batch to {limit} videos.")

    if not pending:
        print("All videos are already transcribed!")
        return

    print(f"Loading faster-whisper model '{model_size}' on CPU (int8)...")
    model = WhisperModel(model_size, device="cpu", compute_type="int8")

    for i, (vmeta, vpath, stem, vname) in enumerate(pending, 1):
        print(f"\n[{i}/{len(pending)}] Transcribing {vname} ({vmeta['duration_seconds']:.1f}s)...")
        t0 = time.time()
        
        try:
            segments, info = model.transcribe(
                str(vpath),
                language="vi",
                beam_size=3,
                word_timestamps=False
            )
            
            results = []
            lines = []
            for seg in segments:
                item = {
                    "id": seg.id,
                    "start": round(seg.start, 2),
                    "end": round(seg.end, 2),
                    "text": seg.text.strip()
                }
                results.append(item)
                lines.append(f"[{item['start']:06.2f} - {item['end']:06.2f}] {item['text']}")

            jsonl_path = transcripts_dir / f"{stem}.jsonl"
            txt_path = transcripts_dir / f"{stem}.txt"

            with open(jsonl_path, "w", encoding="utf-8") as f:
                for item in results:
                    f.write(json.dumps(item, ensure_ascii=False) + "\n")

            with open(txt_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")

            dt = time.time() - t0
            print(f"  -> Done in {dt:.1f}s ({len(results)} segments)")
            
            # Rebuild index dynamically
            build_all_chunks()
            
        except Exception as e:
            print(f"  -> Failed to transcribe {vname}: {e}")

    print("\nBatch transcription complete!")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="Max number of videos to transcribe in this run")
    parser.add_argument("--model", type=str, default="base", help="Whisper model size: tiny, base, small")
    args = parser.parse_args()
    
    transcribe_batch(limit=args.limit, model_size=args.model)
