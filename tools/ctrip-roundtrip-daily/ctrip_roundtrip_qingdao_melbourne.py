# -*- coding: utf-8 -*-
from pathlib import Path
from datetime import datetime
import csv, json, time
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait

FROM_CODE='MEL'; TO_CODE='TAO'
DEPART_DATE='2027-02-01'; RETURN_DATE='2027-02-14'
LIMIT=30; WAIT_SECONDS=35
BASE=Path.home()/'CtripFareCheck'; RESULTS=BASE/'results'; PROFILE=BASE/'edge_profile'
RESULTS.mkdir(parents=True,exist_ok=True); PROFILE.mkdir(parents=True,exist_ok=True)
URL=(f'https://flights.ctrip.com/online/list/round-{FROM_CODE.lower()}-{TO_CODE.lower()}'
     f'?depdate={DEPART_DATE}_{RETURN_DATE}&cabin=Y_S_C_F&adult=1&child=0&infant=0')

JS=r'''return (()=>{const c=v=>(v||'').replace(/\s+/g,' ').trim(),t=s=>/^([01]?\d|2[0-3]):[0-5]\d$/.test(s),cur=s=>/^[¥$€£]$/.test(s),num=s=>/^\d+([.,]\d+)?$/.test(s);const out=[];document.querySelectorAll('.flight-item').forEach(card=>{const a=[];const w=n=>{for(const x of n.childNodes){if(x.nodeType===3){const z=c(x.textContent);if(z)a.push(z)}else if(x.nodeType===1)w(x)}};w(card);const i=a.findIndex(t);if(i<1)return;const j=a.findIndex((x,k)=>k>i&&t(x));if(j<0)return;let p=null,cc=null;for(let k=0;k<a.length-1;k++){if(cur(a[k])&&num(a[k+1])){cc=a[k];p=Number(a[k+1].replace(/,/g,''));break}}if(p===null){for(const x of a){const m=x.match(/([¥$€£])\s*([\d,]+(?:\.\d+)?)/);if(m){cc=m[1];p=Number(m[2].replace(/,/g,''));break}}}out.push({airline:a[0],departureTime:a[i],departureAirport:a[i+1]||'',arrivalTime:a[j],arrivalAirport:a[j+1]||'',price:p,currency:cc,cabin:(a.slice().reverse().find(x=>/舱$/.test(x))||''),rawText:c(card.innerText)});});return out;})();'''

def state(d):
    try:
        text=(d.find_element('tag name','body').text or '').lower()
        if 'captcha' in d.current_url.lower() or '验证码' in text or '安全验证' in text:return 'captcha'
        if d.find_elements('css selector','.flight-item') and any(s in text for s in ('¥','$','€','£')):return 'content'
    except Exception:pass
    return False

def main():
    o=webdriver.EdgeOptions();o.add_argument(f'--user-data-dir={PROFILE}');o.add_argument('--start-maximized')
    d=webdriver.Edge(options=o)
    try:
        print('2027-02-01 墨尔本 MEL -> 青岛 TAO')
        print('2027-02-14 青岛 TAO -> 墨尔本 MEL')
        print(URL);d.get(URL);s=WebDriverWait(d,WAIT_SECONDS).until(state)
        if s=='captcha':
            print('携程要求验证码/安全验证，请在 Edge 中手动完成。');input('完成后按 Enter 继续...');d.get(URL);s=WebDriverWait(d,WAIT_SECONDS).until(state)
        for _ in range(6):d.execute_script('window.scrollTo(0,document.body.scrollHeight)');time.sleep(1.8)
        rows=d.execute_script(JS) or [];rows=sorted(rows,key=lambda r:(r.get('price') is None,r.get('price') or 10**12))[:LIMIT]
        ts=datetime.now().strftime('%Y-%m-%d_%H-%M-%S');csvp=RESULTS/f'{ts}_MEL-TAO.csv';jsonp=RESULTS/f'{ts}_MEL-TAO.json'
        for i,r in enumerate(rows,1):r['rank']=i;r['url']=URL
        fields=['rank','airline','departureTime','departureAirport','arrivalTime','arrivalAirport','price','currency','cabin','url','rawText']
        with csvp.open('w',newline='',encoding='utf-8-sig') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
        with jsonp.open('w',encoding='utf-8') as f:json.dump(rows,f,ensure_ascii=False,indent=2)
        print(f'已保存 {len(rows)} 条结果：{csvp}')
        for r in rows[:10]:print(r['rank'],r.get('airline'),r.get('departureTime'),'->',r.get('arrivalTime'),f"{r.get('currency') or ''}{r.get('price') or ''}")
        time.sleep(15)
    finally:d.quit()
if __name__=='__main__':main()
