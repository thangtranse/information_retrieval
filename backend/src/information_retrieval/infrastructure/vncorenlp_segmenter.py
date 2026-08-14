import os
import shutil
import tempfile
from pathlib import Path
from threading import Lock
from typing import cast

import py_vncorenlp  # type: ignore[import-untyped]

from information_retrieval.domain.segmentation import ArticleSegmentationError


class VnCoreNlpWordSegmenter:
    _JAR_NAME = "VnCoreNLP-1.2.jar"

    def __init__(self, model_dir: Path) -> None:
        if not self.is_model_installed(model_dir):
            raise ArticleSegmentationError(
                f"VnCoreNLP model is missing at {model_dir}; run make download-segmenter-model"
            )
        previous_working_dir = Path.cwd()
        try:
            self._segmenter = py_vncorenlp.VnCoreNLP(annotators=["wseg"], save_dir=str(model_dir))
        except Exception as error:
            raise ArticleSegmentationError(
                f"cannot load VnCoreNLP model from {model_dir}: {error}"
            ) from error
        finally:
            # WHY: The third-party constructor calls os.chdir(model_dir); restoring the process
            # directory prevents unrelated relative file operations from following it there.
            os.chdir(previous_working_dir)
        self._inference_lock = Lock()

    @classmethod
    def is_model_installed(cls, model_dir: Path) -> bool:
        """Avoid a network call when the runtime jar and word segmenter already exist."""
        return (model_dir / cls._JAR_NAME).is_file() and (
            model_dir / "models" / "wordsegmenter"
        ).is_dir()

    @classmethod
    def download_model(cls, model_dir: Path) -> bool:
        """Stage downloads so an interrupted attempt cannot poison the durable model cache."""
        if cls.is_model_installed(model_dir):
            return False
        model_dir.mkdir(parents=True, exist_ok=True)
        previous_working_dir = Path.cwd()
        try:
            with tempfile.TemporaryDirectory(prefix="vncorenlp-") as temporary_dir:
                temporary_path = Path(temporary_dir)
                staged_model_dir = temporary_path / "model"
                staged_model_dir.mkdir()
                os.chdir(temporary_path)
                py_vncorenlp.download_model(save_dir=str(staged_model_dir))
                if not cls.is_model_installed(staged_model_dir):
                    raise ArticleSegmentationError(
                        "VnCoreNLP download completed without the required runtime files"
                    )
                # WHY: Publishing only a verified staging tree repairs partial bind-mounted
                # caches without deleting the last usable model before network work succeeds.
                shutil.copytree(staged_model_dir, model_dir, dirs_exist_ok=True)
        except ArticleSegmentationError:
            raise
        except Exception as error:
            raise ArticleSegmentationError(f"cannot download VnCoreNLP model: {error}") from error
        finally:
            os.chdir(previous_working_dir)
        if not cls.is_model_installed(model_dir):
            raise ArticleSegmentationError(
                f"VnCoreNLP download did not produce a usable model at {model_dir}"
            )
        return True

    def segment(self, text: str) -> list[str]:
        """Translate library/runtime failures into an expected per-document batch failure."""
        try:
            # WHY: Search and ingestion share one Java process whose request state is not
            # guaranteed to be safe across concurrent FastAPI worker threads.
            with self._inference_lock:
                return cast(list[str], self._segmenter.word_segment(text))
        except Exception as error:
            raise ArticleSegmentationError(f"VnCoreNLP segmentation failed: {error}") from error
