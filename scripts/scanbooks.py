import os
from pathlib import Path
import re

def count_words(text):
    return len(re.findall(r'\w+', text))

def process_book(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()

    chapters = re.split(r'(?m)^#\s+', content)[1:]  # Split by top-level headers, ignore content before first header
    
    total_words = 0
    chapter_counts = []

    for i, chapter in enumerate(chapters, 1):
        lines = chapter.split('\n')
        chapter_title = lines[0].strip()
        chapter_content = '\n'.join(lines[1:])
        word_count = count_words(chapter_content)
        total_words += word_count
        chapter_counts.append((chapter_title, word_count))

    return chapter_counts, total_words

def main():
    books_dir = Path('books')
    for book_file in books_dir.glob('*.txt'):
        print(f"\nProcessing book: {book_file.name}")
        chapter_counts, total_words = process_book(book_file)
        
        print(f"{'Chapter':<40} {'Word Count':<10}")
        print("-" * 50)
        for title, count in chapter_counts:
            print(f"{title[:37] + '...' if len(title) > 40 else title:<40} {count:<10}")
        
        print("-" * 50)
        print(f"{'Total':<40} {total_words:<10}")

if __name__ == "__main__":
    main()