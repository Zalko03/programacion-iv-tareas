from datetime import date
from rest_framework import serializers
from .models import Project, Task, Tag


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "name"]


class TaskSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True, read_only=True)

    class Meta:
        model = Task
        fields = [
            "id", "project", "title", "description",
            "priority", "status", "due_date", "tags", "created_at",
        ]

    def validate_due_date(self, value):
        if value and value < date.today():
            raise serializers.ValidationError("La fecha límite no puede ser en el pasado.")
        return value

    def validate(self, data):
        # 1. Regla: no completar sin fecha límite
        status = data.get("status") or (self.instance.status if self.instance else None)
        due_date = data.get("due_date") if "due_date" in data else (self.instance.due_date if self.instance else None)

        if status == "completada" and not due_date:
            raise serializers.ValidationError(
                "No se puede marcar una tarea como completada sin fecha límite registrada."
            )

        # 2. Regla de negocio (Tarea para la casa): no 'en_progreso' si el proyecto no tiene tareas completadas
        if status == "en_progreso":
            project = data.get("project") or (self.instance.project if self.instance else None)
            if project:
                tiene_completadas = project.tasks.filter(status="completada").exists()
                if not tiene_completadas:
                    raise serializers.ValidationError(
                        "No se puede iniciar una tarea si el proyecto no tiene ninguna tarea completada."
                    )

        return data


class ProjectSerializer(serializers.ModelSerializer):
    tasks = TaskSerializer(many=True, read_only=True)

    class Meta:
        model = Project
        fields = ["id", "name", "description", "tasks", "created_at"]