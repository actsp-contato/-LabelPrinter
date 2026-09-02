from pathlib import Path
from flask import Flask
from config import Config
from models import db
from routes import bp
from sqlalchemy import inspect, text


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    db.init_app(app)
    app.register_blueprint(bp)
    with app.app_context():
        db.create_all()
        columns = {column["name"] for column in inspect(db.engine).get_columns("label")}
        for name, definition in {"product_name": "VARCHAR(180) DEFAULT ''", "ean": "VARCHAR(13) DEFAULT ''"}.items():
            if name not in columns:
                db.session.execute(text(f"ALTER TABLE label ADD COLUMN {name} {definition}"))
        db.session.commit()
    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=5000, debug=True)
