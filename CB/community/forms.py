from django import forms
from .models import Board, Post, Message
from django_summernote.widgets import SummernoteWidget

class BoardCreationForm(forms.ModelForm):
    class Meta:
        model = Board
        # 모델에 있는 실제 필드명으로 교체!
        fields = [
            'name', 'slug', 'description', 
            'read_access_depts', 'read_access_ranks', 
            'write_access_depts', 'write_access_ranks'
        ]
        
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '게시판 이름'}),
            'slug': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'URL 주소 (영어)'}),
            'description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '설명'}),
            
            # 다중 선택을 편하게 하기 위해 체크박스로 변경
            'read_access_depts': forms.CheckboxSelectMultiple(),
            'read_access_ranks': forms.CheckboxSelectMultiple(),
            'write_access_depts': forms.CheckboxSelectMultiple(),
            'write_access_ranks': forms.CheckboxSelectMultiple(),
        }
        
        labels = {
            'name': '게시판 이름',
            'slug': '고유 ID (URL용)',
            'description': '설명',
            'read_access_depts': '읽기 허용 부서 (선택 안 하면 전체)',
            'read_access_ranks': '읽기 허용 직급 (선택 안 하면 전체)',
            'write_access_depts': '쓰기 허용 부서 (선택 안 하면 전체)',
            'write_access_ranks': '쓰기 허용 직급 (선택 안 하면 전체)',
        }

# 1. 게시글 작성 폼
class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        # 사용자에게 입력받을 항목들
        fields = ['title', 'content', 'file'] 
        
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '제목을 입력하세요'}),
            # 👇 [핵심] 본문에 썸머노트 에디터 적용
            'content': SummernoteWidget(attrs={'summernote': {'width': '100%', 'height': '400px'}}),
            'file': forms.FileInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'title': '제목',
            'content': '내용',
            'file': '첨부파일',
        }

# 2. 쪽지 작성 폼
class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        # 받는 사람은 URL로 자동 지정하거나 검색할 거라 폼에서는 뺄 수도 있지만, 일단 둡니다.
        fields = ['recipient', 'title', 'content', 'file']
        
        widgets = {
            'recipient': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '쪽지 제목'}),
            # 👇 [핵심] 여기도 에디터 적용
            'content': SummernoteWidget(attrs={'summernote': {'width': '100%', 'height': '300px'}}),
            'file': forms.FileInput(attrs={'class': 'form-control'}),
        }