# reports/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.db.models import Count, Q, Avg, Sum, F
from django.template.loader import render_to_string
from datetime import datetime, timedelta, date
import json
import csv
import xlwt
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

from deviations.models import Deviation, DeviationTrendAnalysis
from capa.models import CAPA, CAPAEffectivenessCheck
from change_control.models import ChangeControl
from accounts.models import User
from core.integration import QMSIntegrationManager


class QMSReportGenerator:
    """مولد التقارير الشاملة لأنظمة QMS"""
    
    @staticmethod
    def generate_executive_summary_report(start_date, end_date, format='pdf'):
        """توليد تقرير الملخص التنفيذي"""
        
        # جمع البيانات
        summary_data = {
            'period': f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
            'deviations': QMSReportGenerator._get_deviation_summary(start_date, end_date),
            'capas': QMSReportGenerator._get_capa_summary(start_date, end_date),
            'changes': QMSReportGenerator._get_change_summary(start_date, end_date),
            'integration_metrics': QMSReportGenerator._get_integration_metrics(start_date, end_date),
            'trends': QMSReportGenerator._get_trend_analysis(start_date, end_date),
            'recommendations': QMSReportGenerator._generate_recommendations(start_date, end_date),
        }
        
        if format == 'pdf':
            return QMSReportGenerator._create_pdf_report(summary_data, 'Executive Summary')
        elif format == 'excel':
            return QMSReportGenerator._create_excel_report(summary_data, 'Executive Summary')
        else:
            return summary_data
    
    @staticmethod
    def generate_deviation_analysis_report(start_date, end_date, filters=None):
        """تقرير تحليل الانحرافات المفصل"""
        
        deviations = Deviation.objects.filter(
            reported_date__range=[start_date, end_date]
        )
        
        # تطبيق الفلاتر
        if filters:
            if filters.get('department'):
                deviations = deviations.filter(department=filters['department'])
            if filters.get('severity'):
                deviations = deviations.filter(severity=filters['severity'])
            if filters.get('type'):
                deviations = deviations.filter(deviation_type=filters['type'])
        
        analysis_data = {
            'total_deviations': deviations.count(),
            'by_severity': deviations.values('severity').annotate(count=Count('id')),
            'by_type': deviations.values('deviation_type').annotate(count=Count('id')),
            'by_department': deviations.values('department').annotate(count=Count('id')),
            'by_month': QMSReportGenerator._get_monthly_breakdown(deviations, 'reported_date'),
            'top_products': deviations.values('affected_products__product_name').annotate(count=Count('id')).order_by('-count')[:10],
            'recurring_issues': QMSReportGenerator._identify_recurring_deviations(deviations),
            'resolution_times': QMSReportGenerator._calculate_resolution_times(deviations),
            'cost_impact': QMSReportGenerator._calculate_cost_impact(deviations),
        }
        
        return analysis_data
    
    @staticmethod
    def generate_capa_effectiveness_report(start_date, end_date):
        """تقرير فعالية CAPAs"""
        
        capas = CAPA.objects.filter(
            initiated_date__range=[start_date, end_date]
        )
        
        effectiveness_data = {
            'total_capas': capas.count(),
            'completed_capas': capas.filter(status='closed').count(),
            'effectiveness_checks': QMSReportGenerator._analyze_effectiveness_checks(start_date, end_date),
            'source_analysis': capas.values('source_type').annotate(count=Count('id')),
            'completion_times': QMSReportGenerator._calculate_capa_completion_times(capas),
            'cost_effectiveness': QMSReportGenerator._calculate_capa_cost_effectiveness(capas),
            'recurrence_prevention': QMSReportGenerator._analyze_recurrence_prevention(capas),
            'risk_reduction': QMSReportGenerator._analyze_risk_reduction(capas),
        }
        
        return effectiveness_data
    
    @staticmethod
    def generate_change_control_report(start_date, end_date):
        """تقرير إدارة التغيير"""
        
        changes = ChangeControl.objects.filter(
            submission_date__range=[start_date, end_date]
        )
        
        change_data = {
            'total_changes': changes.count(),
            'by_type': changes.values('change_type').annotate(count=Count('id')),
            'by_category': changes.values('change_category').annotate(count=Count('id')),
            'by_urgency': changes.values('urgency').annotate(count=Count('id')),
            'implementation_success': QMSReportGenerator._calculate_implementation_success(changes),
            'approval_times': QMSReportGenerator._calculate_approval_times(changes),
            'implementation_times': QMSReportGenerator._calculate_implementation_times(changes),
            'cost_analysis': QMSReportGenerator._calculate_change_costs(changes),
            'impact_assessment': QMSReportGenerator._analyze_change_impacts(changes),
        }
        
        return change_data
    
    @staticmethod
    def generate_regulatory_compliance_report(start_date, end_date):
        """تقرير الامتثال التنظيمي"""
        
        compliance_data = {
            'regulatory_deviations': QMSReportGenerator._get_regulatory_deviations(start_date, end_date),
            'regulatory_capas': QMSReportGenerator._get_regulatory_capas(start_date, end_date),
            'regulatory_changes': QMSReportGenerator._get_regulatory_changes(start_date, end_date),
            'notification_requirements': QMSReportGenerator._analyze_notification_requirements(start_date, end_date),
            'compliance_trends': QMSReportGenerator._analyze_compliance_trends(start_date, end_date),
            'audit_findings': QMSReportGenerator._analyze_audit_findings(start_date, end_date),
            'corrective_actions': QMSReportGenerator._analyze_regulatory_corrective_actions(start_date, end_date),
        }
        
        return compliance_data
    
    @staticmethod
    def generate_trend_analysis_report(analysis_period='quarterly'):
        """تقرير تحليل الاتجاهات"""
        
        if analysis_period == 'monthly':
            periods = 12
            delta = timedelta(days=30)
        elif analysis_period == 'quarterly':
            periods = 4
            delta = timedelta(days=90)
        elif analysis_period == 'yearly':
            periods = 3
            delta = timedelta(days=365)
        else:
            periods = 12
            delta = timedelta(days=30)
        
        trend_data = []
        end_date = timezone.now().date()
        
        for i in range(periods):
            period_end = end_date - (delta * i)
            period_start = period_end - delta
            
            period_data = {
                'period': f"{period_start} to {period_end}",
                'deviations': Deviation.objects.filter(
                    reported_date__range=[period_start, period_end]
                ).count(),
                'capas': CAPA.objects.filter(
                    initiated_date__range=[period_start, period_end]
                ).count(),
                'changes': ChangeControl.objects.filter(
                    submission_date__range=[period_start, period_end]
                ).count(),
            }
            
            trend_data.append(period_data)
        
        # تحليل الاتجاهات
        trends_analysis = QMSReportGenerator._analyze_trends(trend_data)
        
        return {
            'period_data': trend_data,
            'trends_analysis': trends_analysis,
            'predictions': QMSReportGenerator._generate_predictions(trend_data),
            'recommendations': QMSReportGenerator._generate_trend_recommendations(trends_analysis),
        }
    
    # دوال مساعدة لتحليل البيانات
    
    @staticmethod
    def _get_deviation_summary(start_date, end_date):
        """ملخص الانحرافات"""
        deviations = Deviation.objects.filter(
            reported_date__range=[start_date, end_date]
        )
        
        return {
            'total': deviations.count(),
            'critical': deviations.filter(severity='critical').count(),
            'major': deviations.filter(severity='major').count(),
            'minor': deviations.filter(severity='minor').count(),
            'closed': deviations.filter(status='closed').count(),
            'avg_resolution_time': QMSReportGenerator._calculate_avg_resolution_time(deviations),
            'total_cost': deviations.aggregate(total=Sum('actual_cost'))['total'] or 0,
        }
    
    @staticmethod
    def _get_capa_summary(start_date, end_date):
        """ملخص CAPAs"""
        capas = CAPA.objects.filter(
            initiated_date__range=[start_date, end_date]
        )
        
        effectiveness_checks = CAPAEffectivenessCheck.objects.filter(
            check_date__range=[start_date, end_date]
        )
        
        return {
            'total': capas.count(),
            'corrective': capas.filter(capa_type='corrective').count(),
            'preventive': capas.filter(capa_type='preventive').count(),
            'closed': capas.filter(status='closed').count(),
            'effective': effectiveness_checks.filter(result='effective').count(),
            'avg_completion_time': QMSReportGenerator._calculate_avg_capa_completion_time(capas),
            'total_cost': capas.aggregate(total=Sum('actual_cost'))['total'] or 0,
        }
    
    @staticmethod
    def _get_change_summary(start_date, end_date):
        """ملخص التغييرات"""
        changes = ChangeControl.objects.filter(
            submission_date__range=[start_date, end_date]
        )
        
        return {
            'total': changes.count(),
            'emergency': changes.filter(change_type='emergency').count(),
            'permanent': changes.filter(change_type='permanent').count(),
            'completed': changes.filter(status='completed').count(),
            'approved': changes.filter(status='approved').count(),
            'avg_implementation_time': QMSReportGenerator._calculate_avg_implementation_time(changes),
        }
    
    @staticmethod
    def _get_integration_metrics(start_date, end_date):
        """مقاييس التكامل"""
        deviations_with_capa = Deviation.objects.filter(
            reported_date__range=[start_date, end_date],
            related_capa__isnull=False
        ).count()
        
        total_deviations = Deviation.objects.filter(
            reported_date__range=[start_date, end_date]
        ).count()
        
        capas_with_changes = CAPA.objects.filter(
            initiated_date__range=[start_date, end_date],
            related_changes__isnull=False
        ).count()
        
        total_capas = CAPA.objects.filter(
            initiated_date__range=[start_date, end_date]
        ).count()
        
        return {
            'deviation_to_capa_rate': (deviations_with_capa / total_deviations) * 100 if total_deviations > 0 else 0,
            'capa_to_change_rate': (capas_with_changes / total_capas) * 100 if total_capas > 0 else 0,
            'integration_effectiveness': QMSReportGenerator._calculate_integration_effectiveness(start_date, end_date),
        }
    
    @staticmethod
    def _calculate_integration_effectiveness(start_date, end_date):
        """حساب فعالية التكامل"""
        # حساب مدى فعالية التكامل بين الأنظمة
        integrated_items = Deviation.objects.filter(
            reported_date__range=[start_date, end_date],
            related_capa__isnull=False,
            related_capa__related_changes__isnull=False
        ).count()
        
        total_deviations = Deviation.objects.filter(
            reported_date__range=[start_date, end_date],
            severity__in=['critical', 'major']
        ).count()
        
        if total_deviations == 0:
            return 100
        
        return round((integrated_items / total_deviations) * 100, 1)
    
    @staticmethod
    def _create_pdf_report(data, title):
        """إنشاء تقرير PDF"""
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        
        # استخدام الأنماط
        styles = getSampleStyleSheet()
        story = []
        
        # العنوان
        title_para = Paragraph(title, styles['Title'])
        story.append(title_para)
        
        # محتوى التقرير
        for section, content in data.items():
            if isinstance(content, dict):
                section_title = Paragraph(section.replace('_', ' ').title(), styles['Heading2'])
                story.append(section_title)
                
                # إنشاء جدول للبيانات
                table_data = []
                for key, value in content.items():
                    table_data.append([key.replace('_', ' ').title(), str(value)])
                
                if table_data:
                    table = Table(table_data)
                    table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 14),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black)
                    ]))
                    story.append(table)
        
        doc.build(story)
        buffer.seek(0)
        return buffer
    
    @staticmethod
    def _create_excel_report(data, title):
        """إنشاء تقرير Excel"""
        response = HttpResponse(content_type='application/ms-excel')
        response['Content-Disposition'] = f'attachment; filename="{title}.xls"'
        
        wb = xlwt.Workbook(encoding='utf-8')
        ws = wb.add_sheet(title[:31])  # أسماء الأوراق محدودة بـ 31 حرف
        
        # أنماط
        header_style = xlwt.easyxf('font: bold on; align: wrap on, vert centre, horiz center')
        
        row_num = 0
        
        # العنوان
        ws.write(row_num, 0, title, header_style)
        row_num += 2
        
        # البيانات
        for section, content in data.items():
            if isinstance(content, dict):
                ws.write(row_num, 0, section.replace('_', ' ').title(), header_style)
                row_num += 1
                
                for key, value in content.items():
                    ws.write(row_num, 0, key.replace('_', ' ').title())
                    ws.write(row_num, 1, str(value))
                    row_num += 1
                
                row_num += 1
        
        wb.save(response)
        return response


# Views للتقارير

@login_required
def reports_dashboard(request):
    """لوحة تحكم التقارير"""
    
    # التقارير المتاحة
    available_reports = [
        {
            'name': 'executive_summary',
            'title': _('Executive Summary'),
            'description': _('High-level overview of all QMS activities'),
            'icon': 'fas fa-chart-line',
            'category': 'management',
        },
        {
            'name': 'deviation_analysis',
            'title': _('Deviation Analysis'),
            'description': _('Detailed analysis of deviations and trends'),
            'icon': 'fas fa-exclamation-triangle',
            'category': 'quality',
        },
        {
            'name': 'capa_effectiveness',
            'title': _('CAPA Effectiveness'),
            'description': _('Analysis of CAPA performance and effectiveness'),
            'icon': 'fas fa-clipboard-check',
            'category': 'quality',
        },
        {
            'name': 'change_control',
            'title': _('Change Control Report'),
            'description': _('Change management activities and outcomes'),
            'icon': 'fas fa-exchange-alt',
            'category': 'operations',
        },
        {
            'name': 'regulatory_compliance',
            'title': _('Regulatory Compliance'),
            'description': _('Compliance status and regulatory activities'),
            'icon': 'fas fa-balance-scale',
            'category': 'regulatory',
        },
        {
            'name': 'trend_analysis',
            'title': _('Trend Analysis'),
            'description': _('Long-term trends and predictive analysis'),
            'icon': 'fas fa-chart-area',
            'category': 'analytics',
        },
    ]
    
    # التقارير الحديثة
    recent_reports = get_recent_reports(request.user)
    
    # التقارير المجدولة
    scheduled_reports = get_scheduled_reports(request.user)
    
    context = {
        'available_reports': available_reports,
        'recent_reports': recent_reports,
        'scheduled_reports': scheduled_reports,
    }
    
    return render(request, 'reports/dashboard.html', context)


@login_required
def generate_report(request, report_type):
    """توليد تقرير"""
    
    if request.method == 'POST':
        # الحصول على المعاملات
        start_date = datetime.strptime(request.POST.get('start_date'), '%Y-%m-%d').date()
        end_date = datetime.strptime(request.POST.get('end_date'), '%Y-%m-%d').date()
        format_type = request.POST.get('format', 'pdf')
        
        # توليد التقرير حسب النوع
        if report_type == 'executive_summary':
            report = QMSReportGenerator.generate_executive_summary_report(start_date, end_date, format_type)
        elif report_type == 'deviation_analysis':
            filters = {
                'department': request.POST.get('department'),
                'severity': request.POST.get('severity'),
                'type': request.POST.get('type'),
            }
            report = QMSReportGenerator.generate_deviation_analysis_report(start_date, end_date, filters)
        elif report_type == 'capa_effectiveness':
            report = QMSReportGenerator.generate_capa_effectiveness_report(start_date, end_date)
        elif report_type == 'change_control':
            report = QMSReportGenerator.generate_change_control_report(start_date, end_date)
        elif report_type == 'regulatory_compliance':
            report = QMSReportGenerator.generate_regulatory_compliance_report(start_date, end_date)
        elif report_type == 'trend_analysis':
            period = request.POST.get('analysis_period', 'quarterly')
            report = QMSReportGenerator.generate_trend_analysis_report(period)
        else:
            messages.error(request, _('Invalid report type'))
            return redirect('reports:dashboard')
        
        # إرجاع التقرير
        if format_type == 'pdf':
            response = HttpResponse(report.read(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{report_type}_report.pdf"'
            return response
        elif format_type == 'excel':
            return report
        else:
            # عرض التقرير في الصفحة
            return render(request, f'reports/{report_type}_report.html', {'data': report})
    
    # عرض نموذج إعداد التقرير
    return render(request, f'reports/{report_type}_form.html')


@login_required
def export_data(request):
    """تصدير البيانات"""
    
    data_type = request.GET.get('type', 'deviations')
    format_type = request.GET.get('format', 'csv')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    if format_type == 'csv':
        return export_to_csv(data_type, start_date, end_date)
    elif format_type == 'excel':
        return export_to_excel(data_type, start_date, end_date)
    else:
        return JsonResponse({'error': 'Invalid format'}, status=400)


def export_to_csv(data_type, start_date=None, end_date=None):
    """تصدير إلى CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{data_type}_export.csv"'
    
    writer = csv.writer(response)
    
    if data_type == 'deviations':
        deviations = Deviation.objects.all()
        if start_date:
            deviations = deviations.filter(reported_date__gte=start_date)
        if end_date:
            deviations = deviations.filter(reported_date__lte=end_date)
        
        # كتابة الرؤوس
        writer.writerow([
            'Deviation Number', 'Title', 'Type', 'Severity', 'Status',
            'Reported Date', 'Department', 'Reported By'
        ])
        
        # كتابة البيانات
        for deviation in deviations:
            writer.writerow([
                deviation.deviation_number,
                deviation.title,
                deviation.get_deviation_type_display(),
                deviation.get_severity_display(),
                deviation.get_status_display(),
                deviation.reported_date.strftime('%Y-%m-%d'),
                deviation.get_department_display(),
                deviation.reported_by.get_full_name(),
            ])
    
    return response


# دوال مساعدة

def get_recent_reports(user):
    """الحصول على التقارير الحديثة"""
    # يمكن تنفيذ هذا من خلال نموذج لحفظ تاريخ التقارير
    return []


def get_scheduled_reports(user):
    """الحصول على التقارير المجدولة"""
    # يمكن تنفيذ هذا من خلال نظام جدولة المهام
    return []