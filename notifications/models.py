# notifications/models.py
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
import uuid


class NotificationTemplate(models.Model):
    """قوالب الإشعارات"""
    
    NOTIFICATION_TYPES = [
        ('deviation_created', _('Deviation Created')),
        ('deviation_assigned', _('Deviation Assigned')),
        ('deviation_overdue', _('Deviation Overdue')),
        ('capa_created', _('CAPA Created')),
        ('capa_due', _('CAPA Due')),
        ('capa_overdue', _('CAPA Overdue')),
        ('effectiveness_due', _('Effectiveness Check Due')),
        ('change_submitted', _('Change Submitted')),
        ('change_approved', _('Change Approved')),
        ('change_rejected', _('Change Rejected')),
        ('approval_required', _('Approval Required')),
        ('task_assigned', _('Task Assigned')),
        ('system_alert', _('System Alert')),
        ('integration_alert', _('Integration Alert')),
    ]
    
    DELIVERY_METHODS = [
        ('email', _('Email')),
        ('in_app', _('In-App Notification')),
        ('sms', _('SMS')),
        ('both', _('Email and In-App')),
    ]
    
    name = models.CharField(_('Template Name'), max_length=100)
    notification_type = models.CharField(
        _('Notification Type'),
        max_length=30,
        choices=NOTIFICATION_TYPES
    )
    subject_template = models.CharField(_('Subject Template'), max_length=200)
    body_template = models.TextField(_('Body Template'))
    delivery_method = models.CharField(
        _('Delivery Method'),
        max_length=20,
        choices=DELIVERY_METHODS,
        default='both'
    )
    is_active = models.BooleanField(_('Is Active'), default=True)
    
    # إعدادات الإرسال
    send_immediately = models.BooleanField(_('Send Immediately'), default=True)
    delay_minutes = models.IntegerField(_('Delay Minutes'), default=0)
    
    created_date = models.DateTimeField(_('Created Date'), auto_now_add=True)
    updated_date = models.DateTimeField(_('Updated Date'), auto_now=True)
    
    class Meta:
        verbose_name = _('Notification Template')
        verbose_name_plural = _('Notification Templates')
        unique_together = ['notification_type', 'name']
    
    def __str__(self):
        return f"{self.name} - {self.get_notification_type_display()}"


class Notification(models.Model):
    """الإشعارات"""
    
    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('sent', _('Sent')),
        ('delivered', _('Delivered')),
        ('read', _('Read')),
        ('failed', _('Failed')),
    ]
    
    PRIORITY_LEVELS = [
        ('low', _('Low')),
        ('medium', _('Medium')),
        ('high', _('High')),
        ('critical', _('Critical')),
    ]
    
    notification_id = models.UUIDField(default=uuid.uuid4, unique=True)
    
    # المستلم
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name=_('Recipient')
    )
    
    # المرسل
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sent_notifications',
        verbose_name=_('Sender')
    )
    
    # محتوى الإشعار
    notification_type = models.CharField(
        _('Notification Type'),
        max_length=30,
        choices=NotificationTemplate.NOTIFICATION_TYPES
    )
    title = models.CharField(_('Title'), max_length=200)
    message = models.TextField(_('Message'))
    priority = models.CharField(
        _('Priority'),
        max_length=20,
        choices=PRIORITY_LEVELS,
        default='medium'
    )
    
    # العنصر المرتبط
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    related_object = GenericForeignKey('content_type', 'object_id')
    
    # معلومات الإرسال
    status = models.CharField(
        _('Status'),
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    delivery_method = models.CharField(
        _('Delivery Method'),
        max_length=20,
        choices=NotificationTemplate.DELIVERY_METHODS
    )
    
    # التواريخ
    created_date = models.DateTimeField(_('Created Date'), auto_now_add=True)
    scheduled_date = models.DateTimeField(_('Scheduled Date'), null=True, blank=True)
    sent_date = models.DateTimeField(_('Sent Date'), null=True, blank=True)
    read_date = models.DateTimeField(_('Read Date'), null=True, blank=True)
    
    # بيانات إضافية
    action_url = models.URLField(_('Action URL'), blank=True)
    action_text = models.CharField(_('Action Text'), max_length=100, blank=True)
    expires_date = models.DateTimeField(_('Expires Date'), null=True, blank=True)
    
    # تتبع التسليم
    email_sent = models.BooleanField(_('Email Sent'), default=False)
    email_opened = models.BooleanField(_('Email Opened'), default=False)
    sms_sent = models.BooleanField(_('SMS Sent'), default=False)
    
    class Meta:
        verbose_name = _('Notification')
        verbose_name_plural = _('Notifications')
        ordering = ['-created_date']
        indexes = [
            models.Index(fields=['recipient', 'status']),
            models.Index(fields=['notification_type', 'created_date']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.recipient.get_full_name()}"
    
    def mark_as_read(self):
        """تمييز الإشعار كمقروء"""
        if self.status != 'read':
            self.status = 'read'
            self.read_date = timezone.now()
            self.save()
    
    @property
    def is_expired(self):
        """فحص إذا كان الإشعار منتهي الصلاحية"""
        if self.expires_date:
            return timezone.now() > self.expires_date
        return False
    
    @property
    def age_in_hours(self):
        """عمر الإشعار بالساعات"""
        return (timezone.now() - self.created_date).total_seconds() / 3600


class NotificationPreference(models.Model):
    """تفضيلات الإشعارات للمستخدمين"""
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_preferences',
        verbose_name=_('User')
    )
    
    # إعدادات الإشعارات حسب النوع
    deviation_notifications = models.BooleanField(_('Deviation Notifications'), default=True)
    capa_notifications = models.BooleanField(_('CAPA Notifications'), default=True)
    change_notifications = models.BooleanField(_('Change Notifications'), default=True)
    approval_notifications = models.BooleanField(_('Approval Notifications'), default=True)
    system_notifications = models.BooleanField(_('System Notifications'), default=True)
    
    # إعدادات طرق التسليم
    email_enabled = models.BooleanField(_('Email Enabled'), default=True)
    sms_enabled = models.BooleanField(_('SMS Enabled'), default=False)
    in_app_enabled = models.BooleanField(_('In-App Enabled'), default=True)
    
    # إعدادات التوقيت
    quiet_hours_start = models.TimeField(_('Quiet Hours Start'), null=True, blank=True)
    quiet_hours_end = models.TimeField(_('Quiet Hours End'), null=True, blank=True)
    weekend_notifications = models.BooleanField(_('Weekend Notifications'), default=False)
    
    # إعدادات التجميع
    digest_enabled = models.BooleanField(_('Daily Digest'), default=False)
    digest_time = models.TimeField(_('Digest Time'), null=True, blank=True)
    
    created_date = models.DateTimeField(_('Created Date'), auto_now_add=True)
    updated_date = models.DateTimeField(_('Updated Date'), auto_now=True)
    
    class Meta:
        verbose_name = _('Notification Preference')
        verbose_name_plural = _('Notification Preferences')
    
    def __str__(self):
        return f"Preferences for {self.user.get_full_name()}"


class NotificationRule(models.Model):
    """قواعد الإشعارات التلقائية"""
    
    TRIGGER_TYPES = [
        ('creation', _('On Creation')),
        ('status_change', _('On Status Change')),
        ('assignment', _('On Assignment')),
        ('due_date', _('Due Date Approaching')),
        ('overdue', _('Overdue')),
        ('approval_required', _('Approval Required')),
        ('schedule', _('Scheduled')),
    ]
    
    CONDITION_OPERATORS = [
        ('equals', _('Equals')),
        ('not_equals', _('Not Equals')),
        ('contains', _('Contains')),
        ('greater_than', _('Greater Than')),
        ('less_than', _('Less Than')),
        ('in_list', _('In List')),
    ]
    
    name = models.CharField(_('Rule Name'), max_length=100)
    description = models.TextField(_('Description'), blank=True)
    
    # المحفز
    trigger_type = models.CharField(
        _('Trigger Type'),
        max_length=30,
        choices=TRIGGER_TYPES
    )
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    
    # الشروط
    condition_field = models.CharField(_('Condition Field'), max_length=100, blank=True)
    condition_operator = models.CharField(
        _('Condition Operator'),
        max_length=20,
        choices=CONDITION_OPERATORS,
        blank=True
    )
    condition_value = models.TextField(_('Condition Value'), blank=True)
    
    # الإجراء
    notification_template = models.ForeignKey(
        NotificationTemplate,
        on_delete=models.CASCADE,
        verbose_name=_('Notification Template')
    )
    recipient_rule = models.CharField(
        _('Recipient Rule'),
        max_length=100,
        help_text=_('Field name to determine recipient (e.g., assigned_to, reported_by)')
    )
    
    # إعدادات التوقيت
    delay_minutes = models.IntegerField(_('Delay Minutes'), default=0)
    repeat_interval_hours = models.IntegerField(_('Repeat Interval Hours'), default=0)
    max_repeats = models.IntegerField(_('Max Repeats'), default=1)
    
    # الحالة
    is_active = models.BooleanField(_('Is Active'), default=True)
    
    created_date = models.DateTimeField(_('Created Date'), auto_now_add=True)
    updated_date = models.DateTimeField(_('Updated Date'), auto_now=True)
    
    class Meta:
        verbose_name = _('Notification Rule')
        verbose_name_plural = _('Notification Rules')
    
    def __str__(self):
        return f"{self.name} - {self.get_trigger_type_display()}"


# notifications/services.py
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class NotificationService:
    """خدمة إدارة الإشعارات"""
    
    @staticmethod
    def create_notification(notification_type, recipient, title, message, 
                          related_object=None, sender=None, priority='medium',
                          action_url=None, action_text=None):
        """إنشاء إشعار جديد"""
        
        with transaction.atomic():
            # إنشاء الإشعار
            notification = Notification.objects.create(
                notification_type=notification_type,
                recipient=recipient,
                sender=sender,
                title=title,
                message=message,
                priority=priority,
                action_url=action_url,
                action_text=action_text,
            )
            
            # ربط الكائن المرتبط
            if related_object:
                notification.content_type = ContentType.objects.get_for_model(related_object)
                notification.object_id = related_object.pk
                notification.save()
            
            # تحديد طريقة التسليم
            preferences = NotificationPreference.objects.filter(user=recipient).first()
            if preferences:
                if preferences.email_enabled and preferences.in_app_enabled:
                    notification.delivery_method = 'both'
                elif preferences.email_enabled:
                    notification.delivery_method = 'email'
                elif preferences.in_app_enabled:
                    notification.delivery_method = 'in_app'
                else:
                    notification.delivery_method = 'in_app'  # افتراضي
            else:
                notification.delivery_method = 'both'
            
            notification.save()
            
            # إرسال الإشعار
            if notification.delivery_method in ['email', 'both']:
                NotificationService.send_email_notification(notification)
            
            logger.info(f"Notification created: {notification.title} for {recipient.username}")
            return notification
    
    @staticmethod
    def send_email_notification(notification):
        """إرسال إشعار بالبريد الإلكتروني"""
        try:
            # تحضير محتوى البريد الإلكتروني
            context = {
                'notification': notification,
                'recipient': notification.recipient,
                'action_url': notification.action_url,
                'action_text': notification.action_text,
            }
            
            html_message = render_to_string('notifications/email_template.html', context)
            plain_message = strip_tags(html_message)
            
            # إرسال البريد الإلكتروني
            send_mail(
                subject=notification.title,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[notification.recipient.email],
                html_message=html_message,
                fail_silently=False,
            )
            
            # تحديث حالة الإشعار
            notification.email_sent = True
            notification.sent_date = timezone.now()
            notification.status = 'sent'
            notification.save()
            
            logger.info(f"Email notification sent to {notification.recipient.email}")
            
        except Exception as e:
            logger.error(f"Failed to send email notification: {str(e)}")
            notification.status = 'failed'
            notification.save()
    
    @staticmethod
    def create_deviation_notification(deviation, notification_type, recipient=None):
        """إنشاء إشعار خاص بالانحرافات"""
        
        if not recipient:
            if notification_type == 'deviation_created':
                recipient = deviation.assigned_to or deviation.reported_by
            elif notification_type == 'deviation_assigned':
                recipient = deviation.assigned_to
            elif notification_type == 'deviation_overdue':
                recipient = deviation.assigned_to or deviation.reported_by
        
        if not recipient:
            return None
        
        # تحديد محتوى الإشعار
        title_templates = {
            'deviation_created': f'New Deviation Created: {deviation.deviation_number}',
            'deviation_assigned': f'Deviation Assigned to You: {deviation.deviation_number}',
            'deviation_overdue': f'Deviation Overdue: {deviation.deviation_number}',
        }
        
        message_templates = {
            'deviation_created': f'A new deviation has been reported: {deviation.title}',
            'deviation_assigned': f'You have been assigned to investigate deviation: {deviation.title}',
            'deviation_overdue': f'Deviation {deviation.deviation_number} is overdue and requires immediate attention.',
        }
        
        title = title_templates.get(notification_type, 'Deviation Notification')
        message = message_templates.get(notification_type, 'Deviation update notification')
        
        # تحديد الأولوية
        priority = 'high' if deviation.severity in ['critical', 'major'] else 'medium'
        
        return NotificationService.create_notification(
            notification_type=notification_type,
            recipient=recipient,
            title=title,
            message=message,
            related_object=deviation,
            priority=priority,
            action_url=f'/deviations/{deviation.id}/',
            action_text='View Deviation'
        )
    
    @staticmethod
    def create_capa_notification(capa, notification_type, recipient=None):
        """إنشاء إشعار خاص بـ CAPA"""
        
        if not recipient:
            if notification_type == 'capa_created':
                recipient = capa.assigned_to or capa.initiated_by
            elif notification_type == 'capa_due':
                recipient = capa.assigned_to
            elif notification_type == 'capa_overdue':
                recipient = capa.assigned_to or capa.capa_owner
        
        if not recipient:
            return None
        
        title_templates = {
            'capa_created': f'New CAPA Created: {capa.capa_number}',
            'capa_due': f'CAPA Due Soon: {capa.capa_number}',
            'capa_overdue': f'CAPA Overdue: {capa.capa_number}',
        }
        
        message_templates = {
            'capa_created': f'A new CAPA has been initiated: {capa.title}',
            'capa_due': f'CAPA {capa.capa_number} is due in {capa.days_until_due} days',
            'capa_overdue': f'CAPA {capa.capa_number} is {capa.days_overdue} days overdue',
        }
        
        title = title_templates.get(notification_type, 'CAPA Notification')
        message = message_templates.get(notification_type, 'CAPA update notification')
        
        priority = 'high' if capa.priority in ['critical', 'high'] else 'medium'
        
        return NotificationService.create_notification(
            notification_type=notification_type,
            recipient=recipient,
            title=title,
            message=message,
            related_object=capa,
            priority=priority,
            action_url=f'/capa/{capa.id}/',
            action_text='View CAPA'
        )
    
    @staticmethod
    def create_change_notification(change, notification_type, recipient=None):
        """إنشاء إشعار خاص بـ Change Control"""
        
        if not recipient:
            if notification_type == 'change_submitted':
                # إشعار للمدير المسؤول عن الموافقة
                recipient = change.change_owner
            elif notification_type == 'change_approved':
                recipient = change.requester
            elif notification_type == 'change_rejected':
                recipient = change.requester
        
        if not recipient:
            return None
        
        title_templates = {
            'change_submitted': f'Change Request Submitted: {change.change_number}',
            'change_approved': f'Change Request Approved: {change.change_number}',
            'change_rejected': f'Change Request Rejected: {change.change_number}',
        }
        
        message_templates = {
            'change_submitted': f'A new change request has been submitted: {change.title}',
            'change_approved': f'Your change request has been approved: {change.title}',
            'change_rejected': f'Your change request has been rejected: {change.title}',
        }
        
        title = title_templates.get(notification_type, 'Change Control Notification')
        message = message_templates.get(notification_type, 'Change control update notification')
        
        priority = 'high' if change.urgency in ['critical', 'high'] else 'medium'
        
        return NotificationService.create_notification(
            notification_type=notification_type,
            recipient=recipient,
            title=title,
            message=message,
            related_object=change,
            priority=priority,
            action_url=f'/change-control/{change.id}/',
            action_text='View Change Request'
        )
    
    @staticmethod
    def create_approval_notification(approval_object, recipient):
        """إنشاء إشعار الموافقة المطلوبة"""
        
        # تحديد نوع الكائن
        if hasattr(approval_object, 'deviation'):
            item = approval_object.deviation
            item_type = 'Deviation'
            url = f'/deviations/{item.id}/approve/'
        elif hasattr(approval_object, 'capa'):
            item = approval_object.capa
            item_type = 'CAPA'
            url = f'/capa/{item.id}/approve/'
        elif hasattr(approval_object, 'change_control'):
            item = approval_object.change_control
            item_type = 'Change Request'
            url = f'/change-control/{item.id}/approve/'
        else:
            return None
        
        title = f'Approval Required: {item_type} {getattr(item, "deviation_number", getattr(item, "capa_number", getattr(item, "change_number", "")))}'
        message = f'Your approval is required for {item_type}: {item.title}'
        
        return NotificationService.create_notification(
            notification_type='approval_required',
            recipient=recipient,
            title=title,
            message=message,
            related_object=item,
            priority='high',
            action_url=url,
            action_text='Review & Approve'
        )
    
    @staticmethod
    def get_user_notifications(user, unread_only=False, limit=50):
        """الحصول على إشعارات المستخدم"""
        notifications = Notification.objects.filter(recipient=user)
        
        if unread_only:
            notifications = notifications.exclude(status='read')
        
        return notifications.order_by('-created_date')[:limit]
    
    @staticmethod
    def mark_all_as_read(user):
        """تمييز جميع الإشعارات كمقروءة"""
        Notification.objects.filter(
            recipient=user,
            status__in=['pending', 'sent', 'delivered']
        ).update(
            status='read',
            read_date=timezone.now()
        )
    
    @staticmethod
    def cleanup_old_notifications(days=30):
        """تنظيف الإشعارات القديمة"""
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # حذف الإشعارات القديمة المقروءة
        deleted_count = Notification.objects.filter(
            status='read',
            read_date__lt=cutoff_date
        ).delete()[0]
        
        logger.info(f"Cleaned up {deleted_count} old notifications")
        return deleted_count


# notifications/management/commands/send_scheduled_notifications.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from notifications.models import Notification
from notifications.services import NotificationService


class Command(BaseCommand):
    help = 'Send scheduled notifications'
    
    def handle(self, *args, **options):
        # إرسال الإشعارات المجدولة
        scheduled_notifications = Notification.objects.filter(
            status='pending',
            scheduled_date__lte=timezone.now()
        )
        
        for notification in scheduled_notifications:
            if notification.delivery_method in ['email', 'both']:
                NotificationService.send_email_notification(notification)
        
        self.stdout.write(
            self.style.SUCCESS(f'Sent {scheduled_notifications.count()} scheduled notifications')
        )