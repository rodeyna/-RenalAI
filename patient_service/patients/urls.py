from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PatientViewSet, ConsultationViewSet

router = DefaultRouter()
router.register(r'patients', PatientViewSet)
router.register(r'consultations', ConsultationViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
