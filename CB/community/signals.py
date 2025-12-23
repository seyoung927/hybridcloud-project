from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import Post, Notification

User = get_user_model()

@receiver(post_save, sender=Post)
def create_notice_notification(sender, instance, created, **kwargs):
    if created and instance.board.name == '공지사항':
        # ★ 변경점: 작성자에게 직급이 있을 때만 로직 실행
        if instance.author.rank:
            author_level = instance.author.rank.level
            
            # ★ 변경점: DB 쿼리 수정 (rank__level__lt 사용)
            # "유저의 rank의 level이 작성자의 level보다 작은 사람"
            recipients = User.objects.filter(rank__level__lt=author_level)
            
            notifications = []
            for user in recipients:
                notifications.append(
                    Notification(
                        recipient=user,
                        sender=instance.author,
                        message=f"📢 [공지] {instance.title}",
                        link=f"/community/post/{instance.id}/"
                    )
                )
            Notification.objects.bulk_create(notifications)