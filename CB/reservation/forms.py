# reservation/forms.py
from __future__ import annotations

from datetime import time

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import Booking, Facility, _floor_time_to_slot, _ceil_time_to_slot


AMPM_CHOICES = [("AM", "오전"), ("PM", "오후")]
HOUR_CHOICES = [(str(i), f"{i}시") for i in range(1, 13)]
MIN_CHOICES = [("00", "00분"), ("30", "30분")]


class BookingForm(forms.ModelForm):
    # ✅ VMware/브라우저 이슈 대응: 클릭 선택 가능한 12시간제 필드(가짜 필드)
    start_ampm = forms.ChoiceField(choices=AMPM_CHOICES, label="시작(오전/오후)")
    start_hour = forms.ChoiceField(choices=HOUR_CHOICES, label="시작(시)")
    start_min = forms.ChoiceField(choices=MIN_CHOICES, label="시작(분)")

    end_ampm = forms.ChoiceField(choices=AMPM_CHOICES, label="종료(오전/오후)")
    end_hour = forms.ChoiceField(choices=HOUR_CHOICES, label="종료(시)")
    end_min = forms.ChoiceField(choices=MIN_CHOICES, label="종료(분)")

    class Meta:
        model = Booking
        # start_time/end_time은 셀렉트에서 받은 값을 clean()에서 합성해서 넣음
        fields = ["facility", "date", "title"]
        labels = {
            "title": "사유",
        }
        widgets = {
            "date": forms.DateInput(
                attrs={"type": "date", "class": "form-control"}
            ),
            "title": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "사유"}
            ),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._user = user  # save()에서 사용

        # ✅ 날짜 기본값: 오늘
        if not self.initial.get("date"):
            self.initial["date"] = timezone.localdate()

        qs = Facility.objects.filter(is_active=True)

        if not user or not getattr(user, "is_authenticated", False):
            self.fields["facility"].queryset = qs.none()
            return

        if user.is_superuser:
            self.fields["facility"].queryset = qs
        else:
            # ✅ “예약 가능한 시설만” 보여주기
            # - 현재 정책상 제한을 두지 않으므로 비활성만 제외하고 모두 노출
            self.fields["facility"].queryset = qs

        # facility 위젯 스타일(bootstrap)
        self.fields["facility"].widget.attrs.update({"class": "form-select"})

        # ✅ 12시간제 셀렉트 위젯 스타일(bootstrap)
        self.fields["start_ampm"].widget.attrs.update({"class": "form-select time-select"})
        self.fields["start_hour"].widget.attrs.update({"class": "form-select time-select-hour"})
        self.fields["start_min"].widget.attrs.update({"class": "form-select time-select-min"})

        self.fields["end_ampm"].widget.attrs.update({"class": "form-select time-select"})
        self.fields["end_hour"].widget.attrs.update({"class": "form-select time-select-hour"})
        self.fields["end_min"].widget.attrs.update({"class": "form-select time-select-min"})

        # 기본값: 09:00 ~ 09:30
        self.fields["start_ampm"].initial = "AM"
        self.fields["start_hour"].initial = "9"
        self.fields["start_min"].initial = "00"
        self.fields["end_ampm"].initial = "AM"
        self.fields["end_hour"].initial = "9"
        self.fields["end_min"].initial = "30"

        # 수정 화면(instance)일 때 기존 start_time/end_time을 12시간제로 쪼개서 초기값 설정
        if self.instance and self.instance.pk:
            sh = self.instance.start_time.hour
            sm = self.instance.start_time.minute
            eh = self.instance.end_time.hour
            em = self.instance.end_time.minute

            self.fields["start_ampm"].initial = "PM" if sh >= 12 else "AM"
            self.fields["start_hour"].initial = str(
                (sh - 12) if sh > 12 else (12 if sh == 0 else sh)
            )
            self.fields["start_min"].initial = f"{sm:02d}"

            self.fields["end_ampm"].initial = "PM" if eh >= 12 else "AM"
            self.fields["end_hour"].initial = str(
                (eh - 12) if eh > 12 else (12 if eh == 0 else eh)
            )
            self.fields["end_min"].initial = f"{em:02d}"

    def _to_24h(self, ampm: str, hour_str: str, min_str: str) -> time:
        h = int(hour_str)
        m = int(min_str)

        if ampm == "AM":
            if h == 12:
                h = 0
        else:  # PM
            if h != 12:
                h += 12

        return time(hour=h, minute=m)

    # --------------------
    # 폼 유효성 검사
    # --------------------
    def clean(self):
        cleaned = super().clean()

        user = self._user
        facility = cleaned.get("facility")
        date_val = cleaned.get("date")

        # ✅ 셀렉트 값으로 start_time/end_time 합성
        try:
            start_time = self._to_24h(
                cleaned.get("start_ampm"),
                cleaned.get("start_hour"),
                cleaned.get("start_min"),
            )
            end_time = self._to_24h(
                cleaned.get("end_ampm"),
                cleaned.get("end_hour"),
                cleaned.get("end_min"),
            )
        except Exception:
            return cleaned

        if not facility or not date_val:
            return cleaned

        # 시설 예약 가능 여부(최종 방어)
        if user and getattr(user, "is_authenticated", False) and not user.is_superuser:
            if not facility.can_book(user):
                raise ValidationError("해당 시설을 예약할 권한이 부족합니다.")

        # ✅ 30분 슬롯 자동 라운딩(정책)
        start_time = _floor_time_to_slot(start_time)
        end_time = _ceil_time_to_slot(end_time)

        cleaned["start_time"] = start_time
        cleaned["end_time"] = end_time
        self.instance.start_time = start_time
        self.instance.end_time = end_time

        if end_time <= start_time:
            raise ValidationError("종료 시간은 시작 시간보다 늦어야 합니다.")

        # ✅ 충돌 검사(정책: APPROVED만 점유로 봄)
        conflict_qs = Booking.objects.filter(
            facility=facility,
            date=date_val,
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

        # 예약자 세팅
        if self._user and getattr(self._user, "is_authenticated", False):
            if not booking.user_id:
                booking.user = self._user

        # 생성(Create)
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
            # 수정(Update): 승인된 예약 변경 시 재승인
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
                    booking.approved_by = None
                    booking.approved_at = None
                    booking.rejected_by = None
                    booking.rejected_at = None
                    booking.rejection_reason = ""

        # 모델 레벨 최종 검증
        booking.full_clean()

        if commit:
            booking.save()
            self.save_m2m()

        return booking
