from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Rank  # Rank 모델도 관리자에서 봐야 하니까 추가!

# 1. Rank 모델을 관리자 페이지에 등록 (직급 추가/삭제용)
admin.site.register(Rank)

class CustomUserAdmin(UserAdmin):
    # ▼ 수정된 부분: 'get_rank_display' -> 'rank'
    list_display = ('username', 'rank', 'department', 'email', 'is_staff')
    
    # ... (나머지 fieldsets 코드는 그대로 두셔도 됩니다) ...
    fieldsets = UserAdmin.fieldsets + (
        ('추가 정보 (직급/부서)', {'fields': ('rank', 'department', 'nickname')}),
    )
    
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('추가 정보', {'fields': ('rank', 'department', 'nickname')}),
    )
    
    list_filter = ('rank', 'department', 'is_staff', 'is_superuser')

admin.site.register(User, CustomUserAdmin)