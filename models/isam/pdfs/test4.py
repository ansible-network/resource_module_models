data = [{"text":"a","position":2},{"text":"b","position":4},{"text":"c","position":2},{"text":"d","position":4},{"text":"e","position":6}]

result = {"suboptions": {}}
for item in data:
    current = result
    for position in range(item["position"] - 1):
        current = current.setdefault("suboptions", {}).setdefault(data[position]["text"], {})
    current = current.setdefault("suboptions", {})
    current[item["text"]] = None

result = {"options": result["suboptions"]["a"]["suboptions"]}

print(result)