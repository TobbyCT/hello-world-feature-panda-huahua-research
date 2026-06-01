// panda_servos.cc —— PCA9685 舵机控制实现 (ESP-IDF / C++)
#include "panda_servos.h"
#include <algorithm>
#include <cmath>
#include "esp_log.h"

namespace panda {

static const char* TAG = "panda_servo";

// PCA9685 寄存器
static constexpr uint8_t MODE1      = 0x00;
static constexpr uint8_t PRESCALE   = 0xFE;
static constexpr uint8_t LED0_ON_L  = 0x06;

bool ServoBus::Init(i2c_master_bus_handle_t bus, uint8_t addr, float pwm_hz) {
    pwm_hz_ = pwm_hz;
    i2c_device_config_t dev_cfg = {};
    dev_cfg.dev_addr_length = I2C_ADDR_BIT_LEN_7;
    dev_cfg.device_address  = addr;
    dev_cfg.scl_speed_hz    = 400000;
    if (i2c_master_bus_add_device(bus, &dev_cfg, &dev_) != ESP_OK) {
        ESP_LOGE(TAG, "add PCA9685 dev failed");
        return false;
    }
    // 设置 PWM 频率: prescale = round(25MHz / (4096*freq)) - 1
    uint8_t prescale = (uint8_t)std::lround(25000000.0 / (4096.0 * pwm_hz_)) - 1;
    WriteReg(MODE1, 0x10);        // sleep
    WriteReg(PRESCALE, prescale); // set freq
    WriteReg(MODE1, 0x00);        // wake
    vTaskDelay(pdMS_TO_TICKS(5));
    WriteReg(MODE1, 0xA1);        // auto-increment + restart

    for (int i = 0; i < JOINT_COUNT; ++i) cur_deg_[i] = kCal[i].center_deg;
    Relax();
    ESP_LOGI(TAG, "PCA9685 ready, prescale=%d", prescale);
    return true;
}

void ServoBus::WriteReg(uint8_t reg, uint8_t val) {
    uint8_t buf[2] = {reg, val};
    i2c_master_transmit(dev_, buf, sizeof(buf), 50);
}

void ServoBus::SetPwmRaw(uint8_t ch, uint16_t on, uint16_t off) {
    uint8_t reg = LED0_ON_L + 4 * ch;
    uint8_t buf[5] = {reg,
                      (uint8_t)(on & 0xFF), (uint8_t)(on >> 8),
                      (uint8_t)(off & 0xFF), (uint8_t)(off >> 8)};
    i2c_master_transmit(dev_, buf, sizeof(buf), 50);
}

uint16_t ServoBus::UsToTicks(int us) const {
    float ticks = us * pwm_hz_ * 4096.0f / 1000000.0f;       // 脉宽->计数(0..4095)
    return (uint16_t)std::clamp((int)std::lround(ticks), 0, 4095);
}

uint16_t ServoBus::AngleToTicks(Joint j, int deg) const {
    const JointCal& c = kCal[j];
    deg = std::clamp(deg, c.min_deg, c.max_deg);             // 安全限位
    int us = kMinUs + (int)std::lround((kMaxUs - kMinUs) * (deg / 180.0f));
    return UsToTicks(us);
}

void ServoBus::SetAngle(Joint j, int deg) {
    deg = std::clamp(deg, kCal[j].min_deg, kCal[j].max_deg);
    SetPwmRaw(kCal[j].channel, 0, AngleToTicks(j, deg));
    cur_deg_[j] = deg;
}

// 裸通道控制(标定用): 只夹 0~180, 不看关节限位
void ServoBus::SetServoAngleRaw(uint8_t ch, int deg) {
    deg = std::clamp(deg, 0, 180);
    int us = kMinUs + (int)std::lround((kMaxUs - kMinUs) * (deg / 180.0f));
    SetPwmRaw(ch, 0, UsToTicks(us));
}

void ServoBus::SetServoUs(uint8_t ch, int us) {
    us = std::clamp(us, kMinUs, kMaxUs);
    SetPwmRaw(ch, 0, UsToTicks(us));
}

// ease-in-out 缓动, 让动作更像生物而非机械
static float EaseInOut(float t) { return t < 0.5f ? 2*t*t : 1 - std::pow(-2*t + 2, 2) / 2; }

void ServoBus::MoveTo(Joint j, int deg, int ms) {
    int from = cur_deg_[j];
    int to   = std::clamp(deg, kCal[j].min_deg, kCal[j].max_deg);
    const int step_ms = 15;
    int steps = std::max(1, ms / step_ms);
    for (int i = 1; i <= steps; ++i) {
        float t = EaseInOut((float)i / steps);
        SetAngle(j, (int)std::lround(from + (to - from) * t));
        vTaskDelay(pdMS_TO_TICKS(step_ms));
    }
}

void ServoBus::MoveGroup(const Joint* joints, const int* degs, int n, int ms) {
    int from[JOINT_COUNT];
    for (int k = 0; k < n; ++k) from[k] = cur_deg_[joints[k]];
    const int step_ms = 15;
    int steps = std::max(1, ms / step_ms);
    for (int i = 1; i <= steps; ++i) {
        float t = EaseInOut((float)i / steps);
        for (int k = 0; k < n; ++k) {
            int to = std::clamp(degs[k], kCal[joints[k]].min_deg, kCal[joints[k]].max_deg);
            SetAngle(joints[k], (int)std::lround(from[k] + (to - from[k]) * t));
        }
        vTaskDelay(pdMS_TO_TICKS(step_ms));
    }
}

void ServoBus::Relax() {
    for (int i = 0; i < JOINT_COUNT; ++i)
        SetAngle((Joint)i, kCal[i].center_deg);
}

}  // namespace panda
