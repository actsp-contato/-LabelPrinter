from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Label(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    product_name = db.Column(db.String(180), default="")
    ean = db.Column(db.String(13), default="")
    text = db.Column(db.Text, default="")
    logo_filename = db.Column(db.String(255))
    paper_width = db.Column(db.Integer, default=60)
    label_height = db.Column(db.Integer, default=40)
    font_size = db.Column(db.Integer, default=30)
    alignment = db.Column(db.String(10), default="center")
    bold = db.Column(db.Boolean, default=False)
    copies = db.Column(db.Integer, default=1)
    cut_paper = db.Column(db.Boolean, default=True)
    feed_lines = db.Column(db.Integer, default=3)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class PrintJob(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    label_id = db.Column(db.Integer, db.ForeignKey("label.id"), nullable=False)
    label = db.relationship("Label", backref=db.backref("print_jobs", lazy=True))
    status = db.Column(db.String(20), default="pending", nullable=False)
    requested_by = db.Column(db.String(120), default="")
    printer_name = db.Column(db.String(255), default="")
    copies = db.Column(db.Integer, default=1)
    error_message = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
