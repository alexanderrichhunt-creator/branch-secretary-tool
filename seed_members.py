import csv
import os
from pathlib import Path

from app import create_app, db
from app.models import Member, parse_us_date


def main():
    app = create_app()
    data_path = Path(__file__).parent / "data" / "initial_members.tsv"
    if not data_path.exists():
        raise SystemExit(f"Missing data file: {data_path}")

    with app.app_context():
        created = 0
        skipped = 0

        with data_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f, delimiter="\t")
            for row in reader:
                full_name = (row.get("FullName") or "").strip().strip('"')
                if not full_name:
                    continue

                exists = Member.query.filter_by(full_name=full_name).first()
                if exists:
                    skipped += 1
                    continue

                m = Member(
                    full_name=full_name,
                    gender=(row.get("Gender") or "").strip() or None,
                    birthdate=parse_us_date(row.get("Birthdate")),
                    group_label=(row.get("Group") or "").strip() or None,
                )
                db.session.add(m)
                created += 1

        db.session.commit()

    print(f"Seed complete. Created {created}, skipped {skipped}.")


if __name__ == "__main__":
    main()
