import pytest
from PIL import Image


@pytest.fixture
def workspace(tmp_path):
    for directory in ["references/images_1", "products", "brief", "prompts"]:
        (tmp_path / directory).mkdir(parents=True)
    for name in ["10.png", "2.png", "1.png"]:
        Image.new("RGB", (1024, 1024), "blue").save(tmp_path / "references/images_1" / name)
    Image.new("RGB", (128, 128), "red").save(tmp_path / "products/product.jpg")
    (tmp_path / "brief/product.md").write_text("红色陶瓷杯，容量 300mL。", encoding="utf-8")
    return tmp_path
