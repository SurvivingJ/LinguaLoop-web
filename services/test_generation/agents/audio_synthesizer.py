"""
Audio Synthesizer Agent

Generates TTS audio and uploads to R2 storage.
"""

import logging
import random
from typing import Optional, List
import azure.cognitiveservices.speech as speechsdk
import boto3
from botocore.config import Config as BotoConfig
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config import Config

logger = logging.getLogger(__name__)


class AudioSynthesizer:
    """Generates TTS audio and uploads to R2."""

    def __init__(
        self,
        speech_key: str = None,
        service_region: str = None,
        r2_config: dict = None
    ):
        """
        Initialize the Audio Synthesizer.

        Args:
            speech_key: Azure Speech Service subscription key
            service_region: Azure Speech Service region (e.g., 'eastus', 'westeurope')
            r2_config: Dict with R2 configuration:
                - account_id
                - access_key_id
                - secret_access_key
                - bucket_name
        """
        import os

        # Azure Speech Service Configuration
        self.speech_key = speech_key or os.getenv('SPEECH_KEY')
        self.service_region = service_region or os.getenv('SPEECH_REGION')
        self.api_call_count = 0

        if not self.speech_key or not self.service_region:
            logger.warning("Azure Speech Service credentials not configured - TTS will fail")

        # Initialize R2 client
        self.r2_config = r2_config or {
            'account_id': os.getenv('R2_ACCOUNT_ID'),
            'access_key_id': os.getenv('R2_ACCESS_KEY_ID'),
            'secret_access_key': os.getenv('R2_SECRET_ACCESS_KEY'),
            'bucket_name': os.getenv('R2_BUCKET_NAME', 'linguadojoaudio')
        }

        self.r2_client = None
        self._initialize_r2_client()

        logger.info("AudioSynthesizer initialized with Azure Speech Services")

    def _initialize_r2_client(self) -> None:
        """Initialize the R2 client using boto3."""
        try:
            if not all([
                self.r2_config.get('account_id'),
                self.r2_config.get('access_key_id'),
                self.r2_config.get('secret_access_key')
            ]):
                logger.warning("R2 credentials incomplete - audio upload will fail")
                return

            endpoint_url = f"https://{self.r2_config['account_id']}.r2.cloudflarestorage.com"

            self.r2_client = boto3.client(
                's3',
                endpoint_url=endpoint_url,
                aws_access_key_id=self.r2_config['access_key_id'],
                aws_secret_access_key=self.r2_config['secret_access_key'],
                config=BotoConfig(
                    signature_version='s3v4',
                    region_name='auto'
                )
            )

            logger.info(f"R2 client initialized for bucket: {self.r2_config['bucket_name']}")

        except Exception as e:
            logger.error(f"Failed to initialize R2 client: {e}")
            self.r2_client = None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((Exception,)),
        reraise=True
    )
    def generate_and_upload(
        self,
        text: str,
        file_id: str,
        voice: str = None,
        speed: float = None,
        model: str = None
    ) -> str:
        """
        Generate TTS audio using Azure Speech Services and upload to R2.

        Args:
            text: Text to synthesize
            file_id: UUID to use as file name (without .mp3 extension)
            voice: Azure Neural Voice name (default: en-US-AvaMultilingualNeural)
            speed: Playback speed (currently not supported by Azure SDK in same way as OpenAI)
            model: Deprecated parameter (Azure uses voices directly)

        Returns:
            str: R2 public URL for the uploaded audio
        """
        # Default to Azure Neural Voice if not specified
        selected_voice = voice or "en-US-AvaMultilingualNeural"

        try:
            # Generate audio using Azure Speech SDK
            logger.debug(f"Generating TTS for {file_id} with Azure voice '{selected_voice}'")

            # 1. Configure Speech Service
            speech_config = speechsdk.SpeechConfig(
                subscription=self.speech_key,
                region=self.service_region
            )
            speech_config.speech_synthesis_voice_name = selected_voice

            # 2. Set Output Format to MP3 (crucial for web playback and file size)
            speech_config.set_speech_synthesis_output_format(
                speechsdk.SpeechSynthesisOutputFormat.Audio48Khz192KBitRateMonoMp3
            )

            # 3. Create Synthesizer (audio_config=None keeps data in memory)
            synthesizer = speechsdk.SpeechSynthesizer(
                speech_config=speech_config,
                audio_config=None
            )

            # 4. Generate audio
            result = synthesizer.speak_text_async(text).get()

            self.api_call_count += 1

            # 5. Process Result
            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                audio_data = result.audio_data

                if not audio_data:
                    raise Exception("Empty audio response from Azure TTS")

                logger.debug(f"Generated {len(audio_data)} bytes of audio")

                # Upload to R2
                success = self._upload_to_r2(file_id, audio_data)

                if success:
                    logger.info(f"Successfully generated and uploaded audio: {file_id}.mp3")
                    # Return R2 public URL using Config
                    return Config.get_audio_url(file_id)

                raise Exception(f"Failed to upload audio for {file_id}")

            elif result.reason == speechsdk.ResultReason.Canceled:
                cancellation_details = result.cancellation_details
                error_msg = f"Azure TTS Error: {cancellation_details.reason}"
                if cancellation_details.error_details:
                    error_msg += f" - {cancellation_details.error_details}"
                raise Exception(error_msg)
            else:
                raise Exception(f"Unexpected result reason: {result.reason}")

        except Exception as e:
            logger.error(f"Audio generation/upload failed for {file_id}: {e}")
            raise

    def _upload_to_r2(self, slug: str, audio_data: bytes) -> bool:
        """
        Upload audio data to R2 bucket.

        Args:
            slug: File name (without extension)
            audio_data: Binary audio data

        Returns:
            bool: True if successful
        """
        if not self.r2_client:
            raise Exception("R2 client not initialized")

        filename = f"{slug}.mp3"
        bucket = self.r2_config['bucket_name']

        try:
            self.r2_client.put_object(
                Bucket=bucket,
                Key=filename,
                Body=audio_data,
                ContentType='audio/mpeg',
                CacheControl='public, max-age=31536000',
                Metadata={
                    'uploaded-by': 'test-generation',
                    'content-type': 'audio/mpeg'
                }
            )

            logger.debug(f"Uploaded {filename} to R2 bucket {bucket}")
            return True

        except Exception as e:
            logger.error(f"R2 upload failed for {filename}: {e}")
            raise

    def select_voice(
        self,
        voice_ids: List[str] = None,
        language_code: str = None
    ) -> str:
        """
        Select a TTS voice, optionally from a list.

        Args:
            voice_ids: List of voice IDs to choose from
            language_code: Language code (for future language-specific selection)

        Returns:
            str: Selected voice ID (Azure Neural Voice name)
        """
        if voice_ids and len(voice_ids) > 0:
            # Random selection for variety
            return random.choice(voice_ids)

        # Default Azure Neural Voices - high quality multilingual voices
        default_voices = [
            'en-US-AvaMultilingualNeural',      # Balanced female
            'en-US-AndrewMultilingualNeural',   # Balanced male
            'en-US-BrianMultilingualNeural',    # Deep male
            'en-US-EmmaMultilingualNeural'      # Professional female
        ]
        return random.choice(default_voices)

    def check_audio_exists(self, slug: str) -> bool:
        """
        Check if audio file already exists in R2.

        Args:
            slug: File name (without extension)

        Returns:
            bool: True if file exists
        """
        if not self.r2_client:
            return False

        filename = f"{slug}.mp3"
        bucket = self.r2_config['bucket_name']

        try:
            self.r2_client.head_object(Bucket=bucket, Key=filename)
            return True
        except Exception:
            return False

    def delete_audio(self, slug: str) -> bool:
        """
        Delete audio file from R2.

        Args:
            slug: File name (without extension)

        Returns:
            bool: True if successful
        """
        if not self.r2_client:
            return False

        filename = f"{slug}.mp3"
        bucket = self.r2_config['bucket_name']

        try:
            self.r2_client.delete_object(Bucket=bucket, Key=filename)
            logger.info(f"Deleted audio: {filename}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete {filename}: {e}")
            return False

    def reset_call_count(self) -> None:
        """Reset the API call counter."""
        self.api_call_count = 0
