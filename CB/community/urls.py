from django.urls import path
from . import views

urlpatterns = [
    path('inbox/', views.inbox, name='inbox'),
    path('send/', views.send_message, name='send_message'),
    path('message/<int:message_id>/', views.view_message, name='view_message'),

    # ... (기존 쪽지 URL들) ...
    
    # 게시판 관련 URL
    path('', views.board_list, name='board_list'), # /community/ 로 접속 시 게시판 목록
    path('board/<slug:board_slug>/', views.post_list, name='post_list'),
    path('board/<slug:board_slug>/create/', views.post_create, name='post_create'),
    path('post/<int:post_id>/', views.post_detail, name='post_detail'),

]