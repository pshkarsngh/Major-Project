"""Fine-tune YOLOv8 on RDD2020 + extra hazard classes.

Requirements: `pip install ultralytics`. Requires the prepared dataset referenced by
dataset.yaml (not shipped with the repo). Run from the repo root:

    python ml/training/train.py

Export the best weights to ml/weights/best.pt for the backend to load.
"""
import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    from ultralytics import YOLO  # type: ignore

    dataset = os.path.join(HERE, "dataset.yaml")
    model = YOLO("yolov8n.pt")  # COCO-pretrained
    model.train(data=dataset, imgsz=640, epochs=100, patience=20, project=os.path.join(HERE, "runs"))

    best = os.path.join(HERE, "runs", "detect", "train", "weights", "best.pt")
    out_dir = os.path.join(HERE, "..", "weights")
    os.makedirs(out_dir, exist_ok=True)
    if os.path.exists(best):
        shutil.copy2(best, os.path.join(out_dir, "best.pt"))
        print("Exported weights to", os.path.join(out_dir, "best.pt"))


if __name__ == "__main__":
    main()
