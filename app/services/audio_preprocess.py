import shutil
import subprocess
from pathlib import Path

from fastapi import HTTPException, status


def normalize_audio_for_engine(input_path: Path, output_path: Path) -> Path:
    if not input_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"입력 오디오 파일을 찾을 수 없습니다: {input_path}",
        )

    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ffmpeg가 설치되어 있지 않아 오디오를 엔진 규격으로 변환할 수 없습니다.",
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    command = [
        ffmpeg_path,
        "-y",
        "-i",
        str(input_path),
        "-ac",
        "1",
        "-ar",
        "16000",
        "-vn",
        "-c:a",
        "pcm_s16le",
        str(output_path),
    ]

    try:
        subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.strip() or exc.stdout.strip() or "ffmpeg 변환에 실패했습니다."
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"오디오 정규화에 실패했습니다: {detail}",
        )

    return output_path
