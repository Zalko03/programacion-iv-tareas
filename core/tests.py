from datetime import date, timedelta
from unittest.mock import patch
from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from core.models import Project, Task, Tag
from core.services import HolidayService


class CoreAPITests(TestCase):
    def setUp(self):
        cache.clear()
        self.user_a = User.objects.create_user(
            username="usuario_a",
            email="a@ejemplo.com",
            password="Password123!"
        )
        self.user_b = User.objects.create_user(
            username="usuario_b",
            email="b@ejemplo.com",
            password="Password123!"
        )

        token_a = RefreshToken.for_user(self.user_a)
        self.auth_headers_a = {"HTTP_AUTHORIZATION": f"Bearer {token_a.access_token}"}

        token_b = RefreshToken.for_user(self.user_b)
        self.auth_headers_b = {"HTTP_AUTHORIZATION": f"Bearer {token_b.access_token}"}

        self.tag_backend = Tag.objects.create(name="backend")
        self.project = Project.objects.create(
            name="Proyecto Alfa",
            description="Descripción de prueba"
        )
        self.task_a1 = Task.objects.create(
            project=self.project,
            owner=self.user_a,
            title="Tarea A1 Completada",
            description="Detalles de la tarea",
            priority="alta",
            status="completada",
            due_date=date.today() + timedelta(days=2)
        )
        self.task_a1.tags.add(self.tag_backend)

        self.task_a2 = Task.objects.create(
            project=self.project,
            owner=self.user_a,
            title="Tarea A2 Pendiente",
            description="Buscar wireframe en diseño",
            priority="media",
            status="pendiente",
            due_date=date.today() + timedelta(days=5)
        )

        self.task_b1 = Task.objects.create(
            project=self.project,
            owner=self.user_b,
            title="Tarea B1",
            description="Tarea de usuario B",
            priority="baja",
            status="pendiente",
            due_date=date.today() + timedelta(days=3)
        )

    def test_health_check_unauthenticated(self):
        response = self.client.get(reverse("health_check"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {"status": "ok", "service": "TaskFlow API"})

    def test_tasks_unauthenticated_returns_401(self):
        response = self.client.get(reverse("task-list"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        data = response.json()
        self.assertTrue(data.get("error"))
        self.assertIn("detail", data)

    def test_register_success(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "carlos",
                "email": "carlos@ejemplo.com",
                "password": "Password123!"
            },
            content_type="application/json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertNotIn("password", response.json())
        self.assertEqual(response.json()["username"], "carlos")

    def test_register_weak_password_fails(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "carlos2",
                "email": "carlos2@ejemplo.com",
                "password": "123"
            },
            content_type="application/json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertTrue(data.get("error"))

    def test_register_duplicate_email_fails(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "otro_usuario",
                "email": "a@ejemplo.com",
                "password": "Password123!"
            },
            content_type="application/json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertTrue(data.get("error"))
        self.assertIn("Ya existe un usuario con ese email", str(data["detail"]))

    def test_token_obtain_and_refresh(self):
        response = self.client.post(
            reverse("token_obtain_pair"),
            {
                "username": "usuario_a",
                "password": "Password123!"
            },
            content_type="application/json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        access = response.json().get("access")
        refresh = response.json().get("refresh")
        self.assertIsNotNone(access)
        self.assertIsNotNone(refresh)

        # Probar refresh token
        res_refresh = self.client.post(
            reverse("token_refresh"),
            {"refresh": refresh},
            content_type="application/json"
        )
        self.assertEqual(res_refresh.status_code, status.HTTP_200_OK)
        self.assertIn("access", res_refresh.json())

    def test_ownership_isolation_and_idor_prevention(self):
        # Usuario A lista sus tareas (debe ver 2 tareas: task_a1 y task_a2)
        res_a = self.client.get(reverse("task-list"), **self.auth_headers_a)
        self.assertEqual(res_a.status_code, status.HTTP_200_OK)
        self.assertEqual(res_a.json()["count"], 2)

        # Usuario B lista sus tareas (debe ver solo 1 tarea: task_b1)
        res_b = self.client.get(reverse("task-list"), **self.auth_headers_b)
        self.assertEqual(res_b.status_code, status.HTTP_200_OK)
        self.assertEqual(res_b.json()["count"], 1)
        self.assertEqual(res_b.json()["results"][0]["id"], self.task_b1.id)

        # Usuario B intenta acceder a tarea de Usuario A -> 404 (IDOR prevention)
        res_idor = self.client.get(reverse("task-detail", kwargs={"pk": self.task_a1.id}), **self.auth_headers_b)
        self.assertEqual(res_idor.status_code, status.HTTP_404_NOT_FOUND)

    def test_task_create_assigns_owner_automatically(self):
        response = self.client.post(
            reverse("task-list"),
            {
                "project": self.project.id,
                "title": "Tarea Creada Por B",
                "priority": "alta",
                "status": "pendiente",
                "due_date": str(date.today() + timedelta(days=4)),
            },
            content_type="application/json",
            **self.auth_headers_b
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        new_task = Task.objects.get(id=response.json()["id"])
        self.assertEqual(new_task.owner, self.user_b)

    def test_project_list_authenticated(self):
        response = self.client.get(reverse("project-list"), **self.auth_headers_a)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["count"], 1)

    def test_task_action_complete_authenticated(self):
        response = self.client.post(
            reverse("task-complete", kwargs={"pk": self.task_a2.id}),
            **self.auth_headers_a
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.task_a2.refresh_from_db()
        self.assertEqual(self.task_a2.status, "completada")

    def test_task_action_overdue_authenticated(self):
        task_vencida = Task.objects.create(
            project=self.project,
            owner=self.user_a,
            title="Tarea Vencida A",
            status="pendiente",
            due_date=date.today() - timedelta(days=1)
        )
        response = self.client.get(reverse("task-overdue"), **self.auth_headers_a)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [item["id"] for item in response.json()["results"]]
        self.assertIn(task_vencida.id, ids)

    @patch.object(HolidayService, "get_holidays", return_value=["2026-05-25"])
    def test_due_on_holiday_field_authenticated(self, mock_holidays):
        task_feriado = Task.objects.create(
            project=self.project,
            owner=self.user_a,
            title="Tarea en Feriado A",
            status="pendiente",
            due_date=date(2026, 5, 25)
        )
        response = self.client.get(reverse("task-detail", kwargs={"pk": task_feriado.id}), **self.auth_headers_a)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.json()["due_on_holiday"])
