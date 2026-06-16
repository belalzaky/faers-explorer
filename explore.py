# explore.py — fetch the top 10 adverse-event reactions from the openFDA FAERS database

# "import" loads a library so we can use its tools in this script
import requests   # lets us make web (HTTP) requests
import pandas as pd  # pd is the conventional short name for pandas

# ── 1. Build the API URL ──────────────────────────────────────────────────────
#
# The openFDA drug/event endpoint lets us query the FAERS database for free.
# We use a "count" query, which tells the API:
#   "Group all reports by reaction term and count how many times each appears."
#
# URL breakdown:
#   base        = https://api.fda.gov/drug/event.json
#   ?count=     = which field to group/count by
#   patient.reaction.reactionmeddrapt.exact
#               = the standardized medical term for each reaction
#   &limit=10   = only return the top 10 results

URL = (
    "https://api.fda.gov/drug/event.json"
    "?count=patient.reaction.reactionmeddrapt.exact"
    "&limit=10"
)

# ── 2. Fetch the data ─────────────────────────────────────────────────────────
#
# requests.get() sends an HTTP GET request to the URL — the same thing your
# browser does when you visit a website. The server replies with JSON data.
# JSON is just structured text; think of it like a nested dictionary.

print("Fetching data from openFDA...")
response = requests.get(URL)

# raise_for_status() will immediately crash with a helpful error message
# if the server returned an error (e.g. rate limit, bad URL).
# Better to fail loudly than silently produce wrong results.
response.raise_for_status()

# .json() parses the raw text into a Python dictionary we can work with
data = response.json()

# ── 3. Extract the results ────────────────────────────────────────────────────
#
# The API response looks like this (simplified):
#   {
#     "results": [
#       {"term": "DEATH",  "count": 123456},
#       {"term": "NAUSEA", "count": 98765},
#       ...
#     ]
#   }
#
# We dig into ["results"] to get the list of reaction/count pairs.

results = data["results"]

# ── 4. Load into a pandas DataFrame ──────────────────────────────────────────
#
# A DataFrame is like a spreadsheet table — rows and columns.
# pd.DataFrame(results) takes the list of dictionaries and turns each
# dictionary into one row, with the dictionary keys becoming column names.
#
# "term" = the medical reaction name  |  "count" = number of FAERS reports

df = pd.DataFrame(results)

# Rename columns to something more human-readable
df.columns = ["Reaction", "Number of Reports"]

# Add a rank column (1 = most reported)
df.insert(0, "Rank", range(1, len(df) + 1))

# ── 5. Print the table ────────────────────────────────────────────────────────
#
# to_string(index=False) prints the DataFrame as a plain text table
# without the default row numbers pandas adds on the left.

print("\nTop 10 Most-Reported Adverse Event Reactions in FAERS\n")
print(df.to_string(index=False))
print(f"\nDatabase last updated: {data['meta']['last_updated']}")
