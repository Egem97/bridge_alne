import io
import json

import openpyxl
from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from asgiref.sync import sync_to_async

from .utils import NetSuiteClient
from .models import UploadHistory
from .services.pipeline import process_upload
from .services.payload import reorder_payload
from dashboard.decorators import role_required

# Which planilla types each role can access
ROLE_PLANILLA_MAP = {
    'Nomina Empleado': ['empleados'],
    'Nomina Obreros':  ['obreros'],
    'Owner':           ['empleados', 'obreros'],
}


def _get_allowed_types(user_role):
    return ROLE_PLANILLA_MAP.get(user_role, [])


@login_required
@role_required(allowed_roles=['Nomina Empleado', 'Nomina Obreros'])
async def upload_excel_view(request, planilla_type=None):

    def get_user_role():
        try:
            return request.user.profile.role.description
        except Exception:
            return None

    user_role = await sync_to_async(get_user_role)()
    allowed_types = _get_allowed_types(user_role)

    # Default planilla_type: first allowed type for the user
    if planilla_type is None or planilla_type not in allowed_types:
        planilla_type = allowed_types[0] if allowed_types else 'empleados'

    if request.method == 'POST':

        # ── Confirm flow ────────────────────────────────────────────────────
        if request.content_type == 'application/json':
            try:
                body = json.loads(request.body)
                if body.get('action') == 'confirm_upload':
                    upload_id = body.get('upload_id')

                    def run_confirm():
                        try:
                            history = UploadHistory.objects.get(id=upload_id)
                        except UploadHistory.DoesNotExist:
                            return {"valid": False, "error": "Registro de carga no encontrado"}

                        # Reorder keys: PostgreSQL JSONB does not preserve insertion order
                        payload = reorder_payload(history.netsuite_payload)

                        history.status = UploadHistory.Status.SENDING
                        history.save(update_fields=['status', 'modified'])

                        client = NetSuiteClient()
                        try:
                            response = client.restlet(payload)
                            history.netsuite_response = response

                            body_items = (
                                response if isinstance(response, list)
                                else response.get('body', []) if isinstance(response, dict)
                                else []
                            )
                            ns_errors = [
                                item.get('msg', 'Error desconocido')
                                for item in body_items
                                if isinstance(item, dict) and item.get('status') == 'error'
                            ]

                            if ns_errors:
                                history.status = UploadHistory.Status.ERROR
                                history.error_message = '; '.join(ns_errors)
                                history.save()
                                return {
                                    "valid": False,
                                    "error": '; '.join(ns_errors),
                                    "ns_results": [{"status": "netsuite_error", "error": msg} for msg in ns_errors],
                                }

                            history.status = UploadHistory.Status.SUCCESS
                            history.save()
                            return {
                                "valid": True,
                                "ns_results": [{"status": "netsuite_response", "data": response}],
                                "row_count": history.row_count,
                            }
                        except Exception as ns_e:
                            history.status = UploadHistory.Status.ERROR
                            history.error_message = str(ns_e)
                            history.save()
                            return {
                                "valid": False,
                                "error": str(ns_e),
                                "ns_results": [{"status": "netsuite_error", "error": str(ns_e)}],
                            }

                    result = await sync_to_async(run_confirm)()
                    return JsonResponse(result)

            except Exception as e:
                return JsonResponse(
                    {"valid": False, "error": f"Error procesando solicitud: {str(e)}"},
                    status=400
                )

        # ── Upload flow ─────────────────────────────────────────────────────
        elif request.FILES.get('file'):
            uploaded_file = request.FILES['file']
            file_content = uploaded_file.read()
            upload_planilla_type = request.POST.get('planilla_type', planilla_type)

            # Enforce role-based planilla restriction
            if upload_planilla_type not in allowed_types:
                return JsonResponse(
                    {"valid": False, "errors": [{"level": "error", "category": "auth",
                     "message": f"No tienes permiso para cargar planillas de tipo '{upload_planilla_type}'.",
                     "details": {}}]},
                    status=403
                )

            def process():
                return process_upload(file_content, upload_planilla_type)

            result = await sync_to_async(process)()

            if result.get('valid'):
                transformed_data = result.pop('_transformed_data', None)
                transformed_columns = result.pop('_transformed_columns', None)

                def save_history():
                    return UploadHistory.objects.create(
                        user=request.user,
                        file_name=uploaded_file.name,
                        file_size=uploaded_file.size,
                        planilla_type=upload_planilla_type,
                        subsidiary_name=result.get('subsidiary_name'),
                        status=UploadHistory.Status.PREVIEW,
                        row_count=result.get('row_count', 0),
                        total_debit=result.get('total_debit'),
                        total_credit=result.get('total_credit'),
                        netsuite_payload=result.get('netsuite_payload'),
                        transformed_data=transformed_data,
                        transformed_columns=transformed_columns,
                    )

                history = await sync_to_async(save_history)()
                result['upload_id'] = str(history.id)
            else:
                transformed_data = result.pop('_transformed_data', None)
                transformed_columns = result.pop('_transformed_columns', None)

                def save_error_history():
                    return UploadHistory.objects.create(
                        user=request.user,
                        file_name=uploaded_file.name,
                        file_size=uploaded_file.size,
                        planilla_type=upload_planilla_type,
                        subsidiary_name=result.get('subsidiary_name'),
                        status=UploadHistory.Status.VALIDATION_ERROR,
                        validation_errors=result.get('errors', []),
                        error_message=str(result.get('errors', [])),
                        transformed_data=transformed_data,
                        transformed_columns=transformed_columns,
                    )

                try:
                    history = await sync_to_async(save_error_history)()
                    # If we have transformed data, expose upload_id so user can download
                    if transformed_data:
                        result['upload_id'] = str(history.id)
                except Exception as db_err:
                    import logging
                    logging.getLogger(__name__).error(f"Error saving error history: {db_err}")

            return JsonResponse(result)

    return await sync_to_async(render)(
        request,
        'yw_oracle/upload.html',
        {
            'planilla_type': planilla_type,
            'allowed_types': allowed_types,
        }
    )


@login_required
@role_required(allowed_roles=['Nomina Empleado', 'Nomina Obreros'])
async def download_excel_view(request, upload_id):
    """Returns the full transformed DataFrame as an Excel file."""

    def get_user_role():
        try:
            return request.user.profile.role.description
        except Exception:
            return None

    user_role = await sync_to_async(get_user_role)()
    allowed_types = _get_allowed_types(user_role)

    def build_excel():
        try:
            history = UploadHistory.objects.get(id=upload_id)
        except UploadHistory.DoesNotExist:
            return None, "Registro no encontrado"

        if history.planilla_type not in allowed_types:
            return None, "Sin permiso para descargar este archivo"

        rows = history.transformed_data or []
        cols = history.transformed_columns or []

        if not rows or not cols:
            return None, "No hay datos transformados disponibles"

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Transformacion"

        # Header row with bold style
        header_font = openpyxl.styles.Font(bold=True)
        for col_idx, col_name in enumerate(cols, start=1):
            cell = ws.cell(row=1, column=col_idx, value=col_name)
            cell.font = header_font

        # Data rows
        for row_idx, row in enumerate(rows, start=2):
            for col_idx, col_name in enumerate(cols, start=1):
                value = row.get(col_name)
                ws.cell(row=row_idx, column=col_idx, value=value)

        # Auto-width columns
        for col in ws.columns:
            max_len = max((len(str(c.value)) if c.value is not None else 0) for c in col)
            ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 50)

        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        filename = f"transformacion_{history.file_name.rsplit('.', 1)[0]}_{history.planilla_type}.xlsx"
        return buffer, filename

    result, meta = await sync_to_async(build_excel)()

    if result is None:
        return JsonResponse({"error": meta}, status=404)

    response = HttpResponse(
        result.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{meta}"'
    return response


@login_required
@role_required(allowed_roles=['Nomina Empleado', 'Nomina Obreros'])
async def netsuite_query_view(request):
    query = request.GET.get('q', "SELECT * FROM Transaction WHERE Rownum <= 5")

    def run_query():
        client = NetSuiteClient()
        return client.execute_suiteql(query)

    try:
        data = await sync_to_async(run_query)()
        return JsonResponse(data, safe=False)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
