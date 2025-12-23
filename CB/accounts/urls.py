from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # 1. 로그인 (Django 제공 기능 사용)
    # template_name을 지정해줘야 우리가 만든 HTML을 씁니다.
    path('login/', auth_views.LoginView.as_view(template_name='accounts/login.html'), name='login'),
    
    # 2. 로그아웃 (Django 제공 기능 사용)
    # 로그아웃 후에는 다시 로그인 페이지로 튕기게 설정(next_page)
    
    
    # 3. 회원가입 (우리가 만든 뷰)
    path('signup/', views.signup, name='signup'),
    
    # 4. 프로필
    path('profile/', views.profile, name='profile'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),
    path('manage/update/<int:user_id>/', views.user_update, name='user_update'),
    path('manage/', views.manage_home, name='manage_home'),           # 관리자 홈
    path('manage/users/', views.manage_users, name='manage_users'),   # 사원 목록
    path('manage/create/', views.user_create, name='user_create'),    # 사원 추가
    path('manage/structure/', views.manage_structure, name='manage_structure'), #부서 관리
    path('org/', views.org_chart, name='org_chart'),

]