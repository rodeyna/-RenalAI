from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('doctor', 'Doctor'),
        ('assistant', 'Assistant'),
    )
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='doctor')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    assigned_doctor = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='assistants')
    quit_requested = models.BooleanField(default=False)
    phone = models.CharField(max_length=20, null=True, blank=True)
    clinic_name = models.CharField(max_length=100, null=True, blank=True)
    location = models.CharField(max_length=255, null=True, blank=True)
    # On overriding email as unique identifier
    email = models.EmailField(unique=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    def __str__(self):
        return f"{self.email} ({self.role} - {self.status})"
