// panda_mcp_tools.cc —— 把花花动作注册成小智 MCP 工具 (只在 xiaozhi 固件里编译)
#include "panda_mcp_tools.h"
#include "esp_log.h"

// xiaozhi-esp32 提供的 MCP 头文件 (路径以你的工程为准)
#include "mcp_server.h"

namespace panda {

static const char* TAG = "panda_mcp";

// 命名沿用小智风格 self.<module>.<action>; 回调里只 Enqueue, 立即返回(不卡对话)。
void RegisterPandaTools(McpServer& mcp, ActionEngine* engine) {

    mcp.AddTool("self.panda.blink",
        "Make the panda blink its eyes",
        PropertyList(),
        [engine](const PropertyList&) -> ReturnValue {
            engine->Enqueue(ActionId::Blink);
            return true;
        });

    mcp.AddTool("self.panda.nod",
        "Make the panda nod (yes / agree)",
        PropertyList(),
        [engine](const PropertyList&) -> ReturnValue {
            engine->Enqueue(ActionId::Nod);
            return true;
        });

    mcp.AddTool("self.panda.shake_head",
        "Make the panda shake its head (no / disagree)",
        PropertyList(),
        [engine](const PropertyList&) -> ReturnValue {
            engine->Enqueue(ActionId::ShakeHead);
            return true;
        });

    // 带参数: 挥手次数 1~5, 默认 2 (Property 重载见 README 版本差异说明)
    mcp.AddTool("self.panda.wave",
        "Make the panda wave its arm to greet. Optional 'times' (1-5).",
        PropertyList({ Property("times", kPropertyTypeInteger, 2, 1, 5) }),
        [engine](const PropertyList& props) -> ReturnValue {
            int times = props["times"].value<int>();
            engine->Enqueue(ActionId::Wave, times);
            return true;
        });

    // 带字符串参数: 看向 left/right/front
    mcp.AddTool("self.panda.look",
        "Make the panda look toward a direction. 'direction' = left|right|front.",
        PropertyList({ Property("direction", kPropertyTypeString) }),
        [engine](const PropertyList& props) -> ReturnValue {
            std::string d = props["direction"].value<std::string>();
            if (d == "left")       engine->Enqueue(ActionId::LookLeft);
            else if (d == "right") engine->Enqueue(ActionId::LookRight);
            else                   engine->Enqueue(ActionId::LookFront);
            return true;
        });

    // 情绪 -> 复合动作
    mcp.AddTool("self.panda.set_emotion",
        "Express an emotion with eyes/head/arms. 'emotion' = happy|sleepy|calm.",
        PropertyList({ Property("emotion", kPropertyTypeString) }),
        [engine](const PropertyList& props) -> ReturnValue {
            std::string e = props["emotion"].value<std::string>();
            if (e == "happy")       engine->Enqueue(ActionId::EmotionHappy);
            else if (e == "sleepy") engine->Enqueue(ActionId::EmotionSleepy);
            else                    engine->Enqueue(ActionId::Relax);
            return true;
        });

    mcp.AddTool("self.panda.sit",
        "Make the panda sit up",
        PropertyList(),
        [engine](const PropertyList&) -> ReturnValue {
            engine->Enqueue(ActionId::Sit);
            return true;
        });

    ESP_LOGI(TAG, "panda MCP tools registered");
}

}  // namespace panda
