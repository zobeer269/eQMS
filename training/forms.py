from django import forms
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import (
    TrainingProgram, TrainingSession, TrainingRecord,
    TrainingMaterial, TrainingEvaluation
)
from accounts.models import User


class TrainingProgramForm(forms.ModelForm):
    """نموذج إنشاء/تعديل برنامج تدريبي"""
    
    class Meta:
        model = TrainingProgram
        fields = [
            'program_id', 'title', 'title_en', 'description',
            'training_type', 'delivery_method', 'duration_hours',
            'passing_score', 'validity_months', 'prerequisites',
            'target_departments', 'related_documents', 'trainer',
            'is_mandatory'
        ]
        widgets = {
            'program_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('e.g., TRN-QA-001')
            }),
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'dir': 'auto'
            }),
            'title_en': forms.TextInput(attrs={
                'class': 'form-control',
                'dir': 'ltr'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'dir': 'auto'
            }),
            'training_type': forms.Select(attrs={'class': 'form-select'}),
            'delivery_method': forms.Select(attrs={'class': 'form-select'}),
            'duration_hours': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.5',
                'min': '0.5'
            }),
            'passing_score': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'max': '100'
            }),
            'validity_months': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1'
            }),
            'prerequisites': forms.SelectMultiple(attrs={
                'class': 'form-select',
                'size': '5'
            }),
            'target_departments': forms.CheckboxSelectMultiple(),
            'related_documents': forms.SelectMultiple(attrs={
                'class': 'form-select',
                'size': '5'
            }),
            'trainer': forms.Select(attrs={'class': 'form-select'}),
            'is_mandatory': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def clean_program_id(self):
        program_id = self.cleaned_data.get('program_id')
        if program_id:
            # التحقق من الصيغة
            import re
            pattern = r'^TRN-[A-Z]{2,4}-\d{3,4}$'
            if not re.match(pattern, program_id):
                raise ValidationError(
                    _('Program ID must follow format: TRN-XX-001')
                )
        return program_id
    
    def clean_passing_score(self):
        score = self.cleaned_data.get('passing_score')
        if score < 0 or score > 100:
            raise ValidationError(_('Passing score must be between 0 and 100'))
        return score


class TrainingSessionForm(forms.ModelForm):
    """نموذج إنشاء جلسة تدريبية"""
    
    class Meta:
        model = TrainingSession
        fields = [
            'program', 'scheduled_date', 'location',
            'trainer', 'max_participants', 'notes'
        ]
        widgets = {
            'program': forms.Select(attrs={'class': 'form-select'}),
            'scheduled_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('e.g., Conference Room A, Building 2')
            }),
            'trainer': forms.Select(attrs={'class': 'form-select'}),
            'max_participants': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '100'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # فلترة المدربين المؤهلين فقط
        self.fields['trainer'].queryset = User.objects.filter(
            is_active=True,
            groups__name__in=['Trainers', 'Quality Managers']
        ).distinct()
    
    def clean_scheduled_date(self):
        scheduled_date = self.cleaned_data.get('scheduled_date')
        if scheduled_date and scheduled_date <= timezone.now():
            raise ValidationError(_('Scheduled date must be in the future'))
        return scheduled_date


class TrainingEnrollmentForm(forms.Form):
    """نموذج تسجيل المتدربين في جلسة"""
    
    trainees = forms.ModelMultipleChoiceField(
        label=_('Select Trainees'),
        queryset=User.objects.filter(is_active=True),
        widget=forms.CheckboxSelectMultiple(),
        required=True
    )
    
    send_notification = forms.BooleanField(
        label=_('Send email notification to trainees'),
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    def __init__(self, session, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session = session
        
        # استبعاد المتدربين المسجلين بالفعل
        enrolled_users = TrainingRecord.objects.filter(
            session=session
        ).values_list('trainee', flat=True)
        
        # فلترة المستخدمين حسب الأقسام المستهدفة
        queryset = User.objects.filter(is_active=True).exclude(
            id__in=enrolled_users
        )
        
        # إذا كان البرنامج يستهدف أقساماً معينة
        if session.program.target_departments.exists():
            target_depts = session.program.target_departments.values_list(
                'department', flat=True
            ).distinct()
            queryset = queryset.filter(department__in=target_depts)
        
        self.fields['trainees'].queryset = queryset
    
    def clean_trainees(self):
        trainees = self.cleaned_data.get('trainees')
        
        # التحقق من السعة المتاحة
        current_count = self.session.participants_count
        available_slots = self.session.max_participants - current_count
        
        if len(trainees) > available_slots:
            raise ValidationError(
                _('Only %(slots)d slots available. You selected %(selected)d trainees.') % {
                    'slots': available_slots,
                    'selected': len(trainees)
                }
            )
        
        return trainees


class TrainingAttendanceForm(forms.Form):
    """نموذج تسجيل الحضور"""
    
    def __init__(self, session, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # إضافة حقل لكل متدرب مسجل
        records = TrainingRecord.objects.filter(
            session=session,
            status__in=['enrolled', 'attended']
        ).select_related('trainee')
        
        for record in records:
            field_name = f'attendance_{record.id}'
            self.fields[field_name] = forms.BooleanField(
                label=record.trainee.get_full_name(),
                required=False,
                initial=record.status == 'attended',
                widget=forms.CheckboxInput(attrs={
                    'class': 'form-check-input',
                    'data-record-id': record.id
                })
            )
            
            # حقل التوقيع الإلكتروني
            sig_field_name = f'signature_{record.id}'
            self.fields[sig_field_name] = forms.CharField(
                label=_('Electronic Signature'),
                required=False,
                widget=forms.PasswordInput(attrs={
                    'class': 'form-control',
                    'placeholder': _('Password for signature'),
                    'data-record-id': record.id
                })
            )


class TrainingTestForm(forms.ModelForm):
    """نموذج إدخال نتائج الاختبار"""
    
    class Meta:
        model = TrainingRecord
        fields = ['pre_test_score', 'post_test_score']
        widgets = {
            'pre_test_score': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'max': '100',
                'step': '0.5'
            }),
            'post_test_score': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'max': '100',
                'step': '0.5'
            }),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        pre_score = cleaned_data.get('pre_test_score')
        post_score = cleaned_data.get('post_test_score')
        
        if pre_score is not None and (pre_score < 0 or pre_score > 100):
            raise ValidationError({
                'pre_test_score': _('Score must be between 0 and 100')
            })
        
        if post_score is not None and (post_score < 0 or post_score > 100):
            raise ValidationError({
                'post_test_score': _('Score must be between 0 and 100')
            })
        
        return cleaned_data


class TrainingEvaluationForm(forms.ModelForm):
    """نموذج تقييم التدريب"""
    
    class Meta:
        model = TrainingEvaluation
        exclude = ['training_record', 'submitted_date']
        widgets = {
            # تقييم المحتوى
            'content_relevance': forms.RadioSelect(choices=[
                (1, '1 - ضعيف جداً'),
                (2, '2 - ضعيف'),
                (3, '3 - متوسط'),
                (4, '4 - جيد'),
                (5, '5 - ممتاز')
            ]),
            'content_clarity': forms.RadioSelect(choices=[
                (1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')
            ]),
            'content_completeness': forms.RadioSelect(choices=[
                (1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')
            ]),
            
            # تقييم المدرب
            'trainer_knowledge': forms.RadioSelect(choices=[
                (1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')
            ]),
            'trainer_presentation': forms.RadioSelect(choices=[
                (1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')
            ]),
            'trainer_interaction': forms.RadioSelect(choices=[
                (1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')
            ]),
            
            # تقييم البيئة
            'facility_rating': forms.RadioSelect(choices=[
                (1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')
            ]),
            'materials_rating': forms.RadioSelect(choices=[
                (1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')
            ]),
            
            # التقييم العام
            'overall_rating': forms.RadioSelect(choices=[
                (1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')
            ]),
            'would_recommend': forms.RadioSelect(choices=[
                (True, _('Yes')),
                (False, _('No'))
            ]),
            
            # التعليقات
            'strengths': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('What did you like most about this training?')
            }),
            'improvements': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('What could be improved?')
            }),
            'additional_comments': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('Any other comments?')
            }),
        }


class TrainingSearchForm(forms.Form):
    """نموذج البحث في التدريبات"""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Search by title, ID, or trainer...'),
            'dir': 'auto'
        })
    )
    
    training_type = forms.ChoiceField(
        required=False,
        choices=[('', _('All Types'))] + TrainingProgram.TRAINING_TYPES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    delivery_method = forms.ChoiceField(
        required=False,
        choices=[('', _('All Methods'))] + TrainingProgram.DELIVERY_METHODS,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    status = forms.ChoiceField(
        required=False,
        choices=[
            ('', _('All Status')),
            ('active', _('Active')),
            ('inactive', _('Inactive')),
            ('upcoming', _('Upcoming Sessions')),
            ('completed', _('Completed Sessions')),
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
