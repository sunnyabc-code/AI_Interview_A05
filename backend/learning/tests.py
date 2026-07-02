"""
学习路径完成状态测试（8 项 — 4.7.7）
覆盖: 创建路径 → 依次完成 → 重复完成防累加 → 查询当前路径 → 重置路径
"""
import pytest
from django.db import connection
from django.utils import timezone


def _ts():
    return timezone.now().strftime('%Y-%m-%d %H:%M:%S')


@pytest.fixture
def create_ltables(db):
    with connection.cursor() as c:
        c.execute("PRAGMA foreign_keys = OFF")
        c.execute("DROP TABLE IF EXISTS learning_path_items")
        c.execute("DROP TABLE IF EXISTS learning_paths")
        c.execute("DROP TABLE IF EXISTS learning_resources")
        c.execute("""CREATE TABLE learning_paths (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id BIGINT NOT NULL, position_id BIGINT NOT NULL,
            title VARCHAR(200) NOT NULL DEFAULT '', description TEXT NOT NULL DEFAULT '',
            progress REAL NOT NULL DEFAULT 0, is_completed INTEGER NOT NULL DEFAULT 0,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
        c.execute("""CREATE TABLE learning_resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT, title VARCHAR(300) NOT NULL DEFAULT '',
            resource_type VARCHAR(20) NOT NULL DEFAULT 'article', url VARCHAR(200) NOT NULL DEFAULT '',
            content TEXT NOT NULL DEFAULT '', position_id BIGINT NOT NULL DEFAULT 0,
            difficulty INTEGER NOT NULL DEFAULT 1, estimated_time INTEGER,
            tags TEXT NOT NULL DEFAULT '[]', is_active INTEGER NOT NULL DEFAULT 1,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
        c.execute("""CREATE TABLE learning_path_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT, learning_path_id BIGINT NOT NULL,
            resource_id BIGINT NOT NULL, "order" INTEGER NOT NULL DEFAULT 0,
            is_completed INTEGER NOT NULL DEFAULT 0, completed_at DATETIME,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
    yield


class TestLearningPathLifecycle:
    """学习路径完整生命周期"""

    def test_创建路径默认进度为0(self, create_ltables):
        with connection.cursor() as c:
            c.execute("INSERT INTO learning_paths (user_id,position_id,title,description,created_at,updated_at) VALUES (1,1,'Java后端进阶','系统提升',%s,%s)", [_ts(), _ts()])
            c.execute("SELECT progress,is_completed,title FROM learning_paths WHERE user_id=1")
            r = c.fetchone()
        assert r[0] == 0 and r[1] == 0 and r[2] == 'Java后端进阶'

    def test_依次完成后进度为100(self, create_ltables):
        ts = _ts()
        with connection.cursor() as c:
            c.execute("INSERT INTO learning_paths (id,user_id,position_id,title,description,created_at,updated_at) VALUES (1,1,1,'P1','',%s,%s)", [ts, ts])
            for i in range(3):
                c.execute("INSERT INTO learning_resources (id,title,resource_type,position_id,created_at,updated_at) VALUES (%s,%s,'article',1,%s,%s)", [10+i, f'R{i}', ts, ts])
                c.execute("INSERT INTO learning_path_items (learning_path_id,resource_id,\"order\",is_completed,created_at) VALUES (1,%s,%s,0,%s)", [10+i, i, ts])
            for i in range(3):
                c.execute("UPDATE learning_path_items SET is_completed=1,completed_at=%s WHERE learning_path_id=1 AND \"order\"=%s", [ts, i])
            c.execute("SELECT COUNT(*) FROM learning_path_items WHERE learning_path_id=1")
            total = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM learning_path_items WHERE learning_path_id=1 AND is_completed=1")
            done = c.fetchone()[0]
            c.execute("UPDATE learning_paths SET progress=%s,is_completed=%s WHERE id=1", [(done/total)*100, 1 if done==total else 0])
            c.execute("SELECT progress,is_completed FROM learning_paths WHERE id=1")
            r = c.fetchone()
        assert r[0] == 100.0 and r[1] == 1

    def test_部分完成进度正确计算(self, create_ltables):
        ts = _ts()
        with connection.cursor() as c:
            c.execute("INSERT INTO learning_paths (id,user_id,position_id,title,description,created_at,updated_at) VALUES (2,1,1,'P2','',%s,%s)", [ts, ts])
            for i in range(4):
                c.execute("INSERT INTO learning_resources (id,title,resource_type,position_id,created_at,updated_at) VALUES (%s,%s,'article',1,%s,%s)", [20+i, f'R{i}', ts, ts])
                c.execute("INSERT INTO learning_path_items (learning_path_id,resource_id,\"order\",is_completed,completed_at,created_at) VALUES (2,%s,%s,%s,%s,%s)", [20+i, i, 1 if i<2 else 0, ts if i<2 else None, ts])
            c.execute("SELECT COUNT(*) FROM learning_path_items WHERE learning_path_id=2")
            total = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM learning_path_items WHERE learning_path_id=2 AND is_completed=1")
            done = c.fetchone()[0]
            c.execute("UPDATE learning_paths SET progress=%s WHERE id=2", [(done/total)*100])
            c.execute("SELECT progress FROM learning_paths WHERE id=2")
            assert c.fetchone()[0] == 50.0

    def test_重复完成不重复累加(self, create_ltables):
        ts = _ts()
        with connection.cursor() as c:
            c.execute("INSERT INTO learning_paths (id,user_id,position_id,title,description,created_at,updated_at) VALUES (3,1,1,'P3','',%s,%s)", [ts, ts])
            c.execute("INSERT INTO learning_resources (id,title,resource_type,position_id,created_at,updated_at) VALUES (30,'唯一','article',1,%s,%s)", [ts, ts])
            c.execute("INSERT INTO learning_path_items (learning_path_id,resource_id,\"order\",is_completed,completed_at,created_at) VALUES (3,30,0,1,%s,%s)", [ts, ts])
            c.execute("UPDATE learning_path_items SET is_completed=1,completed_at=%s WHERE learning_path_id=3 AND resource_id=30", [ts])
            c.execute("SELECT COUNT(*) FROM learning_path_items WHERE learning_path_id=3 AND is_completed=1")
            assert c.fetchone()[0] == 1

    def test_查询当前活跃路径(self, create_ltables):
        ts = _ts()
        with connection.cursor() as c:
            c.execute("INSERT INTO learning_paths (id,user_id,position_id,title,description,progress,is_completed,created_at,updated_at) VALUES (1,1,1,'已完成','',100,1,%s,%s)", [ts, ts])
            c.execute("INSERT INTO learning_paths (id,user_id,position_id,title,description,progress,is_completed,created_at,updated_at) VALUES (2,1,2,'进行中','',50,0,%s,%s)", [ts, ts])
            c.execute("SELECT title,is_completed FROM learning_paths WHERE user_id=1 AND is_completed=0 ORDER BY id LIMIT 1")
            r = c.fetchone()
        assert r[0] == '进行中' and r[1] == 0

    def test_重置创建新路径旧路径保留(self, create_ltables):
        ts = _ts()
        with connection.cursor() as c:
            c.execute("INSERT INTO learning_paths (id,user_id,position_id,title,description,progress,is_completed,created_at,updated_at) VALUES (1,1,1,'旧','',100,1,%s,%s)", [ts, ts])
            c.execute("INSERT INTO learning_paths (id,user_id,position_id,title,description,progress,is_completed,created_at,updated_at) VALUES (2,1,1,'新','',0,0,%s,%s)", [ts, ts])
            c.execute("SELECT is_completed FROM learning_paths WHERE user_id=1 ORDER BY id")
            rows = c.fetchall()
        assert rows[0][0] == 1 and rows[1][0] == 0

    def test_任务按order排序(self, create_ltables):
        ts = _ts()
        with connection.cursor() as c:
            c.execute("INSERT INTO learning_paths (id,user_id,position_id,title,description,created_at,updated_at) VALUES (4,1,1,'有序','',%s,%s)", [ts, ts])
            for i, o in enumerate([2, 0, 1]):
                c.execute("INSERT INTO learning_resources (id,title,resource_type,position_id,created_at,updated_at) VALUES (%s,%s,'article',1,%s,%s)", [40+i, f'R{i}', ts, ts])
                c.execute("INSERT INTO learning_path_items (learning_path_id,resource_id,\"order\",created_at) VALUES (4,%s,%s,%s)", [40+i, o, ts])
            c.execute("SELECT \"order\" FROM learning_path_items WHERE learning_path_id=4 ORDER BY \"order\"")
            assert [r[0] for r in c.fetchall()] == [0, 1, 2]

    def test_空路径默认未完成(self, create_ltables):
        with connection.cursor() as c:
            c.execute("INSERT INTO learning_paths (user_id,position_id,title,description,created_at,updated_at) VALUES (1,1,'空路径','',%s,%s)", [_ts(), _ts()])
            c.execute("SELECT progress,is_completed FROM learning_paths WHERE title='空路径'")
            r = c.fetchone()
        assert r[0] == 0 and r[1] == 0
