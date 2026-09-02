import os
import subprocess
import tempfile


def escpos_raster(image, cut=True, feed_lines=3):
    image = image.convert("1")
    width_bytes = (image.width + 7) // 8
    rows = bytearray()
    pixels = image.load()
    for y in range(image.height):
        for byte_x in range(width_bytes):
            value = 0
            for bit in range(8):
                x = byte_x * 8 + bit
                if x < image.width and pixels[x, y] == 0:
                    value |= 1 << (7 - bit)
            rows.append(value)
    header = b"\x1b@\x1ba\x00" + b"\x1dv0\x00" + bytes((width_bytes & 255, width_bytes >> 8, image.height & 255, image.height >> 8))
    trailer = b"\n" * max(0, feed_lines) + (b"\x1dV\x00" if cut else b"")
    return header + bytes(rows) + trailer


def list_windows_printers():
    if os.name != "nt":
        return []
    import win32print
    flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
    return [item[2] for item in win32print.EnumPrinters(flags)]


def print_raw(data, printer_name=None):
    if os.name == "nt":
        import win32print
        name = printer_name or win32print.GetDefaultPrinter()
        handle = win32print.OpenPrinter(name)
        try:
            job = win32print.StartDocPrinter(handle, 1, ("Etiqueta LabelPrinter ACT", None, "RAW"))
            try:
                win32print.StartPagePrinter(handle)
                win32print.WritePrinter(handle, data)
                win32print.EndPagePrinter(handle)
            finally:
                win32print.EndDocPrinter(handle)
        finally:
            win32print.ClosePrinter(handle)
        return name

    with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as temp:
        temp.write(data)
        path = temp.name
    try:
        command = ["lp", "-o", "raw"]
        if printer_name:
            command += ["-d", printer_name]
        subprocess.run(command + [path], check=True, capture_output=True)
        return printer_name or "impressora padrão"
    finally:
        os.unlink(path)
