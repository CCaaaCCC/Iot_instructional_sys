from enum import Enum


class UserRole(str, Enum):
    admin = "admin"
    teacher = "teacher"
    operator = "operator"
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
    soil_temp = "soil_temp"
    soil_humidity = "soil_humidity"
    light_intensity = "light_intensity"
    soil_ph = "soil_ph"


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


class DiagnosisResult(str, Enum):
    """ESP32-CAM 视觉诊断结果（6 分类 mock AI）。"""

    tomato_healthy = "tomato_healthy"  # 番茄健康
    tomato_early_blight = "tomato_early_blight"  # 番茄早疫病
    tomato_late_blight = "tomato_late_blight"  # 番茄晚疫病
    cucumber_healthy = "cucumber_healthy"  # 黄瓜健康
    cucumber_powdery_mildew = "cucumber_powdery_mildew"  # 黄瓜白粉病
    cucumber_anthracnose = "cucumber_anthracnose"  # 黄瓜炭疽病
