from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
import datetime

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
    
    # 부서 연결 (새로 추가됨)
    department = models.ForeignKey(
        Department, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='members'  # ★ 이제부터 'user_set' 대신 'members'로 부릅니다!
    )
    rank = models.ForeignKey(Rank, on_delete=models.SET_NULL, null=True, blank=True)
    profile_image = models.ImageField(upload_to='profiles/%Y/%m/', blank=True, null=True)
    last_activity = models.DateTimeField(null=True, blank=True)

    @property
    def rank_power(self):
        return self.rank.level if self.rank else 0
        
    def __str__(self):
        dept = self.department.name if self.department else "무소속"
        rank = self.rank.name if self.rank else "미정"
        return f"[{dept}/{rank}] {self.username}"
    
    @property
    def is_online(self):
        if self.last_activity:
            # 현재 시간보다 5분 전(300초)보다 나중이면 접속 중으로 간주
            return timezone.now() - self.last_activity < datetime.timedelta(minutes=5)
        return False
    
