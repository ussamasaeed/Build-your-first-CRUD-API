import json

# Load data funcation
def load_data():
    with open("data.json", "r") as f:
        return json.load(f)

# Save data funcation
def save_data(data):
    with open("data.json","w") as f:
        json.dump(data,f)


data = load_data()

for key in data["tasks"]:
    print(["title"] in "Buy milk" )
