# -*- coding: utf-8 -*-
"""Ctrip fixed round-trip search: TAO -> MEL 2027-02-01, return 2027-02-14."""

import csv
import json
import sys
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait

FROM_CODE = "TAO"
TO_CODE = "MEL"
DEPART_DATE = "2027-02-01"
RETURN_DATE = "2027-02-14"
LIMIT = 30
WAIT_SECONDS = 35

BASE_DIR = Path(__file__).resolve().parent
PROFILE_DIR = BASE_DIR / "ctrip_browser_profile"
OUTPUT_STEM = f"ctrip_roundtrip_{FROM_CODE}_{TO_CODE}_{DEPART_DATE}_{RETURN_DATE}"
SEARCH_URL = (
    f"https://flights.ctrip.com/online/list/round-{FROM_CODE.lower()}-{TO_CODE.lower()}"
    f"?depdate={DEPART_DATE}_{RETURN_DATE}"
    "&cabin=Y_S_C_F&adult=1&child=0&infant=0"
)

EXTRACT_JS = r"""
return (() => {
  const clean = (v) => (v || '').replace(/\s+/g, ' ').trim();
  const isTime = (s) => /^([01]?\d|2[0-3]):[0-5]\d$/.test(s);
  const isCurrency = (s) => /^[¥$€£]$/.test(s);
  const isPrice = (s) => /^\d+([.,]\d+)?$/.test(s);
  const isFlightNo = (s) => /^[A-Z0-9]{2}\d{3,4}[A-Z]?$/.test(s);
  const rows = [];

  document.querySelectorAll('.flight-item').forEach((card) => {
    const chunks = [];
    const walk = (node) => {
      for (const c of node.childNodes) {
        if (c.nodeType === 3) {
          const t = clean(c.textContent);
          if (t) chunks.push(t);
        } else if (c.nodeType === 1) walk(c);
      }
    };
    walk(card);
    if (chunks.length < 6) return;

    const depIdx = chunks.findIndex(isTime);
    if (depIdx < 1) return;
    const airline = chunks[0];
    if (!airline || isTime(airline)) return;

    let flightNo = null;
    let aircraft = null;
    for (let i = 1; i < depIdx; i++) {
      if (flightNo === null && isFlightNo(chunks[i])) flightNo = chunks[i];
      else if (aircraft === null && !isFlightNo(chunks[i])) aircraft = chunks[i];
    }

    const departureTime = chunks[depIdx];
    const departureAirport = chunks[depIdx + 1] || null;
    const arrIdx = chunks.findIndex((c, i) => i > depIdx && isTime(c));
    if (arrIdx < 0) return;
    const arrivalTime = chunks[arrIdx];
    const arrivalAirport = chunks[arrIdx + 1] || null;
    if (!departureAirport || !arrivalAirport) return;

    let terminal = null;
    if (arrIdx + 2 < chunks.length && /^T\d$/.test(chunks[arrIdx + 2])) terminal = chunks[arrIdx + 2];

    let price = null;
    let currency = null;
    for (let i = 0; i < chunks.length - 1; i++) {
      if (isCurrency(chunks[i]) && isPrice(chunks[i + 1])) {
        currency = chunks[i];
        price = Number(chunks[i + 1].replace(/,/g, ''));
        break;
      }
    }
    if (price === null) {
      for (const chunk of chunks) {
        const m = chunk.match(/([¥$€£])\s*([\d,]+(?:\.\d+)?)/);
        if (m) {
          currency = m[1];
          price = Number(m[2].replace(/,/g, ''));
          break;
        }
      }
    }

    let cabin = null;
    for (let i = chunks.length - 1; i >= 0; i--) {
      if (/舱$/.test(chunks[i])) { cabin = chunks[i]; break; }
    }

    rows.push({
      airline, flightNo, aircraft,
      departureTime, departureAirport,
      arrivalTime, arrivalAirport, terminal,
      price, currency, cabin,
      rawText: clean(card.innerText)
    });
  });
  return rows;
})();
"""


def build_driver():
    options = webdriver.EdgeOptions()
    PROFILE_DIR.mkdir(exist_ok=True)
    options.add_argument(f"--user-data-dir={PROFILE_DIR}")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-popup-blocking")
    return webdriver.Edge(options=options)


def body_text(driver):
    try:
        return driver.find_element("tag name", "body").text or ""
    except Exception:
        return ""


def page_state(driver):
    text = body_text(driver).lower()
    url = driver.current_url.lower()
    if "captcha" in url or "验证码" in text or "安全验证" in text or "verify the human" in text:
        return "captcha"
    cards = driver.find_elements("css selector", ".flight-item")
    if cards and any(s in text for s in ("¥", "$", "€", "£")):
        return "content"
    return False


def wait_results(driver):
    return WebDriverWait(driver, WAIT_SECONDS).until(page_state)


def handle_captcha(driver, state):
    if state != "captcha":
        return
    print("\n携程要求验证码/安全验证。请在 Edge 中手动完成。")
    input("完成后回到此窗口，按 Enter 继续... ")
    driver.get(SEARCH_URL)
    if wait_results(driver) == "captcha":
        raise RuntimeError("验证后仍停留在验证码页面，请稍后重试或先在浏览器登录携程。")


def scroll_more(driver):
    last = len(driver.find_elements("css selector", ".flight-item"))
    plateau = 0
    for _ in range(8):
        if last >= LIMIT:
            break
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2.2)
        now = len(driver.find_elements("css selector", ".flight-item"))
        if now == last:
            plateau += 1
            if plateau >= 2:
                break
        else:
            plateau = 0
            last = now


def extract_rows(driver):
    raw = driver.execute_script(EXTRACT_JS)
    if not isinstance(raw, list):
        return []
    rows = []
    for r in raw:
        if not all([r.get("airline"), r.get("departureTime"), r.get("departureAirport"), r.get("arrivalTime"), r.get("arrivalAirport")]):
            continue
        r["searchUrl"] = SEARCH_URL
        rows.append(r)
    rows.sort(key=lambda r: (r.get("price") is None, r.get("price") or 10**12))
    return rows[:LIMIT]


def save(rows):
    csv_path = BASE_DIR / f"{OUTPUT_STEM}.csv"
    json_path = BASE_DIR / f"{OUTPUT_STEM}.json"
    fields = [
        "rank", "airline", "flightNo", "aircraft",
        "departureTime", "departureAirport", "arrivalTime", "arrivalAirport",
        "terminal", "price", "currency", "cabin", "searchUrl", "rawText"
    ]
    for i, row in enumerate(rows, 1):
        row["rank"] = i
    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    with json_path.open("w", encoding="utf-8") as f:
        json.dump({
            "search": {
                "from": FROM_CODE, "to": TO_CODE,
                "depart": DEPART_DATE, "return": RETURN_DATE,
                "url": SEARCH_URL,
                "note": "携程往返结果第一步：去程候选显示往返总价/起始总价；选定去程后再选返程，最终价格可能变化。"
            },
            "results": rows
        }, f, ensure_ascii=False, indent=2)
    return csv_path, json_path


def print_rows(rows):
    print("\n" + "=" * 70)
    print(f"青岛 TAO -> 墨尔本 MEL：{DEPART_DATE}")
    print(f"墨尔本 MEL -> 青岛 TAO：{RETURN_DATE}")
    print("携程往返模式（不是两张单程简单相加）")
    print("=" * 70)
    if not rows:
        print("没有解析到航班卡片。请检查浏览器页面是否已经正常显示结果。")
        return
    for row in rows[:10]:
        price = "价格未解析" if row.get("price") is None else f"{row.get('currency') or ''}{row['price']}"
        print(
            f"{row['rank']:>2}. {row['airline']} | "
            f"{row['departureTime']} {row['departureAirport']} -> "
            f"{row['arrivalTime']} {row['arrivalAirport']} | {price}"
        )


def main():
    print("正在打开：")
    print(SEARCH_URL)
    driver = None
    try:
        driver = build_driver()
        driver.get(SEARCH_URL)
        state = wait_results(driver)
        handle_captcha(driver, state)
        scroll_more(driver)
        rows = extract_rows(driver)
        csv_path, json_path = save(rows)
        print_rows(rows)
        print(f"\nCSV：{csv_path}")
        print(f"JSON：{json_path}")
        print("\nEdge 会保留在携程往返结果页。可点击最合适的去程，再选择 2027-02-14 的返程航班。")
        input("查看完成后按 Enter 关闭浏览器... ")
    except KeyboardInterrupt:
        print("\n已取消。")
    except Exception as exc:
        print(f"\n运行失败：{type(exc).__name__}: {exc}")
        print("请确认 Edge 可联网；若有验证码请手动完成后重新运行。")
        if driver:
            try:
                input("按 Enter 关闭浏览器... ")
            except Exception:
                pass
        sys.exit(1)
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass


if __name__ == "__main__":
    main()
