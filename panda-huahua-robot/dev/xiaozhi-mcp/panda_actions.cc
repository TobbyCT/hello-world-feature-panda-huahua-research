// panda_actions.cc —— 动作引擎实现 (ESP-IDF / C++)  *零依赖小智*
#include "panda_actions.h"
#include "esp_log.h"

namespace panda {

static const char* TAG = "panda_act";

// ============================ 引擎调度 ============================
void ActionEngine::Begin(ServoBus* bus) {
    AttachBus(bus);
    queue_ = xQueueCreate(8, sizeof(ActionReq));
    xTaskCreate(&ActionEngine::TaskTrampoline, "panda_act", 4096, this, 5, nullptr);
}

bool ActionEngine::Enqueue(ActionId id, int arg) {
    if (!queue_) return false;
    ActionReq r{id, arg};
    // 非阻塞投递; 队列满则丢弃(避免动作堆积导致花花"抽搐")
    return xQueueSend(queue_, &r, 0) == pdTRUE;
}

void ActionEngine::RunBlocking(ActionId id, int arg) {
    Play({id, arg});   // 直接在调用线程里跑完(裸测/串口命令用)
}

void ActionEngine::TaskTrampoline(void* self) {
    static_cast<ActionEngine*>(self)->TaskLoop();
}

void ActionEngine::TaskLoop() {
    ActionReq r;
    for (;;) {
        if (xQueueReceive(queue_, &r, portMAX_DELAY) == pdTRUE) {
            Play(r);
        }
    }
}

void ActionEngine::Play(const ActionReq& r) {
    if (!bus_) return;
    switch (r.id) {
        case ActionId::Blink:         DoBlink(); break;
        case ActionId::Nod:           DoNod(); break;
        case ActionId::ShakeHead:     DoShakeHead(); break;
        case ActionId::Wave:          DoWave(r.arg > 0 ? r.arg : 2); break;
        case ActionId::LookLeft:      DoLook(kCal[HEAD_YAW].max_deg); break;
        case ActionId::LookRight:     DoLook(kCal[HEAD_YAW].min_deg); break;
        case ActionId::LookFront:     DoLook(kCal[HEAD_YAW].center_deg); break;
        case ActionId::Sit:           DoSit(); break;
        case ActionId::EmotionHappy:  DoEmotionHappy(); break;
        case ActionId::EmotionSleepy: DoEmotionSleepy(); break;
        case ActionId::Relax:         bus_->Relax(); break;
    }
}

// ---- 眨眼: 上下眼皮合上再睁开 ----
void ActionEngine::DoBlink() {
    const Joint lids[4] = {EYELID_TL, EYELID_TR, EYELID_BL, EYELID_BR};
    const int closed[4] = {kCal[EYELID_TL].max_deg, kCal[EYELID_TR].max_deg,
                           kCal[EYELID_BL].min_deg, kCal[EYELID_BR].min_deg};
    const int open[4]   = {kCal[EYELID_TL].center_deg, kCal[EYELID_TR].center_deg,
                           kCal[EYELID_BL].center_deg, kCal[EYELID_BR].center_deg};
    bus_->MoveGroup(lids, closed, 4, 90);
    vTaskDelay(pdMS_TO_TICKS(60));
    bus_->MoveGroup(lids, open, 4, 110);
}

// ---- 点头 ----
void ActionEngine::DoNod() {
    int c = kCal[HEAD_PITCH].center_deg;
    for (int i = 0; i < 2; ++i) {
        bus_->MoveTo(HEAD_PITCH, kCal[HEAD_PITCH].max_deg, 220);
        bus_->MoveTo(HEAD_PITCH, c, 220);
    }
}

// ---- 摇头 ----
void ActionEngine::DoShakeHead() {
    int c = kCal[HEAD_YAW].center_deg;
    for (int i = 0; i < 2; ++i) {
        bus_->MoveTo(HEAD_YAW, kCal[HEAD_YAW].min_deg, 200);
        bus_->MoveTo(HEAD_YAW, kCal[HEAD_YAW].max_deg, 260);
    }
    bus_->MoveTo(HEAD_YAW, c, 200);
}

// ---- 招手/挥手 (抬起前肢来回摆) ----
void ActionEngine::DoWave(int times) {
    bus_->MoveTo(ARM_R, kCal[ARM_R].max_deg, 280);     // 抬手
    for (int i = 0; i < times; ++i) {
        bus_->MoveTo(ARM_R, kCal[ARM_R].max_deg - 35, 180);
        bus_->MoveTo(ARM_R, kCal[ARM_R].max_deg, 180);
    }
    bus_->MoveTo(ARM_R, kCal[ARM_R].center_deg, 300);  // 放下
}

// ---- 看向某个方向(头+眼一起) ----
void ActionEngine::DoLook(int yaw_deg) {
    const Joint js[2] = {HEAD_YAW, EYE_X};
    int eye = kCal[EYE_X].center_deg + (yaw_deg - kCal[HEAD_YAW].center_deg) / 2;
    const int tg[2] = {yaw_deg, eye};
    bus_->MoveGroup(js, tg, 2, 350);
}

// ---- 坐起(腰部抬起 + 抬头) ----
void ActionEngine::DoSit() {
    const Joint js[2] = {WAIST, HEAD_PITCH};
    const int tg[2] = {kCal[WAIST].min_deg, kCal[HEAD_PITCH].min_deg};
    bus_->MoveGroup(js, tg, 2, 600);
}

// ---- 开心: 眨眼 + 招手 ----
void ActionEngine::DoEmotionHappy() {
    DoBlink();
    DoWave(2);
}

// ---- 困倦: 眼皮半闭 + 低头 ----
void ActionEngine::DoEmotionSleepy() {
    const Joint lids[2] = {EYELID_TL, EYELID_TR};
    int half[2] = {(kCal[EYELID_TL].center_deg + kCal[EYELID_TL].max_deg) / 2,
                   (kCal[EYELID_TR].center_deg + kCal[EYELID_TR].max_deg) / 2};
    bus_->MoveGroup(lids, half, 2, 500);
    bus_->MoveTo(HEAD_PITCH, kCal[HEAD_PITCH].max_deg, 600);
}

}  // namespace panda
