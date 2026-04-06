from rest_framework import serializers

from user_projects.models import UserProject


class UserProjectSerializer(serializers.ModelSerializer):
    position_name = serializers.CharField(source="position.name", read_only=True)

    class Meta:
        model = UserProject
        fields = [
            "project_id",
            "position",
            "position_name",
            "project_name",
            "project_role",
            "project_description",
            "project_result",
            "created_at",
            "updated_at",
        ]


class UserProjectCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProject
        fields = [
            "position",
            "project_name",
            "project_role",
            "project_description",
            "project_result",
        ]
