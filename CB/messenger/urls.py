from django.urls import path
from . import views

urlpatterns = [
    path('', views.inbox, name='inbox'),            # 기본: 받은 편지함
    path('send/', views.send_message, name='send_message'),
    path('<int:message_id>/', views.view_message, name='view_message'),
    path('sent/', views.sent_box, name='sent_box'), # [추가] 보낸 쪽지함
]