# Image Cropper Sync App

A Python app for retrieving images from Google Photos, cropping them using the Cloudinary AI service, and syncing them with a Google Cloud Storage bucket. This application is intended to run as a Kubernetes job or a standalone cronjob.

## Features

- Retrieve images from Google Photos.
- Crop images using the Cloudinary AI service.
- Sync cropped images with a Google Cloud Storage bucket.
- Deployable as a Kubernetes job or a standalone cronjob.

## Environment Variables

The app requires the following environment variables to be set:

| Environment Variable      | Description |
|---------------------------|-------------|
| `GOOGLE_APP_CREDENTIALS`  | Path to the JSON file that contains your Google application credentials. |
| `IC_BUCKET_NAME`          | The name of the Google Cloud Storage bucket where cropped images will be synced. |
| `IC_ALBUM_SECRET`         | A secret key for accessing the specific album in Google Photos. |
| `IC_ALBUM_ID`             | The ID of the album in Google Photos from which images will be retrieved. |
| `CLOUDINARY_URL`          | The Cloudinary URL for accessing the Cloudinary API. |

## Repository Contents

- **Dockerfile**: Build a Docker image for the app.
- **Helm Chart**: Helm chart for deploying the app in a Kubernetes cluster.

## Usage

### Running as a Kubernetes Job

1. Ensure your Kubernetes cluster is up and running.
2. Configure your environment variables in your values file.
3. Deploy the Helm chart:
   ```sh
   helm install image-cropper-sync ./helm-chart

### Running as a Standalone Cronjob

1. Build the Docker image:
   ```sh
   docker build -t image-cropper-sync .

2. Run the Docker container with the necessary environment variables:
   ```sh
   docker run -e GOOGLE_APP_CREDENTIALS=<your-google-app-credentials> \
           -e IC_BUCKET_NAME=<your-bucket-name> \
           -e IC_ALBUM_SECRET=<your-album-secret> \
           -e IC_ALBUM_ID=<your-album-id> \
           -e CLOUDINARY_URL=<your-cloudinary-url> \
           image-cropper-sync

### Contributing
Contributions are welcome! Please submit a pull request or open an issue to discuss any changes.
