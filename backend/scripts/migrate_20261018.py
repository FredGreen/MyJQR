# -*- coding: utf-8 -*-
"""非破坏性迁移：新表 create_all + 已有表幂等加列。可重复执行，不动任何数据。

用法（backend/ 目录下，需 MySQL 已启动）：
    ../.venv/Scripts/python.exe -X utf8 -m scripts.migrate_20261018

切勿用 app.seeds.main() 代替本脚本 —— seeds 会 drop_all 清空全库。
"""
from sqlalchemy import text

from app.db import Base, engine
import app.models  # noqa: F401  导入即注册全部表到 Base.metadata

# (表, 列, DDL)：列已存在则跳过
ALTERS = [
    ("work_segments", "template_id",
     "ALTER TABLE work_segments ADD COLUMN template_id INT NOT NULL DEFAULT 0 "
     "COMMENT 'regen 版本记录来源模板'"),
    ("work_segments", "word_cnt",
     "ALTER TABLE work_segments ADD COLUMN word_cnt INT NOT NULL DEFAULT 0"),
]


def col_exists(table: str, column: str) -> bool:
    with engine.connect() as conn:
        n = conn.execute(text(
            "SELECT COUNT(*) FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t AND COLUMN_NAME = :c"),
            {"t": table, "c": column}).scalar()
    return n > 0


def main():
    Base.metadata.create_all(engine)  # 只建缺失的表（本次新增 user_memories）
    print("create_all done")
    for table, column, ddl in ALTERS:
        if col_exists(table, column):
            print(f"skip {table}.{column} (exists)")
            continue
        with engine.begin() as conn:
            conn.execute(text(ddl))
        print(f"added {table}.{column}")
    print("migration done")


if __name__ == "__main__":
    main()
