from django.db import models
from django.conf import settings  # 커스텀 유저 모델을 가져오기 위함

# 1. 게시판 카테고리 (권한 관리의 핵심)
class Board(models.Model):
    name = models.CharField(max_length=50, unique=True) # 예: 공지사항, 자유게시판
    slug = models.SlugField(max_length=50, unique=True, allow_unicode=True) # URL용 이름
    description = models.CharField(max_length=100, blank=True)
    
    # ★ 권한 설정 필드 (User 모델의 rank 숫자와 비교할 것임)
    # 예: write_min_rank가 30이면, 과장(30) 이상만 글쓰기 가능
    read_min_rank = models.IntegerField(default=10, help_text="이 등급 이상만 읽을 수 있음")
    write_min_rank = models.IntegerField(default=10, help_text="이 등급 이상만 글 쓸 수 있음")

    def __str__(self):
        return self.name

# 2. 게시글
class Post(models.Model):
    board = models.ForeignKey(Board, on_delete=models.CASCADE, related_name='posts')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    content = models.TextField()
    
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
    
    content = models.TextField()
    is_read = models.BooleanField(default=False) # 읽음 확인
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at'] # 최신 쪽지부터

    def __str__(self):
        return f"{self.sender} -> {self.recipient}: {self.content[:10]}..."