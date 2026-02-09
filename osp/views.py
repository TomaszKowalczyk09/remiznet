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
        return HttpResponseForbidden('Only presidents can add firefighters')

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
def request_create(request, unit_pk):
    unit = get_object_or_404(Unit, pk=unit_pk)
    if not is_president(request.user):
        return HttpResponseForbidden('Only presidents can create requests')

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
        return HttpResponseForbidden('Not authorized')
    return render(request, 'osp/request_list.html', {'requests': qs})


@login_required
def request_detail(request, pk):
    req = get_object_or_404(Request, pk=pk)
    if is_president(request.user) and req.created_by == request.user:
        pass
    elif is_official(request.user):
        pass
    else:
        return HttpResponseForbidden('Not authorized to view this request')
    return render(request, 'osp/request_detail.html', {'request_obj': req})


@login_required
def request_respond(request, pk):
    req = get_object_or_404(Request, pk=pk)
    if not is_official(request.user):
        return HttpResponseForbidden('Only officials can respond')

    if req.status in [Request.STATUS_ACCEPTED, Request.STATUS_REJECTED]:
        return HttpResponseBadRequest('Request already finalized')

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
    # Basic panel showing different options depending on role
    user = request.user
    context = {'is_president': is_president(user), 'is_official': is_official(user)}

    if context['is_official']:
        submitted_qs = Request.objects.filter(status=Request.STATUS_SUBMITTED).order_by('-updated_at')
        context['submitted_count'] = submitted_qs.count()
        context['recent_submitted'] = submitted_qs[:8]

    if context['is_president']:
        # For simplicity, show units created_by the president (or all units)
        context['units'] = Unit.objects.all()

    return render(request, 'osp/panel.html', context)


def landing(request):
    # Public landing page
    return render(request, 'osp/landing.html')
