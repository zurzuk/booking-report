"""Еженедельный отчёт по бронированиям апартаментов.

Читает CSV с бронированиями и считает за неделю:
выручку, количество ночей, средний чек и долю отмен.

Запуск:
    python weekly_report.py bookings.csv 2026-10-05
где вторая дата - понедельник нужной недели.
"""
import csv
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta

REQUIRED_COLUMNS = {"booking_id", "apartment", "check_in", "check_out", "price_total", "status"}
VALID_STATUSES = {"confirmed", "cancelled"}


class ReportError(Exception):
    """Ошибка во входных данных."""


@dataclass
class Booking:
    booking_id: str
    apartment: str
    check_in: date
    check_out: date
    price_total: float
    status: str

    @property
    def nights(self) -> int:
        return (self.check_out - self.check_in).days


def parse_date(value: str, field: str) -> date:
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except (ValueError, AttributeError):
        raise ReportError(f"Неверная дата в поле {field}: {value!r}")


def load_bookings(path: str) -> list[Booking]:
    """Читает CSV, пропускает дубли по booking_id, проверяет данные."""
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or not REQUIRED_COLUMNS.issubset(reader.fieldnames):
            raise ReportError(f"В файле должны быть колонки: {sorted(REQUIRED_COLUMNS)}")

        bookings: list[Booking] = []
        seen_ids: set[str] = set()
        for row_num, row in enumerate(reader, start=2):
            booking_id = (row["booking_id"] or "").strip()
            if not booking_id:
                raise ReportError(f"Строка {row_num}: пустой booking_id")
            if booking_id in seen_ids:
                continue  # дубль, считаем один раз
            seen_ids.add(booking_id)

            status = (row["status"] or "").strip().lower()
            if status not in VALID_STATUSES:
                raise ReportError(f"Строка {row_num}: неизвестный статус {status!r}")

            try:
                price = float(row["price_total"])
            except (TypeError, ValueError):
                raise ReportError(f"Строка {row_num}: неверная цена {row['price_total']!r}")
            if price < 0:
                raise ReportError(f"Строка {row_num}: цена не может быть отрицательной")

            check_in = parse_date(row["check_in"], "check_in")
            check_out = parse_date(row["check_out"], "check_out")
            if check_out <= check_in:
                raise ReportError(f"Строка {row_num}: выезд раньше или в день заезда")

            bookings.append(
                Booking(booking_id, row["apartment"].strip(), check_in, check_out, price, status)
            )
    return bookings


def build_report(bookings: list[Booking], week_start: date) -> dict:
    """Считает метрики по броням, у которых заезд попадает в неделю [пн, вс]."""
    week_end = week_start + timedelta(days=6)
    week_bookings = [b for b in bookings if week_start <= b.check_in <= week_end]

    confirmed = [b for b in week_bookings if b.status == "confirmed"]
    cancelled = [b for b in week_bookings if b.status == "cancelled"]

    revenue = sum(b.price_total for b in confirmed)
    nights = sum(b.nights for b in confirmed)
    total = len(week_bookings)

    return {
        "week_start": week_start.isoformat(),
        "week_end": week_end.isoformat(),
        "bookings_total": total,
        "bookings_confirmed": len(confirmed),
        "bookings_cancelled": len(cancelled),
        "revenue": round(revenue, 2),
        "nights": nights,
        "avg_check": round(revenue / len(confirmed), 2) if confirmed else 0.0,
        "cancel_rate_percent": round(len(cancelled) / total * 100, 1) if total else 0.0,
    }


def format_report(report: dict) -> str:
    return (
        f"Отчёт за неделю {report['week_start']} - {report['week_end']}\n"
        f"Всего броней: {report['bookings_total']} "
        f"(подтверждено {report['bookings_confirmed']}, отменено {report['bookings_cancelled']})\n"
        f"Выручка: {report['revenue']:.2f} EUR\n"
        f"Ночей: {report['nights']}\n"
        f"Средний чек: {report['avg_check']:.2f} EUR\n"
        f"Доля отмен: {report['cancel_rate_percent']}%"
    )


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__)
        return 1
    try:
        week_start = parse_date(argv[2], "week_start")
        if week_start.weekday() != 0:
            raise ReportError("Дата начала недели должна быть понедельником")
        bookings = load_bookings(argv[1])
        print(format_report(build_report(bookings, week_start)))
    except (ReportError, FileNotFoundError) as e:
        print(f"Ошибка: {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
