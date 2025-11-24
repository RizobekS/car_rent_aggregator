# config/views.py
from urllib.parse import urlparse, urlunparse

from django.conf import settings
from django.http import HttpResponseRedirect
from django.utils.translation import activate
from django.views import View


class ActivateLanguageView(View):
    """
    Переключатель языка по URL типа /set_language/<lang>/?next=/ru/admin/
    Корректно подменяет сегмент языка в пути и ставит cookie.
    """

    def get(self, request, lang):
        # Куда возвращаться после смены языка:
        next_url = request.GET.get("next") or request.META.get("HTTP_REFERER") or "/"

        parsed = urlparse(next_url)

        # Защита от внешних хостов: редиректим только внутри текущего домена
        if parsed.netloc and parsed.netloc != request.get_host():
            parsed = parsed._replace(path="/", netloc="")

        path = parsed.path
        parts = path.split("/")

        langs = dict(settings.LANGUAGES).keys()

        # Если URL уже содержит сегмент языка /ru/... → заменяем его
        if len(parts) > 1 and parts[1] in langs:
            parts[1] = lang
        else:
            # Иначе вставляем язык как первый сегмент после слеша
            parts.insert(1, lang)

        new_path = "/".join(parts)
        new_parsed = parsed._replace(path=new_path)
        redirect_url = urlunparse(new_parsed)

        # Активируем язык и ставим cookie
        activate(lang)
        response = HttpResponseRedirect(redirect_url)
        response.set_cookie(settings.LANGUAGE_COOKIE_NAME, lang)
        return response
