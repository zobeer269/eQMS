from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import uuid

class User(AbstractUser):
    """نموذج المستخدم المخصص مع حقول إضافية للامتثال"""
    
    # معلومات الموظف
    employee_id = models.CharField(
        _('Employee ID'),
        max_length=20, 
        unique=True,
        help_text=_('Unique employee identifier')
    )
    
    department = models.CharField(
        _('Department'),
        max_length=100,
        choices=[
            ('quality', _('Quality Assurance')),
            ('regulatory', _('Regulatory Affairs')),
            ('warehouse', _('Warehouse')),
            ('management', _('Management')),
            ('it', _('Information Technology')),
        ]
    )
    
    position = models.CharField(
        _('Position'),
        max_length=100
    )
    
    phone = models.CharField(
        _('Phone Number'),
        max_length=20,
        blank=True
    )
    
    # اللغة المفضلة
    preferred_language = models.CharField(
        _('Preferred Language'),
        max_length=10,
        choices=[('ar', 'العربية'), ('en', 'English')],
        default='ar'
    )
    
    # معلومات الأمان
    must_change_password = models.BooleanField(
        _('Must Change Password'),
        default=False
    )
    
    password_changed_at = models.DateTimeField(
        _('Password Last Changed'),
        default=timezone.now
    )
    
    failed_login_attempts = models.IntegerField(
        _('Failed Login Attempts'),
        default=0
    )
    
    last_failed_login = models.DateTimeField(
        _('Last Failed Login'),
        null=True,
        blank=True
    )
    
    # التوقيع الإلكتروني
    electronic_signature = models.UUIDField(
        _('Electronic Signature'),
        default=uuid.uuid4,
        editable=False,
        unique=True
    )
    
    signature_image = models.ImageField(
        _('Signature Image'),
        upload_to='signatures/',
        null=True,
        blank=True
    )
    
    # الصلاحيات الخاصة
    is_quality_manager = models.BooleanField(
        _('Is Quality Manager'),
        default=False
    )
    
    is_document_controller = models.BooleanField(
        _('Is Document Controller'),
        default=False
    )
    
    can_approve_documents = models.BooleanField(
        _('Can Approve Documents'),
        default=False
    )
    
    # التدريب والمؤهلات
    is_trained = models.BooleanField(
        _('Training Completed'),
        default=False
    )
    
    training_date = models.DateField(
        _('Last Training Date'),
        null=True,
        blank=True
    )
    
    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        
    def __str__(self):
        return f"{self.get_full_name()} ({self.employee_id})"
    
    def get_display_name(self):
        """الحصول على الاسم للعرض حسب اللغة"""
        if self.preferred_language == 'ar':
            return f"{self.first_name} {self.last_name}"
        return f"{self.last_name}, {self.first_name}"


class AuditLog(models.Model):
    """سجل التدقيق لجميع الأنشطة - مطلوب لـ 21 CFR Part 11"""
    
    # معلومات المستخدم
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name=_('User')
    )
    
    username = models.CharField(
        _('Username'),
        max_length=150,
        help_text=_('Stored separately in case user is deleted')
    )
    
    # معلومات الحدث
    action = models.CharField(
        _('Action'),
        max_length=50,
        choices=[
            ('login', _('User Login')),
            ('logout', _('User Logout')),
            ('login_failed', _('Failed Login Attempt')),
            ('password_change', _('Password Changed')),
            ('create', _('Record Created')),
            ('update', _('Record Updated')),
            ('delete', _('Record Deleted')),
            ('view', _('Record Viewed')),
            ('approve', _('Document Approved')),
            ('reject', _('Document Rejected')),
            ('download', _('File Downloaded')),
            ('print', _('Document Printed')),
        ]
    )
    
    # تفاصيل السجل
    model_name = models.CharField(
        _('Model Name'),
        max_length=100,
        blank=True
    )
    
    object_id = models.IntegerField(
        _('Object ID'),
        null=True,
        blank=True
    )
    
    object_repr = models.CharField(
        _('Object Representation'),
        max_length=500,
        blank=True
    )
    
    # البيانات
    old_values = models.JSONField(
        _('Old Values'),
        default=dict,
        blank=True
    )
    
    new_values = models.JSONField(
        _('New Values'),
        default=dict,
        blank=True
    )
    
    # معلومات تقنية
    timestamp = models.DateTimeField(
        _('Timestamp'),
        auto_now_add=True,
        db_index=True
    )
    
    ip_address = models.GenericIPAddressField(
        _('IP Address')
    )
    
    user_agent = models.CharField(
        _('User Agent'),
        max_length=500,
        blank=True
    )
    
    # سبب التغيير (مطلوب لبعض الإجراءات)
    reason = models.TextField(
        _('Reason for Change'),
        blank=True
    )
    
    # التوقيع الإلكتروني للإجراءات الحرجة
    electronic_signature = models.UUIDField(
        _('Electronic Signature'),
        null=True,
        blank=True
    )
    
    signature_meaning = models.CharField(
        _('Signature Meaning'),
        max_length=200,
        blank=True,
        help_text=_('e.g., "I approve this document"')
    )
    
    class Meta:
        verbose_name = _('Audit Log Entry')
        verbose_name_plural = _('Audit Log Entries')
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['action', '-timestamp']),
        ]
        
    def __str__(self):
        return f"{self.username} - {self.action} - {self.timestamp}"


class SecureSession(models.Model):
    """جلسات آمنة مع معلومات إضافية"""
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name=_('User')
    )
    
    session_key = models.CharField(
        _('Session Key'),
        max_length=40,
        unique=True
    )
    
    ip_address = models.GenericIPAddressField(
        _('IP Address')
    )
    
    user_agent = models.CharField(
        _('User Agent'),
        max_length=500
    )
    
    created_at = models.DateTimeField(
        _('Created At'),
        auto_now_add=True
    )
    
    last_activity = models.DateTimeField(
        _('Last Activity'),
        auto_now=True
    )
    
    is_active = models.BooleanField(
        _('Is Active'),
        default=True
    )
    
    class Meta:
        verbose_name = _('Secure Session')
        verbose_name_plural = _('Secure Sessions')