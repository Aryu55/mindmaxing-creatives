"""Read-only local search of the indexed agency dossier. No network calls."""

import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", nargs="?", default="")
    parser.add_argument("--thread", type=int)
    parser.add_argument("--limit", type=int, default=6)
    args = parser.parse_args()
    base = Path(__file__).resolve().parent
    manifest = json.loads((base / "manifest.json").read_text(encoding="utf-8"))

    if args.thread is not None:
        for row in manifest["threads"]:
            if row["number"] == args.thread:
                print((base / row["record_file"]).read_text(encoding="utf-8"))
                return
        parser.error("Thread must be between 1 and 23.")

    words = args.query.casefold().split()
    if not words:
        parser.error("Supply a query or --thread NUMBER.")
    scored = []
    for row in manifest["threads"]:
        metadata = " ".join([row["title"], *row["tags"], row["summary"], row["mindmaxing"], *row["observations"], *row["cautions"]])
        related = [b for b in manifest["benchmarks"] if b["thread"] == row["number"]]
        benchmark_text = " ".join(json.dumps(b, ensure_ascii=False) for b in related)
        raw = (base / row["raw_file"]).read_text(encoding="utf-8")
        corpus = (metadata + "\n" + benchmark_text + "\n" + raw).casefold()
        if not all(w in corpus for w in words):
            continue
        score = sum(metadata.casefold().count(w) * 5 + min(raw.casefold().count(w), 10) for w in words)
        lines = raw.splitlines()
        hits = []
        for i, line in enumerate(lines):
            if any(w in line.casefold() for w in words):
                hits.append((row["source_start_line"] + i, line))
                if len(hits) == 3:
                    break
        scored.append((score, row, hits))

    scored.sort(key=lambda item: (-item[0], item[1]["number"]))
    for _, row, hits in scored[:max(1, args.limit)]:
        print(f"{row['id']} — {row['title']}")
        print(row["summary"])
        print(f"Record: {base / row['record_file']}")
        print(f"Original: {row['permalink']}")
        for line_number, line in hits:
            print(f"  dossier L{line_number}: {line[:230]}")
        print()
    print(f"{len(scored)} matching thread(s); {min(len(scored), max(1, args.limit))} shown.")


if __name__ == "__main__":
    main()
