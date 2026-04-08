from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_view, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Roles
    path('roles/', views.RoleListView.as_view(), name='role_list'),
    path('roles/create/', views.RoleCreateView.as_view(), name='role_create'),
    path('roles/<uuid:pk>/update/', views.RoleUpdateView.as_view(), name='role_update'),
    path('roles/<uuid:pk>/delete/', views.RoleDeleteView.as_view(), name='role_delete'),

    # Categories
    path('categories/', views.CategoryListView.as_view(), name='category_list'),
    path('categories/create/', views.CategoryCreateView.as_view(), name='category_create'),
    path('categories/<uuid:pk>/update/', views.CategoryUpdateView.as_view(), name='category_update'),
    path('categories/<uuid:pk>/delete/', views.CategoryDeleteView.as_view(), name='category_delete'),

    # Companies
    path('companies/', views.CompanyListView.as_view(), name='company_list'),
    path('companies/create/', views.CompanyCreateView.as_view(), name='company_create'),
    path('companies/<uuid:pk>/update/', views.CompanyUpdateView.as_view(), name='company_update'),
    path('companies/<uuid:pk>/delete/', views.CompanyDeleteView.as_view(), name='company_delete'),

    # Profiles
    path('profiles/', views.ProfileListView.as_view(), name='profile_list'),
    path('profiles/create/', views.ProfileCreateView.as_view(), name='profile_create'),
    path('profiles/<uuid:pk>/update/', views.ProfileUpdateView.as_view(), name='profile_update'),
    path('profiles/<uuid:pk>/delete/', views.ProfileDeleteView.as_view(), name='profile_delete'),
]
