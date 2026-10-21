from datetime import date, timedelta
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
        self.task_completada = Task.objects.create(
            project=self.project,
            title="Tarea 1",
            description="Detalles de la tarea",
            priority="alta",
            status="completada",
            due_date=date.today() + timedelta(days=2)
        )
        self.task_completada.tags.add(self.tag_backend)

    def test_health_check(self):
        response = self.client.get(reverse("health_check"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {"status": "ok", "service": "TaskFlow API"})

    def test_project_list(self):
        response = self.client.get(reverse("project-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "Proyecto Alfa")
        self.assertEqual(len(data[0]["tasks"]), 1)
        self.assertEqual(data[0]["tasks"][0]["tags"][0]["name"], "backend")

    def test_project_detail_success(self):
        response = self.client.get(reverse("project-detail", kwargs={"pk": self.project.id}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["name"], "Proyecto Alfa")

    def test_project_detail_not_found_custom_exception(self):
        response = self.client.get(reverse("project-detail", kwargs={"pk": 9999}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        data = response.json()
        self.assertTrue(data.get("error"))
        self.assertIn("detail", data)

    def test_task_list(self):
        response = self.client.get(reverse("task-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["title"], "Tarea 1")

    def test_task_create_success(self):
        response = self.client.post(
            reverse("task-list"),
            {
                "project": self.project.id,
                "title": "Nueva Tarea",
                "priority": "media",
                "status": "pendiente",
                "due_date": str(date.today() + timedelta(days=5)),
            },
            content_type="application/json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()["title"], "Nueva Tarea")

    def test_task_create_invalid_due_date_past(self):
        response = self.client.post(
            reverse("task-list"),
            {
                "project": self.project.id,
                "title": "Tarea Pasada",
                "due_date": str(date.today() - timedelta(days=1)),
            },
            content_type="application/json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertTrue(data.get("error"))
        self.assertIn("La fecha límite no puede ser en el pasado.", str(data["detail"]))

    def test_task_create_completada_without_due_date(self):
        response = self.client.post(
            reverse("task-list"),
            {
                "project": self.project.id,
                "title": "Tarea Sin Fecha",
                "status": "completada",
            },
            content_type="application/json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertTrue(data.get("error"))
        self.assertIn("No se puede marcar una tarea como completada sin fecha límite", str(data["detail"]))

    def test_task_create_en_progreso_without_completed_tasks_in_project(self):
        proyecto_vacio = Project.objects.create(name="Proyecto Vacio")
        response = self.client.post(
            reverse("task-list"),
            {
                "project": proyecto_vacio.id,
                "title": "Tarea Inicial",
                "status": "en_progreso",
            },
            content_type="application/json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertTrue(data.get("error"))
        self.assertIn("No se puede iniciar una tarea si el proyecto no tiene ninguna tarea completada", str(data["detail"]))

    def test_task_delete(self):
        response = self.client.delete(reverse("task-detail", kwargs={"pk": self.task_completada.id}))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Task.objects.filter(id=self.task_completada.id).exists())
