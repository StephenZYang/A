# Ctrip-Crawler是什么，现在还能不能直接用？

## 原始问题
> https://github.com/Suysker/Ctrip-Crawler

## 核心回答
Ctrip-Crawler 不是 ChatGPT Skill，而是一个独立的 Python 携程机票爬虫项目。它主要通过 **Selenium + SeleniumWire** 控制真实浏览器，并截取携程网页产生的网络请求，再解析航班、票价等数据，最后使用 pandas 输出 CSV。

主要能力包括：
- Selenium 浏览器自动化；
- SeleniumWire 网络请求截取；
- 登录与 Cookie 缓存；
- 验证码检测和人工干预；
- 页面/请求异常后的重试；
- IPv6 代理相关策略；
- 航班、票价和部分舒适度数据解析；
- CSV 输出及 CSV→Excel 转换。

当前主程序为：

```text
ctrip_flights_scraper_V3.py
```

主要依赖包括：

```text
pandas==2.2.3
selenium_wire==5.1.0
blinker==1.7.0
python-magic / python-magic-bin
```

## 关键判断：2026 年还能不能直接用？
不能默认认为可以开箱即用。

仓库最后一次代码 push 是 **2025-05-24**。携程网页结构、接口、验证码和反爬机制都可能发生变化，因此到 2026 年运行时可能遇到：

- Selenium 元素定位失效；
- SeleniumWire 无法捕获原有目标请求；
- 接口字段或响应结构变化；
- 登录流程变化；
- 验证码/风控策略升级；
- Chrome / Edge 与 WebDriver 版本兼容问题。

README 中提到的 **JS 逆向版本** 仍属于后续计划，而不是当前已经完成的替代方案。

## 最终心智模型

```text
Ctrip-Crawler
    ↓
真实浏览器自动化（Selenium）
    ↓
触发携程网页正常请求
    ↓
SeleniumWire 截取网络响应
    ↓
解析 JSON / gzip 数据
    ↓
pandas 整理
    ↓
CSV / Excel
```

它的优势不是“直接破解携程 API”，而是 **借浏览器替自己完成网页交互，再从真实请求中拿数据**。

因此判断一个旧爬虫是否还能用，重点不是看 Python 代码能不能启动，而是检查：

```text
页面 DOM 是否还一致
→ 目标请求是否还存在
→ 响应字段是否还一致
→ 登录/验证码是否还能通过
→ 浏览器驱动和依赖是否兼容
```

## 一句话速记
Ctrip-Crawler 是一个 Selenium + SeleniumWire 的携程机票采集工具；思路仍有参考价值，但因为最后代码更新停在 2025 年，2026 年使用前应先做兼容性验证，不能假设直接运行就能工作。

## Source
https://github.com/Suysker/Ctrip-Crawler
