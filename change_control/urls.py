from django.urls import path
from . import views

app_name = 'change_control'

urlpatterns = [
    # القوائم والصفحة الرئيسية
    path('', views.change_list, name='list'),
    path('dashboard/', views.change_dashboard, name='dashboard'),
    path('my/', views.my_changes, name='my_changes'),
    path('calendar/', views.change_calendar, name='calendar'),
    
    # إنشاء وعرض
    path('create/', views.change_create, name='create'),
    path('<int:pk>/', views.change_detail, name='detail'),
    path('<int:pk>/print/', views.change_print, name='print'),
    
    # التحديث والإجراءات
    path('<int:pk>/edit/', views.change_edit, name='edit'),
    path('<int:pk>/submit/', views.change_submit, name='submit'),
    path('<int:pk>/cancel/', views.change_cancel, name='cancel'),
    path('<int:pk>/close/', views.change_close, name='close'),
    
    # تقييم التأثير
    path('<int:pk>/impact-assessment/create/', views.impact_assessment_create, name='impact_assessment_create'),
    path('<int:pk>/impact-assessment/edit/', views.impact_assessment_edit, name='impact_assessment_edit'),
    path('<int:pk>/impact-assessment/view/', views.impact_assessment_view, name='impact_assessment_view'),
    
    # خطة التنفيذ
    path('<int:pk>/implementation-plan/create/', views.implementation_plan_create, name='implementation_plan_create'),
    path('<int:pk>/implementation-plan/edit/', views.implementation_plan_edit, name='implementation_plan_edit'),
    path('<int:pk>/implementation-plan/approve/', views.implementation_plan_approve, name='implementation_plan_approve'),
    
    # المهام
    path('<int:pk>/tasks/', views.task_list, name='task_list'),
    path('<int:pk>/task/create/', views.task_create, name='task_create'),
    path('task/<int:task_id>/edit/', views.task_edit, name='task_edit'),
    path('task/<int:task_id>/update-status/', views.task_update_status, name='task_update_status'),
    path('task/<int:task_id>/verify/', views.task_verify, name='task_verify'),
    path('<int:pk>/tasks/gantt/', views.tasks_gantt_chart, name='tasks_gantt'),
    
    # الموافقات
    path('<int:pk>/approve/', views.change_approve, name='approve'),
    path('approval/<int:approval_id>/action/', views.approval_action, name='approval_action'),
    path('<int:pk>/approval-matrix/', views.approval_matrix, name='approval_matrix'),
    
    # المرفقات
    path('<int:pk>/attachments/', views.attachment_list, name='attachment_list'),
    path('<int:pk>/attachment/upload/', views.attachment_upload, name='attachment_upload'),
    path('attachment/<int:attachment_id>/download/', views.attachment_download, name='attachment_download'),
    path('attachment/<int:attachment_id>/delete/', views.attachment_delete, name='attachment_delete'),
    
    # التقارير والإحصائيات
    path('reports/', views.change_reports, name='reports'),
    path('statistics/', views.change_statistics, name='statistics'),
    path('implementation-report/', views.implementation_report, name='implementation_report'),
    path('impact-analysis-report/', views.impact_analysis_report, name='impact_analysis_report'),
    
    # API endpoints
    path('api/change-chart-data/', views.change_chart_data, name='api_chart_data'),
    path('api/calendar-data/', views.calendar_data, name='api_calendar_data'),
    path('api/task-dependencies/<int:pk>/', views.task_dependencies_data, name='api_task_dependencies'),
    path('api/impact-matrix-data/', views.impact_matrix_data, name='api_impact_matrix'),
]