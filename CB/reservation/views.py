# reservation/views.py
import calendar
from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import BookingForm
from .models import Booking, Facility


# (선택) 알림용: messenger 앱이 있다면 내부 쪽지로 알림
def notify_message(to_user, title, content):
    """
    messenger 앱 모델 구조를 모르면 여기서 import가 깨질 수 있으니,
    실제 messenger 모델(예: Message)을 확인 후 아래 로직을 맞추세요.
    일단은 '연동 지점'만 제공.
    """
    try:
        from messenger.models import Message  # 예: 실제 모델명이 다르면 수정
        Message.objects.create(
            sender=None,
            receiver=to_user,
            title=title,
            content=content
        )
    except Exception:
        # 연동 전에는 실패해도 예약 기능이 죽지 않도록 무시
        pass


def month_range(any_day: date):
    first = any_day.replace(day=1)
    last_day = calendar.monthrange(first.year, first.month)[1]
    last = any_day.replace(day=last_day)
    return first, last


def week_range(any_day: date):
    # Monday=0
    start = any_day - timedelta(days=any_day.weekday())
    end = start + timedelta(days=6)
    return start, end


@login_required
def calendar_view(request):
    view = request.GET.get("view", "month")  # month | week
    date_str = request.GET.get("date")       # YYYY-MM-DD

    if date_str:
        base = date.fromisoformat(date_str)
    else:
        base = timezone.localdate()

    facilities = Facility.objects.filter(is_active=True).order_by("name")

    if view == "week":
        start, end = week_range(base)
        title = f"{start} ~ {end} (주간)"
    else:
        start, end = month_range(base)
        title = f"{start.strftime('%Y-%m')} (월간)"

    # ✅ 정책: 취소된 예약(CANCELED)은 달력에서 숨김(깔끔)
    # ✅ 정책: 일반 사용자/관리자 모두 PENDING + APPROVED는 달력에서 확인 가능
    bookings = (Booking.objects
                .select_related("facility", "user", "user__rank", "user__department")
                .filter(date__gte=start, date__lte=end)
                .filter(status__in=[Booking.Status.PENDING, Booking.Status.APPROVED])
                .order_by("date", "start_time"))

    # 날짜별 묶기
    by_day = {}
    cur = start
    while cur <= end:
        by_day[cur] = []
        cur += timedelta(days=1)
    for b in bookings:
        by_day.setdefault(b.date, []).append(b)

    # 달력(월간) 그리드 생성
    month_grid = None
    if view != "week":
        cal = calendar.Calendar(firstweekday=0)  # Monday start
        month_grid = cal.monthdatescalendar(base.year, base.month)

    ctx = {
        "view": view,
        "base": base,
        "start": start,
        "end": end,
        "title": title,
        "facilities": facilities,
        "by_day": by_day,
        "month_grid": month_grid,
    }
    return render(request, "reservation/calendar.html", ctx)


@login_required
def booking_create(request):
    if request.method == "POST":
        form = BookingForm(request.POST, user=request.user)
        if form.is_valid():
            booking = form.save(commit=False)

            # 서버단 최종 체크: 시설 예약 가능 여부
            if not booking.facility.can_book(request.user):
                messages.error(request, "권한이 부족합니다.")
                return redirect("reservation:calendar")

            # ✅ 정책: 생성 시 무조건 PENDING
            booking.user = request.user
            booking.status = Booking.Status.PENDING
            booking.approved_by = None
            booking.approved_at = None
            booking.rejected_by = None
            booking.rejected_at = None
            booking.rejection_reason = ""
            booking.canceled_by = None
            booking.canceled_at = None
            booking.cancel_reason = ""

            # 시간겹침 검증(정책: APPROVED만 점유)
            booking.full_clean()
            booking.save()

            messages.success(request, "예약이 접수되었습니다. 시설 담당자 승인 후 확정됩니다.")

            # 승인자에게 알림(쪽지/메일 연동 지점)
            if booking.facility.approver:
                notify_message(
                    booking.facility.approver,
                    "예약 승인 요청",
                    f"{booking.user}님이 {booking.facility.name} 예약을 요청했습니다. "
                    f"({booking.date} {booking.start_time}-{booking.end_time})"
                )

            return redirect("reservation:calendar")
    else:
        form = BookingForm(user=request.user)

    return render(request, "reservation/booking_form.html", {"form": form})


@login_required
@require_POST
def booking_cancel(request, booking_id):
    booking = get_object_or_404(Booking, pk=booking_id)

    # ✅ 정책: 취소는 어느 상태든 가능(단, 권한은 체크)
    if not booking.can_cancel(request.user):
        messages.error(request, "권한이 부족합니다.")
        return redirect("reservation:calendar")

    # ✅ 관리자(시설 기준 관리 가능자 or superuser)는 취소 사유 필수
    is_admin_actor = request.user.is_superuser or booking.facility.is_senior_for_management(request.user)
    reason = (request.POST.get("cancel_reason") or "").strip()

    if is_admin_actor and not reason:
        messages.error(request, "관리자 취소 시 사유를 반드시 입력해야 합니다.")
        return redirect("reservation:calendar")

    booking.status = Booking.Status.CANCELED
    booking.canceled_by = request.user
    booking.canceled_at = timezone.now()
    if reason:
        booking.cancel_reason = reason

    booking.save(update_fields=["status", "canceled_by", "canceled_at", "cancel_reason", "updated_at"])
    messages.success(request, "예약이 취소되었습니다.")

    # 예약자 알림(본인이 취소한 경우는 생략)
    if booking.user_id and booking.user_id != request.user.id:
        notify_message(
            booking.user,
            "예약 취소",
            f"{booking.facility.name} 예약이 취소되었습니다. "
            f"({booking.date} {booking.start_time}-{booking.end_time})"
            + (f" / 사유: {reason}" if reason else "")
        )

    return redirect("reservation:calendar")


# ----- 승인(시설 담당자)형 -----

@login_required
def approval_list(request):
    """
    ✅ 정책:
    - superuser 또는 시설담당자(approver)는 PENDING 목록을 볼 수 있음
    - 시설담당자는 자기 시설의 PENDING만 노출
    """
    if request.user.is_superuser:
        pending = (Booking.objects
                   .select_related("facility", "user")
                   .filter(status=Booking.Status.PENDING)
                   .order_by("date", "start_time"))
    else:
        my_facility_ids = Facility.objects.filter(
            approver=request.user,
            is_active=True
        ).values_list("id", flat=True)

        if not my_facility_ids:
            messages.error(request, "권한이 부족합니다.")
            return redirect("reservation:calendar")

        pending = (Booking.objects
                   .select_related("facility", "user")
                   .filter(status=Booking.Status.PENDING, facility_id__in=list(my_facility_ids))
                   .order_by("date", "start_time"))

    return render(request, "reservation/approvals.html", {"pending": pending})


@login_required
@require_POST
def booking_approve(request, booking_id):
    booking = get_object_or_404(Booking, pk=booking_id)

    # ✅ 권한: 시설 담당자(approver) 또는 superuser
    if not booking.can_approve(request.user):
        messages.error(request, "권한이 부족합니다.")
        return redirect("reservation:calendar")

    # ✅ 승인 시점 재검증(정책: APPROVED만 점유)
    with transaction.atomic():
        booking = Booking.objects.select_for_update().get(pk=booking_id)

        if booking.status != Booking.Status.PENDING:
            messages.error(request, "이미 처리된 예약입니다.")
            return redirect("reservation:calendar")

        conflict_qs = Booking.objects.filter(
            facility=booking.facility,
            date=booking.date,
            status=Booking.Status.APPROVED,
            start_time__lt=booking.end_time,
            end_time__gt=booking.start_time,
        ).exclude(pk=booking.pk)

        if conflict_qs.exists():
            messages.error(request, "승인 중 충돌이 발생했습니다. 최신 예약 현황을 확인하세요.")
            return redirect("reservation:calendar")

        booking.status = Booking.Status.APPROVED
        booking.approved_by = request.user
        booking.approved_at = timezone.now()
        booking.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])

    messages.success(request, "승인 완료")

    notify_message(
        booking.user,
        "예약 승인",
        f"{booking.facility.name} 예약이 승인되었습니다. ({booking.date} {booking.start_time}-{booking.end_time})"
    )

    return redirect("reservation:approvals")


@login_required
@require_POST
def booking_reject(request, booking_id):
    booking = get_object_or_404(Booking, pk=booking_id)

    # ✅ 권한: 시설 담당자(approver) 또는 superuser
    if not booking.can_approve(request.user):
        messages.error(request, "권한이 부족합니다.")
        return redirect("reservation:calendar")

    reason = (request.POST.get("rejection_reason") or "").strip()
    if not reason:
        messages.error(request, "거절 사유를 입력해야 합니다.")
        return redirect("reservation:approvals")

    with transaction.atomic():
        booking = Booking.objects.select_for_update().get(pk=booking_id)

        if booking.status != Booking.Status.PENDING:
            messages.error(request, "이미 처리된 예약입니다.")
            return redirect("reservation:calendar")

        booking.status = Booking.Status.REJECTED
        booking.rejected_by = request.user
        booking.rejected_at = timezone.now()
        booking.rejection_reason = reason

        # 거절이므로 승인 기록은 비움
        booking.approved_by = None
        booking.approved_at = None

        booking.save(update_fields=[
            "status",
            "rejected_by", "rejected_at", "rejection_reason",
            "approved_by", "approved_at",
            "updated_at"
        ])

    messages.success(request, "반려 처리 완료")

    notify_message(
        booking.user,
        "예약 반려",
        f"{booking.facility.name} 예약이 반려되었습니다. 사유: {reason}"
    )

    return redirect("reservation:approvals")
