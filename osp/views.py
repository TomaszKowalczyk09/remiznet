from django.utils import timezone
from django.contrib.auth.decorators import login_required
from .forms import SignRequestForm
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseForbidden, HttpResponseBadRequest
from django.db.models import Q
from .models import Unit, Firefighter, Request, RequestResponse
from .forms import FirefighterForm, RequestForm, ResponseForm
from django.contrib.auth.models import Group


def president_units(user):
    return Unit.objects.filter(
        Q(president=user) | Q(firefighters__created_by=user)
    ).distinct()

def firefighter_list(request, unit_pk=None):
    user = request.user
    if is_official(user):
        # Urzędnicy widzą wszystkich strażaków
        if unit_pk:
            unit = get_object_or_404(Unit, pk=unit_pk)
            firefighters = Firefighter.objects.filter(unit=unit)
        else:
            firefighters = Firefighter.objects.all()
    elif is_president(user):
        # Prezesi widzą tylko strażaków ze swoich jednostek
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
def request_sign(request, pk):
    req = get_object_or_404(Request, pk=pk)
    if not is_president(request.user):
        return HttpResponseForbidden('Tylko prezes może podpisać wniosek')
    if req.signed_by:
        return redirect('osp:request_detail', pk=pk)
    if request.method == 'POST':
        form = SignRequestForm(request.POST)
        if form.is_valid():
            req.signed_by = request.user
            req.signed_at = timezone.now()
            req.save()
            return redirect('osp:request_detail', pk=pk)
    else:
        form = SignRequestForm()
    return render(request, 'osp/request_sign.html', {'form': form, 'request_obj': req})
from django.contrib.auth import logout as django_logout

from django.shortcuts import render, redirect

def logout_view(request):
    if request.method == 'POST':
        django_logout(request)
        return render(request, 'registration/logout.html')
    elif request.method == 'GET':
        django_logout(request)
        return render(request, 'registration/logout.html')
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, HttpResponseBadRequest
from .models import Unit, Firefighter, Request, RequestResponse
from .forms import FirefighterForm, RequestForm, ResponseForm
from django.contrib.auth.models import Group


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
    # Prezes może edytować tylko swoich strażaków
    if is_president(user):
        if firefighter.unit not in president_units(user):
            return HttpResponseForbidden('Brak dostępu do edycji tego strażaka')
        can_edit = True
    # Urzędnik ma tylko podgląd
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
        form = RequestForm(request.POST)
        if form.is_valid():
            req = form.save(commit=False)
            req.unit = unit
            req.created_by = request.user
            if request.POST.get('submit') == '1':
                req.status = Request.STATUS_SUBMITTED
            req.save()
            return redirect('osp:request_list')
    else:
        form = RequestForm()
    return render(request, 'osp/request_form.html', {'form': form, 'unit': unit})


@login_required
def request_list(request):
    if is_official(request.user):
        qs = Request.objects.filter(status=Request.STATUS_SUBMITTED)
    elif is_president(request.user):
        # show requests for user's unit(s) — assuming one unit per president for simplicity
        qs = Request.objects.filter(created_by=request.user)
    else:
        return HttpResponseForbidden('Brak uprawnień')
    return render(request, 'osp/request_list.html', {'requests': qs})


@login_required
def request_detail(request, pk):
    req = get_object_or_404(Request, pk=pk)
    user = request.user
    user_is_president = is_president(user)
    user_is_official = is_official(user)

    if user_is_president and req.created_by == user:
        pass
    elif user_is_official:
        pass
    else:
        return HttpResponseForbidden('Brak uprawnień do podglądu tego wniosku')

    context = {
        'request_obj': req,
        'is_president': user_is_president,
        'is_official': user_is_official,
        'can_sign': user_is_president and not req.signed_by,
        'can_respond': user_is_official and req.status == Request.STATUS_SUBMITTED,
    }
    return render(request, 'osp/request_detail.html', context)


@login_required
def request_respond(request, pk):
    req = get_object_or_404(Request, pk=pk)
    if not is_official(request.user):
        return HttpResponseForbidden('Tylko urzędnik może odpowiedzieć na wniosek')

    if req.status in [Request.STATUS_ACCEPTED, Request.STATUS_REJECTED]:
        return HttpResponseBadRequest('Wniosek został już zakończony')

    if request.method == 'POST':
        form = ResponseForm(request.POST)
        if form.is_valid():
            resp = form.save(commit=False)
            resp.request = req
            resp.responder = request.user
            resp.save()
            if resp.action == RequestResponse.ACTION_ACCEPT:
                req.status = Request.STATUS_ACCEPTED
                req.save()
            elif resp.action == RequestResponse.ACTION_REJECT:
                req.status = Request.STATUS_REJECTED
                req.save()
            return redirect('osp:request_detail', pk=pk)
    else:
        form = ResponseForm()
    return render(request, 'osp/request_respond.html', {'form': form, 'request_obj': req})


@login_required
def panel(request):
    # Panel pokazujący różne opcje zależnie od roli
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
    # Public landing page
    return render(request, 'osp/landing.html')
