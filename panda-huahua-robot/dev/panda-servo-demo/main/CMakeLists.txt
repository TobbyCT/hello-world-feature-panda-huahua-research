# 复用 ../../xiaozhi-mcp/ 下的舵机驱动与动作引擎(单一真源, 不复制)
# 注意: 不要把 panda_mcp_tools.cc 加进来——那个依赖小智的 mcp_server.h。
idf_component_register(
    SRCS
        "main.cc"
        "../../xiaozhi-mcp/panda_servos.cc"
        "../../xiaozhi-mcp/panda_actions.cc"
    INCLUDE_DIRS
        "."
        "../../xiaozhi-mcp"
    REQUIRES
        driver
        console
)
