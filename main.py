import ollama, glob, json, argparse, os

MODEL = "mistral:7b" #gemma3:4b is also alright, but a little stupid imo, mistral:7b is good but compared to gemma its pretty much the same

systemPrompt = """You are a perfectionist at readability who creates concise filenames that accurately describe files, removing unnecessary parameters. Keep filenames short and simple, only removing words and not adding new ones.

CRITICAL RULES:
1. ALWAYS preserve the original file extension (e.g., .pdf, .azw3, .epub, .mobi, .txt, .docx)
2. ALWAYS use spaces between words, NEVER underscores
3. Use single hyphens (-) to separate major sections, not double dashes (--)

Instructions:
1. Analyze the filename carefully.
2. Return a **single JSON object** with this format:
   {
     "correction": "New filename WITH original extension",
     "reasoning": "Brief explanation of changes"
   }
3. Do not include anything outside the JSON object.
4. Example: 'Practical Cryptography _ Algorithms and Implementations -- Pathan, Al-Sakib Khan, Azad, Saiful -- Boca Raton, 2014 -- CRC Press_Taylor & Francis; -- 9780367378158 -- 648975ece79a6ebc960543c56941acb9 -- Anna's Archive.pdf' 
   becomes 'Practical Cryptography Algorithms and Implementations - Pathan, Al-Sakib Khan, Azad, Saiful - Boca Raton.pdf'

5. Another example: 'Crypto_ How the Code Rebels Beat the Government Saving -- Steven Levy -- 2001 -- Penguin Group (USA) Incorporated E-Books -- 9780786516650 -- 3cbfefcf8dd3fb39800c3794e2f8fed3 -- Anna's Archive.azw3'
   becomes 'Crypto How the Code Rebels Beat the Government - Steven Levy - 2001.azw3'

Remove:
- Download sources (e.g., "Anna's Archive")
- File hashes (long alphanumeric strings)
- ISBNs (13-digit numbers)
- Publisher names (optional, keep if space permits)
- Replace ALL underscores with spaces
- Replace double dashes (--) with single hyphens (-)
- Remove semicolons and unnecessary punctuation
- Make sure it looks readable and human
- Keep the new filename faithful to the title of the original, dont change the name of the book, just make it more readable and natural

REMEMBER: Keep the file extension! Use spaces, not underscores!

Filename to process:
"""

parser = argparse.ArgumentParser(description="Refine filenames")
parser.add_argument("directory", type=str, help="The directory to recurse under")
args = parser.parse_args()

namePairs = [] #structure is like [[originaname, newname], [and so on for every renamed one]]

files = glob.glob(f"{args.directory}/**/*", recursive=True)
for filepath in files:
    split = filepath.split("/")
    fn = split[len(split) - 1]

    # Generate corrections using Ollama with structured JSON output
    response = ollama.generate(
        model=MODEL,
        prompt=fn,
        system=systemPrompt,
        format="json"
    )

    try:
        # Ollama returns structured output in response['content']
        corrections = json.loads(response.get("response", {}))
        newFn = corrections.get("correction")
        reason = corrections.get("reasoning")

        if newFn == None or reason == None:
            counter = 0
            while counter <= 3:
                response = ollama.generate(
                    model=MODEL,
                    prompt=fn,
                    system=systemPrompt,
                    format="json"
                )
                corrections = json.loads(response.get("response", {}))
                newFn = corrections.get("correction")
                reason = corrections.get("reasoning")
                counter += 1
            if newFn == None and reason == None:
                print(f"Failed to pick a good name for {fn}")
                continue
        
        #print(json.dumps(corrections,indent=3))

        extension = fn.split(".", 1)[1]
        if not newFn.endswith(extension):
            newFn = f"{newFn}.{extension}" #LLMS cant always be trusted
        
        print(f"ORIGINAL: {fn}")
        print(f"NEW     : {newFn}")
        print(f"Notes   : {reason}")
        if not input("Accept [Y/n]: ").lower().startswith("n"):
            newFpSplit = split
            newFpSplit[len(split) - 1] = newFn
            newFp = "/".join(newFpSplit)
            namePairs.append([filepath, newFp])
            #print(namePairs)
        print("-"*50)
    except Exception as e:
        print(f"Error processing {filepath}: {e}")

percentage = round((len(namePairs)/len(files))*100, 2)
print(f"processed {len(namePairs)}/{len(files)} files ({percentage}%)")

input("Gone through all files, go over the changes above again, then, press enter to rename")

for i in namePairs:
    os.rename(i[0], i[1])

print(f"Renamed {len(namePairs)} files")