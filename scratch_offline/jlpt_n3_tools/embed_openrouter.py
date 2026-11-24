"""Run scripts.backfill_sense_embeddings with the embedder pointed at OpenRouter (openai/text-embedding-3-small)."""
import os, sys
sys.path.insert(0, '/home/user/LinguaLoop-web'); os.chdir('/home/user/LinguaLoop-web')
from scripts._common import bootstrap
bootstrap()
import services.topic_generation.agents.embedder as emb
from services.topic_generation.config import topic_gen_config as cfg
assert cfg.embedding_model in ('text-embedding-3-small', 'openai/text-embedding-3-small'), cfg.embedding_model
_orig_get_client = emb.get_client
emb.get_client = lambda base_url=None, api_key=None: _orig_get_client(base_url='https://openrouter.ai/api/v1', api_key=os.environ['OPENROUTER_API_KEY'])
cfg.openai_api_key = cfg.openai_api_key or 'via-openrouter'
cfg.embedding_model = 'openai/text-embedding-3-small'
import scripts.backfill_sense_embeddings as b
sys.argv = ['backfill_sense_embeddings'] + sys.argv[1:]
b.main()
