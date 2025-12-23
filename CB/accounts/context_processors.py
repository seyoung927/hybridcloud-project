from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model

def online_users(request):
    User = get_user_model()
    # 최근 5분 이내에 활동한 사람 찾기
    active_threshold = timezone.now() - timedelta(minutes=5)
    
    # 나 자신은 목록에서 뺄지 말지 결정 (여기선 포함해서 보여줍니다)
    users = User.objects.filter(last_activity__gte=active_threshold, is_active=True).order_by('-last_activity')
    
    return {
        'online_users_list': users
    }