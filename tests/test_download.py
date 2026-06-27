import gzip
import json
from pathlib import Path

import pytest

from ehitk import download
from ehitk.download import (
    DownloadJob,
    DownloadResult,
    IntegrityError,
    _GzipChecker,
    _stream_to_disk,
    download_jobs,
    write_batch_script,
)


class _FakeProgress:
    """Minimal stand-in for rich.progress.Progress used by the downloader."""

    def add_task(self, *args, **kwargs):
        return 0

    def update(self, *args, **kwargs):
        return None

    def remove_task(self, *args, **kwargs):
        return None


def _chunk(data: bytes, size: int = 7):
    return [data[i : i + size] for i in range(0, len(data), size)] or [b""]


def _job(tmp_path: Path, name: str = "sample.fa.gz") -> DownloadJob:
    return DownloadJob(
        entry_type="mag",
        id_field="mag_id",
        id_value="EHM00001",
        url="https://example.org/sample.fa.gz",
        destination=tmp_path / name,
    )


def test_gzip_checker_accepts_valid_stream() -> None:
    checker = _GzipChecker()
    for piece in _chunk(gzip.compress(b">contig\nACGTACGT\n")):
        checker.update(piece)
    checker.finish()  # does not raise


def test_gzip_checker_accepts_concatenated_members() -> None:
    blob = gzip.compress(b"first member\n") + gzip.compress(b"second member\n")
    checker = _GzipChecker()
    for piece in _chunk(blob):
        checker.update(piece)
    checker.finish()


def test_gzip_checker_rejects_truncated_stream() -> None:
    blob = gzip.compress(b"some sequence payload that gets cut off")
    checker = _GzipChecker()
    for piece in _chunk(blob[:-5]):
        checker.update(piece)
    with pytest.raises(IntegrityError):
        checker.finish()


def _incompressible(size: int) -> bytes:
    return bytes((i * 131 + 17) % 256 for i in range(size))


def test_gzip_checker_rejects_corrupted_payload() -> None:
    blob = bytearray(gzip.compress(_incompressible(8000)))
    blob[40] ^= 0xFF  # flip a byte inside the compressed body
    checker = _GzipChecker()
    with pytest.raises(IntegrityError):
        for piece in _chunk(bytes(blob)):
            checker.update(piece)
        checker.finish()


def test_gzip_checker_rejects_non_gzip_content() -> None:
    checker = _GzipChecker()
    with pytest.raises(IntegrityError):
        checker.update(b"this is not gzip at all")


def test_gzip_checker_rejects_empty_stream() -> None:
    checker = _GzipChecker()
    with pytest.raises(IntegrityError):
        checker.finish()


def test_stream_to_disk_returns_checksum_and_size(tmp_path: Path) -> None:
    payload = gzip.compress(b">contig\nACGT\n")
    temporary_path = tmp_path / "sample.fa.gz.part"

    checksum, size = _stream_to_disk(
        _job(tmp_path),
        _chunk(payload),
        len(payload),
        temporary_path,
        _FakeProgress(),
        expect_gzip=True,
    )

    assert size == len(payload)
    assert len(checksum) == 64
    assert temporary_path.read_bytes() == payload


def test_stream_to_disk_detects_size_mismatch(tmp_path: Path) -> None:
    payload = gzip.compress(b">contig\nACGT\n")
    temporary_path = tmp_path / "sample.fa.gz.part"

    with pytest.raises(IntegrityError):
        _stream_to_disk(
            _job(tmp_path),
            _chunk(payload),
            len(payload) + 100,  # server promised more than we received
            temporary_path,
            _FakeProgress(),
            expect_gzip=True,
        )


def test_stream_to_disk_detects_corrupt_gzip(tmp_path: Path) -> None:
    blob = bytearray(gzip.compress(_incompressible(6000)))
    blob[30] ^= 0xFF
    temporary_path = tmp_path / "sample.fa.gz.part"

    with pytest.raises(IntegrityError):
        _stream_to_disk(
            _job(tmp_path),
            _chunk(bytes(blob)),
            len(blob),
            temporary_path,
            _FakeProgress(),
            expect_gzip=True,
        )


def test_stream_to_disk_skips_gzip_check_for_plain_files(tmp_path: Path) -> None:
    payload = b"plain,csv,content\n1,2,3\n"
    temporary_path = tmp_path / "sample.csv.part"

    checksum, size = _stream_to_disk(
        DownloadJob(
            entry_type="mag",
            id_field="mag_id",
            id_value="EHM00001",
            url="https://example.org/sample.csv",
            destination=tmp_path / "sample.csv",
        ),
        _chunk(payload),
        len(payload),
        temporary_path,
        _FakeProgress(),
        expect_gzip=False,
    )

    assert size == len(payload)
    assert len(checksum) == 64


def _run_batch_script(script_path: Path, work_dir: Path) -> "subprocess.CompletedProcess[str]":
    """Run a generated batch script with ``curl`` stubbed out to avoid network IO."""
    import subprocess

    bin_dir = work_dir / "stubbin"
    bin_dir.mkdir(exist_ok=True)
    fake_curl = bin_dir / "curl"
    fake_curl.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    fake_curl.chmod(0o755)

    import os

    env = dict(os.environ, PATH=f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    return subprocess.run(
        ["bash", str(script_path)],
        cwd=work_dir,
        env=env,
        capture_output=True,
        text=True,
    )


def test_write_batch_script_quotes_paths_with_single_quotes(tmp_path: Path) -> None:
    # A single quote in the filename must not be able to break out of the shell
    # quoting and inject commands into the generated script (in either branch:
    # the existence check, the echo messages, and the curl invocation).
    job = DownloadJob(
        entry_type="mag",
        id_field="mag_id",
        id_value="EHM00001",
        url="https://example.org/x'; touch INJECTED #.fa.gz",
        destination=tmp_path / "x'; touch INJECTED #.fa.gz",
    )
    script_path = tmp_path / "batch.sh"

    write_batch_script(script_path, [job])
    result = _run_batch_script(script_path, tmp_path)

    assert result.returncode == 0, result.stderr
    # No injected command executed anywhere under the working directory.
    assert not list(tmp_path.rglob("INJECTED"))


def test_write_batch_script_quotes_paths_with_single_quotes_overwrite(
    tmp_path: Path,
) -> None:
    job = DownloadJob(
        entry_type="mag",
        id_field="mag_id",
        id_value="EHM00001",
        url="https://example.org/y'; touch INJECTED #.fa.gz",
        destination=tmp_path / "y'; touch INJECTED #.fa.gz",
    )
    script_path = tmp_path / "batch.sh"

    write_batch_script(script_path, [job], overwrite=True)
    result = _run_batch_script(script_path, tmp_path)

    assert result.returncode == 0, result.stderr
    assert not list(tmp_path.rglob("INJECTED"))


def test_download_jobs_records_corrupt_status_and_keeps_partial(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    job = _job(tmp_path)
    manifest_path = tmp_path / "manifest.jsonl"

    def fake_http(job, temporary_path, progress, *, expect_gzip):
        temporary_path.write_bytes(b"partial corrupt bytes")
        raise IntegrityError("gzip integrity check failed: boom")

    monkeypatch.setattr(download, "_download_http", fake_http)

    results = download_jobs([job], manifest_path=manifest_path)

    assert len(results) == 1
    result = results[0]
    assert result.status == "corrupt"
    assert result.error is not None

    # The partial file is kept for inspection; the final name is never created.
    assert (tmp_path / "sample.fa.gz.part").exists()
    assert not job.destination.exists()

    entry = json.loads(manifest_path.read_text(encoding="utf-8").strip())
    assert entry["status"] == "corrupt"
    assert entry["bytes"] is None
    assert entry["mag_id"] == "EHM00001"


def test_download_jobs_records_size_for_successful_download(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    job = _job(tmp_path)
    manifest_path = tmp_path / "manifest.jsonl"

    def fake_http(job, temporary_path, progress, *, expect_gzip):
        temporary_path.write_bytes(b"ok")
        return "deadbeef", 1234

    monkeypatch.setattr(download, "_download_http", fake_http)

    results = download_jobs([job], manifest_path=manifest_path)

    assert results[0].status == "downloaded"
    assert results[0].size == 1234

    entry = json.loads(manifest_path.read_text(encoding="utf-8").strip())
    assert entry["status"] == "downloaded"
    assert entry["bytes"] == 1234
    assert entry["checksum"] == "deadbeef"
