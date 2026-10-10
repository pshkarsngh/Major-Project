"""Prepare RDD2022 (India subset) as a 3-class YOLO dataset for SafeRoute AI.

Downloads only the India images/labels from the Hugging Face YOLO mirror
(dronefreak/RDD2022), remaps the 4 RDD classes onto the 3 the app uses, and
writes ml/datasets/saferoute/{images,labels}/{train,val,test} plus a runnable
dataset.yaml in the dataset root.

    python ml/training/prepare_rdd2022.py
"""
import os
import re
import shutil

from huggingface_hub import snapshot_download

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.abspath(os.path.join(HERE, "..", "datasets", "rdd2022_india"))
OUT = os.path.abspath(os.path.join(HERE, "..", "datasets", "saferoute"))
DATASET_YAML = os.path.join(HERE, "dataset.yaml")

# RDD2022: 0 longitudinal_crack, 1 transverse_crack, 2 alligator_crack, 3 pothole
# SafeRoute: 0 pothole, 1 crack, 2 damaged_patch
CLASS_MAP = {0: 1, 1: 1, 2: 2, 3: 0}
SPLITS = {"train": "train", "valid": "val", "test": "test"}


def _link_or_copy(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if os.path.exists(dst):
        return
    try:
        os.link(src, dst)  # same volume -> no duplicate bytes
    except OSError:
        shutil.copy2(src, dst)


def _remap_label(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    rows = []
    if os.path.exists(src):
        with open(src, encoding="utf-8") as fh:
            for line in fh:
                parts = line.split()
                if not parts:
                    continue
                new_cls = CLASS_MAP.get(int(parts[0]))
                if new_cls is not None:
                    rows.append(" ".join([str(new_cls), *parts[1:]]))
    with open(dst, "w", encoding="utf-8") as fh:
        fh.write("".join(row + "\n" for row in rows))


def main():
    snapshot_download(
        "dronefreak/RDD2022",
        repo_type="dataset",
        local_dir=RAW,
        allow_patterns=["data/images/*India_*.jpg", "data/labels/*India_*.txt"],
    )

    counts = {}
    for src_split, dst_split in SPLITS.items():
        src_img = os.path.join(RAW, "data", "images", src_split)
        src_lbl = os.path.join(RAW, "data", "labels", src_split)
        n = 0
        for root, _dirs, files in os.walk(src_img):
            for name in files:
                if not name.endswith(".jpg"):
                    continue
                rel = os.path.relpath(os.path.join(root, name), src_img)
                stem = os.path.splitext(rel)[0]
                _link_or_copy(
                    os.path.join(root, name), os.path.join(OUT, "images", dst_split, rel)
                )
                _remap_label(
                    os.path.join(src_lbl, stem + ".txt"),
                    os.path.join(OUT, "labels", dst_split, stem + ".txt"),
                )
                n += 1
        counts[dst_split] = n

    # Ultralytics resolves a relative `path` against the CWD/global datasets dir,
    # so pin it to the absolute dataset root here.
    with open(DATASET_YAML, encoding="utf-8") as fh:
        yaml_text = fh.read()
    yaml_text = re.sub(
        r'(?m)^path:.*$', 'path: "' + OUT.replace("\\", "/") + '"', yaml_text
    )
    with open(DATASET_YAML, "w", encoding="utf-8") as fh:
        fh.write(yaml_text)
    print("Prepared", OUT, "images:", counts)


if __name__ == "__main__":
    main()
