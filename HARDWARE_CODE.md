# 项目硬件部分代码盘点

本文件是智慧大棚教学平台 `d:\IoT` 配套硬件代码的索引。硬件代码**不在** `d:\IoT` 仓库内，分布在以下 4 个有效关联项目中。设备通过 MQTT / HTTP / UART 与后端或上位机通信。

## 一、代码位置总览

| 路径 | 项目 | 设备类型 |
|------|------|---------|
| `C:\Users\xiezh\Documents\Arduino\greenhouse_lower_node\` | ESP32 下位机检测节点（传感器采集 + 执行器控制） | `esp32` 主节点 |
| `C:\Users\xiezh\Documents\PlatformIO\Projects\tft_screen_1.9\` | ESP32-S3 双屏观测站上位机（TFT + OLED） | `esp32s3_monitor` |
| `D:\Project\esp32cam-upload\` | ESP32-CAM 病虫害诊断上传固件 | `esp32cam` |
| `D:\Project\my_model\` | 病虫害 ResNet 图像分类模型（训练 / 推理） | 后端 AI 模型配套 |

---

## 二、各项目详情

### 1. ESP32 下位机检测节点
- **位置**：`C:\Users\xiezh\Documents\Arduino\greenhouse_lower_node\`
- **工程形式**：Arduino IDE 工程，单文件 `greenhouse_lower_node.ino`
- **板型**：ESP32 Dev Module（ESP32 Classic）
- **功能**：传感器采集 + 执行器控制，纯命令驱动，无本地自动控制（规则引擎在后端）
- **传感器**：
  - DHT11 温湿度（GPIO19）
  - 光敏电阻光照（GPIO34，ADC1_CH6，伪 lux 映射）
  - 土壤湿度（GPIO35，ADC1_CH7）
  - PH4502C 土壤 pH（GPIO36，ADC1_CH0/VP）
  - CO₂ 为模拟值（传感器已损坏，生成 400–600 ppm 波动）
- **执行器**：
  - 水泵继电器（GPIO25，开/关）
  - 风扇 PWM（GPIO13，25kHz / 8 位，0–100%）
  - WS2812 灯带（GPIO4，12 颗灯珠，0–100%）
- **UART 与上位机通信**（Serial1，115200，8N1，交叉连接）：
  - 下位机 RX = GPIO27 ← 上位机 TX（GPIO1）
  - 下位机 TX = GPIO26 → 上位机 RX（GPIO6）
  - 上行：每 2 秒发送一行 JSON
    `{"T":28.5,"H":62.0,"M":45.0,"L":35000,"P":6.8,"C":500}\n`
    （T=空气温度℃、H=空气湿度%、M=土壤湿度%、L=光照 lux、P=土壤 pH、C=CO₂ ppm）
  - 下行：文本命令 `<设备>:<值>\n`
    `P:0/P:1` 水泵关/开、`F:0~100` 风扇、`L:0~100` 灯带亮度、`X:0` 全部关闭
- **依赖库**：`DHT sensor library`（Adafruit）、`Adafruit NeoPixel`
- **编译烧录**：Arduino IDE 选择 ESP32 Dev Module，直接上传
- **对接关系**：不直接连后端，数据经 `tft_screen_1.9` 上位机转发到 MQTT。

### 2. ESP32-S3 双屏观测站上位机
- **位置**：`C:\Users\xiezh\Documents\PlatformIO\Projects\tft_screen_1.9\`
- **设备**：ESP32-S3-DevKitC（ESP32-S3-WROOM-1），对应 `d:\IoT` 的 `esp32s3_monitor`
- **框架**：PlatformIO + Arduino（`board = esp32-s3-devkitc-1`）
- **显示**：
  - ST7789 1.9" TFT（170×320 竖屏）—「科学观测仪」主屏，6 项指标（空气温度/湿度、光照、土壤湿度、CO₂、pH），2s 局部无闪烁刷新，Font4 26px 大字体
  - 128×64 OLED（I2C）— 室外天气对照副屏（NTP 时间 + 和风天气 API）
- **外设**：IR 红外遥控（NEC，GPIO15）→ UART 控制下位机执行器；UART 双向通信（TX=1 / RX=6，115200）
- **MQTT 云端**：PubSubClient；上报 `greenhouse/sensor/data`（每 5s）+ 心跳 `greenhouse/device/status`（每 30s + LWT 告警）；订阅 `greenhouse/device/control` 接收控制命令（按 `component_type` 映射到 UART 命令 P/L/F）
- **数据源切换**：优先使用下位机 UART 真实数据，超过 15s 无数据自动回退模拟数据
- **源码模块**（`src/`）：`main.cpp`、`tft_dashboard.*`、`weather.*`、`oled_display.*`、`ir_control.*`、`uart_uplink.*`、`uart_downlink.*`、`cloud_comm.*`、`chinese_labels.h`（自动生成）、`wifi_config.h`（含凭据，已 gitignore）
- **中文标签生成**：`python generate_labels.py` → 生成 `chinese_labels.h` RGB565 位图
- **文档**：`README.md`、`AGENTS.md`、`CLAUDE.md`（含详细接线、UART/MQTT 协议、已知坑）
- **编译烧录**：`pio run --target upload`；**注意** ESP32-S3-DevKitC 需插 UART 口，烧录前先 Ctrl+C 关闭串口监视器。

### 3. ESP32-CAM 病虫害诊断上传固件
- **位置**：`D:\Project\esp32cam-upload\`
- **设备**：AI-Thinker ESP32-CAM（带 PSRAM），板载 OV2640 摄像头 + GPIO4 闪光灯
- **框架**：PlatformIO + Arduino（`board = esp32cam`）
- **入口**：`src/main.cpp`
- **核心功能**：复位/上电后自动拍照（640×480 JPEG，quality=12）→ 闪光灯预亮 → 流式 multipart 上传 → HTTP POST 到后端 `/api/v1/pest-diagnoses/upload`（Bearer 设备令牌鉴权）→ 串口打印诊断结果。上传失败重试 3 次（间隔 3s）。
- **关键依赖**：`esp_camera`、`WiFi`、`HTTPClient`、`ArduinoJson`
- **配置位置**：`main.cpp` 顶部（ssid / 后端 IP / `deviceToken`）
- **编译烧录**：`pio run --target upload`；串口 `pio device monitor -b 115200`

### 4. 病虫害图像分类模型（训练 / 推理）
- **位置**：`D:\Project\my_model\`
- **用途**：与后端病虫害诊断配套。后端 `d:\IoT` 的 `pest_diagnosis_service` 加载训练产物做真实 ResNet 推理。
- **框架**：Python + PyTorch（`.venv` 虚拟环境）
- **脚本**：
  - `train.py` — 训练（ResNet18，两阶段：冻结主干 5 epoch + 全微调，5 分类）
  - `predict.py` — 推理（多尺度 + 水平翻转 TTA，6 次平均），`load_model()` 支持 resnet18 / resnet50
  - `check_dataset.py` / `test_gpu.py` / `evaluate.py`
- **数据集**：`dataset/PlantVillage/`（Strawberry/Tomato × healthy/blight 5 类）
- **5 类标签**：Strawberry—Leaf scorch / healthy；Tomato—Early blight / Late blight / healthy
- **产物**：`models/best_model.pth`（约 94.4 MB，实测）
- **与后端的关系**：后端 `d:\IoT\app\services\pest_diagnosis_service.py` 默认加载 `d:\IoT\models\pest_model.pth`（可由 `PEST_MODEL_PATH` 覆盖），该文件与本项目产物**大小完全一致**（均为 94,392,273 字节），应为同一次训练的拷贝。checkpoint 需包含 `state_dict` + `classes`，`model_name` 缺省时后端按 `resnet50` 处理。

---

## 三、与 d:\IoT 后端的对接点

| 项目 | 通信方式 | 对接点 |
|------|---------|--------|
| greenhouse_lower_node | UART → 上位机 | 经 `tft_screen_1.9` 转发，不直接连后端 |
| tft_screen_1.9（esp32s3_monitor） | MQTT | `greenhouse/sensor/data`、`greenhouse/device/control`、`greenhouse/device/status` |
| esp32cam-upload | HTTP POST | `/api/v1/pest-diagnoses/upload`，Bearer 设备令牌（esp32cam 类型） |
| my_model | 离线训练/推理 | 训练产物 `best_model.pth` 对应后端默认加载的 `d:\IoT\models\pest_model.pth` |

> 通用约定（详见 `d:\IoT` 根目录 AGENTS.md / CLAUDE.md）：设备令牌由「设备令牌管理」创建（每小组每种设备一个，绑 `group_id`）；上位机需在 `wifi_config.h` 中配置 `NODE_ID`。
