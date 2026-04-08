import uuid
from django.db import models
from django.contrib.auth.models import User


class UploadHistory(models.Model):
    class PlanillaType(models.TextChoices):
        EMPLEADOS = 'empleados', 'Empleados'
        OBREROS = 'obreros', 'Obreros'
        VIDA_LEY = 'vida_ley', 'Vida Ley'

    class Status(models.TextChoices):
        PREVIEW = 'preview', 'Vista Previa'
        SENDING = 'sending', 'Enviando a NetSuite'
        SUCCESS = 'success', 'Exitoso'
        ERROR = 'error', 'Error'
        VALIDATION_ERROR = 'validation_error', 'Error de Validación'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    file_name = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField(help_text="Tamaño en bytes")
    planilla_type = models.CharField(max_length=20, choices=PlanillaType.choices)
    subsidiary_name = models.CharField(max_length=150, blank=True, null=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PREVIEW)
    row_count = models.PositiveIntegerField(default=0)
    total_debit = models.DecimalField(max_digits=14, decimal_places=2, null=True)
    total_credit = models.DecimalField(max_digits=14, decimal_places=2, null=True)
    validation_errors = models.JSONField(default=list, blank=True)
    netsuite_payload = models.JSONField(null=True, blank=True)
    netsuite_response = models.JSONField(null=True, blank=True)
    transformed_data = models.JSONField(null=True, blank=True, help_text="DataFrame transformado completo para descarga")
    transformed_columns = models.JSONField(null=True, blank=True)
    error_message = models.TextField(blank=True, null=True)
    create = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-create']
        verbose_name = 'Historial de Carga'
        verbose_name_plural = 'Historial de Cargas'

    def __str__(self):
        return f"{self.file_name} - {self.get_status_display()} ({self.create})"
