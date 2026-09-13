import os
from groq import Groq
from config import MODEL
from dotenv import load_dotenv

load_dotenv()

api_key = os.environ.get("groq_api_key")
MODEL_NAME = MODEL

def main():
    # Read question from file
    

    # Get API key from environment variable
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("Error: GROQ_API_KEY environment variable not set!")
        print("Set it with: export GROQ_API_KEY=your_key_here")
        return

    # Initialize Groq client
    client = Groq(api_key=api_key)

    print(f"Using model: {MODEL_NAME}")
    print(f"Question: Hi\n")
    print("Generating response...\n")

    # Call Groq API
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hi"}
        ],
        temperature=0.7,
        max_tokens=1024,
        top_p=1,
    )

    output = response.choices[0].message.content

    # Print output
    print("=" * 50)
    print("OUTPUT:")
    print("=" * 50)
    print(output)



if __name__ == "__main__":
    main()