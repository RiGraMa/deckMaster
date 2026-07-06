#!/bin/sh
set -e

mkdir -p "$(dirname "$COLLECTION_DB")" "$COMMANDERS_DIR"

if [ -f "$COLLECTION_CSV" ] && [ ! -f "$COLLECTION_DB" ]; then
  echo "First run: migrating $COLLECTION_CSV -> $COLLECTION_DB"
  python migrate_csv_to_db.py --yes
elif [ ! -f "$COLLECTION_CSV" ]; then
  echo "Note: $COLLECTION_CSV not found — place your ManaBox export there to enable collection tracking."
fi

exec "$@"
