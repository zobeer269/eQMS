from django import forms
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from .models import (
    CAPA, CAPAAction, CAPAEffectivenessCheck, 
    CAPAApproval, CAPAAttachment
)
from accounts.models import User
from documents.models import Document
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, ButtonHolder, Submit, Div, Field, HTML
from crispy_forms.bootstrap import TabHolder, Tab
import datetime

class CAPACreateForm(forms.ModelForm):
    """نموذج إنشاء CAPA جديد"""
    
    class Meta:
        model = CAPA
        fields = [
            'title', 'description', 'capa_type', 'source_type', 
            'source_reference', 'priority', 'due_date', 'capa_owner',
            'problem_statement', 'affected_departments'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Brief title for the CAPA')
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': _('Detailed description of the issue')
            }),
            'capa_type': forms.Select(attrs={'class': 'form-select'}),
            'source_type': forms.Select(attrs={'class': 'form-select'}),
            'source_reference': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('e.g., DEV-2025-001, AUD-2025-002')
            }),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'due_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'capa_owner': forms.Select(attrs={'class': 'form-select'}),
            'problem_statement': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': _('Clear and concise problem statement')
            }),
            'affected_departments': forms.SelectMultiple(attrs={
                'class': 'form-select',
                'size': 5
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.source_type = kwargs.pop('source_type', None)
        self.source_ref = kwargs.pop('source_ref', None)
        super().__init__(*args, **kwargs)
        
        # Set default values if creating from source
        if self.source_type:
            self.fields['source_type'].initial = self.source_type
            self.fields['source_type'].widget.attrs['readonly'] = True
        
        if self.source_ref:
            self.fields['source_reference'].initial = self.source_ref
            self.fields['source_reference'].widget.attrs['readonly'] = True
        
        # Set default due date (30 days from now)
        self.fields['due_date'].initial = (
            datetime.date.today() + datetime.timedelta(days=30)
        )
        
        # Limit CAPA owner to qualified users
        self.fields['capa_owner'].queryset = User.objects.filter(
            is_active=True
        ).filter(
            models.Q(is_quality_manager=True) | 
            models.Q(can_approve_documents=True)
        )
        
        # Configure affected departments
        self.fields['affected_departments'].queryset = User.objects.filter(
            department__isnull=False
        ).values_list('department', flat=True).distinct()
    
    def clean_due_date(self):
        due_date = self.cleaned_data.get('due_date')
        if due_date and due_date < datetime.date.today():
            raise ValidationError(_('Due date cannot be in the past'))
        return due_date


class CAPARootCauseForm(forms.ModelForm):
    """نموذج تحليل السبب الجذري"""
    
    class Meta:
        model = CAPA
        fields = [
            'root_cause_analysis', 'root_cause_category',
            'risk_assessment', 'risk_level'
        ]
        widgets = {
            'root_cause_analysis': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 6,
                'placeholder': _('Detailed root cause analysis using appropriate methods')
            }),
            'root_cause_category': forms.Select(attrs={'class': 'form-select'}),
            'risk_assessment': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': _('Assess risks associated with the issue')
            }),
            'risk_level': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Fieldset(
                _('Root Cause Analysis'),
                'root_cause_analysis',
                'root_cause_category',
            ),
            Fieldset(
                _('Risk Assessment'),
                'risk_assessment',
                'risk_level',
            ),
        )


class CAPAActionForm(forms.ModelForm):
    """نموذج إجراء CAPA"""
    
    class Meta:
        model = CAPAAction
        fields = [
            'action_type', 'action_description', 'responsible_person',
            'planned_date', 'verification_required', 'evidence_description'
        ]
        widgets = {
            'action_type': forms.Select(attrs={'class': 'form-select'}),
            'action_description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('Describe the action to be taken')
            }),
            'responsible_person': forms.Select(attrs={'class': 'form-select'}),
            'planned_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'verification_required': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'evidence_description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': _('What evidence will demonstrate completion?')
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.capa = kwargs.pop('capa', None)
        super().__init__(*args, **kwargs)
        
        # Set default planned date
        self.fields['planned_date'].initial = datetime.date.today() + datetime.timedelta(days=14)
        
        # Limit responsible persons to active users
        self.fields['responsible_person'].queryset = User.objects.filter(is_active=True)
    
    def clean_planned_date(self):
        planned_date = self.cleaned_data.get('planned_date')
        if planned_date and self.capa:
            if planned_date > self.capa.due_date:
                raise ValidationError(
                    _('Action planned date cannot be after CAPA due date (%(due_date)s)') % {
                        'due_date': self.capa.due_date
                    }
                )
        return planned_date


class CAPAActionCompleteForm(forms.ModelForm):
    """نموذج إكمال إجراء CAPA"""
    
    completion_comments = forms.CharField(
        label=_('Completion Comments'),
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': _('Describe how the action was completed')
        }),
        required=True
    )
    
    class Meta:
        model = CAPAAction
        fields = ['actual_completion_date']
        widgets = {
            'actual_completion_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['actual_completion_date'].initial = datetime.date.today()


class CAPAEffectivenessCheckForm(forms.ModelForm):
    """نموذج فحص فعالية CAPA"""
    
    class Meta:
        model = CAPAEffectivenessCheck
        fields = [
            'planned_date', 'check_method', 'acceptance_criteria'
        ]
        widgets = {
            'planned_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'check_method': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('How will effectiveness be verified?')
            }),
            'acceptance_criteria': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('What criteria determine success?')
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.capa = kwargs.pop('capa', None)
        super().__init__(*args, **kwargs)
        
        # Set default date (3 months after CAPA completion)
        if self.capa and self.capa.completion_date:
            self.fields['planned_date'].initial = (
                self.capa.completion_date + datetime.timedelta(days=90)
            )


class CAPAEffectivenessPerformForm(forms.ModelForm):
    """نموذج تنفيذ فحص الفعالية"""
    
    class Meta:
        model = CAPAEffectivenessCheck
        fields = [
            'actual_date', 'result', 'findings',
            'additional_actions_required', 'additional_actions_description'
        ]
        widgets = {
            'actual_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'result': forms.Select(attrs={'class': 'form-select'}),
            'findings': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': _('Describe the findings from the effectiveness check')
            }),
            'additional_actions_required': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'additional_actions_description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('Describe additional actions if needed')
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['actual_date'].initial = datetime.date.today()


class CAPAApprovalForm(forms.Form):
    """نموذج الموافقة على CAPA"""
    
    action = forms.ChoiceField(
        label=_('Action'),
        choices=[
            ('approve', _('Approve')),
            ('reject', _('Reject')),
            ('request_changes', _('Request Changes')),
        ],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    
    comments = forms.CharField(
        label=_('Comments'),
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': _('Provide your review comments')
        }),
        required=True
    )
    
    electronic_signature = forms.CharField(
        label=_('Electronic Signature'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('Enter your password to sign')
        }),
        help_text=_('Enter your password as electronic signature')
    )


class CAPASearchForm(forms.Form):
    """نموذج البحث في CAPA"""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Search by number, title, or description...')
        })
    )
    
    capa_type = forms.ChoiceField(
        required=False,
        choices=[('', _('All Types'))] + CAPA.CAPA_TYPES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    source_type = forms.ChoiceField(
        required=False,
        choices=[('', _('All Sources'))] + CAPA.SOURCE_TYPES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    status = forms.ChoiceField(
        required=False,
        choices=[('', _('All Status'))] + CAPA.STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    priority = forms.ChoiceField(
        required=False,
        choices=[('', _('All Priorities'))] + CAPA.PRIORITY_LEVELS,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    risk_level = forms.ChoiceField(
        required=False,
        choices=[('', _('All Risk Levels'))] + [
            ('critical', _('Critical')),
            ('high', _('High')),
            ('medium', _('Medium')),
            ('low', _('Low')),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    is_overdue = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    owner = forms.ModelChoiceField(
        required=False,
        queryset=User.objects.filter(is_active=True),
        empty_label=_('All Owners'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )