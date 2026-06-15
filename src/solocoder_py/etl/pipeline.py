from __future__ import annotations

import abc
import json
import pickle
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

from .exceptions import (
    CheckpointCorruptedError,
    FatalEtlError,
    StageNotReachableError,
)
from .models import (
    STAGE_COMPLETED,
    STAGE_EXTRACT,
    STAGE_LOAD,
    STAGE_TRANSFORM,
    Checkpoint,
    DataRow,
    ErrorRecord,
)


class Extractor(abc.ABC):
    @abc.abstractmethod
    def extract(self) -> Iterator[DataRow]:
        ...


class InMemoryExtractor(Extractor):
    def __init__(self, rows: Optional[List[Any]] = None) -> None:
        self._rows: List[Any] = list(rows) if rows is not None else []

    def add_row(self, data: Any) -> None:
        self._rows.append(data)

    def extract(self) -> Iterator[DataRow]:
        for idx, data in enumerate(self._rows):
            yield DataRow(row_id=idx, data=data)


class Transformer(abc.ABC):
    @abc.abstractmethod
    def transform_row(self, row: DataRow) -> Any:
        ...


class IdentityTransformer(Transformer):
    def transform_row(self, row: DataRow) -> Any:
        return row.data


class Loader(abc.ABC):
    @abc.abstractmethod
    def load_row(self, row: DataRow, transformed: Any) -> None:
        ...


class InMemoryLoader(Loader):
    def __init__(self) -> None:
        self._loaded: List[Dict[str, Any]] = []
        self._lock: threading.RLock = threading.RLock()

    @property
    def loaded_count(self) -> int:
        with self._lock:
            return len(self._loaded)

    @property
    def loaded_data(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._loaded)

    def clear(self) -> None:
        with self._lock:
            self._loaded.clear()

    def load_row(self, row: DataRow, transformed: Any) -> None:
        with self._lock:
            self._loaded.append({
                "row_id": row.row_id,
                "original": row.data,
                "transformed": transformed,
            })


class CheckpointStore:
    def __init__(self, checkpoint_dir: str | Path) -> None:
        self._dir: Path = Path(checkpoint_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path_for(self, job_id: str) -> Path:
        return self._dir / f"{job_id}.checkpoint.json"

    def _extracted_path_for(self, job_id: str) -> Path:
        return self._dir / f"{job_id}.extracted.pkl"

    def _transformed_path_for(self, job_id: str) -> Path:
        return self._dir / f"{job_id}.transformed.pkl"

    def save(self, checkpoint: Checkpoint) -> None:
        path = self._path_for(checkpoint.job_id)
        payload = {
            "job_id": checkpoint.job_id,
            "last_completed_stage": checkpoint.last_completed_stage,
            "rows_extracted": checkpoint.rows_extracted,
            "rows_transformed": checkpoint.rows_transformed,
            "rows_loaded": checkpoint.rows_loaded,
            "rows_failed": checkpoint.rows_failed,
            "updated_at": checkpoint.updated_at.isoformat(),
            "metadata": checkpoint.metadata,
        }
        tmp_path = path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        tmp_path.replace(path)

    def load(self, job_id: str) -> Optional[Checkpoint]:
        path = self._path_for(job_id)
        if not path.exists():
            return None
        try:
            raw = path.read_text(encoding="utf-8")
            payload = json.loads(raw)
            return Checkpoint(
                job_id=payload["job_id"],
                last_completed_stage=payload["last_completed_stage"],
                rows_extracted=int(payload["rows_extracted"]),
                rows_transformed=int(payload["rows_transformed"]),
                rows_loaded=int(payload["rows_loaded"]),
                rows_failed=int(payload["rows_failed"]),
                updated_at=datetime.fromisoformat(payload["updated_at"]),
                metadata=dict(payload.get("metadata", {})),
            )
        except (KeyError, ValueError, TypeError, json.JSONDecodeError) as e:
            raise CheckpointCorruptedError(str(path), str(e)) from e

    def delete(self, job_id: str) -> bool:
        removed = False
        for p in [
            self._path_for(job_id),
            self._extracted_path_for(job_id),
            self._transformed_path_for(job_id),
        ]:
            if p.exists():
                p.unlink()
                removed = True
        return removed

    def save_extracted(self, job_id: str, rows: List[DataRow]) -> None:
        path = self._extracted_path_for(job_id)
        tmp_path = path.with_suffix(".tmp")
        with open(tmp_path, "wb") as f:
            pickle.dump(rows, f, protocol=pickle.HIGHEST_PROTOCOL)
        tmp_path.replace(path)

    def load_extracted(self, job_id: str) -> Optional[List[DataRow]]:
        path = self._extracted_path_for(job_id)
        if not path.exists():
            return None
        try:
            with open(path, "rb") as f:
                return pickle.load(f)
        except (pickle.UnpicklingError, EOFError, TypeError, ValueError) as e:
            raise CheckpointCorruptedError(str(path), str(e)) from e

    def save_transformed(
        self, job_id: str, pairs: List[Tuple[DataRow, Any]]
    ) -> None:
        path = self._transformed_path_for(job_id)
        tmp_path = path.with_suffix(".tmp")
        with open(tmp_path, "wb") as f:
            pickle.dump(pairs, f, protocol=pickle.HIGHEST_PROTOCOL)
        tmp_path.replace(path)

    def load_transformed(
        self, job_id: str
    ) -> Optional[List[Tuple[DataRow, Any]]]:
        path = self._transformed_path_for(job_id)
        if not path.exists():
            return None
        try:
            with open(path, "rb") as f:
                return pickle.load(f)
        except (pickle.UnpicklingError, EOFError, TypeError, ValueError) as e:
            raise CheckpointCorruptedError(str(path), str(e)) from e


class PipelineResult:
    def __init__(self) -> None:
        self.successful_rows: List[DataRow] = []
        self.error_records: List[ErrorRecord] = []
        self.rows_extracted: int = 0
        self.rows_transformed: int = 0
        self.rows_loaded: int = 0
        self.fatal_error: Optional[BaseException] = None
        self.completed: bool = False
        self.resumed_from_checkpoint: bool = False

    @property
    def rows_failed(self) -> int:
        return len(self.error_records)


class ETLPipeline:
    def __init__(
        self,
        job_id: str,
        extractor: Extractor,
        transformer: Optional[Transformer],
        loader: Loader,
        checkpoint_store: Optional[CheckpointStore] = None,
    ) -> None:
        self._job_id: str = job_id
        self._extractor: Extractor = extractor
        self._transformer: Optional[Transformer] = transformer
        self._loader: Loader = loader
        self._checkpoint_store: Optional[CheckpointStore] = checkpoint_store
        self._lock: threading.RLock = threading.RLock()

    @property
    def job_id(self) -> str:
        return self._job_id

    def get_checkpoint(self) -> Optional[Checkpoint]:
        if self._checkpoint_store is None:
            return None
        return self._checkpoint_store.load(self._job_id)

    def _new_checkpoint(self) -> Checkpoint:
        return Checkpoint(job_id=self._job_id)

    def _persist(self, checkpoint: Checkpoint) -> None:
        if self._checkpoint_store is not None:
            self._checkpoint_store.save(checkpoint)

    def clear_checkpoint(self) -> None:
        if self._checkpoint_store is not None:
            self._checkpoint_store.delete(self._job_id)

    def run(self, run_until_stage: Optional[str] = None) -> PipelineResult:
        with self._lock:
            result = PipelineResult()

            valid_stages = {STAGE_EXTRACT, STAGE_TRANSFORM, STAGE_LOAD, None}
            if run_until_stage is not None and run_until_stage not in valid_stages:
                raise ValueError(
                    f"run_until_stage must be one of {valid_stages}, got '{run_until_stage}'"
                )

            checkpoint = self._new_checkpoint()
            try:
                if self._checkpoint_store is not None:
                    existing = self._checkpoint_store.load(self._job_id)
                    if existing is not None:
                        checkpoint = existing
                        result.resumed_from_checkpoint = True
            except CheckpointCorruptedError as e:
                result.fatal_error = FatalEtlError(
                    f"Failed to load checkpoint: {e}"
                )
                result.fatal_error.__cause__ = e
                return result

            if run_until_stage is not None and checkpoint.is_stage_completed(run_until_stage):
                raise StageNotReachableError(
                    stage=run_until_stage,
                    completed_stage=checkpoint.last_completed_stage or "none",
                )

            if checkpoint.is_job_completed():
                result.completed = True
                result.rows_extracted = checkpoint.rows_extracted
                result.rows_transformed = checkpoint.rows_transformed
                result.rows_loaded = checkpoint.rows_loaded
                return result

            try:
                extracted_rows = self._run_extract(checkpoint, result)
                if run_until_stage == STAGE_EXTRACT:
                    result.rows_extracted = checkpoint.rows_extracted
                    return result

                transformed_pairs = self._run_transform(
                    checkpoint, extracted_rows, result
                )
                if run_until_stage == STAGE_TRANSFORM:
                    result.rows_transformed = checkpoint.rows_transformed
                    return result

                self._run_load(checkpoint, transformed_pairs, result)
                checkpoint.mark_stage_completed(STAGE_COMPLETED)
                self._persist(checkpoint)
                result.completed = True
            except FatalEtlError as e:
                result.fatal_error = e
            except StageNotReachableError:
                raise
            except Exception as e:
                msg = f"Unexpected fatal error: {e}"
                result.fatal_error = FatalEtlError(msg)
                result.fatal_error.__cause__ = e
                self._persist(checkpoint)

            return result

    def _run_extract(
        self, checkpoint: Checkpoint, result: PipelineResult
    ) -> List[DataRow]:
        rows: List[DataRow] = []
        if checkpoint.is_stage_completed(STAGE_EXTRACT):
            result.rows_extracted = checkpoint.rows_extracted
            if self._checkpoint_store is not None:
                restored = self._checkpoint_store.load_extracted(self._job_id)
                if restored is not None:
                    return restored
            return rows

        if (
            checkpoint.rows_extracted > 0
            and not checkpoint.is_stage_completed(STAGE_EXTRACT)
            and self._checkpoint_store is not None
        ):
            restored = self._checkpoint_store.load_extracted(self._job_id)
            if restored is not None and len(restored) == checkpoint.rows_extracted:
                checkpoint.mark_stage_completed(STAGE_EXTRACT)
                self._persist(checkpoint)
                result.rows_extracted = checkpoint.rows_extracted
                return restored

        try:
            for row in self._extractor.extract():
                rows.append(row)
                checkpoint.rows_extracted += 1
        except FatalEtlError:
            raise
        except Exception as e:
            if rows and self._checkpoint_store is not None:
                self._checkpoint_store.save_extracted(self._job_id, rows)
            self._persist(checkpoint)
            result.rows_extracted = checkpoint.rows_extracted
            raise FatalEtlError(f"Extractor failed after {len(rows)} rows: {e}") from e

        checkpoint.mark_stage_completed(STAGE_EXTRACT)
        if self._checkpoint_store is not None:
            self._checkpoint_store.save_extracted(self._job_id, rows)
        self._persist(checkpoint)
        result.rows_extracted = checkpoint.rows_extracted
        return rows

    def _run_transform(
        self,
        checkpoint: Checkpoint,
        extracted_rows: List[DataRow],
        result: PipelineResult,
    ) -> List[Tuple[DataRow, Any]]:
        pairs: List[Tuple[DataRow, Any]] = []
        if checkpoint.is_stage_completed(STAGE_TRANSFORM):
            result.rows_transformed = checkpoint.rows_transformed
            if self._checkpoint_store is not None:
                restored = self._checkpoint_store.load_transformed(self._job_id)
                if restored is not None:
                    return restored
            return pairs

        rows_to_process = extracted_rows
        if not rows_to_process:
            checkpoint.mark_stage_completed(STAGE_TRANSFORM)
            if self._checkpoint_store is not None:
                self._checkpoint_store.save_transformed(self._job_id, pairs)
            self._persist(checkpoint)
            result.rows_transformed = checkpoint.rows_transformed
            return pairs

        for row in rows_to_process:
            if self._transformer is None:
                try:
                    pairs.append((row, row.data))
                    checkpoint.rows_transformed += 1
                except Exception as e:
                    result.error_records.append(ErrorRecord(
                        original_row=row,
                        stage=STAGE_TRANSFORM,
                        error_type=type(e).__name__,
                        error_message=str(e),
                    ))
                    checkpoint.rows_failed += 1
                continue

            try:
                transformed = self._transformer.transform_row(row)
                pairs.append((row, transformed))
                checkpoint.rows_transformed += 1
            except FatalEtlError:
                if self._checkpoint_store is not None:
                    self._checkpoint_store.save_transformed(
                        self._job_id, pairs
                    )
                self._persist(checkpoint)
                result.rows_transformed = checkpoint.rows_transformed
                raise
            except Exception as e:
                result.error_records.append(ErrorRecord(
                    original_row=row,
                    stage=STAGE_TRANSFORM,
                    error_type=type(e).__name__,
                    error_message=str(e),
                ))
                checkpoint.rows_failed += 1

        checkpoint.mark_stage_completed(STAGE_TRANSFORM)
        if self._checkpoint_store is not None:
            self._checkpoint_store.save_transformed(self._job_id, pairs)
        self._persist(checkpoint)
        result.rows_transformed = checkpoint.rows_transformed
        return pairs

    def _run_load(
        self,
        checkpoint: Checkpoint,
        transformed_pairs: List[Tuple[DataRow, Any]],
        result: PipelineResult,
    ) -> None:
        if checkpoint.is_stage_completed(STAGE_LOAD):
            result.rows_loaded = checkpoint.rows_loaded
            return

        rows_to_process = transformed_pairs
        if not rows_to_process:
            checkpoint.mark_stage_completed(STAGE_LOAD)
            self._persist(checkpoint)
            result.rows_loaded = checkpoint.rows_loaded
            return

        for row, transformed in rows_to_process:
            try:
                self._loader.load_row(row, transformed)
                checkpoint.rows_loaded += 1
                result.successful_rows.append(row)
            except FatalEtlError:
                self._persist(checkpoint)
                result.rows_loaded = checkpoint.rows_loaded
                raise
            except Exception as e:
                result.error_records.append(ErrorRecord(
                    original_row=row,
                    stage=STAGE_LOAD,
                    error_type=type(e).__name__,
                    error_message=str(e),
                ))
                checkpoint.rows_failed += 1

        checkpoint.mark_stage_completed(STAGE_LOAD)
        self._persist(checkpoint)
        result.rows_loaded = checkpoint.rows_loaded
