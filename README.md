# digikam-deduper
Query a Digikam database to find duplicates and write a bash script to move them.

## Features
- Connects to a Digikam SQLite database and automatically attaches the `similarity.db` database.
- Identifies duplicate images based on a similarity threshold.
- Decides which files to keep using customizable rules.
- Generates a bash script to move duplicates to a specified folder.

## Usage
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run the script:
   ```bash
   python main.py --db-folder-path /path/to/digikamdb --output-script move_duplicates.sh --similarity-threshold 90 --top 10
   ```
   - `--db-folder-path`: Path to the folder containing Digikam databases.
   - `--output-script`: Path to the output bash script (default: `move_duplicates.sh`).
   - `--similarity-threshold`: Minimum similarity score for duplicates (default: 90).
   - `--top`: Limit to the top N matches (optional).
3. Execute the generated bash script to move duplicates:
   ```bash
   bash move_duplicates.sh
   ```
