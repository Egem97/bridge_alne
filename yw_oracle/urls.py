from django.urls import path
from .views import upload_excel_view, netsuite_query_view, download_excel_view, transactions_view

urlpatterns = [
    path('upload_asiento/', upload_excel_view, name='upload_asiento_oracle'),
    path('upload_asiento/<str:planilla_type>/', upload_excel_view, name='upload_asiento_oracle_typed'),
    path('download_excel/<uuid:upload_id>/', download_excel_view, name='download_excel_oracle'),
    path('asientos/', netsuite_query_view, name='asientos_oracle'),
    path('transacciones/', transactions_view, name='transacciones_oracle'),
]
