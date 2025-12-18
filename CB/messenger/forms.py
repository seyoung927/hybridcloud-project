from django import forms
from .models import Message
from django.contrib.auth import get_user_model

class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['receiver', 'content']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 5, 'class': 'form-control', 'placeholder': '내용을 입력하세요'}),
            'receiver': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None) # 현재 로그인한 유저 제외하기 위해 받음
        super().__init__(*args, **kwargs)
        if user:
            # 나 자신에게는 쪽지 못 보내게 필터링
            User = get_user_model()
            self.fields['receiver'].queryset = User.objects.exclude(id=user.id)