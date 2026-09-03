# -*- coding: utf-8 -*-
from pathlib import Path
from datetime import datetime
import csv
import json
import os
import subprocess
import time

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait

FROM_CODE = 'MEL'
TO_CODE = 'TAO'
DEPART_DATE = '2027-02-01'
RETURN_DATE = '2027-02-14'
LIMIT = 30
WAIT_SECONDS = 35

BASE = Path.home() / 'CtripFareCheck'
RESULTS = BASE / 'results'
PROFILE = BASE / 'edge_profile'
REPO = BASE / 'repo_sync'
MONITOR_DIR = REPO / 'flight-monitor' / 'MEL-TAO'
AUTOMATED = os.environ.get('CTRIP_AUTOMATED') == '1'

RESULTS.mkdir(parents=True, exist_ok=True)
PROFILE.mkdir(parents=True, exist_ok=True)

URL = (
    f'https://flights.ctrip.com/online/list/round-{FROM_CODE.lower()}-{TO_CODE.lower()}'
    f'?depdate={DEPART_DATE}_{RETURN_DATE}&cabin=Y_S_C_F&adult=1&child=0&infant=0'
)

JS = r'''return (()=>{const c=v=>(v||'').replace(/\s+/g,' ').trim(),t=s=>/^([01]?\d|2[0-3]):[0-5]\d$/.test(s),cur=s=>/^[¥$€£]$/.test(s),num=s=>/^\d+([.,]\d+)?$/.test(s);const out=[];document.querySelectorAll('.flight-item').forEach(card=>{const a=[];const w=n=>{for(const x of n.childNodes){if(x.nodeType===3){const z=c(x.textContent);if(z)a.push(z)}else if(x.nodeType===1)w(x)}};w(card);const i=a.findIndex(t);if(i<1)return;const j=a.findIndex((x,k)=>k>i&&t(x));if(j<0)return;let p=null,cc=null;for(let k=0;k<a.length-1;k++){if(cur(a[k])&&num(a[k+1])){cc=a[k];p=Number(a[k+1].replace(/,/g,''));break}}if(p===null){for(const x of a){const m=x.match(/([¥$€£])\s*([\d,]+(?:\.\d+)?)/);if(m){cc=m[1];p=Number(m[2].replace(/,/g,''));break}}}out.push({airline:a[0],departureTime:a[i],departureAirport:a[i+1]||'',arrivalTime:a[j],arrivalAirport:a[j+1]||'',price:p,currency:cc,cabin:(a.slice().reverse().find(x=>/舱$/.test(x))||''),rawText:c(card.innerText)});});return out;})();'''


def page_state(driver):
    try:
        text = (driver.find_element('tag name', 'body').text or '').lower()
        if 'captcha' in driver.current_url.lower() or '验证码' in text or '安全验证' in text:
            return 'captcha'
        if driver.find_elements('css selector', '.flight-item') and any(s in text for s in ('¥', '$', '€', '£')):
            return 'content'
    except Exception:
        pass
    return False


def run_git(*args, check=True):
    return subprocess.run(
        ['git', '-C', str(REPO), *args],
        text=True,
        capture_output=True,
        check=check,
    )


def sync_status(status, rows=None, note=None):
    rows = rows or []
    if not (REPO / '.git').exists():
        print('GitHub sync skipped: repo_sync is not configured yet.')
        return False

    try:
        pull = run_git('pull', '--rebase', 'origin', 'main', check=False)
        if pull.returncode != 0:
            print('GitHub pull warning:', (pull.stderr or pull.stdout).strip())

        MONITOR_DIR.mkdir(parents=True, exist_ok=True)
        latest_path = MONITOR_DIR / 'latest.json'
        history_path = MONITOR_DIR / 'history.jsonl'

        previous = None
        if latest_path.exists():
            try:
                previous = json.loads(latest_path.read_text(encoding='utf-8'))
            except Exception:
                previous = None

        priced = [r for r in rows if isinstance(r.get('price'), (int, float))]
        lowest = priced[0] if priced else None
        previous_price = previous.get('lowest_price') if isinstance(previous, dict) else None
        previous_currency = previous.get('currency') if isinstance(previous, dict) else None

        currency = lowest.get('currency') if lowest else None
        lowest_price = lowest.get('price') if lowest else None
        change_amount = None
        change_percent = None
        if (
            isinstance(lowest_price, (int, float))
            and isinstance(previous_price, (int, float))
            and currency == previous_currency
        ):
            change_amount = round(lowest_price - previous_price, 2)
            if previous_price:
                change_percent = round(change_amount / previous_price * 100, 2)

        top_results = []
        for r in rows[:5]:
            top_results.append({
                'rank': r.get('rank'),
                'airline': r.get('airline'),
                'departureTime': r.get('departureTime'),
                'departureAirport': r.get('departureAirport'),
                'arrivalTime': r.get('arrivalTime'),
                'arrivalAirport': r.get('arrivalAirport'),
                'price': r.get('price'),
                'currency': r.get('currency'),
                'cabin': r.get('cabin'),
            })

        payload = {
            'checked_at': datetime.now().astimezone().isoformat(timespec='seconds'),
            'status': status,
            'route': {
                'outbound': f'{FROM_CODE}->{TO_CODE}',
                'depart_date': DEPART_DATE,
                'return': f'{TO_CODE}->{FROM_CODE}',
                'return_date': RETURN_DATE,
            },
            'lowest_price': lowest_price,
            'currency': currency,
            'previous_lowest_price': previous_price,
            'change_amount': change_amount,
            'change_percent': change_percent,
            'lowest_result': top_results[0] if top_results else None,
            'top_results': top_results,
            'result_count': len(rows),
            'search_url': URL,
            'note': note,
        }

        latest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        with history_path.open('a', encoding='utf-8') as f:
            f.write(json.dumps(payload, ensure_ascii=False) + '\n')

        run_git('config', 'user.name', 'Ctrip Fare Monitor', check=False)
        run_git('config', 'user.email', 'ctrip-fare-monitor@users.noreply.github.com', check=False)
        run_git('add', 'flight-monitor/MEL-TAO/latest.json', 'flight-monitor/MEL-TAO/history.jsonl')
        commit = run_git('commit', '-m', f'chore: update MEL-TAO fare {datetime.now():%Y-%m-%d %H:%M}', check=False)
        if commit.returncode != 0 and 'nothing to commit' not in ((commit.stdout or '') + (commit.stderr or '')).lower():
            print('GitHub commit failed:', (commit.stderr or commit.stdout).strip())
            return False
        push = run_git('push', 'origin', 'main', check=False)
        if push.returncode != 0:
            print('GitHub push failed:', (push.stderr or push.stdout).strip())
            return False
        print('GitHub latest fare status synced successfully.')
        return True
    except Exception as exc:
        print(f'GitHub sync failed: {type(exc).__name__}: {exc}')
        return False


def save_local(rows):
    ts = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    csv_path = RESULTS / f'{ts}_MEL-TAO.csv'
    json_path = RESULTS / f'{ts}_MEL-TAO.json'

    fields = [
        'rank', 'airline', 'departureTime', 'departureAirport',
        'arrivalTime', 'arrivalAirport', 'price', 'currency',
        'cabin', 'url', 'rawText'
    ]
    with csv_path.open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    with json_path.open('w', encoding='utf-8') as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    return csv_path, json_path


def main():
    options = webdriver.EdgeOptions()
    options.add_argument(f'--user-data-dir={PROFILE}')
    options.add_argument('--start-maximized')
    driver = webdriver.Edge(options=options)

    try:
        print('2027-02-01 墨尔本 MEL -> 青岛 TAO')
        print('2027-02-14 青岛 TAO -> 墨尔本 MEL')
        print(URL)
        driver.get(URL)
        state = WebDriverWait(driver, WAIT_SECONDS).until(page_state)

        if state == 'captcha':
            if AUTOMATED:
                print('Ctrip CAPTCHA/security verification detected during automatic run.')
                sync_status('captcha_required', note='携程要求验证码/安全验证；请手动运行脚本完成验证。')
                return
            print('携程要求验证码/安全验证，请在 Edge 中手动完成。')
            input('完成后按 Enter 继续...')
            driver.get(URL)
            state = WebDriverWait(driver, WAIT_SECONDS).until(page_state)
            if state == 'captcha':
                sync_status('captcha_required', note='人工验证后仍检测到验证码。')
                raise RuntimeError('验证后仍停留在验证码页面。')

        for _ in range(6):
            driver.execute_script('window.scrollTo(0,document.body.scrollHeight)')
            time.sleep(1.8)

        rows = driver.execute_script(JS) or []
        rows = sorted(rows, key=lambda r: (r.get('price') is None, r.get('price') or 10**12))[:LIMIT]
        for i, row in enumerate(rows, 1):
            row['rank'] = i
            row['url'] = URL

        csv_path, _ = save_local(rows)
        print(f'已保存 {len(rows)} 条结果：{csv_path}')
        for row in rows[:10]:
            print(
                row['rank'], row.get('airline'), row.get('departureTime'), '->',
                row.get('arrivalTime'), f"{row.get('currency') or ''}{row.get('price') or ''}"
            )

        if rows:
            sync_status('ok', rows=rows)
        else:
            sync_status('empty', note='结果页已加载，但没有解析到可用航班卡片。')

        if not AUTOMATED:
            time.sleep(15)
    except Exception as exc:
        if AUTOMATED:
            sync_status('error', note=f'{type(exc).__name__}: {exc}')
        raise
    finally:
        driver.quit()


if __name__ == '__main__':
    main()
