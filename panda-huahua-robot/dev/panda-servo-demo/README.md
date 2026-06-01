# 熊猫花花 · 舵机裸测 Demo（当晚就能跑通动作）

**目标**：拿到舵机/PCA9685 的当晚，不接大模型、不连 Wi-Fi，用串口直接敲命令把
`blink / nod / wave / look ...` 调通并标定每个关节角度。这是 W2「对话→动作」联调前的硬件 bring-up。

## 1. 硬件接线
| 连接 | 说明 |
|---|---|
| ESP32-S3 `GPIO1(SDA) / GPIO2(SCL)` ↔ PCA9685 `SDA/SCL` | I2C，引脚可在 `main/main.cc` 顶部 `#define` 改 |
| ESP32-S3 `GND` ↔ PCA9685 `GND` ↔ 舵机电源 `GND` | **三者必须共地** |
| 独立 5V 电源 ↔ PCA9685 `V+`（舵机供电） | **别用 ESP32 的 3.3V/USB 直接供舵机**，会复位/烧板 |
| PCA9685 `VCC(逻辑)` ↔ ESP32 `3V3` | 仅芯片逻辑供电 |
| 舵机 → PCA9685 通道 0~10 | 对应 `panda_servos.h` 的 `Joint` 枚举 |

> PCA9685 默认 I2C 地址 `0x40`；多块板叠加时改地址跳线。

## 2. 编译 / 烧录（ESP-IDF 5.x）
```bash
# 已装好 ESP-IDF 并 . ./export.sh
cd dev/panda-servo-demo
idf.py set-target esp32s3
idf.py build flash monitor      # 退出监视器: Ctrl+]
```
> 若 `REQUIRES` 里的 `esp_driver_i2c` 在你的 IDF 版本不存在，删掉它只留 `driver console` 即可；
> 若相对路径 `../../xiaozhi-mcp/*.cc` 在你的环境报找不到，把那两个 `.cc/.h` 复制到本 `main/` 下，并把 SRCS 改成本地文件名。

## 3. 使用（串口监视器里输入）
```
panda> help            # 所有命令
panda> list            # 看 关节->通道 映射 和 当前角度
panda> sweep 9         # 让通道9(右前肢)来回扫, 确认转动顺滑、不卡、不异响
panda> cal 9 40        # 把通道9 转到 40°, 逐步试出安全的 min/center/max
panda> blink           # 眨眼
panda> nod             # 点头
panda> wave 3          # 招手3次
panda> look left       # 看向左
panda> happy           # 开心(眨眼+招手)
panda> idle on         # 待机生命感: 随机眨眼+偶尔转头(演示用)
panda> center          # 复位
```

## 4. 标定流程（重要）
舵机装好后**先标定再玩动作**，否则可能堵转/夹手：
1. `sweep <ch>` 确认每个通道机械上自由、无干涉。
2. `cal <ch> <deg>` 从中位(90)开始, 小步加/减, 找到**机械极限前的安全角度**作为 `min/max`，自然姿态作为 `center`。
3. 把测得的值回填 `../xiaozhi-mcp/panda_servos.h` 的 `kCal[]`。
4. 重新 `idf.py build flash`，此时 `blink/nod/wave` 的关键帧就贴合你的实物了。

## 5. 调通后 → 接大模型（W2 的下一步）
本 Demo 验证的 `panda_servos.* + panda_actions.*` 与正式固件**完全同一套**。调通后只需：
1. 把 `panda_servos.* / panda_actions.* / panda_mcp_tools.*` 三组文件加入你的 **xiaozhi-esp32 自定义板子**组件；
2. 在板子里 `g_engine.Begin(&g_servo)`（启动后台任务）+ 在 `InitializeTools()` 里 `RegisterPandaTools(mcp, &g_engine)`；
3. 配置花花人设 Prompt（见 `../xiaozhi-mcp/README.md`）。
这样大模型说「招招手」就会调用 `self.panda.wave` —— 与本 Demo 跑的是同一个动作。

## 文件
- `main/main.cc` —— 串口 REPL + 待机生命感 + 标定命令
- `main/CMakeLists.txt` —— 复用 `../../xiaozhi-mcp/` 的 `panda_servos.cc / panda_actions.cc`
- `CMakeLists.txt` / `sdkconfig.defaults` —— 工程入口与默认配置
