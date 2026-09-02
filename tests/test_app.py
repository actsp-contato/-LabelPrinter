import tempfile
from app import create_app


def test_create_ean_label_and_preview():
    with tempfile.TemporaryDirectory() as folder:
        app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:", "UPLOAD_FOLDER": folder})
        client = app.test_client()
        response = client.post("/etiqueta/nova", data={"name":"Teste 60x40", "product_name":"Café 500 g", "ean":"789123456789", "text":"Produto teste", "paper_width":"60", "label_height":"40", "font_size":"24", "alignment":"center", "copies":"1", "feed_lines":"3", "cut_paper":"on"})
        assert response.status_code == 302
        preview = client.get("/etiqueta/1/preview.png")
        assert preview.status_code == 200
        assert preview.mimetype == "image/png"


def test_rejects_invalid_ean_check_digit():
    with tempfile.TemporaryDirectory() as folder:
        app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:", "UPLOAD_FOLDER": folder})
        response = app.test_client().post("/etiqueta/nova", data={"name":"Inválida", "ean":"7891234567890", "paper_width":"60", "label_height":"40", "font_size":"24", "alignment":"center", "copies":"1", "feed_lines":"3"})
        assert response.status_code == 200
        assert "dígito verificador correto" in response.get_data(as_text=True)
