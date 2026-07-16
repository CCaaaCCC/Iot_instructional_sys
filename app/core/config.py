from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    PROJECT_NAME: str = "Smart Greenhouse Admin API"
    API_V1_STR: str = "/api/v1"
    DATABASE_URL: str = "sqlite:///./data/greenhouse.db"
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


settings = Settings()
