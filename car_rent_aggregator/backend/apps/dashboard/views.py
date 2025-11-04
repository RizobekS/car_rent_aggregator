# apps/dashboard/views.py
from django.views.generic import TemplateView, View
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import render

from apps.cars.models import Region
from apps.partners.models import Partner, PartnerAdminLink
from apps.dashboard.utils import (
    parse_period,
    base_queryset,
    calc_stats,
    build_excel,
)

PARTNER_GROUP = "Partners"


def _user_partner_ids(user):
    return list(
        PartnerAdminLink.objects.filter(user=user, is_active=True)
        .values_list("partner_id", flat=True)
    )


def _is_partner_admin(user) -> bool:
    return (
        user.is_authenticated
        and user.is_active
        and user.is_staff
        and user.groups.filter(name=PARTNER_GROUP).exists()
    )


@method_decorator(staff_member_required, name="dispatch")
class DashboardReportView(TemplateView):
    """
    /admin/report/
    Веб-дашборд с метриками и графиками.
    Партнёр-админ видит ТОЛЬКО свои данные.
    Суперадмин видит всё и сравнение партнёров.
    """
    template_name = "dashboard/report.html"

    def get(self, request, *args, **kwargs):
        date_from, date_to = parse_period(request)

        partner_id = request.GET.get("partner")
        region_id  = request.GET.get("region")

        partner_mode = _is_partner_admin(request.user)

        # если это партнёр-админ, то он ограничен своими партнёрами
        if partner_mode:
            allowed = _user_partner_ids(request.user)
            if not allowed:
                return HttpResponseForbidden("Нет доступа к данным партнёра")
            # не дать посмотреть чужого партнёра
            if partner_id and int(partner_id) not in allowed:
                partner_id = allowed[0]
            if not partner_id:
                partner_id = allowed[0]

        qs = base_queryset(date_from, date_to, partner_id=partner_id, region_id=region_id)
        stats = calc_stats(qs)

        context = {
            "date_from": date_from,
            "date_to": date_to,

            "stats": stats,
            "top_cars": stats["top_cars_raw"],               # [(car, sum), ...]
            "top_partners": stats["top_partners_raw"],       # [(partner, sum), ...]

            # фильтры
            "regions": Region.objects.all().order_by("name"),
            "partners": Partner.objects.all().order_by("name"),
            "current_partner_id": int(partner_id) if partner_id else None,
            "current_region_id": int(region_id) if region_id else None,
            "is_partner_admin": partner_mode,

            # график топ машин
            "chart_labels": stats["chart_labels"],                   # list[str]
            "chart_values": stats["chart_values"],                   # list[float]

            # график топ партнёров (только админ видит)
            "partners_chart_labels": stats["partners_chart_labels"], # list[str]
            "partners_chart_values": stats["partners_chart_values"], # list[float]
            "show_partner_chart": (not partner_mode),
        }
        return render(request, self.template_name, context)


@method_decorator(staff_member_required, name="dispatch")
class DashboardExportExcelView(View):
    """
    /admin/report/export.xlsx
    Выгружает XLSX по тем же фильтрам.
    """
    def get(self, request, *args, **kwargs):
        date_from, date_to = parse_period(request)

        partner_id = request.GET.get("partner")
        region_id  = request.GET.get("region")

        if _is_partner_admin(request.user):
            allowed = _user_partner_ids(request.user)
            if not allowed:
                return HttpResponseForbidden("Нет доступа к данным партнёра")
            if partner_id and int(partner_id) not in allowed:
                partner_id = allowed[0]
            if not partner_id:
                partner_id = allowed[0]

        qs = base_queryset(date_from, date_to, partner_id=partner_id, region_id=region_id)
        wb = build_excel(qs, date_from, date_to)

        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        filename = f"report_{date_from.date()}_{date_to.date()}.xlsx"
        response["Content-Disposition"] = f'attachment; filename=\"{filename}\"'

        wb.save(response)
        return response
