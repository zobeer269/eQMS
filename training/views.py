from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.utils.translation import gettext as _
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Count, Avg, F
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST
from django.template.loader import get_template
from xhtml2pdf import pisa
from io import BytesIO
from datetime import timedelta
import json

from .models import (
    TrainingProgram, TrainingSession, TrainingRecord,
    TrainingMaterial, TrainingEvaluation
)
from .forms import (
    TrainingProgramForm, TrainingSessionForm, TrainingEnrollmentForm,
    TrainingAttendanceForm, TrainingTestForm, TrainingEvaluationForm,
    TrainingSearchForm
)
from accounts.models import AuditLog, User
from accounts.views import create_audit_log


@login_required
def training_dashboard(request):
    """لوحة تحكم التدريب"""
    
    # إحصائيات عامة
    total_programs = TrainingProgram.objects.filter(is_active=True).count()
    upcoming_sessions = TrainingSession.objects.filter(
        scheduled_date__gte=timezone.now(),
        status='scheduled'
    ).count()
    
    # إحصائيات المستخدم
    user_records = TrainingRecord.objects.filter(trainee=request.user)
    completed_trainings = user_records.filter(status='completed').count()
    enrolled_trainings = user_records.filter(status='enrolled').count()
    
    # التدريبات المستحقة
    overdue_trainings = user_records.filter(
        certificate_expiry_date__lt=timezone.now().date(),
        status='completed'
    ).count()
    
    # التدريبات الإلزامية المطلوبة
    mandatory_programs = TrainingProgram.objects.filter(
        is_mandatory=True,
        is_active=True
    )
    
    # فلترة حسب القسم إذا كان محدداً
    if request.user.department:
        mandatory_programs = mandatory_programs.filter(
            Q(target_departments__isnull=True) |
            Q(target_departments__department=request.user.department)
        ).distinct()
    
    # التدريبات الإلزامية غير المكتملة
    completed_program_ids = user_records.filter(
        status='completed',
        certificate_expiry_date__gte=timezone.now().date()
    ).values_list('session__program_id', flat=True)
    
    pending_mandatory = mandatory_programs.exclude(
        id__in=completed_program_ids
    ).count()
    
    # الجلسات القادمة للمستخدم
    upcoming_user_sessions = TrainingSession.objects.filter(
        participants__trainee=request.user,
        participants__status='enrolled',
        scheduled_date__gte=timezone.now(),
        status='scheduled'
    ).order_by('scheduled_date')[:5]
    
    # آخر التقييمات
    recent_evaluations = TrainingEvaluation.objects.filter(
        training_record__session__program__created_by=request.user
    ).select_related(
        'training_record__trainee',
        'training_record__session__program'
    ).order_by('-submitted_date')[:5]
    
    # معدل الفعالية
    effectiveness_avg = TrainingEvaluation.objects.filter(
        training_record__session__scheduled_date__gte=timezone.now() - timedelta(days=90)
    ).aggregate(
        avg_score=Avg('overall_rating')
    )['avg_score'] or 0
    
    # نسبة الامتثال
    if mandatory_programs.count() > 0:
        compliance_rate = ((mandatory_programs.count() - pending_mandatory) / 
                          mandatory_programs.count() * 100)
    else:
        compliance_rate = 100
    
    context = {
        'total_programs': total_programs,
        'upcoming_sessions': upcoming_sessions,
        'completed_trainings': completed_trainings,
        'enrolled_trainings': enrolled_trainings,
        'overdue_trainings': overdue_trainings,
        'pending_mandatory': pending_mandatory,
        'upcoming_user_sessions': upcoming_user_sessions,
        'recent_evaluations': recent_evaluations,
        'effectiveness_avg': effectiveness_avg,
        'compliance_rate': compliance_rate,
    }
    
    return render(request, 'training/dashboard.html', context)


@login_required
def program_list(request):
    """قائمة البرامج التدريبية"""
    form = TrainingSearchForm(request.GET)
    programs = TrainingProgram.objects.filter(is_active=True)
    
    # تطبيق الفلاتر
    if form.is_valid():
        search = form.cleaned_data.get('search')
        if search:
            programs = programs.filter(
                Q(title__icontains=search) |
                Q(title_en__icontains=search) |
                Q(program_id__icontains=search) |
                Q(description__icontains=search)
            )
        
        if form.cleaned_data.get('training_type'):
            programs = programs.filter(training_type=form.cleaned_data['training_type'])
        
        if form.cleaned_data.get('delivery_method'):
            programs = programs.filter(delivery_method=form.cleaned_data['delivery_method'])
    
    # إضافة معلومات إضافية
    programs = programs.annotate(
        sessions_count=Count('sessions'),
        participants_count=Count('sessions__participants')
    )
    
    # التصفح
    paginator = Paginator(programs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'training/program_list.html', {
        'form': form,
        'page_obj': page_obj,
    })


@login_required
def program_detail(request, pk):
    """تفاصيل البرنامج التدريبي"""
    program = get_object_or_404(TrainingProgram, pk=pk)
    
    # الجلسات القادمة
    upcoming_sessions = program.sessions.filter(
        scheduled_date__gte=timezone.now(),
        status='scheduled'
    ).order_by('scheduled_date')[:5]
    
    # إحصائيات البرنامج
    stats = {
        'total_sessions': program.sessions.count(),
        'total_participants': TrainingRecord.objects.filter(
            session__program=program
        ).count(),
        'completion_rate': 0,
        'average_score': 0,
        'effectiveness_rating': 0,
    }
    
    # حساب معدل الإكمال
    if stats['total_participants'] > 0:
        completed = TrainingRecord.objects.filter(
            session__program=program,
            status='completed'
        ).count()
        stats['completion_rate'] = (completed / stats['total_participants']) * 100
    
    # متوسط الدرجات
    avg_score = TrainingRecord.objects.filter(
        session__program=program,
        post_test_score__isnull=False
    ).aggregate(avg=Avg('post_test_score'))['avg'] or 0
    stats['average_score'] = avg_score
    
    # تقييم الفعالية
    effectiveness = TrainingEvaluation.objects.filter(
        training_record__session__program=program
    ).aggregate(avg=Avg('overall_rating'))['avg'] or 0
    stats['effectiveness_rating'] = effectiveness
    
    # المواد التدريبية
    materials = program.materials.all().order_by('order')
    
    # التحقق من صلاحيات المستخدم
    can_edit = (
        request.user == program.created_by or
        request.user.is_staff or
        request.user.has_perm('training.change_trainingprogram')
    )
    
    can_create_session = (
        request.user.is_staff or
        request.user.has_perm('training.add_trainingsession') or
        request.user == program.trainer
    )
    
    return render(request, 'training/program_detail.html', {
        'program': program,
        'upcoming_sessions': upcoming_sessions,
        'stats': stats,
        'materials': materials,
        'can_edit': can_edit,
        'can_create_session': can_create_session,
    })


@login_required
@permission_required('training.add_trainingprogram', raise_exception=True)
def program_create(request):
    """إنشاء برنامج تدريبي جديد"""
    if request.method == 'POST':
        form = TrainingProgramForm(request.POST)
        if form.is_valid():
            program = form.save(commit=False)
            program.created_by = request.user
            program.save()
            form.save_m2m()
            
            # سجل التدقيق
            create_audit_log(
                request.user, 'create', request,
                model_name='TrainingProgram',
                object_id=program.id,
                object_repr=str(program)
            )
            
            messages.success(request, _('Training program created successfully.'))
            return redirect('training:program_detail', pk=program.pk)
    else:
        form = TrainingProgramForm()
        
        # توليد معرف تلقائي
        last_program = TrainingProgram.objects.order_by('-created_date').first()
        if last_program:
            try:
                parts = last_program.program_id.split('-')
                number = int(parts[-1]) + 1
                suggested_id = f"TRN-{parts[1]}-{number:03d}"
            except:
                suggested_id = "TRN-GEN-001"
        else:
            suggested_id = "TRN-GEN-001"
        
        form.initial['program_id'] = suggested_id
    
    return render(request, 'training/program_form.html', {
        'form': form,
        'title': _('Create Training Program'),
    })


@login_required
def session_list(request):
    """قائمة الجلسات التدريبية"""
    sessions = TrainingSession.objects.select_related('program', 'trainer')
    
    # فلترة حسب الحالة
    status_filter = request.GET.get('status')
    if status_filter:
        sessions = sessions.filter(status=status_filter)
    
    # فلترة حسب التاريخ
    date_filter = request.GET.get('date_filter')
    if date_filter == 'upcoming':
        sessions = sessions.filter(
            scheduled_date__gte=timezone.now(),
            status='scheduled'
        )
    elif date_filter == 'past':
        sessions = sessions.filter(
            scheduled_date__lt=timezone.now()
        )
    elif date_filter == 'this_month':
        sessions = sessions.filter(
            scheduled_date__month=timezone.now().month,
            scheduled_date__year=timezone.now().year
        )
    
    # إضافة معلومات المشاركين
    sessions = sessions.annotate(
        enrolled_count=Count('participants', filter=Q(participants__status='enrolled')),
        attended_count=Count('participants', filter=Q(participants__status='attended')),
        completed_count=Count('participants', filter=Q(participants__status='completed'))
    )
    
    # الترتيب
    sessions = sessions.order_by('-scheduled_date')
    
    # التصفح
    paginator = Paginator(sessions, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'training/session_list.html', {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'date_filter': date_filter,
    })


@login_required
def session_detail(request, pk):
    """تفاصيل الجلسة التدريبية"""
    session = get_object_or_404(
        TrainingSession.objects.select_related('program', 'trainer'),
        pk=pk
    )
    
    # قائمة المشاركين
    participants = TrainingRecord.objects.filter(
        session=session
    ).select_related('trainee').order_by('trainee__last_name', 'trainee__first_name')
    
    # إحصائيات الجلسة
    stats = {
        'enrolled': participants.filter(status='enrolled').count(),
        'attended': participants.filter(status='attended').count(),
        'completed': participants.filter(status='completed').count(),
        'failed': participants.filter(status='failed').count(),
        'absent': participants.filter(status='absent').count(),
    }
    
    # متوسط الدرجات
    test_stats = participants.filter(
        post_test_score__isnull=False
    ).aggregate(
        avg_pre=Avg('pre_test_score'),
        avg_post=Avg('post_test_score'),
        pass_rate=Count('id', filter=Q(
            post_test_score__gte=session.program.passing_score
        )) * 100.0 / Count('id')
    )
    
    # التحقق من الصلاحيات
    is_trainer = request.user == session.trainer
    is_participant = participants.filter(trainee=request.user).exists()
    can_manage = (
        is_trainer or
        request.user.is_staff or
        request.user.has_perm('training.change_trainingsession')
    )
    
    # سجل المستخدم في هذه الجلسة
    user_record = None
    if is_participant:
        user_record = participants.get(trainee=request.user)
    
    return render(request, 'training/session_detail.html', {
        'session': session,
        'participants': participants,
        'stats': stats,
        'test_stats': test_stats,
        'is_trainer': is_trainer,
        'is_participant': is_participant,
        'can_manage': can_manage,
        'user_record': user_record,
    })


@login_required
def session_create(request):
    """إنشاء جلسة تدريبية"""
    # التحقق من الصلاحية
    if not (request.user.is_staff or 
            request.user.has_perm('training.add_trainingsession')):
        # التحقق إذا كان المستخدم مدرباً لأي برنامج
        trainer_programs = TrainingProgram.objects.filter(
            trainer=request.user,
            is_active=True
        )
        if not trainer_programs.exists():
            messages.error(request, _('You do not have permission to create training sessions.'))
            return redirect('training:session_list')
    
    if request.method == 'POST':
        form = TrainingSessionForm(request.POST)
        if form.is_valid():
            session = form.save(commit=False)
            session.created_by = request.user
            session.save()
            
            # سجل التدقيق
            create_audit_log(
                request.user, 'create', request,
                model_name='TrainingSession',
                object_id=session.id,
                object_repr=str(session)
            )
            
            messages.success(request, _('Training session created successfully.'))
            return redirect('training:session_detail', pk=session.pk)
    else:
        form = TrainingSessionForm()
        
        # إذا تم تحديد برنامج في المعاملات
        program_id = request.GET.get('program')
        if program_id:
            try:
                program = TrainingProgram.objects.get(pk=program_id)
                form.initial['program'] = program
                form.initial['trainer'] = program.trainer or request.user
            except TrainingProgram.DoesNotExist:
                pass
    
    return render(request, 'training/session_form.html', {
        'form': form,
        'title': _('Create Training Session'),
    })


@login_required
def session_enroll(request, pk):
    """تسجيل المتدربين في الجلسة"""
    session = get_object_or_404(TrainingSession, pk=pk)
    
    # التحقق من الصلاحية
    if not (request.user == session.trainer or
            request.user.is_staff or
            request.user.has_perm('training.change_trainingsession')):
        messages.error(request, _('You do not have permission to enroll trainees.'))
        return redirect('training:session_detail', pk=pk)
    
    # التحقق من حالة الجلسة
    if session.status != 'scheduled':
        messages.error(request, _('Cannot enroll trainees in a session that is not scheduled.'))
        return redirect('training:session_detail', pk=pk)
    
    if request.method == 'POST':
        form = TrainingEnrollmentForm(session, request.POST)
        if form.is_valid():
            trainees = form.cleaned_data['trainees']
            enrolled_count = 0
            
            for trainee in trainees:
                # إنشاء سجل تدريب
                record, created = TrainingRecord.objects.get_or_create(
                    trainee=trainee,
                    session=session,
                    defaults={'status': 'enrolled'}
                )
                
                if created:
                    enrolled_count += 1
                    
                    # سجل التدقيق
                    create_audit_log(
                        request.user, 'create', request,
                        model_name='TrainingRecord',
                        object_id=record.id,
                        object_repr=f"{trainee.get_full_name()} enrolled in {session}"
                    )
            
            if enrolled_count > 0:
                messages.success(
                    request,
                    _('%(count)d trainee(s) enrolled successfully.') % {'count': enrolled_count}
                )
                
                # إرسال الإشعارات إذا طُلب ذلك
                if form.cleaned_data.get('send_notification'):
                    # TODO: إضافة وظيفة إرسال البريد الإلكتروني
                    pass
            
            return redirect('training:session_detail', pk=pk)
    else:
        form = TrainingEnrollmentForm(session)
    
    return render(request, 'training/session_enroll.html', {
        'form': form,
        'session': session,
    })


@login_required
def my_training(request):
    """التدريبات الخاصة بي"""
    # سجلات التدريب
    training_records = TrainingRecord.objects.filter(
        trainee=request.user
    ).select_related(
        'session__program', 'session__trainer'
    ).order_by('-enrolled_date')
    
    # فلترة حسب الحالة
    status_filter = request.GET.get('status')
    if status_filter:
        training_records = training_records.filter(status=status_filter)
    
    # التدريبات الحالية
    current_trainings = training_records.filter(
        status__in=['enrolled', 'attended'],
        session__scheduled_date__gte=timezone.now()
    )
    
    # التدريبات المكتملة
    completed_trainings = training_records.filter(status='completed')
    
    # الشهادات الصالحة
    valid_certificates = completed_trainings.filter(
        certificate_expiry_date__gte=timezone.now().date()
    )
    
    # الشهادات المنتهية
    expired_certificates = completed_trainings.filter(
        certificate_expiry_date__lt=timezone.now().date()
    )
    
    # التدريبات الإلزامية المطلوبة
    mandatory_programs = TrainingProgram.objects.filter(
        is_mandatory=True,
        is_active=True
    )
    
    if request.user.department:
        mandatory_programs = mandatory_programs.filter(
            Q(target_departments__isnull=True) |
            Q(target_departments__department=request.user.department)
        ).distinct()
    
    # استبعاد البرامج المكتملة
    completed_program_ids = valid_certificates.values_list(
        'session__program_id', flat=True
    )
    pending_mandatory = mandatory_programs.exclude(
        id__in=completed_program_ids
    )
    
    return render(request, 'training/my_training.html', {
        'current_trainings': current_trainings,
        'completed_trainings': completed_trainings,
        'valid_certificates': valid_certificates,
        'expired_certificates': expired_certificates,
        'pending_mandatory': pending_mandatory,
        'status_filter': status_filter,
    })


@login_required
def record_certificate(request, pk):
    """عرض/تحميل الشهادة"""
    record = get_object_or_404(
        TrainingRecord.objects.select_related('trainee', 'session__program'),
        pk=pk
    )
    
    # التحقق من الصلاحية
    if not (request.user == record.trainee or
            request.user.is_staff or
            request.user.has_perm('training.view_trainingrecord')):
        messages.error(request, _('You do not have permission to view this certificate.'))
        return redirect('training:my_training')
    
    # التحقق من وجود الشهادة
    if record.status != 'completed' or not record.certificate_number:
        messages.error(request, _('No certificate available for this training.'))
        return redirect('training:my_training')
    
    # إنشاء PDF للشهادة
    template = get_template('training/certificate.html')
    context = {
        'record': record,
        'trainee': record.trainee,
        'program': record.session.program,
        'session': record.session,
        'issue_date': record.certificate_issued_date,
        'expiry_date': record.certificate_expiry_date,
        'certificate_number': record.certificate_number,
    }
    
    html = template.render(context)
    
    # إنشاء PDF
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
    
    if not pdf.err:
        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'filename="certificate_{record.certificate_number}.pdf"'
        
        # سجل التدقيق
        create_audit_log(
            request.user, 'download', request,
            model_name='TrainingRecord',
            object_id=record.id,
            object_repr=f"Certificate {record.certificate_number}"
        )
        
        return response
    
    messages.error(request, _('Error generating certificate.'))
    return redirect('training:record_detail', pk=pk)


@login_required
def session_attendance(request, pk):
    """تسجيل حضور الجلسة"""
    session = get_object_or_404(TrainingSession, pk=pk)
    
    # التحقق من الصلاحية
    if not (request.user == session.trainer or
            request.user.is_staff or
            request.user.has_perm('training.change_trainingsession')):
        messages.error(request, _('You do not have permission to record attendance.'))
        return redirect('training:session_detail', pk=pk)
    
    # التحقق من حالة الجلسة
    if session.status not in ['scheduled', 'in_progress']:
        messages.error(request, _('Cannot record attendance for this session.'))
        return redirect('training:session_detail', pk=pk)
    
    if request.method == 'POST':
        form = TrainingAttendanceForm(session, request.POST)
        if form.is_valid():
            # تحديث حالة الجلسة
            if session.status == 'scheduled':
                session.status = 'in_progress'
                session.actual_date = timezone.now()
                session.save()
            
            # معالجة الحضور
            for field_name, value in form.cleaned_data.items():
                if field_name.startswith('attendance_'):
                    record_id = int(field_name.replace('attendance_', ''))
                    try:
                        record = TrainingRecord.objects.get(
                            pk=record_id,
                            session=session
                        )
                        
                        if value:  # حضر
                            record.status = 'attended'
                            record.attendance_date = timezone.now()
                            
                            # التحقق من التوقيع الإلكتروني
                            sig_field = f'signature_{record_id}'
                            signature = form.cleaned_data.get(sig_field)
                            if signature and record.trainee.check_password(signature):
                                record.attendance_signature = record.trainee.electronic_signature
                        else:  # غائب
                            record.status = 'absent'
                        
                        record.save()
                        
                    except TrainingRecord.DoesNotExist:
                        continue
            
            messages.success(request, _('Attendance recorded successfully.'))
            return redirect('training:session_detail', pk=pk)
    else:
        form = TrainingAttendanceForm(session)
    
    return render(request, 'training/session_attendance.html', {
        'form': form,
        'session': session,
    })


@login_required
def record_test(request, pk):
    """إدخال نتائج الاختبار"""
    record = get_object_or_404(TrainingRecord, pk=pk)
    
    # التحقق من الصلاحية
    if not (request.user == record.session.trainer or
            request.user.is_staff or
            request.user.has_perm('training.change_trainingrecord')):
        messages.error(request, _('You do not have permission to enter test results.'))
        return redirect('training:session_detail', pk=record.session.pk)
    
    # التحقق من حالة السجل
    if record.status not in ['attended', 'completed']:
        messages.error(request, _('Cannot enter test results for this record.'))
        return redirect('training:session_detail', pk=record.session.pk)
    
    if request.method == 'POST':
        form = TrainingTestForm(request.POST, instance=record)
        if form.is_valid():
            record = form.save(commit=False)
            record.test_date = timezone.now()
            
            # التحقق من النجاح/الرسوب
            if record.post_test_score is not None:
                if record.post_test_score >= record.session.program.passing_score:
                    record.status = 'completed'
                    record.completed_date = timezone.now()
                else:
                    record.status = 'failed'
            
            record.save()
            
            messages.success(request, _('Test results saved successfully.'))
            return redirect('training:session_detail', pk=record.session.pk)
    else:
        form = TrainingTestForm(instance=record)
    
    return render(request, 'training/record_test.html', {
        'form': form,
        'record': record,
    })


@login_required
def record_evaluate(request, pk):
    """تقييم التدريب"""
    record = get_object_or_404(TrainingRecord, pk=pk)
    
    # التحقق من الصلاحية (المتدرب فقط يمكنه التقييم)
    if request.user != record.trainee:
        messages.error(request, _('You can only evaluate your own training.'))
        return redirect('training:my_training')
    
    # التحقق من حالة السجل
    if record.status != 'completed':
        messages.error(request, _('You can only evaluate completed training.'))
        return redirect('training:my_training')
    
    # التحقق من وجود تقييم سابق
    if hasattr(record, 'evaluation'):
        messages.info(request, _('You have already evaluated this training.'))
        return redirect('training:record_detail', pk=pk)
    
    if request.method == 'POST':
        form = TrainingEvaluationForm(request.POST)
        if form.is_valid():
            evaluation = form.save(commit=False)
            evaluation.training_record = record
            evaluation.save()
            
            # تحديث سجل التدريب
            record.effectiveness_score = evaluation.overall_rating
            record.save()
            
            messages.success(request, _('Thank you for your evaluation!'))
            return redirect('training:record_detail', pk=pk)
    else:
        form = TrainingEvaluationForm()
    
    return render(request, 'training/record_evaluate.html', {
        'form': form,
        'record': record,
    })


@login_required
def record_detail(request, pk):
    """تفاصيل سجل التدريب"""
    record = get_object_or_404(
        TrainingRecord.objects.select_related(
            'trainee', 'session__program', 'session__trainer'
        ),
        pk=pk
    )
    
    # التحقق من الصلاحية
    if not (request.user == record.trainee or
            request.user == record.session.trainer or
            request.user.is_staff or
            request.user.has_perm('training.view_trainingrecord')):
        messages.error(request, _('You do not have permission to view this record.'))
        return redirect('training:my_training')
    
    # جلب التقييم إن وجد
    evaluation = None
    if hasattr(record, 'evaluation'):
        evaluation = record.evaluation
    
    return render(request, 'training/record_detail.html', {
        'record': record,
        'evaluation': evaluation,
    })


@login_required
def session_complete(request, pk):
    """إكمال الجلسة التدريبية"""
    session = get_object_or_404(TrainingSession, pk=pk)
    
    # التحقق من الصلاحية
    if not (request.user == session.trainer or
            request.user.is_staff or
            request.user.has_perm('training.change_trainingsession')):
        messages.error(request, _('You do not have permission to complete this session.'))
        return redirect('training:session_detail', pk=pk)
    
    if request.method == 'POST':
        # تحديث حالة الجلسة
        session.status = 'completed'
        session.save()
        
        # إنشاء الشهادات للناجحين
        completed_count = 0
        for record in session.participants.filter(status='completed'):
            if not record.certificate_number:
                record.save()  # سيتم توليد الشهادة تلقائياً
                completed_count += 1
        
        messages.success(
            request,
            _('Session completed. %(count)d certificates generated.') % {
                'count': completed_count
            }
        )
        
        return redirect('training:session_detail', pk=pk)
    
    # عرض ملخص الجلسة
    stats = {
        'total': session.participants.count(),
        'attended': session.participants.filter(status='attended').count(),
        'completed': session.participants.filter(status='completed').count(),
        'failed': session.participants.filter(status='failed').count(),
        'absent': session.participants.filter(status='absent').count(),
    }
    
    return render(request, 'training/session_complete.html', {
        'session': session,
        'stats': stats,
    })


@login_required
def program_edit(request, pk):
    """تعديل البرنامج التدريبي"""
    program = get_object_or_404(TrainingProgram, pk=pk)
    
    # التحقق من الصلاحية
    if not (request.user == program.created_by or
            request.user.is_staff or
            request.user.has_perm('training.change_trainingprogram')):
        messages.error(request, _('You do not have permission to edit this program.'))
        return redirect('training:program_detail', pk=pk)
    
    if request.method == 'POST':
        form = TrainingProgramForm(request.POST, instance=program)
        if form.is_valid():
            program = form.save()
            
            # سجل التدقيق
            create_audit_log(
                request.user, 'update', request,
                model_name='TrainingProgram',
                object_id=program.id,
                object_repr=str(program)
            )
            
            messages.success(request, _('Training program updated successfully.'))
            return redirect('training:program_detail', pk=program.pk)
    else:
        form = TrainingProgramForm(instance=program)
    
    return render(request, 'training/program_form.html', {
        'form': form,
        'program': program,
        'title': _('Edit Training Program'),
    })


@login_required
def session_edit(request, pk):
    """تعديل الجلسة التدريبية"""
    session = get_object_or_404(TrainingSession, pk=pk)
    
    # التحقق من الصلاحية
    if not (request.user == session.trainer or
            request.user == session.created_by or
            request.user.is_staff or
            request.user.has_perm('training.change_trainingsession')):
        messages.error(request, _('You do not have permission to edit this session.'))
        return redirect('training:session_detail', pk=pk)
    
    # لا يمكن تعديل جلسة مكتملة
    if session.status == 'completed':
        messages.error(request, _('Cannot edit a completed session.'))
        return redirect('training:session_detail', pk=pk)
    
    if request.method == 'POST':
        form = TrainingSessionForm(request.POST, instance=session)
        if form.is_valid():
            session = form.save()
            
            # سجل التدقيق
            create_audit_log(
                request.user, 'update', request,
                model_name='TrainingSession',
                object_id=session.id,
                object_repr=str(session)
            )
            
            messages.success(request, _('Training session updated successfully.'))
            return redirect('training:session_detail', pk=session.pk)
    else:
        form = TrainingSessionForm(instance=session)
    
    return render(request, 'training/session_form.html', {
        'form': form,
        'session': session,
        'title': _('Edit Training Session'),
    })


@login_required
def program_materials(request, pk):
    """عرض المواد التدريبية"""
    program = get_object_or_404(TrainingProgram, pk=pk)
    materials = program.materials.all().order_by('order')
    
    return render(request, 'training/program_materials.html', {
        'program': program,
        'materials': materials,
    })


@login_required
def material_add(request, pk):
    """إضافة مادة تدريبية"""
    program = get_object_or_404(TrainingProgram, pk=pk)
    
    # التحقق من الصلاحية
    if not (request.user == program.created_by or
            request.user == program.trainer or
            request.user.is_staff or
            request.user.has_perm('training.add_trainingmaterial')):
        messages.error(request, _('You do not have permission to add materials.'))
        return redirect('training:program_materials', pk=pk)
    
    if request.method == 'POST':
        # معالجة رفع الملف
        title = request.POST.get('title')
        description = request.POST.get('description', '')
        material_type = request.POST.get('material_type')
        file = request.FILES.get('file')
        order = request.POST.get('order', 0)
        is_mandatory = request.POST.get('is_mandatory') == 'on'
        
        if title and file and material_type:
            material = TrainingMaterial.objects.create(
                program=program,
                title=title,
                description=description,
                material_type=material_type,
                file=file,
                order=order,
                is_mandatory=is_mandatory,
                uploaded_by=request.user
            )
            
            messages.success(request, _('Material added successfully.'))
            return redirect('training:program_materials', pk=pk)
        else:
            messages.error(request, _('Please fill all required fields.'))
    
    return render(request, 'training/material_add.html', {
        'program': program,
    })


@login_required
def training_reports(request):
    """تقارير التدريب"""
    if not (request.user.is_staff or
            request.user.has_perm('training.view_trainingprogram')):
        messages.error(request, _('You do not have permission to view reports.'))
        return redirect('training:dashboard')
    
    return render(request, 'training/reports.html')


@login_required
def compliance_report(request):
    """تقرير الامتثال التدريبي"""
    if not (request.user.is_staff or
            request.user.has_perm('training.view_trainingprogram')):
        messages.error(request, _('You do not have permission to view this report.'))
        return redirect('training:dashboard')
    
    # البرامج الإلزامية
    mandatory_programs = TrainingProgram.objects.filter(
        is_mandatory=True,
        is_active=True
    )
    
    # الموظفون النشطون
    employees = User.objects.filter(is_active=True)
    
    # حساب الامتثال لكل موظف
    compliance_data = []
    for employee in employees:
        employee_data = {
            'employee': employee,
            'programs': [],
            'compliance_rate': 0
        }
        
        required_count = 0
        completed_count = 0
        
        for program in mandatory_programs:
            # التحقق إذا كان البرنامج مطلوباً لهذا الموظف
            if (not program.target_departments.exists() or
                employee.department in program.target_departments.values_list('department', flat=True)):
                
                required_count += 1
                
                # التحقق من إكمال التدريب
                latest_record = TrainingRecord.objects.filter(
                    trainee=employee,
                    session__program=program,
                    status='completed'
                ).order_by('-completed_date').first()
                
                program_status = {
                    'program': program,
                    'status': 'not_started',
                    'record': None,
                    'is_expired': False
                }
                
                if latest_record:
                    program_status['record'] = latest_record
                    program_status['status'] = 'completed'
                    
                    if latest_record.certificate_expiry_date:
                        if latest_record.certificate_expiry_date < timezone.now().date():
                            program_status['is_expired'] = True
                            program_status['status'] = 'expired'
                        else:
                            completed_count += 1
                    else:
                        completed_count += 1
                
                employee_data['programs'].append(program_status)
        
        if required_count > 0:
            employee_data['compliance_rate'] = (completed_count / required_count) * 100
        
        compliance_data.append(employee_data)
    
    # فلترة وترتيب
    sort_by = request.GET.get('sort', 'name')
    if sort_by == 'compliance':
        compliance_data.sort(key=lambda x: x['compliance_rate'])
    elif sort_by == 'department':
        compliance_data.sort(key=lambda x: x['employee'].department or '')
    else:
        compliance_data.sort(key=lambda x: x['employee'].get_full_name())
    
    return render(request, 'training/compliance_report.html', {
        'compliance_data': compliance_data,
        'mandatory_programs': mandatory_programs,
    })


@login_required
def effectiveness_report(request):
    """تقرير فعالية التدريب"""
    if not (request.user.is_staff or
            request.user.has_perm('training.view_trainingevaluation')):
        messages.error(request, _('You do not have permission to view this report.'))
        return redirect('training:dashboard')
    
    # فترة التقرير
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    evaluations = TrainingEvaluation.objects.all()
    
    if date_from:
        evaluations = evaluations.filter(submitted_date__gte=date_from)
    if date_to:
        evaluations = evaluations.filter(submitted_date__lte=date_to)
    
    # تجميع البيانات حسب البرنامج
    program_stats = {}
    
    for evaluation in evaluations.select_related('training_record__session__program'):
        program = evaluation.training_record.session.program
        
        if program.id not in program_stats:
            program_stats[program.id] = {
                'program': program,
                'evaluations': [],
                'avg_content_relevance': 0,
                'avg_content_clarity': 0,
                'avg_trainer_knowledge': 0,
                'avg_overall_rating': 0,
                'would_recommend_rate': 0,
                'count': 0
            }
        
        stats = program_stats[program.id]
        stats['evaluations'].append(evaluation)
        stats['count'] += 1
    
    # حساب المتوسطات
    for program_id, stats in program_stats.items():
        evaluations = stats['evaluations']
        count = len(evaluations)
        
        if count > 0:
            stats['avg_content_relevance'] = sum(e.content_relevance for e in evaluations) / count
            stats['avg_content_clarity'] = sum(e.content_clarity for e in evaluations) / count
            stats['avg_trainer_knowledge'] = sum(e.trainer_knowledge for e in evaluations) / count
            stats['avg_overall_rating'] = sum(e.overall_rating for e in evaluations) / count
            stats['would_recommend_rate'] = sum(1 for e in evaluations if e.would_recommend) / count * 100
    
    return render(request, 'training/effectiveness_report.html', {
        'program_stats': program_stats.values(),
        'date_from': date_from,
        'date_to': date_to,
    })


@login_required
def attendance_report(request):
    """تقرير الحضور"""
    if not (request.user.is_staff or
            request.user.has_perm('training.view_trainingsession')):
        messages.error(request, _('You do not have permission to view this report.'))
        return redirect('training:dashboard')
    
    # فترة التقرير
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    sessions = TrainingSession.objects.filter(status__in=['completed', 'in_progress'])
    
    if date_from:
        sessions = sessions.filter(scheduled_date__gte=date_from)
    if date_to:
        sessions = sessions.filter(scheduled_date__lte=date_to)
    
    # إضافة إحصائيات الحضور
    sessions = sessions.annotate(
        total_enrolled=Count('participants'),
        total_attended=Count('participants', filter=Q(participants__status='attended')),
        total_completed=Count('participants', filter=Q(participants__status='completed')),
        total_absent=Count('participants', filter=Q(participants__status='absent'))
    )
    
    return render(request, 'training/attendance_report.html', {
        'sessions': sessions,
        'date_from': date_from,
        'date_to': date_to,
    })


# واجهات برمجة التطبيقات (APIs)
@login_required
def sessions_calendar_api(request):
    """API للحصول على الجلسات للتقويم"""
    start = request.GET.get('start')
    end = request.GET.get('end')
    
    sessions = TrainingSession.objects.filter(
        scheduled_date__gte=start,
        scheduled_date__lte=end
    ).select_related('program', 'trainer')
    
    events = []
    for session in sessions:
        # تحديد اللون حسب الحالة
        color_map = {
            'scheduled': '#0d6efd',  # أزرق
            'in_progress': '#ffc107',  # أصفر
            'completed': '#198754',  # أخضر
            'cancelled': '#dc3545',  # أحمر
        }
        
        events.append({
            'id': session.id,
            'title': f"{session.program.title} ({session.session_code})",
            'start': session.scheduled_date.isoformat(),
            'url': f'/training/sessions/{session.id}/',
            'backgroundColor': color_map.get(session.status, '#6c757d'),
            'extendedProps': {
                'trainer': session.trainer.get_full_name(),
                'location': session.location,
                'participants': session.participants_count,
                'max_participants': session.max_participants,
                'status': session.get_status_display()
            }
        })
    
    return JsonResponse(events, safe=False)


@login_required
def training_stats_api(request):
    """API لإحصائيات التدريب"""
    # إحصائيات عامة
    stats = {
        'total_programs': TrainingProgram.objects.filter(is_active=True).count(),
        'total_sessions': TrainingSession.objects.count(),
        'total_participants': TrainingRecord.objects.count(),
        'completion_rate': 0,
        'average_effectiveness': 0,
    }
    
    # معدل الإكمال
    if stats['total_participants'] > 0:
        completed = TrainingRecord.objects.filter(status='completed').count()
        stats['completion_rate'] = round((completed / stats['total_participants']) * 100, 2)
    
    # متوسط الفعالية
    effectiveness = TrainingEvaluation.objects.aggregate(
        avg=Avg('overall_rating')
    )['avg']
    
    if effectiveness:
        stats['average_effectiveness'] = round(effectiveness, 2)
    
    # إحصائيات شهرية
    monthly_stats = []
    for i in range(6):
        date = timezone.now() - timedelta(days=30 * i)
        month_data = {
            'month': date.strftime('%B %Y'),
            'sessions': TrainingSession.objects.filter(
                scheduled_date__year=date.year,
                scheduled_date__month=date.month
            ).count(),
            'participants': TrainingRecord.objects.filter(
                enrolled_date__year=date.year,
                enrolled_date__month=date.month
            ).count()
        }
        monthly_stats.append(month_data)
    
    return JsonResponse({
        'stats': stats,
        'monthly': monthly_stats
    })