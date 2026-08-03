"""Cloud storage with auto-cleanup for images and videos."""
import boto3
from botocore.config import Config
from pathlib import Path
import os
from datetime import datetime, timedelta


class CloudStorage:
    """Free cloud storage via Cloudflare R2 (10GB free, no egress fees)."""

    def __init__(self):
        # Cloudflare R2 credentials (free tier)
        self.account_id = os.getenv('R2_ACCOUNT_ID', '')
        self.access_key = os.getenv('R2_ACCESS_KEY', '')
        self.secret_key = os.getenv('R2_SECRET_KEY', '')
        self.bucket_name = os.getenv('R2_BUCKET_NAME', 'ubt-media')

        # Local fallback if R2 not configured
        self.local_storage = Path('test_output')
        self.local_storage.mkdir(parents=True, exist_ok=True)

        # Use R2 if configured, else local
        if self.account_id and self.access_key and self.secret_key:
            self.s3_client = boto3.client(
                's3',
                endpoint_url=f'https://{self.account_id}.r2.cloudflarestorage.com',
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                config=Config(signature_version='s3v4'),
                region_name='auto'
            )
            self.use_r2 = True
        else:
            self.s3_client = None
            self.use_r2 = False

    def upload_file(self, file_path: Path, key: str) -> str:
        """Upload file to R2 or save locally. Returns URL."""
        if self.use_r2:
            try:
                self.s3_client.upload_file(
                    str(file_path),
                    self.bucket_name,
                    key,
                    ExtraArgs={'ContentType': self._get_content_type(file_path)}
                )
                url = f"https://pub-{self.account_id}.r2.dev/{key}"
                return url
            except Exception as e:
                print(f"R2 upload failed: {e}, saving locally")
                return self._save_local(file_path, key)
        else:
            return self._save_local(file_path, key)

    def _save_local(self, file_path: Path, key: str) -> str:
        """Save file locally and return path."""
        dest = self.local_storage / Path(key).name
        dest.write_bytes(file_path.read_bytes())
        return f'/static/{dest.name}'

    def list_files(self, prefix='', hours=24) -> list[str]:
        """List files uploaded in last N hours."""
        if not self.use_r2:
            # Local files
            cutoff = datetime.now() - timedelta(hours=hours)
            files = []
            for f in self.local_storage.glob('*'):
                if f.stat().st_mtime > cutoff.timestamp():
                    files.append(f'/static/{f.name}')
            return files

        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            files = []
            cutoff = datetime.utcnow() - timedelta(hours=hours)

            for obj in response.get('Contents', []):
                if obj['LastModified'].replace(tzinfo=None) > cutoff:
                    key = obj['Key']
                    url = f"https://pub-{self.account_id}.r2.dev/{key}"
                    files.append(url)
            return files
        except Exception as e:
            print(f"List files error: {e}")
            return []

    def cleanup_old_files(self, hours=24):
        """Delete files older than N hours."""
        if not self.use_r2:
            # Local cleanup
            cutoff = datetime.now() - timedelta(hours=hours)
            deleted = 0
            for f in self.local_storage.glob('*'):
                if f.stat().st_mtime < cutoff.timestamp():
                    f.unlink()
                    deleted += 1
            return deleted

        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name
            )
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            deleted = 0

            for obj in response.get('Contents', []):
                if obj['LastModified'].replace(tzinfo=None) < cutoff:
                    self.s3_client.delete_object(
                        Bucket=self.bucket_name,
                        Key=obj['Key']
                    )
                    deleted += 1
            return deleted
        except Exception as e:
            print(f"Cleanup error: {e}")
            return 0

    @staticmethod
    def _get_content_type(file_path: Path) -> str:
        ext = file_path.suffix.lower()
        types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.mp4': 'video/mp4',
            '.webm': 'video/webm',
        }
        return types.get(ext, 'application/octet-stream')


# Global instance
storage = CloudStorage()
