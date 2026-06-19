import os

# Loaded by pytest before src imports; prevents import-time Anthropic key failures.
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-dummy-for-tests")
