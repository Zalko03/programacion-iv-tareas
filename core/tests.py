from datetime import date, timedelta
from unittest.mock import patch
from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from asgiref.sync import async_to_sync
from channels.testing import WebsocketCommunicator
from config.asgi import application
from core.models import Project, ProjectMembership, Task, Tag, SecurityLog
from core.services import HolidayService



class CoreAPITests(TestCase):
    def setUp(self):
        cache.clear()
        self.user_admin = User.objects.create_user(
            username="admin_user",
            email="admin_user@ejemplo.com",
            password="Password123!"
        )
        self.user_member = User.objects.create_user(
            username="member_user",
            email="member_user@ejemplo.com",
            password="Password123!"
        )
        self.user_stranger = User.objects.create_user(
            username="stranger_user",
            email="stranger_user@ejemplo.com",
            password="Password123!"
        )

        token_admin = RefreshToken.for_user(self.user_admin)
        self.auth_admin = {"HTTP_AUTHORIZATION": f"Bearer {token_admin.access_token}"}

        token_member = RefreshToken.for_user(self.user_member)
        self.auth_member = {"HTTP_AUTHORIZATION": f"Bearer {token_member.access_token}"}

        token_stranger = RefreshToken.for_user(self.user_stranger)
        self.auth_stranger = {"HTTP_AUTHORIZATION": f"Bearer {token_stranger.access_token}"}

        self.tag_backend = Tag.objects.create(name="backend")
        self.project = Project.objects.create(
            name="Proyecto Alfa",
            description="Descripción de prueba"
        )
        # Memberships
        ProjectMembership.objects.create(project=self.project, user=self.user_admin, role="admin")
        ProjectMembership.objects.create(project=self.project, user=self.user_member, role="miembro")

        self.task_1 = Task.objects.create(
            project=self.project,
            owner=self.user_admin,
            title="Tarea 1 Completada",
            description="Detalles de la tarea",
            priority="alta",
            status="completada",
            due_date=date.today() + timedelta(days=2)
        )
        self.task_1.tags.add(self.tag_backend)

        self.task_2 = Task.objects.create(
            project=self.project,
            owner=self.user_admin,
            title="Tarea 2 Pendiente",
            description="Buscar wireframe en diseño",
            priority="media",
            status="pendiente",
            due_date=date.today() + timedelta(days=5)
        )

    def test_health_check_unauthenticated(self):
        response = self.client.get(reverse("health_check"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {"status": "ok", "service": "TaskFlow API"})

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

    def test_social_login_jwt_view(self):
        response = self.client.get(reverse("social_jwt"), **self.auth_admin)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn("access", data)
        self.assertIn("refresh", data)

    def test_project_visibility_by_membership(self):
        # Admin ve el proyecto
        res_admin = self.client.get(reverse("project-list"), **self.auth_admin)
        self.assertEqual(res_admin.status_code, status.HTTP_200_OK)
        self.assertEqual(res_admin.json()["count"], 1)

        # Miembro ve el proyecto
        res_member = self.client.get(reverse("project-list"), **self.auth_member)
        self.assertEqual(res_member.status_code, status.HTTP_200_OK)
        self.assertEqual(res_member.json()["count"], 1)

        # Extraño no lo ve (lista vacía)
        res_stranger = self.client.get(reverse("project-list"), **self.auth_stranger)
        self.assertEqual(res_stranger.status_code, status.HTTP_200_OK)
        self.assertEqual(res_stranger.json()["count"], 0)

        # Extraño pide por id -> 404
        res_detail = self.client.get(reverse("project-detail", kwargs={"pk": self.project.id}), **self.auth_stranger)
        self.assertEqual(res_detail.status_code, status.HTTP_404_NOT_FOUND)

    def test_project_create_assigns_admin_membership_atomically(self):
        response = self.client.post(
            reverse("project-list"),
            {"name": "Proyecto Beta", "description": "Nuevo proyecto"},
            content_type="application/json",
            **self.auth_admin
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        new_project_id = response.json()["id"]
        membership = ProjectMembership.objects.filter(project_id=new_project_id, user=self.user_admin).first()
        self.assertIsNotNone(membership)
        self.assertEqual(membership.role, "admin")

    def test_member_cannot_modify_project(self):
        response = self.client.patch(
            reverse("project-detail", kwargs={"pk": self.project.id}),
            {"name": "Nombre Modificado"},
            content_type="application/json",
            **self.auth_member
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_task_create_by_admin_succeeds(self):
        response = self.client.post(
            reverse("task-list"),
            {
                "project": self.project.id,
                "title": "Tarea Creada Por Admin",
                "priority": "alta",
                "status": "pendiente",
                "due_date": str(date.today() + timedelta(days=7)),
            },
            content_type="application/json",
            **self.auth_admin
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_task_create_by_member_fails_403(self):
        response = self.client.post(
            reverse("task-list"),
            {
                "project": self.project.id,
                "title": "Intento de Miembro",
                "priority": "alta",
                "status": "pendiente",
                "due_date": str(date.today() + timedelta(days=7)),
            },
            content_type="application/json",
            **self.auth_member
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_task_modify_by_member_fails_403(self):
        response = self.client.patch(
            reverse("task-detail", kwargs={"pk": self.task_2.id}),
            {"title": "Nuevo Titulo"},
            content_type="application/json",
            **self.auth_member
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_add_member_by_admin(self):
        response = self.client.post(
            reverse("project-add-member", kwargs={"pk": self.project.id}),
            {"username": "stranger_user", "role": "miembro"},
            content_type="application/json",
            **self.auth_admin
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(ProjectMembership.objects.filter(project=self.project, user=self.user_stranger).exists())

    def test_add_member_by_non_admin_fails_403(self):
        response = self.client.post(
            reverse("project-add-member", kwargs={"pk": self.project.id}),
            {"username": "stranger_user", "role": "miembro"},
            content_type="application/json",
            **self.auth_member
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_add_member_already_exists_fails_400(self):
        response = self.client.post(
            reverse("project-add-member", kwargs={"pk": self.project.id}),
            {"username": "member_user", "role": "miembro"},
            content_type="application/json",
            **self.auth_admin
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_add_member_user_not_found_fails_404(self):
        response = self.client.post(
            reverse("project-add-member", kwargs={"pk": self.project.id}),
            {"username": "usuario_inexistente_xyz", "role": "miembro"},
            content_type="application/json",
            **self.auth_admin
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch.object(HolidayService, "get_holidays", return_value=["2026-05-25"])
    def test_due_on_holiday_field(self, mock_holidays):
        task_feriado = Task.objects.create(
            project=self.project,
            owner=self.user_admin,
            title="Tarea en Feriado",
            status="pendiente",
            due_date=date(2026, 5, 25)
        )
        response = self.client.get(reverse("task-detail", kwargs={"pk": task_feriado.id}), **self.auth_admin)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.json()["due_on_holiday"])

    def test_task_description_sanitization(self):
        response = self.client.post(
            reverse("task-list"),
            {
                "project": self.project.id,
                "title": "Tarea con XSS",
                "description": "<script>alert(1)</script>Hola <b>mundo</b>",
                "priority": "media",
                "status": "pendiente",
                "due_date": str(date.today() + timedelta(days=3)),
            },
            content_type="application/json",
            **self.auth_admin,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()["description"], "Hola mundo")

    def test_login_rate_limiting_and_security_log(self):
        SecurityLog.objects.filter(action="login_failed").delete()
        for _ in range(5):
            res = self.client.post(
                reverse("token_obtain_pair"),
                {"username": "admin_user", "password": "wrong_password"},
                content_type="application/json",
            )
            self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

        # 6th attempt should be throttled (429)
        res_6 = self.client.post(
            reverse("token_obtain_pair"),
            {"username": "admin_user", "password": "wrong_password"},
            content_type="application/json",
        )
        self.assertEqual(res_6.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

        # There should be 5 login_failed logs (the 6th was throttled before checking password)
        failed_logs = SecurityLog.objects.filter(action="login_failed")
        self.assertEqual(failed_logs.count(), 5)
        self.assertIn("usuario=admin_user", failed_logs.first().detail)

    def test_permission_denied_creates_security_log(self):
        SecurityLog.objects.filter(action="permission_denied").delete()
        response = self.client.patch(
            reverse("project-detail", kwargs={"pk": self.project.id}),
            {"name": "Intento no autorizado"},
            content_type="application/json",
            **self.auth_member,
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        log = SecurityLog.objects.filter(action="permission_denied", user=self.user_member).first()
        self.assertIsNotNone(log)

    def test_cors_allowed_origins(self):
        # Origin permitido
        res_allowed = self.client.get(
            reverse("health_check"),
            HTTP_ORIGIN="http://localhost:3000",
        )
        self.assertEqual(res_allowed.headers.get("Access-Control-Allow-Origin"), "http://localhost:3000")

        # Origin no permitido
        res_disallowed = self.client.get(
            reverse("health_check"),
            HTTP_ORIGIN="http://sitio-malicioso.com",
        )
        self.assertNotIn("Access-Control-Allow-Origin", res_disallowed.headers)

    def test_websocket_connect_and_echo(self):
        async def run():
            communicator = WebsocketCommunicator(application, f"/ws/projects/{self.project.id}/")
            connected, _ = await communicator.connect()
            self.assertTrue(connected)

            await communicator.send_json_to({"mensaje": "hola desde el cliente"})
            response = await communicator.receive_json_from()
            self.assertEqual(response, {"echo": {"mensaje": "hola desde el cliente"}})

            await communicator.disconnect()

        async_to_sync(run)()

    def test_websocket_rejects_nonexistent_project(self):
        async def run():
            communicator = WebsocketCommunicator(application, "/ws/projects/999999/")
            connected, _ = await communicator.connect()
            self.assertFalse(connected)
            await communicator.disconnect()

        async_to_sync(run)()


