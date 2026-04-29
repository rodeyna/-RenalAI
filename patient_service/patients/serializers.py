from rest_framework import serializers
from .models import Patient, Consultation

class ConsultationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Consultation
        fields = '__all__'

class PatientSerializer(serializers.ModelSerializer):
    consultations = ConsultationSerializer(many=True, read_only=True)
    
    class Meta:
        model = Patient
        fields = '__all__'
