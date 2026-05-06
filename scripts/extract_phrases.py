import re
text = open('/dev/stdin').read()
text = re.sub(r'<.*?>', ' ', text)
text = re.sub(r'[^a-zA-Z0-9\s:;\-\'\.\,\!\?]', ' ', text)
words = text.split()
phrases = set()
for i in range(len(words)):
    for j in range(i+1, min(i+15, len(words)+1)):
        phrase = ' '.join(words[i:j])
        if 3 < len(phrase) < 120:
            phrases.add(phrase)
            phrases.add(phrase.replace(' ', ''))
            phrases.add(phrase.replace(' ', '_'))
            phrases.add(phrase.replace(' ', '-'))
# Also add the raw lines
for line in text.split('.'):
    line = line.strip()
    if 4 < len(line) < 120:
        phrases.add(line)
        phrases.add(line.replace(' ', ''))
        phrases.add(line.replace(' ', '_'))
with open('creator_phrases_full.txt', 'w') as f:
    for p in sorted(phrases):
        f.write(p + '\n')
print(f'{len(phrases)} seeds generated')
