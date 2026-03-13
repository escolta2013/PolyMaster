
import docx
import sys

def extract_text(filepath):
    doc = docx.Document(filepath)
    full_text = []
    for para in doc.paragraphs:
        full_text.append(para.text)
    return "\n".join(full_text)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extract_docx.py <filepath>")
    else:
        text = extract_text(sys.argv[1])
        sys.stdout.buffer.write(text.encode('utf-8'))
