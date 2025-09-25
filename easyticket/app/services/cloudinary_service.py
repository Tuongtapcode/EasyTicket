import cloudinary.uploader
from app.configs import cloudinary_configs

class CloudinaryService:
    def upload(self, file, folder="uploads"):
        try:
            response = cloudinary.uploader.upload(
                file,
                folder=folder,
                resource_type="image" #ho tro nhieu loai upload vi du nhu anh
            )
            return {
            "url": response["secure_url"],
            "public_id": response["public_id"]
            }
        except Exception as e:
            print("Upload failed:", e)
            return None