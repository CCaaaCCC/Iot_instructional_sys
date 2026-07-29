"""
迁移脚本：给 device_tokens.device_type ENUM 列添加 'esp32s3_monitor' 值。

背景：SQLAlchemy 的 Mapped[DeviceType] 会创建 MySQL ENUM 列，但
Base.metadata.create_all() 只创建不存在的表，不会修改已有表的 ENUM 定义。
新增枚举值后必须手动 ALTER TABLE。

用法：python migrate_add_esp32s3_monitor.py
"""
from sqlalchemy import text

from app.db.session import engine


def main():
    # 查看当前 ENUM 定义
    with engine.connect() as conn:
        result = conn.execute(text(
            "SELECT COLUMN_TYPE FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() "
            "AND TABLE_NAME = 'device_tokens' AND COLUMN_NAME = 'device_type'"
        ))
        current_type = result.scalar()
        print(f"当前 device_type 列类型: {current_type}")

        if "esp32s3_monitor" in (current_type or ""):
            print("✅ 已包含 esp32s3_monitor，无需迁移")
            return

        # 执行 ALTER
        new_type = "ENUM('esp32','esp32cam','esp32s3','esp32s3_monitor') NOT NULL"
        sql = text(
            f"ALTER TABLE device_tokens MODIFY COLUMN device_type {new_type}"
        )
        conn.execute(sql)
        conn.commit()
        print(f"✅ 已修改为: {new_type}")

        # 验证
        result = conn.execute(text(
            "SELECT COLUMN_TYPE FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() "
            "AND TABLE_NAME = 'device_tokens' AND COLUMN_NAME = 'device_type'"
        ))
        print(f"迁移后类型: {result.scalar()}")


if __name__ == "__main__":
    main()
