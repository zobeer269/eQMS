from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.utils.translation import gettext as _
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.http import JsonResponse, HttpResponse
from .models import Deviation, DeviationInvestigation, DeviationApproval, DeviationAttachment, Product
from .forms import (
    DeviationCreateForm, DeviationInvestigationForm, DeviationUpdateForm,
    DeviationApprovalForm, DeviationCloseForm, DeviationAttachmentForm,
    DeviationSearchForm
)
from accounts.models import AuditLog


@login_required
def deviation_dashboard(request):
    """لوحة تحكم الانحرافات"""
    # إحصائيات عامة
    total_deviations = Deviation.objects.count()
    open_deviations = Deviation.objects.filter(status='open').count()
    under_investigation = Deviation.objects.filter(status='under_investigation').count()
    overdue_deviations = Deviation.objects.filter(
        status__in=['open', 'under_investigation'],
        reported_date__lt=timezone.now() - timezone.timedelta(days=30)
    ).count()
    
    # إحصائيات حسب الشدة
    critical_count = Deviation.objects.filter(severity='critical', status__in=['open', 'under_investigation']).count()
    major_count = Deviation.objects.filter(severity='major', status__in=['open', 'under_investigation']).count()
    minor_count = Deviation.objects.filter(severity='minor', status__in=['open', 'under_investigation']).count()
    
    # الانحرافات الأخيرة
    recent_deviations = Deviation.objects.select_related('reported_by', 'assigned_to').order_by('-reported_date')[:10]
    
    # الانحرافات المتكررة
    recurring_deviations = Deviation.objects.filter(is_recurring=True, status__in=['open', 'under_investigation'])
    
    # الانحرافات التي تحتاج موافقات
    pending_approvals = DeviationApproval.objects.filter(
        approver=request.user,
        status='pending'
    ).select_related('deviation')
    
    context = {
        'total_deviations': total_deviations,
        'open_deviations': open_deviations,
        'under_investigation': under_investigation,
        'overdue_deviations': overdue_deviations,
        'critical_count': critical_count,
        'major_count': major_count,
        'minor_count': minor_count,
        'recent_deviations': recent_deviations,
        'recurring_deviations': recurring_deviations,
        'pending_approvals': pending_approvals,
    }
    
    return render(request, 'deviations/dashboard.html', context)


@login_required
def deviation_list(request):
    """قائمة الانحرافات"""
    form = DeviationSearchForm(request.GET or None)
    
    deviations = Deviation.objects.select_related('reported_by', 'assigned_to', 'qa_reviewer')
    
    # البحث والفلترة
    if form.is_valid():
        if form.cleaned_data.get('search'):
            search_term = form.cleaned_data['search']
            deviations = deviations.filter(
                Q(deviation_number__icontains=search_term) |
                Q(title__icontains=search_term) |
                Q(description__icontains=search_term)
            )
        
        if form.cleaned_data.get('deviation_type'):
            deviations = deviations.filter(deviation_type=form.cleaned_data['deviation_type'])
        
        if form.cleaned_data.get('severity'):
            deviations = deviations.filter(severity=form.cleaned_data['severity'])
        
        if form.cleaned_data.get('status'):
            deviations = deviations.filter(status=form.cleaned_data['status'])
        
        if form.cleaned_data.get('department'):
            deviations = deviations.filter(department=form.cleaned_data['department'])
        
        if form.cleaned_data.get('date_from'):
            deviations = deviations.filter(reported_date__gte=form.cleaned_data['date_from'])
        
        if form.cleaned_data.get('date_to'):
            deviations = deviations.filter(reported_date__lte=form.cleaned_data['date_to'])
        
        if form.cleaned_data.get('is_overdue'):
            deviations = [d for d in deviations if d.is_overdue]
        
        if form.cleaned_data.get('requires_capa'):
            deviations = deviations.filter(requires_capa=True)
    
    deviations = deviations.order_by('-reported_date')
    
    paginator = Paginator(deviations, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'form': form,
        'page_obj': page_obj,
        'deviations': page_obj,
    }
    
    return render(request, 'deviations/deviation_list.html', context)


@login_required
def deviation_create(request):
    """إنشاء انحراف جديد"""
    if request.method == 'POST':
        form = DeviationCreateForm(request.POST, user=request.user)
        if form.is_valid():
            deviation = form.save(commit=False)
            deviation.reported_by = request.user
            deviation.save()
            form.save_m2m()
            
            # سجل التدقيق
            AuditLog.objects.create(
                user=request.user,
                action='create',
                model_name='Deviation',
                object_id=deviation.id,
                object_repr=str(deviation),
                timestamp=timezone.now(),
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            messages.success(request, _('Deviation created successfully.'))
            return redirect('deviations:detail', pk=deviation.pk)
    else:
        form = DeviationCreateForm(user=request.user)
    
    return render(request, 'deviations/deviation_form.html', {
        'form': form,
        'title': _('Report New Deviation')
    })


@login_required
def deviation_detail(request, pk):
    """عرض تفاصيل الانحراف"""
    deviation = get_object_or_404(Deviation, pk=pk)
    
    # التحقق من الصلاحيات
    can_edit = (
        request.user == deviation.reported_by or
        request.user == deviation.assigned_to or
        request.user.has_perm('deviations.change_deviation')
    )
    
    can_investigate = (
        request.user == deviation.qa_reviewer or
        request.user.has_perm('deviations.can_assign_deviation')
    )
    
    can_approve = request.user.has_perm('deviations.can_approve_deviation')
    can_close = request.user.has_perm('deviations.can_close_deviation')
    
    # جلب البيانات المرتبطة
    investigation = hasattr(deviation, 'investigation') and deviation.investigation
    approvals = deviation.approvals.select_related('approver').order_by('-requested_date')
    attachments = deviation.attachments.select_related('uploaded_by').order_by('-uploaded_date')
    
    # التحقق من الموافقات المعلقة
    pending_approval = deviation.approvals.filter(
        approver=request.user,
        status='pending'
    ).first()
    
    context = {
        'deviation': deviation,
        'can_edit': can_edit,
        'can_investigate': can_investigate,
        'can_approve': can_approve,
        'can_close': can_close,
        'investigation': investigation,
        'approvals': approvals,
        'attachments': attachments,
        'pending_approval': pending_approval,
    }
    
    return render(request, 'deviations/deviation_detail.html', context)


@login_required
def deviation_edit(request, pk):
    """تحديث الانحراف"""
    deviation = get_object_or_404(Deviation, pk=pk)
    
    # التحقق من الصلاحيات
    if not (request.user == deviation.reported_by or 
            request.user == deviation.assigned_to or
            request.user.has_perm('deviations.change_deviation')):
        messages.error(request, _('You do not have permission to edit this deviation.'))
        return redirect('deviations:detail', pk=pk)
    
    if request.method == 'POST':
        form = DeviationUpdateForm(request.POST, instance=deviation)
        if form.is_valid():
            form.save()
            
            # سجل التدقيق
            AuditLog.objects.create(
                user=request.user,
                action='update',
                model_name='Deviation',
                object_id=deviation.id,
                object_repr=str(deviation),
                timestamp=timezone.now(),
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            messages.success(request, _('Deviation updated successfully.'))
            return redirect('deviations:detail', pk=pk)
    else:
        form = DeviationUpdateForm(instance=deviation)
    
    return render(request, 'deviations/deviation_form.html', {
        'form': form,
        'deviation': deviation,
        'title': _('Edit Deviation')
    })


@login_required
def deviation_investigate(request, pk):
    """إنشاء/تحديث التحقيق في الانحراف"""
    deviation = get_object_or_404(Deviation, pk=pk)
    
    # التحقق من الصلاحيات
    if not (request.user == deviation.qa_reviewer or
            request.user.has_perm('deviations.can_assign_deviation')):
        messages.error(request, _('You do not have permission to investigate this deviation.'))
        return redirect('deviations:detail', pk=pk)
    
    investigation = hasattr(deviation, 'investigation') and deviation.investigation
    
    if request.method == 'POST':
        form = DeviationInvestigationForm(
            request.POST, 
            instance=investigation,
            deviation=deviation
        )
        if form.is_valid():
            investigation = form.save(commit=False)
            investigation.deviation = deviation
            investigation.save()
            form.save_m2m()
            
            # تحديث حالة الانحراف
            deviation.status = 'under_investigation'
            deviation.save()
            
            messages.success(request, _('Investigation saved successfully.'))
            return redirect('deviations:detail', pk=pk)
    else:
        form = DeviationInvestigationForm(
            instance=investigation,
            deviation=deviation
        )
    
    return render(request, 'deviations/investigation_form.html', {
        'form': form,
        'deviation': deviation,
        'title': _('Deviation Investigation')
    })


@login_required
def deviation_approve(request, pk):
    """الموافقة على الانحراف"""
    deviation = get_object_or_404(Deviation, pk=pk)
    
    # التحقق من وجود موافقة معلقة
    approval = deviation.approvals.filter(
        approver=request.user,
        status='pending'
    ).first()
    
    if not approval:
        messages.error(request, _('No pending approval found for this deviation.'))
        return redirect('deviations:detail', pk=pk)
    
    if request.method == 'POST':
        form = DeviationApprovalForm(request.POST, request.FILES)
        if form.is_valid():
            action = form.cleaned_data['action']
            
            # التحقق من كلمة المرور
            if not request.user.check_password(form.cleaned_data['electronic_signature']):
                messages.error(request, _('Invalid electronic signature.'))
                return render(request, 'deviations/deviation_approve.html', {
                    'form': form,
                    'deviation': deviation,
                    'approval': approval
                })
            
            # تحديث الموافقة
            approval.status = 'approved' if action == 'approve' else 'rejected'
            approval.action_date = timezone.now()
            approval.comments = form.cleaned_data['comments']
            approval.electronic_signature = request.user.electronic_signature
            approval.signature_meaning = _('I approve this deviation') if action == 'approve' else _('I reject this deviation')
            approval.save()
            
            # تحديث حالة الانحراف إذا لزم الأمر
            if action == 'approve' and approval.approval_type == 'closure':
                deviation.status = 'closed'
                deviation.closed_date = timezone.now()
                deviation.save()
            
            messages.success(request, _('Approval action completed successfully.'))
            return redirect('deviations:detail', pk=pk)
    else:
        form = DeviationApprovalForm()
    
    return render(request, 'deviations/deviation_approve.html', {
        'form': form,
        'deviation': deviation,
        'approval': approval
    })


@login_required
def deviation_close(request, pk):
    """إغلاق الانحراف"""
    deviation = get_object_or_404(Deviation, pk=pk)
    
    # التحقق من الصلاحيات
    if not request.user.has_perm('deviations.can_close_deviation'):
        messages.error(request, _('You do not have permission to close this deviation.'))
        return redirect('deviations:detail', pk=pk)
    
    if request.method == 'POST':
        form = DeviationCloseForm(request.POST)
        if form.is_valid():
            # التحقق من كلمة المرور
            if not request.user.check_password(form.cleaned_data['electronic_signature']):
                messages.error(request, _('Invalid electronic signature.'))
                return render(request, 'deviations/deviation_close.html', {
                    'form': form,
                    'deviation': deviation
                })
            
            # إنشاء موافقة الإغلاق
            DeviationApproval.objects.create(
                deviation=deviation,
                approval_type='closure',
                approver=request.user,
                approval_role='qa_manager',
                status='approved',
                action_date=timezone.now(),
                comments=form.cleaned_data['closure_summary'],
                electronic_signature=request.user.electronic_signature,
                signature_meaning=_('I approve the closure of this deviation')
            )
            
            # تحديث الانحراف
            deviation.status = 'closed'
            deviation.closed_date = timezone.now()
            deviation.save()
            
            messages.success(request, _('Deviation closed successfully.'))
            return redirect('deviations:detail', pk=pk)
    else:
        form = DeviationCloseForm()
    
    return render(request, 'deviations/deviation_close.html', {
        'form': form,
        'deviation': deviation
    })


@login_required
def my_deviations(request):
    """الانحرافات الخاصة بي"""
    # الانحرافات التي أبلغت عنها
    reported = Deviation.objects.filter(reported_by=request.user).order_by('-reported_date')
    
    # الانحرافات المخصصة لي
    assigned = Deviation.objects.filter(assigned_to=request.user).exclude(status='closed').order_by('-reported_date')
    
    # الانحرافات التي أراجعها
    reviewing = Deviation.objects.filter(qa_reviewer=request.user).exclude(status='closed').order_by('-reported_date')
    
    # الموافقات المعلقة
    pending_approvals = DeviationApproval.objects.filter(
        approver=request.user,
        status='pending'
    ).select_related('deviation').order_by('-requested_date')
    
    context = {
        'reported': reported,
        'assigned': assigned,
        'reviewing': reviewing,
        'pending_approvals': pending_approvals,
    }
    
    return render(request, 'deviations/my_deviations.html', context)


@login_required
def create_capa(request, pk):
    """إنشاء CAPA من الانحراف"""
    deviation = get_object_or_404(Deviation, pk=pk)
    
    if deviation.related_capa:
        messages.info(request, _('CAPA already created for this deviation.'))
        return redirect('capa:detail', pk=deviation.related_capa.pk)
    
    # الانتقال إلى صفحة إنشاء CAPA مع البيانات المعبأة مسبقاً
    return redirect(f"/capa/create/?source_type=deviation&source_ref={deviation.deviation_number}")


@login_required
def create_change_control(request, pk):
    """إنشاء Change Control من الانحراف"""
    deviation = get_object_or_404(Deviation, pk=pk)
    
    if deviation.related_change_control:
        messages.info(request, _('Change Control already created for this deviation.'))
        return redirect('change_control:detail', pk=deviation.related_change_control.pk)
    
    # الانتقال إلى صفحة إنشاء Change Control
    return redirect(f"/change-control/create/?source_type=deviation&source_ref={deviation.deviation_number}")


@login_required
def deviation_print(request, pk):
    """طباعة تقرير الانحراف"""
    deviation = get_object_or_404(Deviation, pk=pk)
    
    # سجل التدقيق
    AuditLog.objects.create(
        user=request.user,
        action='print',
        model_name='Deviation',
        object_id=deviation.id,
        object_repr=str(deviation),
        timestamp=timezone.now(),
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )
    
    context = {
        'deviation': deviation,
        'investigation': hasattr(deviation, 'investigation') and deviation.investigation,
        'approvals': deviation.approvals.all(),
        'attachments': deviation.attachments.all(),
    }
    
    return render(request, 'deviations/deviation_print.html', context)


# Views للمرفقات
@login_required
def attachment_list(request, pk):
    """قائمة مرفقات الانحراف"""
    deviation = get_object_or_404(Deviation, pk=pk)
    attachments = deviation.attachments.select_related('uploaded_by').order_by('-uploaded_date')
    
    return render(request, 'deviations/attachment_list.html', {
        'deviation': deviation,
        'attachments': attachments,
    })


@login_required
def attachment_upload(request, pk):
    """رفع مرفق جديد"""
    deviation = get_object_or_404(Deviation, pk=pk)
    
    if request.method == 'POST':
        form = DeviationAttachmentForm(request.POST, request.FILES)
        if form.is_valid():
            attachment = form.save(commit=False)
            attachment.deviation = deviation
            attachment.uploaded_by = request.user
            attachment.save()
            
            messages.success(request, _('Attachment uploaded successfully.'))
            return redirect('deviations:detail', pk=pk)
    else:
        form = DeviationAttachmentForm()
    
    return render(request, 'deviations/attachment_form.html', {
        'form': form,
        'deviation': deviation,
    })


@login_required
def attachment_download(request, attachment_id):
    """تحميل المرفق"""
    attachment = get_object_or_404(DeviationAttachment, pk=attachment_id)
    
    # سجل التدقيق
    AuditLog.objects.create(
        user=request.user,
        action='download',
        model_name='DeviationAttachment',
        object_id=attachment.id,
        object_repr=str(attachment),
        timestamp=timezone.now(),
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )
    
    response = HttpResponse(attachment.file.read(), content_type='application/octet-stream')
    response['Content-Disposition'] = f'attachment; filename="{attachment.file.name}"'
    return response


@login_required
def attachment_delete(request, attachment_id):
    """حذف المرفق"""
    attachment = get_object_or_404(DeviationAttachment, pk=attachment_id)
    deviation_pk = attachment.deviation.pk
    
    # التحقق من الصلاحيات
    if not (request.user == attachment.uploaded_by or request.user.has_perm('deviations.delete_deviationattachment')):
        messages.error(request, _('You do not have permission to delete this attachment.'))
        return redirect('deviations:detail', pk=deviation_pk)
    
    if request.method == 'POST':
        attachment.delete()
        messages.success(request, _('Attachment deleted successfully.'))
    
    return redirect('deviations:detail', pk=deviation_pk)


# التقارير والإحصائيات
@login_required
def deviation_reports(request):
    """صفحة التقارير"""
    return render(request, 'deviations/reports.html')


@login_required
def deviation_statistics(request):
    """إحصائيات الانحرافات"""
    # إحصائيات حسب النوع
    by_type = Deviation.objects.values('deviation_type').annotate(count=Count('id'))
    
    # إحصائيات حسب الشدة
    by_severity = Deviation.objects.values('severity').annotate(count=Count('id'))
    
    # إحصائيات حسب القسم
    by_department = Deviation.objects.values('department').annotate(count=Count('id'))
    
    # الاتجاهات الشهرية
    from django.db.models.functions import TruncMonth
    monthly_trends = Deviation.objects.annotate(
        month=TruncMonth('reported_date')
    ).values('month').annotate(count=Count('id')).order_by('month')
    
    context = {
        'by_type': by_type,
        'by_severity': by_severity,
        'by_department': by_department,
        'monthly_trends': monthly_trends,
    }
    
    return render(request, 'deviations/statistics.html', context)


@login_required
def trend_analysis(request):
    """تحليل الاتجاهات"""
    # تحليل الانحرافات المتكررة
    recurring_analysis = Deviation.objects.filter(is_recurring=True).values(
        'deviation_type', 'department'
    ).annotate(count=Count('id')).order_by('-count')
    
    # تحليل أوقات الإغلاق
    closed_deviations = Deviation.objects.filter(status='closed', closed_date__isnull=False)
    
    context = {
        'recurring_analysis': recurring_analysis,
        'closed_deviations': closed_deviations,
    }
    
    return render(request, 'deviations/trend_analysis.html', context)


# API endpoints
def search_products(request):
    """البحث في المنتجات (للاستخدام في الاختيار التلقائي)"""
    query = request.GET.get('q', '')
    products = Product.objects.filter(
        Q(product_code__icontains=query) |
        Q(product_name__icontains=query) |
        Q(product_name_en__icontains=query),
        is_active=True
    )[:10]
    
    results = [{
        'id': p.id,
        'text': f"{p.product_code} - {p.product_name}",
        'code': p.product_code,
        'name': p.product_name
    } for p in products]
    
    return JsonResponse({'results': results})


def deviation_chart_data(request):
    """بيانات الرسوم البيانية"""
    # بيانات للرسوم البيانية
    data = {
        'by_type': list(Deviation.objects.values('deviation_type').annotate(count=Count('id'))),
        'by_severity': list(Deviation.objects.values('severity').annotate(count=Count('id'))),
        'by_status': list(Deviation.objects.values('status').annotate(count=Count('id'))),
    }
    
    return JsonResponse(data)


# إضافة Views الإضافية
@login_required
def deviation_assign(request, pk):
    """تعيين مسؤول عن الانحراف"""
    deviation = get_object_or_404(Deviation, pk=pk)
    
    if not request.user.has_perm('deviations.can_assign_deviation'):
        messages.error(request, _('You do not have permission to assign this deviation.'))
        return redirect('deviations:detail', pk=pk)
    
    if request.method == 'POST':
        assigned_to_id = request.POST.get('assigned_to')
        qa_reviewer_id = request.POST.get('qa_reviewer')
        
        if assigned_to_id:
            deviation.assigned_to_id = assigned_to_id
        if qa_reviewer_id:
            deviation.qa_reviewer_id = qa_reviewer_id
        
        deviation.save()
        messages.success(request, _('Deviation assigned successfully.'))
        return redirect('deviations:detail', pk=pk)
    
    users = User.objects.filter(is_active=True)
    qa_users = users.filter(is_quality_manager=True)
    
    return render(request, 'deviations/deviation_assign.html', {
        'deviation': deviation,
        'users': users,
        'qa_users': qa_users,
    })


@login_required
def investigation_create(request, pk):
    """إنشاء تحقيق جديد"""
    deviation = get_object_or_404(Deviation, pk=pk)
    return deviation_investigate(request, pk)


@login_required
def investigation_edit(request, pk):
    """تحديث التحقيق"""
    deviation = get_object_or_404(Deviation, pk=pk)
    return deviation_investigate(request, pk)


@login_required
def investigation_complete(request, pk):
    """إكمال التحقيق"""
    deviation = get_object_or_404(Deviation, pk=pk)
    investigation = get_object_or_404(DeviationInvestigation, deviation=deviation)
    
    if request.method == 'POST':
        investigation.investigation_end_date = timezone.now()
        investigation.save()
        
        # تحديث حالة الانحراف
        deviation.status = 'pending_approval'
        deviation.save()
        
        # إنشاء طلب موافقة
        DeviationApproval.objects.create(
            deviation=deviation,
            approval_type='investigation',
            approver=deviation.qa_reviewer or request.user,
            approval_role='qa_manager',
            status='pending'
        )
        
        messages.success(request, _('Investigation completed and sent for approval.'))
        return redirect('deviations:detail', pk=pk)
    
    return render(request, 'deviations/investigation_complete.html', {
        'deviation': deviation,
        'investigation': investigation,
    })


@login_required
def approval_action(request, approval_id):
    """معالجة إجراء الموافقة"""
    approval = get_object_or_404(DeviationApproval, pk=approval_id)
    
    if approval.approver != request.user:
        messages.error(request, _('You are not authorized to process this approval.'))
        return redirect('deviations:detail', pk=approval.deviation.pk)
    
    return deviation_approve(request, approval.deviation.pk)