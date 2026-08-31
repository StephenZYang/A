# Ctrip 往返机票搜索：青岛 ↔ 墨尔本

固定行程：

- 去程：2027-02-01 青岛（TAO）→ 墨尔本（MEL）
- 返程：2027-02-14 墨尔本（MEL）→ 青岛（TAO）

## Windows 最快运行方法

1. 安装 **Python 3.11**，安装时勾选 `Add Python to PATH`。
2. 确保 **Microsoft Edge** 已安装并能正常访问携程。
3. 下载本目录的三个文件到同一个文件夹：
   - `ctrip_roundtrip_qingdao_melbourne.py`
   - `requirements.txt`
   - `run_windows.bat`
4. 双击 `run_windows.bat`。
5. 第一次运行会自动创建 `.venv` 并安装 Selenium。
6. Edge 会直接打开携程真正的往返结果页。
7. 如果出现验证码/安全验证，请在 Edge 中手动完成，再回命令窗口按 Enter。
8. 程序会生成：
   - `ctrip_roundtrip_TAO_MEL_2027-02-01_2027-02-14.csv`
   - `ctrip_roundtrip_TAO_MEL_2027-02-01_2027-02-14.json`

## 搜索方式

脚本直接访问：

```text
https://flights.ctrip.com/online/list/round-tao-mel?depdate=2027-02-01_2027-02-14&cabin=Y_S_C_F&adult=1&child=0&infant=0
```

这是携程的 **往返模式**，不是分别查两张单程后相加。

携程往返流程第一步会展示去程候选及对应的 **往返总价 / 起始总价**。选择一个去程后，再进入返程航班选择，因此具体返程航班仍可能改变最终应付价格。脚本会保持浏览器打开，方便继续人工选择返程。

## 输出内容

CSV/JSON 会包含尽可能解析到的：

- 航司
- 航班号（往返页可能不展示）
- 机型（往返页可能不展示）
- 出发/到达时间
- 出发/到达机场
- 价格
- 币种
- 舱位
- 原始航班卡片文本

结果会优先按可解析价格从低到高排序。

## 修改日期或城市

打开 `ctrip_roundtrip_qingdao_melbourne.py` 顶部修改：

```python
FROM_CODE = "TAO"
TO_CODE = "MEL"
DEPART_DATE = "2027-02-01"
RETURN_DATE = "2027-02-14"
```

## 隐私与限制

- 不自动绕过验证码，也不使用代理池。
- `ctrip_browser_profile/` 会保存在本机，用于复用登录/验证状态；不要把该目录上传到公开仓库。
- 携程页面结构可能变化。如果浏览器能看到航班但 CSV 为空，通常说明 `.flight-item` 的 DOM 结构发生更新，需要调整解析器。
