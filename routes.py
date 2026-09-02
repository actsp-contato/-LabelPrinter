from pathlib import Path
from uuid import uuid4
from flask import Blueprint, current_app, flash, redirect, render_template, request, send_file, url_for
from werkzeug.utils import secure_filename
from models import Label, db
from label_renderer import png_bytes, render_label
from printer import escpos_raster, list_windows_printers, print_raw

bp = Blueprint("main", __name__)


def normalize_ean(value):
    digits = "".join(filter(str.isdigit, value or ""))
    if not digits:
        return ""
    if len(digits) not in (7, 8, 12, 13):
        raise ValueError("O EAN deve conter 7, 8, 12 ou 13 dígitos.")
    body = digits if len(digits) in (7, 12) else digits[:-1]
    total = sum(int(digit) * (3 if (len(body) - index) % 2 else 1) for index, digit in enumerate(body))
    check = str((10 - total % 10) % 10)
    if len(digits) in (8, 13) and digits[-1] != check:
        raise ValueError(f"EAN inválido: o dígito verificador correto é {check}.")
    return body + check


def _boolean(name):
    return request.form.get(name) == "on"


def _apply_form(label):
    label.name = request.form.get("name", "").strip() or "Etiqueta sem nome"
    label.product_name = request.form.get("product_name", "").strip()
    label.ean = normalize_ean(request.form.get("ean", ""))
    label.text = request.form.get("text", "")
    label.paper_width = int(request.form.get("paper_width", 60))
    label.label_height = max(15, min(300, int(request.form.get("label_height", 40))))
    label.font_size = max(10, min(100, int(request.form.get("font_size", 30))))
    label.alignment = request.form.get("alignment", "center")
    label.bold = _boolean("bold")
    label.copies = max(1, min(100, int(request.form.get("copies", 1))))
    label.cut_paper = _boolean("cut_paper")
    label.feed_lines = max(0, min(10, int(request.form.get("feed_lines", 3))))
    logo = request.files.get("logo")
    if logo and logo.filename:
        extension = secure_filename(logo.filename).rsplit(".", 1)[-1].lower()
        if extension not in current_app.config["ALLOWED_EXTENSIONS"]:
            raise ValueError("Formato de logotipo não permitido.")
        filename = f"{uuid4().hex}.{extension}"
        logo.save(Path(current_app.config["UPLOAD_FOLDER"]) / filename)
        label.logo_filename = filename


@bp.route("/")
def index():
    return render_template("index.html", labels=Label.query.order_by(Label.updated_at.desc()).all())


@bp.route("/etiqueta/nova", methods=["GET", "POST"])
@bp.route("/etiqueta/<int:label_id>/editar", methods=["GET", "POST"])
def editor(label_id=None):
    label = db.get_or_404(Label, label_id) if label_id else Label()
    if request.method == "POST":
        try:
            _apply_form(label)
            db.session.add(label)
            db.session.commit()
            flash("Etiqueta salva com sucesso.", "success")
            return redirect(url_for("main.editor", label_id=label.id))
        except (ValueError, TypeError) as error:
            db.session.rollback()
            flash(str(error), "danger")
    return render_template("editor.html", label=label, printers=list_windows_printers())


@bp.route("/etiqueta/<int:label_id>/preview.png")
def preview(label_id):
    label = db.get_or_404(Label, label_id)
    return send_file(png_bytes(render_label(label, current_app.config["UPLOAD_FOLDER"])), mimetype="image/png", max_age=0)


@bp.post("/etiqueta/<int:label_id>/imprimir")
def print_label(label_id):
    label = db.get_or_404(Label, label_id)
    try:
        image = render_label(label, current_app.config["UPLOAD_FOLDER"])
        data = escpos_raster(image, label.cut_paper, label.feed_lines)
        printer_name = request.form.get("printer_name") or None
        used = ""
        for _ in range(label.copies):
            used = print_raw(data, printer_name)
        flash(f"{label.copies} cópia(s) enviada(s) para {used}.", "success")
    except Exception as error:
        flash(f"Falha ao imprimir: {error}", "danger")
    return redirect(url_for("main.editor", label_id=label.id))


@bp.post("/etiqueta/<int:label_id>/excluir")
def delete(label_id):
    label = db.get_or_404(Label, label_id)
    db.session.delete(label)
    db.session.commit()
    flash("Etiqueta excluída.", "success")
    return redirect(url_for("main.index"))
