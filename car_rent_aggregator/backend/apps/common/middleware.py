# apps/common/middleware.py
from dataclasses import dataclass
from django.conf import settings
from django.http import JsonResponse

API_PREFIX = getattr(settings, "API_PREFIX", "/api/")
WEBHOOK_WHITELIST = tuple(getattr(settings, "WEBHOOK_WHITELIST_PATHS", []) or ())

def _norm(s: str) -> str:
    return (s or "").strip()

def _is_whitelisted(path: str) -> bool:
    """
    Совпадение по началу пути: webhooks и короткие ссылки оплаты.
    Пример: /api/payments/p/<invoice_id>/ — пройдёт, потому что начинается с /api/payments/p/
    """
    p = _norm(path or "/")
    for base in WEBHOOK_WHITELIST:
        b = _norm(base)
        if p == b or p.startswith(b):
            return True
    return False

@dataclass
class _APIServiceUser:
    id: int | None = None
    pk: int | None = None
    username: str = "api-bot"
    is_authenticated: bool = True
    is_anonymous: bool = False
    is_staff: bool = False
    is_superuser: bool = False

class ApiGatewayMiddleware:
    """
    Один-единственный middleware нового стиля:
      • whitelist пути (webhooks/redirects) — пропускаем и отключаем CSRF
      • всё остальное под /api/ — проверяем X-Api-Key и отключаем CSRF
      • админка /admin/ и обычные страницы — не трогаем
    Никаких process_request / MiddlewareMixin не используется → ошибка NameError исчезает.
    """
    def __init__(self, get_response):
        self.get_response = get_response
        self.api_key = getattr(settings, "BOTS_API_KEY", "")

    def __call__(self, request):
        path = request.path or "/"

        # 1) Белый список: вебхуки Payme/Click и короткий редирект оплаты — без ключа и без CSRF
        if _is_whitelisted(path):
            request._dont_enforce_csrf_checks = True
            return self.get_response(request)

        # 2) Остальной API — только по нашему ключу
        if path.startswith(API_PREFIX):
            key = request.headers.get("X-Api-Key") or request.META.get("HTTP_X_API_KEY")
            if not key or key != self.api_key:
                return JsonResponse({"detail": "Invalid or missing API key"}, status=403)
            request._dont_enforce_csrf_checks = True
            # Если очень нужно «аутентифицировать» запрос, раскомментируй:
            # request.user = _APIServiceUser()

        # 3) Всё остальное (включая /admin/) — пропускаем
        return self.get_response(request)
