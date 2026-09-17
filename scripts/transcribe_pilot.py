import os
import json
import time
from pathlib import Path
from faster_whisper import WhisperModel

def transcribe_pilot():
    repo_root = Path(__file__).resolve().parent.parent
    video_path = repo_root / "materials/raw/Data hackathon/videos/day01/Day1-Token-Context.mp4"
    output_dir = repo_root / "materials/derived/transcripts"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    jsonl_path = output_dir / "Day1-Token-Context.jsonl"
    txt_path = output_dir / "Day1-Token-Context.txt"

    if not video_path.exists():
        print(f"Error: video not found at {video_path}")
        return

    print(f"Transcribing {video_path.name}...")
    start_time = time.time()

    # Use 'small' model on CPU with int8 for good Vietnamese accuracy
    model_size = "small"
    print(f"Loading faster-whisper model '{model_size}' on CPU (int8)...")
    model = WhisperModel(model_size, device="cpu", compute_type="int8")

    segments, info = model.transcribe(
        str(video_path),
        language="vi",
        beam_size=5,
        word_timestamps=True
    )

    print(f"Detected language: {info.language} with probability {info.language_probability:.2f}")

    results = []
    lines = []

    for seg in segments:
        item = {
            "id": seg.id,
            "start": round(seg.start, 2),
            "end": round(seg.end, 2),
            "text": seg.text.strip(),
            "words": [
                {
                    "word": w.word.strip(),
                    "start": round(w.start, 2),
                    "end": round(w.end, 2),
                    "probability": round(w.probability, 2)
                }
                for w in (seg.words or [])
            ]
        }
        results.append(item)
        lines.append(f"[{item['start']:06.2f} - {item['end']:06.2f}] {item['text']}")

    with open(jsonl_path, "w", encoding="utf-8") as f:
        for item in results:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    elapsed = time.time() - start_time
    print(f"Transcription complete in {elapsed:.1f}s!")
    print(f"Segments: {len(results)}")
    print(f"Saved to:\n  - {jsonl_path}\n  - {txt_path}")

    # Inspect sample keywords
    full_text = " ".join([r["text"] for r in results]).lower()
    keywords = ["token", "ngữ cảnh", "context", "mô hình", "embedding", "attention"]
    print("\nKeyword presence check:")
    for kw in keywords:
        count = full_text.count(kw)
        print(f"  - '{kw}': {count} occurrences")

if __name__ == "__main__":
    transcribe_pilot()
