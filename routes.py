from pathlib import Path
from base64 import b64encode
from datetime import datetime, timezone
from secrets import compare_digest
from uuid import uuid4
from flask import Blueprint, abort, current_app, flash, jsonify, redirect, render_template, request, send_file, url_for
from werkzeug.utils import secure_filename
from models import Label, PrintJob, db
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


def _agent_authorized():
    configured = current_app.config.get("PRINT_AGENT_TOKEN", "")
    received = request.headers.get("X-Print-Agent-Token", "")
    return bool(configured and received and compare_digest(configured, received))


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
    jobs = []
    if label.id:
        jobs = PrintJob.query.filter_by(label_id=label.id).order_by(PrintJob.created_at.desc()).limit(5).all()
    return render_template("editor.html", label=label, printers=list_windows_printers(), jobs=jobs)


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


@bp.post("/etiqueta/<int:label_id>/fila")
def enqueue_print(label_id):
    label = db.get_or_404(Label, label_id)
    job = PrintJob(
        label=label,
        copies=label.copies,
        requested_by=request.remote_addr or "",
        printer_name=request.form.get("printer_name", ""),
    )
    db.session.add(job)
    db.session.commit()
    flash("Etiqueta enviada para a fila do agente local.", "success")
    return redirect(url_for("main.editor", label_id=label.id))


@bp.get("/api/print-jobs/next")
def next_print_job():
    if not _agent_authorized():
        abort(401)
    job = PrintJob.query.filter_by(status="pending").order_by(PrintJob.created_at.asc()).first()
    if not job:
        return jsonify({"job": None})

    try:
        image = render_label(job.label, current_app.config["UPLOAD_FOLDER"])
        data = escpos_raster(image, job.label.cut_paper, job.label.feed_lines)
        job.status = "processing"
        job.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        return jsonify(
            {
                "job": {
                    "id": job.id,
                    "label_id": job.label_id,
                    "label_name": job.label.name,
                    "copies": job.copies,
                    "data_base64": b64encode(data).decode("ascii"),
                }
            }
        )
    except Exception as error:
        job.status = "error"
        job.error_message = str(error)
        job.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        return jsonify({"error": str(error)}), 500


@bp.post("/api/print-jobs/<int:job_id>/complete")
def complete_print_job(job_id):
    if not _agent_authorized():
        abort(401)
    job = db.get_or_404(PrintJob, job_id)
    payload = request.get_json(silent=True) or {}
    status = payload.get("status", "")
    if status not in {"printed", "error"}:
        return jsonify({"error": "Status inválido."}), 400
    job.status = status
    job.error_message = payload.get("error_message", "")[:2000]
    job.printer_name = payload.get("printer_name", job.printer_name or "")[:255]
    job.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify({"ok": True})


@bp.post("/etiqueta/<int:label_id>/excluir")
def delete(label_id):
    label = db.get_or_404(Label, label_id)
    db.session.delete(label)
    db.session.commit()
    flash("Etiqueta excluída.", "success")
    return redirect(url_for("main.index"))
