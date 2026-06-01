// panda_mcp_tools.h
// 把花花动作注册成小智 MCP 工具。*只在 xiaozhi-esp32 固件里编译*(依赖 mcp_server.h)。
// 裸测 Demo 不要编译本文件。
#pragma once

#include "panda_actions.h"

class McpServer;  // 来自 xiaozhi-esp32

namespace panda {

// 在板子的 InitializeTools() 里调用; engine 需已 Begin()(后台任务已启动)
void RegisterPandaTools(McpServer& mcp, ActionEngine* engine);

}  // namespace panda
