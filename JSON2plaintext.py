import json
import argparse
import os
import re
import html
from datetime import datetime

def clean_content(content):
    """
    Enhanced content cleaning:
    - Removes markdown links
    - Converts HTML entities to characters
    - Trims extra whitespace
    - Removes JSON artifacts and unwanted syntax
    """
    # Remove markdown links
    content = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', content)
    
    # Convert HTML entities to characters
    content = html.unescape(content)
    
    # Remove JSON artifacts (e.g., debug info, status messages)
    content = re.sub(r'\"?\{.*?\}\"?', '', content, flags=re.DOTALL)
    
    # Remove extra whitespace
    content = content.strip()
    
    return content

def extract_content(item):
    """
    Recursively extracts text content from nested JSON structures.
    """
    if isinstance(item, dict):
        if 'text' in item:
            return item['text']
        elif 'content' in item:
            return extract_content(item['content'])
        elif 'steps' in item:
            content = ''
            for step in item['steps']:
                if step.get('type') == 'contentBlock':
                    content += extract_content(step.get('content', []))
            return content
        elif 'messages' in item:
            return extract_content(item['messages'])
    elif isinstance(item, list):
        content = ''
        for elem in item:
            content += extract_content(elem) + '\n'
        return content
    elif isinstance(item, str):
        return item
    return ''

def format_dialogue(messages, output_format, include_timestamps):
    """
    Formats the entire conversation dialogue based on the chosen output format.

    :param messages: List of message dictionaries from the JSON sample
    :param output_format: 'text', 'markdown', or 'html'
    :param include_timestamps: Boolean to include timestamps (if available)
    """
    formatted_dialogue = ""

    for message in messages:
        # Handle 'versions' with 'currentlySelected'
        if 'versions' in message:
            version_index = message.get('currentlySelected', 0)
            versions = message.get('versions', [])
            if version_index < len(versions):
                version = versions[version_index]
                role = version.get('role', 'Unknown').capitalize()
                content = extract_content(version)
            else:
                print("Warning: 'currentlySelected' index out of range.")
                continue
        else:
            role = message.get('role', 'Unknown').capitalize()
            content = extract_content(message)

        content = clean_content(content)

        if not content:
            continue

        if include_timestamps and 'timestamp' in message:
            timestamp = datetime.fromtimestamp(message['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
            formatted_message = f"{role} [{timestamp}]:\n{content}\n\n"
        else:
            formatted_message = f"{role}:\n{content}\n\n"

        formatted_dialogue += formatted_message

    # Format according to the chosen output format
    if output_format == 'markdown':
        # Basic markdown formatting
        formatted_dialogue = formatted_dialogue.replace("\n", "\n\n")
    elif output_format == 'html':
        # Basic HTML formatting
        formatted_dialogue = formatted_dialogue.replace("\n", "<br>")

    return formatted_dialogue

def main():
    parser = argparse.ArgumentParser(description='Convert JSON conversation to readable text.')
    parser.add_argument('input_file', help='Input JSON file containing the conversation.')
    parser.add_argument('-t', '--timestamp', action='store_true', help='Include timestamps in the output.')
    parser.add_argument('-o', '--output_format', choices=['text', 'markdown', 'html'], default='text', help='Output format.')
    parser.add_argument('-f', '--output_file', help='Output file to save the formatted conversation.')

    args = parser.parse_args()

    input_file = args.input_file
    output_format = args.output_format
    include_timestamps = args.timestamp

    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Flexible JSON Structure Handling
        if 'messages' in data:
            messages = data['messages']
        else:
            print("Error: 'messages' key not found in JSON.")
            return

        formatted_dialogue = format_dialogue(messages, output_format, include_timestamps)

        if args.output_file:
            output_file = args.output_file
        else:
            base, _ = os.path.splitext(input_file)
            output_ext = 'txt' if output_format == 'text' else output_format
            output_file = f"{base}_formatted.{output_ext}"

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(formatted_dialogue)
        print(f"Formatted conversation saved to {output_file}")

    except FileNotFoundError:
        print("Error: Input file not found.")
    except json.JSONDecodeError:
        print("Error: Invalid JSON format in the input file.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == '__main__':
    main()
