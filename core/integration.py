# core/integration.py
"""
نظام إدارة التكامل بين الأنظمة الثلاثة:
- Deviation Management
- CAPA Management  
- Change Control Management
"""

from django.db import models, transaction
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class QMSIntegrationManager:
    """مدير التكامل بين أنظمة QMS"""
    
    @staticmethod
    def create_capa_from_deviation(deviation, user, capa_data=None):
        """إنشاء CAPA من انحراف"""
        from capa.models import CAPA
        from deviations.models import Deviation
        
        if not isinstance(deviation, Deviation):
            raise ValueError("Invalid deviation object")
        
        # التحقق من عدم وجود CAPA مرتبط مسبقاً
        if deviation.related_capa:
            raise ValidationError(_("CAPA already exists for this deviation"))
        
        with transaction.atomic():
            # إنشاء CAPA جديد
            capa_defaults = {
                'title': f"CAPA for {deviation.deviation_number}: {deviation.title}",
                'description': f"CAPA initiated from deviation {deviation.deviation_number}.\n\n"
                              f"Deviation Description: {deviation.description}",
                'capa_type': 'corrective',
                'source_type': 'deviation',
                'source_reference': deviation.deviation_number,
                'problem_statement': deviation.description,
                'initiated_by': user,
                'assigned_to': deviation.assigned_to or user,
                'priority': QMSIntegrationManager._map_severity_to_priority(deviation.severity),
                'risk_level': QMSIntegrationManager._map_impact_to_risk(deviation.overall_impact_level),
                'due_date': deviation.due_date or (timezone.now().date() + timezone.timedelta(days=30)),
                'affected_processes': deviation.area_location,
                'requires_regulatory_notification': deviation.requires_regulatory_notification,
                'requires_customer_notification': deviation.requires_customer_notification,
            }
            
            # دمج البيانات المخصصة
            if capa_data:
                capa_defaults.update(capa_data)
            
            capa = CAPA.objects.create(**capa_defaults)
            
            # ربط المنتجات المتأثرة
            if deviation.affected_products.exists():
                capa.affected_products.set(deviation.affected_products.all())
            
            # ربط الوثائق ذات الصلة
            if deviation.related_documents.exists():
                capa.related_documents.set(deviation.related_documents.all())
            
            # ربط الانحراف بـ CAPA
            deviation.related_capa = capa
            deviation.status = 'capa_required'
            deviation.requires_capa = True
            deviation.save()
            
            # إضافة الانحراف للـ CAPAs المرتبطة
            capa.related_deviations.add(deviation)
            
            logger.info(f"CAPA {capa.capa_number} created from deviation {deviation.deviation_number}")
            return capa
    
    @staticmethod
    def create_change_control_from_capa(capa, user, change_data=None):
        """إنشاء Change Control من CAPA"""
        from change_control.models import ChangeControl
        from capa.models import CAPA
        
        if not isinstance(capa, CAPA):
            raise ValueError("Invalid CAPA object")
        
        with transaction.atomic():
            # إنشاء Change Control جديد
            change_defaults = {
                'title': f"Change Control for {capa.capa_number}: {capa.title}",
                'description': f"Change control initiated from CAPA {capa.capa_number}.\n\n"
                              f"CAPA Description: {capa.description}",
                'change_type': 'permanent',
                'change_category': QMSIntegrationManager._determine_change_category(capa),
                'change_reason': f"Implementation of CAPA {capa.capa_number}",
                'change_benefits': capa.expected_benefits or "Implementation of corrective/preventive actions",
                'requester': user,
                'change_owner': capa.capa_owner or capa.assigned_to,
                'urgency': QMSIntegrationManager._map_priority_to_urgency(capa.priority),
                'affected_areas': capa.affected_processes,
                'requires_risk_assessment': True,
                'requires_validation': capa.requires_validation,
                'requires_regulatory_approval': capa.requires_regulatory_notification,
                'requires_training': capa.requires_training,
            }
            
            # دمج البيانات المخصصة
            if change_data:
                change_defaults.update(change_data)
            
            change = ChangeControl.objects.create(**change_defaults)
            
            # ربط المنتجات المتأثرة
            if capa.affected_products.exists():
                change.affected_products.set(capa.affected_products.all())
            
            # ربط الوثائق ذات الصلة
            if capa.related_documents.exists():
                change.related_documents.set(capa.related_documents.all())
            
            # ربط الانحرافات المرتبطة
            if capa.related_deviations.exists():
                change.related_deviations.set(capa.related_deviations.all())
            
            # ربط CAPA بـ Change Control
            capa.related_changes.add(change)
            change.related_capas.add(capa)
            
            logger.info(f"Change Control {change.change_number} created from CAPA {capa.capa_number}")
            return change
    
    @staticmethod
    def create_change_control_from_deviation(deviation, user, change_data=None):
        """إنشاء Change Control مباشرة من انحراف"""
        from change_control.models import ChangeControl
        from deviations.models import Deviation
        
        if not isinstance(deviation, Deviation):
            raise ValueError("Invalid deviation object")
        
        with transaction.atomic():
            # إنشاء Change Control جديد
            change_defaults = {
                'title': f"Change Control for {deviation.deviation_number}: {deviation.title}",
                'description': f"Change control initiated from deviation {deviation.deviation_number}.\n\n"
                              f"Deviation Description: {deviation.description}",
                'change_type': 'permanent',
                'change_category': QMSIntegrationManager._determine_change_category_from_deviation(deviation),
                'change_reason': f"Address deviation {deviation.deviation_number}",
                'change_benefits': "Prevent recurrence of similar deviations",
                'requester': user,
                'change_owner': deviation.assigned_to or user,
                'urgency': QMSIntegrationManager._map_severity_to_urgency(deviation.severity),
                'affected_areas': deviation.area_location,
                'requires_risk_assessment': deviation.overall_impact_level in ['major', 'significant'],
                'requires_regulatory_approval': deviation.requires_regulatory_notification,
            }
            
            # دمج البيانات المخصصة
            if change_data:
                change_defaults.update(change_data)
            
            change = ChangeControl.objects.create(**change_defaults)
            
            # ربط المنتجات المتأثرة
            if deviation.affected_products.exists():
                change.affected_products.set(deviation.affected_products.all())
            
            # ربط الوثائق ذات الصلة
            if deviation.related_documents.exists():
                change.related_documents.set(deviation.related_documents.all())
            
            # ربط الانحراف بـ Change Control
            deviation.related_change_control = change
            deviation.requires_change_control = True
            deviation.save()
            
            # ربط Change Control بالانحراف
            change.related_deviations.add(deviation)
            
            logger.info(f"Change Control {change.change_number} created from deviation {deviation.deviation_number}")
            return change
    
    @staticmethod
    def link_deviation_to_change(deviation, change_control, user):
        """ربط انحراف موجود بـ Change Control موجود"""
        with transaction.atomic():
            deviation.related_change_control = change_control
            deviation.save()
            
            change_control.related_deviations.add(deviation)
            
            # إنشاء سجل في التدقيق
            logger.info(f"Deviation {deviation.deviation_number} linked to Change Control {change_control.change_number}")
    
    @staticmethod
    def auto_update_statuses():
        """تحديث تلقائي لحالات الأنظمة المترابطة"""
        from deviations.models import Deviation
        from capa.models import CAPA
        from change_control.models import ChangeControl
        
        # تحديث حالات الانحرافات بناءً على CAPA
        deviations_with_capa = Deviation.objects.filter(
            related_capa__isnull=False,
            status='capa_required'
        )
        
        for deviation in deviations_with_capa:
            capa = deviation.related_capa
            if capa.status == 'closed':
                deviation.status = 'pending_closure'
                deviation.save()
            elif capa.status == 'in_progress':
                deviation.status = 'capa_in_progress'
                deviation.save()
        
        # تحديث حالات CAPA بناءً على Change Control
        capas_with_changes = CAPA.objects.filter(
            related_changes__isnull=False
        )
        
        for capa in capas_with_changes:
            changes = capa.related_changes.all()
            if all(change.status == 'completed' for change in changes):
                if capa.status != 'closed':
                    capa.status = 'pending_effectiveness'
                    capa.save()
    
    @staticmethod
    def get_integration_dashboard_data(user=None):
        """الحصول على بيانات لوحة التحكم المتكاملة"""
        from deviations.models import Deviation
        from capa.models import CAPA
        from change_control.models import ChangeControl
        
        data = {
            'deviations': {
                'total': Deviation.objects.count(),
                'open': Deviation.objects.filter(status__in=['open', 'investigation']).count(),
                'overdue': 0,
                'requiring_capa': Deviation.objects.filter(requires_capa=True, related_capa__isnull=True).count(),
            },
            'capas': {
                'total': CAPA.objects.count(),
                'active': CAPA.objects.filter(status__in=['open', 'in_progress']).count(),
                'overdue': 0,
                'pending_effectiveness': CAPA.objects.filter(status='pending_effectiveness').count(),
            },
            'changes': {
                'total': ChangeControl.objects.count(),
                'active': ChangeControl.objects.filter(status__in=['submitted', 'approved', 'in_progress']).count(),
                'overdue': 0,
                'pending_implementation': ChangeControl.objects.filter(status='approved').count(),
            },
            'integration_metrics': {
                'deviation_to_capa_rate': QMSIntegrationManager._calculate_deviation_to_capa_rate(),
                'capa_to_change_rate': QMSIntegrationManager._calculate_capa_to_change_rate(),
                'avg_resolution_time': QMSIntegrationManager._calculate_avg_resolution_time(),
            }
        }
        
        # حساب المتأخرات
        all_deviations = Deviation.objects.filter(status__in=['open', 'investigation'])
        data['deviations']['overdue'] = sum(1 for dev in all_deviations if dev.is_overdue)
        
        all_capas = CAPA.objects.filter(status__in=['open', 'in_progress'])
        data['capas']['overdue'] = sum(1 for capa in all_capas if capa.is_overdue)
        
        all_changes = ChangeControl.objects.filter(status__in=['submitted', 'approved', 'in_progress'])
        data['changes']['overdue'] = sum(1 for change in all_changes if change.is_overdue)
        
        return data
    
    # دوال مساعدة للتحويل والتطابق
    @staticmethod
    def _map_severity_to_priority(severity):
        """تحويل شدة الانحراف إلى أولوية CAPA"""
        mapping = {
            'critical': 'critical',
            'major': 'high',
            'minor': 'medium',
            'informational': 'low'
        }
        return mapping.get(severity, 'medium')
    
    @staticmethod
    def _map_impact_to_risk(impact):
        """تحويل مستوى التأثير إلى مستوى المخاطر"""
        mapping = {
            'major': 'very_high',
            'significant': 'high',
            'moderate': 'medium',
            'minimal': 'low',
            'none': 'very_low'
        }
        return mapping.get(impact, 'medium')
    
    @staticmethod
    def _map_priority_to_urgency(priority):
        """تحويل أولوية CAPA إلى إلحاح Change Control"""
        mapping = {
            'critical': 'critical',
            'high': 'high',
            'medium': 'medium',
            'low': 'low'
        }
        return mapping.get(priority, 'medium')
    
    @staticmethod
    def _map_severity_to_urgency(severity):
        """تحويل شدة الانحراف إلى إلحاح Change Control"""
        mapping = {
            'critical': 'critical',
            'major': 'high',
            'minor': 'medium',
            'informational': 'low'
        }
        return mapping.get(severity, 'medium')
    
    @staticmethod
    def _determine_change_category(capa):
        """تحديد فئة التغيير بناءً على CAPA"""
        if 'process' in capa.affected_processes.lower():
            return 'product'
        elif 'system' in capa.affected_processes.lower():
            return 'system'
        elif 'equipment' in capa.affected_processes.lower():
            return 'equipment'
        elif 'document' in capa.affected_processes.lower():
            return 'sop'
        else:
            return 'other'
    
    @staticmethod
    def _determine_change_category_from_deviation(deviation):
        """تحديد فئة التغيير بناءً على الانحراف"""
        type_mapping = {
            'process': 'product',
            'product_quality': 'product',
            'facility': 'facility',
            'documentation': 'sop',
            'personnel': 'personnel',
            'system': 'system',
            'environmental': 'facility',
        }
        return type_mapping.get(deviation.deviation_type, 'other')
    
    @staticmethod
    def _calculate_deviation_to_capa_rate():
        """حساب معدل تحويل الانحرافات إلى CAPA"""
        from deviations.models import Deviation
        
        total_deviations = Deviation.objects.count()
        if total_deviations == 0:
            return 0
        
        deviations_with_capa = Deviation.objects.filter(related_capa__isnull=False).count()
        return round((deviations_with_capa / total_deviations) * 100, 1)
    
    @staticmethod
    def _calculate_capa_to_change_rate():
        """حساب معدل تحويل CAPA إلى Change Control"""
        from capa.models import CAPA
        
        total_capas = CAPA.objects.count()
        if total_capas == 0:
            return 0
        
        capas_with_changes = CAPA.objects.filter(related_changes__isnull=False).count()
        return round((capas_with_changes / total_capas) * 100, 1)
    
    @staticmethod
    def _calculate_avg_resolution_time():
        """حساب متوسط وقت الحل الشامل"""
        from deviations.models import Deviation
        
        closed_deviations = Deviation.objects.filter(
            status='closed',
            closure_date__isnull=False
        )
        
        if not closed_deviations.exists():
            return 0
        
        total_days = 0
        for deviation in closed_deviations:
            delta = deviation.closure_date.date() - deviation.reported_date.date()
            total_days += delta.days
        
        return round(total_days / closed_deviations.count(), 1)


class QMSWorkflowEngine:
    """محرك سير العمل لأنظمة QMS"""
    
    @staticmethod
    def get_next_actions(item_type, item_id, user):
        """الحصول على الإجراءات المقترحة التالية"""
        actions = []
        
        if item_type == 'deviation':
            actions = QMSWorkflowEngine._get_deviation_next_actions(item_id, user)
        elif item_type == 'capa':
            actions = QMSWorkflowEngine._get_capa_next_actions(item_id, user)
        elif item_type == 'change':
            actions = QMSWorkflowEngine._get_change_next_actions(item_id, user)
        
        return actions
    
    @staticmethod
    def _get_deviation_next_actions(deviation_id, user):
        """الحصول على الإجراءات المقترحة للانحراف"""
        from deviations.models import Deviation
        
        try:
            deviation = Deviation.objects.get(id=deviation_id)
        except Deviation.DoesNotExist:
            return []
        
        actions = []
        
        if deviation.status == 'open':
            actions.extend([
                {
                    'title': _('Start Investigation'),
                    'url': f'/deviations/{deviation.id}/investigate/',
                    'type': 'primary',
                    'icon': 'fas fa-search'
                },
                {
                    'title': _('Assign to User'),
                    'url': f'/deviations/{deviation.id}/assign/',
                    'type': 'secondary',
                    'icon': 'fas fa-user'
                }
            ])
        
        if deviation.status == 'investigation' and not deviation.related_capa:
            actions.append({
                'title': _('Create CAPA'),
                'url': f'/deviations/{deviation.id}/create-capa/',
                'type': 'warning',
                'icon': 'fas fa-plus'
            })
        
        if deviation.status == 'investigation' and not deviation.related_change_control:
            actions.append({
                'title': _('Create Change Control'),
                'url': f'/deviations/{deviation.id}/create-change/',
                'type': 'info',
                'icon': 'fas fa-exchange-alt'
            })
        
        return actions
    
    @staticmethod
    def _get_capa_next_actions(capa_id, user):
        """الحصول على الإجراءات المقترحة لـ CAPA"""
        from capa.models import CAPA
        
        try:
            capa = CAPA.objects.get(id=capa_id)
        except CAPA.DoesNotExist:
            return []
        
        actions = []
        
        if capa.status == 'open':
            actions.extend([
                {
                    'title': _('Create Action Plan'),
                    'url': f'/capa/{capa.id}/actions/',
                    'type': 'primary',
                    'icon': 'fas fa-tasks'
                },
                {
                    'title': _('Create Change Control'),
                    'url': f'/capa/{capa.id}/create-change/',
                    'type': 'info',
                    'icon': 'fas fa-exchange-alt'
                }
            ])
        
        if capa.status == 'pending_effectiveness':
            actions.append({
                'title': _('Perform Effectiveness Check'),
                'url': f'/capa/{capa.id}/effectiveness/create/',
                'type': 'success',
                'icon': 'fas fa-check-circle'
            })
        
        return actions
    
    @staticmethod
    def _get_change_next_actions(change_id, user):
        """الحصول على الإجراءات المقترحة لـ Change Control"""
        from change_control.models import ChangeControl
        
        try:
            change = ChangeControl.objects.get(id=change_id)
        except ChangeControl.DoesNotExist:
            return []
        
        actions = []
        
        if change.status == 'draft':
            actions.append({
                'title': _('Submit for Review'),
                'url': f'/change-control/{change.id}/submit/',
                'type': 'primary',
                'icon': 'fas fa-paper-plane'
            })
        
        if change.status == 'approved':
            actions.extend([
                {
                    'title': _('Create Implementation Plan'),
                    'url': f'/change-control/{change.id}/implementation-plan/create/',
                    'type': 'warning',
                    'icon': 'fas fa-clipboard-list'
                },
                {
                    'title': _('Start Implementation'),
                    'url': f'/change-control/{change.id}/implementation-plan/start/',
                    'type': 'success',
                    'icon': 'fas fa-play'
                }
            ])
        
        return actions


class QMSNotificationManager:
    """مدير الإشعارات المتكاملة"""
    
    @staticmethod
    def send_integration_notification(item_type, item_id, action, user, recipients=None):
        """إرسال إشعار تكامل بين الأنظمة"""
        from django.contrib.auth.models import User
        
        # تحديد المستلمين إذا لم يتم تحديدهم
        if not recipients:
            recipients = QMSNotificationManager._get_default_recipients(item_type, item_id)
        
        # إنشاء الإشعار
        notification_data = {
            'title': QMSNotificationManager._get_notification_title(item_type, action),
            'message': QMSNotificationManager._get_notification_message(item_type, item_id, action, user),
            'item_type': item_type,
            'item_id': item_id,
            'action': action,
            'created_by': user,
            'recipients': recipients,
        }
        
        # إرسال الإشعار (يمكن تنفيذ هذا عبر نظام الإشعارات المفضل)
        logger.info(f"Integration notification sent: {notification_data['title']}")
        
        return notification_data
    
    @staticmethod
    def _get_default_recipients(item_type, item_id):
        """تحديد المستلمين الافتراضيين للإشعار"""
        recipients = []
        
        if item_type == 'deviation':
            from deviations.models import Deviation
            try:
                deviation = Deviation.objects.get(id=item_id)
                recipients = [deviation.reported_by, deviation.assigned_to, deviation.investigation_owner]
            except Deviation.DoesNotExist:
                pass
        
        # إزالة القيم الفارغة
        return [r for r in recipients if r is not None]
    
    @staticmethod
    def _get_notification_title(item_type, action):
        """إنشاء عنوان الإشعار"""
        titles = {
            ('deviation', 'capa_created'): _('CAPA Created from Deviation'),
            ('deviation', 'change_created'): _('Change Control Created from Deviation'),
            ('capa', 'change_created'): _('Change Control Created from CAPA'),
            ('capa', 'effectiveness_checked'): _('CAPA Effectiveness Checked'),
            ('change', 'implemented'): _('Change Control Implemented'),
        }
        
        return titles.get((item_type, action), _('QMS System Update'))
    
    @staticmethod
    def _get_notification_message(item_type, item_id, action, user):
        """إنشاء محتوى الإشعار"""
        return f"User {user.get_full_name()} performed action '{action}' on {item_type} #{item_id}"