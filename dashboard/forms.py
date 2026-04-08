from django import forms
from .models import Role, Category, Company, Profile

class TailwindMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            current_classes = field.widget.attrs.get('class', '')
            # Base input style
            base_classes = "block w-full rounded-lg border-gray-300 py-3 px-4 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-200 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:text-sm sm:leading-6 transition duration-200 ease-in-out bg-gray-50 hover:bg-white"
            
            # Adjust for specific widgets
            if isinstance(field.widget, forms.CheckboxInput):
                tailwind_class = "h-5 w-5 rounded border-gray-300 text-indigo-600 focus:ring-indigo-600 cursor-pointer transition duration-150 ease-in-out"
            elif isinstance(field.widget, forms.Textarea):
                tailwind_class = f"{base_classes} min-h-[120px]"
            elif isinstance(field.widget, forms.Select):
                tailwind_class = f"{base_classes} pr-10" # Extra padding for arrow
            else:
                tailwind_class = base_classes
            
            field.widget.attrs['class'] = f"{current_classes} {tailwind_class}".strip()

class RoleForm(TailwindMixin, forms.ModelForm):
    class Meta:
        model = Role
        fields = '__all__'

class CategoryForm(TailwindMixin, forms.ModelForm):
    class Meta:
        model = Category
        fields = '__all__'

class CompanyForm(TailwindMixin, forms.ModelForm):
    class Meta:
        model = Company
        fields = '__all__'

class ProfileForm(TailwindMixin, forms.ModelForm):
    class Meta:
        model = Profile
        fields = '__all__'
