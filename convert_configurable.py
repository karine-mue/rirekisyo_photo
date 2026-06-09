import io
import configparser
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime

import cv2
import numpy as np
from rembg import remove
from PIL import Image, ImageOps


@dataclass(frozen=True)
class AppConfig:
    input_path: Path
    output_dir: Path
    output_basename: str
    output_width: int
    output_height: int
    dpi: int
    background_color: tuple[int, int, int, int]
    face_height_ratio: float
    face_center_y_ratio: float
    cascade_min_size: tuple[int, int]
    cascade_scale_factor: float
    cascade_min_neighbors: int


def parse_rgba(value: str) -> tuple[int, int, int, int]:
    """
    "250,250,248,255" のような文字列を RGBA tuple に変換する。
    """
    parts = [int(x.strip()) for x in value.split(",")]

    if len(parts) == 3:
        parts.append(255)

    if len(parts) != 4:
        raise ValueError("background_color は R,G,B または R,G,B,A の形式で指定してください。")

    if any(x < 0 or x > 255 for x in parts):
        raise ValueError("background_color の各値は 0〜255 の範囲で指定してください。")

    return tuple(parts)  # type: ignore[return-value]


def parse_size(value: str) -> tuple[int, int]:
    """
    "354,472" のような文字列を width, height に変換する。
    """
    parts = [int(x.strip()) for x in value.split(",")]

    if len(parts) != 2:
        raise ValueError("output_size は width,height の形式で指定してください。")

    width, height = parts

    if width <= 0 or height <= 0:
        raise ValueError("output_size は正の整数で指定してください。")

    return width, height


def load_config(config_path: Path) -> AppConfig:
    """
    config.def を読み込み、型変換して AppConfig に格納する。
    """
    parser = configparser.ConfigParser()
    read_files = parser.read(config_path, encoding="utf-8")

    if not read_files:
        raise FileNotFoundError(f"設定ファイルを読み込めませんでした: {config_path}")

    app = parser["app"]
    photo = parser["photo"]
    face = parser["face_detection"]

    output_width, output_height = parse_size(photo.get("output_size", "354,472"))

    min_w, min_h = parse_size(face.get("min_size", "80,80"))

    return AppConfig(
        input_path=Path(app.get("input_path", "./data/input.jpg")),
        output_dir=Path(app.get("output_dir", ".output")),
        output_basename=app.get("output_basename", "rirekisyo"),
        output_width=output_width,
        output_height=output_height,
        dpi=photo.getint("dpi", fallback=300),
        background_color=parse_rgba(photo.get("background_color", "250,250,248,255")),
        face_height_ratio=photo.getfloat("face_height_ratio", fallback=0.48),
        face_center_y_ratio=photo.getfloat("face_center_y_ratio", fallback=0.42),
        cascade_min_size=(min_w, min_h),
        cascade_scale_factor=face.getfloat("scale_factor", fallback=1.1),
        cascade_min_neighbors=face.getint("min_neighbors", fallback=5),
    )


def validate_config(config: AppConfig) -> None:
    """
    設定値の範囲を検査する。
    """
    if not config.input_path.exists():
        raise FileNotFoundError(f"入力ファイルが存在しません: {config.input_path}")

    if config.input_path.is_dir():
        raise IsADirectoryError(f"入力パスがディレクトリです: {config.input_path}")

    if not (0 < config.face_height_ratio < 1):
        raise ValueError("face_height_ratio は 0 より大きく 1 未満で指定してください。")

    if not (0 < config.face_center_y_ratio < 1):
        raise ValueError("face_center_y_ratio は 0 より大きく 1 未満で指定してください。")

    if config.dpi <= 0:
        raise ValueError("dpi は正の整数で指定してください。")

    if not config.output_basename:
        raise ValueError("output_basename が空です。")


def load_image(path: Path) -> Image.Image:
    """
    EXIF回転を反映してRGB画像として読み込む。
    """
    img = Image.open(path)
    img = ImageOps.exif_transpose(img)
    return img.convert("RGB")


def detect_face(img: Image.Image, config: AppConfig) -> tuple[int, int, int, int]:
    """
    顔を検出する。
    戻り値: (x, y, w, h)
    """
    arr = np.array(img)
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)

    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    cascade = cv2.CascadeClassifier(cascade_path)

    if cascade.empty():
        raise RuntimeError(f"Haar Cascade を読み込めませんでした: {cascade_path}")

    faces = cascade.detectMultiScale(
        gray,
        scaleFactor=config.cascade_scale_factor,
        minNeighbors=config.cascade_min_neighbors,
        minSize=config.cascade_min_size,
    )

    if len(faces) == 0:
        raise RuntimeError("顔を検出できませんでした。画像の明るさ、顔の向き、解像度を確認してください。")

    # 最大の顔を採用
    x, y, w, h = max(faces, key=lambda b: b[2] * b[3])
    return int(x), int(y), int(w), int(h)


def remove_background_to_white(img: Image.Image, config: AppConfig) -> Image.Image:
    """
    rembgで背景を透過し、白系背景に合成する。
    """
    buf = io.BytesIO()
    img.save(buf, format="PNG")

    cut_bytes = remove(buf.getvalue())
    fg = Image.open(io.BytesIO(cut_bytes)).convert("RGBA")

    bg = Image.new("RGBA", fg.size, config.background_color)
    merged = Image.alpha_composite(bg, fg)

    return merged.convert("RGB")


def crop_with_padding(
    img: Image.Image,
    box: tuple[int, int, int, int],
    background_color: tuple[int, int, int, int],
) -> Image.Image:
    """
    画像外にはみ出す切り抜き範囲を白系背景で補う。
    box: (left, top, right, bottom)
    """
    left, top, right, bottom = box
    crop_w = right - left
    crop_h = bottom - top

    canvas = Image.new("RGB", (crop_w, crop_h), background_color[:3])

    src_left = max(left, 0)
    src_top = max(top, 0)
    src_right = min(right, img.width)
    src_bottom = min(bottom, img.height)

    paste_x = src_left - left
    paste_y = src_top - top

    region = img.crop((src_left, src_top, src_right, src_bottom))
    canvas.paste(region, (paste_x, paste_y))

    return canvas


def make_resume_crop(
    img: Image.Image,
    face_box: tuple[int, int, int, int],
    config: AppConfig,
) -> Image.Image:
    """
    顔位置を基準に、履歴書用の3:4比率で切り抜く。
    """
    x, y, w, h = face_box

    face_cx = x + w / 2
    face_cy = y + h / 2

    # 顔の高さから切り抜き全体の高さを逆算
    crop_h = h / config.face_height_ratio
    crop_w = crop_h * config.output_width / config.output_height

    left = face_cx - crop_w / 2
    top = face_cy - crop_h * config.face_center_y_ratio
    right = left + crop_w
    bottom = top + crop_h

    box = (
        round(left),
        round(top),
        round(right),
        round(bottom),
    )

    cropped = crop_with_padding(img, box, config.background_color)
    resized = cropped.resize((config.output_width, config.output_height), Image.LANCZOS)

    return resized


def make_output_path(config: AppConfig) -> Path:
    """
    timestamp付き出力パスを生成する。
    """
    config.output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{config.output_basename}_{timestamp}.png"

    return config.output_dir / filename


def save_output(img: Image.Image, config: AppConfig) -> Path:
    """
    PNG形式で保存する。
    """
    output_path = make_output_path(config)
    img.save(output_path, format="PNG", dpi=(config.dpi, config.dpi))
    return output_path


def main() -> None:
    config_path = Path("./config.def")

    config = load_config(config_path)
    validate_config(config)

    src = load_image(config.input_path)

    face_box = detect_face(src, config)

    white_bg = remove_background_to_white(src, config)

    resume_img = make_resume_crop(white_bg, face_box, config)

    output_path = save_output(resume_img, config)

    print(f"saved: {output_path}")


if __name__ == "__main__":
    main()
