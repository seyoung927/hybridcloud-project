from django.db import models
from django.conf import settings

class Message(models.Model):
    # 보내는 사람 (나)
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='sent_messages_messenger' # community와 이름 충돌 방지
    )
    
    # 👇 [추가] 받는 사람 (forms.py에서 찾던 recipient가 이거!)
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='received_messages_messenger'
    )
    
    # 👇 [추가] 제목 (forms.py에서 찾던 title)
    title = models.CharField(max_length=200, default="제목 없음")
    
    # 내용
    content = models.TextField()
    
    # 👇 [추가] 파일 (forms.py에서 찾던 file)
    file = models.FileField(upload_to='messenger/files/%Y/%m/%d/', blank=True, null=True)
    
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.title}] {self.sender} -> {self.recipient}"
    
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

