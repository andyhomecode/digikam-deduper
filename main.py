import sqlite3
import argparse
from collections import defaultdict

def connect_to_database(db_folder_path):
    """Connect to the Digikam database and attach the similarity database."""
    digikam_db_path = f"{db_folder_path}/digikam4.db"
    similarity_db_path = f"{db_folder_path}/similarity.db"
    conn = sqlite3.connect(digikam_db_path)
    conn.row_factory = sqlite3.Row  # Enable access to rows as dictionaries
    conn.execute(f"ATTACH DATABASE '{similarity_db_path}' AS similarity_db")
    return conn

def find_duplicates(conn, similarity_threshold, top=None):
    """Query the database to find duplicates above the similarity threshold."""
    cursor = conn.cursor()
    query = f"""
    SELECT
        a.id AS file1_id,
        a.name AS file1_name,
        albums_a.relativePath AS file1_album,
        info_a.creationDate AS file1_creation_date,
        a.modificationDate AS file1_modification_date,
        a.fileSize AS file1_size,
        b.id AS file2_id,
        b.name AS file2_name,
        albums_b.relativePath AS file2_album,
        info_b.creationDate AS file2_creation_date,
        b.modificationDate AS file2_modification_date,
        b.fileSize AS file2_size,
        similarity_db.ImageSimilarity.value AS similarity
    FROM
        Images AS a
    JOIN
        Albums AS albums_a
    ON
        a.album = albums_a.id
    JOIN
        ImageInformation AS info_a
    ON
        a.id = info_a.imageid
    JOIN
        Images AS b
    ON
        a.id < b.id
    JOIN
        Albums AS albums_b
    ON
        b.album = albums_b.id
    JOIN
        ImageInformation AS info_b
    ON
        b.id = info_b.imageid
    JOIN
        similarity_db.ImageSimilarity
    ON
        similarity_db.ImageSimilarity.imageid1 = a.id AND similarity_db.ImageSimilarity.imageid2 = b.id
    WHERE
        similarity_db.ImageSimilarity.value >= ?
    ORDER BY
        similarity_db.ImageSimilarity.value DESC
    """
    if top:
        query += f" LIMIT {top}"
    cursor.execute(query, (similarity_threshold / 100,))
    results = cursor.fetchall()

    # Debugging output: Convert rows to dictionaries for readability
    print("Raw query results:")
    for row in results:
        print(dict(row))  # Convert sqlite3.Row to a dictionary for readable output

    duplicates = []
    for row in results:
        duplicates.append({
            "file1": {
                "path": f"{row['file1_album']}/{row['file1_name']}",
                "creation_date": row["file1_creation_date"],
                "modification_date": row["file1_modification_date"],
                "size": row["file1_size"]
            },
            "file2": {
                "path": f"{row['file2_album']}/{row['file2_name']}",
                "creation_date": row["file2_creation_date"],
                "modification_date": row["file2_modification_date"],
                "size": row["file2_size"]
            },
            "similarity": row["similarity"]
        })
    return duplicates

def group_duplicates(duplicates):
    """Group duplicates into clusters using a graph-based approach."""
    graph = defaultdict(set)

    # Build the graph
    for duplicate in duplicates:
        file1 = duplicate["file1"]["path"]
        file2 = duplicate["file2"]["path"]
        graph[file1].add(file2)
        graph[file2].add(file1)

    # Find connected components (clusters)
    visited = set()
    clusters = []

    def dfs(node, cluster):
        visited.add(node)
        cluster.append(node)
        for neighbor in graph[node]:
            if neighbor not in visited:
                dfs(neighbor, cluster)

    for node in graph:
        if node not in visited:
            cluster = []
            dfs(node, cluster)
            clusters.append(cluster)

    return clusters

def decide_files_to_keep(duplicates):
    """Apply rules to decide which files to keep in each cluster."""
    clusters = group_duplicates(duplicates)
    files_to_move = []

    for cluster in clusters:
        # Extract metadata for each file in the cluster
        cluster_files = []
        for duplicate in duplicates:
            if duplicate["file1"]["path"] in cluster:
                cluster_files.append(duplicate["file1"])
            if duplicate["file2"]["path"] in cluster:
                cluster_files.append(duplicate["file2"])

        # Remove duplicates from the cluster
        cluster_files = {file["path"]: file for file in cluster_files}.values()

        # Apply rules to decide which file to keep
        # Example rule: Keep the file with the earliest creation date
        file_to_keep = min(cluster_files, key=lambda f: f["creation_date"] or "9999-99-99")

        # Mark all other files in the cluster for deletion
        for file in cluster_files:
            if file["path"] != file_to_keep["path"]:
                files_to_move.append((file["path"], "duplicates/"))

    return files_to_move

def generate_bash_script(files_to_move, output_script_path):
    """Generate a bash script to move files."""
    with open(output_script_path, 'w') as script:
        script.write("#!/bin/bash\n\n")
        for src, dest in files_to_move:
            script.write(f"mv \"{src}\" \"{dest}\"\n")

def main():
    parser = argparse.ArgumentParser(description="Find duplicates in a Digikam database.")
    parser.add_argument("--db-folder-path", required=True, help="Path to the folder containing Digikam databases.")
    parser.add_argument("--output-script", default="move_duplicates.sh", help="Path to the output bash script.")
    parser.add_argument("--similarity-threshold", type=int, default=90, help="Similarity threshold for duplicates.")
    parser.add_argument("--top", type=int, default=None, help="Limit to the top N matches.")
    args = parser.parse_args()

    with connect_to_database(args.db_folder_path) as conn:
        duplicates = find_duplicates(conn, args.similarity_threshold, args.top)

        print(f"Processing top {len(duplicates)} duplicates.")

        files_to_move = decide_files_to_keep(duplicates)
        generate_bash_script(files_to_move, args.output_script)
        print(f"Bash script generated at {args.output_script}")

if __name__ == "__main__":
    main()