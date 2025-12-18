from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model

User = get_user_model()

class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        # 회원가입 할 때 입력받을 항목들
        fields = ('username', 'nickname', 'email', 'department', 'rank')
        
        # 디자인 팁: rank 필드 도움말 추가
        help_texts = {
            'rank': '본인의 직급을 선택해주세요.',
        }