from django import forms
from .models import Message  # ⭐ 쪽지 모델
from django_summernote.widgets import SummernoteWidget

class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['recipient', 'title', 'content', 'file']
        
        widgets = {
            'recipient': forms.Select(attrs={
                'class': 'form-select', 
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