from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin

class UpdateLastActivityMiddleware(MiddlewareMixin):
    def process_view(self, request, view_func, view_args, view_kwargs):
        # 로그인한 사용자만 추적
        if request.user.is_authenticated:
            # 매번 DB에 쓰면 느려지니까, '마지막 기록'보다 1분 이상 지났을 때만 업데이트 (최적화)
            # (세션에 저장된 시간을 활용하거나, 간단하게 그냥 매번 업데이트해도 되지만 성능상 쿨타임 추천)
            
            # 여기선 간단하고 확실하게 매 요청마다 업데이트하되, 
            # 실제 서비스에선 쿨타임을 주는 게 좋습니다. 일단 심플 버전입니다.
            request.user.last_activity = timezone.now()
            request.user.save(update_fields=['last_activity'])
        return None