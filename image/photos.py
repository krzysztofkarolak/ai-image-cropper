import os
import smbclient
import cloudinary
import cloudinary.uploader
import requests
import logging
import sys
from google.cloud import storage
from PIL import Image, ImageOps

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# SMB config
SMB_SERVER = os.environ.get('SMB_SERVER')
SMB_SHARE = os.environ.get('SMB_SHARE')
SMB_USERNAME = os.environ.get('SMB_USERNAME')
SMB_PASSWORD = os.environ.get('SMB_PASSWORD')

# Cloud Storage Init
GCS_SECRET_FILE = "/tmp/gcs_key.json"
with open(GCS_SECRET_FILE, "w") as file:
    file.write(os.environ.get('GOOGLE_APP_CREDENTIALS'))
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GCS_SECRET_FILE
bucket_name = os.environ.get('IC_BUCKET_NAME')
client = storage.Client()
bucket = client.bucket(bucket_name)

# Services config
cloudinary.config(secure=True)
smbclient.ClientConfig(username=SMB_USERNAME, password=SMB_PASSWORD)
target_image_width = os.environ.get('TARGET_IMAGE_WIDTH')
target_image_height = os.environ.get('TARGET_IMAGE_HEIGHT')

def reduce_image_size(file_path, max_size_mb=8, max_width=2000):
    size_mb = os.path.getsize(file_path) / (1024 * 1024)

    try:
        with Image.open(file_path) as img:
            # Fix photo rotation
            img = ImageOps.exif_transpose(img)

            if (img.width > max_width) and (size_mb > max_size_mb):
                logging.info(f"{file_path} is {size_mb:.2f} MB – optimizing")
                ratio = max_width / float(img.width)
                new_height = int(img.height * ratio)
                img = img.resize((max_width, new_height), Image.LANCZOS)
            else:
                logging.info(f"{file_path} is {size_mb:.2f} MB – OK")

            img = img.convert("RGB")
            img.save(file_path, "JPEG", quality=85, optimize=True)

        new_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        logging.info(f"Reduced size of {file_path} from {size_mb:.2f} MB to {new_size_mb:.2f} MB")

    except Exception as e:
        logging.error(f"Error while optimizing photo locally {file_path}: {e}")

def upload_blob(bucket, file_path):
    blob_name = os.path.basename(file_path)
    blob = bucket.blob(blob_name)
    blob.upload_from_filename(file_path)
    logging.info(f"File {blob_name} uploaded to bucket.")

def upload_image_cloudinary(file_name, public_id):
    logging.info(f"Uploading to Cloudinary")
    cloudinary.uploader.upload(
        file_name,
        public_id=public_id,
        unique_filename=False,
        overwrite=True
    )

def create_transformation_cloudinary(file_name, public_id):
    logging.info(f"Transforming with Cloudinary")
    transformed_url = cloudinary.CloudinaryImage(public_id).build_url(
        gravity="faces",
        height=target_image_height,
        width=target_image_width,
        crop="fill",
        angle=0
    )

    response = requests.get(transformed_url)

    if response.status_code == 200:
        with open(file_name, "wb") as f:
            f.write(response.content)
    cloudinary.uploader.destroy(public_id)

def main():
    blobs_in_bucket = {blob.name for blob in bucket.list_blobs()}
    photos_on_smb = set()

    remote_dir = f"\\\\{SMB_SERVER}\\{SMB_SHARE}\\"
    for file in smbclient.listdir(remote_dir):
        if file.lower().endswith(".jpg"):
            photos_on_smb.add(file)
            if file not in blobs_in_bucket:
                logging.info(f"Downloading and processing: {file}")
                local_file_path = os.path.join("/tmp", file)
                with smbclient.open_file(remote_dir + file, mode="rb") as remote_file, open(local_file_path, "wb") as local_file:
                    local_file.write(remote_file.read())

                public_id = os.path.splitext(file)[0]

                try:
                    reduce_image_size(local_file_path)
                    upload_image_cloudinary(local_file_path, public_id)
                    create_transformation_cloudinary(local_file_path, public_id)
                except Exception as e:
                    logging.error("Error cropping image: " + str(e))

                upload_blob(bucket, local_file_path)
                os.remove(local_file_path)

    for blob_name in blobs_in_bucket:
        if blob_name not in photos_on_smb:
            blob = bucket.blob(blob_name)
            blob.delete()
            logging.info(f"Removed {blob_name} from bucket.")

if __name__ == "__main__":
    main()
