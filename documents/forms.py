from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Document, DocumentCategory, DocumentComment, DocumentApproval
from django.core.exceptions import ValidationError
from accounts.models import User

class DocumentUploadForm(forms.ModelForm):
    """نموذج رفع وثيقة جديدة"""
    
    class Meta:
        model = Document
        fields = [
            'document_id', 'title', 'title_en', 'description',
            'document_type', 'category', 'file', 'keywords',
            'language', 'requires_training', 'owner', 'effective_date',
            'review_date', 'expiry_date'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Enter document title'),
                'dir': 'auto'
            }),
            'title_en': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Enter document title in English'),
                'dir': 'ltr'
            }),
            'document_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('e.g., SOP-QA-001')
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'dir': 'auto'
            }),
            'document_type': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'language': forms.Select(attrs={'class': 'form-select'}),
            'keywords': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Comma-separated keywords')
            }),
            'file': forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf,.doc,.docx,.xls,.xlsx'}),
            'owner': forms.Select(attrs={'class': 'form-select'}),
            'requires_training': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'effective_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'review_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'expiry_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # ترتيب الفئات بشكل هرمي
        self.fields['category'].queryset = DocumentCategory.objects.filter(is_active=True)
        
        # تحديد المالكين المحتملين (مدراء الجودة فقط)
        self.fields['owner'].queryset = User.objects.filter(
            is_active=True,
            is_quality_manager=True
        )
        
        # جعل بعض الحقول اختيارية
        self.fields['title_en'].required = False
        self.fields['description'].required = False
        self.fields['keywords'].required = False
        self.fields['effective_date'].required = False
        self.fields['review_date'].required = False
        self.fields['expiry_date'].required = False
    
    def clean_document_id(self):
        """التحقق من صيغة معرف الوثيقة"""
        document_id = self.cleaned_data.get('document_id')
        if document_id:
            # التحقق من الصيغة: XXX-XX-000
            import re
            pattern = r'^[A-Z]{2,4}-[A-Z]{2,4}-\d{3,4}$'
            if not re.match(pattern, document_id):
                raise ValidationError(
                    _('Document ID must follow format: SOP-QA-001')
                )
        return document_id
    
    def clean_file(self):
        """التحقق من حجم ونوع الملف"""
        file = self.cleaned_data.get('file')
        if file:
            # التحقق من الحجم (أقصى 10 ميجا)
            if file.size > 10 * 1024 * 1024:
                raise ValidationError(_('File size cannot exceed 10 MB'))
            
            # التحقق من النوع
            ext = file.name.split('.')[-1].lower()
            allowed_extensions = ['pdf', 'doc', 'docx', 'xls', 'xlsx']
            if ext not in allowed_extensions:
                raise ValidationError(
                    _('File type not allowed. Allowed types: %(types)s') % {
                        'types': ', '.join(allowed_extensions)
                    }
                )
        return file
    
    def clean(self):
        """التحقق من التواريخ"""
        cleaned_data = super().clean()
        effective_date = cleaned_data.get('effective_date')
        review_date = cleaned_data.get('review_date')
        expiry_date = cleaned_data.get('expiry_date')
        
        # التحقق من أن تاريخ المراجعة بعد تاريخ السريان
        if effective_date and review_date:
            if review_date <= effective_date:
                raise ValidationError({
                    'review_date': _('Review date must be after effective date')
                })
        
        # التحقق من أن تاريخ الانتهاء بعد تاريخ السريان
        if effective_date and expiry_date:
            if expiry_date <= effective_date:
                raise ValidationError({
                    'expiry_date': _('Expiry date must be after effective date')
                })
        
        return cleaned_data


class DocumentSearchForm(forms.Form):
    """نموذج البحث في الوثائق"""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Search by title, ID, or keywords...'),
            'dir': 'auto'
        })
    )
    
    document_type = forms.ChoiceField(
        required=False,
        choices=[('', _('All Types'))] + Document.DOCUMENT_TYPES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    category = forms.ModelChoiceField(
        required=False,
        queryset=DocumentCategory.objects.filter(is_active=True),
        empty_label=_('All Categories'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    status = forms.ChoiceField(
        required=False,
        choices=[('', _('All Status'))] + Document.STATUS_CHOICES,
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


class DocumentReviewForm(forms.ModelForm):
    """نموذج مراجعة الوثيقة"""
    
    comments = forms.CharField(
        label=_('Review Comments'),
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': _('Enter your review comments...'),
            'dir': 'auto'
        })
    )
    
    action = forms.ChoiceField(
        label=_('Action'),
        choices=[
            ('approve', _('Approve')),
            ('reject', _('Reject')),
            ('request_changes', _('Request Changes')),
        ],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    
    electronic_signature = forms.CharField(
        label=_('Electronic Signature'),
        help_text=_('Enter your password to sign this action'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('Your password')
        })
    )
    
    class Meta:
        model = DocumentApproval
        fields = ['comments']


class DocumentChangeForm(forms.Form):
    """نموذج تغيير الوثيقة"""
    
    new_version = forms.CharField(
        label=_('New Version Number'),
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('e.g., 1.1, 2.0')
        })
    )
    
    change_description = forms.CharField(
        label=_('Change Description'),
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': _('Describe what changed...'),
            'dir': 'auto'
        })
    )
    
    change_reason = forms.CharField(
        label=_('Reason for Change'),
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Why is this change needed?'),
            'dir': 'auto'
        })
    )
    
    new_file = forms.FileField(
        label=_('Updated Document File'),
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.pdf,.doc,.docx,.xls,.xlsx'
        })
    )
    
    effective_date = forms.DateField(
        label=_('New Effective Date'),
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    def clean_new_version(self):
        """التحقق من صيغة رقم الإصدار"""
        version = self.cleaned_data.get('new_version')
        if version:
            import re
            # التحقق من الصيغة: X.Y أو X.Y.Z
            if not re.match(r'^\d+\.\d+(\.\d+)?$', version):
                raise ValidationError(_('Version must be in format X.Y or X.Y.Z (e.g., 1.0, 2.1.3)'))
        return version


class DocumentCommentForm(forms.ModelForm):
    """نموذج إضافة تعليق"""
    
    class Meta:
        model = DocumentComment
        fields = ['comment', 'is_review_comment']
        widgets = {
            'comment': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('Add your comment...'),
                'dir': 'auto'
            }),
            'is_review_comment': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
        labels = {
            'comment': _('Comment'),
            'is_review_comment': _('This is a review comment requiring resolution')
        }


class SendForReviewForm(forms.Form):
    """نموذج إرسال الوثيقة للمراجعة"""
    
    reviewers = forms.ModelMultipleChoiceField(
        label=_('Select Reviewers'),
        queryset=User.objects.filter(can_approve_documents=True, is_active=True),
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        }),
        required=False
    )
    
    approvers = forms.ModelMultipleChoiceField(
        label=_('Select Approvers'),
        queryset=User.objects.filter(is_quality_manager=True, is_active=True),
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        }),
        required=True
    )
    
    due_days = forms.IntegerField(
        label=_('Due in (days)'),
        initial=7,
        min_value=1,
        max_value=30,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'style': 'width: 100px;'
        })
    )
    
    message = forms.CharField(
        label=_('Message to reviewers'),
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': _('Optional message to reviewers...'),
            'dir': 'auto'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        reviewers = cleaned_data.get('reviewers', [])
        approvers = cleaned_data.get('approvers', [])
        
        # التحقق من وجود مراجع أو موافق واحد على الأقل
        if not reviewers and not approvers:
            raise ValidationError(_('Please select at least one reviewer or approver'))
        
        return cleaned_data


class BulkActionForm(forms.Form):
    """نموذج الإجراءات الجماعية"""
    
    ACTION_CHOICES = [
        ('', _('Select Action')),
        ('download', _('Download Selected')),
        ('archive', _('Archive Selected')),
        ('delete', _('Delete Selected')),
        ('change_owner', _('Change Owner')),
    ]
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    new_owner = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True, is_quality_manager=True),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    selected_documents = forms.CharField(
        widget=forms.HiddenInput(),
        required=False
    )