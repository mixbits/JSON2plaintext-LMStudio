import json
import argparse
import os
import re
import html
import logging
from datetime import datetime, timezone
from tqdm import tqdm

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
            return extract_content(item['text'])
        elif 'content' in item:
            return extract_content(item['content'])
        elif 'steps' in item:
            content = ''
            for step in item.get('steps', []):
                if step.get('type') == 'contentBlock':
                    content += extract_content(step.get('content', []))
            return content
        elif 'messages' in item:
            return extract_content(item['messages'])
        elif 'data' in item:
            return extract_content(item['data'])
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

    for message in tqdm(messages, desc="Processing messages"):
        # Handle 'versions' with 'currentlySelected'
        if 'versions' in message:
            version_index = message.get('currentlySelected', 0)
            versions = message.get('versions', [])
            if version_index < len(versions):
                version = versions[version_index]
                role = version.get('role', 'Unknown').capitalize()
                content = extract_content(version)
            else:
                logging.warning("'currentlySelected' index out of range.")
                continue
        else:
            role = message.get('role', 'Unknown').capitalize()
            content = extract_content(message)

        content = clean_content(content)

        if not content:
            continue

        timestamp_str = ''
        if include_timestamps and 'timestamp' in message:
            timestamp = datetime.fromtimestamp(
                message['timestamp'], tz=timezone.utc
            ).strftime('%Y-%m-%d %H:%M:%S %Z')
            timestamp_str = f" [{timestamp}]"

        if output_format == 'markdown':
            formatted_message = f"### {role}{timestamp_str}\n\n{content}\n\n"
        elif output_format == 'html':
            formatted_message = f"""<div class="{role.lower()}">
    <h3>{role}{timestamp_str}</h3>
    <p>{content}</p>
</div>\n"""
        else:
            formatted_message = f"{role}{timestamp_str}:\n{content}\n\n"

        formatted_dialogue += formatted_message

    return formatted_dialogue

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s: %(message)s'
    )

def main():
    setup_logging()
    parser = argparse.ArgumentParser(
        description='Convert JSON conversation to readable text.',
        epilog='Example: python script.py input.json -o markdown -t -f output.md'
    )
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
        messages = data.get('messages')
        if not messages:
            logging.error("Error: 'messages' key not found in JSON.")
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
        logging.info(f"Formatted conversation saved to {output_file}")

    except FileNotFoundError:
        logging.error("Error: Input file not found.")
    except json.JSONDecodeError:
        logging.error("Error: Invalid JSON format in the input file.")
    except Exception as e:
        logging.exception(f"An unexpected error occurred: {e}")

if __name__ == '__main__':
    main()
