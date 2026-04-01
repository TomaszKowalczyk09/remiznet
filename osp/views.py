from django.contrib.auth import logout as django_logout
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from .forms import (
    ArchiveRequestForm,
    EquipmentForm,
    FirefighterForm,
    PersonnelResourceForm,
    RequestForm,
    ResponseForm,
    SignRequestForm,
)
from .models import Equipment, Firefighter, PersonnelResource, Request, RequestResponse, SisAuditLog, Unit


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


def log_sis_event(unit, actor, event_type, message, req=None):
    SisAuditLog.objects.create(
        unit=unit,
        actor=actor,
        event_type=event_type,
        message=message,
        request=req,
    )


@login_required
def firefighter_list(request, unit_pk=None):
    user = request.user
    if is_official(user):
        if unit_pk:
            unit = get_object_or_404(Unit, pk=unit_pk)
            firefighters = Firefighter.objects.filter(unit=unit)
        else:
            firefighters = Firefighter.objects.all()
    elif is_president(user):
        units = president_units(user)
        if unit_pk:
            unit = get_object_or_404(units, pk=unit_pk)
            firefighters = Firefighter.objects.filter(unit=unit)
        else:
            firefighters = Firefighter.objects.filter(unit__in=units)
    else:
        return HttpResponseForbidden('Brak dostępu')
    return render(request, 'osp/firefighter_list.html', {'firefighters': firefighters})


@login_required
def equipment_list(request, unit_pk=None):
    user = request.user
    if is_official(user):
        if unit_pk:
            unit = get_object_or_404(Unit, pk=unit_pk)
            equipment = Equipment.objects.filter(unit=unit)
        else:
            equipment = Equipment.objects.all()
    elif is_president(user):
        units = president_units(user)
        if unit_pk:
            unit = get_object_or_404(units, pk=unit_pk)
            equipment = Equipment.objects.filter(unit=unit)
        else:
            equipment = Equipment.objects.filter(unit__in=units)
    else:
        return HttpResponseForbidden('Brak dostępu')
    return render(request, 'osp/equipment_list.html', {'equipment_list': equipment})


@login_required
def equipment_create(request, unit_pk):
    unit = get_object_or_404(Unit, pk=unit_pk)
    if not is_president(request.user):
        return HttpResponseForbidden('Tylko prezes może dodać sprzęt')

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
    if is_official(user):
        if unit_pk:
            unit = get_object_or_404(Unit, pk=unit_pk)
            personnel = PersonnelResource.objects.filter(unit=unit)
        else:
            personnel = PersonnelResource.objects.all()
    elif is_president(user):
        units = president_units(user)
        if unit_pk:
            unit = get_object_or_404(units, pk=unit_pk)
            personnel = PersonnelResource.objects.filter(unit=unit)
        else:
            personnel = PersonnelResource.objects.filter(unit__in=units)
    else:
        return HttpResponseForbidden('Brak dostępu')

    return render(request, 'osp/personnel_list.html', {'personnel_list': personnel})


@login_required
def personnel_create(request, unit_pk):
    unit = get_object_or_404(Unit, pk=unit_pk)
    if not is_president(request.user):
        return HttpResponseForbidden('Tylko prezes może dodać siły i środki osobowe')

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
    if not is_president(request.user):
        return HttpResponseForbidden('Tylko prezes może dodać strażaka')

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
    if not is_president(request.user):
        return HttpResponseForbidden('Tylko prezes może tworzyć wnioski')

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
        ).order_by('-updated_at')
    elif is_president(request.user):
        qs = Request.objects.filter(created_by=request.user).order_by('-updated_at')
    else:
        return HttpResponseForbidden('Brak uprawnień')
    return render(request, 'osp/request_list.html', {'requests': qs})


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
    text.setFont('Helvetica-Bold', 14)
    text.textLine('Wniosek OSP / KSRG')
    text.setFont('Helvetica', 10)
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


def landing(request):
    return render(request, 'osp/landing.html')
