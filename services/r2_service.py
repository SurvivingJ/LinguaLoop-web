# services/r2_service.py
import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError, BotoCoreError
import logging

logger = logging.getLogger(__name__)

class R2Service:
    """
    Cloudflare R2 Storage Service
    Handles audio file uploads, downloads, and management using boto3 S3 interface
    """
    
    def __init__(self, config):
        """Initialize R2 service with configuration"""
        self.config = config
        self.r2_client = None  # ✅ FIXED: Use consistent attribute name
        self.bucket_name = getattr(config, 'R2_BUCKET_NAME', 'linguadojoaudio')
        self.public_url = getattr(config, 'R2_PUBLIC_URL', None)
        
        # Initialize client if credentials are available
        if self._has_required_credentials():
            self._initialize_client()
        else:
            logger.warning("R2 credentials not fully configured. Required: R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_ACCOUNT_ID")
    
    def _has_required_credentials(self) -> bool:
        """Check if all required R2 credentials are present"""
        required_attrs = ['R2_ACCESS_KEY_ID', 'R2_SECRET_ACCESS_KEY', 'R2_ACCOUNT_ID']
        
        for attr in required_attrs:
            if not hasattr(self.config, attr) or not getattr(self.config, attr):
                logger.warning(f"Missing required R2 credential: {attr}")
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
            logger.info(f"R2 client initialized successfully for bucket: {self.bucket_name}")

        except Exception as e:
            logger.error(f"Failed to initialize R2 client: {e}")
            self.r2_client = None
    
    def _test_connection(self):
        """Test R2 connection by listing objects (limited to 1)"""
        try:
            self.r2_client.list_objects_v2(Bucket=self.bucket_name, MaxKeys=1)
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchBucket':
                logger.warning(f"Bucket '{self.bucket_name}' does not exist")
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
            logger.error("R2 client not initialized")
            return False

        try:
            logger.debug(f"Uploading {filename} to R2 bucket: {self.bucket_name} ({len(audio_data)} bytes)")
            
            # Upload to bucket root (not in subdirectory)
            self.r2_client.put_object(
                Bucket=self.bucket_name,
                Key=filename,  # File goes to bucket root
                Body=audio_data,
                ContentType='audio/mpeg',
                CacheControl='public, max-age=31536000',  # Cache for 1 year
                Metadata={
                    'uploaded-by': 'linguadojo-backend',
                    'content-type': 'audio/mpeg'
                }
            )
            
            logger.info(f"Successfully uploaded {filename} to R2")

            # Log the public URL if available
            if self.public_url:
                public_url = f"{self.public_url}/{filename}"
                logger.debug(f"Public URL: {public_url}")

            return True

        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(f"AWS ClientError uploading {filename}: {error_code} - {e}")
            return False
        except BotoCoreError as e:
            logger.error(f"BotoCoreError uploading {filename}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error uploading {filename}: {e}")
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
                logger.error(f"Error checking file existence: {e}")
                return False
        except Exception as e:
            logger.error(f"Unexpected error checking file: {e}")
            return False
    
    def get_audio_url(self, slug: str) -> str:
        """
        Get public URL for audio file

        Args:
            slug: Test slug (filename without extension)

        Returns:
            str: Public URL for the audio file
        """
        filename = f"{slug}.mp3"

        if self.public_url:
            return f"{self.public_url}/{filename}"
        else:
            # Fallback if public_url not configured
            logger.warning("R2_PUBLIC_URL not configured, using default")
            return f"https://audio.linguadojo.com/{filename}"
