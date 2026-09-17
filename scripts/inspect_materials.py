"""Inspect local lecture files without uploading their contents to an AI service."""

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import av
import pypdfium2 as pdfium
from PIL import Image, ImageDraw
from pypdf import PdfReader


def inspect_pdf(path, source_id, output, engine):
    pages = []
    previews = []
    if engine == "pypdf":
        reader = PdfReader(path)
        for number, page in enumerate(reader.pages, 1):
            pages.append({"source_id": source_id, "page": number, "text": page.extract_text() or ""})
    else:
        document = pdfium.PdfDocument(path)
        try:
            for index in range(len(document)):
                page = document[index]
                textpage = page.get_textpage()
                text = textpage.get_text_range().replace("\r\n", "\n")
                text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", text)
                textpage.close()
                pages.append({"source_id": source_id, "page": index + 1, "text": text})
                if not text.strip():
                    target = output / "pdf-previews" / f"{source_id}-page-{index + 1}.png"
                    target.parent.mkdir(parents=True, exist_ok=True)
                    bitmap = page.render(scale=1.5)
                    bitmap.to_pil().save(target)
                    bitmap.close()
                    previews.append(target.relative_to(output).as_posix())
                page.close()
        finally:
            document.close()
    target = output / "pages" / f"{source_id}.jsonl"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "".join(json.dumps(page, ensure_ascii=False) + "\n" for page in pages),
        encoding="utf-8",
    )
    return {
        "kind": "pdf",
        "extraction_engine": engine,
        "pages": len(pages),
        "text_characters": sum(len(page["text"].strip()) for page in pages),
        "empty_text_pages": [p["page"] for p in pages if not p["text"].strip()],
        "short_text_pages": [p["page"] for p in pages if len(p["text"].strip()) < 80],
        "replacement_characters": sum(p["text"].count("\ufffd") for p in pages),
        "extracted_text": target.relative_to(output).as_posix(),
        "empty_page_previews": previews,
    }


def inspect_media(path, source_id, output):
    with av.open(str(path)) as container:
        duration = container.duration / av.time_base if container.duration else None
        streams = []
        for stream in container.streams:
            info = {"type": stream.type, "codec": stream.codec_context.name}
            if stream.type == "video":
                info.update(width=stream.width, height=stream.height)
            elif stream.type == "audio":
                info.update(sample_rate=stream.codec_context.sample_rate)
            streams.append(info)
        has_video = bool(container.streams.video)
        has_audio = bool(container.streams.audio)
        container_format = container.format.name
    result = {
        "kind": "video" if has_video else "audio",
        "container": container_format,
        "duration_seconds": round(duration, 3) if duration else None,
        "streams": streams,
        "subtitle_tracks": sum(s["type"] == "subtitle" for s in streams),
        "sampled_video_timestamps": [],
        "audio_sample_decoded": False,
    }
    # Sample seeking and decoding; this is not a full-file integrity scan.
    if has_video:
        for fraction in (0.1, 0.5, 0.9):
            seconds = (duration or 0) * fraction
            with av.open(str(path)) as container:
                stream = container.streams.video[0]
                container.seek(int(seconds / stream.time_base), stream=stream)
                frame = None
                for candidate in container.decode(stream):
                    frame = candidate
                    if candidate.time is not None and candidate.time >= seconds:
                        break
                if frame is None:
                    raise ValueError(f"No video frame near {seconds:.1f}s")
                result["sampled_video_timestamps"].append(frame.time)
                if fraction == 0.5:
                    image = frame.to_image()
                    image.thumbnail((640, 360))
                    target = output / "frames" / f"{source_id}.jpg"
                    target.parent.mkdir(parents=True, exist_ok=True)
                    image.save(target)
                    result["preview"] = target.relative_to(output).as_posix()
    if has_audio:
        with av.open(str(path)) as container:
            frame = next(container.decode(audio=0), None)
            result["audio_sample_decoded"] = frame is not None and frame.samples > 0
            if not result["audio_sample_decoded"]:
                raise ValueError("Audio stream exists but first frame could not be decoded")
    return result


def make_contact_sheet(records, output):
    previews = [r for r in records if "preview" in r]
    if not previews:
        return
    sheet = Image.new("RGB", (960, ((len(previews) + 1) // 2) * 300), "white")
    draw = ImageDraw.Draw(sheet)
    for index, record in enumerate(previews):
        x, y = (index % 2) * 480, (index // 2) * 300
        with Image.open(output / record["preview"]) as preview:
            preview.thumbnail((480, 270))
            sheet.paste(preview, (x, y))
        label = Path(record["path"]).name[:60]
        draw.text((x + 6, y + 276), label, fill="black")
    sheet.save(output / "video-contact-sheet.jpg")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, default=Path("materials/raw"))
    parser.add_argument("--output", type=Path, default=Path("materials/derived/audit"))
    parser.add_argument("--pdf-engine", choices=("pdfium", "pypdf"), default="pdfium")
    args = parser.parse_args()
    files = sorted(p for p in args.raw.rglob("*") if p.is_file())
    if not files:
        parser.error(f"No files under {args.raw}")
    args.output.mkdir(parents=True, exist_ok=True)
    records = []
    for path in files:
        with path.open("rb") as source:
            signature = source.read(16)
            source.seek(0)
            digest = hashlib.file_digest(source, "sha256").hexdigest()
        source_id = digest[:16]
        match = re.search(r"day[ -]?(\d+)", path.name, re.IGNORECASE)
        record = {
            "source_id": source_id,
            "path": path.relative_to(args.raw).as_posix(),
            "lesson_id": f"day-{int(match[1]):02d}" if match else None,
            "bytes": path.stat().st_size,
            "sha256": digest,
            "missing_extension": not bool(path.suffix),
        }
        try:
            if signature.startswith(b"%PDF-"):
                record.update(inspect_pdf(path, source_id, args.output, args.pdf_engine))
            elif signature[4:8] == b"ftyp" or path.suffix.lower() in {".mp4", ".mkv", ".mov", ".mp3", ".wav"}:
                record.update(inspect_media(path, source_id, args.output))
            elif path.suffix.lower() in {".srt", ".vtt", ".txt", ".md"}:
                record.update(kind="text", characters=len(path.read_text(encoding="utf-8-sig")))
            else:
                record.update(kind="unknown", error="Unsupported file signature")
        except Exception as error:
            record["error"] = f"{type(error).__name__}: {error}"
        records.append(record)
        print(json.dumps({k: v for k, v in record.items() if k != "sha256"}, ensure_ascii=False), flush=True)
    checksums = defaultdict(list)
    for record in records:
        checksums[record["sha256"]].append(record["path"])
    summary = {
        "files": len(records),
        "bytes": sum(r["bytes"] for r in records),
        "kinds": dict(Counter(r.get("kind", "error") for r in records)),
        "pages": sum(r.get("pages", 0) for r in records),
        "video_seconds": round(sum(r.get("duration_seconds") or 0 for r in records if r.get("kind") == "video"), 3),
        "missing_extensions": [r["path"] for r in records if r["missing_extension"]],
        "duplicates": [paths for paths in checksums.values() if len(paths) > 1],
        "errors": [{"path": r["path"], "error": r["error"]} for r in records if "error" in r],
    }
    (args.output / "inventory.json").write_text(
        json.dumps({"summary": summary, "files": records}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    make_contact_sheet(records, args.output)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return bool(summary["errors"])


if __name__ == "__main__":
    raise SystemExit(main())
