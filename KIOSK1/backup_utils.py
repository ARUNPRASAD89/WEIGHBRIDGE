import subprocess
import os
import db_utils # To get DB_CONFIG

def backup_database(output_filepath):
    """
    Creates a backup of the PostgreSQL database using pg_dump.

    Args:
        output_filepath (str): The full path where the .sql backup file will be saved.

    Returns:
        tuple[bool, str]: A tuple containing a boolean for success/failure
                          and a message (error message on failure, success message on success).
    """
    config = db_utils.DB_CONFIG
    pg_dump_cmd = "pg_dump"

    # Set the PGPASSWORD environment variable to avoid password prompts
    # This is more secure than passing the password on the command line.
    env = os.environ.copy()
    env["PGPASSWORD"] = config["password"]

    command = [
        pg_dump_cmd,
        "-U", config["user"],
        "-h", config["host"],
        "-d", config["database"],
        "-f", output_filepath,
        "--format=p",      # p = plain text SQL script
        "--no-owner",      # Do not output commands to set ownership of objects
        "--no-privileges", # Do not output commands to set privileges (GRANT/REVOKE)
        "--inserts"        # Dump data as INSERT commands, more portable
    ]

    try:
        # Execute the pg_dump command
        process = subprocess.run(
            command,
            env=env,
            check=True, # This will raise CalledProcessError if pg_dump returns a non-zero exit code
            capture_output=True, # Capture stdout and stderr
            text=True # Decode stdout/stderr as text, requires Python 3.7+
        )
        return True, f"Backup successful!\nFile saved to:\n{output_filepath}"
    except FileNotFoundError:
        error_message = (
            f"Error: The '{pg_dump_cmd}' command was not found.\n\n"
            "Please ensure that the PostgreSQL bin directory (e.g., 'C:\\Program Files\\PostgreSQL\\<version>\\bin') "
            "is included in your system's PATH environment variable."
        )
        return False, error_message
    except subprocess.CalledProcessError as e:
        # pg_dump writes detailed errors to stderr
        error_message = f"Backup failed with exit code {e.returncode}:\n\n{e.stderr}"
        return False, error_message
    except Exception as e:
        return False, f"An unexpected error occurred: {str(e)}"