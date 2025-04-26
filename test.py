import json
import os
from collections import defaultdict
from django.core.management import call_command

# STEP 1: Load existing dump data
with open('mydata-new.json', 'r') as f:
    data = json.load(f)

# STEP 2: Modify the data
# Example: Remove duplicate users by email, keeping the first one
cleaned_data = [obj for obj in data if obj["model"] != "wallet.wallet"]

# STEP 3: Save the new data
with open('mdump.json', 'w') as f:
    json.dump(cleaned_data, f, indent=2)

print("✅ Modified data saved as new_dump.json")

