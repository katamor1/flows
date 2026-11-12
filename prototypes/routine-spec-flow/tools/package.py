"""Package the prototype's reviewable deliverables, excluding QA intermediates."""
import json
from zipfile import ZipFile, ZIP_DEFLATED
from flow import ROOT, load, sha

manifest = load(ROOT / "output/manifest.json")
verification = load(ROOT / "output/verification.json")
review = load(ROOT / "output/review.json")
assert verification["failed"] == 0
assert review["visual_review"] == "passed"
assert sha(ROOT / "output/PS-RTN-ALM-001.docx") == manifest["output_sha256"] == review["output_sha256"]
assert sha(ROOT / "templates/routine-spec-v01.docx") == manifest["template_sha256"] == review["template_sha256"]
files = [ROOT / name for name in ["README.md", "build.ps1", "requirements.txt", ".gitignore", ".gitattributes"]]
for folder, pattern in [("source", "*.json"), ("schema", "*.json"), ("templates", "*.docx"), ("output", "*.docx"), ("output", "*.json"), ("tools", "*.py"), ("tools", "*.mjs")]:
    files.extend(sorted((ROOT / folder).glob(pattern)))
destination = ROOT / "routine-spec-flow-prototype.zip"
with ZipFile(destination, "w", compression=ZIP_DEFLATED) as z:
    for file in files:
        assert file.is_file()
        z.write(file, "routine-spec-flow/" + file.relative_to(ROOT).as_posix())
with ZipFile(destination) as z:
    assert z.testzip() is None
    count = len(z.namelist())
print(json.dumps({"package": str(destination), "files": count, "bytes": destination.stat().st_size, "sha256": sha(destination)}, ensure_ascii=False))
