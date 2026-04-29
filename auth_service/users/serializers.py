from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    assigned_assistants = serializers.PrimaryKeyRelatedField(many=True, queryset=User.objects.filter(role='assistant'), required=False, write_only=True)
    assistants = serializers.SerializerMethodField()
    doctor = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role', 'status', 'password', 'assigned_assistants', 'assistants', 'doctor', 'assigned_doctor', 'quit_requested', 'phone', 'clinic_name', 'location']
        extra_kwargs = {
            'password': {'write_only': True},
            'assigned_doctor': {'read_only': True}
        }

    def get_doctor(self, obj):
        if obj.role == 'assistant' and obj.assigned_doctor:
            return {"id": obj.assigned_doctor.id, "first_name": obj.assigned_doctor.first_name, "last_name": obj.assigned_doctor.last_name}
        return None

    def get_assistants(self, obj):
        if obj.role == 'doctor':
            return [{"id": ast.id, "first_name": ast.first_name, "last_name": ast.last_name, "quit_requested": ast.quit_requested} for ast in obj.assistants.all()]
        return []

    def create(self, validated_data):
        assigned_assistants = validated_data.pop('assigned_assistants', [])
        assigned_doctor_id = self.initial_data.get('assigned_doctor')
        user = User.objects.create_user(**validated_data)
        
        # If doctor signs up and selects assistants
        if user.role == 'doctor' and assigned_assistants:
            for ast in assigned_assistants:
                if ast.assigned_doctor:
                    continue
                ast.assigned_doctor = user
                ast.save()
        
        # If assistant signs up and is pre-assigned to a doctor
        if user.role == 'assistant' and assigned_doctor_id:
            try:
                doc = User.objects.get(id=assigned_doctor_id, role='doctor')
                user.assigned_doctor = doc
                user.save()
            except User.DoesNotExist:
                pass

        if user.role == 'admin':
            user.status = 'approved'
            user.save()
        return user
