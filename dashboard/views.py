from django.shortcuts import render, redirect
from django.contrib.auth import logout, login
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from .models import Role, Category, Company, Profile
from .mixins import SuperuserRequiredMixin
from .forms import RoleForm, CategoryForm, CompanyForm, ProfileForm

# Helper Mixin to inject common context for our CRUD templates
class CrudMetaMixin:
    model_label = ""
    url_list = ""
    url_create = ""
    url_update = ""
    url_delete = ""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['model_name'] = self.model_label
        context['title'] = f"{self.model_label}s Management"
        
        # Context for List View
        context['create_url'] = reverse_lazy(self.url_create)
        context['update_url_name'] = self.url_update
        context['delete_url_name'] = self.url_delete
        
        # Context for Form/Delete View
        context['back_url'] = reverse_lazy(self.url_list)
        
        if hasattr(self, 'object') and self.object:
            context['action'] = "Edit"
        else:
            context['action'] = "Create"
            
        return context


# --- Authentication Views ---
def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Bienvenido, {user.username}!")
            return redirect('home')
        else:
            messages.error(request, "Usuario o contraseña incorrectos.")
    else:
        form = AuthenticationForm()

    return render(request, 'dashboard/login.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.success(request, "Has cerrado sesión correctamente.")
    return redirect('login')


# --- Main Dashboard ---
#@login_required
def dashboard_view(request):
    context = {
        'power_bi_url': "https://app.powerbi.com/view?r=eyJrIjoiYWUxMzRjYmUtNDllNi00YjdhLWFjMDktMDUxMGRlY2E2ODUzIiwidCI6ImFiZTdjZmIzLWEwYzgtNDVmZS04YTRmLTJjMTE3NjM4YTJhZSIsImMiOjR9", #"https://app.powerbi.com/view?r=eyJrIjoiYjVkMDljOWQtYjhiZi00MmFhLWE5ZTMtMDM1ZWNlZGI3ZWQyIiwidCI6Ijc1Yjc1NWExLTVhZTEtNDgyOS1iYjM3LWMyNDA2ZTMzOTU1MCIsImMiOjR9",
        'page_title': 'Overview'
    }
    return render(request, 'dashboard/index.html', context)


# --- Role Views ---
class RoleListView(SuperuserRequiredMixin, CrudMetaMixin, ListView):
    model = Role
    template_name = 'dashboard/crud/list.html'
    model_label = "Role"
    url_list = 'role_list'
    url_create = 'role_create'
    url_update = 'role_update'
    url_delete = 'role_delete'

class RoleCreateView(SuperuserRequiredMixin, CrudMetaMixin, CreateView):
    model = Role
    form_class = RoleForm
    template_name = 'dashboard/crud/form.html'
    success_url = reverse_lazy('role_list')
    model_label = "Role"
    url_list = 'role_list'

class RoleUpdateView(SuperuserRequiredMixin, CrudMetaMixin, UpdateView):
    model = Role
    form_class = RoleForm
    template_name = 'dashboard/crud/form.html'
    success_url = reverse_lazy('role_list')
    model_label = "Role"
    url_list = 'role_list'

class RoleDeleteView(SuperuserRequiredMixin, CrudMetaMixin, DeleteView):
    model = Role
    template_name = 'dashboard/crud/confirm_delete.html'
    success_url = reverse_lazy('role_list')
    model_label = "Role"
    url_list = 'role_list'


# --- Category Views ---
class CategoryListView(SuperuserRequiredMixin, CrudMetaMixin, ListView):
    model = Category
    template_name = 'dashboard/crud/list.html'
    model_label = "Category"
    url_list = 'category_list'
    url_create = 'category_create'
    url_update = 'category_update'
    url_delete = 'category_delete'

class CategoryCreateView(SuperuserRequiredMixin, CrudMetaMixin, CreateView):
    model = Category
    form_class = CategoryForm
    template_name = 'dashboard/crud/form.html'
    success_url = reverse_lazy('category_list')
    model_label = "Category"
    url_list = 'category_list'

class CategoryUpdateView(SuperuserRequiredMixin, CrudMetaMixin, UpdateView):
    model = Category
    form_class = CategoryForm
    template_name = 'dashboard/crud/form.html'
    success_url = reverse_lazy('category_list')
    model_label = "Category"
    url_list = 'category_list'

class CategoryDeleteView(SuperuserRequiredMixin, CrudMetaMixin, DeleteView):
    model = Category
    template_name = 'dashboard/crud/confirm_delete.html'
    success_url = reverse_lazy('category_list')
    model_label = "Category"
    url_list = 'category_list'


# --- Company Views ---
class CompanyListView(SuperuserRequiredMixin, CrudMetaMixin, ListView):
    model = Company
    template_name = 'dashboard/crud/list.html'
    model_label = "Company"
    url_list = 'company_list'
    url_create = 'company_create'
    url_update = 'company_update'
    url_delete = 'company_delete'

class CompanyCreateView(SuperuserRequiredMixin, CrudMetaMixin, CreateView):
    model = Company
    form_class = CompanyForm
    template_name = 'dashboard/crud/form.html'
    success_url = reverse_lazy('company_list')
    model_label = "Company"
    url_list = 'company_list'

class CompanyUpdateView(SuperuserRequiredMixin, CrudMetaMixin, UpdateView):
    model = Company
    form_class = CompanyForm
    template_name = 'dashboard/crud/form.html'
    success_url = reverse_lazy('company_list')
    model_label = "Company"
    url_list = 'company_list'

class CompanyDeleteView(SuperuserRequiredMixin, CrudMetaMixin, DeleteView):
    model = Company
    template_name = 'dashboard/crud/confirm_delete.html'
    success_url = reverse_lazy('company_list')
    model_label = "Company"
    url_list = 'company_list'


# --- Profile Views ---
class ProfileListView(SuperuserRequiredMixin, CrudMetaMixin, ListView):
    model = Profile
    template_name = 'dashboard/crud/list.html'
    model_label = "Profile"
    url_list = 'profile_list'
    url_create = 'profile_create'
    url_update = 'profile_update'
    url_delete = 'profile_delete'

class ProfileCreateView(SuperuserRequiredMixin, CrudMetaMixin, CreateView):
    model = Profile
    form_class = ProfileForm
    template_name = 'dashboard/crud/form.html'
    success_url = reverse_lazy('profile_list')
    model_label = "Profile"
    url_list = 'profile_list'

class ProfileUpdateView(SuperuserRequiredMixin, CrudMetaMixin, UpdateView):
    model = Profile
    form_class = ProfileForm
    template_name = 'dashboard/crud/form.html'
    success_url = reverse_lazy('profile_list')
    model_label = "Profile"
    url_list = 'profile_list'

class ProfileDeleteView(SuperuserRequiredMixin, CrudMetaMixin, DeleteView):
    model = Profile
    template_name = 'dashboard/crud/confirm_delete.html'
    success_url = reverse_lazy('profile_list')
    model_label = "Profile"
    url_list = 'profile_list'
