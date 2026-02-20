# Tech Stack Reference

## Core Framework
| Package | Version | Purpose |
|---------|---------|---------|
| Flask | 3.0.3 | Web framework, application core |
| Flask-Cors | 5.0.0 | Cross-Origin Resource Sharing for API endpoints |
| Flask-JWT-Extended | 4.6.0 | JWT token management (headers + cookies) |
| Werkzeug | 3.0.6 | WSGI utility library (Flask dependency) |
| Jinja2 | 3.1.6 | HTML template engine for server-rendered pages |
| gunicorn | 21.2.0 | Production WSGI HTTP server |
| click | 8.1.8 | CLI framework (Flask dependency) |
| blinker | 1.8.2 | Signal support (Flask dependency) |
| itsdangerous | 2.2.0 | Data signing (Flask sessions) |
| MarkupSafe | 2.1.5 | HTML escaping (Jinja2 dependency) |

## Database & Auth
| Package | Version | Purpose |
|---------|---------|---------|
| supabase | 2.6.0 | Supabase Python client (PostgreSQL + Auth + Storage) |
| postgrest | 0.16.11 | PostgREST client for Supabase queries |
| gotrue | 2.9.2 | Supabase Auth client (OTP, JWT, sessions) |
| storage3 | 0.7.7 | Supabase Storage client |
| supafunc | 0.5.1 | Supabase Edge Functions client |
| realtime | 1.0.6 | Supabase Realtime subscriptions |
| PyJWT | 2.9.0 | JWT encoding/decoding |
| bcrypt | 4.3.0 | Password hashing (available but OTP-only auth used) |
| cryptography | 45.0.6 | Cryptographic primitives |

## AI & ML Services
| Package | Version | Purpose |
|---------|---------|---------|
| openai | 1.99.3 | OpenAI API client (GPT, embeddings, TTS, moderation) |
| azure-cognitiveservices-speech | 1.40.0 | Azure Speech Services for TTS audio generation |

## Cloud Storage
| Package | Version | Purpose |
|---------|---------|---------|
| boto3 | 1.37.38 | AWS SDK - used for Cloudflare R2 (S3-compatible) |
| botocore | 1.37.38 | Core boto3 library |
| s3transfer | 0.11.5 | S3 transfer management |

## Payments
| Package | Version | Purpose |
|---------|---------|---------|
| stripe | 12.4.0 | Stripe payment processing for token purchases |

## Data & Validation
| Package | Version | Purpose |
|---------|---------|---------|
| pydantic | 2.10.6 | Data validation and settings management |
| pydantic_core | 2.27.2 | Core pydantic library |
| annotated-types | 0.7.0 | Type annotation support |
| typing_extensions | 4.13.2 | Backported typing features |

## HTTP & Networking
| Package | Version | Purpose |
|---------|---------|---------|
| httpx | 0.27.2 | Modern async HTTP client (used by Supabase) |
| httpcore | 1.0.9 | Core HTTP transport |
| requests | 2.32.4 | HTTP library for external API calls |
| urllib3 | 1.26.20 | HTTP client utilities |
| h2 | 4.1.0 | HTTP/2 protocol support |
| h11 | 0.16.0 | HTTP/1.1 protocol support |
| hpack | 4.0.0 | HTTP/2 header compression |
| hyperframe | 6.0.1 | HTTP/2 frame handling |
| certifi | 2025.8.3 | SSL certificate bundle |
| idna | 3.10 | Internationalized domain names |
| charset-normalizer | 3.4.2 | Character encoding detection |
| anyio | 4.5.2 | Async I/O abstraction |
| sniffio | 1.3.1 | Async library detection |
| websocket-client | 1.8.0 | WebSocket client (Supabase Realtime) |
| websockets | 12.0 | WebSocket protocol support |

## Content & Scraping
| Package | Version | Purpose |
|---------|---------|---------|
| beautifulsoup4 | 4.13.4 | HTML/XML parsing |
| html5lib | 1.1 | HTML5 parser |
| soupsieve | 2.7 | CSS selector support for BeautifulSoup |
| webencodings | 0.5.1 | Web character encoding |
| praw | 7.8.1 | Reddit API wrapper (content sourcing) |
| prawcore | 2.4.0 | Core PRAW library |
| newsapi-python | 0.2.7 | News API client (content sourcing) |

## Testing
| Package | Version | Purpose |
|---------|---------|---------|
| pytest | 8.3.5 | Python test framework |
| pytest-flask | 1.3.0 | Flask test integration |
| pluggy | 1.5.0 | Plugin system (pytest dependency) |
| iniconfig | 2.1.0 | INI config parsing (pytest dependency) |
| tomli | 2.2.1 | TOML parsing |
| exceptiongroup | 1.3.0 | Exception groups backport |

## Configuration & Environment
| Package | Version | Purpose |
|---------|---------|---------|
| python-dotenv | 1.0.1 | Load .env file variables |
| python-decouple | 3.8 | Configuration management |

## Utilities
| Package | Version | Purpose |
|---------|---------|---------|
| tenacity | 8.2.3 | Retry logic with exponential backoff |
| tqdm | 4.67.1 | Progress bars for batch scripts |
| uuid | 1.30 | UUID generation |
| python-dateutil | 2.9.0 | Date parsing utilities |
| six | 1.17.0 | Python 2/3 compatibility |
| colorama | 0.4.6 | Terminal color output (Windows) |
| psutil | (latest) | System/process utilities |
| packaging | 25.0 | Version parsing |
| update-checker | 0.18.0 | Package update checking |
| deprecation | 2.1.0 | Deprecation warning helpers |
| distro | 1.9.0 | Linux distribution info |
| jiter | 0.9.1 | Fast JSON parsing |
| jmespath | 1.0.1 | JSON query language (boto3 dependency) |
| StrEnum | 0.4.15 | String enum support |
| importlib_metadata | 8.5.0 | Package metadata access |
| zipp | 3.20.2 | Zipfile path utilities |
| cffi | 1.17.1 | C FFI for Python |
| pycparser | 2.22 | C parser (cffi dependency) |

## Key Architectural Choices

### Why Flask over Django/FastAPI?
Lightweight, flexible, well-suited for a template-rendered app with REST API endpoints. No ORM needed (Supabase client handles DB).

### Why Supabase over raw PostgreSQL?
Provides managed PostgreSQL with built-in Auth (OTP), Row-Level Security, Edge Functions, Realtime, and Storage. Reduces infrastructure management.

### Why OpenRouter?
Allows routing to language-specific LLM models (Gemini for English, DeepSeek for Chinese, Qwen for Japanese) through a single API interface.

### Why Cloudflare R2 over AWS S3?
Zero egress fees for audio file delivery. S3-compatible API means boto3 works unchanged.

### Why Azure TTS over OpenAI TTS?
Better multi-language voice quality, more voice options per language, and competitive pricing. Migrated from OpenAI TTS (see AZURE_MIGRATION_GUIDE.md).

## Related Documents
- [Project Overview](01-project-overview.md)
- [Environment Variables](../11-Rules-and-Conventions/04-environment-variables.md)
- [Config Reference](../04-Backend/02-config-reference.md)
