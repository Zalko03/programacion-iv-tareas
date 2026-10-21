from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from core.models import Project, Task, Tag


class CoreAPITests(TestCase):
    def setUp(self):
        self.tag_backend = Tag.objects.create(name="backend")
        self.project = Project.objects.create(
            name="Proyecto Alfa",
            description="Descripción de prueba"
        )
        self.task = Task.objects.create(
            project=self.project,
            title="Tarea 1",
            description="Detalles de la tarea",
            priority="alta",
            status="pendiente"
        )
        self.task.tags.add(self.tag_backend)

    def test_health_check(self):
        response = self.client.get(reverse("health_check"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {"status": "ok", "service": "TaskFlow API"})

    def test_project_list(self):
        response = self.client.get(reverse("project_list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "Proyecto Alfa")
        self.assertEqual(len(data[0]["tasks"]), 1)
        self.assertEqual(data[0]["tasks"][0]["title"], "Tarea 1")
        self.assertEqual(data[0]["tasks"][0]["tags"][0]["name"], "backend")

    def test_project_detail_success(self):
        response = self.client.get(reverse("project_detail", kwargs={"project_id": self.project.id}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["name"], "Proyecto Alfa")
        self.assertEqual(len(data["tasks"]), 1)

    def test_project_detail_not_found(self):
        response = self.client.get(reverse("project_detail", kwargs={"project_id": 9999}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_task_list(self):
        response = self.client.get(reverse("task_list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["title"], "Tarea 1")
        self.assertEqual(data[0]["project"], self.project.id)
        self.assertEqual(data[0]["tags"][0]["name"], "backend")
