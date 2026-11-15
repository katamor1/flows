"""Bundle this PoC and text evidence without compiler binaries or build outputs."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ROOT_FILES = ("README.md", "job.json", "generation-record.json",
              "traceability.md", ".gitignore")
DIRS = ("input", "include", "src", "tests", "tools", "prompts", "qa")
SUFFIXES = {".json", ".h", ".c", ".py", ".md", ".txt", ".s"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, help="New ZIP outside the PoC")
    args = parser.parse_args()
    output = Path(args.output).resolve()
    if output.is_relative_to(ROOT) or output.suffix.lower() != ".zip":
        parser.error("Output must be a ZIP outside the PoC root")
    if output.exists() or output.with_suffix(".receipt.json").exists():
        parser.error("Refusing to overwrite a delivery")
    paths = [ROOT / name for name in ROOT_FILES]
    for dirname in DIRS:
        paths.extend(p for p in (ROOT / dirname).rglob("*")
                     if p.is_file() and p.suffix.lower() in SUFFIXES
                     and "__pycache__" not in p.parts)
    entries = {p.relative_to(ROOT).as_posix(): p.read_bytes() for p in sorted(paths)}
    manifest = {
        "format_version": "0.1.0", "package": "routine-code-poc", "version": "0.1.0",
        "status": "draft_trial", "binaries_included": False,
        "files": {name: hashlib.sha256(data).hexdigest() for name, data in entries.items()}
    }
    entries["manifest.json"] = (json.dumps(manifest, ensure_ascii=False, indent=2)
                                 + "\n").encode("utf-8")
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(entries.items()):
            info = zipfile.ZipInfo("routine-code-poc/" + name, (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    with zipfile.ZipFile(output) as archive:
        if archive.testzip() is not None:
            raise RuntimeError("ZIP CRC check failed")
        for name, data in entries.items():
            if archive.read("routine-code-poc/" + name) != data:
                raise RuntimeError("Archive content mismatch: " + name)
    receipt = {
        "archive": output.name, "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "size_bytes": output.stat().st_size, "entry_count": len(entries),
        "archive_readback": "passed", "binaries_included": False
    }
    with output.with_suffix(".receipt.json").open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
