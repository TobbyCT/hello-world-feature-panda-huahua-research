// main.cc —— 熊猫花花 · 舵机裸测 Demo (ESP-IDF / C++)
// ============================================================================
// 不接大模型、不连 Wi-Fi。烧录后打开串口监视器(115200), 直接敲命令让花花做动作:
//
//   blink            眨眼
//   nod              点头
//   shake            摇头
//   wave [次数]      招手(默认2次)        例: wave 3
//   look <dir>       看向 left|right|front 例: look left
//   sit              坐起
//   happy / sleepy   情绪复合动作
//   center           所有舵机回中位(复位)
//   list             打印 关节->通道 映射 与 当前角度
//   cal <ch> <deg>   直接把某通道转到某角度(0~180), 用来找 min/center/max 做标定
//   sweep <ch>       自动来回扫一个通道(50~130), 检查是否卡顿/异响
//   idle <on|off>    待机生命感: 随机眨眼+偶尔转头看(展示用)
//   help             查看所有命令
//
// 标定流程: 用 cal/sweep 找到每个关节真实的 min/center/max, 回填 panda_servos.h 的 kCal。
// ----------------------------------------------------------------------------
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"
#include "driver/i2c_master.h"
#include "esp_console.h"
#include "esp_log.h"
#include "esp_random.h"

#include "panda_servos.h"
#include "panda_actions.h"

// ===== 按你的接线修改 =====
#define PANDA_I2C_PORT   I2C_NUM_0
#define PANDA_SDA_GPIO   GPIO_NUM_1
#define PANDA_SCL_GPIO   GPIO_NUM_2
#define PCA9685_ADDR     0x40

static const char* TAG = "panda_demo";

static panda::ServoBus     g_servo;
static panda::ActionEngine g_engine;     // 裸测只用 RunBlocking, 不启动后台任务
static SemaphoreHandle_t   g_mtx;        // 串行化舵机访问(命令 vs 待机任务)
static volatile bool       g_idle = false;

static inline void Lock()   { xSemaphoreTake(g_mtx, portMAX_DELAY); }
static inline void Unlock() { xSemaphoreGive(g_mtx); }

// 用互斥锁包一层, 同步播放一个动作
static void RunSafe(panda::ActionId id, int arg = 0) {
    Lock();
    g_engine.RunBlocking(id, arg);
    Unlock();
}

// ============================ 命令实现 ============================
static int cmd_blink(int, char**)  { RunSafe(panda::ActionId::Blink);        return 0; }
static int cmd_nod(int, char**)    { RunSafe(panda::ActionId::Nod);          return 0; }
static int cmd_shake(int, char**)  { RunSafe(panda::ActionId::ShakeHead);    return 0; }
static int cmd_sit(int, char**)    { RunSafe(panda::ActionId::Sit);          return 0; }
static int cmd_happy(int, char**)  { RunSafe(panda::ActionId::EmotionHappy); return 0; }
static int cmd_sleepy(int, char**) { RunSafe(panda::ActionId::EmotionSleepy);return 0; }
static int cmd_center(int, char**) { RunSafe(panda::ActionId::Relax);        return 0; }

static int cmd_wave(int argc, char** argv) {
    int times = (argc >= 2) ? atoi(argv[1]) : 2;
    if (times < 1) times = 1; if (times > 5) times = 5;
    RunSafe(panda::ActionId::Wave, times);
    return 0;
}

static int cmd_look(int argc, char** argv) {
    if (argc < 2) { printf("用法: look <left|right|front>\n"); return 1; }
    std::string d = argv[1];
    if (d == "left")       RunSafe(panda::ActionId::LookLeft);
    else if (d == "right") RunSafe(panda::ActionId::LookRight);
    else                   RunSafe(panda::ActionId::LookFront);
    return 0;
}

static int cmd_list(int, char**) {
    static const char* names[panda::JOINT_COUNT] = {
        "EYE_X","EYE_Y","EYELID_TL","EYELID_TR","EYELID_BL","EYELID_BR",
        "HEAD_PITCH","HEAD_YAW","ARM_L","ARM_R","WAIST"};
    printf(" idx  关节        通道  min center max   当前\n");
    for (int i = 0; i < panda::JOINT_COUNT; ++i) {
        const panda::JointCal& c = panda::kCal[i];
        printf(" %2d   %-10s  %3d  %4d %5d %4d  %4d\n",
               i, names[i], c.channel, c.min_deg, c.center_deg, c.max_deg,
               g_servo.CurrentAngle((panda::Joint)i));
    }
    return 0;
}

static int cmd_cal(int argc, char** argv) {
    if (argc < 3) { printf("用法: cal <channel 0-15> <deg 0-180>\n"); return 1; }
    int ch = atoi(argv[1]);
    int deg = atoi(argv[2]);
    Lock();
    g_servo.SetServoAngleRaw((uint8_t)ch, deg);
    Unlock();
    printf("ch %d -> %d deg (记下卡到机械极限前的安全角度, 填入 kCal)\n", ch, deg);
    return 0;
}

static int cmd_sweep(int argc, char** argv) {
    if (argc < 2) { printf("用法: sweep <channel 0-15>\n"); return 1; }
    int ch = atoi(argv[1]);
    printf("扫描 ch %d : 50->130->90 ...\n", ch);
    Lock();
    for (int d = 50; d <= 130; d += 2) { g_servo.SetServoAngleRaw((uint8_t)ch, d); vTaskDelay(pdMS_TO_TICKS(20)); }
    for (int d = 130; d >= 50; d -= 2) { g_servo.SetServoAngleRaw((uint8_t)ch, d); vTaskDelay(pdMS_TO_TICKS(20)); }
    g_servo.SetServoAngleRaw((uint8_t)ch, 90);
    Unlock();
    return 0;
}

static int cmd_idle(int argc, char** argv) {
    if (argc < 2) { printf("用法: idle <on|off>\n"); return 1; }
    g_idle = (strcmp(argv[1], "on") == 0);
    printf("待机生命感: %s\n", g_idle ? "ON" : "OFF");
    return 0;
}

// 待机生命感: 随机眨眼, 偶尔转头看一下
static void IdleTask(void*) {
    for (;;) {
        if (g_idle) {
            if (xSemaphoreTake(g_mtx, 0) == pdTRUE) {     // 拿不到锁说明正在执行命令, 跳过
                g_engine.RunBlocking(panda::ActionId::Blink);
                if ((esp_random() % 3) == 0) {            // 1/3 概率转头看
                    int r = esp_random() % 3;
                    g_engine.RunBlocking(r == 0 ? panda::ActionId::LookLeft :
                                         r == 1 ? panda::ActionId::LookRight :
                                                  panda::ActionId::LookFront);
                }
                xSemaphoreGive(g_mtx);
            }
        }
        vTaskDelay(pdMS_TO_TICKS(2500 + (esp_random() % 3500)));  // 2.5~6s
    }
}

static void RegisterCmd(const char* name, const char* help, esp_console_cmd_func_t fn) {
    esp_console_cmd_t c = {};
    c.command = name;
    c.help    = help;
    c.hint    = nullptr;
    c.func    = fn;
    ESP_ERROR_CHECK(esp_console_cmd_register(&c));
}

extern "C" void app_main(void) {
    // 1) 建 I2C 总线
    i2c_master_bus_config_t bus_cfg = {};
    bus_cfg.i2c_port   = PANDA_I2C_PORT;
    bus_cfg.sda_io_num = PANDA_SDA_GPIO;
    bus_cfg.scl_io_num = PANDA_SCL_GPIO;
    bus_cfg.clk_source = I2C_CLK_SRC_DEFAULT;
    bus_cfg.glitch_ignore_cnt = 7;
    bus_cfg.flags.enable_internal_pullup = true;
    i2c_master_bus_handle_t bus = nullptr;
    ESP_ERROR_CHECK(i2c_new_master_bus(&bus_cfg, &bus));

    // 2) 初始化舵机 + 动作引擎(裸测只绑定, 不起后台任务)
    if (!g_servo.Init(bus, PCA9685_ADDR)) {
        ESP_LOGE(TAG, "PCA9685 init 失败, 检查接线/地址");
    }
    g_engine.AttachBus(&g_servo);
    g_mtx = xSemaphoreCreateMutex();
    xTaskCreate(&IdleTask, "panda_idle", 4096, nullptr, 4, nullptr);

    // 3) 串口 REPL
    esp_console_repl_t* repl = nullptr;
    esp_console_repl_config_t repl_cfg = ESP_CONSOLE_REPL_CONFIG_DEFAULT();
    repl_cfg.prompt = "panda>";
    repl_cfg.max_cmdline_length = 128;
    esp_console_dev_uart_config_t uart_cfg = ESP_CONSOLE_DEV_UART_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_console_new_repl_uart(&uart_cfg, &repl_cfg, &repl));

    RegisterCmd("blink",  "眨眼",                         &cmd_blink);
    RegisterCmd("nod",    "点头",                         &cmd_nod);
    RegisterCmd("shake",  "摇头",                         &cmd_shake);
    RegisterCmd("wave",   "招手 [次数1-5]",               &cmd_wave);
    RegisterCmd("look",   "看向 left|right|front",        &cmd_look);
    RegisterCmd("sit",    "坐起",                         &cmd_sit);
    RegisterCmd("happy",  "开心(眨眼+招手)",              &cmd_happy);
    RegisterCmd("sleepy", "困倦(半闭眼+低头)",            &cmd_sleepy);
    RegisterCmd("center", "所有舵机回中位",               &cmd_center);
    RegisterCmd("list",   "打印关节->通道映射与当前角度", &cmd_list);
    RegisterCmd("cal",    "标定: cal <ch> <deg>",         &cmd_cal);
    RegisterCmd("sweep",  "扫描通道: sweep <ch>",         &cmd_sweep);
    RegisterCmd("idle",   "待机生命感: idle on|off",      &cmd_idle);
    esp_console_register_help_command();

    printf("\n==== 熊猫花花 舵机裸测 Demo ====\n输入 help 查看命令; 先用 list / cal / sweep 标定, 再玩 blink/nod/wave。\n\n");
    ESP_ERROR_CHECK(esp_console_start_repl(repl));
}
