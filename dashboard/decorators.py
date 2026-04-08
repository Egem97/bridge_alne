import asyncio
import logging
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from asgiref.sync import sync_to_async
from django.core.exceptions import PermissionDenied

logger = logging.getLogger(__name__)

def role_required(allowed_roles=[]):
    """
    Decorator for views that checks whether a user has a particular role,
    redirecting to the log-in page if necessary.
    Supports both sync and async views.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                logger.warning(f"Unauthenticated user tried to access {view_func.__name__}")
                return redirect('login')

            # Sync check
            try:
                if hasattr(request.user, 'profile') and request.user.profile.role:
                    role_desc = request.user.profile.role.description
                    if role_desc == 'Owner' or role_desc in allowed_roles:
                        logger.info(f"User {request.user.username} with role {role_desc} accessing {view_func.__name__}")
                        return view_func(request, *args, **kwargs)
                    else:
                        logger.warning(f"User {request.user.username} with role {role_desc} denied access to {view_func.__name__}. Required: {allowed_roles}")
                else:
                    logger.warning(f"User {request.user.username} has no profile or role")
            except Exception as e:
                logger.error(f"Error checking role for {request.user.username}: {str(e)}")

            return redirect('home')

        @wraps(view_func)
        async def _wrapped_view_async(request, *args, **kwargs):
            # Check authentication safely in async
            is_authenticated = await sync_to_async(lambda: request.user.is_authenticated)()
            if not is_authenticated:
                logger.warning(f"Unauthenticated user tried to access {view_func.__name__}")
                return redirect('login')

            try:
                # Async check for DB access
                has_permission = False

                # Use sync_to_async for DB interactions
                def check_user_role(user):
                    try:
                        if hasattr(user, 'profile') and user.profile.role:
                            role_desc = user.profile.role.description
                            has_perm = role_desc == 'Owner' or role_desc in allowed_roles
                            if has_perm:
                                logger.info(f"User {user.username} with role {role_desc} accessing {view_func.__name__}")
                            else:
                                logger.warning(f"User {user.username} with role {role_desc} denied access to {view_func.__name__}. Required: {allowed_roles}")
                            return has_perm
                        else:
                            logger.warning(f"User {user.username} has no profile or role")
                            return False
                    except Exception as e:
                        logger.error(f"Error checking role for user: {str(e)}")
                        return False

                has_permission = await sync_to_async(check_user_role)(request.user)

                if has_permission:
                    return await view_func(request, *args, **kwargs)

            except Exception as e:
                logger.error(f"Error in async role check: {str(e)}")

            # Redirect to home if permission denied
            return redirect('home')

        if asyncio.iscoroutinefunction(view_func):
            return _wrapped_view_async
        return _wrapped_view

    return decorator
