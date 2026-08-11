from pathlib import Path
from typing import cast

import py_vncorenlp  # type: ignore[import-untyped]

from information_retrieval.domain.preprocessing import ArticlePreprocessingError


class VnCoreNlpWordSegmenter:
    _JAR_NAME = "VnCoreNLP-1.2.jar"

    def __init__(self, model_dir: Path) -> None:
        if not self.is_model_installed(model_dir):
            raise ArticlePreprocessingError(
                f"VnCoreNLP model is missing at {model_dir}; run make download-segmenter-model"
            )
        try:
            self._segmenter = py_vncorenlp.VnCoreNLP(annotators=["wseg"], save_dir=str(model_dir))
        except Exception as error:
            raise ArticlePreprocessingError(
                f"cannot load VnCoreNLP model from {model_dir}: {error}"
            ) from error

    @classmethod
    def is_model_installed(cls, model_dir: Path) -> bool:
        """Avoid a network call when the runtime jar and word segmenter already exist."""
        return (model_dir / cls._JAR_NAME).is_file() and (
            model_dir / "models" / "wordsegmenter"
        ).is_dir()

    @classmethod
    def download_model(cls, model_dir: Path) -> bool:
        """Keep model download explicit because preprocessing should be offline-repeatable."""
        if cls.is_model_installed(model_dir):
            return False
        model_dir.mkdir(parents=True, exist_ok=True)
        py_vncorenlp.download_model(save_dir=str(model_dir))
        if not cls.is_model_installed(model_dir):
            raise ArticlePreprocessingError(
                f"VnCoreNLP download did not produce a usable model at {model_dir}"
            )
        return True

    def segment(self, text: str) -> list[str]:
        """Translate library/runtime failures into an expected per-document batch failure."""
        try:
            return cast(list[str], self._segmenter.word_segment(text))
        except Exception as error:
            raise ArticlePreprocessingError(f"VnCoreNLP segmentation failed: {error}") from error
