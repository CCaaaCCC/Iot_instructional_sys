from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    PROJECT_NAME: str = "Smart Greenhouse Admin API"
    API_V1_STR: str = "/api/v1"
    DATABASE_URL: str = "mysql+pymysql://root:CHANGE_ME@localhost:3306/greenhouse?charset=utf8mb4"
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    CORS_ORIGINS: str = "*"
    LOG_LEVEL: str = "INFO"
    AUTO_CREATE_DB: bool = True
    INIT_ADMIN_USERNAME: str = "admin"
    INIT_ADMIN_PASSWORD: str = "changeme_in_production"
    INIT_SAMPLE_DATA: bool = True
    # MQTT
    MQTT_BROKER_HOST: str = "localhost"
    MQTT_BROKER_PORT: int = 1883
    MQTT_CLIENT_ID: str = "greenhouse-backend"
    MQTT_TOPIC_SENSOR_DATA: str = "greenhouse/sensor/data"
    MQTT_TOPIC_DEVICE_STATUS: str = "greenhouse/device/status"
    MQTT_TOPIC_DEVICE_CONTROL: str = "greenhouse/device/control"
    # AI / DeepSeek
    DEEPSEEK_API_KEY: str = ""  # 空=未配置，AI 接口返回 503
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL_CHAT: str = "deepseek-chat"
    DEEPSEEK_MODEL_REASONER: str = "deepseek-reasoner"
    AI_DAILY_QUOTA: int = 50  # 每用户每日调用上限（chat+reasoner 合计）
    AI_CONTEXT_WINDOW: int = 10  # 注入历史消息条数（偶数=完整轮次）
    AI_SESSION_TITLE_MAXLEN: int = 30  # 会话标题自动截断长度
    AI_REQUEST_TIMEOUT: int = 60  # DeepSeek API 请求超时秒数
    # MCP Bridge (小智 AI)
    MCP_ENDPOINT: str = ""  # 小智 MCP WebSocket 接入点，空=未配置
    DEVICE_TOKEN: str = ""  # esp32s3 设备 token，用于本地 API 鉴权
    LOCAL_API_BASE: str = "http://127.0.0.1:8001"  # 本地后端地址


settings = Settings()
