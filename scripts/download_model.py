"""Download public model assets; no hosted inference or paid API is used."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.config import get_settings
from huggingface_hub import HfApi, snapshot_download

if __name__ == "__main__":
    settings = get_settings()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--runtime-only",
        action="store_true",
        help="Download ONNX assets without PyTorch weights",
    )
    args = parser.parse_args()
    manifest_path = settings.data_dir / "snapshot/manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    revision = (
        manifest.get("embedding_revision")
        if manifest.get("embedding_model") == settings.embedding_model
        else None
    )
    revision = revision or HfApi().model_info(settings.embedding_model).sha
    path = snapshot_download(
        settings.embedding_model,
        local_dir=settings.data_dir / "models/minilm",
        revision=revision,
        allow_patterns=["*.json", "1_Pooling/*", "vocab.txt", "onnx/model.onnx"]
        + ([] if args.runtime_only else ["model.safetensors"]),
    )
    (Path(path) / "model-metadata.json").write_text(
        json.dumps(
            {"model_id": settings.embedding_model, "revision": revision}, indent=2
        )
        + "\n"
    )
    print(f"Model assets ready: {path}")
