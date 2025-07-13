# capa/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg, Sum
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.template.loader import render_to_string
from django.db import transaction
import json
from datetime import datetime, timedelta
import calendar

from .models import (
    CAPA, CAPAAction, CAPAEffectivenessCheck, CAPAApproval, 
    CAPAAttachment, CAPAComment
)
from .forms import (
    CAPACreateForm, CAPAEditForm, CAPASearchForm, CAPAActionForm,
    CAPAEffectivenessCheckForm, CAPAApprovalActionForm, CAPAAttachmentForm,
    CAPACommentForm, ActionUpdateForm, EffectivenessCheckForm
)
from accounts.models import User
from audit.utils import create_audit_log


@login_required
def capa_list(request):
    """قائمة CAPAs"""
    form = CAPASearchForm(request.GET)
    capas = CAPA.objects.select_related(
        'initiated_by', 'assigned_to', 'capa_owner'
    ).prefetch_related('affected_products', 'approvals')
    
    # تطبيق الفلاتر
    if form.is_valid():
        if form.cleaned_data.get('search'):
            search = form.cleaned_data['search']
            capas = capas.filter(
                Q(capa_number__icontains=search) |
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(problem_statement__icontains=search)
            )
        
        if form.cleaned_data.get('status'):
            capas = capas.filter(status=form.cleaned_data['status'])
        
        if form.cleaned_data.get('capa_type'):
            capas = capas.filter(capa_type=form.cleaned_data['capa_type'])
        
        if form.cleaned_data.get('source_type'):
            capas = capas.filter(source_type=form.cleaned_data['source_type'])
        
        if form.cleaned_data.get('priority'):
            capas = capas.filter(priority=form.cleaned_data['priority'])
        
        if form.cleaned_data.get('risk_level'):
            capas = capas.filter(risk_level=form.cleaned_data['risk_level'])
        
        if form.cleaned_data.get('date_from'):
            capas = capas.filter(initiated_date__gte=form.cleaned_data['date_from'])
        
        if form.cleaned_data.get('date_to'):
            capas = capas.filter(initiated_date__lte=form.cleaned_data['date_to'])
        
        if form.cleaned_data.get('assigned_to'):
            capas = capas.filter(assigned_to=form.cleaned_data['assigned_to'])
        
        if form.cleaned_data.get('is_overdue'):
            overdue_capas = []
            for capa in capas:
                if capa.is_overdue:
                    overdue_capas.append(capa.id)
            capas = capas.filter(id__in=overdue_capas)
    
    # التصفح
    paginator = Paginator(capas, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # إحصائيات
    stats = {
        'total': capas.count(),
        'draft': capas.filter(status='draft').count(),
        'open': capas.filter(status='open').count(),
        'in_progress': capas.filter(status='in_progress').count(),
        'pending_verification': capas.filter(status='pending_verification').count(),
        'closed': capas.filter(status='closed').count(),
        'overdue': sum(1 for capa in capas if capa.is_overdue),
    }
    
    return render(request, 'capa/capa_list.html', {
        'form': form,
        'page_obj': page_obj,
        'stats': stats,
    })


@login_required
def capa_dashboard(request):
    """لوحة تحكم CAPA"""
    # CAPAs النشطة
    active_capas = CAPA.objects.filter(
        status__in=['open', 'in_progress', 'pending_verification', 'pending_effectiveness']
    ).select_related('initiated_by', 'assigned_to', 'capa_owner')[:10]
    
    # CAPAs المتأخرة
    overdue_capas = []
    all_capas = CAPA.objects.filter(
        status__in=['open', 'in_progress', 'pending_verification', 'pending_effectiveness']
    )
    for capa in all_capas:
        if capa.is_overdue:
            overdue_capas.append(capa)
    
    # الموافقات المعلقة
    pending_approvals = CAPAApproval.objects.filter(
        status='pending',
        approver=request.user
    ).select_related('capa')
    
    # الإجراءات المعينة لي
    my_actions = CAPAAction.objects.filter(
        assigned_to=request.user,
        status__in=['planned', 'in_progress']
    ).select_related('capa')[:10]
    
    # فحوصات الفعالية المطلوبة
    effectiveness_checks_due = CAPAEffectivenessCheck.objects.filter(
        check_date__lte=timezone.now().date() + timedelta(days=7),
        result='pending',
        performed_by=request.user
    ).select_related('capa')
    
    # إحصائيات شهرية
    current_month = timezone.now().replace(day=1)
    monthly_stats = {
        'initiated': CAPA.objects.filter(
            initiated_date__gte=current_month
        ).count(),
        'completed': CAPA.objects.filter(
            status='closed',
            closed_date__gte=current_month
        ).count(),
        'avg_completion_time': calculate_avg_completion_time(),
        'effectiveness_rate': calculate_effectiveness_rate(),
    }
    
    # CAPAs حسب المصدر
    source_stats = {}
    for source, label in CAPA.SOURCE_TYPES:
        count = CAPA.objects.filter(source_type=source).count()
        if count > 0:
            source_stats[label] = count
    
    # اتجاهات المخاطر
    risk_trends = calculate_risk_trends()
    
    context = {
        'active_capas': active_capas,
        'overdue_capas': overdue_capas[:10],
        'pending_approvals': pending_approvals,
        'my_actions': my_actions,
        'effectiveness_checks_due': effectiveness_checks_due,
        'monthly_stats': monthly_stats,
        'source_stats': source_stats,
        'risk_trends': risk_trends,
    }
    
    return render(request, 'capa/dashboard.html', context)


@login_required
def my_capas(request):
    """CAPAs الخاصة بي"""
    # CAPAs التي بدأتها
    initiated = CAPA.objects.filter(initiated_by=request.user)
    
    # CAPAs المعينة لي
    assigned = CAPA.objects.filter(assigned_to=request.user)
    
    # CAPAs التي أملكها
    owned = CAPA.objects.filter(capa_owner=request.user)
    
    # الموافقات المعلقة
    pending_approvals = CAPAApproval.objects.filter(
        approver=request.user,
        status='pending'
    ).select_related('capa')
    
    # الإجراءات المعينة لي
    my_actions = CAPAAction.objects.filter(
        assigned_to=request.user,
        status__in=['planned', 'in_progress']
    ).select_related('capa')
    
    # فحوصات الفعالية
    my_effectiveness_checks = CAPAEffectivenessCheck.objects.filter(
        performed_by=request.user,
        result='pending'
    ).select_related('capa')
    
    context = {
        'initiated': initiated.order_by('-initiated_date')[:10],
        'assigned': assigned.order_by('-initiated_date')[:10],
        'owned': owned.order_by('-initiated_date')[:10],
        'pending_approvals': pending_approvals,
        'my_actions': my_actions,
        'my_effectiveness_checks': my_effectiveness_checks,
    }
    
    return render(request, 'capa/my_capas.html', context)


@login_required
def capa_create(request):
    """إنشاء CAPA جديد"""
    if request.method == 'POST':
        form = CAPACreateForm(request.POST)
        if form.is_valid():
            capa = form.save(commit=False)
            capa.initiated_by = request.user
            capa.save()
            form.save_m2m()  # حفظ العلاقات many-to-many
            
            # إنشاء سجل تدقيق
            create_audit_log(
                request.user, 'create', request,
                model_name='CAPA',
                object_id=capa.id,
                object_repr=str(capa)
            )
            
            messages.success(request, _('CAPA created successfully.'))
            return redirect('capa:detail', pk=capa.pk)
    else:
        form = CAPACreateForm()
        
        # التحقق من وجود مصدر محدد
        source_type = request.GET.get('source_type')
        source_ref = request.GET.get('source_ref')
        if source_type and source_ref:
            form.fields['source_type'].initial = source_type
            form.fields['source_reference'].initial = source_ref
    
    return render(request, 'capa/capa_create.html', {
        'form': form,
    })


@login_required
def capa_create_from_source(request, source_type, source_ref):
    """إنشاء CAPA من مصدر محدد"""
    if request.method == 'POST':
        form = CAPACreateForm(request.POST)
        if form.is_valid():
            capa = form.save(commit=False)
            capa.initiated_by = request.user
            capa.source_type = source_type
            capa.source_reference = source_ref
            capa.save()
            form.save_m2m()
            
            # ربط مع المصدر الأصلي
            if source_type == 'deviation':
                try:
                    from deviations.models import Deviation
                    deviation = Deviation.objects.get(deviation_number=source_ref)
                    capa.related_deviations.add(deviation)
                    deviation.related_capa = capa
                    deviation.save()
                except Deviation.DoesNotExist:
                    pass
            elif source_type == 'change_control':
                try:
                    from change_control.models import ChangeControl
                    change = ChangeControl.objects.get(change_number=source_ref)
                    capa.related_changes.add(change)
                except ChangeControl.DoesNotExist:
                    pass
            
            messages.success(request, _('CAPA created successfully from {}.').format(source_ref))
            return redirect('capa:detail', pk=capa.pk)
    else:
        form = CAPACreateForm(initial={
            'source_type': source_type,
            'source_reference': source_ref
        })
    
    return render(request, 'capa/capa_create.html', {
        'form': form,
        'source_type': source_type,
        'source_ref': source_ref,
    })


@login_required
def capa_detail(request, pk):
    """تفاصيل CAPA"""
    capa = get_object_or_404(
        CAPA.objects.select_related(
            'initiated_by', 'assigned_to', 'capa_owner'
        ).prefetch_related(
            'affected_products', 'related_documents', 'related_deviations',
            'related_changes', 'approvals__approver', 'attachments',
            'actions', 'effectiveness_checks', 'comments__user'
        ),
        pk=pk
    )
    
    # فحص الصلاحيات
    can_edit = (
        request.user == capa.initiated_by or 
        request.user == capa.assigned_to or
        request.user == capa.capa_owner or
        request.user.has_perm('capa.change_capa')
    )
    
    # الموافقات
    approvals = capa.approvals.all().order_by('approval_type')
    
    # الإجراءات
    actions = capa.actions.all().order_by('action_number')
    action_stats = {
        'total': actions.count(),
        'planned': actions.filter(status='planned').count(),
        'in_progress': actions.filter(status='in_progress').count(),
        'completed': actions.filter(status='completed').count(),
        'verified': actions.filter(status='verified').count(),
        'overdue': sum(1 for action in actions if action.is_overdue),
    }
    
    # فحوصات الفعالية
    effectiveness_checks = capa.effectiveness_checks.all().order_by('-check_date')
    
    # المرفقات
    attachments = capa.attachments.all().order_by('-uploaded_date')
    
    # التعليقات
    comments = capa.comments.filter(is_internal=True).order_by('-created_date')
    
    # تقييم التقدم
    total_cost = actions.aggregate(
        estimated=Sum('estimated_cost'),
        actual=Sum('actual_cost')
    )
    
    context = {
        'capa': capa,
        'can_edit': can_edit,
        'approvals': approvals,
        'actions': actions,
        'action_stats': action_stats,
        'effectiveness_checks': effectiveness_checks,
        'attachments': attachments,
        'comments': comments,
        'total_cost': total_cost,
    }
    
    return render(request, 'capa/capa_detail.html', context)


@login_required
def action_create(request, pk):
    """إنشاء إجراء CAPA"""
    capa = get_object_or_404(CAPA, pk=pk)
    
    # فحص الصلاحيات
    if not (request.user == capa.capa_owner or
            request.user == capa.assigned_to or
            request.user.has_perm('capa.add_capaaction')):
        messages.error(request, _('You do not have permission to create actions.'))
        return redirect('capa:detail', pk=pk)
    
    if request.method == 'POST':
        form = CAPAActionForm(request.POST, capa=capa)
        if form.is_valid():
            action = form.save(commit=False)
            action.capa = capa
            
            # توليد رقم الإجراء
            last_action = capa.actions.order_by('-action_number').first()
            if last_action:
                last_num = int(last_action.action_number[1:])  # إزالة A
                next_num = last_num + 1
            else:
                next_num = 1
            action.action_number = f'A{next_num:03d}'
            
            action.save()
            form.save_m2m()  # حفظ التبعيات
            
            # تحديث حالة CAPA إذا لزم الأمر
            if capa.status == 'draft':
                capa.status = 'open'
                capa.save()
            
            messages.success(request, _('Action created successfully.'))
            return redirect('capa:detail', pk=pk)
    else:
        form = CAPAActionForm(capa=capa)
    
    return render(request, 'capa/action_create.html', {
        'form': form,
        'capa': capa,
    })


@login_required
def action_list(request, pk):
    """قائمة إجراءات CAPA"""
    capa = get_object_or_404(CAPA, pk=pk)
    actions = capa.actions.all().order_by('action_number')
    
    # إحصائيات
    action_stats = {
        'total': actions.count(),
        'planned': actions.filter(status='planned').count(),
        'in_progress': actions.filter(status='in_progress').count(),
        'completed': actions.filter(status='completed').count(),
        'verified': actions.filter(status='verified').count(),
        'overdue': sum(1 for action in actions if action.is_overdue),
    }
    
    return render(request, 'capa/action_list.html', {
        'capa': capa,
        'actions': actions,
        'action_stats': action_stats,
    })


@login_required
@require_POST
def action_update_status(request, action_id):
    """تحديث حالة الإجراء"""
    action = get_object_or_404(CAPAAction, id=action_id)
    
    # فحص الصلاحيات
    if not (request.user == action.assigned_to or
            request.user == action.capa.capa_owner or
            request.user.has_perm('capa.change_capaaction')):
        return JsonResponse({'success': False, 'error': 'Permission denied'})
    
    form = ActionUpdateForm(request.POST)
    if form.is_valid():
        action.status = form.cleaned_data['status']
        action.progress_percentage = form.cleaned_data.get('progress_percentage', action.progress_percentage)
        
        if form.cleaned_data['status'] == 'in_progress' and not action.actual_start_date:
            action.actual_start_date = timezone.now().date()
        elif form.cleaned_data['status'] == 'completed':
            action.actual_completion_date = timezone.now().date()
            action.progress_percentage = 100
        
        if form.cleaned_data.get('notes'):
            action.notes = form.cleaned_data['notes']
        
        action.save()
        
        # تحديث حالة CAPA إذا لزم الأمر
        update_capa_status_based_on_actions(action.capa)
        
        return JsonResponse({'success': True, 'status': action.status})
    
    return JsonResponse({'success': False, 'error': 'Invalid form data'})


@login_required
def effectiveness_create(request, pk):
    """إنشاء فحص فعالية"""
    capa = get_object_or_404(CAPA, pk=pk)
    
    # فحص إذا كان CAPA مؤهل لفحص الفعالية
    if capa.status not in ['pending_effectiveness', 'closed']:
        messages.error(request, _('CAPA must be in pending effectiveness status.'))
        return redirect('capa:detail', pk=pk)
    
    if request.method == 'POST':
        form = CAPAEffectivenessCheckForm(request.POST)
        if form.is_valid():
            check = form.save(commit=False)
            check.capa = capa
            check.performed_by = request.user
            
            # توليد رقم الفحص
            last_check = capa.effectiveness_checks.order_by('-check_number').first()
            if last_check:
                last_num = int(last_check.check_number[2:])  # إزالة EC
                next_num = last_num + 1
            else:
                next_num = 1
            check.check_number = f'EC{next_num:03d}'
            
            check.save()
            
            # تحديث حالة CAPA حسب نتيجة الفحص
            if check.result == 'effective':
                capa.status = 'closed'
                capa.closed_date = timezone.now()
                capa.save()
            elif check.result in ['partially_effective', 'ineffective']:
                if check.additional_actions_required:
                    capa.status = 'in_progress'
                    capa.save()
            
            messages.success(request, _('Effectiveness check created successfully.'))
            return redirect('capa:detail', pk=pk)
    else:
        form = CAPAEffectivenessCheckForm()
    
    return render(request, 'capa/effectiveness_create.html', {
        'form': form,
        'capa': capa,
    })


@login_required
def capa_approve(request, pk):
    """صفحة الموافقة على CAPA"""
    capa = get_object_or_404(CAPA, pk=pk)
    
    # البحث عن الموافقات المعلقة للمستخدم الحالي
    pending_approvals = capa.approvals.filter(
        approver=request.user,
        status='pending'
    )
    
    if not pending_approvals.exists():
        messages.error(request, _('You do not have pending approvals for this CAPA.'))
        return redirect('capa:detail', pk=pk)
    
    return render(request, 'capa/capa_approve.html', {
        'capa': capa,
        'pending_approvals': pending_approvals,
    })


@login_required
@require_POST
def approval_action(request, approval_id):
    """تنفيذ إجراء الموافقة"""
    approval = get_object_or_404(CAPAApproval, id=approval_id)
    
    # فحص الصلاحيات
    if request.user != approval.approver:
        messages.error(request, _('You are not authorized to act on this approval.'))
        return redirect('capa:detail', pk=approval.capa.pk)
    
    if approval.status != 'pending':
        messages.error(request, _('This approval has already been processed.'))
        return redirect('capa:detail', pk=approval.capa.pk)
    
    form = CAPAApprovalActionForm(request.POST)
    if form.is_valid():
        approval.status = form.cleaned_data['action']
        approval.comments = form.cleaned_data['comments']
        approval.approval_date = timezone.now()
        approval.save()
        
        # تحديث حالة CAPA
        capa = approval.capa
        if approval.status == 'approved':
            # فحص إذا كانت كل الموافقات المطلوبة تمت
            pending_approvals = capa.approvals.filter(
                approval_type=approval.approval_type,
                status='pending'
            )
            if not pending_approvals.exists():
                update_capa_status_after_approval(capa, approval.approval_type)
        elif approval.status == 'rejected':
            capa.status = 'draft'
            capa.save()
        
        messages.success(request, _('Approval action completed successfully.'))
    else:
        messages.error(request, _('Invalid form data.'))
    
    return redirect('capa:detail', pk=approval.capa.pk)


@login_required
def capa_statistics(request):
    """إحصائيات CAPA"""
    # إحصائيات عامة
    total_capas = CAPA.objects.count()
    
    # إحصائيات حسب الحالة
    status_stats = {}
    for status, label in CAPA.STATUS_CHOICES:
        status_stats[status] = CAPA.objects.filter(status=status).count()
    
    # إحصائيات حسب النوع
    type_stats = {}
    for capa_type, label in CAPA.CAPA_TYPES:
        type_stats[capa_type] = CAPA.objects.filter(capa_type=capa_type).count()
    
    # إحصائيات حسب المصدر
    source_stats = {}
    for source, label in CAPA.SOURCE_TYPES:
        source_stats[source] = CAPA.objects.filter(source_type=source).count()
    
    # إحصائيات حسب الأولوية
    priority_stats = {}
    for priority, label in CAPA.PRIORITY_LEVELS:
        priority_stats[priority] = CAPA.objects.filter(priority=priority).count()
    
    # إحصائيات شهرية
    monthly_stats = []
    for i in range(12):
        month_start = timezone.now().replace(month=i+1, day=1, hour=0, minute=0, second=0, microsecond=0)
        if i == 11:  # ديسمبر
            month_end = month_start.replace(year=month_start.year + 1, month=1)
        else:
            month_end = month_start.replace(month=i+2)
        
        month_capas = CAPA.objects.filter(
            initiated_date__gte=month_start,
            initiated_date__lt=month_end
        ).count()
        
        monthly_stats.append({
            'month': calendar.month_name[i+1],
            'count': month_capas
        })
    
    # معدل الفعالية
    effectiveness_rate = calculate_effectiveness_rate()
    
    # متوسط وقت الإنجاز
    avg_completion_time = calculate_avg_completion_time()
    
    context = {
        'total_capas': total_capas,
        'status_stats': status_stats,
        'type_stats': type_stats,
        'source_stats': source_stats,
        'priority_stats': priority_stats,
        'monthly_stats': monthly_stats,
        'effectiveness_rate': effectiveness_rate,
        'avg_completion_time': avg_completion_time,
    }
    
    return render(request, 'capa/statistics.html', context)


# دوال مساعدة
def calculate_avg_completion_time():
    """حساب متوسط وقت الإنجاز"""
    closed_capas = CAPA.objects.filter(
        status='closed',
        initiated_date__isnull=False,
        closed_date__isnull=False
    )
    
    if not closed_capas.exists():
        return 0
    
    total_days = 0
    for capa in closed_capas:
        delta = capa.closed_date.date() - capa.initiated_date.date()
        total_days += delta.days
    
    return round(total_days / closed_capas.count(), 1)


def calculate_effectiveness_rate():
    """حساب معدل الفعالية"""
    total_checks = CAPAEffectivenessCheck.objects.exclude(result='pending').count()
    if total_checks == 0:
        return 0
    
    effective_checks = CAPAEffectivenessCheck.objects.filter(
        result__in=['effective', 'partially_effective']
    ).count()
    
    return round((effective_checks / total_checks) * 100, 1)


def calculate_risk_trends():
    """حساب اتجاهات المخاطر"""
    # حساب CAPAs حسب مستوى المخاطر في آخر 6 أشهر
    six_months_ago = timezone.now() - timedelta(days=180)
    
    risk_trends = {}
    for risk_level, label in CAPA.RISK_LEVELS:
        count = CAPA.objects.filter(
            risk_level=risk_level,
            initiated_date__gte=six_months_ago
        ).count()
        risk_trends[risk_level] = count
    
    return risk_trends


def update_capa_status_based_on_actions(capa):
    """تحديث حالة CAPA بناءً على حالة الإجراءات"""
    actions = capa.actions.all()
    if not actions.exists():
        return
    
    total_actions = actions.count()
    completed_actions = actions.filter(status='completed').count()
    verified_actions = actions.filter(status='verified').count()
    
    if verified_actions == total_actions:
        capa.status = 'pending_effectiveness'
        capa.save()
    elif completed_actions == total_actions:
        capa.status = 'pending_verification'
        capa.save()
    elif completed_actions > 0:
        capa.status = 'in_progress'
        capa.save()


def update_capa_status_after_approval(capa, approval_type):
    """تحديث حالة CAPA بعد الموافقة"""
    if approval_type == 'initiation':
        capa.status = 'open'
    elif approval_type == 'action_plan':
        capa.status = 'in_progress'
    elif approval_type == 'implementation':
        capa.status = 'pending_verification'
    elif approval_type == 'effectiveness':
        capa.status = 'pending_effectiveness'
    elif approval_type == 'closure':
        capa.status = 'closed'
        capa.closed_date = timezone.now()
    
    capa.save()


@login_required
def capa_chart_data(request):
    """بيانات المخططات لـ CAPA"""
    chart_type = request.GET.get('type', 'status')
    
    if chart_type == 'status':
        data = []
        for status, label in CAPA.STATUS_CHOICES:
            count = CAPA.objects.filter(status=status).count()
            if count > 0:
                data.append({
                    'label': str(label),
                    'value': count
                })
        return JsonResponse(data, safe=False)
    
    elif chart_type == 'source':
        data = []
        for source, label in CAPA.SOURCE_TYPES:
            count = CAPA.objects.filter(source_type=source).count()
            if count > 0:
                data.append({
                    'label': str(label),
                    'value': count
                })
        return JsonResponse(data, safe=False)
    
    return JsonResponse([], safe=False)


@login_required
def capa_reports(request):
    """تقارير CAPA"""
    # تقرير CAPAs النشطة
    active_capas = CAPA.objects.filter(
        status__in=['open', 'in_progress', 'pending_verification', 'pending_effectiveness']
    ).count()
    
    # تقرير CAPAs المتأخرة
    overdue_count = 0
    all_capas = CAPA.objects.filter(
        status__in=['open', 'in_progress', 'pending_verification', 'pending_effectiveness']
    )
    for capa in all_capas:
        if capa.is_overdue:
            overdue_count += 1
    
    # تقرير الفعالية
    effectiveness_rate = calculate_effectiveness_rate()
    
    # تقرير متوسط وقت الإنجاز
    avg_completion_time = calculate_avg_completion_time()
    
    context = {
        'active_capas': active_capas,
        'overdue_count': overdue_count,
        'effectiveness_rate': effectiveness_rate,
        'avg_completion_time': avg_completion_time,
    }
    
    return render(request, 'capa/reports.html', context)