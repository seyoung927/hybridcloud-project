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