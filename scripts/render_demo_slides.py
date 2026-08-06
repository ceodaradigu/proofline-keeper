"""Render deterministic 1080p slides for the Proofline Keeper demo."""

from __future__ import annotations

import json
from pathlib import Path
import textwrap

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "video" / "build"
EVIDENCE = ROOT / "evidence" / "base-sepolia-live.json"
WIDTH, HEIGHT = 1920, 1080

BG = "#09111f"
PANEL = "#111f33"
PANEL_ALT = "#142741"
WHITE = "#f5f7fb"
MUTED = "#a9b5c7"
GOLD = "#f2c96d"
TEAL = "#4ed7c8"
GREEN = "#58d68d"
RED = "#ff7c8a"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        Path(
            "C:/Windows/Fonts/seguisb.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf"
        ),
        Path("C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


F_TITLE = font(70, True)
F_SUB = font(32)
F_CARD_TITLE = font(31, True)
F_BODY = font(28)
F_SMALL = font(23)
F_MONO = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 25)
F_MONO_BIG = ImageFont.truetype("C:/Windows/Fonts/consolab.ttf", 31)


def canvas(
    number: int, title: str, kicker: str
) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, WIDTH, 10), fill=GOLD)
    draw.text((82, 56), "RELAUNCH DEPT. / PROOFLINE KEEPER", font=F_SMALL, fill=TEAL)
    draw.text((82, 104), kicker.upper(), font=F_SMALL, fill=GOLD)
    draw.multiline_text((82, 160), title, font=F_TITLE, fill=WHITE, spacing=8)
    draw.text((1760, 62), f"0{number} / 06", font=F_SMALL, fill=MUTED)
    draw.text(
        (82, 1016),
        "AI-assisted production • Live testnet evidence • No mainnet funds",
        font=F_SMALL,
        fill=MUTED,
    )
    return image, draw


def rounded(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    fill: str,
    outline: str | None = None,
    radius: int = 28,
) -> None:
    draw.rounded_rectangle(
        box, radius=radius, fill=fill, outline=outline, width=2 if outline else 1
    )


def check_mark(
    draw: ImageDraw.ImageDraw,
    center: tuple[int, int],
    color: str,
    *,
    size: int = 28,
    width: int = 7,
) -> None:
    """Draw a font-independent check mark."""
    x, y = center
    draw.line(
        (x - size, y, x - size // 3, y + size, x + size, y - size),
        fill=color,
        width=width,
        joint="curve",
    )


def cross_mark(
    draw: ImageDraw.ImageDraw,
    center: tuple[int, int],
    color: str,
    *,
    size: int = 13,
    width: int = 5,
) -> None:
    """Draw a font-independent cross mark."""
    x, y = center
    draw.line((x - size, y - size, x + size, y + size), fill=color, width=width)
    draw.line((x - size, y + size, x + size, y - size), fill=color, width=width)


def wrap(
    draw: ImageDraw.ImageDraw,
    text: str,
    box: tuple[int, int, int, int],
    *,
    body_font: ImageFont.FreeTypeFont = F_BODY,
    color: str = MUTED,
    spacing: int = 12,
) -> None:
    x1, y1, x2, _ = box
    avg = max(draw.textlength("abcdefghijklmnopqrstuvwxyz", font=body_font) / 26, 1)
    width = max(int((x2 - x1) / avg), 10)
    draw.multiline_text(
        (x1, y1),
        textwrap.fill(text, width=width),
        font=body_font,
        fill=color,
        spacing=spacing,
    )


def slide_one() -> Image.Image:
    image, draw = canvas(1, "Agents need a\ntransaction firewall", "The problem")
    rounded(draw, (82, 410, 1838, 904), PANEL)
    failures = [
        ("01", "Intent drift", "Recipient or amount changes after review."),
        ("02", "Stale evidence", "An old simulation is treated as current."),
        ("03", "Duplicate write", "A retry becomes a second transaction."),
    ]
    for index, (tag, title, body) in enumerate(failures):
        x = 128 + index * 565
        rounded(draw, (x, 478, x + 500, 830), PANEL_ALT, TEAL if index == 1 else None)
        draw.text((x + 34, 514), tag, font=F_MONO_BIG, fill=GOLD)
        draw.text((x + 34, 586), title, font=F_CARD_TITLE, fill=WHITE)
        wrap(draw, body, (x + 34, 650, x + 455, 800))
    return image


def slide_two() -> Image.Image:
    image, draw = canvas(2, "Exact intent. Exact approval.", "The execution boundary")
    steps = [
        ("INTENT", "chain • recipient\namount • purpose", GOLD),
        ("SIMULATE", "success = true\nwouldRevert = false", TEAL),
        ("BIND", "intent hash\nsimulation hash", "#8fb8ff"),
        ("APPROVE", "cap • expiry\nidempotency", GREEN),
    ]
    for index, (name, body, color) in enumerate(steps):
        x = 82 + index * 448
        rounded(draw, (x, 426, x + 388, 774), PANEL, color)
        draw.ellipse((x + 34, 464, x + 88, 518), fill=color)
        draw.text((x + 112, 467), name, font=F_CARD_TITLE, fill=WHITE)
        draw.multiline_text((x + 34, 570), body, font=F_MONO, fill=MUTED, spacing=18)
        if index < len(steps) - 1:
            draw.line((x + 392, 600, x + 438, 600), fill=MUTED, width=4)
            draw.polygon([(x + 438, 600), (x + 422, 590), (x + 422, 610)], fill=MUTED)
    rounded(draw, (82, 818, 1838, 922), "#0d2b2a", TEAL)
    draw.text(
        (118, 849),
        "Broadcast exists only when the unchanged decision is READY",
        font=F_CARD_TITLE,
        fill=TEAL,
    )
    return image


def slide_three() -> Image.Image:
    image, draw = canvas(
        3, "Failure is explicit,\nnot optimistic", "Deterministic safety"
    )
    blocked = [
        "missing simulation",
        "revert or stale receipt",
        "recipient changed",
        "amount exceeds cap",
        "approval expired",
        "unsafe execution ID",
    ]
    for index, item in enumerate(blocked):
        column = index % 2
        row = index // 2
        x = 92 + column * 884
        y = 430 + row * 155
        rounded(draw, (x, y, x + 810, y + 116), PANEL)
        draw.ellipse((x + 30, y + 32, x + 78, y + 80), fill=RED)
        cross_mark(draw, (x + 54, y + 56), BG, size=8, width=4)
        draw.text((x + 108, y + 38), item, font=F_CARD_TITLE, fill=WHITE)
    rounded(draw, (1350, 235, 1838, 350), "#123528", GREEN)
    draw.text((1390, 260), "22 / 22 tests passing", font=F_CARD_TITLE, fill=GREEN)
    return image


def slide_four(evidence: dict[str, object]) -> Image.Image:
    image, draw = canvas(4, "Verified live execution", "KeeperHub + Base Sepolia")
    status = evidence["status"]["body"]
    receipt = status["receipts"][0]
    rounded(draw, (82, 400, 1838, 930), PANEL)
    rounded(draw, (126, 446, 652, 866), "#113227", GREEN)
    check_mark(draw, (389, 552), GREEN, size=58, width=16)
    draw.text((389, 675), "VERIFIED", font=font(45, True), fill=WHITE, anchor="mm")
    draw.text(
        (389, 741), "KeeperHub direct execution", font=F_SMALL, fill=MUTED, anchor="mm"
    )
    rows = [
        ("Execution", evidence["broadcast"]["executionId"]),
        ("Network", "Base Sepolia / 84532"),
        ("Block", str(receipt["blockNumber"])),
        ("Gas", f"{receipt['gasUsed']} units • sponsored"),
        (
            "Receipt",
            f"{receipt['receiptStatus']} • verified={str(receipt['verified']).lower()}",
        ),
    ]
    for index, (label, value) in enumerate(rows):
        y = 474 + index * 77
        draw.text((716, y), label.upper(), font=F_SMALL, fill=GOLD)
        draw.text(
            (950, y - 4), value, font=F_MONO_BIG if index == 0 else F_MONO, fill=WHITE
        )
    tx = evidence["broadcast"]["transactionHash"]
    draw.text((716, 872), f"tx {tx[:20]}…{tx[-12:]}", font=F_MONO, fill=TEAL)
    return image


def slide_five(evidence: dict[str, object]) -> Image.Image:
    image, draw = canvas(5, "Live evidence improved\nthe client", "Onboarding insight")
    live_id = evidence["broadcast"]["executionId"]
    rounded(draw, (82, 410, 890, 900), PANEL)
    draw.text((126, 460), "DOCUMENTED EXAMPLE", font=F_SMALL, fill=GOLD)
    draw.text((126, 520), "direct_123", font=font(46, True), fill=WHITE)
    draw.text((126, 650), "LIVE IDENTIFIER", font=F_SMALL, fill=TEAL)
    draw.text((126, 710), live_id, font=font(42, True), fill=WHITE)
    rounded(draw, (946, 410, 1838, 900), PANEL_ALT, TEAL)
    draw.text((994, 458), "FIXED BOUNDARY", font=F_SMALL, fill=TEAL)
    fixes = [
        "Accept a safe opaque path segment",
        "Reject traversal and unsafe characters",
        "Preserve broadcast evidence if polling fails",
        "Keep API keys out of errors and packets",
    ]
    for index, item in enumerate(fixes):
        y = 540 + index * 82
        draw.ellipse((994, y + 3, 1028, y + 37), fill=GREEN)
        check_mark(draw, (1011, y + 20), BG, size=7, width=3)
        draw.text((1052, y), item, font=F_BODY, fill=WHITE)
    return image


def slide_six(evidence: dict[str, object]) -> Image.Image:
    image, draw = canvas(6, "Simulate. Bind.\nApprove. Prove.", "Proofline Keeper")
    rounded(draw, (82, 430, 1838, 898), PANEL)
    draw.text((136, 486), "PUBLIC, REPRODUCIBLE EVIDENCE", font=F_SMALL, fill=GOLD)
    items = [
        ("SOURCE", "github.com/ceodaradigu/proofline-keeper"),
        ("TESTS", "22 focused checks passing"),
        ("EXECUTION", evidence["broadcast"]["executionId"]),
        ("TRANSACTION", evidence["broadcast"]["transactionHash"][:30] + "…"),
    ]
    for index, (label, value) in enumerate(items):
        y = 568 + index * 70
        draw.text((136, y), label, font=F_SMALL, fill=TEAL)
        draw.text((390, y - 4), value, font=F_MONO, fill=WHITE)
    draw.text(
        (1430, 805), "PROOF BEFORE ACTION", font=F_CARD_TITLE, fill=GREEN, anchor="mm"
    )
    return image


def main() -> None:
    BUILD.mkdir(parents=True, exist_ok=True)
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    slides = [
        slide_one(),
        slide_two(),
        slide_three(),
        slide_four(evidence),
        slide_five(evidence),
        slide_six(evidence),
    ]
    for index, slide in enumerate(slides, start=1):
        slide.save(BUILD / f"slide-{index:02d}.png", optimize=True)
    print(json.dumps({"slides": len(slides), "output": str(BUILD)}, indent=2))


if __name__ == "__main__":
    main()
