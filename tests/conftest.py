import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from xhs_clone_api.db import Base, get_db
from xhs_clone_api.main import app
from xhs_clone_api.seed import seed_all


@pytest.fixture()
def client(tmp_path):
    db_url = f"sqlite:///{tmp_path}/test.db"
    test_engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False},
    )
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    Base.metadata.create_all(test_engine)
    with TestSession() as s:
        seed_all(s)

    def override_get_db():
        s = TestSession()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = override_get_db
    # 不进 lifespan (避免触碰默认 sqlite engine) · TestClient 不用 with 直接构造
    yield TestClient(app)
    app.dependency_overrides.clear()
