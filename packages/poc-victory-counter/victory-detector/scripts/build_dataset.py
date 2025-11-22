"""学習用データセットを構築するスクリプト。

`samples/<label>/*.png` 形式のフォルダ構造からデータセットを生成する。
label ごとに画像を配置するだけで処理できる。

`--crop x,y,width,height` を指定すると、共通の矩形でクロップできる。
値はピクセル、または 0〜1 の比率指定。未指定時は推奨クロップ領域
460,378,995,550 が使用される。

出力は `dataset/<label>/` の構造で保存される。
"""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2  # type: ignore

DATASET_ROOT = Path("dataset")
SAMPLES_ROOT = Path("data/samples")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build dataset from samples.")
    parser.add_argument("--samples", type=Path, default=SAMPLES_ROOT)
    parser.add_argument("--output", type=Path, default=DATASET_ROOT)
    parser.add_argument("--size", type=int, default=None, help="出力画像の一辺のサイズ（未指定時はリサイズしない）")
    parser.add_argument(
        "--crop",
        type=str,
        default=None,
        help="クロップ矩形を 'x,y,width,height' 形式で指定 (値はピクセルまたは 0〜1 の比率)",
    )
    parser.add_argument("--mask", nargs='?', const='0,534,1920,295', default=None, help="マスク領域 (x,y,width,height)。値を省略した場合はデフォルト: 0,534,1920,295")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.samples.is_dir():
        print(f"[ERROR] サンプルディレクトリが見つかりません: {args.samples}")
        return 1

    crop_rect = None
    if args.crop:
        try:
            crop_rect = tuple(float(part.strip()) for part in args.crop.split(","))
            if len(crop_rect) != 4:
                raise ValueError
        except ValueError as exc:
            print("[ERROR] --crop は 'x,y,width,height' 形式で指定してください。", exc)
            return 1

    # マスク領域のパース
    mask_regions = None
    if args.mask is not None:
        mask_regions = []
        mask_str = args.mask
        try:
            parts = mask_str.split(",")
            if len(parts) != 4:
                print(f"[ERROR] マスク領域の形式が不正です: {mask_str}")
                return 1
            x, y, w, h = map(int, parts)
            mask_regions.append((x, y, w, h))
        except ValueError:
            print(f"[ERROR] マスク領域の形式が不正です: {mask_str}")
            return 1
    print(f"[INFO] Mask regions: {mask_regions if mask_regions else 'disabled'}")

    _process_structured_samples(args.samples, args.output, args.size, crop_rect, mask_regions)
    return 0


def _process_structured_samples(
    samples_root: Path,
    output_root: Path,
    size: int | None,
    crop_rect: tuple[float, float, float, float] | None,
    mask_regions: list[tuple[int, int, int, int]] | None = None,
) -> None:
    for label_dir in sorted(samples_root.iterdir()):
        if not label_dir.is_dir():
            continue
        label = label_dir.name
        for image_path in sorted(label_dir.glob("*.png")):
            image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
            if image is None:
                continue
            height, width = image.shape[:2]
            if crop_rect:
                cx, cy, cw, ch = crop_rect
                x = int(round(cx * width)) if abs(cx) <= 1 else int(round(cx))
                y = int(round(cy * height)) if abs(cy) <= 1 else int(round(cy))
                w = int(round(cw * width)) if abs(cw) <= 1 else int(round(cw))
                h = int(round(ch * height)) if abs(ch) <= 1 else int(round(ch))
            else:
                # fallback: 推奨クロップ領域を使用
                x, y, w, h = 460, 378, 995, 550

            x = max(0, min(x, width - 1))
            y = max(0, min(y, height - 1))
            w = max(1, min(w, width - x))
            h = max(1, min(h, height - y))

            _write_sample(
                image=image,
                crop=(x, y, w, h),
                output_root=output_root,
                label=label,
                file_name=image_path.name,
                size=size,
                mask_regions=mask_regions,
            )


def _resize_keep_aspect_ratio(image: cv2.typing.MatLike, max_size: int) -> cv2.typing.MatLike:
    """画像のアスペクト比を維持しながらリサイズする。長辺がmax_sizeになるように縮小。"""
    h, w = image.shape[:2]
    if h == 0 or w == 0:
        return image

    # 長辺を基準にスケールを計算
    scale = max_size / max(h, w)
    new_w = int(w * scale)
    new_h = int(h * scale)

    # リサイズ（最低1pxは確保）
    new_w = max(1, new_w)
    new_h = max(1, new_h)

    resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
    return resized


def _write_sample(
    image: cv2.typing.MatLike,
    crop: tuple[int, int, int, int],
    output_root: Path,
    label: str,
    file_name: str,
    size: int | None,
    mask_regions: list[tuple[int, int, int, int]] | None = None,
) -> None:
    # マスク適用（クロップより前）
    if mask_regions:
        image = image.copy()  # 元画像を変更しないようコピー
        for mx, my, mw, mh in mask_regions:
            height, width = image.shape[:2]
            # マスク領域のクリッピング
            mx = max(0, min(mx, width - 1))
            my = max(0, min(my, height - 1))
            mw = max(1, min(mw, width - mx))
            mh = max(1, min(mh, height - my))
            image[my : my + mh, mx : mx + mw] = 0  # 黒で塗りつぶす

    x, y, w, h = crop
    cropped = image[y : y + h, x : x + w]

    # size指定時のみリサイズ、未指定時はオリジナルサイズ
    if size is not None:
        processed = _resize_keep_aspect_ratio(cropped, size)
        size_info = f"resized=({processed.shape[1]},{processed.shape[0]})"
    else:
        processed = cropped
        size_info = f"original=({processed.shape[1]},{processed.shape[0]})"

    output_dir = output_root / label
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / file_name
    cv2.imwrite(str(output_path), processed)
    print(f"[INFO] {output_path} を出力しました。 (crop=({x},{y},{w},{h}), {size_info})")


if __name__ == "__main__":
    raise SystemExit(main())
