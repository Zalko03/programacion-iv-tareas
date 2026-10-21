from django.contrib.auth.models import User
from django.db import transaction
from django.http import JsonResponse
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Project, ProjectMembership
from .permissions import IsProjectAdminOrReadOnly
from .repositories import TaskRepository
from .serializers import ProjectSerializer, TaskSerializer
from .serializers_auth import RegisterSerializer
from .services import MembershipService, ProjectService, TaskService


def health_check(request):
    return JsonResponse({"status": "ok", "service": "TaskFlow API"})


class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all().order_by("id")
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated, IsProjectAdminOrReadOnly]

    def get_queryset(self):
        return MembershipService.projects_for(self.request.user)

    def perform_create(self, serializer):
        # Quien crea el proyecto queda como su admin
        with transaction.atomic():
            project = serializer.save()
            ProjectMembership.objects.create(project=project, user=self.request.user, role="admin")

    @action(detail=True, methods=["get"])
    def summary(self, request, pk=None):
        project = self.get_object()
        summary_data = ProjectService.project_summary(project)
        return Response(summary_data)

    @action(detail=True, methods=["post"])
    def add_member(self, request, pk=None):
        project = self.get_object()
        username = request.data.get("username")
        role = request.data.get("role", "miembro")

        if not username:
            return Response(
                {"error": True, "detail": "El campo username es obligatorio."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user_to_add = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response(
                {"error": True, "detail": "Usuario no encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if ProjectMembership.objects.filter(project=project, user=user_to_add).exists():
            return Response(
                {"error": True, "detail": "El usuario ya es miembro de este proyecto."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        membership = ProjectMembership.objects.create(project=project, user=user_to_add, role=role)
        return Response(
            {
                "id": membership.id,
                "user": user_to_add.username,
                "project": project.id,
                "role": membership.role,
            },
            status=status.HTTP_201_CREATED,
        )


class TaskViewSet(viewsets.ModelViewSet):
    queryset = TaskRepository.get_queryset()
    serializer_class = TaskSerializer
    filterset_fields = ["status", "priority", "project"]
    ordering_fields = ["due_date", "created_at", "priority"]
    search_fields = ["title", "description"]
    permission_classes = [IsAuthenticated, IsProjectAdminOrReadOnly]

    def get_queryset(self):
        return super().get_queryset().filter(
            project__memberships__user=self.request.user
        ).distinct()

    def check_project_admin(self, project):
        if not MembershipService.is_admin(self.request.user, project):
            raise PermissionDenied("Solo un admin del proyecto puede crear o mover tareas en él.")

    def perform_create(self, serializer):
        self.check_project_admin(serializer.validated_data["project"])
        serializer.save(owner=self.request.user)

    def perform_update(self, serializer):
        if "project" in serializer.validated_data:
            self.check_project_admin(serializer.validated_data["project"])
        serializer.save()

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        task = self.get_object()
        TaskService.mark_completed(task)
        return Response(self.get_serializer(task).data)

    @action(detail=False, methods=["get"])
    def overdue(self, request):
        tasks = TaskService.tasks_overdue(self.get_queryset())
        page = self.paginate_queryset(tasks)
        if page is not None:
            return self.get_paginated_response(self.get_serializer(page, many=True).data)
        return Response(self.get_serializer(tasks, many=True).data)


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class SocialLoginJWTView(APIView):
    """
    Después de loguearse con Google, allauth deja al usuario con una sesión
    de Django. Esta vista toma ese usuario y le entrega un par de JWT propios,
    los mismos que devuelve /api/token/ (Clase 6).
    """

    def get(self, request):
        refresh = RefreshToken.for_user(request.user)
        return Response({"refresh": str(refresh), "access": str(refresh.access_token)})