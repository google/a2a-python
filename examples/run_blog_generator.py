import asyncio
import os
# It's good practice to handle potential ImportError for dotenv
try:
    from dotenv import load_dotenv
except ImportError:
    print("python-dotenv library not found. Please install it by running: pip install python-dotenv")
    print("This script relies on a .env file to load your GEMINI_API_KEY.")
    exit(1)


# Assuming ExampleAgent and TaskParameters are accessible via a2a.
# This might require ensuring src is in PYTHONPATH or the package is installed.
# For direct script execution, you might need to adjust sys.path or set PYTHONPATH.
import sys
# Add src to Python path if running script directly from repo root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from a2a.example_agent.agent import ExampleAgent
from a2a.example_agent.agent import TaskParameters # Using the placeholder from agent.py

# MockTaskCompleter to capture results for the script
class ScriptTaskCompleter:
    def __init__(self):
        self.output = None
        self.error = None
        self.has_failed = False

    def complete_task(self, output: any):
        self.output = output
        self.error = None
        self.has_failed = False
        # print(f"Task completed successfully.") # Optional: for verbose logging

    def fail_task(self, error_message: str):
        self.output = None
        self.error = error_message
        self.has_failed = True
        # print(f"Task failed: {error_message}") # Optional: for verbose logging

async def main():
    # Attempt to load .env file from the project root (one level up from examples/)
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path)
        print(f"Loaded .env from {dotenv_path}")
    else:
        # Fallback to trying to load .env from the current directory (examples/)
        if load_dotenv():
             print(f"Loaded .env from current directory")
        else:
            print("No .env file found in project root or current directory.")


    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable not set or .env file not found/loaded.")
        print("Please create a .env file in the project root with your API key:")
        print("Example .env content: GEMINI_API_KEY='your_actual_api_key_here'")
        return

    try:
        agent = ExampleAgent() # Initializes with API key from env
    except ValueError as e:
        print(f"Error initializing agent: {e}")
        return

    completer = ScriptTaskCompleter()

    # 1. Generate Blog Topic
    print("\n--- 1. Generating Blog Topic ---")
    topic_keywords = ["artificial intelligence in healthcare", "future trends", "patient outcomes"]
    print(f"Keywords: {', '.join(topic_keywords)}")
    topic_params = TaskParameters(parameters={
        "capability_name": "generate_blog_topic",
        "keywords": topic_keywords
    })
    await agent.execute_task(completer, topic_params)

    if completer.has_failed:
        print(f"Could not generate topic: {completer.error}")
        return
    blog_topic = completer.output
    print(f"Generated Topic: {blog_topic}")

    # 2. Generate Blog Outline
    print("\n--- 2. Generating Blog Outline ---")
    print(f"Using topic: {blog_topic}")
    outline_params = TaskParameters(parameters={
        "capability_name": "generate_blog_outline",
        "topic": blog_topic
    })
    await agent.execute_task(completer, outline_params)

    if completer.has_failed:
        print(f"Could not generate outline: {completer.error}")
        return
    blog_outline = completer.output
    if not blog_outline: # Check if outline is empty or None
        print(f"Generated outline was empty. Stopping.")
        return

    print(f"Generated Outline:")
    for i, section_title in enumerate(blog_outline):
        print(f"   {i+1}. {section_title}")

    # 3. Write Blog Sections
    print("\n--- 3. Writing Blog Sections ---")
    written_sections = []
    for i, section_title in enumerate(blog_outline):
        # Check if section_title is valid
        if not section_title or not isinstance(section_title, str) or not section_title.strip():
            print(f"  Skipping invalid section title at index {i}: '{section_title}'")
            written_sections.append(f"Skipped section due to invalid title: '{section_title}'")
            continue

        print(f"  Writing section {i+1}: '{section_title}'...")
        section_params = TaskParameters(parameters={
            "capability_name": "write_blog_section",
            "section_prompt": section_title
            # Using default model 'gemini-1.5-flash-latest'
        })
        await agent.execute_task(completer, section_params)

        if completer.has_failed:
            error_msg = completer.error if completer.error else "Unknown error"
            print(f"  Could not write section '{section_title}': {error_msg}")
            written_sections.append(f"Content for '{section_title}' could not be generated: {error_msg}")
            continue # Continue to next section for now

        section_content = completer.output if completer.output else ""
        written_sections.append(section_content)
        print(f"  Section content (first 80 chars): {section_content[:80].replace('\n', ' ')}...")


    # 4. Assemble Blog Post
    print("\n--- 4. Assembling Blog Post ---")
    assembly_params = TaskParameters(parameters={
        "capability_name": "assemble_blog_post",
        "title": blog_topic, # Using the generated topic as title
        "sections": written_sections
    })
    await agent.execute_task(completer, assembly_params)

    if completer.has_failed:
        print(f"Could not assemble blog post: {completer.error}")
        return

    final_blog_post = completer.output
    print("\n--- Generated Blog Post ---")
    print(final_blog_post)

    # Save to file
    output_filename = "generated_blog_post.md"
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(final_blog_post)
    print(f"\nBlog post saved to: {output_filename}")

    print("\n\n--- Example Script Finished ---")
    print("To run this script again: python examples/run_blog_generator.py")
    print("Ensure you have a .env file in the project root (../.env) or in the examples/ directory (./.env) with your GEMINI_API_KEY.")

if __name__ == "__main__":
    asyncio.run(main())
