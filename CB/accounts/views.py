from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from .forms import CustomUserCreationForm



# 1. 회원가입 (Signup)
def signup(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # 가입하자마자 자동 로그인 시키기 (선택사항)
            login(request, user)
            return redirect('board_list') # 가입 후 게시판 메인으로 이동
    else:
        form = CustomUserCreationForm()
    return render(request, 'accounts/signup.html', {'form': form})

# 2. 내 프로필 보기 (My Page) - 내 직급 확인용
@login_required
def profile(request):
    return render(request, 'accounts/profile.html', {'user': request.user})

from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import User, Department, Rank

# 1. 관리자 여부 체크 함수 (True면 통과, False면 튕김)
def is_manager(user):
    return user.is_superuser

# 2. 회원 관리 목록 페이지
@user_passes_test(is_manager) 
def manage_users(request):
    users = User.objects.all().order_by('department', 'rank') # 부서별, 직급별 정렬
    return render(request, 'accounts/manage_users.html', {'users': users})

# 3. 회원 정보 수정 (부서/직급 변경)
@user_passes_test(is_manager)
def user_update(request, user_id):
    target_user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        # 폼에서 넘어온 데이터 받기
        dept_id = request.POST.get('department')
        rank_id = request.POST.get('rank')
        
        # DB 업데이트
        if dept_id:
            target_user.department = Department.objects.get(id=dept_id)
        if rank_id:
            target_user.rank = Rank.objects.get(id=rank_id)
            
        target_user.save()
        messages.success(request, f"{target_user.nickname}님의 정보를 수정했습니다.")
        return redirect('manage_users')

    # GET 요청일 때: 수정 폼 보여주기 (부서/직급 목록 필요)
    departments = Department.objects.all()
    ranks = Rank.objects.all()
    
    return render(request, 'accounts/user_update.html', {
        'target_user': target_user,
        'departments': departments,
        'ranks': ranks
    })

# accounts/views.py (기존 import 밑에 추가)
from .forms import EmployeeCreationForm # 방금 만든 폼 import
from .models import Department, Rank

# 1. 관리자 홈 (메뉴판)
@user_passes_test(is_manager)
def manage_home(request):
    return render(request, 'accounts/manage_home.html')

# 2. 사원 계정 생성 (관리자가 직접 생성)
@user_passes_test(is_manager)
def user_create(request):
    if request.method == 'POST':
        form = EmployeeCreationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            messages.success(request, f"🎉 '{user.nickname}' 사원 계정이 생성되었습니다!")
            return redirect('manage_users') # 생성 후 목록으로 이동
    else:
        form = EmployeeCreationForm()
        
    return render(request, 'accounts/user_create.html', {'form': form})

# 3. 부서/직급 관리 (추가/삭제)
@user_passes_test(is_manager)
def manage_structure(request):
    # 부서 추가 로직
    if request.method == 'POST':
        if 'add_dept' in request.POST:
            name = request.POST.get('dept_name')
            if name:
                Department.objects.create(name=name)
                messages.success(request, f"부서 '{name}' 추가 완료")
        
        elif 'add_rank' in request.POST:
            name = request.POST.get('rank_name')
            level = request.POST.get('rank_level') # HTML의 name="rank_level" 값을 가져옴
    
            if name and level:
        # Rank 모델은 name과 level 필드를 모두 필요로 합니다
                Rank.objects.create(name=name, level=level)
                messages.success(request, f"직급 '{name}'(Lv.{level})이 생성되었습니다.")
            return redirect('manage_structure')

        # 삭제 로직 (name='delete_dept' value='ID')
        elif 'delete_dept' in request.POST:
            dept_id = request.POST.get('delete_dept')
            Department.objects.filter(id=dept_id).delete()
            messages.warning(request, "부서를 삭제했습니다.")
            
        elif 'delete_rank' in request.POST:
            rank_id = request.POST.get('delete_rank')
            Rank.objects.filter(id=rank_id).delete()
            messages.warning(request, "직급을 삭제했습니다.")
            
        return redirect('manage_structure')

    return render(request, 'accounts/manage_structure.html', {
        'departments': Department.objects.all(),
        'ranks': Rank.objects.all()
    })

@user_passes_test(is_manager)
def user_update(request, user_id):
    target_user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        # 폼에서 데이터 받기
        new_nickname = request.POST.get('nickname') # [추가] 이름 받기
        dept_id = request.POST.get('department')
        rank_id = request.POST.get('rank')
        
        # DB 업데이트
        if new_nickname:
            target_user.nickname = new_nickname # [추가] 이름 저장
            
        if dept_id:
            target_user.department = Department.objects.get(id=dept_id)
        if rank_id:
            target_user.rank = Rank.objects.get(id=rank_id)
            
        target_user.save()
        messages.success(request, f"{target_user.nickname}님의 정보를 수정했습니다.")
        return redirect('manage_users')

    # GET 요청 처리 (그대로 유지)
    departments = Department.objects.all()
    ranks = Rank.objects.all()
    
    return render(request, 'accounts/user_update.html', {
        'target_user': target_user,
        'departments': departments,
        'ranks': ranks
    })

# accounts/views.py

@login_required
def org_chart(request):
    # [수정] 'user_set' -> 'members'
    departments = Department.objects.prefetch_related('members').all()
    return render(request, 'accounts/org_chart.html', {'departments': departments})
