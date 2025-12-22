from django import forms
from .models import Board

class BoardCreationForm(forms.ModelForm):
    class Meta:
        model = Board
        fields = ['name', 'description', 'write_permission', 'read_permission']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '예: 공지사항'}),
            'description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '게시판에 대한 설명'}),
            'write_permission': forms.NumberInput(attrs={'class': 'form-control'}),
            'read_permission': forms.NumberInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'name': '게시판 이름',
            'description': '설명',
            'write_permission': '쓰기 권한 (레벨)',
            'read_permission': '읽기 권한 (레벨)',
        }