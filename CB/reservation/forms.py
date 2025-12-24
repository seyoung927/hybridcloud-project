# reservation/forms.py
from __future__ import annotations

from django import forms
from django.core.exceptions import ValidationError

from .models import Booking, Facility, _floor_time_to_slot, _ceil_time_to_slot


class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ["facility", "date", "start_time", "end_time", "title"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "start_time": forms.TimeInput(attrs={"type": "time", "class": "form-control"}),
            "end_time": forms.TimeInput(attrs={"type": "time", "class": "form-control"}),
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "예약 제목(선택)"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._user = user  # save()에서 사용

        qs = Facility.objects.filter(is_active=True)

        if not user or not getattr(user, "is_authenticated", False):
            self.fields["facility"].queryset = qs.none()
            return

        if user.is_superuser:
            self.fields["facility"].queryset = qs
            return

        # ✅ “예약 가능한 시설만” 보여주기
        # - 정책상 부서/직급 제한을 두지 않더라도,
        #   Facility에 제한값(allowed_departments/allowed_ranks/min_rank_level)이 설정되어 있을 수 있으므로
        #   can_book() 기준으로 필터링
        allowed_ids = [f.id for f in qs if f.can_book(user)]
        self.fields["facility"].queryset = qs.filter(id__in=allowed_ids)

    # --------------------
    # 폼 유효성 검사
    # --------------------
    def clean(self):
        cleaned = super().clean()

        user = self._user
        facility = cleaned.get("facility")
        date = cleaned.get("date")
        start_time = cleaned.get("start_time")
        end_time = cleaned.get("end_time")

        # 필수값 누락 시 추가검증 불가
        if not facility or not date or not start_time or not end_time:
            return cleaned

        # 시설 예약 가능 여부(안전)
        if user and getattr(user, "is_authenticated", False) and not user.is_superuser:
            if not facility.can_book(user):
                raise ValidationError("해당 시설을 예약할 권한이 부족합니다.")

        # ✅ 30분 슬롯 자동 라운딩(정책)
        # - start_time: 30분 단위 내림
        # - end_time  : 30분 단위 올림
        start_time = _floor_time_to_slot(start_time)
        end_time = _ceil_time_to_slot(end_time)

        cleaned["start_time"] = start_time
        cleaned["end_time"] = end_time

        if end_time <= start_time:
            raise ValidationError("종료 시간은 시작 시간보다 늦어야 합니다.")

        # ✅ 충돌 검사(정책: APPROVED만 점유로 봄)
        conflict_qs = Booking.objects.filter(
            facility=facility,
            date=date,
            status=Booking.Status.APPROVED,
            start_time__lt=end_time,
            end_time__gt=start_time,
        )
        if self.instance.pk:
            conflict_qs = conflict_qs.exclude(pk=self.instance.pk)

        if conflict_qs.exists():
            raise ValidationError("해당 시간에 이미 승인된 예약이 있습니다.")

        return cleaned

    # --------------------
    # 저장 로직 (정책 반영)
    # --------------------
    def save(self, commit=True):
        """
        정책 반영:
        - 생성(Create): 무조건 PENDING
        - 수정(Update):
            * APPROVED 상태의 예약을 수정하면 -> PENDING으로 되돌리고 재승인 필요
            * 승인/반려 관련 기록은 초기화(새로운 결정이 필요하므로)
        """
        booking: Booking = super().save(commit=False)

        # 예약자 세팅(뷰에서도 가능하지만, 폼에서도 안전장치로 보장)
        if self._user and getattr(self._user, "is_authenticated", False):
            if not booking.user_id:
                booking.user = self._user

        # 생성(Create): 항상 PENDING
        if booking.pk is None:
            booking.status = Booking.Status.PENDING
            booking.approved_by = None
            booking.approved_at = None
            booking.rejected_by = None
            booking.rejected_at = None
            booking.rejection_reason = ""
            booking.canceled_by = None
            booking.canceled_at = None
            booking.cancel_reason = ""

        else:
            # 수정(Update): 승인된 예약이 “시간/날짜/시설” 변경되면 재승인
            prev = Booking.objects.filter(pk=booking.pk).only(
                "status", "facility_id", "date", "start_time", "end_time"
            ).first()

            if prev and prev.status == Booking.Status.APPROVED:
                changed = (
                    prev.facility_id != booking.facility_id
                    or prev.date != booking.date
                    or prev.start_time != booking.start_time
                    or prev.end_time != booking.end_time
                )
                if changed:
                    booking.status = Booking.Status.PENDING
                    # ✅ 재승인 필요 → 기존 결정/반려 기록 초기화
                    booking.approved_by = None
                    booking.approved_at = None
                    booking.rejected_by = None
                    booking.rejected_at = None
                    booking.rejection_reason = ""

        # 모델 레벨 clean()까지 포함한 최종 검증
        booking.full_clean()

        if commit:
            booking.save()
            self.save_m2m()

        return booking
