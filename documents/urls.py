from django.urls import path
from . import views

app_name = 'documents'

urlpatterns = [
    # القوائم
    path('', views.document_list, name='list'),
    path('my/', views.my_documents, name='my_documents'),
    path('categories/', views.document_categories, name='categories'),
    
    # إنشاء وعرض
    path('create/', views.document_create, name='create'),
    path('<int:pk>/', views.document_detail, name='detail'),
    path('<int:pk>/download/', views.document_download, name='download'),
    
    # التحديث والمراجعة
    path('<int:pk>/edit/', views.document_edit, name='edit'),
    path('<int:pk>/change/', views.document_change, name='change'),
    path('<int:pk>/review/', views.document_review, name='review'),
    path('<int:pk>/send-review/', views.document_send_for_review, name='send_for_review'),
    path('<int:pk>/acknowledge/', views.document_acknowledge, name='acknowledge'),
    path('<int:pk>/publish/', views.document_publish, name='publish'),
    
    # التعليقات
    path('<int:pk>/comment/', views.document_comment, name='comment'),
    
    # الإجراءات الجماعية
    path('bulk-action/', views.bulk_action, name='bulk_action'),
]