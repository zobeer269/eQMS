from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.utils import timezone
from django.core.validators import FileExtensionValidator
import uuid
import os

def document_upload_path(instance, filename):
    """مسار رفع الوثائق منظم حسب السنة والشهر"""
    ext = filename.split('.')[-1]
    filename = f"{instance.document_id}_{uuid.uuid4().hex[:8]}.{ext}"
    return os.path.join('documents', str(timezone.now().year), str(timezone.now().month), filename)

class DocumentCategory(models.Model):
    """فئات الوثائق"""
    name = models.CharField(_('Category Name'), max_length=100)
    name_en = models.CharField(_('Category Name (English)'), max_length=100)
    code = models.CharField(_('Category Code'), max_length=10, unique=True)
    description = models.TextField(_('Description'), blank=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    is_active = models.BooleanField(_('Active'), default=True)
    
    class Meta:
        verbose_name = _('Document Category')
        verbose_name_plural = _('Document Categories')
        ordering = ['code']
    
    def __str__(self):
        if self.parent:
            return f"{self.parent.name} / {self.name}"
        return self.name

class Document(models.Model):
    """نموذج الوثيقة الرئيسي"""
    
    STATUS_CHOICES = [
        ('draft', _('Draft')),
        ('review', _('Under Review')),
        ('approved', _('Approved')),
        ('published', _('Published')),
        ('obsolete', _('Obsolete')),
    ]
    
    DOCUMENT_TYPES = [
        ('sop', _('Standard Operating Procedure')),
        ('wp', _('Work Instruction')),
        ('form', _('Form')),
        ('policy', _('Policy')),
        ('manual', _('Manual')),
        ('specification', _('Specification')),
        ('certificate', _('Certificate')),
        ('report', _('Report')),
        ('other', _('Other')),
    ]
    
    # معرف الوثيقة
    document_id = models.CharField(
        _('Document ID'), 
        max_length=50, 
        unique=True,
        help_text=_('e.g., SOP-QA-001')
    )
    
    # معلومات أساسية
    title = models.CharField(_('Document Title'), max_length=200)
    title_en = models.CharField(_('Document Title (English)'), max_length=200, blank=True)
    description = models.TextField(_('Description'), blank=True)
    document_type = models.CharField(_('Document Type'), max_length=20, choices=DOCUMENT_TYPES)
    category = models.ForeignKey(DocumentCategory, on_delete=models.PROTECT, verbose_name=_('Category'))
    
    # الإصدار والحالة
    version = models.CharField(_('Version'), max_length=10, default='1.0')
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # التواريخ
    created_date = models.DateTimeField(_('Created Date'), auto_now_add=True)
    effective_date = models.DateField(_('Effective Date'), null=True, blank=True)
    review_date = models.DateField(_('Next Review Date'), null=True, blank=True)
    expiry_date = models.DateField(_('Expiry Date'), null=True, blank=True)
    
    # المسؤولون
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.PROTECT, 
        related_name='authored_documents',
        verbose_name=_('Author')
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='owned_documents',
        verbose_name=_('Document Owner'),
        help_text=_('Responsible for document content and updates')
    )
    
    # الملف
    file = models.FileField(
        _('Document File'),
        upload_to=document_upload_path,
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'doc', 'docx', 'xls', 'xlsx'])]
    )
    file_size = models.IntegerField(_('File Size (bytes)'), default=0)
    file_pages = models.IntegerField(_('Number of Pages'), null=True, blank=True)
    
    # التحكم في الوصول
    is_public = models.BooleanField(_('Public Document'), default=False)
    departments = models.ManyToManyField(
        'accounts.User',
        blank=True,
        limit_choices_to={'department__isnull': False},
        related_name='accessible_documents',
        verbose_name=_('Accessible to Departments')
    )
    
    # البيانات الوصفية
    keywords = models.CharField(_('Keywords'), max_length=500, blank=True, help_text=_('Comma-separated'))
    language = models.CharField(_('Language'), max_length=10, choices=[('ar', 'العربية'), ('en', 'English')], default='ar')
    
    # الأمان والامتثال
    requires_training = models.BooleanField(_('Requires Training'), default=False)
    is_controlled = models.BooleanField(_('Controlled Document'), default=True)
    retention_years = models.IntegerField(_('Retention Period (Years)'), default=5)
    
    class Meta:
        verbose_name = _('Document')
        verbose_name_plural = _('Documents')
        ordering = ['-created_date']
        permissions = [
            ("can_approve_document", "Can approve documents"),
            ("can_publish_document", "Can publish documents"),
            ("can_obsolete_document", "Can obsolete documents"),
        ]
    
    def __str__(self):
        return f"{self.document_id} - {self.title} (v{self.version})"
    
    def save(self, *args, **kwargs):
        if self.file:
            self.file_size = self.file.size
        super().save(*args, **kwargs)
    
    @property
    def is_expired(self):
        if self.expiry_date:
            return self.expiry_date < timezone.now().date()
        return False
    
    @property
    def is_due_for_review(self):
        if self.review_date:
            return self.review_date <= timezone.now().date()
        return False

class DocumentVersion(models.Model):
    """تتبع إصدارات الوثيقة"""
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='versions')
    version_number = models.CharField(_('Version Number'), max_length=10)
    file = models.FileField(_('Version File'), upload_to='document_versions/')
    
    # معلومات التغيير
    change_description = models.TextField(_('Change Description'))
    change_reason = models.CharField(_('Change Reason'), max_length=200)
    
    # التواريخ والمستخدمون
    created_date = models.DateTimeField(_('Created Date'), auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    
    # الحالة
    is_current = models.BooleanField(_('Is Current Version'), default=False)
    
    class Meta:
        verbose_name = _('Document Version')
        verbose_name_plural = _('Document Versions')
        ordering = ['-created_date']
        unique_together = ['document', 'version_number']
    
    def __str__(self):
        return f"{self.document.document_id} - v{self.version_number}"

class DocumentApproval(models.Model):
    """سير عمل الموافقات"""
    APPROVAL_STATUS = [
        ('pending', _('Pending')),
        ('approved', _('Approved')),
        ('rejected', _('Rejected')),
        ('cancelled', _('Cancelled')),
    ]
    
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='approvals')
    version = models.ForeignKey(DocumentVersion, on_delete=models.CASCADE, null=True, blank=True)
    
    # المراجع/الموافق
    approver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='document_approvals')
    approval_role = models.CharField(_('Approval Role'), max_length=50, choices=[
        ('reviewer', _('Reviewer')),
        ('approver', _('Approver')),
        ('publisher', _('Publisher')),
    ])
    
    # الحالة والتواريخ
    status = models.CharField(_('Status'), max_length=20, choices=APPROVAL_STATUS, default='pending')
    requested_date = models.DateTimeField(_('Requested Date'), auto_now_add=True)
    action_date = models.DateTimeField(_('Action Date'), null=True, blank=True)
    due_date = models.DateTimeField(_('Due Date'), null=True, blank=True)
    
    # التعليقات والتوقيع
    comments = models.TextField(_('Comments'), blank=True)
    electronic_signature = models.UUIDField(_('Electronic Signature'), null=True, blank=True)
    signature_meaning = models.CharField(_('Signature Meaning'), max_length=200, blank=True)
    
    # التذكيرات
    reminder_sent = models.BooleanField(_('Reminder Sent'), default=False)
    reminder_date = models.DateTimeField(_('Reminder Date'), null=True, blank=True)
    
    class Meta:
        verbose_name = _('Document Approval')
        verbose_name_plural = _('Document Approvals')
        ordering = ['requested_date']
    
    def __str__(self):
        return f"{self.document.document_id} - {self.get_approval_role_display()} - {self.approver.get_full_name()}"

class DocumentAccess(models.Model):
    """تتبع من يصل للوثائق"""
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='access_logs')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    
    # نوع الوصول
    access_type = models.CharField(_('Access Type'), max_length=20, choices=[
        ('view', _('View')),
        ('download', _('Download')),
        ('print', _('Print')),
        ('email', _('Email')),
    ])
    
    # التفاصيل
    access_date = models.DateTimeField(_('Access Date'), auto_now_add=True)
    ip_address = models.GenericIPAddressField(_('IP Address'))
    user_agent = models.CharField(_('User Agent'), max_length=500, blank=True)
    
    # للتدريب
    acknowledged = models.BooleanField(_('Acknowledged Reading'), default=False)
    acknowledgment_date = models.DateTimeField(_('Acknowledgment Date'), null=True, blank=True)
    
    class Meta:
        verbose_name = _('Document Access Log')
        verbose_name_plural = _('Document Access Logs')
        ordering = ['-access_date']

class DocumentDistribution(models.Model):
    """قائمة التوزيع المحكوم"""
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='distributions')
    
    # لمن يتم التوزيع
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    department = models.CharField(_('Department'), max_length=100, blank=True)
    external_party = models.CharField(_('External Party'), max_length=200, blank=True)
    
    # التفاصيل
    copy_number = models.CharField(_('Copy Number'), max_length=20, blank=True)
    distribution_date = models.DateTimeField(_('Distribution Date'), auto_now_add=True)
    distributed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='distributions_made')
    
    # التأكيد
    receipt_confirmed = models.BooleanField(_('Receipt Confirmed'), default=False)
    confirmation_date = models.DateTimeField(_('Confirmation Date'), null=True, blank=True)
    
    # السحب
    is_withdrawn = models.BooleanField(_('Withdrawn'), default=False)
    withdrawal_date = models.DateTimeField(_('Withdrawal Date'), null=True, blank=True)
    withdrawal_reason = models.CharField(_('Withdrawal Reason'), max_length=200, blank=True)
    
    class Meta:
        verbose_name = _('Document Distribution')
        verbose_name_plural = _('Document Distributions')
        ordering = ['-distribution_date']

class DocumentComment(models.Model):
    """التعليقات على الوثائق"""
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    
    comment = models.TextField(_('Comment'))
    created_date = models.DateTimeField(_('Created Date'), auto_now_add=True)
    
    # للمراجعة
    is_review_comment = models.BooleanField(_('Review Comment'), default=False)
    resolved = models.BooleanField(_('Resolved'), default=False)
    resolved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_comments')
    resolved_date = models.DateTimeField(_('Resolved Date'), null=True, blank=True)
    
    class Meta:
        verbose_name = _('Document Comment')
        verbose_name_plural = _('Document Comments')
        ordering = ['-created_date']