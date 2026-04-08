from django.contrib.auth.mixins import AccessMixin
from django.shortcuts import redirect

class SuperuserRequiredMixin(AccessMixin):
    """Verify that the current user is a superuser."""
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_superuser:
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)

class RoleRequiredMixin(AccessMixin):
    """Verify that the current user has one of the allowed roles."""
    allowed_roles = []

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        try:
            if hasattr(request.user, 'profile') and request.user.profile.role:
                role_desc = request.user.profile.role.description
                if role_desc == 'Owner' or role_desc in self.allowed_roles:
                    return super().dispatch(request, *args, **kwargs)
        except Exception:
            pass
            
        return redirect('home')
