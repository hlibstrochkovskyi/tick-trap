"""Preserve complete audit outputs with a checked, deterministic archive manifest."""

import argparse
import gzip
from hashlib import sha256
import io
import json
from pathlib import Path
import tarfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("results/audit-milestone"))
    parser.add_argument("--output", type=Path, default=Path("docs/data/audit-evidence.tar.gz"))
    parser.add_argument("--manifest", type=Path, help="Manifest path (defaults to audit-manifest.json beside the archive)")
    args = parser.parse_args()
    sources = [args.input/"environment.json", *sorted(args.input.glob("*/metadata.json"))]
    metadata = [json.loads(p.read_text()) for p in sources]
    if any(m["git_status"] != "" for m in metadata) or len({m["git_commit"] for m in metadata}) != 1:
        raise ValueError("Evidence must share one clean source commit")
    files = []
    buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode="wb", mtime=0, filename="") as compressed:
        with tarfile.open(fileobj=compressed, mode="w") as archive:
            for path in sorted(args.input.rglob("*")):
                if not path.is_file():
                    continue
                if path.is_symlink():
                    raise ValueError("Evidence must not contain symlinks")
                data, name = path.read_bytes(), path.relative_to(args.input).as_posix()
                info = tarfile.TarInfo(name)
                info.size, info.mode, info.mtime = len(data), 0o644, 0
                archive.addfile(info, io.BytesIO(data))
                files.append({"path": name, "bytes": len(data), "sha256": sha256(data).hexdigest()})
    data = buffer.getvalue()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(data)
    # Read back every member before accepting the archive as saved evidence.
    with tarfile.open(args.output, "r:gz") as archive:
        for item in files:
            if sha256(archive.extractfile(item["path"]).read()).hexdigest() != item["sha256"]:
                raise ArithmeticError("Archive member failed read-back verification")
    manifest = {"source_git_commit": metadata[0]["git_commit"], "source_sha256": metadata[0]["source_sha256"],
                "archive": args.output.name, "archive_bytes": len(data), "archive_sha256": sha256(data).hexdigest(),
                "uncompressed_bytes": sum(f["bytes"] for f in files), "files": files}
    manifest_path = args.manifest or args.output.with_name("audit-manifest.json")
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2)+"\n")
    print(f"Archived and read-back verified {len(files)} files ({len(data)} compressed bytes)")


if __name__ == "__main__":
    main()
