from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
import datetime
from django.contrib.auth.signals import user_logged_out
from django.dispatch import receiver
# 1. 직급을 관리하는 별도 테이블 (관리자가 추가 가능)
class Rank(models.Model):
    name = models.CharField(max_length=20, unique=True) # 예: 사원, 대리
    level = models.IntegerField(unique=True)            # 예: 10, 20 (권한 비교용)

    class Meta:
        ordering = ['level'] # 레벨 낮은 순(사원)부터 정렬

    def __str__(self):
        return f"{self.name}(Lv.{self.level})"
    
class Department(models.Model):
    name = models.CharField(max_length=50, unique=True) # 예: 개발팀, 인사팀
    description = models.TextField(blank=True)          # 예: IT 서비스 개발 전담
    
    def __str__(self):
        return self.name

class User(AbstractUser):
    nickname = models.CharField(max_length=20, blank=True)
    
    # 부서 & 직급
    department = models.ForeignKey(
        'Department', # 따옴표로 감싸면 순서 상관없이 참조 가능
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='members'
    )
    rank = models.ForeignKey('Rank', on_delete=models.SET_NULL, null=True, blank=True)
    profile_image = models.ImageField(upload_to='profiles/%Y/%m/', blank=True, null=True)
    
    # 👇 [추가된 필드]
    last_activity = models.DateTimeField(null=True, blank=True)

    @property
    def rank_power(self):
        return self.rank.level if self.rank else 0
        
    def __str__(self):
        dept = self.department.name if self.department else "무소속"
        rank = self.rank.name if self.rank else "미정"
        return f"[{dept}/{rank}] {self.username}"
    
    # 👇 [추가된 기능] 온라인 여부 확인
    @property
    def is_online(self):
        if self.last_activity:
            return timezone.now() - self.last_activity < datetime.timedelta(minutes=5)
        return False

@receiver(user_logged_out)
def remove_online_status_on_logout(sender, request, user, **kwargs):
    """
    로그아웃 하는 순간 last_activity를 비워서 즉시 '오프라인'으로 만듭니다.
    """
    if user:
        user.last_activity = None
        user.save(update_fields=['last_activity'])
