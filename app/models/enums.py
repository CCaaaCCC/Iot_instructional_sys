from enum import Enum


class UserRole(str, Enum):
    admin = "admin"
    teacher = "teacher"
    student = "student"


class ComponentType(str, Enum):
    sensor = "sensor"
    fan = "fan"
    pump = "pump"
    light = "light"


class ComponentStatus(str, Enum):
    on = "on"
    off = "off"
    auto = "auto"


class RuleOperator(str, Enum):
    gt = ">"
    gte = ">="
    lt = "<"
    lte = "<="


class SensorMetric(str, Enum):
    air_temp = "air_temp"
    air_humidity = "air_humidity"
    soil_humidity = "soil_humidity"
    light_intensity = "light_intensity"
    soil_ph = "soil_ph"
    co2 = "co2"


class TaskStatus(str, Enum):
    pending = "pending"
    in_progress = "in_progress"
    done = "done"


class CourseSubject(str, Enum):
    labor = "labor"
    science = "science"


class TaskType(str, Enum):
    observation = "observation"
    experiment = "experiment"
    maintenance = "maintenance"


class ExperimentStatus(str, Enum):
    ongoing = "ongoing"
    completed = "completed"


class ExperimentRole(str, Enum):
    control = "control"
    experimental = "experimental"


class DeviceType(str, Enum):
    esp32 = "esp32"
    esp32cam = "esp32cam"
    esp32s3 = "esp32s3"
    esp32s3_monitor = "esp32s3_monitor"


class DiagnosisResult(str, Enum):
    """ESP32-CAM 视觉诊断结果（5 分类，基于 ResNet50 真实模型推理）。"""

    tomato_healthy = "tomato_healthy"  # 番茄健康
    tomato_early_blight = "tomato_early_blight"  # 番茄早疫病
    tomato_late_blight = "tomato_late_blight"  # 番茄晚疫病
    strawberry_healthy = "strawberry_healthy"  # 草莓健康
    strawberry_leaf_scorch = "strawberry_leaf_scorch"  # 草莓叶焦病
