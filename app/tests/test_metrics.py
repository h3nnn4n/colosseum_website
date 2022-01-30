from uuid import uuid4

from django.test import TestCase

from app.metrics import process_urls_into_tags


class ProcessUrlsIntoTagsTestCase(TestCase):
    def test_agent_detail(self):
        result = process_urls_into_tags(f"/api/agents/{uuid4()}/")
        self.assertEqual(result, "/api/agents/<pk>/")

    def test_agent_index(self):
        result = process_urls_into_tags("/api/agents/")
        self.assertEqual(result, "/api/agents/")

    def test_multiple_pk_fake(self):
        result = process_urls_into_tags(f"/foo/{uuid4()}/bar/{uuid4()}/{uuid4()}/")
        self.assertEqual(result, "/foo/<pk>/bar/<pk>/<pk>/")
