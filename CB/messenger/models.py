from django.db import models
from django.conf import settings

class Message(models.Model):
    # ▼ related_name을 'messenger_sent'로 변경
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='messenger_sent',  # 여기가 핵심!
        verbose_name="보낸 사람"
    )
    
    # ▼ related_name을 'messenger_received'로 변경
    receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='messenger_received', # 여기가 핵심!
        verbose_name="받는 사람"
    )
    
    content = models.TextField(verbose_name="내용")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="보낸 시간")
    read_at = models.DateTimeField(null=True, blank=True, verbose_name="읽은 시간")
    
    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.sender} -> {self.receiver} : {self.content[:20]}"
    
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

