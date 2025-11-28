# services/r2_service.py
import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError, BotoCoreError
import os
import mimetypes
from typing import Optional, Dict, List
import logging

class R2Service:
    """
    Cloudflare R2 Storage Service
    Handles audio file uploads, downloads, and management using boto3 S3 interface
    """
    
    def __init__(self, config):
        """Initialize R2 service with configuration"""
        self.config = config
        self.r2_client = None  # ✅ FIXED: Use consistent attribute name
        self.bucket_name = getattr(config, 'R2_BUCKET_NAME', 'lingualoopaudio')
        self.public_url = getattr(config, 'R2_PUBLIC_URL', None)
        
        # Initialize client if credentials are available
        if self._has_required_credentials():
            self._initialize_client()
        else:
            print("❌ Warning: R2 credentials not fully configured")
            print("Required: R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_ACCOUNT_ID")
    
    def _has_required_credentials(self) -> bool:
        """Check if all required R2 credentials are present"""
        required_attrs = ['R2_ACCESS_KEY_ID', 'R2_SECRET_ACCESS_KEY', 'R2_ACCOUNT_ID']
        
        for attr in required_attrs:
            if not hasattr(self.config, attr) or not getattr(self.config, attr):
                print(f"❌ Missing required credential: {attr}")
                return False
        return True
    
    def _initialize_client(self):
        """Initialize the R2 client using boto3 S3 interface"""
        try:
            # Construct endpoint URL
            endpoint_url = f"https://{self.config.R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
            
            self.r2_client = boto3.client(
                's3',
                endpoint_url=endpoint_url,
                aws_access_key_id=self.config.R2_ACCESS_KEY_ID,
                aws_secret_access_key=self.config.R2_SECRET_ACCESS_KEY,
                config=BotoConfig(
                    signature_version='s3v4',
                    region_name='auto'
                )
            )
            
            # Test the connection
            self._test_connection()
            print(f"✅ R2 client initialized successfully for bucket: {self.bucket_name}")
            
        except Exception as e:
            print(f"❌ Failed to initialize R2 client: {e}")
            self.r2_client = None
    
    def _test_connection(self):
        """Test R2 connection by listing objects (limited to 1)"""
        try:
            self.r2_client.list_objects_v2(Bucket=self.bucket_name, MaxKeys=1)
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchBucket':
                print(f"⚠️ Warning: Bucket '{self.bucket_name}' does not exist")
            else:
                raise e
    
    def upload_audio(self, filename: str, audio_data: bytes) -> bool:
        """
        Upload audio data to R2 bucket
        
        Args:
            filename: Name of the file (e.g., "test-slug.mp3")
            audio_data: Binary audio data
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.r2_client:
            print("❌ R2 client not initialized")
            return False
        
        try:
            print(f"🔧 Uploading {filename} to R2 bucket: {self.bucket_name}")
            print(f"🔧 File size: {len(audio_data)} bytes")
            
            # Upload to bucket root (not in subdirectory)
            self.r2_client.put_object(
                Bucket=self.bucket_name,
                Key=filename,  # File goes to bucket root
                Body=audio_data,
                ContentType='audio/mpeg',
                CacheControl='public, max-age=31536000',  # Cache for 1 year
                Metadata={
                    'uploaded-by': 'lingualoop-backend',
                    'content-type': 'audio/mpeg'
                }
            )
            
            print(f"✅ Successfully uploaded {filename} to R2")
            
            # Log the public URL if available
            if self.public_url:
                public_url = f"{self.public_url}/{filename}"
                print(f"🌐 Public URL: {public_url}")
            
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            print(f"❌ AWS ClientError uploading {filename}: {error_code} - {e}")
            return False
        except BotoCoreError as e:
            print(f"❌ BotoCoreError uploading {filename}: {e}")
            return False
        except Exception as e:
            print(f"❌ Unexpected error uploading {filename}: {e}")
            return False
    
    def download_audio(self, filename: str) -> Optional[bytes]:
        """
        Download audio file from R2 bucket
        
        Args:
            filename: Name of the file to download
            
        Returns:
            bytes: Audio data if successful, None otherwise
        """
        if not self.r2_client:
            print("❌ R2 client not initialized")
            return None
        
        try:
            print(f"📥 Downloading {filename} from R2")
            
            response = self.r2_client.get_object(
                Bucket=self.bucket_name,
                Key=filename
            )
            
            audio_data = response['Body'].read()
            print(f"✅ Downloaded {filename} ({len(audio_data)} bytes)")
            return audio_data
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey':
                print(f"❌ File not found: {filename}")
            else:
                print(f"❌ Error downloading {filename}: {error_code} - {e}")
            return None
        except Exception as e:
            print(f"❌ Unexpected error downloading {filename}: {e}")
            return None
    
    def delete_audio(self, filename: str) -> bool:
        """
        Delete audio file from R2 bucket
        
        Args:
            filename: Name of the file to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.r2_client:
            print("❌ R2 client not initialized")
            return False
        
        try:
            print(f"🗑️ Deleting {filename} from R2")
            
            self.r2_client.delete_object(
                Bucket=self.bucket_name,
                Key=filename
            )
            
            print(f"✅ Successfully deleted {filename} from R2")
            return True
            
        except ClientError as e:
            print(f"❌ Error deleting {filename}: {e}")
            return False
        except Exception as e:
            print(f"❌ Unexpected error deleting {filename}: {e}")
            return False
    
    def file_exists(self, filename: str) -> bool:
        """
        Check if audio file exists in R2 bucket
        
        Args:
            filename: Name of the file to check
            
        Returns:
            bool: True if file exists, False otherwise
        """
        if not self.r2_client:
            return False
        
        try:
            self.r2_client.head_object(Bucket=self.bucket_name, Key=filename)
            return True
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                return False
            else:
                print(f"❌ Error checking file existence: {e}")
                return False
        except Exception as e:
            print(f"❌ Unexpected error checking file: {e}")
            return False
    
    def list_audio_files(self, prefix: str = '', max_keys: int = 100) -> List[Dict]:
        """
        List audio files in R2 bucket
        
        Args:
            prefix: Filter files by prefix
            max_keys: Maximum number of files to return
            
        Returns:
            List[Dict]: List of file information dictionaries
        """
        if not self.r2_client:
            print("❌ R2 client not initialized")
            return []
        
        try:
            response = self.r2_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                MaxKeys=max_keys
            )
            
            files = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    files.append({
                        'key': obj['Key'],
                        'size': obj['Size'],
                        'last_modified': obj['LastModified'].isoformat(),
                        'etag': obj['ETag'].strip('"')
                    })
            
            print(f"📋 Found {len(files)} files with prefix '{prefix}'")
            return files
            
        except ClientError as e:
            print(f"❌ Error listing files: {e}")
            return []
        except Exception as e:
            print(f"❌ Unexpected error listing files: {e}")
            return []
    
    def get_audio_url(self, slug: str) -> str:
        """
        Get public URL for audio file
        
        Args:
            slug: Test slug (filename without extension)
            
        Returns:
            str: Public URL for the audio file
        """
        if self.public_url:
            return f"{self.public_url}/{slug}.mp3"
        else:
            # Fallback to constructed URL if public_url not configured
            return f"https://pub-{self.bucket_name}.r2.dev/{slug}.mp3"
    
    def get_file_info(self, filename: str) -> Optional[Dict]:
        """
        Get detailed information about a file
        
        Args:
            filename: Name of the file
            
        Returns:
            Dict: File information or None if not found
        """
        if not self.r2_client:
            return None
        
        try:
            response = self.r2_client.head_object(
                Bucket=self.bucket_name,
                Key=filename
            )
            
            return {
                'filename': filename,
                'size': response['ContentLength'],
                'last_modified': response['LastModified'].isoformat(),
                'content_type': response.get('ContentType', 'unknown'),
                'etag': response['ETag'].strip('"'),
                'cache_control': response.get('CacheControl', ''),
                'metadata': response.get('Metadata', {})
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey':
                return None
            else:
                print(f"❌ Error getting file info: {e}")
                return None
        except Exception as e:
            print(f"❌ Unexpected error getting file info: {e}")
            return None
    
    def upload_from_url(self, filename: str, url: str) -> bool:
        """
        Upload audio from a URL to R2 (useful for external audio sources)
        
        Args:
            filename: Name to save the file as
            url: URL to download from
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            import requests
            
            print(f"📥 Downloading from URL: {url}")
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            audio_data = response.content
            print(f"✅ Downloaded {len(audio_data)} bytes from URL")
            
            return self.upload_audio(filename, audio_data)
            
        except ImportError:
            print("❌ requests library not available for URL download")
            return False
        except requests.RequestException as e:
            print(f"❌ Error downloading from URL: {e}")
            return False
        except Exception as e:
            print(f"❌ Unexpected error in upload_from_url: {e}")
            return False
    
    def get_bucket_stats(self) -> Dict:
        """
        Get statistics about the R2 bucket
        
        Returns:
            Dict: Bucket statistics
        """
        if not self.r2_client:
            return {"error": "R2 client not initialized"}
        
        try:
            # List all objects to calculate stats
            response = self.r2_client.list_objects_v2(Bucket=self.bucket_name)
            
            total_files = 0
            total_size = 0
            
            if 'Contents' in response:
                total_files = len(response['Contents'])
                total_size = sum(obj['Size'] for obj in response['Contents'])
            
            return {
                'bucket_name': self.bucket_name,
                'total_files': total_files,
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'public_url': self.public_url
            }
            
        except Exception as e:
            return {"error": f"Failed to get bucket stats: {e}"}
