# change_control/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.template.loader import render_to_string
import json
from datetime import datetime, timedelta
from django.db import transaction
import calendar

from .models import (
    ChangeControl, ChangeImpactAssessment, ChangeImplementationPlan,
    ChangeTask, ChangeApproval, ChangeAttachment
)
from .forms import (
    ChangeControlCreateForm, ChangeControlEditForm, ChangeSearchForm,
    ChangeImpactAssessmentForm, ChangeImplementationPlanForm,
    ChangeTaskForm, ChangeApprovalActionForm, ChangeAttachmentForm
)
from accounts.models import User
from audit.utils import create_audit_log


@login_required
def change_list(request):
    """قائمة التغييرات"""
    form = ChangeSearchForm(request.GET)
    changes = ChangeControl.objects.select_related(
        'requester', 'change_owner', 'change_coordinator'
    ).prefetch_related('affected_products', 'approvals')
    
    # تطبيق الفلاتر
    if form.is_valid():
        if form.cleaned_data.get('search'):
            search = form.cleaned_data['search']
            changes = changes.filter(
                Q(change_number__icontains=search) |
                Q(title__icontains=search) |
                Q(description__icontains=search)
            )
        
        if form.cleaned_data.get('status'):
            changes = changes.filter(status=form.cleaned_data['status'])
        
        if form.cleaned_data.get('change_type'):
            changes = changes.filter(change_type=form.cleaned_data['change_type'])
        
        if form.cleaned_data.get('change_category'):
            changes = changes.filter(change_category=form.cleaned_data['change_category'])
        
        if form.cleaned_data.get('urgency'):
            changes = changes.filter(urgency=form.cleaned_data['urgency'])
        
        if form.cleaned_data.get('date_from'):
            changes = changes.filter(submission_date__gte=form.cleaned_data['date_from'])
        
        if form.cleaned_data.get('date_to'):
            changes = changes.filter(submission_date__lte=form.cleaned_data['date_to'])
        
        if form.cleaned_data.get('is_overdue'):
            overdue_changes = []
            for change in changes:
                if change.is_overdue:
                    overdue_changes.append(change.id)
            changes = changes.filter(id__in=overdue_changes)
    
    # التصفح
    paginator = Paginator(changes, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # إحصائيات
    stats = {
        'total': changes.count(),
        'draft': changes.filter(status='draft').count(),
        'submitted': changes.filter(status='submitted').count(),
        'approved': changes.filter(status='approved').count(),
        'in_progress': changes.filter(status='in_progress').count(),
        'completed': changes.filter(status='completed').count(),
    }
    
    return render(request, 'change_control/change_list.html', {
        'form': form,
        'page_obj': page_obj,
        'stats': stats,
    })


@login_required
def change_dashboard(request):
    """لوحة تحكم التغييرات"""
    # التغييرات النشطة
    active_changes = ChangeControl.objects.filter(
        status__in=['submitted', 'under_review', 'approved', 'in_progress']
    ).select_related('requester', 'change_owner')[:10]
    
    # التغييرات المتأخرة
    overdue_changes = []
    all_changes = ChangeControl.objects.filter(
        status__in=['submitted', 'under_review', 'approved', 'in_progress']
    )
    for change in all_changes:
        if change.is_overdue:
            overdue_changes.append(change)
    
    # الموافقات المعلقة
    pending_approvals = ChangeApproval.objects.filter(
        status='pending',
        approver=request.user
    ).select_related('change_control')
    
    # المهام المعينة لي
    my_tasks = ChangeTask.objects.filter(
        assigned_to=request.user,
        status__in=['pending', 'in_progress']
    ).select_related('implementation_plan__change_control')[:10]
    
    # إحصائيات شهرية
    current_month = timezone.now().replace(day=1)
    monthly_stats = {
        'submitted': ChangeControl.objects.filter(
            submission_date__gte=current_month
        ).count(),
        'approved': ChangeControl.objects.filter(
            status='approved',
            submission_date__gte=current_month
        ).count(),
        'completed': ChangeControl.objects.filter(
            status='completed',
            completion_date__gte=current_month
        ).count(),
    }
    
    # التغييرات القادمة للتنفيذ
    upcoming_implementations = ChangeControl.objects.filter(
        status='approved',
        target_implementation_date__gte=timezone.now().date(),
        target_implementation_date__lte=timezone.now().date() + timedelta(days=30)
    ).order_by('target_implementation_date')[:5]
    
    context = {
        'active_changes': active_changes,
        'overdue_changes': overdue_changes[:10],
        'pending_approvals': pending_approvals,
        'my_tasks': my_tasks,
        'monthly_stats': monthly_stats,
        'upcoming_implementations': upcoming_implementations,
    }
    
    return render(request, 'change_control/dashboard.html', context)


@login_required
def my_changes(request):
    """تغييراتي"""
    # التغييرات التي طلبتها
    requested = ChangeControl.objects.filter(requester=request.user)
    
    # التغييرات التي أملكها
    owned = ChangeControl.objects.filter(change_owner=request.user)
    
    # التغييرات التي أنسقها
    coordinated = ChangeControl.objects.filter(change_coordinator=request.user)
    
    # الموافقات المعلقة
    pending_approvals = ChangeApproval.objects.filter(
        approver=request.user,
        status='pending'
    ).select_related('change_control')
    
    # المهام المعينة لي
    my_tasks = ChangeTask.objects.filter(
        assigned_to=request.user,
        status__in=['pending', 'in_progress']
    ).select_related('implementation_plan__change_control')
    
    context = {
        'requested': requested.order_by('-submission_date')[:10],
        'owned': owned.order_by('-submission_date')[:10],
        'coordinated': coordinated.order_by('-submission_date')[:10],
        'pending_approvals': pending_approvals,
        'my_tasks': my_tasks,
    }
    
    return render(request, 'change_control/my_changes.html', context)


@login_required
def change_create(request):
    """إنشاء طلب تغيير جديد"""
    if request.method == 'POST':
        form = ChangeControlCreateForm(request.POST)
        if form.is_valid():
            change = form.save(commit=False)
            change.requester = request.user
            change.created_by = request.user
            change.save()
            form.save_m2m()  # حفظ العلاقات many-to-many
            
            # إنشاء سجل تدقيق
            create_audit_log(
                request.user, 'create', request,
                model_name='ChangeControl',
                object_id=change.id,
                object_repr=str(change)
            )
            
            messages.success(request, _('Change request created successfully.'))
            return redirect('change_control:detail', pk=change.pk)
    else:
        form = ChangeControlCreateForm()
    
    return render(request, 'change_control/change_create.html', {
        'form': form,
    })


@login_required
def change_detail(request, pk):
    """تفاصيل التغيير"""
    change = get_object_or_404(
        ChangeControl.objects.select_related(
            'requester', 'change_owner', 'change_coordinator'
        ).prefetch_related(
            'affected_products', 'related_documents', 'related_deviations',
            'related_capas', 'approvals__approver', 'attachments'
        ),
        pk=pk
    )
    
    # فحص الصلاحيات
    can_edit = (
        request.user == change.requester or 
        request.user == change.change_owner or
        request.user == change.change_coordinator or
        request.user.has_perm('change_control.change_changecontrol')
    )
    
    # الموافقات
    approvals = change.approvals.all().order_by('approval_type')
    
    # المرفقات
    attachments = change.attachments.all().order_by('-uploaded_date')
    
    # خطة التنفيذ والمهام
    implementation_plan = getattr(change, 'implementation_plan', None)
    tasks = []
    if implementation_plan:
        tasks = implementation_plan.tasks.all().order_by('task_number')
    
    # تقييم التأثير
    impact_assessment = getattr(change, 'impact_assessment', None)
    
    context = {
        'change': change,
        'can_edit': can_edit,
        'approvals': approvals,
        'attachments': attachments,
        'implementation_plan': implementation_plan,
        'tasks': tasks,
        'impact_assessment': impact_assessment,
    }
    
    return render(request, 'change_control/change_detail.html', context)


@login_required
def change_edit(request, pk):
    """تعديل التغيير"""
    change = get_object_or_404(ChangeControl, pk=pk)
    
    # فحص الصلاحيات
    if not (request.user == change.requester or 
            request.user == change.change_owner or
            request.user.has_perm('change_control.change_changecontrol')):
        messages.error(request, _('You do not have permission to edit this change.'))
        return redirect('change_control:detail', pk=pk)
    
    # فحص إذا كان التغيير قابل للتعديل
    if change.status not in ['draft', 'submitted']:
        messages.error(request, _('This change cannot be edited in its current status.'))
        return redirect('change_control:detail', pk=pk)
    
    if request.method == 'POST':
        form = ChangeControlEditForm(request.POST, instance=change)
        if form.is_valid():
            form.save()
            
            # سجل التدقيق
            create_audit_log(
                request.user, 'update', request,
                model_name='ChangeControl',
                object_id=change.id,
                object_repr=str(change)
            )
            
            messages.success(request, _('Change updated successfully.'))
            return redirect('change_control:detail', pk=pk)
    else:
        form = ChangeControlEditForm(instance=change)
    
    return render(request, 'change_control/change_edit.html', {
        'form': form,
        'change': change,
    })


@login_required
@require_POST
def change_submit(request, pk):
    """تقديم طلب التغيير للمراجعة"""
    change = get_object_or_404(ChangeControl, pk=pk)
    
    # فحص الصلاحيات
    if not (request.user == change.requester or 
            request.user == change.change_owner or
            request.user.has_perm('change_control.change_changecontrol')):
        messages.error(request, _('You do not have permission to submit this change.'))
        return redirect('change_control:detail', pk=pk)
    
    if change.status != 'draft':
        messages.error(request, _('Only draft changes can be submitted.'))
        return redirect('change_control:detail', pk=pk)
    
    with transaction.atomic():
        # تحديث الحالة
        change.status = 'submitted'
        change.submission_date = timezone.now()
        change.save()
        
        # إنشاء موافقات مطلوبة
        approvers = []
        
        # موافقة مراجعة التغيير (مدير الجودة)
        quality_managers = User.objects.filter(groups__name='Quality Manager')
        for manager in quality_managers:
            ChangeApproval.objects.create(
                change_control=change,
                approval_type='change_review',
                approver=manager,
                due_date=timezone.now() + timedelta(days=5)
            )
        
        # إضافة موافقات إضافية حسب نوع التغيير
        if change.requires_regulatory_approval:
            regulatory_managers = User.objects.filter(groups__name='Regulatory Affairs')
            for manager in regulatory_managers:
                ChangeApproval.objects.create(
                    change_control=change,
                    approval_type='change_review',
                    approver=manager,
                    due_date=timezone.now() + timedelta(days=7)
                )
        
        # سجل التدقيق
        create_audit_log(
            request.user, 'submit', request,
            model_name='ChangeControl',
            object_id=change.id,
            object_repr=str(change)
        )
    
    messages.success(request, _('Change submitted for review successfully.'))
    return redirect('change_control:detail', pk=pk)


@login_required
def impact_assessment_create(request, pk):
    """إنشاء تقييم التأثير"""
    change = get_object_or_404(ChangeControl, pk=pk)
    
    # فحص وجود تقييم تأثير مسبقاً
    if hasattr(change, 'impact_assessment'):
        messages.info(request, _('Impact assessment already exists.'))
        return redirect('change_control:impact_assessment_view', pk=pk)
    
    # فحص الصلاحيات
    if not (request.user == change.change_owner or
            request.user.has_perm('change_control.add_changeimpactassessment')):
        messages.error(request, _('You do not have permission to create impact assessment.'))
        return redirect('change_control:detail', pk=pk)
    
    if request.method == 'POST':
        form = ChangeImpactAssessmentForm(request.POST)
        if form.is_valid():
            assessment = form.save(commit=False)
            assessment.change_control = change
            assessment.assessed_by = request.user
            assessment.save()
            
            # تحديث حالة التغيير
            if change.status == 'submitted':
                change.status = 'impact_assessment'
                change.save()
            
            messages.success(request, _('Impact assessment created successfully.'))
            return redirect('change_control:detail', pk=pk)
    else:
        form = ChangeImpactAssessmentForm()
    
    return render(request, 'change_control/impact_assessment_create.html', {
        'form': form,
        'change': change,
    })


@login_required
def implementation_plan_create(request, pk):
    """إنشاء خطة التنفيذ"""
    change = get_object_or_404(ChangeControl, pk=pk)
    
    # فحص وجود خطة تنفيذ مسبقاً
    if hasattr(change, 'implementation_plan'):
        messages.info(request, _('Implementation plan already exists.'))
        return redirect('change_control:detail', pk=pk)
    
    # فحص الصلاحيات
    if not (request.user == change.change_owner or
            request.user.has_perm('change_control.add_changeimplementationplan')):
        messages.error(request, _('You do not have permission to create implementation plan.'))
        return redirect('change_control:detail', pk=pk)
    
    if request.method == 'POST':
        form = ChangeImplementationPlanForm(request.POST)
        if form.is_valid():
            plan = form.save(commit=False)
            plan.change_control = change
            plan.created_by = request.user
            plan.save()
            
            # تحديث حالة التغيير
            if change.status in ['approved', 'impact_assessment']:
                change.status = 'implementation_planning'
                change.save()
            
            messages.success(request, _('Implementation plan created successfully.'))
            return redirect('change_control:detail', pk=pk)
    else:
        form = ChangeImplementationPlanForm()
    
    return render(request, 'change_control/implementation_plan_create.html', {
        'form': form,
        'change': change,
    })


@login_required
def task_create(request, pk):
    """إنشاء مهمة تنفيذ"""
    change = get_object_or_404(ChangeControl, pk=pk)
    
    if not hasattr(change, 'implementation_plan'):
        messages.error(request, _('Implementation plan must be created first.'))
        return redirect('change_control:detail', pk=pk)
    
    plan = change.implementation_plan
    
    if request.method == 'POST':
        form = ChangeTaskForm(request.POST, implementation_plan=plan)
        if form.is_valid():
            task = form.save(commit=False)
            task.implementation_plan = plan
            
            # توليد رقم المهمة
            last_task = plan.tasks.order_by('-task_number').first()
            if last_task:
                last_num = int(last_task.task_number[1:])  # إزالة T
                next_num = last_num + 1
            else:
                next_num = 1
            task.task_number = f'T{next_num:03d}'
            
            task.save()
            form.save_m2m()  # حفظ التبعيات
            
            messages.success(request, _('Task created successfully.'))
            return redirect('change_control:task_list', pk=pk)
    else:
        form = ChangeTaskForm(implementation_plan=plan)
    
    return render(request, 'change_control/task_create.html', {
        'form': form,
        'change': change,
        'plan': plan,
    })


@login_required
def task_list(request, pk):
    """قائمة مهام التنفيذ"""
    change = get_object_or_404(ChangeControl, pk=pk)
    
    if not hasattr(change, 'implementation_plan'):
        messages.error(request, _('Implementation plan does not exist.'))
        return redirect('change_control:detail', pk=pk)
    
    plan = change.implementation_plan
    tasks = plan.tasks.all().order_by('task_number')
    
    # إحصائيات المهام
    task_stats = {
        'total': tasks.count(),
        'pending': tasks.filter(status='pending').count(),
        'in_progress': tasks.filter(status='in_progress').count(),
        'completed': tasks.filter(status='completed').count(),
        'verified': tasks.filter(status='verified').count(),
        'overdue': sum(1 for task in tasks if task.is_overdue),
    }
    
    return render(request, 'change_control/task_list.html', {
        'change': change,
        'plan': plan,
        'tasks': tasks,
        'task_stats': task_stats,
    })


@login_required
@require_POST
def task_update_status(request, task_id):
    """تحديث حالة المهمة"""
    task = get_object_or_404(ChangeTask, id=task_id)
    new_status = request.POST.get('status')
    
    if new_status not in [choice[0] for choice in ChangeTask.STATUS_CHOICES]:
        return JsonResponse({'success': False, 'error': 'Invalid status'})
    
    # فحص الصلاحيات
    if not (request.user == task.assigned_to or
            request.user.has_perm('change_control.change_changetask')):
        return JsonResponse({'success': False, 'error': 'Permission denied'})
    
    # فحص إذا كان يمكن تحديث الحالة
    if new_status == 'in_progress' and not task.can_start:
        return JsonResponse({
            'success': False, 
            'error': 'Cannot start task due to pending dependencies'
        })
    
    task.status = new_status
    if new_status == 'completed':
        task.completion_date = timezone.now()
        task.progress_percentage = 100
    elif new_status == 'in_progress':
        task.progress_percentage = max(task.progress_percentage, 10)
    
    task.save()
    
    return JsonResponse({'success': True, 'status': new_status})


@login_required
def change_approve(request, pk):
    """صفحة الموافقة على التغيير"""
    change = get_object_or_404(ChangeControl, pk=pk)
    
    # البحث عن الموافقات المعلقة للمستخدم الحالي
    pending_approvals = change.approvals.filter(
        approver=request.user,
        status='pending'
    )
    
    if not pending_approvals.exists():
        messages.error(request, _('You do not have pending approvals for this change.'))
        return redirect('change_control:detail', pk=pk)
    
    return render(request, 'change_control/change_approve.html', {
        'change': change,
        'pending_approvals': pending_approvals,
    })


@login_required
@require_POST
def approval_action(request, approval_id):
    """تنفيذ إجراء الموافقة"""
    approval = get_object_or_404(ChangeApproval, id=approval_id)
    
    # فحص الصلاحيات
    if request.user != approval.approver:
        messages.error(request, _('You are not authorized to act on this approval.'))
        return redirect('change_control:detail', pk=approval.change_control.pk)
    
    if approval.status != 'pending':
        messages.error(request, _('This approval has already been processed.'))
        return redirect('change_control:detail', pk=approval.change_control.pk)
    
    form = ChangeApprovalActionForm(request.POST)
    if form.is_valid():
        approval.status = form.cleaned_data['action']
        approval.comments = form.cleaned_data['comments']
        approval.approval_date = timezone.now()
        approval.save()
        
        # تحديث حالة التغيير
        change = approval.change_control
        if approval.status == 'approved':
            # فحص إذا كانت كل الموافقات المطلوبة تمت
            pending_approvals = change.approvals.filter(status='pending')
            if not pending_approvals.exists():
                change.status = 'approved'
                change.save()
        elif approval.status == 'rejected':
            change.status = 'rejected'
            change.save()
        
        messages.success(request, _('Approval action completed successfully.'))
    else:
        messages.error(request, _('Invalid form data.'))
    
    return redirect('change_control:detail', pk=approval.change_control.pk)


@login_required
def change_calendar(request):
    """تقويم التغييرات"""
    # الحصول على التغييرات مع تواريخ التنفيذ
    changes = ChangeControl.objects.filter(
        target_implementation_date__isnull=False
    ).select_related('requester', 'change_owner')
    
    return render(request, 'change_control/change_calendar.html', {
        'changes': changes,
    })


@login_required
def calendar_data(request):
    """بيانات التقويم لعرض التغييرات"""
    changes = ChangeControl.objects.filter(
        target_implementation_date__isnull=False
    ).select_related('requester', 'change_owner')
    
    events = []
    for change in changes:
        color = {
            'draft': '#6c757d',
            'submitted': '#17a2b8',
            'approved': '#28a745',
            'in_progress': '#ffc107',
            'completed': '#6f42c1',
            'rejected': '#dc3545',
        }.get(change.status, '#6c757d')
        
        events.append({
            'id': change.id,
            'title': f"{change.change_number} - {change.title}",
            'start': change.target_implementation_date.isoformat(),
            'backgroundColor': color,
            'borderColor': color,
            'url': f"/change-control/{change.id}/",
        })
    
    return JsonResponse(events, safe=False)


@login_required
def change_statistics(request):
    """إحصائيات التغييرات"""
    # إحصائيات عامة
    total_changes = ChangeControl.objects.count()
    
    # إحصائيات حسب الحالة
    status_stats = {}
    for status, label in ChangeControl.STATUS_CHOICES:
        status_stats[status] = ChangeControl.objects.filter(status=status).count()
    
    # إحصائيات حسب النوع
    type_stats = {}
    for change_type, label in ChangeControl.CHANGE_TYPES:
        type_stats[change_type] = ChangeControl.objects.filter(change_type=change_type).count()
    
    # إحصائيات حسب الفئة
    category_stats = {}
    for category, label in ChangeControl.CHANGE_CATEGORIES:
        category_stats[category] = ChangeControl.objects.filter(change_category=category).count()
    
    # إحصائيات شهرية
    monthly_stats = []
    for i in range(12):
        month_start = timezone.now().replace(month=i+1, day=1, hour=0, minute=0, second=0, microsecond=0)
        if i == 11:  # ديسمبر
            month_end = month_start.replace(year=month_start.year + 1, month=1)
        else:
            month_end = month_start.replace(month=i+2)
        
        month_changes = ChangeControl.objects.filter(
            submission_date__gte=month_start,
            submission_date__lt=month_end
        ).count()
        
        monthly_stats.append({
            'month': calendar.month_name[i+1],
            'count': month_changes
        })
    
    context = {
        'total_changes': total_changes,
        'status_stats': status_stats,
        'type_stats': type_stats,
        'category_stats': category_stats,
        'monthly_stats': monthly_stats,
    }
    
    return render(request, 'change_control/statistics.html', context)


@login_required
def change_chart_data(request):
    """بيانات المخططات للتغييرات"""
    chart_type = request.GET.get('type', 'status')
    
    if chart_type == 'status':
        data = []
        for status, label in ChangeControl.STATUS_CHOICES:
            count = ChangeControl.objects.filter(status=status).count()
            if count > 0:
                data.append({
                    'label': str(label),
                    'value': count
                })
        return JsonResponse(data, safe=False)
    
    elif chart_type == 'monthly':
        data = []
        for i in range(12):
            month_start = timezone.now().replace(month=i+1, day=1)
            if i == 11:
                month_end = month_start.replace(year=month_start.year + 1, month=1)
            else:
                month_end = month_start.replace(month=i+2)
            
            count = ChangeControl.objects.filter(
                submission_date__gte=month_start,
                submission_date__lt=month_end
            ).count()
            
            data.append({
                'month': calendar.month_name[i+1],
                'count': count
            })
        return JsonResponse(data, safe=False)
    
    return JsonResponse([], safe=False)


# دوال إضافية للمرفقات والتقارير
@login_required
def attachment_upload(request, pk):
    """رفع مرفق"""
    change = get_object_or_404(ChangeControl, pk=pk)
    
    if request.method == 'POST':
        form = ChangeAttachmentForm(request.POST, request.FILES)
        if form.is_valid():
            attachment = form.save(commit=False)
            attachment.change_control = change
            attachment.uploaded_by = request.user
            attachment.save()
            
            messages.success(request, _('Attachment uploaded successfully.'))
            return redirect('change_control:detail', pk=pk)
    else:
        form = ChangeAttachmentForm()
    
    return render(request, 'change_control/attachment_upload.html', {
        'form': form,
        'change': change,
    })


@login_required
def attachment_download(request, attachment_id):
    """تحميل مرفق"""
    attachment = get_object_or_404(ChangeAttachment, id=attachment_id)
    
    # إنشاء استجابة التحميل
    response = HttpResponse(attachment.file.read(), content_type='application/octet-stream')
    response['Content-Disposition'] = f'attachment; filename="{attachment.file.name}"'
    
    return response


@login_required
def change_reports(request):
    """تقارير التغييرات"""
    # تقرير التغييرات النشطة
    active_changes = ChangeControl.objects.filter(
        status__in=['submitted', 'under_review', 'approved', 'in_progress']
    ).count()
    
    # تقرير التغييرات المتأخرة
    overdue_count = 0
    all_changes = ChangeControl.objects.filter(
        status__in=['submitted', 'under_review', 'approved', 'in_progress']
    )
    for change in all_changes:
        if change.is_overdue:
            overdue_count += 1
    
    # تقرير متوسط وقت التنفيذ
    completed_changes = ChangeControl.objects.filter(
        status='completed',
        submission_date__isnull=False,
        completion_date__isnull=False
    )
    
    total_days = 0
    if completed_changes.exists():
        for change in completed_changes:
            delta = change.completion_date.date() - change.submission_date.date()
            total_days += delta.days
        avg_implementation_time = total_days / completed_changes.count()
    else:
        avg_implementation_time = 0
    
    context = {
        'active_changes': active_changes,
        'overdue_count': overdue_count,
        'avg_implementation_time': round(avg_implementation_time, 1),
        'completed_changes_count': completed_changes.count(),
    }
    
    return render(request, 'change_control/reports.html', context)