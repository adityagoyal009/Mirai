"""
Download and index FinePersonas dataset.
Streams from HuggingFace, saves all 21M personas as compact JSONL with label index.
"""
import json
import os
import sys
from collections import defaultdict

def main():
    from datasets import load_dataset

    out_dir = os.path.dirname(os.path.abspath(__file__))
    personas_file = os.path.join(out_dir, "personas.jsonl")
    index_file = os.path.join(out_dir, "label_index.json")

    print("Streaming FinePersonas-v0.1 from HuggingFace...")
    print(f"Output: {personas_file}")

    ds = load_dataset("argilla/FinePersonas-v0.1", split="train", streaming=True)

    label_index = defaultdict(list)  # label -> [line_numbers]
    count = 0

    with open(personas_file, "w") as f:
        for item in ds:
            persona = item.get("persona", "")
            labels_raw = item.get("labels", "[]")
            try:
                labels = json.loads(labels_raw) if isinstance(labels_raw, str) else labels_raw
            except json.JSONDecodeError:
                labels = []

            record = {"persona": persona, "labels": labels}
            f.write(json.dumps(record) + "\n")

            for label in labels:
                label_lower = label.lower().strip()
                label_index[label_lower].append(count)

            count += 1
            if count % 500000 == 0:
                print(f"  Processed {count:,} personas ({len(label_index):,} unique labels)")

    print(f"\nDone: {count:,} personas saved")
    print(f"Unique labels: {len(label_index):,}")

    # Save label index (label -> list of line numbers)
    # For large lists, store only count + sample indices to keep index small
    compact_index = {}
    for label, indices in label_index.items():
        if len(indices) <= 1000:
            compact_index[label] = indices
        else:
            # Store count + first 500 + last 500 for sampling
            compact_index[label] = {
                "count": len(indices),
                "sample": indices[:500] + indices[-500:],
            }

    with open(index_file, "w") as f:
        json.dump(compact_index, f)

    index_size = os.path.getsize(index_file) / (1024 * 1024)
    data_size = os.path.getsize(personas_file) / (1024 * 1024 * 1024)
    print(f"Personas file: {data_size:.1f} GB")
    print(f"Label index: {index_size:.1f} MB")

    # Print top 30 labels
    top = sorted(label_index.items(), key=lambda x: len(x[1]), reverse=True)[:30]
    print("\nTop 30 labels:")
    for label, indices in top:
        print(f"  {label}: {len(indices):,}")


if __name__ == "__main__":
    main()
