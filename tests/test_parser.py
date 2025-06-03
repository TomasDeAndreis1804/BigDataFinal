import pytest
from unittest.mock import patch, MagicMock
from parser import parser

# Evento simulado para Lambda con archivo válido en S3
mock_event = {
    "Records": [
        {
            "s3": {
                "bucket": {"name": "mi-bucket"},
                "object": {"key": "headlines/raw/publimetro_2025-06-03.html"}
            }
        }
    ]
}

# Contenido HTML de prueba para simular get_object
mock_html_content = """
<html>
<body>
    <article>
        <h2>Noticia de prueba</h2>
        <a href="/categoria/noticia1">Link</a>
    </article>
</body>
</html>
"""

@patch("parser.parser.s3")
def test_app_lambda(mock_s3_client):
    # Mock para get_object: devuelve contenido HTML
    mock_s3_client.get_object.return_value = {
        "Body": MagicMock(read=lambda: mock_html_content.encode("utf-8"))
    }
    # Mock para put_object: simulamos éxito
    mock_s3_client.put_object.return_value = {}

    # Ejecutamos la función app
    response = parser.app(mock_event, None)

    # Verificamos que get_object se llamó con bucket y key correctos
    mock_s3_client.get_object.assert_called_once_with(
        Bucket="mi-bucket",
        Key="headlines/raw/publimetro_2025-06-03.html"
    )

    # Verificamos que put_object se llamó para subir el CSV (revisamos solo la llamada, no el contenido exacto)
    mock_s3_client.put_object.assert_called_once()
    put_call_args = mock_s3_client.put_object.call_args[1]
    assert put_call_args["Bucket"] == "mi-bucket"
    assert put_call_args["Key"].startswith("headlines/final/periodico=publimetro/")

    # Verificamos la respuesta
    assert response["statusCode"] == 200
    assert "publimetro" in response["body"]