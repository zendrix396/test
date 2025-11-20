from django.test import TestCase
from django.urls import reverse

class OpenAPISchemaTests(TestCase):
    def test_schema_url_is_accessible(self):
        """
        Test that the OpenAPI schema URL is accessible and returns a 200 OK response.
        """
        url = reverse('schema')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_swagger_ui_is_accessible(self):
        """
        Test that the Swagger UI URL is accessible and returns a 200 OK response.
        """
        url = reverse('swagger-ui')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_redoc_ui_is_accessible(self):
        """
        Test that the ReDoc UI URL is accessible and returns a 200 OK response.
        """
        url = reverse('redoc')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
