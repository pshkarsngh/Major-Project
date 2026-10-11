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
    # shortcut: pin_memory=True crashes dataloader workers on Windows (WDDM) after
    # epoch 1; re-enable once torch fixes it. Both trainer and validator import their
    # own build_dataloader, so patch both (val crashed in validation at epoch 1->2).
    from ultralytics.data import build_dataloader as _build_dataloader
    from ultralytics.models.yolo.detect import train as _detect_train
    from ultralytics.models.yolo.detect import val as _detect_val

    def _build_dataloader_no_pin(*args, **kwargs):
        kwargs["pin_memory"] = False
        return _build_dataloader(*args, **kwargs)

    _detect_train.build_dataloader = _build_dataloader_no_pin
    _detect_val.build_dataloader = _build_dataloader_no_pin

    from ultralytics import YOLO  # type: ignore

    dataset = os.path.join(HERE, "dataset.yaml")
    model = YOLO("yolov8n.pt")  # COCO-pretrained
    # workers=0: on Windows the multiprocessing dataloader workers die during
    # validation (RuntimeError: worker exited unexpectedly). Single-process loading
    # is slower but stable; raise workers once that's fixed upstream.
    model.train(data=dataset, imgsz=640, epochs=100, patience=20, workers=0,
                project=os.path.join(HERE, "runs"))

    # Use the trainer's own save_dir: ultralytics increments the run name (train2, train3...).
    save_dir = str(getattr(getattr(model, "trainer", None), "save_dir", os.path.join(HERE, "runs", "train")))
    best = os.path.join(save_dir, "weights", "best.pt")
    out_dir = os.path.join(HERE, "..", "weights")
    os.makedirs(out_dir, exist_ok=True)
    if os.path.exists(best):
        shutil.copy2(best, os.path.join(out_dir, "best.pt"))
        print("Exported weights to", os.path.join(out_dir, "best.pt"))


if __name__ == "__main__":
    main()
