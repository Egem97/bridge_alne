from django.contrib import admin
from .models import UploadHistory


@admin.register(UploadHistory)
class UploadHistoryAdmin(admin.ModelAdmin):
    list_display = ('file_name', 'planilla_type', 'subsidiary_name', 'status', 'row_count', 'user', 'create')
    list_filter = ('status', 'planilla_type', 'create')
    search_fields = ('file_name', 'subsidiary_name')
    readonly_fields = ('id', 'create', 'modified')
    ordering = ('-create',)
