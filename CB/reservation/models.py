# reservation/models.py
from __future__ import annotations

from datetime import datetime, time
import math

from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone

from accounts.models import Rank, Department


# ======================================================
# 시간 슬롯(30분) 라운딩 유틸
# - 폼 입력 시 자동 라운딩 정책:
#   start_time: 30분 단위 내림(floor)
#   end_time  : 30분 단위 올림(ceil)
# ======================================================
SLOT_MINUTES = 30


def _to_minutes(t: time) -> int:
    return t.hour * 60 + t.minute


def _floor_time_to_slot(t: time, slot_minutes: int = SLOT_MINUTES) -> time:
    total = _to_minutes(t)
    floored = (total // slot_minutes) * slot_minutes
    return time(floored // 60, floored % 60)


def _ceil_time_to_slot(t: time, slot_minutes: int = SLOT_MINUTES) -> time:
    total = _to_minutes(t)
    ceiled = int(math.ceil(total / slot_minutes) * slot_minutes)
    # 24:00은 TimeField에 넣을 수 없으므로, 정책상 23:59로 클램프(또는 에러로 바꿔도 됨)
    if ceiled >= 24 * 60:
        return time(23, 59)
    return time(ceiled // 60, ceiled % 60)


class Facility(models.Model):
    """
    시설
    - 소회의실 / 대회의실 / 세미나실 / 교육장 / 탁구장 등
    """
    name = models.CharField(max_length=50, unique=True)
    location = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)

    # 예약 가능 제한 (비어 있으면 전체 허용)
    allowed_departments = models.ManyToManyField(
        Department,
        blank=True,
        related_name="facilities_allowed",
        verbose_name="예약 가능 부서(선택)"
    )
    allowed_ranks = models.ManyToManyField(
        Rank,
        blank=True,
        related_name="facilities_allowed",
        verbose_name="예약 가능 직급(선택)"
    )

    # 최소 직급 레벨 이상만 예약 가능
    min_rank_level = models.IntegerField(null=True, blank=True)

    # ✅ 시설 기준 관리(취소) 가능 최소 직급 레벨
    # - 예약 정보 열람은 전체 공개(A)
    # - 취소/관리만 이 기준을 사용
    view_min_rank_level = models.IntegerField(
        null=True, blank=True,
        verbose_name="관리 가능 최소 직급 레벨(이상)"
    )

    # 관리자 승인형 예약
    require_approval = models.BooleanField(default=False)

    # ✅ 시설 담당자(승인자) 1명
    # - 정책: 시설별 담당자 1명이 승인/거절을 처리
    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="facilities_to_approve",
        verbose_name="시설 담당자(승인자)"
    )

    def __str__(self):
        return self.name

    # --------------------
    # 권한 관련 유틸
    # --------------------
    def user_level(self, user) -> int:
        return user.rank.level if getattr(user, "rank", None) else 0

    def can_book(self, user) -> bool:
        """시설 예약 가능 여부"""
        if not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        if not self.is_active:
            return False

        # 부서 제한
        if self.allowed_departments.exists():
            if not user.department_id:
                return False
            if not self.allowed_departments.filter(pk=user.department_id).exists():
                return False

        # 직급 제한(목록)
        if self.allowed_ranks.exists():
            if not user.rank_id:
                return False
            if not self.allowed_ranks.filter(pk=user.rank_id).exists():
                return False

        # 최소 직급 레벨 제한
        if self.min_rank_level is not None:
            if self.user_level(user) < self.min_rank_level:
                return False

        return True

    def is_senior_for_management(self, user) -> bool:
        """
        시설 기준 윗직급(관리자급) 여부
        - 예약 취소/관리 권한 판단에 사용
        """
        if not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        if self.view_min_rank_level is None:
            return False
        return self.user_level(user) >= self.view_min_rank_level

    def is_approver(self, user) -> bool:
        """
        시설 담당자(승인자) 여부
        - 정책: 시설별 담당자 1명
        """
        if not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        return self.approver_id is not None and self.approver_id == user.id


class Booking(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "승인대기"
        APPROVED = "APPROVED", "승인완료"
        REJECTED = "REJECTED", "반려"
        CANCELED = "CANCELED", "취소"

    facility = models.ForeignKey(
        Facility,
        on_delete=models.PROTECT,
        related_name="bookings"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bookings"
    )

    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()

    title = models.CharField(max_length=100, blank=True)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING  # ✅ 정책: 생성 시 자동 PENDING
    )

    # 공통 메모(선택)
    decision_note = models.CharField(max_length=200, blank=True)

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="approved_bookings"
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    # ✅ 반려 기록(거절 사유 포함)
    rejected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="rejected_bookings"
    )
    rejected_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.CharField(max_length=300, blank=True)

    # ✅ 취소 기록(관리자는 취소 사유 필수로 강제할 예정: 폼/뷰에서 검증 권장)
    canceled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="canceled_bookings"
    )
    canceled_at = models.DateTimeField(null=True, blank=True)
    cancel_reason = models.CharField(max_length=300, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "-start_time"]
        indexes = [
            models.Index(fields=["facility", "date", "status", "start_time", "end_time"]),
        ]

    def __str__(self):
        return f"{self.facility} {self.date} {self.start_time}-{self.end_time} ({self.user})"

    # --------------------
    # datetime 유틸
    # --------------------
    @property
    def start_dt(self):
        """달력(JSON) 응답용: date + start_time 을 aware datetime으로 변환"""
        return timezone.make_aware(datetime.combine(self.date, self.start_time))

    @property
    def end_dt(self):
        """달력(JSON) 응답용: date + end_time 을 aware datetime으로 변환"""
        return timezone.make_aware(datetime.combine(self.date, self.end_time))

    # --------------------
    # 유효성 검사
    # --------------------
    def clean(self):
        # ✅ 30분 슬롯 자동 라운딩(폼 입력 정책)
        # - start_time: 30분 단위 내림
        # - end_time  : 30분 단위 올림
        if self.start_time:
            self.start_time = _floor_time_to_slot(self.start_time, SLOT_MINUTES)
        if self.end_time:
            self.end_time = _ceil_time_to_slot(self.end_time, SLOT_MINUTES)

        if self.end_time <= self.start_time:
            raise ValidationError("종료 시간은 시작 시간보다 늦어야 합니다.")

        # ✅ 시간 겹침 체크(정책: APPROVED만 점유로 봄)
        qs = Booking.objects.filter(
            facility=self.facility,
            date=self.date,
            status=Booking.Status.APPROVED,
        )
        if self.pk:
            qs = qs.exclude(pk=self.pk)

        if qs.filter(
            start_time__lt=self.end_time,
            end_time__gt=self.start_time
        ).exists():
            # 정책 문구
            raise ValidationError("해당 시간에 이미 승인된 예약이 있습니다.")

    # --------------------
    # 취소 권한 (⭐ 핵심)
    # --------------------
    def can_cancel(self, actor) -> bool:
        """
        예약 취소 가능 여부
        - 본인
        - 관리자
        - 시설 기준 윗직급
        """
        if not actor.is_authenticated:
            return False
        if actor.is_superuser:
            return True
        if actor == self.user:
            return True
        return self.facility.is_senior_for_management(actor)

    # --------------------
    # 승인 권한 (시설 담당자 1명)
    # --------------------
    def can_approve(self, actor) -> bool:
        """
        예약 승인/반려 가능 여부
        - 시설 담당자(approver)
        - superuser
        """
        return self.facility.is_approver(actor)

    # --------------------
    # 승인/대기 자동 설정
    # --------------------
    def set_pending_or_approved(self):
        """
        시설 require_approval 설정에 따라
        예약 상태 자동 설정

        ✅ 정책 변경 사항:
        - 현재 요구사항: 생성 시 자동 PENDING(자동 승인 없음)
        - 하지만 기존 require_approval 플래그를 유지하되,
          생성 로직에서 항상 PENDING으로 가는 것을 권장
          (이 메서드는 호환을 위해 남겨둠)
        """
        # 정책상: 생성은 무조건 PENDING
        self.status = Booking.Status.PENDING
        self.approved_at = None
        self.approved_by = None
        self.rejected_at = None
        self.rejected_by = None
        self.rejection_reason = ""
        self.canceled_at = None
        self.canceled_by = None
        self.cancel_reason = ""
