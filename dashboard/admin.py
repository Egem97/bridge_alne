from django.contrib import admin

# Register your models here.
from .models import Role, Category, Company, Profile

admin.site.register(Role)
admin.site.register(Category)
admin.site.register(Company)
admin.site.register(Profile)
