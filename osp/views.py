import csv
from datetime import datetime, timedelta
from pathlib import Path

from django.contrib.auth import logout as django_logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import Font
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from .forms import (
    ArchiveRequestForm,
    EquipmentForm,
    FirefighterForm,
    PersonnelResourceForm,
    RescueArchiveForm,
    RescueFinalReportForm,
    RescueMessageForm,
    RescueOperationForm,
    RescueStatusForm,
    RequestForm,
    ResponseForm,
    SignRequestForm,
    OSPReportForm,
    FuelUsageForm,
    VehicleInsuranceForm,
    FirefighterTestForm,
    EquipmentMaintenanceForm,
    TrainingRecordForm,
)
from .models import (
    Equipment,
    Firefighter,
    PersonnelResource,
    Request,
    RequestResponse,
    RescueAuditLog,
    RescueMessage,
    RescueOperation,
    SisAuditLog,
    Unit,
    OSPReport,
    FuelUsage,
    VehicleInsurance,
    FirefighterTest,
    EquipmentMaintenance,
    TrainingRecord,
)
from .notifications import notify_officials, notify_user


def index(request):
    units = Unit.objects.all()
    return render(request, 'osp/index.html', {'units': units})


def is_president(user):
    return (
        user.is_authenticated
        and user.groups.filter(name__in=['Prezes OSP', 'president']).exists()
    )


def is_official(user):
    return (
        user.is_authenticated
        and user.groups.filter(name__in=['Urzędnik gminy', 'official']).exists()
    )


def president_units(user):
    return Unit.objects.filter(
        Q(president=user) | Q(firefighters__created_by=user)
    ).distinct()


def can_manage_unit(user, unit):
    return is_president(user) and president_units(user).filter(pk=unit.pk).exists()


def can_manage_firefighter(user, firefighter):
    return is_official(user) or can_manage_unit(user, firefighter.unit)


def paginate(request, queryset, per_page=25):
    return Paginator(queryset, per_page).get_page(request.GET.get('page'))


def log_sis_event(unit, actor, event_type, message, req=None):
    SisAuditLog.objects.create(
        unit=unit,
        actor=actor,
        event_type=event_type,
        message=message,
        request=req,
    )


def can_access_rescue_operation(user, operation):
    if is_official(user):
        return True
    return is_president(user) and operation.created_by == user


def log_rescue_event(operation, actor, event_type, message):
    RescueAuditLog.objects.create(
        unit=operation.unit,
        operation=operation,
        actor=actor,
        event_type=event_type,
        message=message,
    )


def _font_search_dirs():
    candidates = [
        Path('C:/Windows/Fonts'),
        Path.home() / 'AppData' / 'Local' / 'Microsoft' / 'Windows' / 'Fonts',
        Path('/usr/share/fonts'),
        Path('/usr/local/share/fonts'),
        Path('/Library/Fonts'),
        Path('/System/Library/Fonts'),
        Path.home() / '.fonts',
        Path.home() / '.local' / 'share' / 'fonts',
    ]
    return [directory for directory in candidates if directory.exists()]


def _find_font_file(filenames):
    for directory in _font_search_dirs():
        for filename in filenames:
            direct = directory / filename
            if direct.is_file():
                return direct
            for candidate in directory.rglob(filename):
                if candidate.is_file():
                    return candidate
    return None


def _register_helvetica_neue_fonts():
    font_map = {
        'HelveticaNeue': (
            ['HelveticaNeueRoman.otf', 'HelveticaNeue.ttf', 'Arial.ttf', 'LiberationSans-Regular.ttf', 'DejaVuSans.ttf'],
            'Helvetica',
        ),
        'HelveticaNeue-Bold': (
            ['HelveticaNeueBold.otf', 'HelveticaNeue-Bold.ttf', 'Arial Bold.ttf', 'LiberationSans-Bold.ttf', 'DejaVuSans-Bold.ttf'],
            'Helvetica-Bold',
        ),
        'HelveticaNeue-Italic': (
            ['HelveticaNeueItalic.ttf', 'Arial Italic.ttf', 'LiberationSans-Italic.ttf', 'DejaVuSans-Oblique.ttf'],
            'Helvetica-Oblique',
        ),
        'HelveticaNeue-BoldItalic': (
            ['HelveticaNeueBoldItalic.otf', 'Arial Bold Italic.ttf', 'LiberationSans-BoldItalic.ttf', 'DejaVuSans-BoldOblique.ttf'],
            'Helvetica-BoldOblique',
        ),
    }

    for font_name, (filenames, base_font) in font_map.items():
        if font_name in pdfmetrics.getRegisteredFontNames():
            continue

        font_path = _find_font_file(filenames)
        if font_path and font_path.suffix.lower() in {'.ttf', '.ttc'}:
            try:
                pdfmetrics.registerFont(TTFont(font_name, str(font_path)))
                continue
            except Exception:
                pass

        pdfmetrics.registerFont(Font(font_name, base_font, 'WinAnsiEncoding'))


def _pdf_font_name(weight='regular', italic=False):
    _register_helvetica_neue_fonts()

    if weight == 'bold' and italic:
        return 'HelveticaNeue-BoldItalic' if 'HelveticaNeue-BoldItalic' in pdfmetrics.getRegisteredFontNames() else 'Helvetica-BoldOblique'
    if weight == 'bold':
        return 'HelveticaNeue-Bold' if 'HelveticaNeue-Bold' in pdfmetrics.getRegisteredFontNames() else 'Helvetica-Bold'
    if italic:
        return 'HelveticaNeue-Italic' if 'HelveticaNeue-Italic' in pdfmetrics.getRegisteredFontNames() else 'Helvetica-Oblique'
    return 'HelveticaNeue' if 'HelveticaNeue' in pdfmetrics.getRegisteredFontNames() else 'Helvetica'


def _set_pdf_fonts(text_object):
    text_object.setFont(_pdf_font_name('bold'), 14)
    text_object.textLine('')
    text_object.setFont(_pdf_font_name(), 10)


@login_required
def firefighter_list(request, unit_pk=None):
    user = request.user
    context = {'is_president': is_president(user)}

    if is_official(user):
        if unit_pk:
            unit = get_object_or_404(Unit, pk=unit_pk)
            firefighters = Firefighter.objects.filter(unit=unit)
            context['unit'] = unit
        else:
            firefighters = Firefighter.objects.all()
    elif is_president(user):
        units = president_units(user)
        context['units'] = units
        if unit_pk:
            unit = get_object_or_404(units, pk=unit_pk)
            firefighters = Firefighter.objects.filter(unit=unit)
            context['unit'] = unit
        else:
            firefighters = Firefighter.objects.filter(unit__in=units)
    else:
        return HttpResponseForbidden('Brak dostępu')

    query = request.GET.get('q', '').strip()
    if query:
        firefighters = firefighters.filter(
            Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(pesel__icontains=query)
            | Q(email__icontains=query)
            | Q(phone__icontains=query)
        )
    page_obj = paginate(request, firefighters.order_by('last_name', 'first_name'))
    context['firefighters'] = page_obj
    context['page_obj'] = page_obj
    context['q'] = query
    return render(request, 'osp/firefighter_list.html', context)


@login_required
def equipment_list(request, unit_pk=None):
    user = request.user
    context = {'is_president': is_president(user)}

    if is_official(user):
        if unit_pk:
            unit = get_object_or_404(Unit, pk=unit_pk)
            equipment = Equipment.objects.filter(unit=unit)
            context['unit'] = unit
        else:
            equipment = Equipment.objects.all()
    elif is_president(user):
        units = president_units(user)
        context['units'] = units
        if unit_pk:
            unit = get_object_or_404(units, pk=unit_pk)
            equipment = Equipment.objects.filter(unit=unit)
            context['unit'] = unit
        else:
            equipment = Equipment.objects.filter(unit__in=units)
    else:
        return HttpResponseForbidden('Brak dostępu')

    query = request.GET.get('q', '').strip()
    if query:
        equipment = equipment.filter(
            Q(name__icontains=query)
            | Q(category__icontains=query)
            | Q(inventory_number__icontains=query)
        )
    page_obj = paginate(request, equipment.order_by('name'))
    context['equipment_list'] = page_obj
    context['page_obj'] = page_obj
    context['q'] = query
    return render(request, 'osp/equipment_list.html', context)


@login_required
def equipment_create(request, unit_pk):
    unit = get_object_or_404(Unit, pk=unit_pk)
    if not can_manage_unit(request.user, unit):
        return HttpResponseForbidden('Tylko prezes tej jednostki może dodać sprzęt')

    if request.method == 'POST':
        form = EquipmentForm(request.POST)
        if form.is_valid():
            equipment = form.save(commit=False)
            equipment.unit = unit
            equipment.created_by = request.user
            equipment.save()
            log_sis_event(
                unit=unit,
                actor=request.user,
                event_type=SisAuditLog.EVENT_RESOURCE_UPDATE,
                message=f'Utworzono zasób sprzętowy: {equipment.name} ({equipment.inventory_number}).',
            )
            return redirect('osp:equipment_list_unit', unit_pk=unit.pk)
    else:
        form = EquipmentForm()

    return render(request, 'osp/equipment_form.html', {'form': form, 'unit': unit})


@login_required
def personnel_list(request, unit_pk=None):
    user = request.user
    context = {'is_president': is_president(user)}
    
    if is_official(user):
        if unit_pk:
            unit = get_object_or_404(Unit, pk=unit_pk)
            personnel = PersonnelResource.objects.filter(unit=unit)
            context['unit'] = unit
        else:
            personnel = PersonnelResource.objects.all()
    elif is_president(user):
        units = president_units(user)
        context['units'] = units
        if unit_pk:
            unit = get_object_or_404(units, pk=unit_pk)
            personnel = PersonnelResource.objects.filter(unit=unit)
            context['unit'] = unit
        else:
            personnel = PersonnelResource.objects.filter(unit__in=units)
    else:
        return HttpResponseForbidden('Brak dostępu')

    query = request.GET.get('q', '').strip()
    if query:
        personnel = personnel.filter(
            Q(role_name__icontains=query)
            | Q(qualifications__icontains=query)
            | Q(firefighter__first_name__icontains=query)
            | Q(firefighter__last_name__icontains=query)
        )
    page_obj = paginate(request, personnel.order_by('role_name'))
    context['personnel_list'] = page_obj
    context['page_obj'] = page_obj
    context['q'] = query
    return render(request, 'osp/personnel_list.html', context)


@login_required
def personnel_create(request, unit_pk):
    unit = get_object_or_404(Unit, pk=unit_pk)
    if not can_manage_unit(request.user, unit):
        return HttpResponseForbidden('Tylko prezes tej jednostki może dodać siły i środki osobowe')

    if request.method == 'POST':
        form = PersonnelResourceForm(request.POST, unit=unit)
        if form.is_valid():
            personnel = form.save(commit=False)
            personnel.unit = unit
            personnel.save()
            log_sis_event(
                unit=unit,
                actor=request.user,
                event_type=SisAuditLog.EVENT_RESOURCE_UPDATE,
                message=f'Utworzono zasób osobowy: {personnel.role_name}.',
            )
            return redirect('osp:personnel_list_unit', unit_pk=unit.pk)
    else:
        form = PersonnelResourceForm(unit=unit)

    return render(request, 'osp/personnel_form.html', {'form': form, 'unit': unit})


@login_required
def firefighter_create(request, unit_pk):
    unit = get_object_or_404(Unit, pk=unit_pk)
    if not can_manage_unit(request.user, unit):
        return HttpResponseForbidden('Tylko prezes tej jednostki może dodać strażaka')

    if request.method == 'POST':
        form = FirefighterForm(request.POST)
        if form.is_valid():
            ff = form.save(commit=False)
            ff.unit = unit
            ff.created_by = request.user
            ff.save()
            return redirect('osp:request_list')
    else:
        form = FirefighterForm()
    return render(request, 'osp/firefighter_form.html', {'form': form, 'unit': unit})


@login_required
def firefighter_edit(request, pk):
    firefighter = get_object_or_404(Firefighter, pk=pk)
    user = request.user
    if is_president(user):
        if firefighter.unit not in president_units(user):
            return HttpResponseForbidden('Brak dostępu do edycji tego strażaka')
        can_edit = True
    elif is_official(user):
        can_edit = False
    else:
        return HttpResponseForbidden('Brak dostępu')

    if request.method == 'POST' and can_edit:
        form = FirefighterForm(request.POST, instance=firefighter)
        if form.is_valid():
            form.save()
            return redirect('osp:firefighter_list_unit', unit_pk=firefighter.unit.pk)
    else:
        form = FirefighterForm(instance=firefighter)
        if not can_edit:
            for field in form.fields.values():
                field.disabled = True
    return render(request, 'osp/firefighter_edit.html', {'form': form, 'firefighter': firefighter, 'can_edit': can_edit})


@login_required
def request_create(request, unit_pk):
    unit = get_object_or_404(Unit, pk=unit_pk)
    if not can_manage_unit(request.user, unit):
        return HttpResponseForbidden('Tylko prezes tej jednostki może tworzyć wnioski')

    if request.method == 'POST':
        form = RequestForm(request.POST, unit=unit)
        if form.is_valid():
            req = form.save(commit=False)
            req.unit = unit
            req.created_by = request.user
            if request.POST.get('submit') == '1':
                req.status = Request.STATUS_SUBMITTED
            req.save()
            form.save_m2m()
            log_sis_event(
                unit=unit,
                actor=request.user,
                event_type=SisAuditLog.EVENT_REQUEST_FLOW,
                message=f'Utworzono wniosek KSRG: {req.title} (status: {req.get_status_display()}).',
                req=req,
            )
            return redirect('osp:request_list')
    else:
        form = RequestForm(unit=unit)
    return render(request, 'osp/request_form.html', {'form': form, 'unit': unit})


@login_required
def request_list(request):
    if is_official(request.user):
        qs = Request.objects.filter(
            status__in=[Request.STATUS_SUBMITTED, Request.STATUS_ACCEPTED, Request.STATUS_REJECTED]
        )
    elif is_president(request.user):
        qs = Request.objects.filter(created_by=request.user)
    else:
        return HttpResponseForbidden('Brak uprawnień')

    status = request.GET.get('status', '').strip()
    if status in dict(Request.STATUS_CHOICES):
        qs = qs.filter(status=status)
    query = request.GET.get('q', '').strip()
    if query:
        qs = qs.filter(Q(title__icontains=query) | Q(description__icontains=query))
    page_obj = paginate(request, qs.order_by('-updated_at'))
    return render(request, 'osp/request_list.html', {
        'requests': page_obj,
        'page_obj': page_obj,
        'q': query,
        'status': status,
        'status_choices': Request.STATUS_CHOICES,
    })


@login_required
def request_detail(request, pk):
    req = get_object_or_404(Request.objects.prefetch_related('responses', 'equipment_resources', 'personnel_resources'), pk=pk)
    user = request.user
    user_is_president = is_president(user)
    user_is_official = is_official(user)

    if user_is_president and req.created_by == user:
        pass
    elif user_is_official:
        pass
    else:
        return HttpResponseForbidden('Brak uprawnień do podglądu tego wniosku')

    can_sign = (
        user_is_president
        and req.created_by == user
        and req.status in [Request.STATUS_ACCEPTED, Request.STATUS_REJECTED]
        and not req.signed_by
    )
    can_archive = (
        user_is_official
        and req.status in [Request.STATUS_ACCEPTED, Request.STATUS_REJECTED]
        and req.signed_by is not None
        and req.archived_at is None
    )

    context = {
        'request_obj': req,
        'is_president': user_is_president,
        'is_official': user_is_official,
        'can_sign': can_sign,
        'can_archive': can_archive,
        'can_respond': user_is_official and req.status == Request.STATUS_SUBMITTED,
    }
    return render(request, 'osp/request_detail.html', context)


@login_required
def request_sign(request, pk):
    req = get_object_or_404(Request, pk=pk)
    if not is_president(request.user) or req.created_by != request.user:
        return HttpResponseForbidden('Tylko autor będący prezesem może podpisać wniosek')
    if req.signed_by:
        return redirect('osp:request_detail', pk=pk)
    if req.status not in [Request.STATUS_ACCEPTED, Request.STATUS_REJECTED]:
        return HttpResponseBadRequest('Podpis jest dostępny dopiero po decyzji urzędnika')

    if request.method == 'POST':
        form = SignRequestForm(request.POST)
        if form.is_valid():
            req.signed_by = request.user
            req.signed_at = timezone.now()
            req.save(update_fields=['signed_by', 'signed_at', 'updated_at'])
            log_sis_event(
                unit=req.unit,
                actor=request.user,
                event_type=SisAuditLog.EVENT_REQUEST_FLOW,
                message=f'Wniosek {req.pk} został podpisany przez prezesa.',
                req=req,
            )
            return redirect('osp:request_detail', pk=pk)
    else:
        form = SignRequestForm()
    return render(request, 'osp/request_sign.html', {'form': form, 'request_obj': req})


@login_required
def request_archive(request, pk):
    req = get_object_or_404(Request, pk=pk)
    if not is_official(request.user):
        return HttpResponseForbidden('Tylko urzędnik może archiwizować wniosek')
    if req.status not in [Request.STATUS_ACCEPTED, Request.STATUS_REJECTED]:
        return HttpResponseBadRequest('Archiwizować można tylko wniosek po decyzji')
    if not req.signed_by:
        return HttpResponseBadRequest('Wniosek musi zostać podpisany przed archiwizacją')
    if req.archived_at:
        return redirect('osp:request_detail', pk=pk)

    if request.method == 'POST':
        form = ArchiveRequestForm(request.POST)
        if form.is_valid():
            req.status = Request.STATUS_ARCHIVED
            req.archived_by = request.user
            req.archived_at = timezone.now()
            req.save(update_fields=['status', 'archived_by', 'archived_at', 'updated_at'])
            log_sis_event(
                unit=req.unit,
                actor=request.user,
                event_type=SisAuditLog.EVENT_REQUEST_FLOW,
                message=f'Wniosek {req.pk} został zarchiwizowany.',
                req=req,
            )
            return redirect('osp:request_detail', pk=pk)
    else:
        form = ArchiveRequestForm()

    return render(request, 'osp/request_sign.html', {'form': form, 'request_obj': req, 'archive_mode': True})


def logout_view(request):
    if request.method in ['POST', 'GET']:
        django_logout(request)
        return render(request, 'registration/logout.html')


@login_required
def request_pdf(request, pk):
    req = get_object_or_404(
        Request.objects.prefetch_related('responses', 'equipment_resources', 'personnel_resources'),
        pk=pk,
    )
    user = request.user
    user_is_president = is_president(user)
    user_is_official = is_official(user)

    if not ((user_is_president and req.created_by == user) or user_is_official):
        return HttpResponseForbidden('Brak uprawnień do pobrania PDF tego wniosku')

    filename = f"wniosek-{req.pk}.pdf"
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    pdf = canvas.Canvas(response, pagesize=A4)
    _, page_height = A4
    text = pdf.beginText(40, page_height - 50)
    text.setFont(_pdf_font_name('bold'), 14)
    text.textLine('Wniosek OSP / KSRG')
    text.setFont(_pdf_font_name(), 10)
    text.textLine('')

    lines = [
        f'ID: {req.pk}',
        f'Tytul: {req.title}',
        f'Jednostka: {req.unit.name}',
        f'Status: {req.get_status_display()}',
        f'Utworzony przez: {req.created_by or "-"}',
        f'Data utworzenia: {req.created_at.strftime("%Y-%m-%d %H:%M")}',
        '',
        'Opis:',
    ]

    for line in lines:
        text.textLine(line)

    for paragraph_line in req.description.splitlines() or ['-']:
        current_line = paragraph_line
        while len(current_line) > 110:
            text.textLine(current_line[:110])
            current_line = current_line[110:]
        text.textLine(current_line)

    text.textLine('')
    text.textLine('Zasoby sprzetowe SiS:')
    equipment_resources = req.equipment_resources.all().order_by('name')
    if equipment_resources.exists():
        for equipment in equipment_resources:
            text.textLine(f'- {equipment.name} ({equipment.inventory_number}) [{equipment.get_condition_display()}]')
    else:
        text.textLine('- Brak')

    text.textLine('')
    text.textLine('Sily i srodki osobowe SiS:')
    personnel_resources = req.personnel_resources.all().order_by('role_name')
    if personnel_resources.exists():
        for personnel in personnel_resources:
            person_label = personnel.firefighter or '-'
            text.textLine(f'- {personnel.role_name} | {person_label} [{personnel.get_readiness_display()}]')
    else:
        text.textLine('- Brak')

    text.textLine('')
    text.textLine('Podpis:')
    if req.signed_by and req.signed_at:
        text.textLine(f'Podpisany przez: {req.signed_by}')
        text.textLine(f'Data podpisu: {req.signed_at.strftime("%Y-%m-%d %H:%M")}')
    else:
        text.textLine('Brak podpisu')

    text.textLine('')
    text.textLine('Archiwizacja:')
    if req.archived_by and req.archived_at:
        text.textLine(f'Zarchiwizowany przez: {req.archived_by}')
        text.textLine(f'Data archiwizacji: {req.archived_at.strftime("%Y-%m-%d %H:%M")}')
    else:
        text.textLine('Brak archiwizacji')

    text.textLine('')
    text.textLine('Odpowiedzi:')
    responses = req.responses.select_related('responder').order_by('created_at')
    if responses.exists():
        for resp in responses:
            summary = f'- {resp.created_at.strftime("%Y-%m-%d %H:%M")} | {resp.get_action_display()} | {resp.responder or "-"}'
            text.textLine(summary[:120])
            if resp.message:
                message_line = f'  {resp.message}'
                while len(message_line) > 118:
                    text.textLine(message_line[:118])
                    message_line = f'  {message_line[118:]}'
                text.textLine(message_line)
    else:
        text.textLine('Brak odpowiedzi')

    pdf.drawText(text)
    pdf.showPage()
    pdf.save()
    return response


@login_required
def request_respond(request, pk):
    req = get_object_or_404(Request, pk=pk)
    if not is_official(request.user):
        return HttpResponseForbidden('Tylko urzędnik może odpowiedzieć na wniosek')

    if req.status != Request.STATUS_SUBMITTED:
        return HttpResponseBadRequest('Wniosek nie jest na etapie decyzji urzędnika')

    if request.method == 'POST':
        form = ResponseForm(request.POST)
        if form.is_valid():
            resp = form.save(commit=False)
            resp.request = req
            resp.responder = request.user
            resp.save()
            if resp.action == RequestResponse.ACTION_ACCEPT:
                req.status = Request.STATUS_ACCEPTED
            elif resp.action == RequestResponse.ACTION_REJECT:
                req.status = Request.STATUS_REJECTED
            req.save(update_fields=['status', 'updated_at'])
            log_sis_event(
                unit=req.unit,
                actor=request.user,
                event_type=SisAuditLog.EVENT_REQUEST_FLOW,
                message=f'Podjeto decyzje urzednika: {resp.get_action_display()} dla wniosku {req.pk}.',
                req=req,
            )
            return redirect('osp:request_detail', pk=pk)
    else:
        form = ResponseForm()
    return render(request, 'osp/request_respond.html', {'form': form, 'request_obj': req})


@login_required
def rescue_operation_list(request):
    context = {'is_president': is_president(request.user)}
    
    if is_official(request.user):
        operations = RescueOperation.objects.select_related('unit', 'created_by')
    elif is_president(request.user):
        operations = RescueOperation.objects.select_related('unit', 'created_by').filter(created_by=request.user)
        context['units'] = president_units(request.user)
    else:
        return HttpResponseForbidden('Brak uprawnień')

    status = request.GET.get('status', '').strip()
    if status in dict(RescueOperation.STATUS_CHOICES):
        operations = operations.filter(status=status)
    query = request.GET.get('q', '').strip()
    if query:
        operations = operations.filter(
            Q(title__icontains=query)
            | Q(location__icontains=query)
            | Q(incident_type__icontains=query)
        )
    page_obj = paginate(request, operations.order_by('-updated_at'))
    context['operations'] = page_obj
    context['page_obj'] = page_obj
    context['q'] = query
    context['status'] = status
    context['status_choices'] = RescueOperation.STATUS_CHOICES
    return render(request, 'osp/rescue_operation_list.html', context)


@login_required
def rescue_operation_create(request, unit_pk):
    unit = get_object_or_404(Unit, pk=unit_pk)
    if not can_manage_unit(request.user, unit):
        return HttpResponseForbidden('Tylko prezes tej jednostki może zarejestrować działanie ratownicze')

    if request.method == 'POST':
        form = RescueOperationForm(request.POST)
        if form.is_valid():
            operation = form.save(commit=False)
            operation.unit = unit
            operation.created_by = request.user
            operation.status = RescueOperation.STATUS_REGISTERED
            operation.save()
            log_rescue_event(
                operation=operation,
                actor=request.user,
                event_type=RescueAuditLog.EVENT_FLOW,
                message='Zarejestrowano działanie ratownicze.',
            )
            return redirect('osp:rescue_operation_detail', pk=operation.pk)
    else:
        form = RescueOperationForm()

    return render(request, 'osp/rescue_operation_form.html', {'form': form, 'unit': unit})


@login_required
def rescue_operation_detail(request, pk):
    operation = get_object_or_404(
        RescueOperation.objects.select_related('unit', 'created_by', 'archived_by').prefetch_related('messages__author', 'audit_logs'),
        pk=pk,
    )
    if not can_access_rescue_operation(request.user, operation):
        return HttpResponseForbidden('Brak uprawnień do podglądu działania')

    can_manage = is_official(request.user)
    context = {
        'operation': operation,
        'messages': operation.messages.all(),
        'audit_logs': operation.audit_logs.all()[:20],
        'can_manage': can_manage,
        'can_archive': is_official(request.user) and operation.status == RescueOperation.STATUS_CLOSED and operation.archived_at is None,
        'message_form': RescueMessageForm(),
        'status_form': RescueStatusForm(initial={'status': operation.status, 'action_started_at': operation.action_started_at}),
        'final_report_form': RescueFinalReportForm(instance=operation),
        'archive_form': RescueArchiveForm(),
    }
    return render(request, 'osp/rescue_operation_detail.html', context)


@login_required
def rescue_operation_add_message(request, pk):
    operation = get_object_or_404(RescueOperation, pk=pk)
    if not can_access_rescue_operation(request.user, operation):
        return HttpResponseForbidden('Brak uprawnień do dodawania meldunków')
    if request.method != 'POST':
        return HttpResponseBadRequest('Nieprawidłowa metoda')

    form = RescueMessageForm(request.POST)
    if form.is_valid():
        rescue_message = form.save(commit=False)
        rescue_message.operation = operation
        rescue_message.author = request.user
        rescue_message.sender_type = RescueMessage.SENDER_PSP if is_official(request.user) else RescueMessage.SENDER_OSP
        rescue_message.save()
        log_rescue_event(
            operation=operation,
            actor=request.user,
            event_type=RescueAuditLog.EVENT_FLOW,
            message=f'Dodano meldunek ({rescue_message.get_kind_display()}) po stronie {rescue_message.sender_type}.',
        )
    return redirect('osp:rescue_operation_detail', pk=pk)


@login_required
def rescue_operation_update_status(request, pk):
    operation = get_object_or_404(RescueOperation, pk=pk)
    if not is_official(request.user):
        return HttpResponseForbidden('Status może zmieniać wyłącznie urzędnik')
    if operation.status in [RescueOperation.STATUS_CLOSED, RescueOperation.STATUS_ARCHIVED]:
        return HttpResponseBadRequest('Działanie jest już zamknięte lub zarchiwizowane')
    if request.method != 'POST':
        return HttpResponseBadRequest('Nieprawidłowa metoda')

    form = RescueStatusForm(request.POST)
    if form.is_valid():
        operation.status = form.cleaned_data['status']
        action_started_at = form.cleaned_data['action_started_at']
        if action_started_at:
            operation.action_started_at = action_started_at
        operation.save(update_fields=['status', 'action_started_at', 'updated_at'])
        log_rescue_event(
            operation=operation,
            actor=request.user,
            event_type=RescueAuditLog.EVENT_FLOW,
            message=f'Zmieniono status działania na: {operation.get_status_display()}.',
        )
    return redirect('osp:rescue_operation_detail', pk=pk)


@login_required
def rescue_operation_finalize(request, pk):
    operation = get_object_or_404(RescueOperation, pk=pk)
    if not is_official(request.user):
        return HttpResponseForbidden('Raport końcowy może zatwierdzić wyłącznie urzędnik')
    if operation.status == RescueOperation.STATUS_ARCHIVED:
        return HttpResponseBadRequest('Zarchiwizowane działanie nie może zostać ponownie zamknięte')
    if request.method != 'POST':
        return HttpResponseBadRequest('Nieprawidłowa metoda')

    form = RescueFinalReportForm(request.POST, instance=operation)
    if form.is_valid():
        operation = form.save(commit=False)
        operation.status = RescueOperation.STATUS_CLOSED
        if not operation.closed_at:
            operation.closed_at = timezone.now()
        operation.save(update_fields=['final_report', 'closed_at', 'status', 'updated_at'])
        log_rescue_event(
            operation=operation,
            actor=request.user,
            event_type=RescueAuditLog.EVENT_FLOW,
            message='Zamknięto działanie i zatwierdzono raport końcowy.',
        )
    return redirect('osp:rescue_operation_detail', pk=pk)


@login_required
def rescue_operation_archive(request, pk):
    operation = get_object_or_404(RescueOperation, pk=pk)
    if not is_official(request.user):
        return HttpResponseForbidden('Tylko urzędnik może archiwizować działania')
    if operation.status != RescueOperation.STATUS_CLOSED:
        return HttpResponseBadRequest('Archiwizować można tylko działanie zamknięte raportem końcowym')
    if request.method != 'POST':
        return HttpResponseBadRequest('Nieprawidłowa metoda')

    form = RescueArchiveForm(request.POST)
    if form.is_valid():
        operation.status = RescueOperation.STATUS_ARCHIVED
        operation.archived_by = request.user
        operation.archived_at = timezone.now()
        operation.save(update_fields=['status', 'archived_by', 'archived_at', 'updated_at'])
        log_rescue_event(
            operation=operation,
            actor=request.user,
            event_type=RescueAuditLog.EVENT_FLOW,
            message='Zarchiwizowano działanie ratownicze.',
        )
    return redirect('osp:rescue_operation_detail', pk=pk)


@login_required
def rescue_operation_report_csv(request, pk):
    operation = get_object_or_404(RescueOperation.objects.select_related('unit', 'created_by'), pk=pk)
    if not can_access_rescue_operation(request.user, operation):
        return HttpResponseForbidden('Brak uprawnień do raportu')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="dzialanie-{operation.pk}.csv"'
    writer = csv.writer(response)
    writer.writerow(['ID', operation.pk])
    writer.writerow(['Tytuł', operation.title])
    writer.writerow(['Jednostka', operation.unit.name])
    writer.writerow(['Typ zdarzenia', operation.incident_type])
    writer.writerow(['Lokalizacja', operation.location])
    writer.writerow(['Priorytet', operation.get_priority_display()])
    writer.writerow(['Status', operation.get_status_display()])
    writer.writerow(['Data zgłoszenia', operation.occurred_at.strftime('%Y-%m-%d %H:%M')])
    writer.writerow(['Start działań', operation.action_started_at.strftime('%Y-%m-%d %H:%M') if operation.action_started_at else '-'])
    writer.writerow(['Zakończenie', operation.closed_at.strftime('%Y-%m-%d %H:%M') if operation.closed_at else '-'])
    writer.writerow([])
    writer.writerow(['Raport końcowy'])
    writer.writerow([operation.final_report or '-'])
    writer.writerow([])
    writer.writerow(['Meldunki'])
    writer.writerow(['Data', 'Nadawca', 'Typ', 'Autor', 'Treść'])
    for msg in operation.messages.select_related('author').all():
        writer.writerow([
            msg.created_at.strftime('%Y-%m-%d %H:%M'),
            msg.get_sender_type_display(),
            msg.get_kind_display(),
            str(msg.author or '-'),
            msg.message,
        ])

    log_rescue_event(
        operation=operation,
        actor=request.user,
        event_type=RescueAuditLog.EVENT_REPORTING,
        message='Wygenerowano raport operacyjny CSV.',
    )
    return response


@login_required
def rescue_operation_report_pdf(request, pk):
    operation = get_object_or_404(RescueOperation.objects.select_related('unit', 'created_by'), pk=pk)
    if not can_access_rescue_operation(request.user, operation):
        return HttpResponseForbidden('Brak uprawnień do raportu')

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="dzialanie-{operation.pk}.pdf"'
    pdf = canvas.Canvas(response, pagesize=A4)
    _, page_height = A4
    text = pdf.beginText(40, page_height - 50)
    text.setFont(_pdf_font_name('bold'), 14)
    text.textLine('Raport operacyjny działania ratowniczego')
    text.setFont(_pdf_font_name(), 10)
    text.textLine('')

    lines = [
        f'ID: {operation.pk}',
        f'Tytuł: {operation.title}',
        f'Jednostka: {operation.unit.name}',
        f'Typ zdarzenia: {operation.incident_type}',
        f'Lokalizacja: {operation.location}',
        f'Priorytet: {operation.get_priority_display()}',
        f'Status: {operation.get_status_display()}',
        f'Data zgłoszenia: {operation.occurred_at.strftime("%Y-%m-%d %H:%M")}',
        f'Start działań: {operation.action_started_at.strftime("%Y-%m-%d %H:%M") if operation.action_started_at else "-"}',
        f'Zakończenie: {operation.closed_at.strftime("%Y-%m-%d %H:%M") if operation.closed_at else "-"}',
        '',
        'Opis:',
    ]
    for line in lines:
        text.textLine(line)

    for raw_line in (operation.description.splitlines() or ['-']):
        current_line = raw_line
        while len(current_line) > 110:
            text.textLine(current_line[:110])
            current_line = current_line[110:]
        text.textLine(current_line)

    text.textLine('')
    text.textLine('Raport końcowy:')
    for raw_line in (operation.final_report.splitlines() or ['-']):
        current_line = raw_line
        while len(current_line) > 110:
            text.textLine(current_line[:110])
            current_line = current_line[110:]
        text.textLine(current_line)

    text.textLine('')
    text.textLine('Meldunki OSP/PSP:')
    messages = operation.messages.select_related('author').all()
    if messages.exists():
        for msg in messages:
            line = f'- {msg.created_at.strftime("%Y-%m-%d %H:%M")} | {msg.sender_type} | {msg.get_kind_display()} | {msg.author or "-"}'
            text.textLine(line[:115])
            message_text = msg.message
            while len(message_text) > 108:
                text.textLine(f'  {message_text[:108]}')
                message_text = message_text[108:]
            text.textLine(f'  {message_text}')
    else:
        text.textLine('- Brak meldunków')

    pdf.drawText(text)
    pdf.showPage()
    pdf.save()

    log_rescue_event(
        operation=operation,
        actor=request.user,
        event_type=RescueAuditLog.EVENT_REPORTING,
        message='Wygenerowano raport operacyjny PDF.',
    )
    return response


def _get_year_month(request):
    now = timezone.localtime()
    try:
        year = int(request.GET.get('year', now.year))
        month = int(request.GET.get('month', now.month))
    except (TypeError, ValueError):
        return None, None, HttpResponseBadRequest('Nieprawidłowy rok lub miesiąc')
    if not (2000 <= year <= 2100) or not (1 <= month <= 12):
        return None, None, HttpResponseBadRequest('Nieprawidłowy rok lub miesiąc')
    return year, month, None


def _monthly_rescue_queryset(user, year, month):
    start = timezone.datetime(year=year, month=month, day=1, tzinfo=timezone.get_current_timezone())
    if month == 12:
        end = timezone.datetime(year=year + 1, month=1, day=1, tzinfo=timezone.get_current_timezone())
    else:
        end = timezone.datetime(year=year, month=month + 1, day=1, tzinfo=timezone.get_current_timezone())

    queryset = RescueOperation.objects.select_related('unit', 'created_by').filter(occurred_at__gte=start, occurred_at__lt=end)
    if is_official(user):
        return queryset
    if is_president(user):
        return queryset.filter(created_by=user)
    return RescueOperation.objects.none()


def _durations_minutes(operation):
    reaction_minutes = None
    close_minutes = None
    if operation.action_started_at:
        reaction_minutes = int((operation.action_started_at - operation.occurred_at).total_seconds() // 60)
    if operation.closed_at:
        close_minutes = int((operation.closed_at - operation.occurred_at).total_seconds() // 60)
    return reaction_minutes, close_minutes


@login_required
def rescue_monthly_report(request):
    if not (is_official(request.user) or is_president(request.user)):
        return HttpResponseForbidden('Brak uprawnień')

    year, month, error = _get_year_month(request)
    if error:
        return error
    operations = list(_monthly_rescue_queryset(request.user, year, month).order_by('-occurred_at'))

    reaction_values = []
    close_values = []
    for operation in operations:
        reaction_minutes, close_minutes = _durations_minutes(operation)
        if reaction_minutes is not None:
            reaction_values.append(reaction_minutes)
        if close_minutes is not None:
            close_values.append(close_minutes)

    stats = {
        'total': len(operations),
        'registered': sum(1 for op in operations if op.status == RescueOperation.STATUS_REGISTERED),
        'in_progress': sum(1 for op in operations if op.status == RescueOperation.STATUS_IN_PROGRESS),
        'closed': sum(1 for op in operations if op.status == RescueOperation.STATUS_CLOSED),
        'archived': sum(1 for op in operations if op.status == RescueOperation.STATUS_ARCHIVED),
        'avg_reaction_minutes': int(sum(reaction_values) / len(reaction_values)) if reaction_values else None,
        'avg_close_minutes': int(sum(close_values) / len(close_values)) if close_values else None,
    }

    return render(
        request,
        'osp/rescue_monthly_report.html',
        {
            'operations': operations,
            'year': year,
            'month': month,
            'stats': stats,
        },
    )


@login_required
def rescue_monthly_report_csv(request):
    if not (is_official(request.user) or is_president(request.user)):
        return HttpResponseForbidden('Brak uprawnień')

    year, month, error = _get_year_month(request)
    if error:
        return error
    operations = _monthly_rescue_queryset(request.user, year, month).order_by('-occurred_at')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="raport-miesieczny-{year}-{month:02d}.csv"'
    writer = csv.writer(response)
    writer.writerow(['Raport miesięczny działań ratowniczych', f'{year}-{month:02d}'])
    writer.writerow([])
    writer.writerow(['ID', 'Tytuł', 'Jednostka', 'Status', 'Priorytet', 'Data zgłoszenia', 'Czas reakcji (min)', 'Czas zamknięcia (min)'])
    for operation in operations:
        reaction_minutes, close_minutes = _durations_minutes(operation)
        writer.writerow([
            operation.pk,
            operation.title,
            operation.unit.name,
            operation.get_status_display(),
            operation.get_priority_display(),
            operation.occurred_at.strftime('%Y-%m-%d %H:%M'),
            reaction_minutes if reaction_minutes is not None else '-',
            close_minutes if close_minutes is not None else '-',
        ])
    return response


@login_required
def rescue_monthly_report_pdf(request):
    if not (is_official(request.user) or is_president(request.user)):
        return HttpResponseForbidden('Brak uprawnień')

    year, month, error = _get_year_month(request)
    if error:
        return error
    operations = _monthly_rescue_queryset(request.user, year, month).order_by('-occurred_at')

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="raport-miesieczny-{year}-{month:02d}.pdf"'

    pdf = canvas.Canvas(response, pagesize=A4)
    _, page_height = A4
    text = pdf.beginText(40, page_height - 50)
    text.setFont(_pdf_font_name('bold'), 14)
    text.textLine(f'Raport miesięczny działań ratowniczych: {year}-{month:02d}')
    text.setFont(_pdf_font_name(), 10)
    text.textLine('')
    text.textLine(f'Liczba działań: {operations.count()}')
    text.textLine('')
    text.textLine('Lista działań:')
    for operation in operations[:70]:
        text.textLine(
            f'- #{operation.pk} | {operation.occurred_at.strftime("%Y-%m-%d %H:%M")} | '
            f'{operation.get_status_display()} | {operation.title[:50]}'
        )
    if operations.count() > 70:
        text.textLine('... (lista skrócona)')

    pdf.drawText(text)
    pdf.showPage()
    pdf.save()
    return response


@login_required
def panel(request):
    user = request.user
    context = {'is_president': is_president(user), 'is_official': is_official(user)}

    if context['is_official']:
        submitted_qs = Request.objects.filter(status=Request.STATUS_SUBMITTED).order_by('-updated_at')
        context['submitted_count'] = submitted_qs.count()
        context['recent_submitted'] = submitted_qs[:8]

    if context['is_president']:
        context['units'] = president_units(user)

    return render(request, 'osp/panel.html', context)


# ==================== OSP REPORTING VIEWS ====================


@login_required
def osp_report_list(request, unit_pk=None):
    """List OSP reports with optional unit filtering."""
    user = request.user
    if is_official(user):
        reports = OSPReport.objects.select_related('unit', 'created_by').order_by('-created_at')
        if unit_pk:
            unit = get_object_or_404(Unit, pk=unit_pk)
            reports = reports.filter(unit=unit)
    elif is_president(user):
        units = president_units(user)
        reports = OSPReport.objects.select_related('unit', 'created_by').filter(unit__in=units).order_by('-created_at')
        if unit_pk:
            unit = get_object_or_404(units, pk=unit_pk)
            reports = reports.filter(unit=unit)
    else:
        return HttpResponseForbidden('Brak dostępu')

    status = request.GET.get('status', '').strip()
    if status in dict(OSPReport.STATUS_CHOICES):
        reports = reports.filter(status=status)
    query = request.GET.get('q', '').strip()
    if query:
        reports = reports.filter(Q(title__icontains=query) | Q(description__icontains=query))
    page_obj = paginate(request, reports)
    return render(request, 'osp/osp_report_list.html', {
        'reports': page_obj,
        'page_obj': page_obj,
        'unit_pk': unit_pk,
        'q': query,
        'status': status,
        'status_choices': OSPReport.STATUS_CHOICES,
    })


@login_required
def osp_report_create(request, unit_pk):
    """Create a new OSP report."""
    unit = get_object_or_404(Unit, pk=unit_pk)
    if not can_manage_unit(request.user, unit):
        return HttpResponseForbidden('Tylko prezes tej jednostki może tworzyć raporty')

    if request.method == 'POST':
        form = OSPReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.unit = unit
            report.created_by = request.user
            report.save()
            return redirect('osp:osp_report_detail', pk=report.pk)
    else:
        form = OSPReportForm()
    
    return render(request, 'osp/osp_report_form.html', {'form': form, 'unit': unit})


@login_required
def osp_report_detail(request, pk):
    """View OSP report details with all related data."""
    report = get_object_or_404(OSPReport.objects.select_related('unit', 'created_by'), pk=pk)
    user = request.user
    
    # Check permissions
    if is_president(user):
        if report.unit not in president_units(user):
            return HttpResponseForbidden('Brak dostępu do tego raportu')
        can_edit = report.status == OSPReport.STATUS_DRAFT
    elif is_official(user):
        can_edit = False
    else:
        return HttpResponseForbidden('Brak dostępu')
    
    fuel_usage = report.fuel_usage.all()
    
    return render(request, 'osp/osp_report_detail.html', {
        'report': report,
        'fuel_usage': fuel_usage,
        'can_edit': can_edit,
    })


@login_required
def osp_report_edit(request, pk):
    """Edit OSP report."""
    report = get_object_or_404(OSPReport, pk=pk)
    user = request.user
    
    if is_president(user):
        if report.unit not in president_units(user) or report.status != OSPReport.STATUS_DRAFT:
            return HttpResponseForbidden('Nie możesz edytować tego raportu')
    else:
        return HttpResponseForbidden('Brak dostępu')

    if request.method == 'POST':
        form = OSPReportForm(request.POST, instance=report)
        if form.is_valid():
            form.save()
            return redirect('osp:osp_report_detail', pk=report.pk)
    else:
        form = OSPReportForm(instance=report)
    
    return render(request, 'osp/osp_report_form.html', {'form': form, 'report': report})


@login_required
def fuel_usage_add(request, report_pk):
    """Add fuel usage record to report."""
    report = get_object_or_404(OSPReport, pk=report_pk)
    user = request.user
    
    if is_president(user):
        if report.unit not in president_units(user) or report.status != OSPReport.STATUS_DRAFT:
            return HttpResponseForbidden('Nie możesz dodawać paliwa do tego raportu')
    else:
        return HttpResponseForbidden('Brak dostępu')

    if request.method == 'POST':
        form = FuelUsageForm(request.POST, unit=report.unit, report=report)
        if form.is_valid():
            fuel = form.save(commit=False)
            fuel.report = report
            fuel.recorded_by = request.user
            fuel.save()
            return redirect('osp:osp_report_detail', pk=report.pk)
    else:
        form = FuelUsageForm(unit=report.unit, report=report)
    
    return render(request, 'osp/fuel_usage_form.html', {'form': form, 'report': report})


@login_required
def vehicle_insurance_add(request, unit_pk):
    """Add or manage vehicle insurance."""
    unit = get_object_or_404(Unit, pk=unit_pk)
    user = request.user
    
    if not is_president(user) or unit not in president_units(user):
        return HttpResponseForbidden('Brak dostępu')

    if request.method == 'POST':
        form = VehicleInsuranceForm(request.POST, unit=unit)
        if form.is_valid():
            form.save()
            return redirect('osp:vehicle_insurance_list', unit_pk=unit.pk)
    else:
        form = VehicleInsuranceForm(unit=unit)
    
    return render(request, 'osp/vehicle_insurance_form.html', {'form': form, 'unit': unit})


@login_required
def vehicle_insurance_list(request, unit_pk):
    """List vehicles with insurance info."""
    unit = get_object_or_404(Unit, pk=unit_pk)
    user = request.user
    
    if is_president(user):
        if unit not in president_units(user):
            return HttpResponseForbidden('Brak dostępu')
    elif is_official(user):
        pass
    else:
        return HttpResponseForbidden('Brak dostępu')
    
    insurance_list = VehicleInsurance.objects.filter(unit=unit).select_related('equipment')
    today = timezone.localdate()

    return render(request, 'osp/vehicle_insurance_list.html', {
        'insurance_list': insurance_list,
        'unit': unit,
        'today': today,
        'soon': today + timedelta(days=60),
        'is_president': is_president(user),
        'is_official': is_official(user),
    })


@login_required
def firefighter_test_add(request, firefighter_pk):
    """Add test/certification record for firefighter."""
    firefighter = get_object_or_404(Firefighter, pk=firefighter_pk)
    user = request.user
    
    if is_president(user):
        if firefighter.unit not in president_units(user):
            return HttpResponseForbidden('Brak dostępu')
    elif is_official(user):
        pass
    else:
        return HttpResponseForbidden('Brak dostępu')

    if request.method == 'POST':
        form = FirefighterTestForm(request.POST)
        if form.is_valid():
            test = form.save(commit=False)
            test.firefighter = firefighter
            test.save()
            return redirect('osp:firefighter_edit', pk=firefighter.pk)
    else:
        form = FirefighterTestForm()
    
    return render(request, 'osp/firefighter_test_form.html', {'form': form, 'firefighter': firefighter})


@login_required
def equipment_maintenance_list(request, unit_pk):
    """List equipment maintenance records."""
    unit = get_object_or_404(Unit, pk=unit_pk)
    user = request.user
    
    if is_president(user):
        if unit not in president_units(user):
            return HttpResponseForbidden('Brak dostępu')
    elif is_official(user):
        pass
    else:
        return HttpResponseForbidden('Brak dostępu')
    
    maintenance = EquipmentMaintenance.objects.filter(
        equipment__unit=unit
    ).select_related('equipment').order_by('-scheduled_date')
    
    return render(request, 'osp/equipment_maintenance_list.html', {
        'maintenance_list': maintenance,
        'unit': unit,
    })


@login_required
def training_record_list(request, firefighter_pk):
    """List training records for a firefighter."""
    firefighter = get_object_or_404(Firefighter, pk=firefighter_pk)
    user = request.user
    
    if is_president(user):
        if firefighter.unit not in president_units(user):
            return HttpResponseForbidden('Brak dostępu')
    elif is_official(user):
        pass
    else:
        return HttpResponseForbidden('Brak dostępu')
    
    training = TrainingRecord.objects.filter(firefighter=firefighter).order_by('-training_date')

    return render(request, 'osp/training_record_list.html', {
        'training_list': training,
        'firefighter': firefighter,
        'today': timezone.localdate(),
    })


@login_required
@require_POST
def osp_report_submit(request, pk):
    """Submit report for approval."""
    report = get_object_or_404(OSPReport, pk=pk)
    user = request.user

    if not can_manage_unit(user, report.unit):
        return HttpResponseForbidden('Brak dostępu')

    if report.status != OSPReport.STATUS_DRAFT:
        return HttpResponseBadRequest('Raport musi być w stanie roboczym')

    report.status = OSPReport.STATUS_SUBMITTED
    report.submitted_by = user
    report.submitted_at = timezone.now()
    report.save()

    log_sis_event(
        report.unit,
        user,
        SisAuditLog.EVENT_REPORT_FLOW,
        f'Złożono raport OSP #{report.pk} do akceptacji.',
    )
    notify_officials(
        f'Raport OSP #{report.pk} do akceptacji',
        f'Jednostka {report.unit.name} złożyła raport "{report.title}" do akceptacji.',
    )

    return redirect('osp:osp_report_detail', pk=report.pk)


@login_required
@require_POST
def osp_report_approve(request, pk):
    """Accept a submitted OSP report (official only)."""
    report = get_object_or_404(OSPReport, pk=pk)
    user = request.user

    if not is_official(user):
        return HttpResponseForbidden('Tylko urzędnik może zaakceptować raport')

    if report.status != OSPReport.STATUS_SUBMITTED:
        return HttpResponseBadRequest('Raport musi być złożony')

    report.status = OSPReport.STATUS_ACCEPTED
    report.approved_by = user
    report.approved_at = timezone.now()
    report.save()

    log_sis_event(
        report.unit,
        user,
        SisAuditLog.EVENT_REPORT_FLOW,
        f'Zaakceptowano raport OSP #{report.pk}.',
    )
    notify_user(
        report.created_by,
        f'Raport OSP #{report.pk} zaakceptowany',
        f'Raport "{report.title}" został zaakceptowany przez urzędnika.',
    )

    return redirect('osp:osp_report_detail', pk=report.pk)


@login_required
@require_POST
def osp_report_archive(request, pk):
    """Archive an accepted OSP report (official only)."""
    report = get_object_or_404(OSPReport, pk=pk)
    user = request.user

    if not is_official(user):
        return HttpResponseForbidden('Tylko urzędnik może archiwizować raport')

    if report.status != OSPReport.STATUS_ACCEPTED:
        return HttpResponseBadRequest('Raport musi być zaakceptowany')

    report.status = OSPReport.STATUS_ARCHIVED
    report.archived_at = timezone.now()
    report.save()

    log_sis_event(
        report.unit,
        user,
        SisAuditLog.EVENT_REPORT_FLOW,
        f'Zarchiwizowano raport OSP #{report.pk}.',
    )

    return redirect('osp:osp_report_detail', pk=report.pk)


@login_required
def osp_report_export_pdf(request, pk):
    """Export OSP report as PDF."""
    report = get_object_or_404(OSPReport.objects.prefetch_related('fuel_usage'), pk=pk)
    user = request.user
    
    # Check permissions
    if is_president(user):
        if report.unit not in president_units(user):
            return HttpResponseForbidden('Brak dostępu')
    elif is_official(user):
        pass
    else:
        return HttpResponseForbidden('Brak dostępu')
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="raport-osp-{report.pk}.pdf"'
    
    pdf = canvas.Canvas(response, pagesize=A4)
    _, page_height = A4
    text = pdf.beginText(40, page_height - 50)
    text.setFont(_pdf_font_name('bold'), 14)
    text.textLine('Raport Ochotniczej Straży Pożarnej')
    text.setFont(_pdf_font_name(), 10)
    text.textLine('')
    
    lines = [
        f'Jednostka: {report.unit.name}',
        f'Okres: {report.report_start_date} - {report.report_end_date}',
        f'Status: {report.get_status_display()}',
        f'Utworzono: {report.created_at.strftime("%Y-%m-%d %H:%M")}',
        '',
        f'Tytuł: {report.title}',
    ]
    for line in lines:
        text.textLine(line)
    
    if report.description:
        text.textLine('')
        text.textLine('Opis:')
        for raw_line in report.description.splitlines():
            text.textLine(raw_line[:115])
    
    # Fuel usage summary
    fuel_records = report.fuel_usage.all()
    if fuel_records.exists():
        text.textLine('')
        text.textLine('Rozliczenie paliwa:')
        total_liters = sum(f.liters for f in fuel_records)
        total_cost = sum(f.total_cost for f in fuel_records)
        text.textLine(f'Łączna ilość paliwa: {total_liters} litrów')
        text.textLine(f'Łączny koszt: {total_cost} zł')
        text.textLine(f'Liczba tankowań: {fuel_records.count()}')
    
    pdf.drawText(text)
    pdf.showPage()
    pdf.save()
    
    return response


# ==================== MAINTENANCE / TRAINING VIEWS ====================


def _can_manage_maintenance(user, maintenance):
    unit = maintenance.equipment.unit
    return is_official(user) or can_manage_unit(user, unit)


@login_required
def equipment_maintenance_add(request, unit_pk):
    unit = get_object_or_404(Unit, pk=unit_pk)
    if not (is_official(request.user) or can_manage_unit(request.user, unit)):
        return HttpResponseForbidden('Brak dostępu')

    if request.method == 'POST':
        form = EquipmentMaintenanceForm(request.POST, unit=unit)
        if form.is_valid():
            form.save()
            return redirect('osp:equipment_maintenance_list', unit_pk=unit.pk)
    else:
        form = EquipmentMaintenanceForm(unit=unit)

    return render(request, 'osp/form_page.html', {
        'form': form,
        'title': 'Dodaj serwis sprzętu',
        'cancel_url': reverse('osp:equipment_maintenance_list', args=[unit.pk]),
    })


@login_required
def equipment_maintenance_edit(request, pk):
    maintenance = get_object_or_404(EquipmentMaintenance.objects.select_related('equipment__unit'), pk=pk)
    if not _can_manage_maintenance(request.user, maintenance):
        return HttpResponseForbidden('Brak dostępu')
    unit = maintenance.equipment.unit

    if request.method == 'POST':
        form = EquipmentMaintenanceForm(request.POST, instance=maintenance, unit=unit)
        if form.is_valid():
            form.save()
            return redirect('osp:equipment_maintenance_list', unit_pk=unit.pk)
    else:
        form = EquipmentMaintenanceForm(instance=maintenance, unit=unit)

    return render(request, 'osp/form_page.html', {
        'form': form,
        'title': 'Edytuj serwis sprzętu',
        'cancel_url': reverse('osp:equipment_maintenance_list', args=[unit.pk]),
    })


@login_required
def equipment_maintenance_delete(request, pk):
    maintenance = get_object_or_404(EquipmentMaintenance.objects.select_related('equipment__unit'), pk=pk)
    if not _can_manage_maintenance(request.user, maintenance):
        return HttpResponseForbidden('Brak dostępu')
    unit = maintenance.equipment.unit

    if request.method == 'POST':
        maintenance.delete()
        return redirect('osp:equipment_maintenance_list', unit_pk=unit.pk)

    return render(request, 'osp/confirm_delete.html', {
        'object': maintenance,
        'title': 'Usuń serwis sprzętu',
        'cancel_url': reverse('osp:equipment_maintenance_list', args=[unit.pk]),
    })


@login_required
def training_record_add(request, firefighter_pk):
    firefighter = get_object_or_404(Firefighter, pk=firefighter_pk)
    if not can_manage_firefighter(request.user, firefighter):
        return HttpResponseForbidden('Brak dostępu')

    if request.method == 'POST':
        form = TrainingRecordForm(request.POST)
        if form.is_valid():
            training = form.save(commit=False)
            training.firefighter = firefighter
            training.save()
            return redirect('osp:training_record_list', firefighter_pk=firefighter.pk)
    else:
        form = TrainingRecordForm()

    return render(request, 'osp/form_page.html', {
        'form': form,
        'title': 'Dodaj szkolenie',
        'cancel_url': reverse('osp:training_record_list', args=[firefighter.pk]),
    })


@login_required
def training_record_edit(request, pk):
    training = get_object_or_404(TrainingRecord.objects.select_related('firefighter__unit'), pk=pk)
    if not can_manage_firefighter(request.user, training.firefighter):
        return HttpResponseForbidden('Brak dostępu')

    if request.method == 'POST':
        form = TrainingRecordForm(request.POST, instance=training)
        if form.is_valid():
            form.save()
            return redirect('osp:training_record_list', firefighter_pk=training.firefighter_id)
    else:
        form = TrainingRecordForm(instance=training)

    return render(request, 'osp/form_page.html', {
        'form': form,
        'title': 'Edytuj szkolenie',
        'cancel_url': reverse('osp:training_record_list', args=[training.firefighter_id]),
    })


@login_required
def training_record_delete(request, pk):
    training = get_object_or_404(TrainingRecord.objects.select_related('firefighter__unit'), pk=pk)
    if not can_manage_firefighter(request.user, training.firefighter):
        return HttpResponseForbidden('Brak dostępu')

    if request.method == 'POST':
        firefighter_pk = training.firefighter_id
        training.delete()
        return redirect('osp:training_record_list', firefighter_pk=firefighter_pk)

    return render(request, 'osp/confirm_delete.html', {
        'object': training,
        'title': 'Usuń szkolenie',
        'cancel_url': reverse('osp:training_record_list', args=[training.firefighter_id]),
    })


# ==================== EDIT / DELETE VIEWS ====================


@login_required
def fuel_usage_edit(request, pk):
    fuel = get_object_or_404(FuelUsage.objects.select_related('report__unit'), pk=pk)
    report = fuel.report
    if not can_manage_unit(request.user, report.unit) or report.status != OSPReport.STATUS_DRAFT:
        return HttpResponseForbidden('Nie możesz edytować tego tankowania')

    if request.method == 'POST':
        form = FuelUsageForm(request.POST, instance=fuel, unit=report.unit, report=report)
        if form.is_valid():
            form.save()
            return redirect('osp:osp_report_detail', pk=report.pk)
    else:
        form = FuelUsageForm(instance=fuel, unit=report.unit, report=report)

    return render(request, 'osp/form_page.html', {
        'form': form,
        'title': 'Edytuj tankowanie',
        'cancel_url': reverse('osp:osp_report_detail', args=[report.pk]),
    })


@login_required
def fuel_usage_delete(request, pk):
    fuel = get_object_or_404(FuelUsage.objects.select_related('report__unit'), pk=pk)
    report = fuel.report
    if not can_manage_unit(request.user, report.unit) or report.status != OSPReport.STATUS_DRAFT:
        return HttpResponseForbidden('Nie możesz usunąć tego tankowania')

    if request.method == 'POST':
        fuel.delete()
        return redirect('osp:osp_report_detail', pk=report.pk)

    return render(request, 'osp/confirm_delete.html', {
        'object': fuel,
        'title': 'Usuń tankowanie',
        'cancel_url': reverse('osp:osp_report_detail', args=[report.pk]),
    })


@login_required
def vehicle_insurance_edit(request, pk):
    insurance = get_object_or_404(VehicleInsurance.objects.select_related('unit'), pk=pk)
    if not (is_official(request.user) or can_manage_unit(request.user, insurance.unit)):
        return HttpResponseForbidden('Brak dostępu')

    if request.method == 'POST':
        form = VehicleInsuranceForm(request.POST, instance=insurance, unit=insurance.unit)
        if form.is_valid():
            form.save()
            return redirect('osp:vehicle_insurance_list', unit_pk=insurance.unit_id)
    else:
        form = VehicleInsuranceForm(instance=insurance, unit=insurance.unit)

    return render(request, 'osp/form_page.html', {
        'form': form,
        'title': 'Edytuj ubezpieczenie',
        'cancel_url': reverse('osp:vehicle_insurance_list', args=[insurance.unit_id]),
    })


@login_required
def vehicle_insurance_delete(request, pk):
    insurance = get_object_or_404(VehicleInsurance.objects.select_related('unit'), pk=pk)
    if not (is_official(request.user) or can_manage_unit(request.user, insurance.unit)):
        return HttpResponseForbidden('Brak dostępu')

    if request.method == 'POST':
        unit_pk = insurance.unit_id
        insurance.delete()
        return redirect('osp:vehicle_insurance_list', unit_pk=unit_pk)

    return render(request, 'osp/confirm_delete.html', {
        'object': insurance,
        'title': 'Usuń ubezpieczenie',
        'cancel_url': reverse('osp:vehicle_insurance_list', args=[insurance.unit_id]),
    })


@login_required
def firefighter_test_edit(request, pk):
    test = get_object_or_404(FirefighterTest.objects.select_related('firefighter__unit'), pk=pk)
    if not can_manage_firefighter(request.user, test.firefighter):
        return HttpResponseForbidden('Brak dostępu')

    if request.method == 'POST':
        form = FirefighterTestForm(request.POST, instance=test)
        if form.is_valid():
            form.save()
            return redirect('osp:firefighter_edit', pk=test.firefighter_id)
    else:
        form = FirefighterTestForm(instance=test)

    return render(request, 'osp/form_page.html', {
        'form': form,
        'title': 'Edytuj badanie/certyfikat',
        'cancel_url': reverse('osp:firefighter_edit', args=[test.firefighter_id]),
    })


@login_required
def firefighter_test_delete(request, pk):
    test = get_object_or_404(FirefighterTest.objects.select_related('firefighter__unit'), pk=pk)
    if not can_manage_firefighter(request.user, test.firefighter):
        return HttpResponseForbidden('Brak dostępu')

    if request.method == 'POST':
        firefighter_pk = test.firefighter_id
        test.delete()
        return redirect('osp:firefighter_edit', pk=firefighter_pk)

    return render(request, 'osp/confirm_delete.html', {
        'object': test,
        'title': 'Usuń badanie/certyfikat',
        'cancel_url': reverse('osp:firefighter_edit', args=[test.firefighter_id]),
    })


@login_required
def equipment_edit(request, pk):
    equipment = get_object_or_404(Equipment.objects.select_related('unit'), pk=pk)
    if not can_manage_unit(request.user, equipment.unit):
        return HttpResponseForbidden('Brak dostępu')

    if request.method == 'POST':
        form = EquipmentForm(request.POST, instance=equipment)
        if form.is_valid():
            form.save()
            return redirect('osp:equipment_list', unit_pk=equipment.unit_id)
    else:
        form = EquipmentForm(instance=equipment)

    return render(request, 'osp/form_page.html', {
        'form': form,
        'title': 'Edytuj sprzęt',
        'cancel_url': reverse('osp:equipment_list', args=[equipment.unit_id]),
    })


@login_required
def equipment_delete(request, pk):
    equipment = get_object_or_404(Equipment.objects.select_related('unit'), pk=pk)
    if not can_manage_unit(request.user, equipment.unit):
        return HttpResponseForbidden('Brak dostępu')

    if request.method == 'POST':
        unit_pk = equipment.unit_id
        equipment.delete()
        return redirect('osp:equipment_list', unit_pk=unit_pk)

    return render(request, 'osp/confirm_delete.html', {
        'object': equipment,
        'title': 'Usuń sprzęt',
        'cancel_url': reverse('osp:equipment_list', args=[equipment.unit_id]),
    })


@login_required
def personnel_edit(request, pk):
    personnel = get_object_or_404(PersonnelResource.objects.select_related('unit'), pk=pk)
    if not can_manage_unit(request.user, personnel.unit):
        return HttpResponseForbidden('Brak dostępu')

    if request.method == 'POST':
        form = PersonnelResourceForm(request.POST, instance=personnel, unit=personnel.unit)
        if form.is_valid():
            form.save()
            return redirect('osp:personnel_list', unit_pk=personnel.unit_id)
    else:
        form = PersonnelResourceForm(instance=personnel, unit=personnel.unit)

    return render(request, 'osp/form_page.html', {
        'form': form,
        'title': 'Edytuj siły i środki osobowe',
        'cancel_url': reverse('osp:personnel_list', args=[personnel.unit_id]),
    })


@login_required
def personnel_delete(request, pk):
    personnel = get_object_or_404(PersonnelResource.objects.select_related('unit'), pk=pk)
    if not can_manage_unit(request.user, personnel.unit):
        return HttpResponseForbidden('Brak dostępu')

    if request.method == 'POST':
        unit_pk = personnel.unit_id
        personnel.delete()
        return redirect('osp:personnel_list', unit_pk=unit_pk)

    return render(request, 'osp/confirm_delete.html', {
        'object': personnel,
        'title': 'Usuń siły i środki osobowe',
        'cancel_url': reverse('osp:personnel_list', args=[personnel.unit_id]),
    })


@login_required
def request_edit(request, pk):
    req = get_object_or_404(Request, pk=pk)
    if req.created_by != request.user or req.status != Request.STATUS_DRAFT:
        return HttpResponseForbidden('Możesz edytować tylko własne wnioski robocze')

    if request.method == 'POST':
        form = RequestForm(request.POST, instance=req, unit=req.unit)
        if form.is_valid():
            form.save()
            return redirect('osp:request_detail', pk=req.pk)
    else:
        form = RequestForm(instance=req, unit=req.unit)

    return render(request, 'osp/form_page.html', {
        'form': form,
        'title': 'Edytuj wniosek',
        'cancel_url': reverse('osp:request_detail', args=[req.pk]),
    })


@login_required
def request_delete(request, pk):
    req = get_object_or_404(Request, pk=pk)
    if req.created_by != request.user or req.status != Request.STATUS_DRAFT:
        return HttpResponseForbidden('Możesz usunąć tylko własne wnioski robocze')

    if request.method == 'POST':
        req.delete()
        return redirect('osp:request_list')

    return render(request, 'osp/confirm_delete.html', {
        'object': req,
        'title': 'Usuń wniosek',
        'cancel_url': reverse('osp:request_detail', args=[req.pk]),
    })


@login_required
def osp_report_delete(request, pk):
    report = get_object_or_404(OSPReport.objects.select_related('unit'), pk=pk)
    if not can_manage_unit(request.user, report.unit) or report.status != OSPReport.STATUS_DRAFT:
        return HttpResponseForbidden('Możesz usunąć tylko własny raport roboczy')

    if request.method == 'POST':
        report.delete()
        return redirect('osp:osp_report_list')

    return render(request, 'osp/confirm_delete.html', {
        'object': report,
        'title': 'Usuń raport OSP',
        'cancel_url': reverse('osp:osp_report_detail', args=[report.pk]),
    })


def landing(request):
    return render(request, 'osp/landing.html')
