import os

os.environ["TEST_EMAIL_SENDER"] = "1"

from fastapi.testclient import TestClient

from main import app  # <-- импортируйте вашу FastAPI app

# включаем режим тестовой отправки

client = TestClient(app)
DEMO_DIR = "demo"


def upload_files():
    report_path = os.path.join(DEMO_DIR, "reports.html")
    employees_path = os.path.join(DEMO_DIR, "users.txt")

    # Проверяем, что файлы действительно существуют
    assert os.path.exists(report_path)
    assert os.path.exists(employees_path)

    with open(report_path, "rb") as report_file, open(
        employees_path, "rb"
    ) as employees_file:
        files = {
            "report": ("reports.html", report_file.read(), "application/octet-stream"),
            "employees": (
                "users.txt",
                employees_file.read(),
                "application/octet-stream",
            ),
        }
    return files


# ---------- /api/v1/upload ----------
def test_upload_file_real_files():

    response = client.post("/api/v1/upload", files=upload_files())

    assert response.status_code == 200
    data = response.json()

    # Проверяем минимально — не знаем структуру ответа
    assert isinstance(data, list)
    assert len(data) > 0
    assert "email" in data[0]
    assert "name" in data[0]
    assert data[0].get("html", None) is None


def test_upload_bad_request():
    # нет обязательных полей
    response = client.post("/api/v1/upload", json={})
    assert response.status_code in (400, 422)


# ---------- /api/v1/report/{id} ----------
def test_get_report_not_found():
    response = client.get("/api/v1/report/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 200
    assert response.text == ""


def test_get_report_ok():
    # сначала создаём отчёт (если upload действительно создаёт report)
    response = client.post("/api/v1/upload", files=upload_files())

    assert response.status_code == 200
    data = response.json()

    response = client.get(f"/api/v1/report/{data[0]['id']}")
    assert response.status_code == 200
    assert data[0]["name"] in response.text
    assert data[1]["name"] not in response.text


# ---------- /api/v1/send ----------
def test_send_ok():
    response = client.post("/api/v1/upload", files=upload_files())

    assert response.status_code == 200
    data = response.json()

    response = client.post("/api/v1/send", json=[data[0]["id"]])
    assert response.status_code == 200

    assert response.json().get("status", None) is True
