# 熊猫花花 · 小智 MCP 动作骨架（wave / blink / nod ...）

把这套骨架塞进 [78/xiaozhi-esp32](https://github.com/78/xiaozhi-esp32) 的**自定义板子**里，
大模型在对话中就能调用 `self.panda.wave / blink / nod / look / set_emotion / sit` 让花花做动作。

## 文件
| 文件 | 作用 | 谁编译 |
|---|---|---|
| `panda_servos.h/.cc` | PCA9685 16 路舵机驱动 + 关节通道映射 + 角度限位 + ease 缓动 | 裸测 Demo + 固件 |
| `panda_actions.h/.cc` | 动作引擎(`Enqueue` 异步 / `RunBlocking` 同步) + 关键帧动画 | 裸测 Demo + 固件 |
| `panda_mcp_tools.h/.cc` | **MCP 工具注册** `RegisterPandaTools()`（依赖 `mcp_server.h`） | **仅固件** |

> 设计上把 MCP 注册单独拆到 `panda_mcp_tools.*`，因此 `panda_servos.* + panda_actions.*` **零依赖小智**，
> 可被 `../panda-servo-demo/`(舵机裸测 Demo) 直接复用。**裸测 Demo 不要编译 `panda_mcp_tools.cc`。**
>
> 这是**可直接套用的骨架**，不是成品：关节角度(`kCal`)、I2C 引脚、舵机脉宽都需按你的实物标定。
>
> 👉 **先去 `../panda-servo-demo/` 用串口把动作调通+标定**，再回到这里接大模型。

## 1. 硬件接线
- PCA9685 ←I2C→ ESP32-S3（如 `SDA=GPIO1, SCL=GPIO2`，按你的板子改）。
- PCA9685 V+ 接**独立 5V 舵机供电**（别用 ESP32 的 3.3V/USB 直供舵机），共地。
- 舵机插到 PCA9685 通道，对应 `panda_servos.h` 里的 `Joint` 枚举（眼 6 路 + 头/臂/腰 5 路）。

## 2. 集成到小智自定义板子（关键 3 步）
在你的板子类（继承 `WifiBoard`/`Board`，参考 `boards/` 下任意一块板）里：

```cpp
#include "panda_servos.h"
#include "panda_actions.h"
#include "panda_mcp_tools.h"

class PandaBoard : public WifiBoard {
private:
    i2c_master_bus_handle_t i2c_bus_;   // 多数板子已有一条 i2c 总线, 复用即可
    panda::ServoBus    servo_;
    panda::ActionEngine engine_;

    void InitPandaServos() {
        // 若板子还没建 i2c bus, 这里建一条 (引脚按实物)
        i2c_master_bus_config_t cfg = {};
        cfg.i2c_port = I2C_NUM_0;
        cfg.sda_io_num = GPIO_NUM_1;
        cfg.scl_io_num = GPIO_NUM_2;
        cfg.clk_source = I2C_CLK_SRC_DEFAULT;
        cfg.flags.enable_internal_pullup = true;
        i2c_new_master_bus(&cfg, &i2c_bus_);

        servo_.Init(i2c_bus_, /*addr=*/0x40);
        engine_.Begin(&servo_);
    }

public:
    PandaBoard() { InitPandaServos(); }

    // 小智会在启动时调用板子的 InitializeTools() 注册 MCP 工具
    virtual void InitializeTools() override {
        auto& mcp = McpServer::GetInstance();
        // (可选) mcp.AddCommonTools();  // 若基类没加, 保留内置工具
        engine_.Begin(&servo_);                    // 启动后台动作任务(异步播放)
        panda::RegisterPandaTools(mcp, &engine_);  // ← 注册花花动作
    }
};
```

CMake：把 `panda_servos.cc / panda_actions.cc / panda_mcp_tools.cc` 三个都加入该板子组件的 `SRCS`（`idf_component_register`）。

## 3. 让大模型"会用"这些动作（人设 Prompt）
在小智后端/角色设定里加一句，引导模型主动调用工具：

> 你是憨态可掬的大熊猫"花花"。表达情绪时请调用动作工具：打招呼用 `self.panda.wave`，
> 认同/开心用 `self.panda.nod` 或 `self.panda.set_emotion(happy)`，被叫到名字先 `self.panda.look(front)` 看向对方再回答；
> 每次回答尽量配 1 个自然的小动作，不要频繁重复。

## 4. 自测（不接大模型也能测）
用 MCP 的 `tools/call` 直接触发（WebSocket/MQTT 通道，见仓库 `docs/mcp-protocol.md`）：

```json
{ "jsonrpc":"2.0","method":"tools/call",
  "params": { "name":"self.panda.wave", "arguments": { "times": 3 } }, "id": 1 }
```

```json
{ "jsonrpc":"2.0","method":"tools/call",
  "params": { "name":"self.panda.look", "arguments": { "direction":"left" } }, "id": 2 }
```

## ⚠️ 版本差异注意（务必核对）
不同小智/ESP-IDF 版本的 API 略有出入，编译前对照你本地源码改：
1. **`Property` 构造重载**：本骨架用了 `Property("times", kPropertyTypeInteger, 2, 1, 5)`（名,类型,默认,最小,最大）。
   官方文档示例是 `Property("r", kPropertyTypeInteger, 0, 255)`（名,类型,最小,最大，无默认）。
   请打开你工程里的 `mcp_server.h` / `property.h` 确认实际重载，必要时去掉默认值参数。
2. **I2C 驱动**：本骨架用 ESP-IDF 5.x 新 `i2c_master_*`。若你的板子用旧 `driver/i2c.h`，把 `panda_servos.cc` 的 I2C 部分换成旧 API。
3. **`AddCommonTools`**：若基类已调用，别重复加内置工具，只调 `RegisterPandaTools`。

## 备注
- 动作引擎用独立 FreeRTOS 任务 + 队列，**MCP 回调只入队、立即返回**，不会卡住对话。
- 队列满时丢弃新动作，避免堆积导致"抽搐"。
- 复杂步态/行走不在此骨架内（按产品决策为选配）。
- 开源件商用授权（小智 / Will Cogley 眼机构等）请在量产前逐一核对。
