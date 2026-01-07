from django.apps import AppConfig

class CommunityConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'community'

    # ▼ 이 부분을 추가해야 시그널이 작동합니다!
    def ready(self):
        import community.signals