// panda_servos.h
// 熊猫花花 —— PCA9685 多路舵机控制 (ESP-IDF / C++)
// ----------------------------------------------------------------------------
// 零依赖小智, 裸测 Demo 与正式固件都可复用。
// 适配 ESP-IDF 5.x 的 i2c_master 新驱动。标 TODO 处需按你的接线/舵机标定。
#pragma once

#include <cstdint>
#include "driver/i2c_master.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

namespace panda {

// ===== 1) 关节 -> PCA9685 通道映射 (按你的实际接线修改) =====
enum Joint : uint8_t {
    // 仿生眼 (Will Cogley 双眼机构, 共 6 路)
    EYE_X        = 0,   // 双眼左右(共用)
    EYE_Y        = 1,   // 双眼上下(共用)
    EYELID_TL    = 2,   // 左上眼皮
    EYELID_TR    = 3,   // 右上眼皮
    EYELID_BL    = 4,   // 左下眼皮
    EYELID_BR    = 5,   // 右下眼皮
    // 头 / 四肢 / 腰
    HEAD_PITCH   = 6,   // 头部俯仰(点头)
    HEAD_YAW     = 7,   // 头部左右(摇头/看向)
    ARM_L        = 8,   // 左前肢
    ARM_R        = 9,   // 右前肢
    WAIST        = 10,  // 腰部(坐起/前倾)
    JOINT_COUNT  = 11
};

// ===== 2) 每个关节的安全角度范围与中位 (防夹手/防堵转, 务必按实物标定) =====
struct JointCal {
    uint8_t channel;
    int min_deg;     // 机械下限
    int max_deg;     // 机械上限
    int center_deg;  // 自然中位/复位姿态
};

class ServoBus {
public:
    // 用已建好的 i2c master bus 初始化
    bool Init(i2c_master_bus_handle_t bus, uint8_t addr = 0x40, float pwm_hz = 50.0f);

    // 按"关节"控制(带安全限位)——业务/动作层用这个
    void SetAngle(Joint j, int deg);
    void MoveTo(Joint j, int deg, int ms);                              // 单关节缓动
    void MoveGroup(const Joint* joints, const int* degs, int n, int ms); // 多关节同步缓动
    void Relax();                                                       // 全部回中位
    int  CurrentAngle(Joint j) const { return cur_deg_[j]; }

    // —— 标定/裸测用: 直接按"通道+角度/脉宽"驱动, 不做关节级限位(只夹 0~180) ——
    void SetServoAngleRaw(uint8_t ch, int deg);
    void SetServoUs(uint8_t ch, int us);

private:
    void SetPwmRaw(uint8_t ch, uint16_t on, uint16_t off);
    void WriteReg(uint8_t reg, uint8_t val);
    uint16_t UsToTicks(int us) const;
    uint16_t AngleToTicks(Joint j, int deg) const;

    i2c_master_dev_handle_t dev_ = nullptr;
    int cur_deg_[JOINT_COUNT];

    // 舵机脉宽 (us): 多数 9g/MG90S 为 500~2500us 对应 0~180°, 按你的舵机调
    static constexpr int kMinUs = 500;
    static constexpr int kMaxUs = 2500;
    float pwm_hz_ = 50.0f;
};

// 全局标定表 (TODO: 用 Demo 的 cal/sweep 命令逐项标定后回填这里)
inline const JointCal kCal[JOINT_COUNT] = {
    /* EYE_X     */ {EYE_X,      60, 120, 90},
    /* EYE_Y     */ {EYE_Y,      60, 120, 90},
    /* EYELID_TL */ {EYELID_TL,  20, 110, 30},   // 30=睁, 110=闭(示意)
    /* EYELID_TR */ {EYELID_TR,  20, 110, 30},
    /* EYELID_BL */ {EYELID_BL,  70, 160, 150},
    /* EYELID_BR */ {EYELID_BR,  70, 160, 150},
    /* HEAD_PITCH*/ {HEAD_PITCH, 60, 120, 90},
    /* HEAD_YAW  */ {HEAD_YAW,   50, 130, 90},
    /* ARM_L     */ {ARM_L,      30, 150, 40},
    /* ARM_R     */ {ARM_R,      30, 150, 40},
    /* WAIST     */ {WAIST,      70, 120, 90},
};

}  // namespace panda
