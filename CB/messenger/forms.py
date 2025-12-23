from django import forms
# 👇 [중요] 여기서는 오직 Message 모델만 가져옵니다. (Board, Post 삭제)
from .models import Message
from django_summernote.widgets import SummernoteWidget

class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['recipient', 'title', 'content', 'file']
        
        # ⭐ 입력창 디자인 (부트스트랩) & 에디터 적용
        widgets = {
            'recipient': forms.Select(attrs={
                'class': 'form-select', 
                'placeholder': '받는 사람을 선택하세요'
            }),
            'title': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': '제목을 입력하세요'
            }),
            'content': SummernoteWidget(attrs={
                'summernote': {'width': '100%', 'height': '300px'}
            }),
            'file': forms.FileInput(attrs={
                'class': 'form-control'
            }),
        }
        
        labels = {
            'recipient': '받는 사람',
            'title': '제목',
            'content': '내용',
            'file': '첨부파일',
        }