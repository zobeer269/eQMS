from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Q, Count
from datetime import timedelta
from accounts.models import AuditLog
from documents.models import Document, DocumentApproval, DocumentAccess

@login_required
def dashboard_view(request):
    """عرض لوحة التحكم الرئيسية"""
    
    # إحصائيات الوثائق
    documents = Document.objects.all()
    total_documents = documents.count()
    published_documents = documents.filter(status='published').count()
    draft_documents = documents.filter(status='draft').count()
    review_documents = documents.filter(status='review').count()
    
    # الموافقات المعلقة للمستخدم الحالي
    pending_approvals = DocumentApproval.objects.filter(
        approver=request.user,
        status='pending'
    ).count()
    
    # الوثائق التي تحتاج مراجعة قريباً
    documents_needing_review = Document.objects.filter(
        review_date__lte=timezone.now().date() + timedelta(days=30),
        status='published'
    ).count()
    
    # الوثائق الشائعة - أكثر الوثائق مشاهدة
    popular_documents = Document.objects.filter(
        status='published'
    ).annotate(
        views_count=Count('access_logs')  # تم التصحيح من 'documentaccess' إلى 'access_logs'
    ).order_by('-views_count')[:5]
    
    # الموردين النشطين (سنضيفه لاحقاً عند بناء وحدة الموردين)
    active_suppliers = 0
    expiring_certificates = 0
    
    # نسبة التدريب (سنضيفه لاحقاً عند بناء وحدة التدريب)
    training_percentage = 75  # قيمة افتراضية للعرض
    overdue_training = 0
    
    # الأنشطة الأخيرة - آخر 10 أنشطة
    recent_activities = AuditLog.objects.all().select_related('user').order_by('-timestamp')[:10]
    
    # المهام القادمة
    upcoming_tasks = []
    
    # إضافة الموافقات المعلقة كمهام
    pending_approval_tasks = DocumentApproval.objects.filter(
        approver=request.user,
        status='pending'
    ).select_related('document')[:5]
    
    for approval in pending_approval_tasks:
        upcoming_tasks.append({
            'due_date': approval.due_date or timezone.now() + timedelta(days=7),
            'title': f'Review: {approval.document.title}',
            'type': 'approval',
            'type_color': 'warning',
            'get_type_display': 'Document Approval',
            'priority': 'high' if approval.due_date and approval.due_date < timezone.now() else 'medium',
            'get_status_display': 'Pending',
            'get_absolute_url': f'/documents/{approval.document.pk}/'
        })
    
    # إشعارات
    notifications = []
    
    # إضافة إشعارات للموافقات المعلقة
    if pending_approvals > 0:
        notifications.append({
            'type': 'warning',
            'icon': 'exclamation-triangle',
            'message': f'لديك {pending_approvals} موافقة معلقة',
            'link': '/documents/my/'
        })
    
    # إضافة إشعارات للوثائق التي تحتاج مراجعة
    if documents_needing_review > 0:
        notifications.append({
            'type': 'info',
            'icon': 'info-circle',
            'message': f'{documents_needing_review} وثيقة تحتاج مراجعة قريباً',
            'link': '/documents/'
        })
    
    # التدقيقات القادمة (سنضيفه لاحقاً)
    upcoming_audits = 0
    
    # نسب مئوية للنظام
    max_expected_documents = 100  # عدد متوقع للوثائق
    documents_percentage = min(100, int((published_documents / max_expected_documents) * 100)) if max_expected_documents > 0 else 0
    supplier_percentage = 85  # قيمة افتراضية للعرض
    audit_percentage = 60  # قيمة افتراضية للعرض
    
    # حساب عدد الإشعارات غير المقروءة
    unread_notifications_count = len(notifications)
    
    context = {
        # إحصائيات الوثائق
        'total_documents': total_documents,
        'published_documents': published_documents,
        'draft_documents': draft_documents,
        'review_documents': review_documents,
        'pending_approvals': pending_approvals,
        
        # الموردين
        'active_suppliers': active_suppliers,
        'expiring_certificates': expiring_certificates,
        
        # التدريب
        'training_percentage': training_percentage,
        'overdue_training': overdue_training,
        
        # الأنشطة والمهام
        'recent_activities': recent_activities,
        'upcoming_tasks': upcoming_tasks,
        
        # الإشعارات
        'notifications': notifications,
        'unread_notifications_count': unread_notifications_count,
        
        # التدقيقات
        'upcoming_audits': upcoming_audits,
        
        # النسب المئوية
        'documents_percentage': documents_percentage,
        'training_percentage': training_percentage,
        'supplier_percentage': supplier_percentage,
        'audit_percentage': audit_percentage,
        
        # الوثائق الشائعة
        'popular_documents': popular_documents,
    }
    
    return render(request, 'dashboard.html', context)