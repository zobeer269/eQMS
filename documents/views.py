from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.utils.translation import gettext as _
from django.utils import timezone
from django.http import HttpResponse, FileResponse, JsonResponse
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST
from .models import (
    Document, DocumentCategory, DocumentVersion, 
    DocumentApproval, DocumentAccess, DocumentDistribution,
    DocumentComment
)
from .forms import (
    DocumentUploadForm, DocumentSearchForm, 
    DocumentReviewForm, DocumentChangeForm,
    DocumentCommentForm, SendForReviewForm,
    BulkActionForm
)
from accounts.models import AuditLog, User
from accounts.views import create_audit_log

@login_required
def document_list(request):
    """عرض قائمة الوثائق"""
    form = DocumentSearchForm(request.GET)
    documents = Document.objects.select_related('category', 'author', 'owner')
    
    # تطبيق الفلاتر
    if form.is_valid():
        search = form.cleaned_data.get('search')
        if search:
            documents = documents.filter(
                Q(title__icontains=search) |
                Q(title_en__icontains=search) |
                Q(document_id__icontains=search) |
                Q(keywords__icontains=search) |
                Q(description__icontains=search)
            )
        
        if form.cleaned_data.get('document_type'):
            documents = documents.filter(document_type=form.cleaned_data['document_type'])
        
        if form.cleaned_data.get('category'):
            documents = documents.filter(category=form.cleaned_data['category'])
        
        if form.cleaned_data.get('status'):
            documents = documents.filter(status=form.cleaned_data['status'])
        
        if form.cleaned_data.get('date_from'):
            documents = documents.filter(created_date__date__gte=form.cleaned_data['date_from'])
        
        if form.cleaned_data.get('date_to'):
            documents = documents.filter(created_date__date__lte=form.cleaned_data['date_to'])
    
    # التحقق من الصلاحيات
    if not request.user.is_staff:
        # إظهار الوثائق العامة والخاصة بالقسم فقط
        documents = documents.filter(
            Q(is_public=True) |
            Q(departments__in=[request.user]) |
            Q(author=request.user) |
            Q(owner=request.user)
        ).distinct()
    
    # ترتيب حسب التاريخ
    documents = documents.order_by('-created_date')
    
    # التصفح
    paginator = Paginator(documents, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # إحصائيات سريعة
    stats = {
        'total': documents.count(),
        'draft': documents.filter(status='draft').count(),
        'review': documents.filter(status='review').count(),
        'approved': documents.filter(status='approved').count(),
        'published': documents.filter(status='published').count(),
    }
    
    # نموذج الإجراءات الجماعية
    bulk_form = BulkActionForm()
    
    return render(request, 'documents/document_list.html', {
        'form': form,
        'page_obj': page_obj,
        'stats': stats,
        'bulk_form': bulk_form,
    })


@login_required
def document_create(request):
    """إنشاء وثيقة جديدة"""
    if request.method == 'POST':
        form = DocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            document.author = request.user
            document.save()
            
            # إنشاء أول إصدار
            DocumentVersion.objects.create(
                document=document,
                version_number=document.version,
                file=document.file,
                change_description=_('Initial version'),
                change_reason=_('Document creation'),
                created_by=request.user,
                is_current=True
            )
            
            # سجل التدقيق
            create_audit_log(
                request.user, 'create', request,
                model_name='Document',
                object_id=document.id,
                object_repr=str(document)
            )
            
            messages.success(request, _('Document created successfully.'))
            
            # إرسال للمراجعة إذا لزم الأمر
            if request.POST.get('send_for_review'):
                return redirect('documents:send_for_review', pk=document.pk)
            
            return redirect('documents:detail', pk=document.pk)
    else:
        form = DocumentUploadForm()
        # توليد معرف تلقائي
        doc_type = request.GET.get('type', 'sop')
        category_code = request.GET.get('category', 'QA')
        
        last_doc = Document.objects.filter(
            document_id__startswith=f"{doc_type.upper()}-{category_code}-"
        ).order_by('-created_date').first()
        
        if last_doc:
            # استخراج الرقم وزيادته
            try:
                parts = last_doc.document_id.split('-')
                number = int(parts[-1]) + 1
                suggested_id = f"{'-'.join(parts[:-1])}-{number:03d}"
            except:
                suggested_id = f"{doc_type.upper()}-{category_code}-001"
        else:
            suggested_id = f"{doc_type.upper()}-{category_code}-001"
        
        form.initial['document_id'] = suggested_id
        
        # إذا كان المستخدم مدير جودة، اجعله المالك الافتراضي
        if request.user.is_quality_manager:
            form.initial['owner'] = request.user
    
    return render(request, 'documents/document_form.html', {
        'form': form,
        'title': _('Create New Document'),
        'submit_text': _('Create Document'),
    })


@login_required
def document_detail(request, pk):
    """عرض تفاصيل الوثيقة"""
    document = get_object_or_404(Document, pk=pk)
    
    # التحقق من الصلاحية
    can_view = (
        document.is_public or
        request.user.is_staff or
        request.user == document.author or
        request.user == document.owner or
        request.user in document.departments.all()
    )
    
    if not can_view:
        messages.error(request, _('You do not have permission to view this document.'))
        return redirect('documents:list')
    
    # تسجيل الوصول
    DocumentAccess.objects.create(
        document=document,
        user=request.user,
        access_type='view',
        ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1'),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
    )
    
    # سجل التدقيق
    create_audit_log(
        request.user, 'view', request,
        model_name='Document',
        object_id=document.id,
        object_repr=str(document)
    )
    
    # جلب البيانات المرتبطة
    versions = document.versions.all().order_by('-created_date')
    approvals = document.approvals.all().order_by('-requested_date')
    comments = document.comments.all().order_by('-created_date')
    access_logs = document.access_logs.all().order_by('-access_date')[:10]
    distributions = document.distributions.filter(is_withdrawn=False)
    
    # التحقق من الحاجة للتدريب
    needs_training = False
    training_completed = False
    if document.requires_training:
        # تحقق من إكمال التدريب
        training_completed = DocumentAccess.objects.filter(
            document=document,
            user=request.user,
            acknowledged=True
        ).exists()
        needs_training = not training_completed
    
    # التحقق من الموافقات المعلقة
    pending_approval = document.approvals.filter(
        approver=request.user,
        status='pending'
    ).first()
    
    # نموذج التعليق
    comment_form = DocumentCommentForm()
    
    # صلاحيات المستخدم
    can_edit = (
        request.user == document.author or 
        request.user == document.owner or 
        request.user.is_staff
    ) and document.status in ['draft', 'rejected']
    
    can_approve = (
        request.user.has_perm('documents.can_approve_document') or
        request.user.can_approve_documents
    )
    
    can_publish = (
        request.user.has_perm('documents.can_publish_document') or
        request.user.is_quality_manager
    )
    
    can_change = can_edit or (can_publish and document.status == 'published')
    
    return render(request, 'documents/document_detail.html', {
        'document': document,
        'versions': versions,
        'approvals': approvals,
        'comments': comments,
        'access_logs': access_logs,
        'distributions': distributions,
        'needs_training': needs_training,
        'training_completed': training_completed,
        'pending_approval': pending_approval,
        'comment_form': comment_form,
        'can_edit': can_edit,
        'can_approve': can_approve,
        'can_publish': can_publish,
        'can_change': can_change,
    })


@login_required
def document_download(request, pk):
    """تحميل الوثيقة"""
    document = get_object_or_404(Document, pk=pk)
    
    # التحقق من الصلاحية
    can_download = (
        document.is_public or
        request.user.is_staff or
        request.user == document.author or
        request.user == document.owner or
        request.user in document.departments.all()
    )
    
    if not can_download:
        messages.error(request, _('You do not have permission to download this document.'))
        return redirect('documents:list')
    
    # تسجيل التحميل
    DocumentAccess.objects.create(
        document=document,
        user=request.user,
        access_type='download',
        ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1'),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
    )
    
    # سجل التدقيق
    create_audit_log(
        request.user, 'download', request,
        model_name='Document',
        object_id=document.id,
        object_repr=str(document)
    )
    
    # إرسال الملف
    response = FileResponse(
        document.file.open('rb'),
        as_attachment=True,
        filename=f"{document.document_id}_v{document.version}_{document.file.name.split('/')[-1]}"
    )
    return response


@login_required
def document_edit(request, pk):
    """تعديل الوثيقة"""
    document = get_object_or_404(Document, pk=pk)
    
    # التحقق من الصلاحية
    can_edit = (
        request.user == document.author or 
        request.user == document.owner or 
        request.user.is_staff
    ) and document.status in ['draft', 'rejected']
    
    if not can_edit:
        messages.error(request, _('You cannot edit this document in its current status.'))
        return redirect('documents:detail', pk=pk)
    
    if request.method == 'POST':
        form = DocumentUploadForm(request.POST, request.FILES, instance=document)
        if form.is_valid():
            old_values = {
                'title': document.title,
                'description': document.description,
                'owner': str(document.owner),
            }
            
            document = form.save()
            
            new_values = {
                'title': document.title,
                'description': document.description,
                'owner': str(document.owner),
            }
            
            # سجل التدقيق
            create_audit_log(
                request.user, 'update', request,
                model_name='Document',
                object_id=document.id,
                object_repr=str(document),
                old_values=old_values,
                new_values=new_values
            )
            
            messages.success(request, _('Document updated successfully.'))
            return redirect('documents:detail', pk=document.pk)
    else:
        form = DocumentUploadForm(instance=document)
    
    return render(request, 'documents/document_form.html', {
        'form': form,
        'document': document,
        'title': _('Edit Document'),
        'submit_text': _('Update Document'),
    })


@login_required
def document_review(request, pk):
    """مراجعة والموافقة على الوثيقة"""
    document = get_object_or_404(Document, pk=pk)
    approval = get_object_or_404(
        DocumentApproval,
        document=document,
        approver=request.user,
        status='pending'
    )
    
    if request.method == 'POST':
        form = DocumentReviewForm(request.POST, instance=approval)
        if form.is_valid():
            # التحقق من التوقيع الإلكتروني
            password = form.cleaned_data['electronic_signature']
            if not request.user.check_password(password):
                messages.error(request, _('Invalid electronic signature.'))
                return render(request, 'documents/document_review.html', {
                    'form': form,
                    'document': document,
                    'approval': approval,
                })
            
            # تحديث الموافقة
            action = form.cleaned_data['action']
            approval.status = 'approved' if action == 'approve' else 'rejected'
            approval.action_date = timezone.now()
            approval.electronic_signature = request.user.electronic_signature
            approval.signature_meaning = _('I have reviewed and %(action)s this document') % {'action': action}
            approval.save()
            
            # تحديث حالة الوثيقة
            if action == 'approve':
                # التحقق من اكتمال جميع الموافقات
                pending_approvals = document.approvals.filter(
                    status='pending'
                ).exclude(pk=approval.pk).count()
                
                if pending_approvals == 0:
                    document.status = 'approved'
                    document.save()
                    messages.success(request, _('Document approved successfully.'))
                else:
                    messages.info(request, _('Your approval has been recorded. Waiting for other approvals.'))
            else:
                document.status = 'rejected'
                document.save()
                messages.warning(request, _('Document rejected. It has been sent back to draft.'))
            
            # إضافة تعليق
            if form.cleaned_data['comments']:
                DocumentComment.objects.create(
                    document=document,
                    user=request.user,
                    comment=form.cleaned_data['comments'],
                    is_review_comment=True
                )
            
            # سجل التدقيق
            create_audit_log(
                request.user, 'approve' if action == 'approve' else 'reject', request,
                model_name='Document',
                object_id=document.id,
                object_repr=str(document),
                electronic_signature=str(request.user.electronic_signature),
                signature_meaning=approval.signature_meaning,
                reason=form.cleaned_data['comments']
            )
            
            return redirect('documents:detail', pk=document.pk)
    else:
        form = DocumentReviewForm(instance=approval)
    
    return render(request, 'documents/document_review.html', {
        'form': form,
        'document': document,
        'approval': approval,
    })


@login_required
def document_change(request, pk):
    """تغيير/تحديث الوثيقة"""
    document = get_object_or_404(Document, pk=pk)
    
    # التحقق من الصلاحية
    can_change = (
        request.user == document.author or 
        request.user == document.owner or 
        request.user.is_staff or
        (request.user.is_quality_manager and document.status == 'published')
    )
    
    if not can_change:
        messages.error(request, _('You do not have permission to change this document.'))
        return redirect('documents:detail', pk=pk)
    
    if request.method == 'POST':
        form = DocumentChangeForm(request.POST, request.FILES)
        if form.is_valid():
            # إنشاء إصدار جديد
            new_version = DocumentVersion.objects.create(
                document=document,
                version_number=form.cleaned_data['new_version'],
                file=form.cleaned_data['new_file'],
                change_description=form.cleaned_data['change_description'],
                change_reason=form.cleaned_data['change_reason'],
                created_by=request.user,
                is_current=True
            )
            
            # تحديث الإصدار القديم
            DocumentVersion.objects.filter(
                document=document,
                is_current=True
            ).exclude(pk=new_version.pk).update(is_current=False)
            
            # تحديث الوثيقة
            old_version = document.version
            document.version = form.cleaned_data['new_version']
            document.file = form.cleaned_data['new_file']
            document.status = 'draft'  # العودة للمسودة للمراجعة
            
            if form.cleaned_data.get('effective_date'):
                document.effective_date = form.cleaned_data['effective_date']
            
            document.save()
            
            # سجل التدقيق
            create_audit_log(
                request.user, 'update', request,
                model_name='Document',
                object_id=document.id,
                object_repr=str(document),
                old_values={'version': old_version},
                new_values={'version': new_version.version_number},
                reason=form.cleaned_data['change_reason']
            )
            
            messages.success(request, _('Document updated successfully. New version created.'))
            return redirect('documents:detail', pk=document.pk)
    else:
        # اقتراح رقم الإصدار التالي
        current_version = document.version
        try:
            parts = current_version.split('.')
            if len(parts) == 2:
                major, minor = parts
                suggested_version = f"{major}.{int(minor) + 1}"
            else:
                suggested_version = f"{int(float(current_version)) + 1}.0"
        except:
            suggested_version = "2.0"
        
        form = DocumentChangeForm(initial={
            'new_version': suggested_version,
            'effective_date': timezone.now().date()
        })
    
    return render(request, 'documents/document_change.html', {
        'form': form,
        'document': document,
    })


@login_required
def document_send_for_review(request, pk):
    """إرسال الوثيقة للمراجعة"""
    document = get_object_or_404(Document, pk=pk)
    
    # التحقق من الصلاحية
    if request.user != document.author and request.user != document.owner:
        messages.error(request, _('You do not have permission to send this document for review.'))
        return redirect('documents:detail', pk=pk)
    
    # التحقق من الحالة
    if document.status not in ['draft', 'rejected']:
        messages.error(request, _('Only draft or rejected documents can be sent for review.'))
        return redirect('documents:detail', pk=pk)
    
    if request.method == 'POST':
        form = SendForReviewForm(request.POST)
        if form.is_valid():
            # إنشاء طلبات الموافقة
            due_date = timezone.now() + timezone.timedelta(days=form.cleaned_data['due_days'])
            
            for reviewer in form.cleaned_data.get('reviewers', []):
                DocumentApproval.objects.create(
                    document=document,
                    approver=reviewer,
                    approval_role='reviewer',
                    due_date=due_date
                )
            
            for approver in form.cleaned_data.get('approvers', []):
                DocumentApproval.objects.create(
                    document=document,
                    approver=approver,
                    approval_role='approver',
                    due_date=due_date
                )
            
            # تحديث حالة الوثيقة
            document.status = 'review'
            document.save()
            
            # سجل التدقيق
            create_audit_log(
                request.user, 'update', request,
                model_name='Document',
                object_id=document.id,
                object_repr=str(document),
                old_values={'status': 'draft'},
                new_values={'status': 'review'}
            )
            
            messages.success(request, _('Document sent for review successfully.'))
            return redirect('documents:detail', pk=pk)
    else:
        form = SendForReviewForm()
    
    return render(request, 'documents/send_for_review.html', {
        'form': form,
        'document': document,
    })


@login_required
@require_POST
def document_acknowledge(request, pk):
    """تأكيد قراءة وفهم الوثيقة"""
    document = get_object_or_404(Document, pk=pk)
    
    # البحث عن سجل الوصول الأخير
    access_log = DocumentAccess.objects.filter(
        document=document,
        user=request.user,
        acknowledged=False
    ).order_by('-access_date').first()
    
    if access_log:
        access_log.acknowledged = True
        access_log.acknowledgment_date = timezone.now()
        access_log.save()
        
        # سجل التدقيق
        create_audit_log(
            request.user, 'update', request,
            model_name='DocumentAccess',
            object_id=access_log.id,
            object_repr=f"Acknowledged {document.document_id}"
        )
        
        messages.success(request, _('Your acknowledgment has been recorded.'))
    else:
        # إنشاء سجل جديد
        DocumentAccess.objects.create(
            document=document,
            user=request.user,
            access_type='view',
            ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            acknowledged=True,
            acknowledgment_date=timezone.now()
        )
        messages.success(request, _('Your acknowledgment has been recorded.'))
    
    return redirect('documents:detail', pk=pk)


@login_required
@require_POST
def document_comment(request, pk):
    """إضافة تعليق على الوثيقة"""
    document = get_object_or_404(Document, pk=pk)
    
    form = DocumentCommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.document = document
        comment.user = request.user
        comment.save()
        
        messages.success(request, _('Comment added successfully.'))
    else:
        messages.error(request, _('Error adding comment.'))
    
    return redirect('documents:detail', pk=pk)


@login_required
def document_publish(request, pk):
    """نشر الوثيقة"""
    document = get_object_or_404(Document, pk=pk)
    
    # التحقق من الصلاحية
    if not request.user.is_quality_manager and not request.user.has_perm('documents.can_publish_document'):
        messages.error(request, _('You do not have permission to publish documents.'))
        return redirect('documents:detail', pk=pk)
    
    # التحقق من الحالة
    if document.status != 'approved':
        messages.error(request, _('Only approved documents can be published.'))
        return redirect('documents:detail', pk=pk)
    
    if request.method == 'POST':
        # نشر الوثيقة
        document.status = 'published'
        if not document.effective_date:
            document.effective_date = timezone.now().date()
        document.save()
        
        # سجل التدقيق
        create_audit_log(
            request.user, 'update', request,
            model_name='Document',
            object_id=document.id,
            object_repr=str(document),
            old_values={'status': 'approved'},
            new_values={'status': 'published'}
        )
        
        messages.success(request, _('Document published successfully.'))
        return redirect('documents:detail', pk=pk)
    
    return render(request, 'documents/confirm_publish.html', {
        'document': document,
    })


@login_required
def my_documents(request):
    """الوثائق الخاصة بي"""
    # الوثائق التي أنشأتها
    authored = Document.objects.filter(author=request.user).order_by('-created_date')[:10]
    
    # الوثائق التي أملكها
    owned = Document.objects.filter(owner=request.user).order_by('-created_date')[:10]
    
    # الوثائق التي تحتاج موافقتي
    pending_approvals = DocumentApproval.objects.filter(
        approver=request.user,
        status='pending'
    ).select_related('document').order_by('due_date')
    
    # الوثائق التي تحتاج لقراءتها
    unread_documents = Document.objects.filter(
        status='published',
        requires_training=True
    ).exclude(
        access_logs__user=request.user,
        access_logs__acknowledged=True
    ).distinct()[:10]
    
    # التعليقات التي تحتاج رد
    if request.user.is_quality_manager:
        unresolved_comments = DocumentComment.objects.filter(
            is_review_comment=True,
            resolved=False
        ).select_related('document', 'user').order_by('-created_date')[:10]
    else:
        unresolved_comments = DocumentComment.objects.filter(
            is_review_comment=True,
            resolved=False,
            document__in=Document.objects.filter(
                Q(author=request.user) | Q(owner=request.user)
            )
        ).select_related('document', 'user').order_by('-created_date')[:10]
    
    return render(request, 'documents/my_documents.html', {
        'authored': authored,
        'owned': owned,
        'pending_approvals': pending_approvals,
        'unread_documents': unread_documents,
        'unresolved_comments': unresolved_comments,
    })


@login_required
def document_categories(request):
    """إدارة فئات الوثائق"""
    if not request.user.is_staff:
        messages.error(request, _('You do not have permission to manage categories.'))
        return redirect('documents:list')
    
    categories = DocumentCategory.objects.all().order_by('code')
    
    return render(request, 'documents/categories.html', {
        'categories': categories,
    })


@login_required
@require_POST
def bulk_action(request):
    """تنفيذ إجراءات جماعية"""
    form = BulkActionForm(request.POST)
    
    if form.is_valid():
        action = form.cleaned_data['action']
        document_ids = request.POST.getlist('selected_documents')
        
        if not document_ids:
            messages.error(request, _('No documents selected.'))
            return redirect('documents:list')
        
        documents = Document.objects.filter(pk__in=document_ids)
        
        if action == 'download':
            # TODO: تنفيذ تحميل متعدد
            messages.info(request, _('Bulk download feature coming soon.'))
        
        elif action == 'change_owner':
            new_owner = form.cleaned_data.get('new_owner')
            if new_owner:
                count = documents.update(owner=new_owner)
                messages.success(request, _('%(count)d documents updated.') % {'count': count})
        
        elif action == 'archive':
            count = documents.update(status='obsolete')
            messages.success(request, _('%(count)d documents archived.') % {'count': count})
    
    return redirect('documents:list')