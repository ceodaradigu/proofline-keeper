"""Render the square Proofline Keeper submission logo."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "video" / "proofline-keeper-logo.png"

SIZE = 480
BG = "#09111f"
PANEL = "#142741"
WHITE = "#f5f7fb"
GOLD = "#f2c96d"
TEAL = "#4ed7c8"
GREEN = "#58d68d"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "seguisb.ttf" if bold else "segoeui.ttf"
    return ImageFont.truetype(f"C:/Windows/Fonts/{name}", size)


def main() -> None:
    image = Image.new("RGB", (SIZE, SIZE), BG)
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, SIZE, 10), fill=GOLD)
    draw.rounded_rectangle(
        (60, 56, 420, 342), radius=54, fill=PANEL, outline=TEAL, width=4
    )

    # A font-independent proof mark inside an execution boundary.
    draw.line((155, 195, 210, 250, 326, 118), fill=GREEN, width=24, joint="curve")
    draw.text((240, 298), "PK", font=font(54, True), fill=WHITE, anchor="mm")
    draw.text(
        (240, 380), "PROOFLINE KEEPER", font=font(28, True), fill=WHITE, anchor="mm"
    )
    draw.text((240, 426), "PROOF BEFORE ACTION", font=font(18), fill=TEAL, anchor="mm")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    image.save(OUTPUT, optimize=True)
    print(OUTPUT)


if __name__ == "__main__":
    main()
