from datetime import date, timedelta
from unittest.mock import patch
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from core.models import Project, Task, Tag
from core.services import HolidayService, ProjectService, TaskService


class CoreAPITests(TestCase):
    def setUp(self):
        cache.clear()
        self.tag_backend = Tag.objects.create(name="backend")
        self.project = Project.objects.create(
            name="Proyecto Alfa",
            description="Descripción de prueba"
        )
        self.task_completada = Task.objects.create(
            project=self.project,
            title="Tarea 1 Completada",
            description="Detalles de la tarea",
            priority="alta",
            status="completada",
            due_date=date.today() + timedelta(days=2)
        )
        self.task_completada.tags.add(self.tag_backend)

        self.task_pendiente = Task.objects.create(
            project=self.project,
            title="Tarea 2 Pendiente",
            description="Buscar wireframe en diseño",
            priority="media",
            status="pendiente",
            due_date=date.today() + timedelta(days=5)
        )

    def test_health_check(self):
        response = self.client.get(reverse("health_check"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {"status": "ok", "service": "TaskFlow API"})

    def test_project_list_pagination(self):
        response = self.client.get(reverse("project-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn("count", data)
        self.assertIn("results", data)
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["name"], "Proyecto Alfa")

    def test_project_summary_action(self):
        response = self.client.get(reverse("project-summary", kwargs={"pk": self.project.id}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["completada"], 1)
        self.assertEqual(data["pendiente"], 1)
        self.assertEqual(data["en_progreso"], 0)

    def test_task_list_pagination(self):
        response = self.client.get(reverse("task-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn("count", data)
        self.assertIn("results", data)
        self.assertEqual(data["count"], 2)

    def test_task_filtering_by_status(self):
        response = self.client.get(reverse("task-list") + "?status=completada")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["id"], self.task_completada.id)

    def test_task_search(self):
        response = self.client.get(reverse("task-list") + "?search=wireframe")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["id"], self.task_pendiente.id)

    def test_task_ordering(self):
        response = self.client.get(reverse("task-list") + "?ordering=-due_date")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        # La tarea pendiente tiene due_date más lejano
        self.assertEqual(data["results"][0]["id"], self.task_pendiente.id)

    def test_task_action_complete_success(self):
        response = self.client.post(reverse("task-complete", kwargs={"pk": self.task_pendiente.id}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["status"], "completada")
        self.task_pendiente.refresh_from_db()
        self.assertEqual(self.task_pendiente.status, "completada")

    def test_task_action_complete_without_due_date_fails(self):
        task_no_due = Task.objects.create(
            project=self.project,
            title="Tarea Sin Fecha",
            status="pendiente",
            due_date=None
        )
        response = self.client.post(reverse("task-complete", kwargs={"pk": task_no_due.id}))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertTrue(data.get("error"))
        self.assertIn("No se puede marcar una tarea como completada sin fecha límite", str(data["detail"]))

    def test_task_action_overdue(self):
        # Creamos una tarea vencida (ayer)
        task_vencida = Task.objects.create(
            project=self.project,
            title="Tarea Vencida",
            status="pendiente",
            due_date=date.today() - timedelta(days=1)
        )
        response = self.client.get(reverse("task-overdue"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn("results", data)
        ids = [item["id"] for item in data["results"]]
        self.assertIn(task_vencida.id, ids)
        self.assertNotIn(self.task_completada.id, ids)

    @patch.object(HolidayService, "get_holidays", return_value=["2026-05-25", "2026-07-09"])
    def test_due_on_holiday_field(self, mock_holidays):
        task_feriado = Task.objects.create(
            project=self.project,
            title="Tarea en Feriado",
            status="pendiente",
            due_date=date(2026, 5, 25)
        )
        response = self.client.get(reverse("task-detail", kwargs={"pk": task_feriado.id}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.json()["due_on_holiday"])

        response_normal = self.client.get(reverse("task-detail", kwargs={"pk": self.task_pendiente.id}))
        self.assertEqual(response_normal.status_code, status.HTTP_200_OK)
        self.assertFalse(response_normal.json()["due_on_holiday"])
