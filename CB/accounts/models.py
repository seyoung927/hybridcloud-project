from django.db import models
from django.contrib.auth.models import AbstractUser

# 1. 직급을 관리하는 별도 테이블 (관리자가 추가 가능)
class Rank(models.Model):
    name = models.CharField(max_length=20, unique=True) # 예: 사원, 대리
    level = models.IntegerField(unique=True)            # 예: 10, 20 (권한 비교용)

    class Meta:
        ordering = ['level'] # 레벨 낮은 순(사원)부터 정렬

    def __str__(self):
        return f"{self.name}(Lv.{self.level})"

class User(AbstractUser):
    nickname = models.CharField(max_length=20, blank=True)
    department = models.CharField(max_length=50, blank=True)
    
    # 2. 이제 숫자가 아니라 Rank 모델을 바라봅니다.
    # on_delete=models.SET_NULL: 직급이 삭제돼도 유저는 남겨둠 (직급 없음 상태)
    rank = models.ForeignKey(Rank, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        # 직급이 없으면 '미정' 출력
        rank_name = self.rank.name if self.rank else "미정"
        return f"[{rank_name}] {self.username}"
        
    # ★ 꿀팁: 템플릿이나 코드에서 user.rank_power 로 편하게 숫자를 쓰기 위한 속성
    @property
    def rank_power(self):
        return self.rank.level if self.rank else 0