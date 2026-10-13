from datetime import date

import pytest

from weekly_report import ReportError, build_report, load_bookings, main

WEEK = date(2026, 10, 5)  # понедельник


def write_csv(tmp_path, body: str):
    path = tmp_path / "b.csv"
    path.write_text(
        "booking_id,apartment,check_in,check_out,price_total,status\n" + body,
        encoding="utf-8",
    )
    return str(path)


# TC-01: основной сценарий на тестовом файле
def test_main_scenario():
    report = build_report(load_bookings("bookings.csv"), WEEK)
    assert report["bookings_total"] == 5
    assert report["bookings_confirmed"] == 4
    assert report["bookings_cancelled"] == 1
    assert report["revenue"] == 1330.0
    assert report["nights"] == 12
    assert report["avg_check"] == 332.5
    assert report["cancel_rate_percent"] == 20.0


# TC-02: дубли по booking_id считаются один раз
def test_duplicates_counted_once(tmp_path):
    path = write_csv(
        tmp_path,
        "B1,A,2026-10-05,2026-10-07,100,confirmed\n"
        "B1,A,2026-10-05,2026-10-07,100,confirmed\n",
    )
    assert len(load_bookings(path)) == 1


# TC-03: неделя без броней, нет деления на ноль
def test_empty_week():
    report = build_report([], WEEK)
    assert report["revenue"] == 0
    assert report["avg_check"] == 0.0
    assert report["cancel_rate_percent"] == 0.0


# TC-04: отменённая бронь не попадает в выручку
def test_cancelled_not_in_revenue(tmp_path):
    path = write_csv(tmp_path, "B1,A,2026-10-05,2026-10-07,100,cancelled\n")
    report = build_report(load_bookings(path), WEEK)
    assert report["revenue"] == 0
    assert report["cancel_rate_percent"] == 100.0


# TC-05: граница недели - заезд в воскресенье входит, в следующий понедельник нет
def test_week_boundaries(tmp_path):
    path = write_csv(
        tmp_path,
        "B1,A,2026-10-11,2026-10-12,50,confirmed\n"
        "B2,A,2026-10-12,2026-10-13,60,confirmed\n"
        "B3,A,2026-10-04,2026-10-05,70,confirmed\n",
    )
    report = build_report(load_bookings(path), WEEK)
    assert report["bookings_total"] == 1
    assert report["revenue"] == 50.0


# TC-06: пустая цена
def test_empty_price(tmp_path):
    path = write_csv(tmp_path, "B1,A,2026-10-05,2026-10-07,,confirmed\n")
    with pytest.raises(ReportError):
        load_bookings(path)


# TC-07: отрицательная цена
def test_negative_price(tmp_path):
    path = write_csv(tmp_path, "B1,A,2026-10-05,2026-10-07,-10,confirmed\n")
    with pytest.raises(ReportError):
        load_bookings(path)


# TC-08: выезд раньше заезда
def test_checkout_before_checkin(tmp_path):
    path = write_csv(tmp_path, "B1,A,2026-10-07,2026-10-05,100,confirmed\n")
    with pytest.raises(ReportError):
        load_bookings(path)


# TC-09: неверный формат даты
def test_bad_date_format(tmp_path):
    path = write_csv(tmp_path, "B1,A,05.10.2026,2026-10-07,100,confirmed\n")
    with pytest.raises(ReportError):
        load_bookings(path)


# TC-10: неизвестный статус
def test_unknown_status(tmp_path):
    path = write_csv(tmp_path, "B1,A,2026-10-05,2026-10-07,100,pending\n")
    with pytest.raises(ReportError):
        load_bookings(path)


# TC-11: нет обязательной колонки
def test_missing_column(tmp_path):
    path = tmp_path / "b.csv"
    path.write_text("booking_id,apartment\nB1,A\n", encoding="utf-8")
    with pytest.raises(ReportError):
        load_bookings(str(path))


# TC-12: дата начала недели не понедельник
def test_week_start_not_monday(capsys):
    code = main(["weekly_report.py", "bookings.csv", "2026-10-06"])
    assert code == 1
    assert "понедельником" in capsys.readouterr().out


# TC-13: файла не существует
def test_file_not_found(capsys):
    code = main(["weekly_report.py", "nope.csv", "2026-10-05"])
    assert code == 1
