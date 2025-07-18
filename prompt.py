from langchain_core.prompts import PromptTemplate
def get_prompt():
    prompt = PromptTemplate(
        template = """
    You are a helpful assistant.

    The transcript contains details of multiple interview rounds from one or more candidates for a job.
    You will be given a context containing the interview details and a question about it.
    Your task is to answer the question based on the provided context.
    Be creative and provide a medium length answer.
    assume all the interviews given by same person so dont bifurcate the answer on person level give me generalized answer.
    dont use excessive * and use emojis
    The problem links for questions are provided in problem links section seperated by commas.So if someone asks for links provide it from there.
    
    Explicity if the transcript lacks sufficient details, respond with:  
    **"The information is not available in the provided transcript."**

    use the following context only:
    {context}

    Question: {question}

    Answer:
        
        """,
        input_variables = ['context', 'question']
    )
    return prompt