# reservation/urls.py
from django.urls import path
from . import views

app_name = "reservation"

urlpatterns = [
    # --------------------
    # 달력 / 예약 생성
    # --------------------
    path("", views.calendar_view, name="calendar"),          # 월/주 달력
    path("create/", views.booking_create, name="create"),    # 예약 생성

    # --------------------
    # 예약 액션
    # --------------------
    path("<int:booking_id>/cancel/", views.booking_cancel, name="cancel"),

    # --------------------
    # 승인(시설 담당자 / 관리자)
    # --------------------
    path("approvals/", views.approval_list, name="approvals"),
    path("approvals/<int:booking_id>/approve/", views.booking_approve, name="approve"),
    path("approvals/<int:booking_id>/reject/", views.booking_reject, name="reject"),
]
