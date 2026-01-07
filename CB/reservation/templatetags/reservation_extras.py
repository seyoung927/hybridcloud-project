from django import template

register = template.Library()

@register.filter
def get_item(d, key):
    return d.get(key, [])

@register.filter
def can_cancel(booking, user):
    if not user.is_authenticated:
        return False

    # 1) 본인
    if booking.user_id == user.id:
        return True

    # 2) 관리자
    if user.is_staff or user.is_superuser:
        return True

    # 3) 직급(윗직급) 비교
    if getattr(booking.user, "rank", None) and getattr(user, "rank", None):
        if booking.user.rank and user.rank and user.rank.level > booking.user.rank.level:
            return True

    # 4) 시설 정책(윗직급 열람/관리 허용)
    # facility 쪽에 allow_upper_rank_view 같은 필드가 있을 때만 동작
    facility = getattr(booking, "facility", None)
    if facility and getattr(facility, "allow_upper_rank_view", False):
        return True

    return False
