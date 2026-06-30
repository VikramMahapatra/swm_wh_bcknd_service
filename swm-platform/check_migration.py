#!/usr/bin/env python3
"""Check and apply database migrations"""
import subprocess
import sys
import os

def run_migration():
    """Run alembic upgrade"""
    os.chdir("swm-platform")

    result = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "libs/db/alembic.ini", "upgrade", "head"],
        capture_output=True,
        text=True
    )

    # Write output to file
    with open("migration_result.txt", "w") as f:
        f.write("=== ALEMBIC MIGRATION OUTPUT ===\n")
        f.write(f"Return code: {result.returncode}\n\n")
        f.write("=== STDOUT ===\n")
        f.write(result.stdout)
        f.write("\n\n=== STDERR ===\n")
        f.write(result.stderr)

    print(f"Migration completed with code {result.returncode}")
    print(f"Output written to migration_result.txt")

    # Print to console
    print("\n=== STDOUT ===")
    print(result.stdout)
    if result.stderr:
        print("\n=== STDERR ===")
        print(result.stderr)

    return result.returncode == 0

if __name__ == "__main__":
    try:
        success = run_migration()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
