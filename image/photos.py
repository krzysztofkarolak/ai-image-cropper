from gphotospy import authorize
from gphotospy.album import Album
from gphotospy.media import Media
from gphotospy.media import MediaItem
from google.cloud import storage
import cloudinary
import cloudinary.uploader
import cloudinary.api
import requests
import os

# Google Photos Init
CLIENT_SECRET_FILE = "gphoto_oauth.json"
with open(CLIENT_SECRET_FILE, "w") as file:
    file.write(os.environ.get('IC_ALBUM_SECRET'))
album_id = os.environ.get('IC_ALBUM_ID')
service = authorize.init(CLIENT_SECRET_FILE)
album_manager = Album(service)
media_manager = Media(service)

# Cloud Storage Init
bucket_name = os.environ.get('IC_BUCKET_NAME')
client = storage.Client()
bucket = client.bucket(bucket_name)
blobs_list = []

# Cloudinary
config = cloudinary.config(secure=True)

def set_file_extension(file_name):
    file_name_parts = file_name.split('.')
    if len(file_name_parts) > 1:
        file_name_without_extension = '.'.join(file_name_parts[:-1])
        new_file_name = file_name_without_extension + ".jpg"
        return new_file_name

def get_public_id(file_name):
    file_name_parts = file_name.split('.')
    if len(file_name_parts) > 1:
        file_name_without_extension = '.'.join(file_name_parts[:-1])
        return file_name_without_extension

def fetch_and_store_image(url, file_name):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            with open(file_name, 'wb') as f:
                f.write(response.content)
            return file_name
        else:
            print("Failed to fetch image:", response.status_code)
    except Exception as e:
        print("Error fetching image:", str(e))


def upload_image_cloudinary(file_name, public_id):
    cloudinary.uploader.upload(file_name,
                               public_id=public_id, unique_filename=False, overwrite=True)


def create_transformation_cloudinary(file_name, public_id):
    transformed_url = cloudinary.CloudinaryImage(public_id).build_url(gravity="faces", height=480, width=800, crop="fill")
    fetch_and_store_image(transformed_url, file_name)

    cloudinary.uploader.destroy(public_id)


def downloadAndStorePhoto(search_iterator, file_name):
    media = MediaItem(search_iterator).get_url()
    blob_name = fetch_and_store_image(media, file_name)
    try:
        upload_image_cloudinary(blob_name, get_public_id(blob_name))
        create_transformation_cloudinary(blob_name, get_public_id(blob_name))
    except Exception as e:
        print("Error cropping image: " + str(e))
    upload_blob(bucket, blob_name)
    os.remove(blob_name)


def create_blob_list():
    blobs = bucket.list_blobs()
    for blob in blobs:
        blobs_list.append(blob.name)


def upload_blob(bucket, file_name):
    blob = bucket.blob(file_name)
    generation_match_precondition = 0

    blob.upload_from_filename(file_name, if_generation_match=generation_match_precondition)

    print(
        f"File {file_name} uploaded to {file_name}."
    )

def delete_blob(bucket, blob_name):
    blob = bucket.blob(blob_name)
    generation_match_precondition = None

    blob.reload()
    generation_match_precondition = blob.generation

    blob.delete(if_generation_match=generation_match_precondition)

    print(f"Blob {blob_name} deleted.")

create_blob_list()

photos_list = []

# search in album, adding new photos
search_iterator = media_manager.search_album(album_id)
try:
    for _ in range(2048):
        iterator = next(search_iterator)
        file_name = iterator.get("filename")
        item_name = set_file_extension(file_name)
        photos_list.append(item_name)
        print("Checking to add: " + item_name)
        if item_name not in blobs_list:
            print(item_name + " not in bucket")
            downloadAndStorePhoto(iterator, item_name)
except (StopIteration, TypeError) as e:
    print("No (more) media in album.")

# Remove photos deleted from album
for file in blobs_list:
    print("Checking to delete: " + file)
    if file not in photos_list:
        print(file + " not in album anymore")
        delete_blob(bucket, file)