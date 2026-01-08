from django.urls import path
from . import views


urlpatterns = [
    path('', views.board_list, name='board_list'),
    path('board/<slug:board_slug>/', views.post_list, name='post_list'),
    path('board/<slug:board_slug>/create/', views.post_create, name='post_create'),
    path('post/<int:post_id>/', views.post_detail, name='post_detail'),
    path('post/<int:post_id>/comment/', views.comment_create, name='comment_create'),
    path('comment/<int:comment_id>/delete/', views.comment_delete, name='comment_delete'),
    path('post/<int:post_id>/delete/', views.post_delete, name='post_delete'),
    path('all/', views.all_posts, name='all_posts'),
    path('manage/', views.manage_boards, name='manage_boards'),
    path('manage/edit/<int:board_id>/', views.edit_board, name='edit_board'),

    # ❌ 아래 쪽지 기능은 messenger 앱에서 처리하므로 제거/주석
    # path('inbox/', views.inbox, name='inbox'),
    # path('send/', views.send_message, name='send_message'),
    # path('message/<int:message_id>/', views.view_message, name='view_message'),
]