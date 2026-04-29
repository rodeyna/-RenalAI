from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from .serializers import UserSerializer

User = get_user_model()

# In-memory storage for reset requests to avoid database migrations
RESET_REQUESTS = {}
LEAVE_REQUESTS = {}

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    @action(detail=False, methods=['post'])
    def signup(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({"message": "User created. Status is pending.", "user_id": user.id}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def login(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        
        # We need to authenticate using email, but Django's default auth uses username.
        # We set USERNAME_FIELD='email' in models.py, so this should work.
        user = authenticate(request, username=email, password=password)
        
        if user is not None:
            if user.status != 'approved':
                return Response({"error": "Account is pending approval by an administrator."}, status=status.HTTP_403_FORBIDDEN)
            # Typically you'd return a JWT token here. For simplicity, just return user info.
            return Response({"message": "Login successful", "user": UserSerializer(user).data})
        return Response({"error": "Invalid Credentials"}, status=status.HTTP_401_UNAUTHORIZED)
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        user = self.get_object()
        user.status = 'approved'
        user.save()
        return Response({"message": "User approved."})

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        user = self.get_object()
        user.delete()
        return Response({"message": "User rejected and deleted."})

    @action(detail=True, methods=['post'])
    def delete_user(self, request, pk=None):
        user = self.get_object()
        # Safety check: prevent deleting an admin account for now, or at least prevent self-deletion
        if user.id == request.user.id:
            return Response({"error": "You cannot delete your own account"}, status=status.HTTP_400_BAD_REQUEST)
        user.delete()
        return Response({"message": "User account deleted."})

    @action(detail=False, methods=['post'])
    def request_reset(self, request):
        email = request.data.get('email')
        new_password = request.data.get('new_password')
        try:
            user = User.objects.get(email=email)
            RESET_REQUESTS[str(user.id)] = {
                "id": user.id,
                "full_name": f"{user.first_name} {user.last_name}",
                "email": user.email,
                "new_password": new_password
            }
            return Response({"message": "Reset request sent to admin."})
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['get'])
    def list_resets(self, request):
        return Response(list(RESET_REQUESTS.values()))

    @action(detail=True, methods=['post'])
    def approve_reset(self, request, pk=None):
        request_data = RESET_REQUESTS.get(str(pk))
        if request_data:
            user = User.objects.get(id=pk)
            user.set_password(request_data['new_password'])
            user.save()
            del RESET_REQUESTS[str(pk)]
            return Response({"message": "Password reset successfully."})
        return Response({"error": "No pending reset found"}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def request_quit(self, request):
        user_id = request.data.get('user_id')
        try:
            user = User.objects.get(id=user_id)
            user.quit_requested = True
            user.save()
            return Response({"message": "Quit requested."})
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'])
    def approve_quit(self, request, pk=None):
        ast = self.get_object()
        ast.quit_requested = False
        ast.assigned_doctor = None
        ast.status = 'quit'
        ast.save()
        return Response({"message": "Quit approved. Assistant unassigned."})

    @action(detail=True, methods=['post'])
    def reject_quit(self, request, pk=None):
        ast = self.get_object()
        ast.quit_requested = False
        ast.save()
        return Response({"message": "Quit request rejected."})

    @action(detail=True, methods=['post'])
    def impersonate(self, request, pk=None):
        ast = self.get_object()
        return Response({"message": "Impersonation successful", "user": UserSerializer(ast).data})

    @action(detail=False, methods=['post'])
    def replace_assistant(self, request):
        old_id = request.data.get('old_id')
        new_id = request.data.get('new_id')
        doc_id = request.data.get('doctor_id')
        
        try:
            doc = User.objects.get(id=doc_id)
            if old_id:
                try:
                    old_ast = User.objects.get(id=old_id)
                    old_ast.assigned_doctor = None
                    old_ast.quit_requested = False
                    old_ast.status = 'quit'
                    old_ast.save()
                except User.DoesNotExist:
                    pass
            if new_id:
                new_ast = User.objects.get(id=new_id)
                new_ast.assigned_doctor = doc
                new_ast.save()
            return Response({"message": "Assistant replaced successfully."})
        except User.DoesNotExist:
            return Response({"error": "Doctor not found"}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['post'])
    def request_leave(self, request):
        user_id = request.data.get('user_id')
        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')
        try:
            assistant = User.objects.get(id=user_id)
            leave_key = str(user_id)
            LEAVE_REQUESTS[leave_key] = {
                "assistant_id": assistant.id,
                "assistant_name": f"{assistant.first_name} {assistant.last_name}",
                "doctor_id": assistant.assigned_doctor_id if assistant.assigned_doctor else None,
                "start_date": start_date,
                "end_date": end_date,
                "status": "pending"
            }
            return Response({"message": "Leave request sent to your doctor."})
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['get'])
    def list_leave_requests(self, request):
        doctor_id = request.query_params.get('doctor_id')
        if doctor_id:
            result = [v for v in LEAVE_REQUESTS.values() if str(v.get('doctor_id')) == str(doctor_id)]
        else:
            result = list(LEAVE_REQUESTS.values())
        return Response(result)

    @action(detail=False, methods=['post'])
    def approve_leave(self, request):
        assistant_id = request.data.get('assistant_id')
        leave_key = str(assistant_id)
        if leave_key in LEAVE_REQUESTS:
            LEAVE_REQUESTS[leave_key]['status'] = 'approved'
            return Response({"message": "Leave approved.", "leave": LEAVE_REQUESTS[leave_key]})
        return Response({"error": "No pending leave found"}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['post'])
    def reject_leave(self, request):
        assistant_id = request.data.get('assistant_id')
        leave_key = str(assistant_id)
        if leave_key in LEAVE_REQUESTS:
            del LEAVE_REQUESTS[leave_key]
            return Response({"message": "Leave rejected."})
        return Response({"error": "No pending leave found"}, status=status.HTTP_404_NOT_FOUND)

