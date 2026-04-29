from django.db import models

class Patient(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    contact_info = models.CharField(max_length=200)
    assigned_doctor_id = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

class Consultation(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='consultations')
    doctor_id = models.IntegerField()
    date = models.DateTimeField(auto_now_add=True)
    scanner_image_url = models.CharField(max_length=500)
    ai_result = models.CharField(max_length=100)
    ai_confidence = models.FloatField(null=True, blank=True)
    medical_notes = models.TextField()
    status = models.CharField(max_length=20, default='pending', choices=[('pending', 'Pending'), ('validated', 'Validated')])
    appointment_id = models.BigIntegerField(null=True, blank=True)

    def __str__(self):
        return f"Consultation for {self.patient} on {self.date}"
