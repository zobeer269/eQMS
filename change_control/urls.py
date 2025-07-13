# change_control/urls.py
from django.urls import path
from . import views

app_name = 'change_control'

urlpatterns = [
    # الصفحات الرئيسية
    path('', views.change_list, name='list'),
    path('dashboard/', views.change_dashboard, name='dashboard'),
    path('my/', views.my_changes, name='my_changes'),
    path('calendar/', views.change_calendar, name='calendar'),
    
    # إنشاء وعرض التغييرات
    path('create/', views.change_create, name='create'),
    path('<int:pk>/', views.change_detail, name='detail'),
    path('<int:pk>/print/', views.change_print, name='print'),
    path('<int:pk>/timeline/', views.change_timeline, name='timeline'),
    
    # تحديث وإدارة التغييرات
    path('<int:pk>/edit/', views.change_edit, name='edit'),
    path('<int:pk>/submit/', views.change_submit, name='submit'),
    path('<int:pk>/cancel/', views.change_cancel, name='cancel'),
    path('<int:pk>/close/', views.change_close, name='close'),
    path('<int:pk>/reopen/', views.change_reopen, name='reopen'),
    
    # تقييم التأثير
    path('<int:pk>/impact-assessment/create/', views.impact_assessment_create, name='impact_assessment_create'),
    path('<int:pk>/impact-assessment/edit/', views.impact_assessment_edit, name='impact_assessment_edit'),
    path('<int:pk>/impact-assessment/view/', views.impact_assessment_view, name='impact_assessment_view'),
    path('<int:pk>/impact-assessment/approve/', views.impact_assessment_approve, name='impact_assessment_approve'),
    
    # خطة التنفيذ
    path('<int:pk>/implementation-plan/create/', views.implementation_plan_create, name='implementation_plan_create'),
    path('<int:pk>/implementation-plan/edit/', views.implementation_plan_edit, name='implementation_plan_edit'),
    path('<int:pk>/implementation-plan/view/', views.implementation_plan_view, name='implementation_plan_view'),
    path('<int:pk>/implementation-plan/approve/', views.implementation_plan_approve, name='implementation_plan_approve'),
    path('<int:pk>/implementation-plan/start/', views.implementation_start, name='implementation_start'),
    
    # إدارة المهام
    path('<int:pk>/tasks/', views.task_list, name='task_list'),
    path('<int:pk>/task/create/', views.task_create, name='task_create'),
    path('task/<int:task_id>/edit/', views.task_edit, name='task_edit'),
    path('task/<int:task_id>/detail/', views.task_detail, name='task_detail'),
    path('task/<int:task_id>/update-status/', views.task_update_status, name='task_update_status'),
    path('task/<int:task_id>/update-progress/', views.task_update_progress, name='task_update_progress'),
    path('task/<int:task_id>/verify/', views.task_verify, name='task_verify'),
    path('task/<int:task_id>/assign/', views.task_assign, name='task_assign'),
    path('<int:pk>/tasks/gantt/', views.tasks_gantt_chart, name='tasks_gantt'),
    path('<int:pk>/tasks/kanban/', views.tasks_kanban, name='tasks_kanban'),
    
    # الموافقات
    path('<int:pk>/approve/', views.change_approve, name='approve'),
    path('<int:pk>/approval-workflow/', views.approval_workflow, name='approval_workflow'),
    path('approval/<int:approval_id>/action/', views.approval_action, name='approval_action'),
    path('<int:pk>/approval-matrix/', views.approval_matrix, name='approval_matrix'),
    path('<int:pk>/approval-history/', views.approval_history, name='approval_history'),
    
    # المرفقات
    path('<int:pk>/attachments/', views.attachment_list, name='attachment_list'),
    path('<int:pk>/attachment/upload/', views.attachment_upload, name='attachment_upload'),
    path('attachment/<int:attachment_id>/view/', views.attachment_view, name='attachment_view'),
    path('attachment/<int:attachment_id>/download/', views.attachment_download, name='attachment_download'),
    path('attachment/<int:attachment_id>/edit/', views.attachment_edit, name='attachment_edit'),
    path('attachment/<int:attachment_id>/delete/', views.attachment_delete, name='attachment_delete'),
    
    # التعليقات والمناقشات
    path('<int:pk>/comments/', views.change_comments, name='comments'),
    path('<int:pk>/comment/add/', views.comment_add, name='comment_add'),
    path('comment/<int:comment_id>/edit/', views.comment_edit, name='comment_edit'),
    path('comment/<int:comment_id>/delete/', views.comment_delete, name='comment_delete'),
    
    # التقارير والإحصائيات
    path('reports/', views.change_reports, name='reports'),
    path('reports/dashboard/', views.reports_dashboard, name='reports_dashboard'),
    path('reports/status/', views.status_report, name='status_report'),
    path('reports/performance/', views.performance_report, name='performance_report'),
    path('reports/overdue/', views.overdue_report, name='overdue_report'),
    path('statistics/', views.change_statistics, name='statistics'),
    path('implementation-report/', views.implementation_report, name='implementation_report'),
    path('impact-analysis-report/', views.impact_analysis_report, name='impact_analysis_report'),
    path('trend-analysis/', views.trend_analysis, name='trend_analysis'),
    
    # تصدير البيانات
    path('export/excel/', views.export_changes_excel, name='export_excel'),
    path('export/csv/', views.export_changes_csv, name='export_csv'),
    path('<int:pk>/export/pdf/', views.export_change_pdf, name='export_pdf'),
    
    # واجهة برمجة التطبيقات (API)
    path('api/search/', views.change_search_api, name='api_search'),
    path('api/change-chart-data/', views.change_chart_data, name='api_chart_data'),
    path('api/calendar-data/', views.calendar_data, name='api_calendar_data'),
    path('api/task-dependencies/<int:pk>/', views.task_dependencies_data, name='api_task_dependencies'),
    path('api/impact-matrix-data/', views.impact_matrix_data, name='api_impact_matrix'),
    path('api/workflow-data/<int:pk>/', views.workflow_data, name='api_workflow_data'),
    path('api/progress-data/<int:pk>/', views.progress_data, name='api_progress_data'),
    
    # إدارة القوالب والنماذج
    path('templates/', views.change_templates, name='templates'),
    path('template/<int:template_id>/use/', views.use_template, name='use_template'),
    path('bulk-actions/', views.bulk_actions, name='bulk_actions'),
    
    # تكامل مع الأنظمة الأخرى
    path('<int:pk>/create-deviation/', views.create_related_deviation, name='create_deviation'),
    path('<int:pk>/create-capa/', views.create_related_capa, name='create_capa'),
    path('<int:pk>/link-documents/', views.link_documents, name='link_documents'),
    
    # إشعارات ومتابعة
    path('<int:pk>/follow/', views.follow_change, name='follow'),
    path('<int:pk>/unfollow/', views.unfollow_change, name='unfollow'),
    path('<int:pk>/subscribe/', views.subscribe_notifications, name='subscribe'),
    path('notifications/', views.change_notifications, name='notifications'),
    
    # مراجعة وتدقيق
    path('<int:pk>/audit-trail/', views.audit_trail, name='audit_trail'),
    path('<int:pk>/review/', views.change_review, name='review'),
    path('<int:pk>/quality-review/', views.quality_review, name='quality_review'),
]