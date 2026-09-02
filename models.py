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
