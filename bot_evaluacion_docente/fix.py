with open('app_web.py', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('âš¡', '>>')

with open('app_web.py', 'w', encoding='utf-8') as f:
    f.write(text)
