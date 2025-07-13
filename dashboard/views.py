# dashboard/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.db.models import Count, Q, Avg, Sum
from django.core.paginator import Paginator
from datetime import datetime, timedelta
import json
import calendar

from deviations.models import Deviation, DeviationTrendAnalysis
from capa.models import CAPA, CAPAEffectivenessCheck
from change_control.models import ChangeControl
from accounts.models import User
from core.integration import QMSIntegrationManager, QMSWorkflowEngine
from audit.utils import create_audit_log


@login_required
def integrated_dashboard(request):
    """لوحة التحكم المتكاملة الرئيسية"""
    
    # الحصول على بيانات التكامل
    integration_data = QMSIntegrationManager.get_integration_dashboard_data(request.user)
    
    # العناصر النشطة
    total_active_items = (
        integration_data['deviations']['open'] +
        integration_data['capas']['active'] +
        integration_data['changes']['active']
    )
    
    # العناصر المتأخرة
    overdue_items = (
        integration_data['deviations']['overdue'] +
        integration_data['capas']['overdue'] +
        integration_data['changes']['overdue']
    )
    
    # الموافقات المعلقة للمستخدم الحالي
    pending_approvals = get_pending_approvals_for_user(request.user)
    
    # العناصر المكتملة هذا الشهر
    current_month = timezone.now().replace(day=1)
    completed_this_month = get_completed_items_count(current_month)
    
    # العناصر الجديدة هذا الأسبوع
    week_ago = timezone.now() - timedelta(days=7)
    new_this_week = get_new_items_count(week_ago)
    
    # معدل الإنجاز مقارنة بالشهر الماضي
    last_month = (current_month - timedelta(days=1)).replace(day=1)
    completion_rate = calculate_completion_rate_change(current_month, last_month)
    
    # العناصر الحديثة لكل نظام
    recent_deviations = Deviation.objects.filter(
        status__in=['open', 'investigation']
    ).order_by('-reported_date')[:3]
    
    recent_capas = CAPA.objects.filter(
        status__in=['open', 'in_progress']
    ).order_by('-initiated_date')[:3]
    
    recent_changes = ChangeControl.objects.filter(
        status__in=['submitted', 'approved', 'in_progress']
    ).order_by('-submission_date')[:3]
    
    # الإجراءات ذات الأولوية
    priority_actions = get_priority_actions(request.user)
    
    # مقاييس الأداء
    performance_metrics = calculate_system_performance()
    
    context = {
        # المقاييس الأساسية
        'total_active_items': total_active_items,
        'overdue_items': overdue_items,
        'pending_approvals': len(pending_approvals),
        'completed_this_month': completed_this_month,
        'new_this_week': new_this_week,
        'completion_rate': completion_rate,
        
        # بيانات الأنظمة
        'deviations': integration_data['deviations'],
        'capas': integration_data['capas'],
        'changes': integration_data['changes'],
        'integration_metrics': integration_data['integration_metrics'],
        
        # العناصر الحديثة
        'recent_deviations': recent_deviations,
        'recent_capas': recent_capas,
        'recent_changes': recent_changes,
        
        # الإجراءات والتنبيهات
        'priority_actions': priority_actions,
        'pending_approvals_list': pending_approvals,
        
        # مقاييس الأداء
        'overall_performance': performance_metrics['overall'],
        'ontime_completion': performance_metrics['ontime'],
        'quality_score': performance_metrics['quality'],
        'integration_score': performance_metrics['integration'],
        'overall_performance_circumference': 339.292,  # 2 * π * 54
        'overall_performance_offset': 339.292 * (1 - performance_metrics['overall'] / 100),
    }
    
    return render(request, 'dashboard/integrated_dashboard.html', context)


@login_required
def qms_analytics(request):
    """صفحة التحليلات الشاملة"""
    
    # تحليل الاتجاهات الشهرية
    monthly_trends = calculate_monthly_trends()
    
    # تحليل الأداء حسب القسم
    department_performance = calculate_department_performance()
    
    # تحليل أنواع الانحرافات
    deviation_type_analysis = analyze_deviation_types()
    
    # تحليل فعالية CAPA
    capa_effectiveness_analysis = analyze_capa_effectiveness()
    
    # تحليل أوقات التنفيذ
    implementation_time_analysis = analyze_implementation_times()
    
    # توقعات الاتجاهات
    trend_predictions = predict_future_trends()
    
    context = {
        'monthly_trends': monthly_trends,
        'department_performance': department_performance,
        'deviation_type_analysis': deviation_type_analysis,
        'capa_effectiveness_analysis': capa_effectiveness_analysis,
        'implementation_time_analysis': implementation_time_analysis,
        'trend_predictions': trend_predictions,
    }
    
    return render(request, 'dashboard/qms_analytics.html', context)


@login_required
def system_health_monitor(request):
    """مراقب صحة النظام"""
    
    # فحص أداء كل نظام
    system_health = {
        'deviations': check_deviation_system_health(),
        'capas': check_capa_system_health(),
        'changes': check_change_system_health(),
        'integration': check_integration_health(),
    }
    
    # تحديد المشاكل والتحذيرات
    issues = identify_system_issues()
    warnings = identify_system_warnings()
    
    # مقاييس الأداء التفصيلية
    performance_details = get_detailed_performance_metrics()
    
    # حالة النسخ الاحتياطي
    backup_status = check_backup_status()
    
    # حالة التدقيق
    audit_status = check_audit_compliance()
    
    context = {
        'system_health': system_health,
        'issues': issues,
        'warnings': warnings,
        'performance_details': performance_details,
        'backup_status': backup_status,
        'audit_status': audit_status,
    }
    
    return render(request, 'dashboard/system_health.html', context)


@login_required
def qms_reports(request):
    """صفحة التقارير الشاملة"""
    
    # أنواع التقارير المتاحة
    available_reports = get_available_reports()
    
    # التقارير المحفوظة
    saved_reports = get_user_saved_reports(request.user)
    
    # التقارير المجدولة
    scheduled_reports = get_scheduled_reports(request.user)
    
    context = {
        'available_reports': available_reports,
        'saved_reports': saved_reports,
        'scheduled_reports': scheduled_reports,
    }
    
    return render(request, 'dashboard/qms_reports.html', context)


@login_required
def generate_executive_summary(request):
    """توليد ملخص تنفيذي"""
    
    # الفترة الزمنية
    period = request.GET.get('period', 'monthly')
    
    if period == 'weekly':
        start_date = timezone.now() - timedelta(days=7)
    elif period == 'quarterly':
        start_date = timezone.now() - timedelta(days=90)
    elif period == 'yearly':
        start_date = timezone.now() - timedelta(days=365)
    else:  # monthly
        start_date = timezone.now().replace(day=1)
    
    # جمع البيانات للفترة المحددة
    summary_data = compile_executive_summary_data(start_date, timezone.now())
    
    context = {
        'period': period,
        'start_date': start_date,
        'end_date': timezone.now(),
        'summary_data': summary_data,
    }
    
    return render(request, 'reports/executive_summary.html', context)


# دوال مساعدة

def get_pending_approvals_for_user(user):
    """الحصول على الموافقات المعلقة للمستخدم"""
    from deviations.models import DeviationApproval
    from capa.models import CAPAApproval
    from change_control.models import ChangeApproval
    
    approvals = []
    
    # موافقات الانحرافات
    dev_approvals = DeviationApproval.objects.filter(
        approver=user,
        status='pending'
    ).select_related('deviation')
    
    for approval in dev_approvals:
        approvals.append({
            'type': 'deviation',
            'item': approval.deviation,
            'approval_type': approval.get_approval_type_display(),
            'due_date': approval.due_date,
            'url': f'/deviations/{approval.deviation.id}/approve/',
        })
    
    # موافقات CAPA
    capa_approvals = CAPAApproval.objects.filter(
        approver=user,
        status='pending'
    ).select_related('capa')
    
    for approval in capa_approvals:
        approvals.append({
            'type': 'capa',
            'item': approval.capa,
            'approval_type': approval.get_approval_type_display(),
            'due_date': approval.due_date,
            'url': f'/capa/{approval.capa.id}/approve/',
        })
    
    # موافقات Change Control
    change_approvals = ChangeApproval.objects.filter(
        approver=user,
        status='pending'
    ).select_related('change_control')
    
    for approval in change_approvals:
        approvals.append({
            'type': 'change',
            'item': approval.change_control,
            'approval_type': approval.get_approval_type_display(),
            'due_date': approval.due_date,
            'url': f'/change-control/{approval.change_control.id}/approve/',
        })
    
    return sorted(approvals, key=lambda x: x['due_date'])


def get_completed_items_count(start_date):
    """عدد العناصر المكتملة منذ تاريخ معين"""
    completed_deviations = Deviation.objects.filter(
        status='closed',
        closure_date__gte=start_date
    ).count()
    
    completed_capas = CAPA.objects.filter(
        status='closed',
        closed_date__gte=start_date
    ).count()
    
    completed_changes = ChangeControl.objects.filter(
        status='completed',
        completion_date__gte=start_date
    ).count()
    
    return completed_deviations + completed_capas + completed_changes


def get_new_items_count(start_date):
    """عدد العناصر الجديدة منذ تاريخ معين"""
    new_deviations = Deviation.objects.filter(
        reported_date__gte=start_date
    ).count()
    
    new_capas = CAPA.objects.filter(
        initiated_date__gte=start_date
    ).count()
    
    new_changes = ChangeControl.objects.filter(
        created_date__gte=start_date
    ).count()
    
    return new_deviations + new_capas + new_changes


def calculate_completion_rate_change(current_month, last_month):
    """حساب تغيير معدل الإنجاز"""
    current_completed = get_completed_items_count(current_month)
    
    last_month_end = current_month - timedelta(days=1)
    last_completed = get_completed_items_count(last_month)
    
    if last_completed == 0:
        return 100 if current_completed > 0 else 0
    
    return round(((current_completed - last_completed) / last_completed) * 100, 1)


def get_priority_actions(user):
    """الحصول على الإجراءات ذات الأولوية"""
    actions = []
    
    # انحرافات حرجة مفتوحة
    critical_deviations = Deviation.objects.filter(
        severity='critical',
        status__in=['open', 'investigation']
    )
    
    for deviation in critical_deviations:
        next_actions = QMSWorkflowEngine.get_next_actions('deviation', deviation.id, user)
        for action in next_actions:
            actions.append({
                'title': f"Critical Deviation: {action['title']}",
                'description': f"{deviation.title}",
                'type': 'danger',
                'icon': 'fas fa-exclamation-triangle',
                'url': action['url'],
                'item_type': 'deviation',
                'item_number': deviation.deviation_number,
                'priority': 1,
            })
    
    # CAPAs متأخرة
    overdue_capas = CAPA.objects.filter(
        status__in=['open', 'in_progress']
    )
    
    for capa in overdue_capas:
        if capa.is_overdue:
            actions.append({
                'title': f"Overdue CAPA",
                'description': f"{capa.title}",
                'type': 'warning',
                'icon': 'fas fa-clock',
                'url': f'/capa/{capa.id}/',
                'item_type': 'capa',
                'item_number': capa.capa_number,
                'priority': 2,
            })
    
    # فحوصات فعالية مستحقة
    due_effectiveness_checks = CAPAEffectivenessCheck.objects.filter(
        check_date__lte=timezone.now().date(),
        result='pending',
        performed_by=user
    )
    
    for check in due_effectiveness_checks:
        actions.append({
            'title': 'Effectiveness Check Due',
            'description': f"CAPA {check.capa.capa_number}",
            'type': 'info',
            'icon': 'fas fa-check-circle',
            'url': f'/capa/{check.capa.id}/effectiveness/{check.id}/perform/',
            'item_type': 'capa',
            'item_number': check.capa.capa_number,
            'priority': 3,
        })
    
    # ترتيب حسب الأولوية
    return sorted(actions, key=lambda x: x['priority'])[:5]


def calculate_system_performance():
    """حساب مقاييس أداء النظام"""
    # نسبة الإنجاز في الوقت المحدد
    total_items = Deviation.objects.count() + CAPA.objects.count() + ChangeControl.objects.count()
    if total_items == 0:
        return {'overall': 0, 'ontime': 0, 'quality': 0, 'integration': 0}
    
    # العناصر المنجزة في الوقت المحدد
    ontime_deviations = Deviation.objects.filter(
        status='closed',
        closure_date__isnull=False
    ).count()
    
    ontime_capas = CAPA.objects.filter(
        status='closed',
        closed_date__isnull=False
    ).count()
    
    ontime_changes = ChangeControl.objects.filter(
        status='completed',
        completion_date__isnull=False
    ).count()
    
    ontime_completion = round(((ontime_deviations + ontime_capas + ontime_changes) / total_items) * 100, 1)
    
    # مقياس الجودة (فعالية CAPA)
    effective_capas = CAPAEffectivenessCheck.objects.filter(
        result='effective'
    ).count()
    
    total_checks = CAPAEffectivenessCheck.objects.exclude(result='pending').count()
    quality_score = round((effective_capas / total_checks) * 100, 1) if total_checks > 0 else 90
    
    # مقياس التكامل
    integration_score = QMSIntegrationManager._calculate_deviation_to_capa_rate()
    
    # الأداء العام
    overall = round((ontime_completion + quality_score + integration_score) / 3, 1)
    
    return {
        'overall': overall,
        'ontime': ontime_completion,
        'quality': quality_score,
        'integration': integration_score,
    }


def calculate_monthly_trends():
    """حساب اتجاهات شهرية"""
    trends = []
    
    for i in range(12):
        month_start = timezone.now().replace(month=i+1, day=1, hour=0, minute=0, second=0, microsecond=0)
        if i == 11:
            month_end = month_start.replace(year=month_start.year + 1, month=1)
        else:
            month_end = month_start.replace(month=i+2)
        
        deviations_count = Deviation.objects.filter(
            reported_date__gte=month_start,
            reported_date__lt=month_end
        ).count()
        
        capas_count = CAPA.objects.filter(
            initiated_date__gte=month_start,
            initiated_date__lt=month_end
        ).count()
        
        changes_count = ChangeControl.objects.filter(
            created_date__gte=month_start,
            created_date__lt=month_end
        ).count()
        
        trends.append({
            'month': calendar.month_name[i+1],
            'deviations': deviations_count,
            'capas': capas_count,
            'changes': changes_count,
        })
    
    return trends


# API Endpoints للـ Dashboard

@login_required
def dashboard_chart_data(request):
    """بيانات المخططات للوحة التحكم"""
    chart_type = request.GET.get('type', 'trends')
    
    if chart_type == 'trends':
        data = calculate_monthly_trends()
        return JsonResponse(data, safe=False)
    
    elif chart_type == 'status_distribution':
        data = {
            'deviations': get_status_distribution('deviation'),
            'capas': get_status_distribution('capa'),
            'changes': get_status_distribution('change'),
        }
        return JsonResponse(data)
    
    elif chart_type == 'performance_metrics':
        data = calculate_system_performance()
        return JsonResponse(data)
    
    return JsonResponse({'error': 'Invalid chart type'}, status=400)


def get_status_distribution(item_type):
    """توزيع الحالات لنوع عنصر معين"""
    if item_type == 'deviation':
        statuses = Deviation.objects.values('status').annotate(count=Count('status'))
    elif item_type == 'capa':
        statuses = CAPA.objects.values('status').annotate(count=Count('status'))
    elif item_type == 'change':
        statuses = ChangeControl.objects.values('status').annotate(count=Count('status'))
    else:
        return []
    
    return [{'status': s['status'], 'count': s['count']} for s in statuses]


@login_required
def system_notifications(request):
    """إشعارات النظام"""
    notifications = []
    
    # انحرافات تحتاج متابعة
    overdue_deviations = Deviation.objects.filter(
        status__in=['open', 'investigation']
    )
    
    for deviation in overdue_deviations:
        if deviation.is_overdue:
            notifications.append({
                'type': 'warning',
                'title': 'Overdue Deviation',
                'message': f"Deviation {deviation.deviation_number} is overdue",
                'url': f'/deviations/{deviation.id}/',
                'timestamp': timezone.now(),
            })
    
    # CAPAs تحتاج فحص فعالية
    pending_effectiveness = CAPAEffectivenessCheck.objects.filter(
        check_date__lte=timezone.now().date(),
        result='pending'
    )
    
    for check in pending_effectiveness:
        notifications.append({
            'type': 'info',
            'title': 'Effectiveness Check Due',
            'message': f"CAPA {check.capa.capa_number} needs effectiveness check",
            'url': f'/capa/{check.capa.id}/effectiveness/{check.id}/perform/',
            'timestamp': timezone.now(),
        })
    
    return JsonResponse(notifications, safe=False)


# دوال إضافية للصحة والمراقبة

def check_deviation_system_health():
    """فحص صحة نظام الانحرافات"""
    total = Deviation.objects.count()
    open_deviations = Deviation.objects.filter(status__in=['open', 'investigation']).count()
    overdue = sum(1 for d in Deviation.objects.filter(status__in=['open', 'investigation']) if d.is_overdue)
    
    health_score = 100
    if total > 0:
        overdue_percentage = (overdue / total) * 100
        if overdue_percentage > 20:
            health_score = 60
        elif overdue_percentage > 10:
            health_score = 80
    
    return {
        'score': health_score,
        'status': 'good' if health_score >= 80 else 'warning' if health_score >= 60 else 'critical',
        'total': total,
        'open': open_deviations,
        'overdue': overdue,
    }


def check_capa_system_health():
    """فحص صحة نظام CAPA"""
    total = CAPA.objects.count()
    active = CAPA.objects.filter(status__in=['open', 'in_progress']).count()
    overdue = sum(1 for c in CAPA.objects.filter(status__in=['open', 'in_progress']) if c.is_overdue)
    
    health_score = 100
    if total > 0:
        overdue_percentage = (overdue / total) * 100
        if overdue_percentage > 15:
            health_score = 60
        elif overdue_percentage > 8:
            health_score = 80
    
    return {
        'score': health_score,
        'status': 'good' if health_score >= 80 else 'warning' if health_score >= 60 else 'critical',
        'total': total,
        'active': active,
        'overdue': overdue,
    }


def check_change_system_health():
    """فحص صحة نظام Change Control"""
    total = ChangeControl.objects.count()
    active = ChangeControl.objects.filter(status__in=['submitted', 'approved', 'in_progress']).count()
    overdue = sum(1 for c in ChangeControl.objects.filter(status__in=['submitted', 'approved', 'in_progress']) if c.is_overdue)
    
    health_score = 100
    if total > 0:
        overdue_percentage = (overdue / total) * 100
        if overdue_percentage > 10:
            health_score = 60
        elif overdue_percentage > 5:
            health_score = 80
    
    return {
        'score': health_score,
        'status': 'good' if health_score >= 80 else 'warning' if health_score >= 60 else 'critical',
        'total': total,
        'active': active,
        'overdue': overdue,
    }


def check_integration_health():
    """فحص صحة التكامل بين الأنظمة"""
    integration_data = QMSIntegrationManager.get_integration_dashboard_data()
    
    deviation_to_capa_rate = integration_data['integration_metrics']['deviation_to_capa_rate']
    capa_to_change_rate = integration_data['integration_metrics']['capa_to_change_rate']
    
    health_score = (deviation_to_capa_rate + capa_to_change_rate) / 2
    
    return {
        'score': health_score,
        'status': 'good' if health_score >= 70 else 'warning' if health_score >= 50 else 'critical',
        'deviation_to_capa_rate': deviation_to_capa_rate,
        'capa_to_change_rate': capa_to_change_rate,
    }