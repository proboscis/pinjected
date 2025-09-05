from pinjected import design
from pinjected_genai.genai_pricing import GenAIModelTable, genai_state

__design__ = design(genai_model_table=GenAIModelTable(), genai_state=genai_state)
