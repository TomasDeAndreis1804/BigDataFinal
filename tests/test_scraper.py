import pytest
from unittest.mock import patch, MagicMock
from scraper import scraper
import json

@patch("scraper.scraper.s3")
@patch("scraper.scraper.requests.get")
def test_scraper_app(mock_requests_get, mock_s3_client):
    # Configurar el mock para requests.get
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "<html>contenido de prueba</html>"
    mock_requests_get.return_value = mock_response

    # Configurar mock para s3.put_object
    mock_s3_client.put_object.return_value = {}

    # Llamar la función app con evento y contexto None
    response = scraper.app({}, None)

    # Validar que requests.get fue llamada con las URLs correctas
    mock_requests_get.assert_any_call('https://www.eltiempo.com', timeout=10)
    mock_requests_get.assert_any_call('https://www.publimetro.co/', timeout=10)
    assert mock_requests_get.call_count == 2

    # Validar que s3.put_object fue llamada dos veces (una por cada página)
    assert mock_s3_client.put_object.call_count == 2

    # Revisar que las llamadas a put_object usaron el bucket correcto y keys con el prefijo esperado
    bucket_name = 'parcial3-t-s'
    for call_args in mock_s3_client.put_object.call_args_list:
        kwargs = call_args.kwargs
        assert kwargs['Bucket'] == bucket_name
        assert kwargs['Key'].startswith('headlines/raw/')
        assert kwargs['Body'] == "<html>contenido de prueba</html>"
        assert kwargs['ContentType'] == 'text/html'

    # Verificar respuesta
    assert response['statusCode'] == 200
    assert json.loads(response['body']) == 'Scraping completado exitosamente'