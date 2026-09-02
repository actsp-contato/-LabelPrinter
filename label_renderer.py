from io import BytesIO
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps

DPI = 203
L_CODES = {"0":"0001101","1":"0011001","2":"0010011","3":"0111101","4":"0100011","5":"0110001","6":"0101111","7":"0111011","8":"0110111","9":"0001011"}
G_CODES = {"0":"0100111","1":"0110011","2":"0011011","3":"0100001","4":"0011101","5":"0111001","6":"0000101","7":"0010001","8":"0001001","9":"0010111"}
R_CODES = {digit: "".join("1" if bit == "0" else "0" for bit in code) for digit, code in L_CODES.items()}
PARITY13 = {"0":"LLLLLL","1":"LLGLGG","2":"LLGGLG","3":"LLGGGL","4":"LGLLGG","5":"LGGLLG","6":"LGGGLL","7":"LGLGLG","8":"LGLGGL","9":"LGGLGL"}


def _ean_bits(ean):
    if len(ean) == 13:
        left = "".join((L_CODES if kind == "L" else G_CODES)[digit] for kind, digit in zip(PARITY13[ean[0]], ean[1:7]))
        return "101" + left + "01010" + "".join(R_CODES[d] for d in ean[7:]) + "101"
    if len(ean) == 8:
        return "101" + "".join(L_CODES[d] for d in ean[:4]) + "01010" + "".join(R_CODES[d] for d in ean[4:]) + "101"
    return ""


def _draw_barcode(canvas, draw, ean, top, left, right, bottom):
    bits = _ean_bits(ean)
    if not bits or bottom - top < 30:
        return
    number_font = _font(max(12, min(22, (bottom - top) // 4)))
    text_height = draw.textbbox((0, 0), ean, font=number_font)[3] + 3
    bar_height = max(18, bottom - top - text_height)
    module = max(1, (right - left) // (len(bits) + 20))
    barcode_width = len(bits) * module
    x0 = left + ((right - left) - barcode_width) // 2
    for index, bit in enumerate(bits):
        if bit == "1":
            draw.rectangle((x0 + index * module, top, x0 + (index + 1) * module - 1, top + bar_height), fill=0)
    text_box = draw.textbbox((0, 0), ean, font=number_font)
    draw.text(((canvas.width - (text_box[2] - text_box[0])) // 2, top + bar_height + 1), ean, font=number_font, fill=0)


def mm_to_px(mm):
    return max(1, round(float(mm) * DPI / 25.4))


def _font(size, bold=False):
    candidates = [
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def render_label(label, upload_folder):
    width, height = mm_to_px(label.paper_width), mm_to_px(label.label_height)
    canvas = Image.new("L", (width, height), 255)
    draw = ImageDraw.Draw(canvas)
    margin, y = max(12, width // 40), 8
    barcode_height = max(0, int(height * 0.43)) if label.ean else 0
    content_bottom = height - barcode_height - (6 if label.ean else 0)

    if label.logo_filename:
        logo_path = Path(upload_folder) / label.logo_filename
        if logo_path.exists():
            with Image.open(logo_path) as source:
                logo = ImageOps.contain(source.convert("L"), (width - 2 * margin, max(20, height // 5)))
                x = (width - logo.width) // 2
                canvas.paste(logo, (x, y))
                y += logo.height + 10

    font = _font(label.font_size, label.bold)
    max_width = width - 2 * margin
    lines = []
    content = "\n".join(part for part in (label.product_name, label.text) if part)
    for paragraph in content.splitlines() or [""]:
        words, current = paragraph.split(), ""
        if not words:
            lines.append("")
        for word in words:
            trial = f"{current} {word}".strip()
            if draw.textbbox((0, 0), trial, font=font)[2] <= max_width or not current:
                current = trial
            else:
                lines.append(current)
                current = word
        if current:
            lines.append(current)

    spacing = max(4, label.font_size // 5)
    for line in lines:
        box = draw.textbbox((0, 0), line, font=font)
        line_width = box[2] - box[0]
        x = margin if label.alignment == "left" else width - margin - line_width if label.alignment == "right" else (width - line_width) // 2
        draw.text((x, y), line, fill=0, font=font)
        y += box[3] - box[1] + spacing
        if y >= content_bottom:
            break
    if label.ean:
        _draw_barcode(canvas, draw, label.ean, height - barcode_height, margin, width - margin, height - 3)
    return canvas.point(lambda p: 0 if p < 160 else 255, mode="1")


def png_bytes(image):
    output = BytesIO()
    image.save(output, "PNG")
    output.seek(0)
    return output
