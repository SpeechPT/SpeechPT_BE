"""faster-whisper 기반 STT 서비스 (백엔드 전용)."""
from __future__ import annotations

import logging
import os
import tempfile
import wave
from pathlib import Path
from typing import Any, Dict, Tuple

import numpy as np

logger = logging.getLogger(__name__)

_model = None

_WAV_SUFFIX = ".wav"
_CONVERTIBLE_SUFFIXES = {".mp3", ".m4a", ".mp4", ".aac", ".ogg", ".flac", ".webm"}


def _get_model():
    """모델을 처음 호출 시 한 번만 로드하고 재사용한다."""
    global _model
    if _model is None:
        try:
            from faster_whisper import WhisperModel
            logger.info("Whisper 모델 로딩 중 (small / cpu / int8)…")
            _model = WhisperModel("small", device="cpu", compute_type="int8")
            logger.info("Whisper 모델 로딩 완료")
        except ImportError as exc:
            raise RuntimeError(
                "faster-whisper가 설치되어 있지 않습니다. `pip install faster-whisper`를 실행하세요."
            ) from exc
    return _model


def _to_wav(audio_path: str) -> Tuple[str, bool]:
    """비WAV 파일을 임시 WAV(16kHz mono 16-bit)로 변환한다.

    Returns:
        (wav_path, needs_cleanup) — 이미 WAV면 원본 경로와 False를 반환한다.
    """
    if Path(audio_path).suffix.lower() == _WAV_SUFFIX:
        return audio_path, False

    logger.info("오디오 변환 시작: %s → WAV", audio_path)
    from faster_whisper.audio import decode_audio  # PyAV 기반 디코더

    # float32 ndarray, 16 kHz mono
    audio_data: np.ndarray = decode_audio(audio_path)

    tmp = tempfile.NamedTemporaryFile(suffix=_WAV_SUFFIX, delete=False)
    tmp.close()

    audio_int16 = (np.clip(audio_data, -1.0, 1.0) * 32767).astype(np.int16)
    with wave.open(tmp.name, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)   # 16-bit
        wf.setframerate(16000)
        wf.writeframes(audio_int16.tobytes())

    logger.info("오디오 변환 완료: %s", tmp.name)
    return tmp.name, True


def run_stt(audio_path: str | Path) -> Dict[str, Any]:
    """음성 파일을 STT 처리하여 전체 텍스트와 단어별 타임스탬프를 반환한다.

    MP3, M4A 등 비WAV 포맷은 자동으로 WAV로 변환 후 처리한다.

    반환 형식:
        {
            "text": "전체 변환 텍스트",
            "words": [{"word": str, "start": float, "end": float, "probability": float}, ...]
        }
    """
    path = str(Path(audio_path))
    logger.info("STT 시작: %s", path)

    wav_path, needs_cleanup = _to_wav(path)
    try:
        model = _get_model()
        segments, _ = model.transcribe(
            wav_path,
            language="ko",
            word_timestamps=True,
            vad_filter=True,
        )

        texts = []
        words = []
        for segment in segments:
            texts.append(segment.text.strip())
            if segment.words is None:
                continue
            for word in segment.words:
                token = (word.word or "").strip()
                if not token:
                    continue
                words.append(
                    {
                        "word": token,
                        "start": float(word.start),
                        "end": float(word.end),
                        "probability": float(getattr(word, "probability", 0.0)),
                    }
                )
    finally:
        if needs_cleanup:
            try:
                os.unlink(wav_path)
            except OSError:
                pass

    result = {"text": " ".join(texts).strip(), "words": words}
    logger.info("STT 완료: %d 단어", len(words))
    return result
