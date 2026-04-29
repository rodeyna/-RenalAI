# start_all.ps1
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host " Démarrage du système Medical Microservices" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# 1. Check if Docker is running
Write-Host "Vérification de Docker..." -ForegroundColor Yellow
$dockerStatus = (docker info 2>&1)
if ($dockerStatus -match "error during connect") {
    Write-Host "ERREUR: Docker n'est pas lancé. Veuillez démarrer Docker Desktop et réessayer." -ForegroundColor Red
    exit 1
}
Write-Host "Docker est en cours d'exécution." -ForegroundColor Green

# 2. Build and start containers
Write-Host "Construction et démarrage des conteneurs (cela peut prendre quelques minutes)..." -ForegroundColor Yellow
docker-compose up -d --build

# 3. Wait for infrastructure to be ready
Write-Host "Attente de l'initialisation de RabbitMQ et Consul (20 secondes)..." -ForegroundColor Yellow
Start-Sleep -Seconds 20

# 4. Run Django Migrations
Write-Host "Application des migrations pour Auth Service..." -ForegroundColor Yellow
docker exec -e DJANGO_SETTINGS_MODULE=core.settings auth_service python manage.py makemigrations
docker exec -e DJANGO_SETTINGS_MODULE=core.settings auth_service python manage.py migrate

Write-Host "Application des migrations pour Patient Service..." -ForegroundColor Yellow
docker exec -e DJANGO_SETTINGS_MODULE=core.settings patient_service python manage.py makemigrations
docker exec -e DJANGO_SETTINGS_MODULE=core.settings patient_service python manage.py migrate

# 5. Create default admin if not exists (in auth_service)
Write-Host "Création de l'administrateur par défaut..." -ForegroundColor Yellow
$createAdminCmd = "import os, django; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings'); django.setup(); from django.contrib.auth import get_user_model; User = get_user_model(); exists = User.objects.filter(email='admin@hospital.com').exists(); print('Exists:', exists); (User.objects.create_superuser('admin', 'admin@hospital.com', 'admin123', status='approved') if not exists else print('Admin already exists'))"

docker exec auth_service python -c "$createAdminCmd"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host " Système prêt ! URLs d'accès :" -ForegroundColor Green
Write-Host " - Frontend (App)  : http://localhost:5001"
Write-Host " - Auth API        : http://localhost:8001/api/"
Write-Host " - Patient API     : http://localhost:8002/api/"
Write-Host " - Scanner AI API  : http://localhost:8003/docs"
Write-Host " - Consul UI       : http://localhost:8500"
Write-Host " - RabbitMQ UI     : http://localhost:15672 (admin/admin123)"
Write-Host "==========================================" -ForegroundColor Cyan
