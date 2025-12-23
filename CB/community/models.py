from django.db import models
from django.conf import settings  # 커스텀 유저 모델을 가져오기 위함

# 1. 게시판 카테고리 (권한 관리의 핵심)
from django.db import models
from django.conf import settings
# accounts 앱의 모델을 가져옵니다.
from accounts.models import Rank, Department 

class Board(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True, allow_unicode=True)
    description = models.CharField(max_length=100, blank=True)

    # ★ 권한 설정 (핵심 변경!)
    # ManyToManyField: 여러 개를 동시에 선택할 수 있음 (체크박스)
    # blank=True: 아무것도 선택 안 하면 '모두 허용'으로 처리하기 위함
    
    # 1. 읽기(접속) 권한
    read_access_depts = models.ManyToManyField(
        Department, 
        blank=True, 
        verbose_name="읽기 허용 부서",
        related_name='read_boards'  # ★ 추가: 부서 입장에서 "읽을 수 있는 게시판들"
    )
    read_access_ranks = models.ManyToManyField(
        Rank, 
        blank=True, 
        verbose_name="읽기 허용 직급",
        related_name='read_boards'  # ★ 추가
    )
    
    # 2. 쓰기(글작성) 권한
    write_access_depts = models.ManyToManyField(
        Department, 
        blank=True, 
        verbose_name="쓰기 허용 부서",
        related_name='write_boards' # ★ 추가: 부서 입장에서 "쓸 수 있는 게시판들"
    )
    write_access_ranks = models.ManyToManyField(
        Rank, 
        blank=True, 
        verbose_name="쓰기 허용 직급",
        related_name='write_boards' # ★ 추가
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일')

    def __str__(self):
        return self.name
        
    # 헬퍼 메서드: 이 유저가 읽을 수 있나?
    def can_read(self, user):
        # 관리자는 프리패스
        if user.is_superuser: return True
        
        # 1. 부서 체크 (설정된 부서가 있는데, 내 부서가 거기에 없으면 탈락)
        if self.read_access_depts.exists():
            if not user.department or user.department not in self.read_access_depts.all():
                return False
                
        # 2. 직급 체크 (설정된 직급이 있는데, 내 직급이 거기에 없으면 탈락)
        if self.read_access_ranks.exists():
            if not user.rank or user.rank not in self.read_access_ranks.all():
                return False
                
        return True # 모든 관문 통과

    # 헬퍼 메서드: 이 유저가 쓸 수 있나?
    def can_write(self, user):
        if user.is_superuser: return True
        
        # 읽지도 못하는 사람은 당연히 못 씀
        if not self.can_read(user): return False
        
        # 1. 부서 체크
        if self.write_access_depts.exists():
            if not user.department or user.department not in self.write_access_depts.all():
                return False
                
        # 2. 직급 체크
        if self.write_access_ranks.exists():
            if not user.rank or user.rank not in self.write_access_ranks.all():
                return False
                
        return True

# 2. 게시글
class Post(models.Model):
    board = models.ForeignKey(Board, on_delete=models.CASCADE, related_name='posts')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    content = models.TextField()
    is_active = models.BooleanField(default=True) # True: 정상, False: 삭제됨
    
    # 파일 업로드 (공지사항엔 첨부파일이 필수죠)
    file = models.FileField(upload_to='community/files/%Y/%m/%d/', blank=True, null=True)
    
    # 조회수
    view_count = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at'] # 최신글이 위로

    def __str__(self):
        return f"[{self.board.name}] {self.title}"

# 3. 댓글
class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.author}님의 댓글"

# 4. 알림 (Notification) - 사내 메신저 역할
class Notification(models.Model):
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    
    message = models.CharField(max_length=255) # 예: "부장님이 공지사항을 등록했습니다."
    link = models.URLField(blank=True, null=True) # 클릭하면 해당 글로 이동
    
    is_read = models.BooleanField(default=False) # 읽음 여부 (빨간 점 표시용)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.recipient}에게: {self.message}"

class Message(models.Model):
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_messages')
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_messages')
    
    # 👇 [추가] 쪽지 제목
    title = models.CharField(max_length=200, default="제목 없음") 
    
    # 👇 [추가] 쪽지 내용 (에디터 쓸 거라 TextField 유지)
    content = models.TextField()
    
    # 👇 [추가] 파일 첨부 기능
    file = models.FileField(upload_to='messages/files/%Y/%m/%d/', blank=True, null=True)

    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.title}] {self.sender} -> {self.recipient}"