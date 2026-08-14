from pathlib import Path
from threading import Lock
from typing import Any, cast

import torch
from transformers import AutoModel, AutoTokenizer

from information_retrieval.domain.embedding import SentenceEmbeddingError


class PhoBertSentenceEncoder:
    def __init__(self, model_name: str, cache_dir: Path, max_length: int) -> None:
        """Load model and tokenizer together so their vocabulary and weights cannot drift."""
        self._tokenizer: Any = AutoTokenizer.from_pretrained(model_name, cache_dir=cache_dir)
        self._model: Any = AutoModel.from_pretrained(model_name, cache_dir=cache_dir)
        self._model.eval()
        self._max_length = max_length
        self._inference_lock = Lock()

    def encode(self, sentences: list[str]) -> list[list[float]]:
        """Exclude padding and special tokens so sentence length does not bias mean pooling."""
        if not sentences:
            return []

        try:
            # WHY: Search and ingestion share this heavy model, so inference must not mutate
            # tokenizer/model state concurrently across FastAPI worker threads.
            with self._inference_lock:
                encoded = self._tokenizer(
                    sentences,
                    return_tensors="pt",
                    padding=True,
                    truncation=True,
                    max_length=self._max_length,
                )
                with torch.no_grad():
                    output = self._model(**encoded)

                special_tokens_mask = torch.tensor(
                    [
                        self._tokenizer.get_special_tokens_mask(
                            token_ids, already_has_special_tokens=True
                        )
                        for token_ids in encoded["input_ids"].tolist()
                    ],
                    device=output.last_hidden_state.device,
                )
                content_mask = encoded["attention_mask"] * (1 - special_tokens_mask)
                pooling_mask = content_mask.unsqueeze(-1).to(output.last_hidden_state.dtype)
                token_count = pooling_mask.sum(dim=1).clamp(min=1e-9)
                embeddings = (output.last_hidden_state * pooling_mask).sum(dim=1) / token_count
        except (OSError, RuntimeError, ValueError) as error:
            raise SentenceEmbeddingError(f"PhoBERT encoding failed: {error}") from error

        return cast(list[list[float]], embeddings.detach().cpu().tolist())
