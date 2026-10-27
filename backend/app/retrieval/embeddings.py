"""The same MiniLM model and normalized mean pooling for documents and queries.

The ONNX runtime avoids importing torch on small hosts. Ingestion can also use
SentenceTransformer; model ID and backend are recorded in every index manifest.
"""

import json
from pathlib import Path
from threading import Lock

import numpy as np


class Embedder:
    def __init__(self, model_id: str, model_dir: Path, backend: str = "onnx"):
        self.model_id, self.model_dir, self.backend = model_id, model_dir, backend
        self._model = None
        self._tokenizer = None
        self._lock = Lock()

    def load(self):
        with self._lock:
            if self._model is not None:
                return
            metadata = self.model_dir / "model-metadata.json"
            if (
                not metadata.exists()
                or json.loads(metadata.read_text()).get("model_id") != self.model_id
            ):
                raise ValueError(
                    "Model assets do not match configured embedding model. Run download_model.py."
                )
            if self.backend == "sentence-transformers":
                from sentence_transformers import SentenceTransformer

                self._model = SentenceTransformer(
                    str(self.model_dir), device="cpu", local_files_only=True
                )
                self._model.max_seq_length = 256
            elif self.backend == "onnx":
                import onnxruntime as ort
                from tokenizers import Tokenizer

                options = ort.SessionOptions()
                options.intra_op_num_threads = 2
                options.inter_op_num_threads = 1
                self._model = ort.InferenceSession(
                    str(self.model_dir / "onnx/model.onnx"),
                    sess_options=options,
                    providers=["CPUExecutionProvider"],
                )
                self._tokenizer = Tokenizer.from_file(
                    str(self.model_dir / "tokenizer.json")
                )
                self._tokenizer.enable_truncation(max_length=256)
                self._tokenizer.enable_padding(pad_id=0, pad_token="[PAD]")
            else:
                raise ValueError("Unsupported embedding backend")

    def _encode_windows(self, texts: list[str]) -> np.ndarray:
        self.load()
        if self.backend == "sentence-transformers":
            return self._model.encode(
                texts,
                batch_size=16,
                normalize_embeddings=True,
                convert_to_numpy=True,
                show_progress_bar=False,
            )
        rows = []
        # The tokenizer's padding configuration is shared. Serialize encoding only.
        with self._lock:
            batches = [
                self._tokenizer.encode_batch(texts[i : i + 16])
                for i in range(0, len(texts), 16)
            ]
        for encoded in batches:
            mask = np.array([e.attention_mask for e in encoded], dtype=np.int64)
            feeds = {
                "input_ids": np.array([e.ids for e in encoded], dtype=np.int64),
                "attention_mask": mask,
                "token_type_ids": np.array(
                    [e.type_ids for e in encoded], dtype=np.int64
                ),
            }
            required = {v.name for v in self._model.get_inputs()}
            hidden = self._model.run(
                None, {k: v for k, v in feeds.items() if k in required}
            )[0]
            pooled = (hidden * mask[:, :, None]).sum(axis=1) / np.maximum(
                mask.sum(axis=1, keepdims=True), 1
            )
            pooled /= np.maximum(np.linalg.norm(pooled, axis=1, keepdims=True), 1e-12)
            rows.extend(pooled)
        return np.asarray(rows, dtype=np.float32)

    def encode(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, 384), dtype=np.float32)
        windows, spans = [], []
        for text in texts:
            words = text.split()
            parts = [
                " ".join(words[i : i + 180]) for i in range(0, max(1, len(words)), 150)
            ]
            spans.append((len(windows), len(windows) + len(parts)))
            windows.extend(parts)
        vectors = self._encode_windows(windows)
        result = np.array(
            [vectors[a:b].mean(axis=0) for a, b in spans], dtype=np.float32
        )
        return result / np.maximum(np.linalg.norm(result, axis=1, keepdims=True), 1e-12)
