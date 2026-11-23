class AIService:
    """Holder for the shared OpenAI-compatible client (``app.openai_service``).

    The vocabulary pipeline and the health check read ``.client`` from it.
    """

    def __init__(self, openai_client, config, prompt_service=None, use_openrouter=False):
        self.client = openai_client
        self.config = config
        self.use_openrouter = use_openrouter
