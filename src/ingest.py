import os
import json
from pathlib import Path

LESSON_NAMES = {
    "day-01": "Day 01: AI & LLM Foundation",
    "day-02": "Day 02: Define Problem For AI",
    "day-03": "Day 03: Design Pattern ReAct",
    "day-04": "Day 04: Prompt Engineering & Tool Calling",
    "day-05": "Day 05: AI Product Thinking & Requirement"
}

def build_all_chunks():
    repo_root = Path(__file__).resolve().parent.parent
    audit_dir = repo_root / "materials/derived/audit"
    transcripts_dir = repo_root / "materials/derived/transcripts"
    output_dir = repo_root / "materials/derived/chunks"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    inventory_path = audit_dir / "inventory.json"
    if not inventory_path.exists():
        raise FileNotFoundError(f"Inventory not found at {inventory_path}")
        
    with open(inventory_path, "r", encoding="utf-8") as f:
        inventory = json.load(f)

    all_chunks = []
    chunk_counter = 1

    # 1. Process ALL PDF slides for all lessons (Day 1 -> Day 5)
    for item in inventory.get("files", []):
        if item.get("kind") == "pdf":
            source_id = item["source_id"]
            source_path = item["path"]
            lesson_id = item.get("lesson_id", "day-01")
            source_name = Path(source_path).name
            lesson_name = LESSON_NAMES.get(lesson_id, lesson_id.upper())
            
            page_jsonl = audit_dir / "pages" / f"{source_id}.jsonl"
            if not page_jsonl.exists():
                continue
                
            with open(page_jsonl, "r", encoding="utf-8") as pf:
                for line in pf:
                    data = json.loads(line)
                    text = data.get("text", "").strip()
                    if not text:
                        continue
                    
                    chunk = {
                        "chunk_id": f"chk_{chunk_counter:04d}",
                        "lesson_id": lesson_id,
                        "lesson_name": lesson_name,
                        "source_id": source_id,
                        "source_type": "pdf",
                        "source_name": source_name,
                        "source_path": source_path,
                        "page": data["page"],
                        "start_seconds": None,
                        "end_seconds": None,
                        "timestamp_label": f"Trang {data['page']}",
                        "text": text
                    }
                    all_chunks.append(chunk)
                    chunk_counter += 1

    # 2. Process ALL available Video transcripts
    for item in inventory.get("files", []):
        if item.get("kind") == "video":
            source_id = item["source_id"]
            source_path = item["path"]
            lesson_id = item.get("lesson_id", "day-01")
            video_filename = Path(source_path).name
            base_name = Path(source_path).stem
            lesson_name = LESSON_NAMES.get(lesson_id, lesson_id.upper())
            
            # Check if transcript exists for this video
            candidate_files = [
                transcripts_dir / f"{base_name}.jsonl",
                transcripts_dir / f"{video_filename}.jsonl",
                transcripts_dir / f"{source_id}.jsonl"
            ]
            transcript_jsonl = next((p for p in candidate_files if p.exists()), None)
            
            if not transcript_jsonl:
                continue

            segments = []
            with open(transcript_jsonl, "r", encoding="utf-8") as tf:
                for line in tf:
                    try:
                        segments.append(json.loads(line))
                    except Exception:
                        pass
                        
            if not segments:
                continue

            window_size = 4
            for i in range(0, len(segments), window_size):
                window = segments[i:i + window_size]
                combined_text = " ".join([seg["text"] for seg in window]).strip()
                start_sec = window[0]["start"]
                end_sec = window[-1]["end"]
                
                start_min, start_s = divmod(int(start_sec), 60)
                end_min, end_s = divmod(int(end_sec), 60)
                ts_label = f"{start_min:02d}:{start_s:02d} - {end_min:02d}:{end_s:02d}"
                
                chunk = {
                    "chunk_id": f"chk_{chunk_counter:04d}",
                    "lesson_id": lesson_id,
                    "lesson_name": lesson_name,
                    "source_id": source_id,
                    "source_type": "video",
                    "source_name": video_filename,
                    "source_path": source_path,
                    "page": None,
                    "start_seconds": start_sec,
                    "end_seconds": end_sec,
                    "timestamp_label": ts_label,
                    "text": combined_text
                }
                all_chunks.append(chunk)
                chunk_counter += 1

    # Save unified index
    output_file = output_dir / "all_chunks.jsonl"
    with open(output_file, "w", encoding="utf-8") as out:
        for chk in all_chunks:
            out.write(json.dumps(chk, ensure_ascii=False) + "\n")
            
    print(f"Total chunks indexed: {len(all_chunks)} saved to {output_file}")
    by_lesson = {}
    for c in all_chunks:
        by_lesson[c["lesson_id"]] = by_lesson.get(c["lesson_id"], 0) + 1
    for lid, cnt in sorted(by_lesson.items()):
        print(f"  - {lid}: {cnt} chunks")
        
    return all_chunks

if __name__ == "__main__":
    build_all_chunks()
