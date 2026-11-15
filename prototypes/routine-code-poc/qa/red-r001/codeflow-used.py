"""Fixed host verification for this one-routine PoC; never generates logic.

Python standard library only. Tool paths must be supplied explicitly.
Every run writes a new output directory and records actual return codes.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
FLAGS = ["-std=c90", "-pedantic-errors", "-Wall", "-Wextra", "-Werror"]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")


def inside(relative):
    path = (ROOT / relative).resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError("Job path must stay inside the PoC: " + relative)
    return path


def normalized(text):
    return re.sub(r"\s+", " ", text).strip()


def run_tool(args, outdir, label, records):
    result = subprocess.run([str(x) for x in args], cwd=ROOT,
                            capture_output=True, text=True, encoding="utf-8",
                            errors="replace", timeout=120, shell=False)
    (outdir / (label + ".stdout.txt")).write_text(result.stdout, encoding="utf-8")
    (outdir / (label + ".stderr.txt")).write_text(result.stderr, encoding="utf-8")
    records.append({"step": label, "argv": [str(x) for x in args],
                    "returncode": result.returncode})
    return result


def verify(args):
    job = json.loads((ROOT / "job.json").read_text(encoding="utf-8"))
    spec_path = inside(job["spec"])
    if sha(spec_path) != job["spec_sha256"]:
        raise ValueError("Spec hash mismatch; create a reviewed new job for a changed spec")
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    header = inside(job["header"])
    header_text = normalized(header.read_text(encoding="ascii"))
    for key in ("type_definitions", "prototype"):
        if normalized(spec["interface"][key]) not in header_text:
            raise ValueError("Header differs from specification: " + key)
    source = inside("qa/unimplemented.c" if args.red else job["source"])
    source.read_text(encoding="ascii")
    test = inside(job["test"])
    clang = Path(args.clang).resolve(strict=True)
    nm = clang.with_name("llvm-nm.exe")
    if not nm.is_file() and not args.red:
        raise ValueError("llvm-nm.exe must be beside clang.exe for object inspection")
    outdir = inside(args.output)
    outdir.mkdir(parents=True, exist_ok=False)
    evidence = {
        "format_version": "0.1.0",
        "time_utc": datetime.now(timezone.utc).isoformat(),
        "kind": "expected_red_baseline" if args.red else "host_verification",
        "status": "failed", "generation": job["generation"],
        "target": "host Windows x64; not target RTOS or WCET verification",
        "files": {p.relative_to(ROOT).as_posix(): sha(p) for p in
                  (spec_path, ROOT / "job.json", header, source, test, Path(__file__))},
        "tools": {"clang_sha256": sha(clang)},
        "commands": []
    }
    records = evidence["commands"]
    try:
        version = run_tool([clang, "--version"], outdir, "compiler-version", records)
        if version.returncode != 0:
            raise RuntimeError("Compiler version failed")
        evidence["tools"]["clang_version"] = version.stdout.strip()
        executable = outdir / "host-tests.exe"
        compile_result = run_tool(
            [clang, *FLAGS, "-O0", "-I", ROOT / "include", source, test,
             "-o", executable], outdir, "compile-tests", records)
        if compile_result.returncode != 0:
            raise RuntimeError("Test compilation failed; inspect compile-tests.stderr.txt")
        tests = run_tool([executable], outdir, "tests", records)
        evidence["test_output"] = tests.stdout
        if args.red:
            if tests.returncode == 0:
                raise RuntimeError("Baseline unexpectedly passed")
            evidence["status"] = "expected_failure_observed"
        else:
            if tests.returncode != 0:
                raise RuntimeError("Host acceptance tests failed")
            obj = outdir / "AlarmQualification.obj"
            assembly = outdir / "AlarmQualification.s"
            for label, extra in (("compile-object", ["-c", "-o", obj]),
                                 ("compile-assembly", ["-S", "-o", assembly])):
                result = run_tool([clang, *FLAGS, "-O2", "-I", ROOT / "include",
                                   source, *extra], outdir, label, records)
                if result.returncode != 0:
                    raise RuntimeError(label + " failed")
            undefined = run_tool([nm, "--undefined-only", obj], outdir,
                                 "undefined-symbols", records)
            defined = run_tool([nm, "--defined-only", "--extern-only", obj],
                               outdir, "defined-symbols", records)
            if undefined.returncode or defined.returncode:
                raise RuntimeError("Object inspection failed")
            if undefined.stdout.strip():
                raise RuntimeError("Unexpected external dependencies in object")
            symbols = [line.split()[-1] for line in defined.stdout.splitlines()
                       if line.strip()]
            if symbols != [job["exported_object_symbol"]]:
                raise RuntimeError("Unexpected public object symbols: " + repr(symbols))
            evidence["object_inspection"] = {
                "undefined_symbols": [], "public_symbols": symbols,
                "note": "Object symbol visibility is not a DLL export declaration."
            }
            evidence["status"] = "passed"
        return 0
    except Exception as exc:
        evidence["error"] = str(exc)
        return 1
    finally:
        write_json(outdir / "verification.json", evidence)
        print(json.dumps({"status": evidence["status"],
                          "evidence": str(outdir / "verification.json"),
                          "error": evidence.get("error")}, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["verify"])
    parser.add_argument("--clang", required=True, help="Absolute path to clang.exe")
    parser.add_argument("--output", required=True, help="New directory inside PoC")
    parser.add_argument("--red", action="store_true", help="Use unimplemented QA stub")
    args = parser.parse_args()
    try:
        return verify(args)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
