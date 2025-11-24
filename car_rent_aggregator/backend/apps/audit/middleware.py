from __future__ import annotations
import time
from typing import Callable

from django.http import HttpRequest, HttpResponse
from django.conf import settings

from .models import AuditEvent

WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
API_PREFIX = getattr(settings, "API_PREFIX", "/api/")
WEBHOOK_WHITELIST = tuple(getattr(settings, "WEBHOOK_WHITELIST_PATHS", []) or ())


def _path_is_webhook(path: str) -> bool:
    p = (path or "/").strip()
    for base in WEBHOOK_WHITELIST:
        b = (base or "").strip()
        if p == b or p.startswith(b):
            return True
    return False


class RequestAuditMiddleware:
    """
    Лёгкий request-аудит:
      - Пишем только write-методы (POST/PUT/PATCH/DELETE).
      - Логируем /admin/* и /api/* (включая вебхуки).
      - actor_kind:
           user    — обычный staff/superuser из админки
           bot     — запрос с валидным X-Api-Key (боты)
           webhook — Payme/Click вебхуки (пути из WEBHOOK_WHITELIST_PATHS)
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response
        self.api_key = getattr(settings, "BOTS_API_KEY", "")

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Пишем только изменяющие запросы
        if request.method not in WRITE_METHODS:
            return self.get_response(request)

        started = time.perf_counter()
        response: HttpResponse | None = None
        ex: Exception | None = None

        try:
            response = self.get_response(request)
            return response
        except Exception as e:
            ex = e
            raise
        finally:
            # ВАЖНО: тут НЕТ return, чтобы не перебивать ответ!
            self._log_request(request, response, started, ex)

    def _log_request(
        self,
        request: HttpRequest,
        response: HttpResponse | None,
        started: float,
        ex: Exception | None,
    ) -> None:
        """
        Вспомогательная функция, которая пишет AuditEvent.
        Любые return/исключения здесь НЕ влияют на __call__.
        """
        try:
            path = request.path or "/"

            # Логируем только admin и API; остальное (включая /i18n/setlang/) пропускаем
            if not (path.startswith("/admin/") or path.startswith(API_PREFIX)):
                return

            actor_kind = "user"
            actor_label = ""
            user = getattr(request, "user", None)

            # вебхуки?
            if _path_is_webhook(path):
                actor_kind = "webhook"
                actor_label = "webhook"

            # api-бот?
            elif path.startswith(API_PREFIX):
                key = request.headers.get("X-Api-Key") or request.META.get("HTTP_X_API_KEY")
                if key and key == self.api_key:
                    actor_kind = "bot"
                    actor_label = "X-Api-Key"

            # статус и задержка
            if response is not None:
                status = response.status_code
            else:
                status = 500
            latency_ms = int((time.perf_counter() - started) * 1000)

            # кто
            is_staff = bool(getattr(user, "is_staff", False))
            is_superuser = bool(getattr(user, "is_superuser", False))
            ip = (
                request.META.get("HTTP_X_REAL_IP")
                or request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
                or request.META.get("REMOTE_ADDR")
            )

            resolver_match = getattr(request, "resolver_match", None)
            view_name = resolver_match.view_name if resolver_match else ""

            AuditEvent.objects.create(
                user=user if getattr(user, "is_authenticated", False) else None,
                is_staff=is_staff,
                is_superuser=is_superuser,
                actor_kind=actor_kind,
                actor_label=actor_label,
                ip=ip,
                ua=request.META.get("HTTP_USER_AGENT", ""),
                path=path,
                method=request.method,
                status_code=status,
                latency_ms=latency_ms,
                view_name=view_name,
                action=_infer_action(request, status, actor_kind, ex),
                object_model="",
                object_id="",
                object_repr="",
                changes=None,
                extra={"GET": request.GET.dict() if request.GET else None},
            )
        except Exception:
            # аудит не должен ломать основной поток
            return


def _infer_action(request: HttpRequest, status: int, actor_kind: str, ex: Exception | None) -> str:
    """
    Мини-эвристика: распознаём действие по пути/методу.
    """
    path = (request.path or "").lower()
    m = request.method.upper()

    if actor_kind == "webhook":
        return "webhook.success" if status < 400 else "webhook.fail"

    if path.startswith("/admin/login/") and m == "POST":
        return "login" if status in (302, 200) else "login.fail"
    if path.startswith("/admin/logout/"):
        return "logout"

    # простые CRUD-ярлыки
    if m == "POST":
        return "create" if status < 400 else "create.fail"
    if m == "PUT" or m == "PATCH":
        return "update" if status < 400 else "update.fail"
    if m == "DELETE":
        return "delete" if status < 400 else "delete.fail"

    return "write"
