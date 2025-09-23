import pytest
from unittest.mock import patch
from app.services.cloudinary_service import CloudinaryService


# ---- Tests upload ----
def test_upload_success():
    svc = CloudinaryService()

    mock_response = {
        "secure_url": "https://res.cloudinary.com/demo/image/upload/v12345/sample.jpg",
        "public_id": "sample"
    }

    with patch("cloudinary.uploader.upload", return_value=mock_response) as mock_upload:
        result = svc.upload("fake_file.jpg", folder="test_folder")

        # Đảm bảo hàm upload được gọi đúng
        mock_upload.assert_called_once_with(
            "fake_file.jpg",
            folder="test_folder",
            resource_type="image"
        )

        # Đảm bảo kết quả trả về đúng format
        assert result["url"] == mock_response["secure_url"]
        assert result["public_id"] == mock_response["public_id"]


def test_upload_failure():
    svc = CloudinaryService()

    with patch("cloudinary.uploader.upload", side_effect=Exception("Upload error")) as mock_upload:
        result = svc.upload("fake_file.jpg")

        mock_upload.assert_called_once()
        # Nếu upload fail thì kết quả trả về phải là None
        assert result is None
