// panda_actions.h
// 熊猫花花 —— 动作引擎 (ESP-IDF / C++)  *零依赖小智, 裸测 Demo 也能用*
// ----------------------------------------------------------------------------
// 设计要点:
//   * Enqueue(): 非阻塞投递, 给 MCP 回调用(回调里只入队、立即返回, 不卡对话);
//   * RunBlocking(): 同步播放, 给裸测 Demo / 串口命令用(在调用线程里跑完);
//   * 关键帧动画统一在这里, MCP 路径和裸测路径共用同一套动作。
#pragma once

#include "panda_servos.h"
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"

namespace panda {

enum class ActionId {
    Blink,
    Nod,
    ShakeHead,
    Wave,
    LookLeft,
    LookRight,
    LookFront,
    Sit,
    EmotionHappy,
    EmotionSleepy,
    Relax,
};

struct ActionReq {
    ActionId id;
    int      arg;   // 备用参数(如挥手次数)
};

class ActionEngine {
public:
    void AttachBus(ServoBus* bus) { bus_ = bus; }   // 仅绑定舵机(裸测/同步用)
    void Begin(ServoBus* bus);                      // 绑定舵机 + 启动后台播放任务(异步/MCP 用)
    bool Enqueue(ActionId id, int arg = 0);         // 非阻塞: 投递到队列, 后台任务播放
    void RunBlocking(ActionId id, int arg = 0);     // 同步: 在当前线程里直接播放完

private:
    static void TaskTrampoline(void* self);
    void TaskLoop();
    void Play(const ActionReq& r);

    // 具体动作(关键帧序列)
    void DoBlink();
    void DoNod();
    void DoShakeHead();
    void DoWave(int times);
    void DoLook(int yaw_deg);
    void DoSit();
    void DoEmotionHappy();
    void DoEmotionSleepy();

    ServoBus*     bus_   = nullptr;
    QueueHandle_t queue_ = nullptr;
};

}  // namespace panda
